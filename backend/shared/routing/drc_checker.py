"""
PCB Builder - Routing DRC Checker
Validates routed traces against design rules during and after routing.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RoutingDRCViolation:
    """A DRC violation found in routed traces."""
    rule_id: str
    rule_name: str
    severity: str  # critical, error, warning
    message: str
    net: str = ""
    location: tuple[float, float] = (0.0, 0.0)
    measured_value: float = 0.0
    required_value: float = 0.0
    unit: str = "mm"


class RoutingDRCChecker:
    """
    Checks routed traces against DRC rules.

    Runs incrementally during routing and as a final validation.
    """

    def __init__(
        self,
        min_trace_width: float = 0.15,
        min_clearance: float = 0.15,
        min_via_drill: float = 0.3,
        min_via_pad: float = 0.6,
        min_annular_ring: float = 0.05,
        max_aspect_ratio: float = 10.0,
        board_thickness: float = 1.6,
    ):
        self.min_trace_width = min_trace_width
        self.min_clearance = min_clearance
        self.min_via_drill = min_via_drill
        self.min_via_pad = min_via_pad
        self.min_annular_ring = min_annular_ring
        self.max_aspect_ratio = max_aspect_ratio
        self.board_thickness = board_thickness
        self.violations: list[RoutingDRCViolation] = []

    def check_tracks(self, tracks: list[dict]) -> list[RoutingDRCViolation]:
        """Run all DRC checks on a list of tracks."""
        self.violations = []

        self._check_trace_width(tracks)
        self._check_trace_clearance(tracks)
        self._check_board_edge(tracks)

        return self.violations

    def check_vias(self, vias: list[dict]) -> list[RoutingDRCViolation]:
        """Run all DRC checks on vias."""
        self._check_via_drill(vias)
        self._check_annular_ring(vias)
        self._check_via_spacing(vias)

        return self.violations

    def check_diff_pair(
        self,
        pos_tracks: list[dict],
        neg_tracks: list[dict],
        max_length_diff: float = 0.254,
    ) -> list[RoutingDRCViolation]:
        """Check differential pair constraints."""
        pos_length = sum(self._track_length(t) for t in pos_tracks)
        neg_length = sum(self._track_length(t) for t in neg_tracks)
        diff = abs(pos_length - neg_length)

        if diff > max_length_diff:
            self.violations.append(RoutingDRCViolation(
                rule_id="DP001",
                rule_name="Differential Pair Length Match",
                severity="error",
                message=f"Length mismatch: {diff:.3f}mm > {max_length_diff}mm",
                measured_value=diff,
                required_value=max_length_diff,
                unit="mm",
            ))

        # Check spacing between pairs
        for pt in pos_tracks:
            for nt in neg_tracks:
                dist = self._track_to_track_distance(pt, nt)
                if dist < self.min_clearance * 2:
                    self.violations.append(RoutingDRCViolation(
                        rule_id="DP002",
                        rule_name="Differential Pair Spacing",
                        severity="warning",
                        message=f"Pair spacing {dist:.3f}mm may be too tight",
                        measured_value=dist,
                        required_value=self.min_clearance * 2,
                        unit="mm",
                    ))

        return self.violations

    def _check_trace_width(self, tracks: list[dict]):
        """Check all traces meet minimum width."""
        for track in tracks:
            width = track.get("width", 0.25)
            net = track.get("net", "")

            # Power nets need wider traces
            is_power = any(
                p in net.upper()
                for p in ["VCC", "3V3", "5V", "VDD", "VBAT", "PWR"]
            )
            min_width = 0.3 if is_power else self.min_trace_width

            if width < min_width:
                self.violations.append(RoutingDRCViolation(
                    rule_id="RW001",
                    rule_name="Minimum Trace Width",
                    severity="error",
                    message=f"Trace '{net}' width {width}mm < {min_width}mm",
                    net=net,
                    location=(track.get("start", [0, 0])[0], track.get("start", [0, 0])[1]),
                    measured_value=width,
                    required_value=min_width,
                    unit="mm",
                ))

    def _check_trace_clearance(self, tracks: list[dict]):
        """Check clearance between traces on same layer."""
        for i, t1 in enumerate(tracks):
            for t2 in tracks[i + 1:]:
                if t1.get("net") == t2.get("net"):
                    continue
                if t1.get("layer") != t2.get("layer"):
                    continue

                dist = self._track_to_track_distance(t1, t2)
                if dist < self.min_clearance and dist >= 0:
                    self.violations.append(RoutingDRCViolation(
                        rule_id="RC001",
                        rule_name="Trace Clearance",
                        severity="critical",
                        message=f"Clearance {dist:.3f}mm between '{t1.get('net')}' and '{t2.get('net')}'",
                        net=t1.get("net", ""),
                        location=(t1.get("start", [0, 0])[0], t1.get("start", [0, 0])[1]),
                        measured_value=dist,
                        required_value=self.min_clearance,
                        unit="mm",
                    ))

    def _check_board_edge(self, tracks: list[dict]):
        """Check traces don't go outside board edge."""
        for track in tracks:
            for pt_name in ["start", "end"]:
                pt = track.get(pt_name, [0, 0])
                if pt[0] < 0 or pt[1] < 0:
                    self.violations.append(RoutingDRCViolation(
                        rule_id="BE001",
                        rule_name="Board Edge",
                        severity="error",
                        message=f"Track endpoint at ({pt[0]}, {pt[1]}) outside board",
                        net=track.get("net", ""),
                        location=(pt[0], pt[1]),
                    ))

    def _check_via_drill(self, vias: list[dict]):
        """Check via drill sizes."""
        for via in vias:
            drill = via.get("drill", 0.3)
            if drill < self.min_via_drill:
                self.violations.append(RoutingDRCViolation(
                    rule_id="VD001",
                    rule_name="Minimum Via Drill",
                    severity="error",
                    message=f"Via drill {drill}mm < {self.min_via_drill}mm",
                    location=(via.get("x", 0), via.get("y", 0)),
                    measured_value=drill,
                    required_value=self.min_via_drill,
                    unit="mm",
                ))

    def _check_annular_ring(self, vias: list[dict]):
        """Check annular ring on vias."""
        for via in vias:
            diameter = via.get("diameter", 0.6)
            drill = via.get("drill", 0.3)
            annular = (diameter - drill) / 2

            if annular < self.min_annular_ring:
                self.violations.append(RoutingDRCViolation(
                    rule_id="AR001",
                    rule_name="Minimum Annular Ring",
                    severity="error",
                    message=f"Annular ring {annular:.3f}mm < {self.min_annular_ring}mm",
                    location=(via.get("x", 0), via.get("y", 0)),
                    measured_value=annular,
                    required_value=self.min_annular_ring,
                    unit="mm",
                ))

            # Aspect ratio
            if drill > 0:
                aspect = self.board_thickness / drill
                if aspect > self.max_aspect_ratio:
                    self.violations.append(RoutingDRCViolation(
                        rule_id="AR002",
                        rule_name="Via Aspect Ratio",
                        severity="warning",
                        message=f"Aspect ratio {aspect:.1f}:1 > {self.max_aspect_ratio}:1",
                        location=(via.get("x", 0), via.get("y", 0)),
                        measured_value=aspect,
                        required_value=self.max_aspect_ratio,
                        unit=":1",
                    ))

    def _check_via_spacing(self, vias: list[dict]):
        """Check spacing between vias."""
        for i, v1 in enumerate(vias):
            for v2 in vias[i + 1:]:
                dx = v1.get("x", 0) - v2.get("x", 0)
                dy = v1.get("y", 0) - v2.get("y", 0)
                dist = math.sqrt(dx**2 + dy**2)

                min_spacing = max(v1.get("diameter", 0.6), v2.get("diameter", 0.6))
                if dist < min_spacing:
                    self.violations.append(RoutingDRCViolation(
                        rule_id="VS001",
                        rule_name="Via Spacing",
                        severity="error",
                        message=f"Vias too close: {dist:.3f}mm",
                        location=(v1.get("x", 0), v1.get("y", 0)),
                        measured_value=dist,
                        required_value=min_spacing,
                        unit="mm",
                    ))

    def _track_length(self, track: dict) -> float:
        """Calculate track length."""
        start = track.get("start", [0, 0])
        end = track.get("end", [0, 0])
        return math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)

    def _track_to_track_distance(self, t1: dict, t2: dict) -> float:
        """Calculate minimum distance between two track segments."""
        a1 = t1.get("start", [0, 0])
        a2 = t1.get("end", [0, 0])
        b1 = t2.get("start", [0, 0])
        b2 = t2.get("end", [0, 0])

        def dot(u, v):
            return u[0]*v[0] + u[1]*v[1]

        def sub(u, v):
            return [u[0]-v[0], u[1]-v[1]]

        def d2(u):
            return dot(u, u)

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
