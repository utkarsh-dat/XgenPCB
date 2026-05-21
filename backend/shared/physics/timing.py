"""
PCB Builder - Timing Analysis Engine
Propagation delay, setup/hold timing, clock skew, and DDR timing budgets.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TimingViolation:
    """A timing violation."""
    rule_id: str
    rule_name: str
    severity: str
    message: str
    net: str = ""
    location: tuple[float, float] = (0.0, 0.0)
    measured_ns: float = 0.0
    required_ns: float = 0.0
    suggestion: str = ""


@dataclass
class TimingResult:
    """Complete timing analysis result."""
    passed: bool
    score: float
    propagation_issues: list[TimingViolation] = field(default_factory=list)
    setup_hold_issues: list[TimingViolation] = field(default_factory=list)
    clock_skew_issues: list[TimingViolation] = field(default_factory=list)
    ddr_timing_issues: list[TimingViolation] = field(default_factory=list)
    high_speed_nets: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class TimingAnalyzer:
    """
    Analyzes signal timing for high-speed digital designs.

    Checks:
    - Propagation delay (t_prop = length * sqrt(epsilon_r) / c)
    - Setup/hold timing for synchronous interfaces
    - Clock skew between clock domains
    - DDR timing budgets (address/command vs data)
    - SPI/I2C timing margins
    """

    SPEED_OF_LIGHT = 299792458  # m/s
    FR4_DIELECTRIC = 4.5
    FR4_EFFECTIVE = 3.5  # Effective dielectric constant for microstrip

    def __init__(self, dielectric_constant: float = 3.5):
        self.epsilon_r = dielectric_constant
        self.propagation_delay_ps_per_mm = self._calc_prop_delay()

    def _calc_prop_delay(self) -> float:
        """Calculate propagation delay in ps/mm for FR4."""
        v = self.SPEED_OF_LIGHT / math.sqrt(self.epsilon_r)
        return (1 / v) * 1e12  # ps/mm

    def analyze(self, design_data: dict) -> TimingResult:
        """Run full timing analysis."""
        high_speed_nets = self._identify_timing_critical_nets(design_data)

        prop_issues = self._check_propagation_delays(design_data, high_speed_nets)
        setup_hold = self._check_setup_hold(design_data, high_speed_nets)
        clock_skew = self._check_clock_skew(design_data, high_speed_nets)
        ddr_issues = self._check_ddr_timing(design_data, high_speed_nets)

        all_issues = prop_issues + setup_hold + clock_skew + ddr_issues
        critical_count = sum(1 for i in all_issues if i.severity == "critical")
        error_count = sum(1 for i in all_issues if i.severity == "error")
        warning_count = sum(1 for i in all_issues if i.severity == "warning")

        score = 100.0 - critical_count * 25 - error_count * 10 - warning_count * 3
        score = max(0.0, score)

        return TimingResult(
            passed=critical_count == 0,
            score=round(score, 1),
            propagation_issues=prop_issues,
            setup_hold_issues=setup_hold,
            clock_skew_issues=clock_skew,
            ddr_timing_issues=ddr_issues,
            high_speed_nets=high_speed_nets,
            summary={
                "total_issues": len(all_issues),
                "critical": critical_count,
                "error": error_count,
                "warning": warning_count,
                "propagation_delay_ps_per_mm": round(self.propagation_delay_ps_per_mm, 2),
                "timing_critical_nets": len(high_speed_nets),
            },
        )

    def _identify_timing_critical_nets(self, design_data: dict) -> list[dict]:
        """Identify nets that require timing analysis."""
        nets = design_data.get("nets", [])
        critical = []

        for net in nets:
            name = net.get("name", "").upper()
            net_type = None
            freq_mhz = 0
            max_delay_ns = None
            length_tolerance_mm = None

            if "CLK" in name or "CLOCK" in name:
                net_type = "clock"
                freq_mhz = self._estimate_clock_freq(name)
                max_delay_ns = None  # Clocks need skew analysis, not absolute delay
            elif "DDR" in name:
                net_type = "ddr"
                if "ADDR" in name or "CMD" in name:
                    freq_mhz = 100  # DDR address/command typically 100MHz
                    length_tolerance_mm = 0.508  # 20mil
                else:
                    freq_mhz = 1600  # DDR4 data rate
                    length_tolerance_mm = 0.127  # 5mil
            elif "USB" in name:
                net_type = "usb"
                freq_mhz = 480 if "2" not in name else 480
                length_tolerance_mm = 0.254  # 10mil
            elif "PCIE" in name or "PCI_E" in name:
                net_type = "pcie"
                freq_mhz = 8000  # PCIe Gen3+
                length_tolerance_mm = 0.127  # 5mil
            elif "SPI" in name and "CLK" in name:
                net_type = "spi"
                freq_mhz = 50
                max_delay_ns = 10  # 10ns margin for SPI
            elif "I2C" in name and "CLK" in name:
                net_type = "i2c"
                freq_mhz = 3.4  # Fast mode plus
                max_delay_ns = 100  # 100ns margin for I2C
            elif "ETH" in name or "LAN" in name:
                net_type = "ethernet"
                freq_mhz = 125  # 1000BASE-T
                length_tolerance_mm = 0.254
            elif "MIPI" in name:
                net_type = "mipi"
                freq_mhz = 1500
                length_tolerance_mm = 0.127
            elif "HDMI" in name:
                net_type = "hdmi"
                freq_mhz = 5940
                length_tolerance_mm = 0.127

            if net_type:
                critical.append({
                    "name": net.get("name", ""),
                    "type": net_type,
                    "freq_mhz": freq_mhz,
                    "max_delay_ns": max_delay_ns,
                    "length_tolerance_mm": length_tolerance_mm,
                })

        return critical

    def _check_propagation_delays(
        self,
        design_data: dict,
        critical_nets: list[dict],
    ) -> list[TimingViolation]:
        """Check propagation delays against timing budgets."""
        issues = []
        tracks = design_data.get("tracks", [])

        for net_info in critical_nets:
            if not net_info.get("max_delay_ns"):
                continue

            net_name = net_info["name"]
            max_delay = net_info["max_delay_ns"]

            net_tracks = [t for t in tracks if t.get("net", "") == net_name]
            if not net_tracks:
                continue

            total_length_mm = sum(
                math.sqrt((t["end"][0]-t["start"][0])**2 + (t["end"][1]-t["start"][1])**2)
                for t in net_tracks
            )

            prop_delay_ns = total_length_mm * self.propagation_delay_ps_per_mm / 1000

            if prop_delay_ns > max_delay:
                issues.append(TimingViolation(
                    rule_id="TP001",
                    rule_name="Propagation Delay",
                    severity="error",
                    message=f"Net '{net_name}' propagation delay {prop_delay_ns:.2f}ns > {max_delay}ns budget",
                    net=net_name,
                    measured_ns=prop_delay_ns,
                    required_ns=max_delay,
                    suggestion=f"Shorten trace from {total_length_mm:.1f}mm to <{max_delay*1000/self.propagation_delay_ps_per_mm:.1f}mm",
                ))

        return issues

    def _check_setup_hold(
        self,
        design_data: dict,
        critical_nets: list[dict],
    ) -> list[TimingViolation]:
        """Check setup/hold timing for synchronous interfaces."""
        issues = []
        routing = design_data.get("routing", {})
        diff_pairs = routing.get("differential_pairs", [])

        for pair in diff_pairs:
            pos_net = pair.get("net_pos", "")
            neg_net = pair.get("net_neg", "")

            # Find net info
            net_info = None
            for ni in critical_nets:
                if ni["name"] in [pos_net, neg_net]:
                    net_info = ni
                    break

            if not net_info:
                continue

            # Check length matching (affects setup/hold)
            if net_info.get("length_tolerance_mm"):
                length_diff = pair.get("length_diff_mm", 0)
                tolerance = net_info["length_tolerance_mm"]

                if length_diff > tolerance:
                    issues.append(TimingViolation(
                        rule_id="SH001",
                        rule_name="Setup/Hold Timing",
                        severity="error",
                        message=f"Differential pair {pos_net}/{neg_net} length mismatch {length_diff:.3f}mm > {tolerance}mm",
                        net=pos_net,
                        measured_ns=length_diff * self.propagation_delay_ps_per_mm / 1000,
                        required_ns=tolerance * self.propagation_delay_ps_per_mm / 1000,
                        suggestion="Add serpentine tuning to match lengths within timing budget",
                    ))

        return issues

    def _check_clock_skew(
        self,
        design_data: dict,
        critical_nets: list[dict],
    ) -> list[TimingViolation]:
        """Check clock skew between related clock nets."""
        issues = []
        tracks = design_data.get("tracks", [])
        clock_nets = [n for n in critical_nets if n["type"] == "clock"]

        if len(clock_nets) < 2:
            return issues

        # Check skew between clock nets going to same destination
        clock_lengths = {}
        for cn in clock_nets:
            net_tracks = [t for t in tracks if t.get("net", "") == cn["name"]]
            length = sum(
                math.sqrt((t["end"][0]-t["start"][0])**2 + (t["end"][1]-t["start"][1])**2)
                for t in net_tracks
            )
            clock_lengths[cn["name"]] = length

        # Find max skew
        if len(clock_lengths) >= 2:
            lengths = list(clock_lengths.values())
            max_skew_mm = max(lengths) - min(lengths)
            max_skew_ns = max_skew_mm * self.propagation_delay_ps_per_mm / 1000

            # Clock skew budget: typically < 5% of clock period
            min_freq = min(n["freq_mhz"] for n in clock_nets)
            period_ns = 1000 / min_freq
            skew_budget_ns = period_ns * 0.05

            if max_skew_ns > skew_budget_ns:
                issues.append(TimingViolation(
                    rule_id="CS001",
                    rule_name="Clock Skew",
                    severity="error",
                    message=f"Clock skew {max_skew_ns:.2f}ns > {skew_budget_ns:.2f}ns budget ({min_freq}MHz clock)",
                    net=", ".join(clock_lengths.keys()),
                    measured_ns=max_skew_ns,
                    required_ns=skew_budget_ns,
                    suggestion=f"Match clock trace lengths within {skew_budget_ns*1000/self.propagation_delay_ps_per_mm:.2f}mm",
                ))

        return issues

    def _check_ddr_timing(
        self,
        design_data: dict,
        critical_nets: list[dict],
    ) -> list[TimingViolation]:
        """Check DDR-specific timing requirements."""
        issues = []
        routing = design_data.get("routing", {})
        diff_pairs = routing.get("differential_pairs", [])

        ddr_nets = [n for n in critical_nets if n["type"] == "ddr"]

        for net_info in ddr_nets:
            name = net_info["name"]
            tolerance = net_info.get("length_tolerance_mm", 0.127)

            # Check DQS/DQ length matching
            if "DQS" in name.upper():
                # Find corresponding DQ nets
                dq_nets = [
                    n for n in ddr_nets
                    if "DQ" in n["name"].upper() and "DQS" not in n["name"].upper()
                ]

                for dq_net in dq_nets[:8]:  # Check first 8 DQ lines
                    dqs_tracks = [
                        t for t in design_data.get("tracks", [])
                        if t.get("net", "") == name
                    ]
                    dq_tracks = [
                        t for t in design_data.get("tracks", [])
                        if t.get("net", "") == dq_net["name"]
                    ]

                    dqs_len = sum(
                        math.sqrt((t["end"][0]-t["start"][0])**2 + (t["end"][1]-t["start"][1])**2)
                        for t in dqs_tracks
                    )
                    dq_len = sum(
                        math.sqrt((t["end"][0]-t["start"][0])**2 + (t["end"][1]-t["start"][1])**2)
                        for t in dq_tracks
                    )

                    diff = abs(dqs_len - dq_len)
                    if diff > tolerance:
                        issues.append(TimingViolation(
                            rule_id="DDR001",
                            rule_name="DDR DQS/DQ Length Match",
                            severity="error",
                            message=f"DQS '{name}' to DQ '{dq_net['name']}' mismatch: {diff:.3f}mm > {tolerance}mm",
                            net=name,
                            measured_ns=diff * self.propagation_delay_ps_per_mm / 1000,
                            required_ns=tolerance * self.propagation_delay_ps_per_mm / 1000,
                            suggestion="Match DQS and DQ trace lengths for proper data capture",
                        ))

        return issues

    def _estimate_clock_freq(self, net_name: str) -> float:
        """Estimate clock frequency from net name."""
        name = net_name.upper()
        if "DDR" in name:
            return 1600
        elif "PCIE" in name:
            return 8000
        elif "USB3" in name:
            return 5000
        elif "ETH" in name:
            return 125
        elif "SPI" in name:
            return 50
        elif "I2C" in name:
            return 3.4
        else:
            return 100  # Default assumption
