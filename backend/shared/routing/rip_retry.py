"""
PCB Builder - Rip-up and Retry Router
Handles routing conflicts by removing blocking traces and rerouting.
"""

import math
from dataclasses import dataclass, field
from typing import Optional

from shared.logging_config import logger
from shared.routing.astar_router import AStarRouter, RoutePath
from shared.routing.grid import RoutingGrid


@dataclass
class RoutedNet:
    """A successfully routed net."""
    net_name: str
    paths: list[RoutePath]
    pins: list[tuple[float, float]]
    is_routed: bool = True
    retry_count: int = 0


@dataclass
class RoutingResult:
    """Complete routing result."""
    routed_nets: list[RoutedNet]
    unrouted_nets: list[str]
    total_vias: int = 0
    total_length_mm: float = 0.0
    completion_rate: float = 0.0
    iterations: int = 0


class RipAndRetryRouter:
    """
    Multi-net router with rip-up and retry strategy.

    Routes nets in priority order. When a net cannot be routed,
    it rips up blocking traces and retries with increasing N.
    """

    def __init__(
        self,
        grid: RoutingGrid,
        max_ripups: int = 3,
        max_iterations: int = 50,
    ):
        self.grid = grid
        self.max_ripups = max_ripups
        self.max_iterations = max_iterations
        self.router = AStarRouter(grid)
        self.routed_nets: dict[str, RoutedNet] = {}
        self.iterations = 0

    def route_all(
        self,
        nets: list[dict],
        components: list[dict],
        pin_positions: dict[str, dict[str, tuple[float, float]]],
    ) -> RoutingResult:
        """
        Route all nets with rip-up and retry.

        Args:
            nets: List of net definitions with name and pins
            components: List of placed components
            pin_positions: Map of component_id -> pin_name -> (x, y) in mm

        Returns:
            RoutingResult with routed and unrouted nets
        """
        self.routed_nets = {}
        self.iterations = 0

        # Add component obstacles to grid
        self._add_component_obstacles(components)

        # Sort nets by priority: power first, then high-speed, then signals
        sorted_nets = self._sort_nets_by_priority(nets)

        total_nets = len(sorted_nets)
        unrouted = []

        for net in sorted_nets:
            net_name = net.get("name", "")
            pins = net.get("pins", [])

            if len(pins) < 2:
                continue

            # Get pin positions
            pin_coords = []
            for pin in pins:
                comp_id = pin.get("component_id", "")
                pin_name = pin.get("pin", "")
                if comp_id in pin_positions and pin_name in pin_positions[comp_id]:
                    pin_coords.append(pin_positions[comp_id][pin_name])

            if len(pin_coords) < 2:
                unrouted.append(net_name)
                continue

            # Route this net
            success = self._route_net(net_name, pin_coords)
            if not success:
                # Try rip-up and retry
                success = self._rip_and_retry(net_name, pin_coords)

            if success:
                pass
            else:
                unrouted.append(net_name)
                logger.warning(
                    "Net could not be routed after retries",
                    net=net_name,
                )

        # Build result
        routed_list = list(self.routed_nets.values())
        total_vias = sum(
            sum(p.via_count for p in rn.paths)
            for rn in routed_list
        )
        total_length = sum(
            sum(p.total_length_mm for p in rn.paths)
            for rn in routed_list
        )
        completion = len(routed_list) / max(total_nets, 1) * 100

        return RoutingResult(
            routed_nets=routed_list,
            unrouted_nets=unrouted,
            total_vias=total_vias,
            total_length_mm=total_length,
            completion_rate=round(completion, 1),
            iterations=self.iterations,
        )

    def _route_net(
        self,
        net_name: str,
        pin_coords: list[tuple[float, float]],
    ) -> bool:
        """Route a single net connecting all its pins."""
        if len(pin_coords) < 2:
            return False

        paths = []

        # Minimum spanning tree approach: connect nearest unconnected pin
        connected = {0}
        unconnected = set(range(1, len(pin_coords)))

        while unconnected:
            best_dist = float("inf")
            best_pair = None

            for ci in connected:
                for ui in unconnected:
                    dx = pin_coords[ui][0] - pin_coords[ci][0]
                    dy = pin_coords[ui][1] - pin_coords[ci][1]
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist < best_dist:
                        best_dist = dist
                        best_pair = (ci, ui)

            if not best_pair:
                break

            ci, ui = best_pair
            start = pin_coords[ci]
            end = pin_coords[ui]

            path = self.router.find_path(start, end, net_id=net_name)
            if path:
                self.router.occupy_path(path, net_name)
                paths.append(path)
                connected.add(ui)
            else:
                return False

            unconnected.remove(ui)
            self.iterations += 1

        if paths:
            self.routed_nets[net_name] = RoutedNet(
                net_name=net_name,
                paths=paths,
                pins=pin_coords,
            )
            return True

        return False

    def _rip_and_retry(
        self,
        net_name: str,
        pin_coords: list[tuple[float, float]],
    ) -> bool:
        """Try to route by ripping up blocking nets."""
        for rip_count in range(1, self.max_ripups + 1):
            # Find blocking nets
            blocking_nets = self._find_blocking_nets(pin_coords)

            if not blocking_nets:
                return False

            # Rip up the net with fewest traces (least impact)
            victim = min(blocking_nets, key=lambda n: len(self.routed_nets[n].paths))

            logger.info(
                "Ripping up blocking net for retry",
                victim_net=victim,
                target_net=net_name,
                rip_count=rip_count,
            )

            # Free victim's cells
            victim_net = self.routed_nets.pop(victim)
            for path in victim_net.paths:
                for x_mm, y_mm, layer in path.points:
                    gx, gy = self.grid.mm_to_grid(x_mm, y_mm)
                    self.grid.free_cell(gx, gy, layer)

            # Try routing target
            success = self._route_net(net_name, pin_coords)
            if success:
                # Re-route victim
                self._route_net(victim, victim_net.pins)
                return True

            # If still fails, continue to next rip-up iteration
            # Put victim back
            self.routed_nets[victim] = victim_net
            for path in victim_net.paths:
                self.router.occupy_path(path, victim)

        return False

    def _find_blocking_nets(
        self,
        pin_coords: list[tuple[float, float]],
    ) -> set[str]:
        """Find nets that block the direct path between pins."""
        blocking = set()

        # Simple heuristic: find nets whose traces are near the bounding box
        if len(pin_coords) < 2:
            return blocking

        min_x = min(p[0] for p in pin_coords)
        max_x = max(p[0] for p in pin_coords)
        min_y = min(p[1] for p in pin_coords)
        max_y = max(p[1] for p in pin_coords)

        margin = 2.0  # mm

        for net_name, routed in self.routed_nets.items():
            for path in routed.paths:
                for x_mm, y_mm, layer in path.points:
                    if (
                        min_x - margin <= x_mm <= max_x + margin
                        and min_y - margin <= y_mm <= max_y + margin
                    ):
                        blocking.add(net_name)
                        break
                if net_name in blocking:
                    break

        return blocking

    def _sort_nets_by_priority(self, nets: list[dict]) -> list[dict]:
        """Sort nets: power/ground first, then high-speed, then signals."""
        power_nets = []
        high_speed_nets = []
        signal_nets = []

        for net in nets:
            name = net.get("name", "").upper()
            if any(p in name for p in ["VCC", "GND", "VDD", "3V3", "5V", "PWR", "VBAT"]):
                power_nets.append(net)
            elif any(h in name for h in ["USB", "PCIE", "DDR", "MIPI", "ETH", "HDMI", "CLK"]):
                high_speed_nets.append(net)
            else:
                signal_nets.append(net)

        return power_nets + high_speed_nets + signal_nets

    def _add_component_obstacles(self, components: list[dict]):
        """Add component body obstacles to the grid."""
        for comp in components:
            x = comp.get("x", 0)
            y = comp.get("y", 0)
            footprint = comp.get("footprint", "")

            # Estimate component size from footprint
            size_mm = self._estimate_footprint_size(footprint)

            # Obstacle on top layer
            self.grid.set_obstacle(x, y, size_mm / 2, layer=0)

    def _estimate_footprint_size(self, footprint: str) -> float:
        """Estimate component body size from footprint name."""
        fp = footprint.upper()

        size_map = {
            "0402": 1.0,
            "0603": 1.6,
            "0805": 2.0,
            "1206": 3.2,
            "SOT-23": 3.0,
            "SOT-223": 6.5,
            "SOIC-8": 5.0,
            "SOIC-16": 10.0,
            "TQFP-48": 7.0,
            "TQFP-64": 10.0,
            "QFN-48": 7.0,
            "QFN-32": 5.0,
            "BGA": 10.0,
            "DIP-8": 9.0,
            "DIP-14": 19.0,
            "DIP-16": 19.0,
        }

        for key, size in size_map.items():
            if key in fp:
                return size

        return 2.0  # Default small component

    def get_tracks_from_result(self, result: RoutingResult) -> list[dict]:
        """Convert routing result to track format for design JSON."""
        tracks = []

        for routed in result.routed_nets:
            for path in routed.paths:
                points = path.points
                for i in range(len(points) - 1):
                    p1 = points[i]
                    p2 = points[i + 1]

                    # Only create track for same-layer segments
                    if p1[2] == p2[2]:
                        tracks.append({
                            "start": [round(p1[0], 3), round(p1[1], 3)],
                            "end": [round(p2[0], 3), round(p2[1], 3)],
                            "width": 0.25,
                            "layer": f"L{p1[2]}.Cu",
                            "net": routed.net_name,
                        })

        return tracks

    def get_vias_from_result(self, result: RoutingResult) -> list[dict]:
        """Convert routing result to via format for design JSON."""
        vias = []

        for routed in result.routed_nets:
            for path in routed.paths:
                points = path.points
                for i in range(1, len(points)):
                    p1 = points[i - 1]
                    p2 = points[i]

                    if p1[2] != p2[2]:
                        vias.append({
                            "x": round(p1[0], 3),
                            "y": round(p1[1], 3),
                            "from_layer": min(p1[2], p2[2]),
                            "to_layer": max(p1[2], p2[2]),
                            "diameter": 0.6,
                            "drill": 0.3,
                        })

        return vias
