"""
PCB Builder - A* Pathfinding Router
Core routing algorithm with DRC-aware cost functions.
"""

import heapq
import math
from dataclasses import dataclass, field
from typing import Optional

from shared.routing.grid import RoutingGrid


@dataclass
class RoutePath:
    """A completed route path."""
    points: list[tuple[float, float, int]]  # (x_mm, y_mm, layer)
    via_count: int = 0
    total_length_mm: float = 0.0
    layer_changes: list[int] = field(default_factory=list)


class AStarRouter:
    """
    A* pathfinding router for PCB traces.

    Uses a multi-layer grid with DRC-aware cost functions including:
    - Manhattan distance heuristic
    - Via penalty
    - Layer preference (signal layers vs power planes)
    - Obstacle avoidance
    - 45-degree angle preference
    """

    def __init__(
        self,
        grid: RoutingGrid,
        via_cost: float = 5.0,
        layer_change_penalty: float = 2.0,
        angle_preference: float = 0.5,
    ):
        self.grid = grid
        self.via_cost = via_cost
        self.layer_change_penalty = layer_change_penalty
        self.angle_preference = angle_preference

    def find_path(
        self,
        start_mm: tuple[float, float],
        end_mm: tuple[float, float],
        preferred_layer: int = 0,
        net_id: str = "",
    ) -> Optional[RoutePath]:
        """
        Find optimal path between two points using A*.

        Args:
            start_mm: Start position (x, y) in mm
            end_mm: End position (x, y) in mm
            preferred_layer: Preferred routing layer
            net_id: Net identifier for tracking

        Returns:
            RoutePath if found, None if no path exists
        """
        sx, sy = self.grid.mm_to_grid(start_mm[0], start_mm[1])
        ex, ey = self.grid.mm_to_grid(end_mm[0], end_mm[1])

        # Try preferred layer first, then all layers
        start_layers = [preferred_layer]
        for l in range(self.grid.num_layers):
            if l != preferred_layer:
                start_layers.append(l)

        best_path = None
        best_cost = float("inf")

        for start_layer in start_layers:
            if not self.grid.is_valid(sx, sy, start_layer):
                continue
            if self.grid.get_cell(sx, sy, start_layer).is_occupied:
                continue

            path = self._astar(sx, sy, start_layer, ex, ey, preferred_layer)
            if path:
                cost = self._evaluate_path(path, preferred_layer)
                if cost < best_cost:
                    best_cost = cost
                    best_path = path

        if not best_path:
            return None

        # Convert grid coords to mm
        mm_points = []
        for gx, gy, layer in best_path:
            x_mm, y_mm = self.grid.grid_to_mm(gx, gy)
            mm_points.append((x_mm, y_mm, layer))

        # Calculate metrics
        via_count = 0
        total_length = 0.0
        layer_changes = []
        for i in range(1, len(mm_points)):
            p1 = mm_points[i - 1]
            p2 = mm_points[i]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            total_length += math.sqrt(dx**2 + dy**2)
            if p1[2] != p2[2]:
                via_count += 1
                layer_changes.append(i)

        return RoutePath(
            points=mm_points,
            via_count=via_count,
            total_length_mm=total_length,
            layer_changes=layer_changes,
        )

    def _astar(
        self,
        sx: int,
        sy: int,
        start_layer: int,
        ex: int,
        ey: int,
        preferred_layer: int,
    ) -> Optional[list[tuple[int, int, int]]]:
        """Core A* algorithm."""
        # Priority queue: (f_score, counter, gx, gy, layer)
        counter = 0
        open_set: list[tuple[float, int, int, int, int]] = []
        heapq.heappush(open_set, (0, counter, sx, sy, start_layer))

        came_from: dict[tuple[int, int, int], tuple[int, int, int]] = {}
        g_score: dict[tuple[int, int, int], float] = {}
        g_score[(sx, sy, start_layer)] = 0

        closed_set: set[tuple[int, int, int]] = set()

        while open_set:
            _, _, cx, cy, clayer = heapq.heappop(open_set)
            current = (cx, cy, clayer)

            if current in closed_set:
                continue

            if cx == ex and cy == ey:
                return self._reconstruct_path(came_from, current)

            closed_set.add(current)

            for nx, ny, nlayer in self.grid.get_neighbors(cx, cy, clayer):
                neighbor = (nx, ny, nlayer)
                if neighbor in closed_set:
                    continue

                # Movement cost
                if nlayer != clayer:
                    move_cost = self.via_cost + self.layer_change_penalty
                else:
                    move_cost = 1.0

                # Layer preference penalty
                if nlayer != preferred_layer:
                    move_cost += 0.1 * abs(nlayer - preferred_layer)

                # Angle preference (prefer continuing straight)
                if current in came_from:
                    px, py, pl = came_from[current]
                    if pl == clayer == nlayer:
                        dx1, dy1 = cx - px, cy - py
                        dx2, dy2 = nx - cx, ny - cy
                        if dx1 == dx2 and dy1 == dy2:
                            move_cost -= self.angle_preference

                tentative_g = g_score[current] + move_cost

                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    h = self._heuristic(nx, ny, ex, ey, nlayer, preferred_layer)
                    f = tentative_g + h
                    counter += 1
                    heapq.heappush(open_set, (f, counter, nx, ny, nlayer))

        return None

    def _heuristic(
        self,
        gx: int,
        gy: int,
        ex: int,
        ey: int,
        layer: int,
        preferred_layer: int,
    ) -> float:
        """Admissible heuristic: Manhattan distance + layer penalty."""
        dist = abs(gx - ex) + abs(gy - ey)
        layer_penalty = abs(layer - preferred_layer) * 2.0
        return dist + layer_penalty

    def _evaluate_path(
        self,
        path: list[tuple[int, int, int]],
        preferred_layer: int,
    ) -> float:
        """Evaluate path quality (lower is better)."""
        if not path:
            return float("inf")

        cost = 0.0
        via_count = 0
        off_layer_steps = 0

        for i in range(1, len(path)):
            p1 = path[i - 1]
            p2 = path[i]
            if p1[2] != p2[2]:
                via_count += 1
                cost += self.via_cost
            if p2[2] != preferred_layer:
                off_layer_steps += 1

        cost += via_count * self.layer_change_penalty
        cost += off_layer_steps * 0.1
        cost += len(path) * 0.01

        return cost

    def _reconstruct_path(
        self,
        came_from: dict[tuple[int, int, int], tuple[int, int, int]],
        current: tuple[int, int, int],
    ) -> list[tuple[int, int, int]]:
        """Reconstruct path from came_from map."""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def occupy_path(self, path: RoutePath, net_id: str):
        """Mark path cells as occupied by the net."""
        for x_mm, y_mm, layer in path.points:
            gx, gy = self.grid.mm_to_grid(x_mm, y_mm)
            self.grid.occupy_cell(gx, gy, layer, net_id)
