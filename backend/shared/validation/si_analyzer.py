"""
PCB Builder - Signal Integrity Analyzer
Physics-based checks for high-speed signals, impedance, and crosstalk.
"""

import math
from dataclasses import dataclass, field
from typing import Any

from shared.validation.drc_engine import DRCViolation, RuleCategory, RuleSeverity


@dataclass
class SIResult:
    """Signal integrity analysis result."""
    passed: bool
    score: float
    impedance_issues: list[DRCViolation] = field(default_factory=list)
    length_mismatch_issues: list[DRCViolation] = field(default_factory=list)
    crosstalk_issues: list[DRCViolation] = field(default_factory=list)
    return_path_issues: list[DRCViolation] = field(default_factory=list)
    high_speed_nets: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class SignalIntegrityAnalyzer:
    """Analyzes signal integrity for high-speed PCB designs."""

    # Material properties
    FR4_DK = 4.5  # Dielectric constant
    FR4_DF = 0.02  # Loss tangent
    COPPER_RESISTIVITY = 1.68e-8  # Ohm·m

    # Impedance targets
    IMPEDANCE_TARGETS = {
        "single_ended": 50.0,
        "usb_2": 90.0,
        "usb_3": 90.0,
        "pcie": 85.0,
        "ethernet": 100.0,
        "ddr4_single": 40.0,
        "ddr4_diff": 80.0,
        "mipi": 100.0,
    }

    # Length matching tolerances (mm)
    LENGTH_TOLERANCES = {
        "usb_2": 0.254,
        "usb_3": 0.127,
        "pcie_gen3": 0.127,
        "pcie_gen4": 0.051,
        "ddr4_data": 0.127,
        "ddr4_addr": 0.508,
        "mipi": 0.127,
    }

    def analyze(self, design_data: dict) -> SIResult:
        """Run full SI analysis."""
        issues = []

        impedance_issues = self._check_impedance(design_data)
        length_issues = self._check_length_matching(design_data)
        crosstalk_issues = self._check_crosstalk(design_data)
        return_path_issues = self._check_return_paths(design_data)

        issues.extend(impedance_issues)
        issues.extend(length_issues)
        issues.extend(crosstalk_issues)
        issues.extend(return_path_issues)

        high_speed_nets = self._identify_high_speed_nets(design_data)

        critical_count = sum(1 for i in issues if i.severity == RuleSeverity.CRITICAL)
        error_count = sum(1 for i in issues if i.severity == RuleSeverity.ERROR)

        score = 100.0 - critical_count * 20 - error_count * 10
        score = max(0.0, score)

        return SIResult(
            passed=critical_count == 0,
            score=round(score, 2),
            impedance_issues=impedance_issues,
            length_mismatch_issues=length_issues,
            crosstalk_issues=crosstalk_issues,
            return_path_issues=return_path_issues,
            high_speed_nets=high_speed_nets,
            summary={
                "total_issues": len(issues),
                "critical": critical_count,
                "error": error_count,
                "warning": sum(1 for i in issues if i.severity == RuleSeverity.WARNING),
                "high_speed_nets_identified": len(high_speed_nets),
                "impedance_controlled_nets": sum(1 for n in high_speed_nets if n.get("impedance_controlled", False)),
            },
        )

    def _identify_high_speed_nets(self, design_data: dict) -> list[dict]:
        """Identify nets that require SI attention."""
        nets = design_data.get("nets", [])
        high_speed = []

        for net in nets:
            name = net.get("name", "").upper()
            interface_type = None
            speed_mbps = 0
            impedance_target = None

            if "USB" in name:
                interface_type = "USB"
                if "3" in name:
                    speed_mbps = 5000
                    impedance_target = 90.0
                else:
                    speed_mbps = 480
                    impedance_target = 90.0
            elif "PCIE" in name or "PCI_E" in name:
                interface_type = "PCIe"
                speed_mbps = 8000
                impedance_target = 85.0
            elif "DDR" in name:
                interface_type = "DDR"
                speed_mbps = 3200
                impedance_target = 40.0 if "DATA" in name else 80.0
            elif "MIPI" in name:
                interface_type = "MIPI"
                speed_mbps = 1500
                impedance_target = 100.0
            elif "ETH" in name or "LAN" in name:
                interface_type = "Ethernet"
                speed_mbps = 1000
                impedance_target = 100.0
            elif "HDMI" in name:
                interface_type = "HDMI"
                speed_mbps = 5940
                impedance_target = 100.0
            elif "SPI" in name and "CLK" in name:
                interface_type = "SPI"
                speed_mbps = 50
                impedance_target = 50.0
            elif "I2C" in name and "CLK" in name:
                interface_type = "I2C"
                speed_mbps = 3.4
                impedance_target = None  # Not typically impedance controlled

            if interface_type:
                high_speed.append({
                    "name": net.get("name", ""),
                    "interface": interface_type,
                    "speed_mbps": speed_mbps,
                    "impedance_target_ohm": impedance_target,
                    "impedance_controlled": impedance_target is not None,
                    "pins": len(net.get("pins", [])),
                })

        return high_speed

    def _check_impedance(self, design_data: dict) -> list[DRCViolation]:
        """Check impedance for controlled impedance nets."""
        issues = []
        tracks = design_data.get("tracks", [])
        board = design_data.get("board_config", {})
        dielectric_thickness = board.get("thickness_mm", 1.6) / board.get("layers", 2)

        high_speed_nets = self._identify_high_speed_nets(design_data)

        for net_info in high_speed_nets:
            if not net_info.get("impedance_controlled"):
                continue

            net_name = net_info["name"]
            target = net_info["impedance_target_ohm"]
            net_tracks = [t for t in tracks if t.get("net", "").upper() == net_name]

            for track in net_tracks:
                width = track.get("width", 0.25)
                # Simplified impedance calculation (microstrip approximation)
                # Z0 ≈ 87 / sqrt(εr + 1.41) * ln(5.98h / (0.8w + t))
                # where h = dielectric thickness, w = trace width, t = copper thickness
                copper_thickness = 0.035  # 1oz = 35um
                h = dielectric_thickness
                w = width
                t = copper_thickness

                if w > 0 and h > 0:
                    z0 = 87 / math.sqrt(self.FR4_DK + 1.41) * math.log(5.98 * h / (0.8 * w + t))
                    tolerance = target * 0.10  # ±10%

                    if abs(z0 - target) > tolerance:
                        issues.append(DRCViolation(
                            rule_id="SI001",
                            rule_name="Impedance Control",
                            category=RuleCategory.HIGH_SPEED,
                            severity=RuleSeverity.ERROR,
                            message=f"Net '{net_name}' impedance {z0:.1f}Ω deviates from target {target}Ω (±{tolerance:.1f}Ω)",
                            location={"x": track["start"][0], "y": track["start"][1], "layer": track.get("layer", "F.Cu")},
                            affected_nets=[net_name],
                            measured_value=z0,
                            required_value=target,
                            unit="Ω",
                            suggestion=f"Adjust trace width to achieve {target}Ω. Current width {width}mm, try {self._suggest_trace_width(target, h):.3f}mm",
                            ipc_reference="IPC-2141A",
                            fix_strategy="adjust_trace_width",
                        ))

        return issues

    def _check_length_matching(self, design_data: dict) -> list[DRCViolation]:
        """Check length matching for differential pairs and parallel buses."""
        issues = []
        routing = design_data.get("routing", {})
        diff_pairs = routing.get("differential_pairs", [])
        tracks = design_data.get("tracks", [])

        for pair in diff_pairs:
            pos_net = pair.get("net_pos", "")
            neg_net = pair.get("net_neg", "")

            pos_tracks = [t for t in tracks if t.get("net", "") == pos_net]
            neg_tracks = [t for t in tracks if t.get("net", "") == neg_net]

            pos_length = sum(self._track_length(t) for t in pos_tracks)
            neg_length = sum(self._track_length(t) for t in neg_tracks)
            diff = abs(pos_length - neg_length)

            # Determine tolerance based on interface
            name_upper = (pos_net + neg_net).upper()
            tolerance = 0.254  # Default 10mil
            if "USB3" in name_upper or "PCIE" in name_upper:
                tolerance = 0.127
            elif "MIPI" in name_upper:
                tolerance = 0.127
            elif "DDR4" in name_upper:
                tolerance = 0.127

            if diff > tolerance:
                issues.append(DRCViolation(
                    rule_id="SI002",
                    rule_name="Differential Pair Length Match",
                    category=RuleCategory.HIGH_SPEED,
                    severity=RuleSeverity.ERROR,
                    message=f"Differential pair {pos_net}/{neg_net} length mismatch: {diff:.3f}mm (tolerance: {tolerance}mm)",
                    location={"x": 0, "y": 0, "layer": "F.Cu"},
                    affected_nets=[pos_net, neg_net],
                    measured_value=diff,
                    required_value=tolerance,
                    unit="mm",
                    suggestion=f"Add serpentine tuning to shorter trace. {pos_net}={pos_length:.2f}mm, {neg_net}={neg_length:.2f}mm",
                    ipc_reference="IPC-2141A Section 4.2",
                    fix_strategy="add_length_matching",
                ))

        return issues

    def _check_crosstalk(self, design_data: dict) -> list[DRCViolation]:
        """Check for potential crosstalk between adjacent signals."""
        issues = []
        tracks = design_data.get("tracks", [])
        high_speed_nets = self._identify_high_speed_nets(design_data)
        hs_names = {n["name"] for n in high_speed_nets}

        for i, t1 in enumerate(tracks):
            net1 = t1.get("net", "")
            if net1 not in hs_names:
                continue

            for j, t2 in enumerate(tracks):
                if i >= j or t1.get("layer") != t2.get("layer"):
                    continue
                net2 = t2.get("net", "")
                if net1 == net2:
                    continue

                dist = self._segment_distance(
                    t1.get("start", [0, 0]), t1.get("end", [0, 0]),
                    t2.get("start", [0, 0]), t2.get("end", [0, 0]),
                )
                width = t1.get("width", 0.25)
                min_spacing = width * 3  # 3W rule

                if dist < min_spacing and dist >= 0:
                    issues.append(DRCViolation(
                        rule_id="SI003",
                        rule_name="Crosstalk (3W Rule)",
                        category=RuleCategory.HIGH_SPEED,
                        severity=RuleSeverity.WARNING,
                        message=f"High-speed net '{net1}' too close to '{net2}' ({dist:.3f}mm < 3W={min_spacing:.3f}mm)",
                        location={"x": t1["start"][0], "y": t1["start"][1], "layer": t1.get("layer", "F.Cu")},
                        affected_nets=[net1, net2],
                        measured_value=dist,
                        required_value=min_spacing,
                        unit="mm",
                        suggestion="Increase spacing to 3W or route perpendicularly on adjacent layers",
                        ipc_reference="IPC-2141A Section 5.3",
                        fix_strategy="increase_spacing",
                    ))

        return issues

    def _check_return_paths(self, design_data: dict) -> list[DRCViolation]:
        """Check return path continuity for high-speed signals."""
        issues = []
        high_speed_nets = self._identify_high_speed_nets(design_data)
        vias = design_data.get("vias", [])

        for net_info in high_speed_nets:
            net_name = net_info["name"]
            # Simplified check: ensure stitching vias near layer transitions
            # A more complete check would require full 3D analysis
            if net_info.get("speed_mbps", 0) > 1000:
                # Flag if no stitching vias exist (simplified)
                if len(vias) < 2:
                    issues.append(DRCViolation(
                        rule_id="SI004",
                        rule_name="Return Path Continuity",
                        category=RuleCategory.HIGH_SPEED,
                        severity=RuleSeverity.WARNING,
                        message=f"High-speed net '{net_name}' may lack return path stitching vias",
                        location={"x": 0, "y": 0, "layer": "all"},
                        affected_nets=[net_name],
                        suggestion="Add stitching vias near layer transitions for high-speed signals",
                        ipc_reference="IPC-2141A Section 6.1",
                        fix_strategy="add_stitching_vias",
                    ))

        return issues

    def _suggest_trace_width(self, target_z0: float, h: float) -> float:
        """Suggest trace width for target impedance."""
        # Inverted microstrip formula approximation
        # w ≈ (5.98 * h) / exp(target * sqrt(εr + 1.41) / 87) / 0.8
        try:
            denom = math.exp(target_z0 * math.sqrt(self.FR4_DK + 1.41) / 87)
            w = (5.98 * h / denom - 0.035) / 0.8
            return max(0.1, w)
        except:
            return 0.25

    def _track_length(self, track: dict) -> float:
        start = track.get("start", [0, 0])
        end = track.get("end", [0, 0])
        return math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)

    def _segment_distance(self, a1, a2, b1, b2) -> float:
        def dot(u, v): return u[0]*v[0] + u[1]*v[1]
        def sub(u, v): return [u[0]-v[0], u[1]-v[1]]
        def d2(u): return dot(u, u)

        u = sub(a2, a1)
        v = sub(b2, b1)
        w = sub(a1, b1)

        a = dot(u, u)
        b = dot(u, v)
        c = dot(v, v)
        d = dot(u, w)
        e = dot(v, w)

        D = a * c - b * b
        if D < 1e-9:
            return math.sqrt(d2(sub(a1, b1)))

        sc = max(0.0, min(1.0, (b * e - c * d) / D))
        tc = max(0.0, min(1.0, (a * e - b * d) / D))

        p1 = [a1[0] + sc * u[0], a1[1] + sc * u[1]]
        p2 = [b1[0] + tc * v[0], b1[1] + tc * v[1]]
        return math.sqrt(d2(sub(p1, p2)))


def run_si_analysis(design_data: dict) -> SIResult:
    """Convenience function to run SI analysis."""
    analyzer = SignalIntegrityAnalyzer()
    return analyzer.analyze(design_data)
