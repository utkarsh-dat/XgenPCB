"""
PCB Builder - Power Integrity Engine
IR drop analysis, PDN impedance, and current capacity validation.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IRDropIssue:
    """An IR drop violation."""
    net: str
    location: tuple[float, float]
    voltage_drop_mv: float
    max_allowed_mv: float
    severity: str  # critical, warning
    suggestion: str


@dataclass
class PDNIssue:
    """A PDN impedance issue."""
    net: str
    frequency_mhz: float
    impedance_ohm: float
    target_ohm: float
    severity: str
    suggestion: str


@dataclass
class PIResult:
    """Complete power integrity analysis result."""
    passed: bool
    score: float
    ir_drop_issues: list[IRDropIssue] = field(default_factory=list)
    pdn_issues: list[PDNIssue] = field(default_factory=list)
    current_capacity_issues: list[dict] = field(default_factory=list)
    decoupling_analysis: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class PowerIntegrityEngine:
    """
    Analyzes power delivery network integrity.

    Checks:
    - IR drop on power traces (V = I * R)
    - PDN target impedance (Z = Vdd * ripple% / Imax)
    - Trace current capacity (IPC-2152)
    - Decoupling capacitor placement effectiveness
    """

    COPPER_RESISTIVITY = 1.68e-8  # Ohm-m
    COPPER_THICKNESS_1OZ = 35e-6  # meters

    def __init__(
        self,
        copper_thickness_m: float = 35e-6,
        max_temp_rise_c: float = 10.0,
    ):
        self.copper_thickness = copper_thickness_m
        self.max_temp_rise = max_temp_rise_c

    def analyze(self, design_data: dict) -> PIResult:
        """Run full power integrity analysis."""
        ir_issues = self._check_ir_drop(design_data)
        pdn_issues = self._check_pdn_impedance(design_data)
        current_issues = self._check_current_capacity(design_data)
        decap_analysis = self._analyze_decoupling(design_data)

        all_issues = ir_issues + pdn_issues + current_issues
        critical_count = sum(1 for i in all_issues if i.get("severity") == "critical")
        warning_count = sum(1 for i in all_issues if i.get("severity") == "warning")

        score = 100.0 - critical_count * 20 - warning_count * 5
        score = max(0.0, score)

        return PIResult(
            passed=critical_count == 0,
            score=round(score, 1),
            ir_drop_issues=ir_issues,
            pdn_issues=pdn_issues,
            current_capacity_issues=current_issues,
            decoupling_analysis=decap_analysis,
            summary={
                "total_issues": len(all_issues),
                "critical": critical_count,
                "warning": warning_count,
                "ir_drop_max_mv": max((i.voltage_drop_mv for i in ir_issues), default=0),
                "nets_analyzed": len(set(i.net for i in all_issues)),
            },
        )

    def _check_ir_drop(self, design_data: dict) -> list[IRDropIssue]:
        """
        Calculate IR drop on power traces.

        V_drop = I * R where R = rho * L / (w * t)
        """
        issues = []
        tracks = design_data.get("tracks", [])
        components = design_data.get("placed_components", [])

        # Estimate current requirements from components
        current_map = self._estimate_component_currents(components)

        for track in tracks:
            net = track.get("net", "").upper()
            if not any(p in net for p in ["VCC", "3V3", "5V", "VDD", "VBAT", "PWR"]):
                continue

            start = track.get("start", [0, 0])
            end = track.get("end", [0, 0])
            length_m = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2) * 1e-3
            width_m = track.get("width", 0.25) * 1e-3

            # Resistance: R = rho * L / A
            area = width_m * self.copper_thickness
            if area <= 0:
                continue
            resistance = self.COPPER_RESISTIVITY * length_m / area

            # Estimate current for this net
            current_a = current_map.get(track.get("net", ""), 0.1)

            # Voltage drop
            v_drop_v = current_a * resistance
            v_drop_mv = v_drop_v * 1000

            # Determine max allowed drop (typically 3% of Vdd)
            vdd = self._get_net_voltage(net)
            max_drop_mv = vdd * 0.03 * 1000  # 3% of Vdd

            if v_drop_mv > max_drop_mv:
                severity = "critical" if v_drop_mv > max_drop_mv * 2 else "warning"
                issues.append(IRDropIssue(
                    net=track.get("net", ""),
                    location=(start[0], start[1]),
                    voltage_drop_mv=round(v_drop_mv, 2),
                    max_allowed_mv=round(max_drop_mv, 2),
                    severity=severity,
                    suggestion=f"Widen trace or add parallel path. Current: {current_a:.1f}A, Length: {length_m*1000:.1f}mm",
                ))

        return issues

    def _check_pdn_impedance(self, design_data: dict) -> list[PDNIssue]:
        """
        Check PDN target impedance.

        Z_target = Vdd * ripple% / Imax
        """
        issues = []
        components = design_data.get("placed_components", [])
        tracks = design_data.get("tracks", [])

        current_map = self._estimate_component_currents(components)

        for net, current_a in current_map.items():
            if current_a < 0.1:
                continue

            net_upper = net.upper()
            if not any(p in net_upper for p in ["VCC", "3V3", "5V", "VDD", "VBAT"]):
                continue

            vdd = self._get_net_voltage(net_upper)
            ripple_pct = 0.05  # 5% ripple target
            z_target = vdd * ripple_pct / current_a

            # Estimate PDN impedance from trace geometry
            # Simplified: Z ≈ sqrt(L/C) where L and C depend on trace geometry
            net_tracks = [t for t in tracks if t.get("net", "").upper() == net_upper]
            if not net_tracks:
                continue

            total_length = sum(
                math.sqrt((t["end"][0]-t["start"][0])**2 + (t["end"][1]-t["start"][1])**2)
                for t in net_tracks
            )
            avg_width = sum(t.get("width", 0.25) for t in net_tracks) / len(net_tracks)

            # Simplified PDN impedance estimation
            # For a plane: Z ≈ (h / w) * sqrt(mu/epsilon) * length_factor
            h = 0.2e-3  # dielectric thickness (m)
            w = avg_width * 1e-3  # trace width (m)
            length_m = total_length * 1e-3

            # Inductance per unit length for microstrip
            l_per_m = 4e-7 * math.log(4 * h / w + 1)  # H/m (simplified)
            total_inductance = l_per_m * length_m

            # Target frequency (switching frequency estimate)
            freq_mhz = 100  # Default 100 MHz
            omega = 2 * math.pi * freq_mhz * 1e6
            z_pdn = omega * total_inductance

            if z_pdn > z_target:
                issues.append(PDNIssue(
                    net=net,
                    frequency_mhz=freq_mhz,
                    impedance_ohm=round(z_pdn * 1000, 2),  # mOhm
                    target_ohm=round(z_target * 1000, 2),
                    severity="warning",
                    suggestion=f"Add decoupling capacitors near load. Z_PDN={z_pdn*1000:.1f}mOhm > Z_target={z_target*1000:.1f}mOhm",
                ))

        return issues

    def _check_current_capacity(self, design_data: dict) -> list[dict]:
        """
        Check trace current capacity per IPC-2152.

        I = k * A^b where A is cross-sectional area
        """
        issues = []
        tracks = design_data.get("tracks", [])
        components = design_data.get("placed_components", [])
        current_map = self._estimate_component_currents(components)

        for track in tracks:
            net = track.get("net", "").upper()
            if not any(p in net for p in ["VCC", "3V3", "5V", "VDD", "VBAT", "PWR"]):
                continue

            width_mm = track.get("width", 0.25)
            width_m = width_mm * 1e-3
            area_m2 = width_m * self.copper_thickness

            # IPC-2152 approximation for external layers
            # I = 0.048 * A^0.725 for 10C rise (A in mil^2)
            area_mil2 = area_m2 * (1000 / 25.4)**2
            i_max_10c = 0.048 * area_mil2**0.725

            # For 20C rise (more common)
            i_max_20c = i_max_10c * 1.4

            current_a = current_map.get(track.get("net", ""), 0.1)

            if current_a > i_max_20c:
                issues.append({
                    "net": track.get("net", ""),
                    "current_a": round(current_a, 2),
                    "max_current_a": round(i_max_20c, 2),
                    "trace_width_mm": width_mm,
                    "severity": "critical",
                    "message": f"Trace '{track.get('net')}' carries {current_a:.1f}A but can only handle {i_max_20c:.1f}A at 20C rise",
                    "suggestion": f"Widen trace to at least {self._calculate_required_width(current_a):.2f}mm",
                })
            elif current_a > i_max_10c:
                issues.append({
                    "net": track.get("net", ""),
                    "current_a": round(current_a, 2),
                    "max_current_a": round(i_max_10c, 2),
                    "trace_width_mm": width_mm,
                    "severity": "warning",
                    "message": f"Trace '{track.get('net')}' may exceed 10C temperature rise",
                    "suggestion": f"Consider widening trace for lower temperature rise",
                })

        return issues

    def _analyze_decoupling(self, design_data: dict) -> list[dict]:
        """Analyze decoupling capacitor placement and effectiveness."""
        analysis = []
        components = design_data.get("placed_components", [])
        nets = design_data.get("nets", [])

        # Find ICs that need decoupling
        ics = [
            c for c in components
            if any(k in c.get("name", "").upper() for k in ["U", "IC", "MCU", "CPU", "FPGA"])
        ]

        # Find decoupling capacitors
        decaps = [
            c for c in components
            if any(k in c.get("name", "").upper() for k in ["C"])
            and c.get("footprint", "") in ["0402", "0603", "0805"]
        ]

        for ic in ics:
            ic_x = ic.get("x", 0)
            ic_y = ic.get("y", 0)
            ic_id = ic.get("id", "")

            # Find nearby decoupling caps
            nearby_caps = []
            for cap in decaps:
                dx = cap.get("x", 0) - ic_x
                dy = cap.get("y", 0) - ic_y
                dist = math.sqrt(dx**2 + dy**2)
                if dist < 5.0:  # Within 5mm
                    nearby_caps.append({
                        "id": cap.get("id", ""),
                        "distance_mm": round(dist, 2),
                        "footprint": cap.get("footprint", ""),
                    })

            # Sort by distance
            nearby_caps.sort(key=lambda c: c["distance_mm"])

            # Analysis
            has_close_cap = any(c["distance_mm"] < 2.0 for c in nearby_caps)
            cap_count = len(nearby_caps)

            analysis.append({
                "ic_id": ic_id,
                "ic_name": ic.get("name", ""),
                "decoupling_caps": cap_count,
                "closest_cap_mm": nearby_caps[0]["distance_mm"] if nearby_caps else None,
                "adequate": has_close_cap and cap_count >= 2,
                "recommendation": (
                    "Adequate decoupling"
                    if has_close_cap and cap_count >= 2
                    else f"Add decoupling capacitors within 2mm of {ic_id}"
                ),
            })

        return analysis

    def _estimate_component_currents(self, components: list[dict]) -> dict[str, float]:
        """Estimate current consumption from component types."""
        currents = {}

        for comp in components:
            name = comp.get("name", "").upper()
            footprint = comp.get("footprint", "")

            # Typical current estimates
            if any(k in name for k in ["ESP32", "ESP8266"]):
                currents["3V3"] = currents.get("3V3", 0) + 0.25
            elif any(k in name for k in ["STM32"]):
                currents["3V3"] = currents.get("3V3", 0) + 0.15
            elif any(k in name for k in ["FPGA"]):
                currents["VCC"] = currents.get("VCC", 0) + 1.0
                currents["3V3"] = currents.get("3V3", 0) + 0.5
            elif any(k in name for k in ["REG", "LDO", "AMS1117"]):
                pass  # Regulator, current flows through
            elif any(k in name for k in ["LED"]):
                currents["5V"] = currents.get("5V", 0) + 0.02
            elif any(k in name for k in ["USB"]):
                currents["5V"] = currents.get("5V", 0) + 0.5
            elif footprint in ["0402", "0603", "0805"]:
                pass  # Passive, negligible current

        # Ensure minimum current for power nets
        for net in ["VCC", "3V3", "5V", "VDD", "VBAT"]:
            if net not in currents:
                currents[net] = 0.05

        return currents

    def _get_net_voltage(self, net_name: str) -> float:
        """Get nominal voltage for a power net."""
        net = net_name.upper()
        if "3V3" in net or "3.3" in net:
            return 3.3
        elif "5V" in net:
            return 5.0
        elif "1V8" in net or "1.8" in net:
            return 1.8
        elif "1V2" in net or "1.2" in net:
            return 1.2
        elif "1V0" in net or "1.0" in net:
            return 1.0
        elif "2V5" in net or "2.5" in net:
            return 2.5
        else:
            return 3.3  # Default

    def _calculate_required_width(self, current_a: float) -> float:
        """Calculate minimum trace width for given current (IPC-2152)."""
        # Inverse of I = 0.048 * A^0.725
        # A = (I / 0.048)^(1/0.725)
        area_mil2 = (current_a / 0.048) ** (1 / 0.725)
        area_m2 = area_mil2 * (25.4 / 1000)**2
        width_m = area_m2 / self.copper_thickness
        return width_m * 1000  # mm
