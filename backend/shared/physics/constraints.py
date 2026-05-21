"""
PCB Builder - Constraint Extractor
Automatically extracts physics constraints from schematic/netlist.
"""

import math
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedConstraint:
    """A single extracted constraint."""
    constraint_type: str
    target: str
    value: Any
    priority: str  # critical, high, medium, low
    source: str  # How it was detected
    description: str = ""


@dataclass
class ConstraintSet:
    """Complete set of extracted constraints."""
    drc_rules: dict = field(default_factory=dict)
    impedance_nets: list[dict] = field(default_factory=list)
    differential_pairs: list[dict] = field(default_factory=list)
    power_nets: list[dict] = field(default_factory=list)
    clock_nets: list[dict] = field(default_factory=list)
    bypass_capacitors: list[dict] = field(default_factory=list)
    length_matched_groups: list[dict] = field(default_factory=list)
    keepout_regions: list[dict] = field(default_factory=list)
    raw_constraints: list[ExtractedConstraint] = field(default_factory=list)


class ConstraintExtractor:
    """
    Extracts design constraints from schematic/netlist data.

    Automatically detects:
    - Differential pairs (by net naming convention)
    - Impedance-controlled nets (USB, PCIe, DDR, etc.)
    - Power nets with current requirements
    - Clock nets with frequency requirements
    - Bypass/decoupling capacitors
    - Length-matched bus groups
    - Keepout regions (connectors, mounting holes)
    """

    # Net naming patterns
    DIFF_PAIR_PATTERNS = [
        (r"(.+)_P$", r"(.+)_N$"),
        (r"(.+)\+?$", r"(.+)-$"),
        (r"(.+)_POS$", r"(.+)_NEG$"),
        (r"(.+)_TX_P$", r"(.+)_TX_N$"),
        (r"(.+)_RX_P$", r"(.+)_RX_N$"),
        (r"(.+)_DP$", r"(.+)_DN$"),
    ]

    IMPEDANCE_NET_PATTERNS = {
        "USB": {"impedance_ohm": 90, "type": "differential"},
        "USB_D": {"impedance_ohm": 90, "type": "differential"},
        "PCIE": {"impedance_ohm": 85, "type": "differential"},
        "DDR": {"impedance_ohm": 40, "type": "single_ended"},
        "MIPI": {"impedance_ohm": 100, "type": "differential"},
        "ETH": {"impedance_ohm": 100, "type": "differential"},
        "HDMI": {"impedance_ohm": 100, "type": "differential"},
        "SDIO": {"impedance_ohm": 50, "type": "single_ended"},
    }

    POWER_NET_NAMES = ["VCC", "VDD", "3V3", "3.3V", "5V", "1V8", "1.2V", "VBAT", "PWR", "VDDIO"]

    def extract(self, design_data: dict) -> ConstraintSet:
        """Extract all constraints from design data."""
        nets = design_data.get("nets", [])
        components = design_data.get("components", [])
        board = design_data.get("board_config", {})

        constraint_set = ConstraintSet()

        # Set default DRC rules
        constraint_set.drc_rules = self._get_default_drc_rules(board)

        # Extract specific constraints
        constraint_set.differential_pairs = self._extract_diff_pairs(nets)
        constraint_set.impedance_nets = self._extract_impedance_nets(nets)
        constraint_set.power_nets = self._extract_power_nets(nets, components)
        constraint_set.clock_nets = self._extract_clock_nets(nets)
        constraint_set.bypass_capacitors = self._extract_bypass_caps(components, nets)
        constraint_set.length_matched_groups = self._extract_length_groups(nets)
        constraint_set.keepout_regions = self._extract_keepouts(components, board)

        return constraint_set

    def _get_default_drc_rules(self, board: dict) -> dict:
        """Get default DRC rules based on board config."""
        layers = board.get("layers", 2)

        if layers <= 2:
            return {
                "min_trace_width_mm": 0.2,
                "min_clearance_mm": 0.2,
                "min_via_drill_mm": 0.3,
                "min_via_pad_mm": 0.6,
                "min_annular_ring_mm": 0.1,
                "min_board_edge_clearance_mm": 0.3,
                "min_component_clearance_mm": 0.25,
                "ipc_class": "Class 2",
            }
        elif layers <= 4:
            return {
                "min_trace_width_mm": 0.15,
                "min_clearance_mm": 0.15,
                "min_via_drill_mm": 0.25,
                "min_via_pad_mm": 0.5,
                "min_annular_ring_mm": 0.075,
                "min_board_edge_clearance_mm": 0.3,
                "min_component_clearance_mm": 0.2,
                "ipc_class": "Class 2",
            }
        else:
            return {
                "min_trace_width_mm": 0.1,
                "min_clearance_mm": 0.1,
                "min_via_drill_mm": 0.2,
                "min_via_pad_mm": 0.45,
                "min_annular_ring_mm": 0.075,
                "min_board_edge_clearance_mm": 0.5,
                "min_component_clearance_mm": 0.15,
                "ipc_class": "Class 3",
            }

    def _extract_diff_pairs(self, nets: list[dict]) -> list[dict]:
        """Extract differential pairs from net names."""
        pairs = []
        net_names = [n.get("name", "") for n in nets]

        for pos_pattern, neg_pattern in self.DIFF_PAIR_PATTERNS:
            pos_nets = [n for n in net_names if re.match(pos_pattern, n)]
            neg_nets = [n for n in net_names if re.match(neg_pattern, n)]

            for pos_net in pos_nets:
                pos_match = re.match(pos_pattern, pos_net)
                if not pos_match:
                    continue

                prefix = pos_match.group(1)

                # Find matching negative net
                for neg_net in neg_nets:
                    neg_match = re.match(neg_pattern, neg_net)
                    if neg_match and neg_match.group(1) == prefix:
                        # Determine impedance target
                        impedance = self._get_impedance_for_net(pos_net)

                        pairs.append({
                            "net_pos": pos_net,
                            "net_neg": neg_net,
                            "impedance_ohm": impedance,
                            "length_tolerance_mm": self._get_length_tolerance(pos_net),
                            "spacing_mm": 0.25,
                        })
                        break

        return pairs

    def _extract_impedance_nets(self, nets: list[dict]) -> list[dict]:
        """Extract nets requiring impedance control."""
        impedance_nets = []

        for net in nets:
            name = net.get("name", "").upper()

            for pattern, spec in self.IMPEDANCE_NET_PATTERNS.items():
                if pattern in name:
                    impedance_nets.append({
                        "net": net.get("name", ""),
                        "impedance_ohm": spec["impedance_ohm"],
                        "type": spec["type"],
                        "tolerance_pct": 10,
                    })
                    break

        return impedance_nets

    def _extract_power_nets(self, nets: list[dict], components: list[dict]) -> list[dict]:
        """Extract power nets with estimated current requirements."""
        power_nets = []

        for net in nets:
            name = net.get("name", "").upper()

            if any(p in name for p in self.POWER_NET_NAMES):
                voltage = self._get_net_voltage(name)
                current = self._estimate_net_current(net, components)

                power_nets.append({
                    "net": net.get("name", ""),
                    "voltage_v": voltage,
                    "estimated_current_a": current,
                    "min_trace_width_mm": self._calc_power_trace_width(current),
                    "priority": "critical",
                })

        return power_nets

    def _extract_clock_nets(self, nets: list[dict]) -> list[dict]:
        """Extract clock nets with frequency requirements."""
        clock_nets = []

        for net in nets:
            name = net.get("name", "").upper()

            if "CLK" in name or "CLOCK" in name:
                freq = self._estimate_clock_frequency(name)
                clock_nets.append({
                    "net": net.get("name", ""),
                    "frequency_mhz": freq,
                    "max_skew_mm": self._calc_max_skew(freq),
                    "priority": "high",
                })

        return clock_nets

    def _extract_bypass_caps(
        self,
        components: list[dict],
        nets: list[dict],
    ) -> list[dict]:
        """Extract bypass/decoupling capacitors and their target ICs."""
        bypass_caps = []

        # Find capacitors
        caps = [
            c for c in components
            if c.get("name", "").upper().startswith("C")
            and c.get("footprint", "") in ["0402", "0603", "0805"]
        ]

        # Find ICs
        ics = [
            c for c in components
            if any(k in c.get("name", "").upper() for k in ["U", "IC", "MCU", "CPU", "FPGA"])
        ]

        for cap in caps:
            # Find which IC this cap decouples by checking shared nets
            cap_id = cap.get("id", "")

            # Find nets connected to this capacitor
            cap_nets = set()
            for net in nets:
                for pin in net.get("pins", []):
                    if pin.get("component_id") == cap_id:
                        cap_nets.add(net.get("name", ""))

            # Find ICs sharing power nets with this cap
            target_ics = []
            for ic in ics:
                ic_id = ic.get("id", "")
                for net in nets:
                    net_name = net.get("name", "")
                    if any(p in net_name.upper() for p in ["VCC", "3V3", "5V", "VDD"]):
                        net_has_cap = any(
                            p.get("component_id") == cap_id for p in net.get("pins", [])
                        )
                        net_has_ic = any(
                            p.get("component_id") == ic_id for p in net.get("pins", [])
                        )
                        if net_has_cap and net_has_ic:
                            target_ics.append(ic_id)

            if target_ics:
                bypass_caps.append({
                    "capacitor_id": cap_id,
                    "target_ics": target_ics,
                    "max_distance_mm": 2.0,
                    "priority": "critical",
                })

        return bypass_caps

    def _extract_length_groups(self, nets: list[dict]) -> list[dict]:
        """Extract groups of nets that need length matching."""
        groups = []

        # DDR data bus
        ddr_data = [n for n in nets if "DDR" in n.get("name", "").upper() and "DQ" in n.get("name", "").upper()]
        if ddr_data:
            groups.append({
                "group_name": "DDR Data Bus",
                "nets": [n.get("name", "") for n in ddr_data],
                "tolerance_mm": 0.127,
                "priority": "critical",
            })

        # DDR address bus
        ddr_addr = [n for n in nets if "DDR" in n.get("name", "").upper() and "ADDR" in n.get("name", "").upper()]
        if ddr_addr:
            groups.append({
                "group_name": "DDR Address Bus",
                "nets": [n.get("name", "") for n in ddr_addr],
                "tolerance_mm": 0.508,
                "priority": "high",
            })

        return groups

    def _extract_keepouts(self, components: list[dict], board: dict) -> list[dict]:
        """Extract keepout regions from connectors and mounting holes."""
        keepouts = []

        for comp in components:
            name = comp.get("name", "").upper()
            comp_id = comp.get("id", "")
            x = comp.get("x", 0)
            y = comp.get("y", 0)

            # Connectors need edge clearance
            if any(k in name for k in ["USB", "JST", "CONN", "HEADER", "J"]):
                keepouts.append({
                    "type": "connector",
                    "component_id": comp_id,
                    "center": (x, y),
                    "radius_mm": 5.0,
                    "description": f"Connector {comp_id} keepout",
                })

            # Mounting holes
            if "MH" in comp_id or "MOUNT" in name:
                keepouts.append({
                    "type": "mounting_hole",
                    "component_id": comp_id,
                    "center": (x, y),
                    "radius_mm": 3.0,
                    "description": f"Mounting hole {comp_id} keepout",
                })

            # Crystals need isolation
            if "Y" in comp_id or "XTAL" in name or "CRYSTAL" in name:
                keepouts.append({
                    "type": "crystal",
                    "component_id": comp_id,
                    "center": (x, y),
                    "radius_mm": 3.0,
                    "description": f"Crystal {comp_id} isolation zone",
                })

        return keepouts

    def _get_impedance_for_net(self, net_name: str) -> float:
        """Get target impedance for a net."""
        name = net_name.upper()
        if "USB" in name:
            return 90
        elif "PCIE" in name:
            return 85
        elif "ETH" in name:
            return 100
        elif "MIPI" in name:
            return 100
        elif "HDMI" in name:
            return 100
        return 50

    def _get_length_tolerance(self, net_name: str) -> float:
        """Get length matching tolerance for a net."""
        name = net_name.upper()
        if "USB3" in name or "PCIE" in name:
            return 0.127  # 5mil
        elif "MIPI" in name:
            return 0.127
        elif "USB" in name:
            return 0.254  # 10mil
        return 0.254

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
        elif "2V5" in net or "2.5" in net:
            return 2.5
        return 3.3

    def _estimate_net_current(self, net: dict, components: list[dict]) -> float:
        """Estimate current for a power net."""
        net_name = net.get("name", "").upper()
        total_current = 0.0

        for comp in components:
            # Check if component is connected to this net
            connected = False
            for pin in net.get("pins", []):
                if pin.get("component_id") == comp.get("id"):
                    connected = True
                    break

            if not connected:
                continue

            name = comp.get("name", "").upper()

            # Current estimates by component type
            if any(k in name for k in ["ESP32"]):
                total_current += 0.25
            elif any(k in name for k in ["STM32"]):
                total_current += 0.15
            elif any(k in name for k in ["FPGA"]):
                total_current += 1.0
            elif any(k in name for k in ["LED"]):
                total_current += 0.02
            elif any(k in name for k in ["USB"]):
                total_current += 0.5

        return max(total_current, 0.05)

    def _calc_power_trace_width(self, current_a: float) -> float:
        """Calculate minimum trace width for power net (IPC-2152)."""
        # I = 0.048 * A^0.725 for 10C rise (external layer)
        area_mil2 = (current_a / 0.048) ** (1 / 0.725)
        area_m2 = area_mil2 * (25.4 / 1000) ** 2
        thickness_m = 35e-6  # 1oz copper
        width_m = area_m2 / thickness_m
        return max(width_m * 1000, 0.3)  # Minimum 0.3mm

    def _estimate_clock_frequency(self, net_name: str) -> float:
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
        return 100

    def _calc_max_skew(self, freq_mhz: float) -> float:
        """Calculate maximum clock skew (5% of period)."""
        period_ns = 1000 / freq_mhz
        skew_ns = period_ns * 0.05
        # Convert to mm (propagation delay ~150ps/mm for FR4)
        return skew_ns * 1000 / 150
