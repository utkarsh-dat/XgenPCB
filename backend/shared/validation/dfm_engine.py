"""
PCB Builder - DFM (Design for Manufacturing) Engine
Fabrication and assembly checks for production-ready boards.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from shared.validation.drc_engine import DRCViolation, RuleCategory, RuleSeverity


@dataclass
class DFMResult:
    """Complete DFM analysis report."""
    passed: bool
    score: float
    fabrication_issues: list[DRCViolation] = field(default_factory=list)
    assembly_issues: list[DRCViolation] = field(default_factory=list)
    copper_balance: dict = field(default_factory=dict)
    panelization: dict = field(default_factory=dict)
    test_point_coverage: float = 0.0
    summary: dict = field(default_factory=dict)
    manufacturer_recommendations: list[str] = field(default_factory=list)


class DFMEngine:
    """DFM analysis engine for fabrication and assembly."""

    def __init__(self, rule_set: Any = None):
        self.rule_set = rule_set
        self.issues: list[DRCViolation] = []

    def analyze(self, design_data: dict) -> DFMResult:
        """Run full DFM analysis."""
        self.issues = []

        self._check_fabrication(design_data)
        self._check_assembly(design_data)
        self._check_copper_balance(design_data)
        self._check_test_points(design_data)
        self._check_panelization(design_data)

        fab_issues = [i for i in self.issues if i.category == RuleCategory.MANUFACTURING]
        asm_issues = [i for i in self.issues if i.category == RuleCategory.COMPONENT]

        critical_count = sum(1 for i in self.issues if i.severity == RuleSeverity.CRITICAL)
        error_count = sum(1 for i in self.issues if i.severity == RuleSeverity.ERROR)

        score = 100.0 - critical_count * 20 - error_count * 10
        score = max(0.0, score)

        return DFMResult(
            passed=critical_count == 0,
            score=round(score, 2),
            fabrication_issues=fab_issues,
            assembly_issues=asm_issues,
            copper_balance=self._analyze_copper_balance(design_data),
            test_point_coverage=self._calculate_test_coverage(design_data),
            summary={
                "total_issues": len(self.issues),
                "critical": critical_count,
                "error": error_count,
                "warning": sum(1 for i in self.issues if i.severity == RuleSeverity.WARNING),
                "test_point_coverage": self._calculate_test_coverage(design_data),
            },
            manufacturer_recommendations=self._generate_recommendations(design_data),
        )

    def _check_fabrication(self, design_data: dict):
        """Fabrication checks: copper balance, slivers, acid traps."""
        tracks = design_data.get("tracks", [])
        board = design_data.get("board_config", {})
        board_w = board.get("width_mm", 100)
        board_h = board.get("height_mm", 100)
        board_area = board_w * board_h

        # Check acute angles (acid traps)
        for i, t1 in enumerate(tracks):
            for j, t2 in enumerate(tracks):
                if i >= j:
                    continue
                # Check if tracks meet at a point
                if self._tracks_meet(t1, t2):
                    angle = self._track_angle(t1, t2)
                    if angle < 90:
                        self.issues.append(DRCViolation(
                            rule_id="DF001",
                            rule_name="Acute Angle (Acid Trap)",
                            category=RuleCategory.MANUFACTURING,
                            severity=RuleSeverity.WARNING,
                            message=f"Acute angle {angle:.1f}° between traces may trap etchant",
                            location={"x": t1["end"][0], "y": t1["end"][1], "layer": t1.get("layer", "F.Cu")},
                            suggestion="Use 90° or 135° angles, or rounded corners",
                            ipc_reference="IPC-2221 Section 6.4",
                            fix_strategy="change_to_45_or_90_degree",
                        ))

        # Check copper balance
        track_area = sum(
            self._track_length(t) * t.get("width", 0.25)
            for t in tracks
        )
        copper_ratio = track_area / board_area
        if copper_ratio < 0.15 or copper_ratio > 0.85:
            self.issues.append(DRCViolation(
                rule_id="DF002",
                rule_name="Copper Balance",
                category=RuleCategory.MANUFACTURING,
                severity=RuleSeverity.WARNING,
                message=f"Copper coverage {copper_ratio*100:.1f}% outside recommended 15-85% range",
                location={"x": board_w/2, "y": board_h/2, "layer": "all"},
                measured_value=copper_ratio * 100,
                required_value=50,
                unit="%",
                suggestion="Add dummy copper pours or hatched planes for balance",
                ipc_reference="IPC-2221 Section 4.3",
                fix_strategy="add_copper_pour",
            ))

        # Check for thin copper slivers
        for track in tracks:
            width = track.get("width", 0.25)
            length = self._track_length(track)
            if width < 0.1 and length > 2.0:
                self.issues.append(DRCViolation(
                    rule_id="DF003",
                    rule_name="Copper Sliver",
                    category=RuleCategory.MANUFACTURING,
                    severity=RuleSeverity.WARNING,
                    message=f"Thin sliver {width}mm x {length}mm may lift during processing",
                    location={"x": track["start"][0], "y": track["start"][1], "layer": track.get("layer", "F.Cu")},
                    suggestion="Remove or thicken sliver, or connect to larger copper area",
                    fix_strategy="merge_or_thicken_sliver",
                ))

    def _check_assembly(self, design_data: dict):
        """Assembly checks: component spacing, test points."""
        components = design_data.get("placed_components", [])
        min_spacing = 0.5  # mm for pick-and-place

        for i, c1 in enumerate(components):
            for c2 in components[i + 1:]:
                dx = abs(c1.get("x", 0) - c2.get("x", 0))
                dy = abs(c1.get("y", 0) - c2.get("y", 0))
                dist = (dx ** 2 + dy ** 2) ** 0.5
                if dist < min_spacing:
                    self.issues.append(DRCViolation(
                        rule_id="DA001",
                        rule_name="Component Spacing (Assembly)",
                        category=RuleCategory.COMPONENT,
                        severity=RuleSeverity.ERROR,
                        message=f"Components {c1['id']} and {c2['id']} {dist:.2f}mm apart < {min_spacing}mm for assembly",
                        location={"x": c1["x"], "y": c1["y"], "layer": c1.get("layer", "F")},
                        measured_value=dist,
                        required_value=min_spacing,
                        unit="mm",
                        suggestion="Increase spacing to at least 0.5mm for pick-and-place",
                        ipc_reference="IPC-7351",
                        fix_strategy="reposition_component",
                    ))

    def _check_copper_balance(self, design_data: dict):
        """Analyze copper distribution across layers."""
        pass  # Detailed analysis done in _analyze_copper_balance

    def _analyze_copper_balance(self, design_data: dict) -> dict:
        """Calculate copper density per layer."""
        tracks = design_data.get("tracks", [])
        board = design_data.get("board_config", {})
        board_w = board.get("width_mm", 100)
        board_h = board.get("height_mm", 100)
        board_area = board_w * board_h

        layer_areas = {}
        for track in tracks:
            layer = track.get("layer", "F.Cu")
            length = self._track_length(track)
            width = track.get("width", 0.25)
            layer_areas[layer] = layer_areas.get(layer, 0) + length * width

        result = {}
        for layer, area in layer_areas.items():
            ratio = area / board_area
            result[layer] = {
                "copper_area_mm2": round(area, 2),
                "board_area_mm2": round(board_area, 2),
                "ratio": round(ratio, 3),
                "balanced": 0.15 <= ratio <= 0.85,
            }
        return result

    def _check_test_points(self, design_data: dict):
        """Check test point accessibility."""
        components = design_data.get("placed_components", [])
        test_points = [c for c in components if "test" in c.get("name", "").lower() or "tp" in c.get("id", "").lower()]
        nets = design_data.get("nets", [])

        if len(nets) > 5 and len(test_points) < len(nets) * 0.3:
            self.issues.append(DRCViolation(
                rule_id="DA002",
                rule_name="Test Point Coverage",
                category=RuleCategory.COMPONENT,
                severity=RuleSeverity.WARNING,
                message=f"Only {len(test_points)} test points for {len(nets)} nets (target: 80%)",
                location={"x": 0, "y": 0, "layer": "F.Cu"},
                suggestion="Add test points for key nets and power rails",
                fix_strategy="add_test_points",
            ))

    def _calculate_test_coverage(self, design_data: dict) -> float:
        """Calculate test point coverage percentage."""
        components = design_data.get("placed_components", [])
        nets = design_data.get("nets", [])
        test_points = [c for c in components if "test" in c.get("name", "").lower() or "tp" in c.get("id", "").lower()]
        if not nets:
            return 0.0
        return min(100.0, len(test_points) / len(nets) * 100)

    def _check_panelization(self, design_data: dict):
        """Check panelization feasibility."""
        board = design_data.get("board_config", {})
        w = board.get("width_mm", 100)
        h = board.get("height_mm", 100)

        # Check if board fits in standard panel sizes
        standard_panels = [(100, 100), (150, 100), (200, 150), (300, 200), (400, 300)]
        fits = any(w <= pw and h <= ph for pw, ph in standard_panels)

        if not fits:
            self.issues.append(DRCViolation(
                rule_id="DP001",
                rule_name="Panelization",
                category=RuleCategory.MANUFACTURING,
                severity=RuleSeverity.INFO,
                message=f"Board size {w}x{h}mm may require custom panelization",
                location={"x": w/2, "y": h/2, "layer": "all"},
                suggestion="Consider smaller board or custom quote",
                fix_strategy="optimize_board_size",
            ))

    def _generate_recommendations(self, design_data: dict) -> list[str]:
        """Generate manufacturer-specific recommendations."""
        recs = []
        board = design_data.get("board_config", {})
        layers = board.get("layers", 2)
        w = board.get("width_mm", 100)
        h = board.get("height_mm", 100)

        if layers <= 2:
            recs.append("2-layer design: Use JLCPCB Standard for lowest cost")
        elif layers <= 4:
            recs.append("4-layer design: Consider JLCPCB Standard with impedance control")
        else:
            recs.append(f"{layers}-layer design: Use JLCPCB Advanced or PCBWay")

        if w < 20 or h < 20:
            recs.append("Small board: Consider panelization for assembly efficiency")

        return recs

    def _tracks_meet(self, t1: dict, t2: dict) -> bool:
        """Check if two tracks share an endpoint."""
        pts1 = [tuple(t1.get("start", [0, 0])), tuple(t1.get("end", [0, 0]))]
        pts2 = [tuple(t2.get("start", [0, 0])), tuple(t2.get("end", [0, 0]))]
        return any(p in pts2 for p in pts1) and t1.get("layer") == t2.get("layer")

    def _track_angle(self, t1: dict, t2: dict) -> float:
        """Calculate angle between two tracks in degrees."""
        def vec(track, endpoint):
            if endpoint == "start":
                return [track["end"][0] - track["start"][0], track["end"][1] - track["start"][1]]
            return [track["start"][0] - track["end"][0], track["start"][1] - track["end"][1]]

        # Find shared endpoint
        p1s, p1e = tuple(t1["start"]), tuple(t1["end"])
        p2s, p2e = tuple(t2["start"]), tuple(t2["end"])

        v1 = None
        v2 = None
        if p1e == p2s:
            v1, v2 = vec(t1, "start"), vec(t2, "end")
        elif p1e == p2e:
            v1, v2 = vec(t1, "start"), vec(t2, "start")
        elif p1s == p2s:
            v1, v2 = vec(t1, "end"), vec(t2, "end")
        elif p1s == p2e:
            v1, v2 = vec(t1, "end"), vec(t2, "start")

        if v1 is None or v2 is None:
            return 180.0

        dot = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
        if mag1 == 0 or mag2 == 0:
            return 180.0

        cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        return math.degrees(math.acos(cos_angle))

    def _track_length(self, track: dict) -> float:
        """Calculate track segment length."""
        start = track.get("start", [0, 0])
        end = track.get("end", [0, 0])
        return math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)


def run_dfm_analysis(design_data: dict, rule_set: Any = None) -> DFMResult:
    """Convenience function to run DFM analysis."""
    engine = DFMEngine(rule_set)
    return engine.analyze(design_data)
