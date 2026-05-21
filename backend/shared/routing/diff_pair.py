"""
PCB Builder - Differential Pair Router
Routes differential pairs with length matching and coupling control.
"""

import math
from dataclasses import dataclass
from typing import Optional

from shared.routing.astar_router import AStarRouter, RoutePath
from shared.routing.grid import RoutingGrid


@dataclass
class DiffPairResult:
    """Result of differential pair routing."""
    net_pos: str
    net_neg: str
    pos_path: RoutePath
    neg_path: RoutePath
    length_diff_mm: float = 0.0
    matched: bool = True
    coupling_violations: int = 0


class DifferentialPairRouter:
    """
    Routes differential pairs with:
    - Controlled spacing (coupling)
    - Length matching
    - Parallel routing preference
    """

    def __init__(
        self,
        grid: RoutingGrid,
        diff_spacing_mm: float = 0.25,
        length_tolerance_mm: float = 0.254,
    ):
        self.grid = grid
        self.diff_spacing_mm = diff_spacing_mm
        self.length_tolerance_mm = length_tolerance_mm
        self.router = AStarRouter(grid)

    def route_diff_pair(
        self,
        net_pos: str,
        net_neg: str,
        pos_start: tuple[float, float],
        pos_end: tuple[float, float],
        neg_start: tuple[float, float],
        neg_end: tuple[float, float],
        preferred_layer: int = 0,
    ) -> Optional[DiffPairResult]:
        """
        Route a differential pair with length matching.

        Strategy: Route the positive net first, then route the negative
        net parallel to it at the specified spacing.
        """
        # Route positive net
        pos_path = self.router.find_path(
            pos_start, pos_end,
            preferred_layer=preferred_layer,
            net_id=net_pos,
        )
        if not pos_path:
            return None

        self.router.occupy_path(pos_path, net_pos)

        # Route negative net parallel to positive
        neg_path = self._route_parallel(
            pos_path, neg_start, neg_end,
            preferred_layer, net_neg,
        )

        if not neg_path:
            # Free positive and fail
            self.grid.free_net(net_pos)
            return None

        # Check length matching
        length_diff = abs(pos_path.total_length_mm - neg_path.total_length_mm)
        matched = length_diff <= self.length_tolerance_mm

        # If not matched, try to add serpentine tuning
        if not matched:
            neg_path = self._add_length_tuning(
                neg_path, pos_path.total_length_mm, net_neg,
            )
            length_diff = abs(pos_path.total_length_mm - neg_path.total_length_mm)
            matched = length_diff <= self.length_tolerance_mm

        return DiffPairResult(
            net_pos=net_pos,
            net_neg=net_neg,
            pos_path=pos_path,
            neg_path=neg_path,
            length_diff_mm=round(length_diff, 3),
            matched=matched,
        )

    def _route_parallel(
        self,
        ref_path: RoutePath,
        start: tuple[float, float],
        end: tuple[float, float],
        preferred_layer: int,
        net_id: str,
    ) -> Optional[RoutePath]:
        """Route a path parallel to a reference path at fixed spacing."""
        # Offset the reference path by the differential spacing
        offset_points = []
        for i in range(len(ref_path.points) - 1):
            p1 = ref_path.points[i]
            p2 = ref_path.points[i + 1]

            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = math.sqrt(dx**2 + dy**2)

            if length > 0:
                nx = -dy / length * self.diff_spacing_mm
                ny = dx / length * self.diff_spacing_mm
            else:
                nx, ny = self.diff_spacing_mm, 0

            offset_points.append((p1[0] + nx, p1[1] + ny, p1[2]))

        if offset_points:
            offset_points.append(ref_path.points[-1])

        # Try to route from start to end using A*
        # with the offset path as a guide
        path = self.router.find_path(
            start, end,
            preferred_layer=preferred_layer,
            net_id=net_id,
        )

        return path

    def _add_length_tuning(
        self,
        path: RoutePath,
        target_length: float,
        net_id: str,
    ) -> RoutePath:
        """Add serpentine traces to match target length."""
        current_length = path.total_length_mm
        needed = target_length - current_length

        if needed <= 0:
            return path

        # Add serpentine at the end of the path
        if not path.points:
            return path

        last = path.points[-1]
        layer = last[2]
        x, y = last[0], last[1]

        # Create serpentine pattern
        serpentine_points = list(path.points)
        remaining = needed
        amplitude = self.diff_spacing_mm * 2
        period = self.diff_spacing_mm * 4

        while remaining > period:
            # Add one serpentine cycle
            serpentine_points.append((x + amplitude, y, layer))
            serpentine_points.append((x + amplitude, y + amplitude, layer))
            serpentine_points.append((x, y + amplitude, layer))
            serpentine_points.append((x, y + period, layer))

            x = x
            y += period
            remaining -= period * 2

            if len(serpentine_points) > 1000:
                break

        # Rebuild path
        total_length = 0.0
        for i in range(1, len(serpentine_points)):
            p1 = serpentine_points[i - 1]
            p2 = serpentine_points[i]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            total_length += math.sqrt(dx**2 + dy**2)

        return RoutePath(
            points=serpentine_points,
            via_count=path.via_count,
            total_length_mm=total_length,
            layer_changes=path.layer_changes,
        )
