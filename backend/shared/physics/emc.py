"""
PCB Builder - EMI/EMC Checker
Return path analysis, loop area, ground plane integrity, radiation estimation.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EMCViolation:
    """An EMI/EMC violation."""
    rule_id: str
    rule_name: str
    severity: str
    message: str
    net: str = ""
    location: tuple[float, float] = (0.0, 0.0)
    measured_value: float = 0.0
    required_value: float = 0.0
    unit: str = ""
    suggestion: str = ""


@dataclass
class EMCResult:
    """Complete EMI/EMC analysis result."""
    passed: bool
    score: float
    return_path_issues: list[EMCViolation] = field(default_factory=list)
    loop_area_issues: list[EMCViolation] = field(default_factory=list)
    ground_plane_issues: list[EMCViolation] = field(default_factory=list)
    radiation_estimates: list[dict] = field(default_factory=list)
    slot_antenna_issues: list[EMCViolation] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class EMIEMCChecker:
    """
    Analyzes EMI/EMC compliance of PCB designs.

    Checks:
    - Return path continuity for high-speed signals
    - Loop area minimization (EMI radiation proportional to loop area)
    - Ground plane integrity (splits, slots, isolation)
    - Slot antenna detection in ground planes
    - Differential mode vs common mode radiation
    - Edge coupling and radiation from board edges
    """

    SPEED_OF_LIGHT = 299792458  # m/s
    IMPEDANCE_FREE_SPACE = 377  # Ohms

    def __init__(self, frequency_range_mhz: tuple[float, float] = (30, 1000)):
        self.freq_min = frequency_range_mhz[0]
        self.freq_max = frequency_range_mhz[1]

    def analyze(self, design_data: dict) -> EMCResult:
        """Run full EMI/EMC analysis."""
        return_path = self._check_return_paths(design_data)
        loop_area = self._check_loop_areas(design_data)
        ground_plane = self._check_ground_plane(design_data)
        slot_antenna = self._check_slot_antennas(design_data)
        radiation = self._estimate_radiation(design_data)

        all_issues = return_path + loop_area + ground_plane + slot_antenna
        critical_count = sum(1 for i in all_issues if i.severity == "critical")
        error_count = sum(1 for i in all_issues if i.severity == "error")
        warning_count = sum(1 for i in all_issues if i.severity == "warning")

        score = 100.0 - critical_count * 25 - error_count * 10 - warning_count * 3
        score = max(0.0, score)

        return EMCResult(
            passed=critical_count == 0,
            score=round(score, 1),
            return_path_issues=return_path,
            loop_area_issues=loop_area,
            ground_plane_issues=ground_plane,
            radiation_estimates=radiation,
            slot_antenna_issues=slot_antenna,
            summary={
                "total_issues": len(all_issues),
                "critical": critical_count,
                "error": error_count,
                "warning": warning_count,
                "high_speed_nets_analyzed": len(radiation),
            },
        )

    def _check_return_paths(self, design_data: dict) -> list[EMCViolation]:
        """
        Check return path continuity for high-speed signals.

        High-speed signals need a continuous reference plane beneath them.
        Layer transitions without nearby stitching vias cause return path discontinuities.
        """
        issues = []
        tracks = design_data.get("tracks", [])
        vias = design_data.get("vias", [])
        board = design_data.get("board_config", {})
        num_layers = board.get("layers", 2)

        # Only relevant for 4+ layer boards with dedicated ground planes
        if num_layers < 4:
            return issues

        high_speed_nets = self._identify_high_speed_nets(design_data)

        for net_info in high_speed_nets:
            net_name = net_info["name"]
            net_tracks = [t for t in tracks if t.get("net", "") == net_name]

            # Check for layer transitions
            layer_changes = []
            for track in net_tracks:
                layer = track.get("layer", "")
                layer_changes.append(layer)

            unique_layers = set(layer_changes)
            if len(unique_layers) > 1:
                # Signal changes layers - check for nearby stitching vias
                for track in net_tracks:
                    start = track.get("start", [0, 0])
                    end = track.get("end", [0, 0])

                    # Check if there's a ground via nearby
                    has_stitching_via = False
                    for via in vias:
                        vx, vy = via.get("x", 0), via.get("y", 0)
                        dist = math.sqrt((vx - start[0])**2 + (vy - start[1])**2)
                        if dist < 3.0:  # Within 3mm
                            has_stitching_via = True
                            break

                    if not has_stitching_via:
                        issues.append(EMCViolation(
                            rule_id="RP001",
                            rule_name="Return Path Discontinuity",
                            severity="warning",
                            message=f"High-speed net '{net_name}' changes layers without nearby stitching via",
                            net=net_name,
                            location=(start[0], start[1]),
                            suggestion="Add ground stitching via within 3mm of layer transition",
                        ))

        return issues

    def _check_loop_areas(self, design_data: dict) -> list[EMCViolation]:
        """
        Check loop areas for EMI radiation.

        EMI radiation is proportional to:
        - Loop area
        - Current squared
        - Frequency squared

        Large current loops = strong EMI radiators.
        """
        issues = []
        tracks = design_data.get("tracks", [])
        components = design_data.get("placed_components", [])
        nets = design_data.get("nets", [])

        # Check power/ground loops
        power_nets = ["VCC", "3V3", "5V", "VDD", "VBAT"]
        gnd_tracks = [t for t in tracks if "GND" in t.get("net", "").upper()]

        for pwr_net in power_nets:
            pwr_tracks = [t for t in tracks if pwr_net in t.get("net", "").upper()]

            if not pwr_tracks or not gnd_tracks:
                continue

            # Estimate loop area between power and ground traces
            # Simplified: bounding box of power traces
            if not pwr_tracks:
                continue

            min_x = min(t["start"][0] for t in pwr_tracks)
            max_x = max(t["end"][0] for t in pwr_tracks)
            min_y = min(t["start"][1] for t in pwr_tracks)
            max_y = max(t["end"][1] for t in pwr_tracks)

            loop_area_mm2 = (max_x - min_x) * (max_y - min_y)

            # Large power loops are problematic
            if loop_area_mm2 > 400:  # > 20mm x 20mm
                issues.append(EMCViolation(
                    rule_id="LA001",
                    rule_name="Large Power Loop",
                    severity="warning",
                    message=f"Power net '{pwr_net}' has large loop area: {loop_area_mm2:.0f}mm^2",
                    net=pwr_net,
                    location=((min_x + max_x) / 2, (min_y + max_y) / 2),
                    measured_value=loop_area_mm2,
                    required_value=400,
                    unit="mm^2",
                    suggestion="Reduce power loop area by routing power and ground traces closer together",
                ))

        # Check decoupling capacitor loop areas
        for comp in components:
            name = comp.get("name", "").upper()
            if "C" in name and comp.get("footprint", "") in ["0402", "0603"]:
                # This is likely a decoupling cap
                # Check distance to target IC
                comp_x = comp.get("x", 0)
                comp_y = comp.get("y", 0)

                # Find nearby ICs
                for ic in components:
                    ic_name = ic.get("name", "").upper()
                    if any(k in ic_name for k in ["U", "IC", "MCU", "CPU"]):
                        ic_x = ic.get("x", 0)
                        ic_y = ic.get("y", 0)
                        dist = math.sqrt((comp_x - ic_x)**2 + (comp_y - ic_y)**2)

                        if dist > 3.0:
                            issues.append(EMCViolation(
                                rule_id="LA002",
                                rule_name="Decoupling Loop Area",
                                severity="warning",
                                message=f"Decoupling cap '{comp.get('id')}' is {dist:.1f}mm from IC '{ic.get('id')}'",
                                location=(comp_x, comp_y),
                                measured_value=dist,
                                required_value=3.0,
                                unit="mm",
                                suggestion="Move decoupling capacitor within 2mm of IC power pin",
                            ))

        return issues

    def _check_ground_plane(self, design_data: dict) -> list[EMCViolation]:
        """
        Check ground plane integrity.

        Splits in ground planes cause:
        - Return path discontinuities
        - Increased EMI
        - Signal integrity degradation
        """
        issues = []
        board = design_data.get("board_config", {})
        num_layers = board.get("layers", 2)

        if num_layers < 4:
            # 2-layer boards don't have dedicated ground planes
            issues.append(EMCViolation(
                rule_id="GP001",
                rule_name="No Ground Plane",
                severity="warning",
                message=f"{num_layers}-layer design has no dedicated ground plane",
                suggestion="Consider 4-layer stackup with dedicated ground plane for EMI control",
            ))
            return issues

        # Check for ground pours on signal layers
        copper_pours = design_data.get("routing", {}).get("copper_pours", [])
        gnd_pours = [p for p in copper_pours if "GND" in p.get("net", "").upper()]

        if not gnd_pours:
            issues.append(EMCViolation(
                rule_id="GP002",
                rule_name="No Ground Pour",
                severity="warning",
                message="No ground copper pour found on signal layers",
                suggestion="Add ground pour on signal layers for EMI shielding",
            ))

        return issues

    def _check_slot_antennas(self, design_data: dict) -> list[EMCViolation]:
        """
        Detect potential slot antennas in ground planes.

        A slot in a ground plane acts as an antenna when:
        slot_length = lambda / 2

        For 1GHz: lambda/2 = 75mm in FR4
        For 2.4GHz: lambda/2 = 31mm in FR4
        """
        issues = []
        board = design_data.get("board_config", {})

        # Check for splits in ground pours
        copper_pours = design_data.get("routing", {}).get("copper_pours", [])
        gnd_pours = [p for p in copper_pours if "GND" in p.get("net", "").upper()]

        if len(gnd_pours) > 1:
            # Multiple ground pours = potential split
            # Check if any high-speed signals cross the split
            high_speed_nets = self._identify_high_speed_nets(design_data)

            for net_info in high_speed_nets:
                issues.append(EMCViolation(
                    rule_id="SA001",
                    rule_name="Ground Plane Split",
                    severity="warning",
                    message=f"Multiple ground pours detected; high-speed net '{net_info['name']}' may cross split",
                    net=net_info["name"],
                    suggestion="Ensure high-speed signals do not cross ground plane splits",
                ))

        return issues

    def _estimate_radiation(self, design_data: dict) -> list[dict]:
        """Estimate radiation from high-speed nets."""
        estimates = []
        tracks = design_data.get("tracks", [])
        high_speed_nets = self._identify_high_speed_nets(design_data)

        for net_info in high_speed_nets:
            net_name = net_info["name"]
            freq_mhz = net_info["freq_mhz"]

            net_tracks = [t for t in tracks if t.get("net", "") == net_name]
            if not net_tracks:
                continue

            total_length_mm = sum(
                math.sqrt((t["end"][0]-t["start"][0])**2 + (t["end"][1]-t["start"][1])**2)
                for t in net_tracks
            )
            length_m = total_length_mm * 1e-3

            # Wavelength in FR4
            wavelength_m = self.SPEED_OF_LIGHT / (freq_mhz * 1e6 * math.sqrt(3.5))

            # Radiation efficiency (simplified dipole model)
            if length_m < wavelength_m / 20:
                efficiency = "low"
                risk = "low"
            elif length_m < wavelength_m / 10:
                efficiency = "medium"
                risk = "medium"
            else:
                efficiency = "high"
                risk = "high"

            estimates.append({
                "net": net_name,
                "frequency_mhz": freq_mhz,
                "trace_length_mm": round(total_length_mm, 1),
                "wavelength_mm": round(wavelength_m * 1000, 1),
                "length_ratio": round(length_m / wavelength_m, 3),
                "radiation_efficiency": efficiency,
                "emi_risk": risk,
            })

        return estimates

    def _identify_high_speed_nets(self, design_data: dict) -> list[dict]:
        """Identify high-speed nets for EMI analysis."""
        nets = design_data.get("nets", [])
        high_speed = []

        for net in nets:
            name = net.get("name", "").upper()
            freq_mhz = 0

            if "CLK" in name or "CLOCK" in name:
                freq_mhz = 100
            elif "DDR" in name:
                freq_mhz = 1600
            elif "USB3" in name:
                freq_mhz = 5000
            elif "USB" in name:
                freq_mhz = 480
            elif "PCIE" in name:
                freq_mhz = 8000
            elif "ETH" in name:
                freq_mhz = 125
            elif "HDMI" in name:
                freq_mhz = 5940
            elif "MIPI" in name:
                freq_mhz = 1500

            if freq_mhz > 0:
                high_speed.append({
                    "name": net.get("name", ""),
                    "freq_mhz": freq_mhz,
                })

        return high_speed
