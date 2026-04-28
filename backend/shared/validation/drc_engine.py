"""
PCB Builder - Physics-Aware DRC Engine
Comprehensive design rule checking based on IPC standards and manufacturer capabilities.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RuleSeverity(Enum):
    CRITICAL = "critical"   # Must fix - board will fail
    ERROR = "error"         # Should fix - manufacturing risk
    WARNING = "warning"     # Advisory - may affect quality
    INFO = "info"           # Informational


class RuleCategory(Enum):
    ELECTRICAL = "electrical"
    MANUFACTURING = "manufacturing"
    COMPONENT = "component"
    HIGH_SPEED = "high_speed"
    THERMAL = "thermal"
    DFM = "dfm"


@dataclass
class DRCViolation:
    """A single DRC violation with physics-aware details."""
    rule_id: str
    rule_name: str
    category: RuleCategory
    severity: RuleSeverity
    message: str
    location: dict  # {"x": float, "y": float, "layer": str}
    affected_nets: list[str] = field(default_factory=list)
    measured_value: Optional[float] = None
    required_value: Optional[float] = None
    unit: str = "mm"
    suggestion: str = ""
    ipc_reference: str = ""  # e.g., "IPC-2221 Section 4.2"
    fix_strategy: str = ""  # How to auto-fix


@dataclass
class DRCResult:
    """Complete DRC report."""
    passed: bool
    score: float  # 0.0 - 100.0
    violations: list[DRCViolation] = field(default_factory=list)
    by_category: dict[str, list[DRCViolation]] = field(default_factory=dict)
    by_severity: dict[str, list[DRCViolation]] = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    ipc_compliance: dict = field(default_factory=dict)  # Per-standard scores


class DRCRuleSet:
    """Base class for DRC rule sets."""

    def __init__(self, name: str, description: str, rules: dict[str, Any]):
        self.name = name
        self.description = description
        self.rules = rules

    def get(self, key: str, default: Any = None) -> Any:
        return self.rules.get(key, default)


# Pre-configured IPC rule sets
IPC_CLASS_1_RULES = DRCRuleSet(
    name="IPC-2221 Class 1",
    description="General electronic products (consumer, toys)",
    rules={
        "min_trace_width_mm": 0.15,
        "min_trace_spacing_mm": 0.15,
        "min_via_drill_mm": 0.3,
        "min_via_pad_mm": 0.6,
        "min_annular_ring_mm": 0.05,
        "min_board_edge_clearance_mm": 0.25,
        "min_component_clearance_mm": 0.2,
        "min_silkscreen_clearance_mm": 0.15,
        "max_aspect_ratio": 8.0,
        "min_solder_mask_dam_mm": 0.1,
        "ipc_class": "Class 1",
    },
)

IPC_CLASS_2_RULES = DRCRuleSet(
    name="IPC-2221 Class 2",
    description="Dedicated service electronic products (industrial, instruments)",
    rules={
        "min_trace_width_mm": 0.127,
        "min_trace_spacing_mm": 0.127,
        "min_via_drill_mm": 0.25,
        "min_via_pad_mm": 0.5,
        "min_annular_ring_mm": 0.05,
        "min_board_edge_clearance_mm": 0.3,
        "min_component_clearance_mm": 0.25,
        "min_silkscreen_clearance_mm": 0.15,
        "max_aspect_ratio": 10.0,
        "min_solder_mask_dam_mm": 0.1,
        "ipc_class": "Class 2",
    },
)

IPC_CLASS_3_RULES = DRCRuleSet(
    name="IPC-2221 Class 3",
    description="High performance/harsh environment (medical, aerospace)",
    rules={
        "min_trace_width_mm": 0.1,
        "min_trace_spacing_mm": 0.1,
        "min_via_drill_mm": 0.2,
        "min_via_pad_mm": 0.45,
        "min_annular_ring_mm": 0.075,
        "min_board_edge_clearance_mm": 0.5,
        "min_component_clearance_mm": 0.3,
        "min_silkscreen_clearance_mm": 0.2,
        "max_aspect_ratio": 12.0,
        "min_solder_mask_dam_mm": 0.15,
        "ipc_class": "Class 3",
    },
)

# Manufacturer rule sets
JLCPCB_STANDARD_RULES = DRCRuleSet(
    name="JLCPCB Standard",
    description="JLCPCB standard capabilities (5/5mil, 0.3mm drill, 4 layers)",
    rules={
        "min_trace_width_mm": 0.127,  # 5mil
        "min_trace_spacing_mm": 0.127,
        "min_via_drill_mm": 0.3,
        "min_via_pad_mm": 0.6,
        "min_annular_ring_mm": 0.15,
        "min_board_edge_clearance_mm": 0.3,
        "min_component_clearance_mm": 0.2,
        "min_hole_to_hole_mm": 0.5,
        "max_board_size_mm": 500,
        "max_layers": 4,
        "min_silkscreen_width_mm": 0.15,
        "min_silkscreen_height_mm": 0.8,
        "controlled_impedance": True,
        "blind_buried_vias": False,
        "max_aspect_ratio": 8.0,
    },
)

JLCPCB_ADVANCED_RULES = DRCRuleSet(
    name="JLCPCB Advanced",
    description="JLCPCB advanced capabilities (3.5/3.5mil, 0.2mm drill, 8 layers)",
    rules={
        "min_trace_width_mm": 0.09,
        "min_trace_spacing_mm": 0.09,
        "min_via_drill_mm": 0.2,
        "min_via_pad_mm": 0.4,
        "min_annular_ring_mm": 0.1,
        "min_board_edge_clearance_mm": 0.25,
        "min_component_clearance_mm": 0.15,
        "min_hole_to_hole_mm": 0.25,
        "max_board_size_mm": 500,
        "max_layers": 8,
        "min_silkscreen_width_mm": 0.12,
        "min_silkscreen_height_mm": 0.6,
        "controlled_impedance": True,
        "blind_buried_vias": True,
        "max_aspect_ratio": 12.0,
    },
)

PCBWAY_STANDARD_RULES = DRCRuleSet(
    name="PCBWay Standard",
    description="PCBWay standard capabilities",
    rules={
        "min_trace_width_mm": 0.127,
        "min_trace_spacing_mm": 0.127,
        "min_via_drill_mm": 0.2,
        "min_via_pad_mm": 0.5,
        "min_annular_ring_mm": 0.1,
        "min_board_edge_clearance_mm": 0.3,
        "min_component_clearance_mm": 0.2,
        "max_board_size_mm": 600,
        "max_layers": 14,
        "max_aspect_ratio": 8.0,
    },
)

MANUFACTURER_RULES = {
    "jlcpcb_standard": JLCPCB_STANDARD_RULES,
    "jlcpcb_advanced": JLCPCB_ADVANCED_RULES,
    "pcbway_standard": PCBWAY_STANDARD_RULES,
    "ipc_class_1": IPC_CLASS_1_RULES,
    "ipc_class_2": IPC_CLASS_2_RULES,
    "ipc_class_3": IPC_CLASS_3_RULES,
}


def get_rule_set(name: str) -> DRCRuleSet:
    """Get a pre-configured rule set by name."""
    if name.lower() in MANUFACTURER_RULES:
        return MANUFACTURER_RULES[name.lower()]
    # Default to IPC Class 2
    return IPC_CLASS_2_RULES


class PhysicsAwareDRC:
    """Production-grade DRC engine with physics-aware validation."""

    def __init__(self, rule_set: DRCRuleSet | None = None):
        self.rule_set = rule_set or IPC_CLASS_2_RULES
        self.violations: list[DRCViolation] = []

    def run_full_check(self, design_data: dict) -> DRCResult:
        """Run complete DRC suite."""
        self.violations = []

        self._check_electrical_rules(design_data)
        self._check_manufacturing_rules(design_data)
        self._check_component_rules(design_data)
        self._check_board_edge_rules(design_data)
        self._check_high_speed_rules(design_data)

        # Categorize
        by_category = {}
        by_severity = {}
        for v in self.violations:
            cat = v.category.value
            sev = v.severity.value
            by_category.setdefault(cat, []).append(v)
            by_severity.setdefault(sev, []).append(v)

        critical_count = len(by_severity.get("critical", []))
        error_count = len(by_severity.get("error", []))
        warning_count = len(by_severity.get("warning", []))

        # Score calculation
        score = 100.0
        score -= critical_count * 25
        score -= error_count * 10
        score -= warning_count * 2
        score = max(0.0, score)

        # IPC compliance
        ipc_compliance = {
            "ipc_2221": score,
            "ipc_7351": 100.0 if not any(v.ipc_reference.startswith("IPC-7351") for v in self.violations) else max(0.0, 100 - error_count * 5),
        }

        return DRCResult(
            passed=critical_count == 0 and error_count == 0,
            score=round(score, 2),
            violations=self.violations,
            by_category=by_category,
            by_severity=by_severity,
            summary={
                "total_violations": len(self.violations),
                "critical": critical_count,
                "error": error_count,
                "warning": warning_count,
                "info": len(by_severity.get("info", [])),
                "rule_set": self.rule_set.name,
            },
            ipc_compliance=ipc_compliance,
        )

    def _check_electrical_rules(self, design_data: dict):
        """Check electrical rules: clearance, width, shorts."""
        tracks = design_data.get("tracks", [])
        components = design_data.get("placed_components", [])
        vias = design_data.get("vias", [])
        min_trace = self.rule_set.get("min_trace_width_mm", 0.15)
        min_clearance = self.rule_set.get("min_trace_spacing_mm", 0.15)
        min_via_drill = self.rule_set.get("min_via_drill_mm", 0.3)

        # Trace width check
        for track in tracks:
            width = track.get("width", 0.25)
            net = track.get("net", "")
            if width < min_trace:
                is_power = any(p in net.upper() for p in ["VCC", "3V3", "5V", "VDD", "VBAT", "PWR"])
                self.violations.append(DRCViolation(
                    rule_id="E001",
                    rule_name="Minimum Trace Width",
                    category=RuleCategory.ELECTRICAL,
                    severity=RuleSeverity.ERROR,
                    message=f"Trace '{net}' width {width}mm < minimum {min_trace}mm",
                    location={"x": track.get("start", [0, 0])[0], "y": track.get("start", [0, 0])[1], "layer": track.get("layer", "F.Cu")},
                    affected_nets=[net],
                    measured_value=width,
                    required_value=min_trace,
                    unit="mm",
                    suggestion=f"Increase trace width to {min_trace}mm or wider",
                    ipc_reference="IPC-2221 Section 6.2",
                    fix_strategy="widen_trace",
                ))

        # Trace-to-trace clearance
        for i, t1 in enumerate(tracks):
            for t2 in tracks[i + 1:]:
                if t1.get("net") == t2.get("net"):
                    continue
                dist = self._segment_distance(
                    t1.get("start", [0, 0]), t1.get("end", [0, 0]),
                    t2.get("start", [0, 0]), t2.get("end", [0, 0]),
                )
                if dist < min_clearance and dist >= 0:
                    self.violations.append(DRCViolation(
                        rule_id="E002",
                        rule_name="Trace Clearance",
                        category=RuleCategory.ELECTRICAL,
                        severity=RuleSeverity.CRITICAL,
                        message=f"Clearance {dist:.3f}mm between '{t1.get('net')}' and '{t2.get('net')}' < {min_clearance}mm",
                        location={"x": (t1["start"][0] + t1["end"][0]) / 2, "y": (t1["start"][1] + t1["end"][1]) / 2, "layer": t1.get("layer", "F.Cu")},
                        affected_nets=[t1.get("net", ""), t2.get("net", "")],
                        measured_value=dist,
                        required_value=min_clearance,
                        unit="mm",
                        suggestion="Increase spacing or reroute traces",
                        ipc_reference="IPC-2221 Section 6.3",
                        fix_strategy="reroute_or_increase_spacing",
                    ))

        # Via checks
        for via in vias:
            drill = via.get("drill", 0.3)
            if drill < min_via_drill:
                self.violations.append(DRCViolation(
                    rule_id="E003",
                    rule_name="Minimum Via Drill",
                    category=RuleCategory.ELECTRICAL,
                    severity=RuleSeverity.ERROR,
                    message=f"Via drill {drill}mm < minimum {min_via_drill}mm",
                    location={"x": via.get("x", 0), "y": via.get("y", 0), "layer": "all"},
                    measured_value=drill,
                    required_value=min_via_drill,
                    unit="mm",
                    suggestion=f"Increase via drill to {min_via_drill}mm",
                    ipc_reference="IPC-2221 Section 9.2",
                    fix_strategy="increase_via_size",
                ))

    def _check_manufacturing_rules(self, design_data: dict):
        """Check manufacturing rules: annular ring, aspect ratio."""
        vias = design_data.get("vias", [])
        board_thickness = design_data.get("board_config", {}).get("thickness_mm", 1.6)
        min_annular = self.rule_set.get("min_annular_ring_mm", 0.05)
        max_aspect = self.rule_set.get("max_aspect_ratio", 10.0)

        for via in vias:
            diameter = via.get("diameter", 0.6)
            drill = via.get("drill", 0.3)
            annular = (diameter - drill) / 2

            if annular < min_annular:
                self.violations.append(DRCViolation(
                    rule_id="M001",
                    rule_name="Minimum Annular Ring",
                    category=RuleCategory.MANUFACTURING,
                    severity=RuleSeverity.ERROR,
                    message=f"Annular ring {annular:.3f}mm < minimum {min_annular}mm",
                    location={"x": via.get("x", 0), "y": via.get("y", 0), "layer": "all"},
                    measured_value=annular,
                    required_value=min_annular,
                    unit="mm",
                    suggestion=f"Increase pad diameter or decrease drill size",
                    ipc_reference="IPC-2221 Section 9.3",
                    fix_strategy="increase_pad_size",
                ))

            # Aspect ratio
            if drill > 0:
                aspect = board_thickness / drill
                if aspect > max_aspect:
                    self.violations.append(DRCViolation(
                        rule_id="M002",
                        rule_name="Via Aspect Ratio",
                        category=RuleCategory.MANUFACTURING,
                        severity=RuleSeverity.WARNING,
                        message=f"Aspect ratio {aspect:.1f}:1 > maximum {max_aspect}:1",
                        location={"x": via.get("x", 0), "y": via.get("y", 0), "layer": "all"},
                        measured_value=aspect,
                        required_value=max_aspect,
                        unit=":1",
                        suggestion="Use larger drill or thinner board",
                        ipc_reference="IPC-6012",
                        fix_strategy="increase_drill_or_reduce_thickness",
                    ))

    def _check_component_rules(self, design_data: dict):
        """Check component spacing and orientation."""
        components = design_data.get("placed_components", [])
        min_comp_clearance = self.rule_set.get("min_component_clearance_mm", 0.25)

        for i, c1 in enumerate(components):
            for c2 in components[i + 1:]:
                dx = abs(c1.get("x", 0) - c2.get("x", 0))
                dy = abs(c1.get("y", 0) - c2.get("y", 0))
                dist = (dx ** 2 + dy ** 2) ** 0.5
                if dist < min_comp_clearance:
                    self.violations.append(DRCViolation(
                        rule_id="C001",
                        rule_name="Component Clearance",
                        category=RuleCategory.COMPONENT,
                        severity=RuleSeverity.ERROR,
                        message=f"Components {c1.get('id')} and {c2.get('id')} are {dist:.2f}mm apart (min {min_comp_clearance}mm)",
                        location={"x": c1.get("x", 0), "y": c1.get("y", 0), "layer": c1.get("layer", "F")},
                        affected_nets=[],
                        measured_value=dist,
                        required_value=min_comp_clearance,
                        unit="mm",
                        suggestion="Increase component spacing",
                        ipc_reference="IPC-7351",
                        fix_strategy="reposition_component",
                    ))

    def _check_board_edge_rules(self, design_data: dict):
        """Check copper clearance from board edge."""
        board = design_data.get("board_config", {})
        tracks = design_data.get("tracks", [])
        components = design_data.get("placed_components", [])
        board_w = board.get("width_mm", 100)
        board_h = board.get("height_mm", 100)
        min_edge = self.rule_set.get("min_board_edge_clearance_mm", 0.3)

        for track in tracks:
            for pt in [track.get("start", [0, 0]), track.get("end", [0, 0])]:
                if pt[0] < min_edge or pt[0] > board_w - min_edge or pt[1] < min_edge or pt[1] > board_h - min_edge:
                    self.violations.append(DRCViolation(
                        rule_id="B001",
                        rule_name="Board Edge Clearance",
                        category=RuleCategory.MANUFACTURING,
                        severity=RuleSeverity.ERROR,
                        message=f"Trace too close to board edge at ({pt[0]:.2f}, {pt[1]:.2f})",
                        location={"x": pt[0], "y": pt[1], "layer": track.get("layer", "F.Cu")},
                        measured_value=min(pt[0], board_w - pt[0], pt[1], board_h - pt[1]),
                        required_value=min_edge,
                        unit="mm",
                        suggestion=f"Keep traces {min_edge}mm from board edge",
                        ipc_reference="IPC-2221 Section 4.5",
                        fix_strategy="reroute_inward",
                    ))

        for comp in components:
            x, y = comp.get("x", 0), comp.get("y", 0)
            if x < min_edge or x > board_w - min_edge or y < min_edge or y > board_h - min_edge:
                self.violations.append(DRCViolation(
                    rule_id="B002",
                    rule_name="Component Edge Clearance",
                    category=RuleCategory.COMPONENT,
                    severity=RuleSeverity.WARNING,
                    message=f"Component {comp.get('id')} near board edge",
                    location={"x": x, "y": y, "layer": comp.get("layer", "F")},
                    suggestion="Move component inward",
                    ipc_reference="IPC-2221 Section 4.5",
                    fix_strategy="reposition_component",
                ))

    def _check_high_speed_rules(self, design_data: dict):
        """Check high-speed signal integrity rules."""
        routing = design_data.get("routing", {})
        diff_pairs = routing.get("differential_pairs", [])
        tracks = design_data.get("tracks", [])

        for pair in diff_pairs:
            if not pair.get("matched", False):
                self.violations.append(DRCViolation(
                    rule_id="HS001",
                    rule_name="Differential Pair Length Match",
                    category=RuleCategory.HIGH_SPEED,
                    severity=RuleSeverity.WARNING,
                    message=f"Differential pair {pair.get('net_pos')}/{pair.get('net_neg')} not length matched",
                    location={"x": 0, "y": 0, "layer": "F.Cu"},
                    affected_nets=[pair.get("net_pos", ""), pair.get("net_neg", "")],
                    suggestion="Add serpentine tuning to match lengths",
                    ipc_reference="IPC-2141A",
                    fix_strategy="add_length_matching",
                ))

            length_diff = pair.get("length_diff_mm", 0)
            if length_diff and length_diff > 0.254:  # 10mil
                self.violations.append(DRCViolation(
                    rule_id="HS002",
                    rule_name="Differential Pair Length Tolerance",
                    category=RuleCategory.HIGH_SPEED,
                    severity=RuleSeverity.ERROR,
                    message=f"Length mismatch {length_diff:.3f}mm > 0.254mm tolerance",
                    location={"x": 0, "y": 0, "layer": "F.Cu"},
                    measured_value=length_diff,
                    required_value=0.254,
                    unit="mm",
                    suggestion="Tighten length matching",
                    ipc_reference="IPC-2141A Section 4.2",
                    fix_strategy="adjust_serpentine",
                ))

    def _segment_distance(self, a1, a2, b1, b2) -> float:
        """Calculate minimum distance between two line segments."""
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
            # Parallel
            return math.sqrt(d2(sub(a1, b1)))

        sc = (b * e - c * d) / D
        tc = (a * e - b * d) / D

        sc = max(0.0, min(1.0, sc))
        tc = max(0.0, min(1.0, tc))

        p1 = [a1[0] + sc * u[0], a1[1] + sc * u[1]]
        p2 = [b1[0] + tc * v[0], b1[1] + tc * v[1]]
        return math.sqrt(d2(sub(p1, p2)))


def run_physics_drc(design_data: dict, rule_set_name: str = "ipc_class_2") -> DRCResult:
    """Convenience function to run physics-aware DRC."""
    rule_set = get_rule_set(rule_set_name)
    engine = PhysicsAwareDRC(rule_set)
    return engine.run_full_check(design_data)
