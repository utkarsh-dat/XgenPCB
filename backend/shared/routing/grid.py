"""
PCB Builder - Routing Grid
Discretizes the PCB into a multi-layer grid for pathfinding.
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GridCell:
    """Single cell in the routing grid."""
    x: int
    y: int
    layer: int
    is_occupied: bool = False
    is_obstacle: bool = False
    cost: float = 1.0
    net_id: Optional[str] = None
    via_cost: float = 1.0


class RoutingGrid:
    """
    Multi-layer routing grid for A* pathfinding.

    Converts continuous PCB coordinates into a discretized grid
    with configurable resolution per layer.
    """

    def __init__(
        self,
        width_mm: float,
        height_mm: float,
        num_layers: int,
        resolution_mm: float = 0.05,
        min_clearance_mm: float = 0.15,
    ):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.num_layers = num_layers
        self.resolution_mm = resolution_mm
        self.min_clearance_mm = min_clearance_mm

        self.grid_width = int(math.ceil(width_mm / resolution_mm))
        self.grid_height = int(math.ceil(height_mm / resolution_mm))

        # 3D grid: [layer][y][x]
        self.cells: list[list[list[GridCell]]] = []
        self._initialize_grid()

    def _initialize_grid(self):
        for layer in range(self.num_layers):
            layer_grid = []
            for y in range(self.grid_height):
                row = []
                for x in range(self.grid_width):
                    row.append(GridCell(x=x, y=y, layer=layer))
                layer_grid.append(row)
            self.cells.append(layer_grid)

    def mm_to_grid(self, x_mm: float, y_mm: float) -> tuple[int, int]:
        """Convert mm coordinates to grid indices."""
        gx = int(round(x_mm / self.resolution_mm))
        gy = int(round(y_mm / self.resolution_mm))
        gx = max(0, min(gx, self.grid_width - 1))
        gy = max(0, min(gy, self.grid_height - 1))
        return gx, gy

    def grid_to_mm(self, gx: int, gy: int) -> tuple[float, float]:
        """Convert grid indices to mm coordinates."""
        x_mm = gx * self.resolution_mm
        y_mm = gy * self.resolution_mm
        return x_mm, y_mm

    def is_valid(self, gx: int, gy: int, layer: int) -> bool:
        """Check if grid coordinates are within bounds."""
        return (
            0 <= gx < self.grid_width
            and 0 <= gy < self.grid_height
            and 0 <= layer < self.num_layers
        )

    def get_cell(self, gx: int, gy: int, layer: int) -> Optional[GridCell]:
        """Get a cell at the given grid coordinates."""
        if not self.is_valid(gx, gy, layer):
            return None
        return self.cells[layer][gy][gx]

    def set_obstacle(self, x_mm: float, y_mm: float, radius_mm: float, layer: int):
        """Mark a circular area as obstacle."""
        gx_center, gy_center = self.mm_to_grid(x_mm, y_mm)
        radius_cells = int(math.ceil(radius_mm / self.resolution_mm))

        for dy in range(-radius_cells, radius_cells + 1):
            for dx in range(-radius_cells, radius_cells + 1):
                gx = gx_center + dx
                gy = gy_center + dy
                if self.is_valid(gx, gy, layer):
                    dist = math.sqrt(dx**2 + dy**2) * self.resolution_mm
                    if dist <= radius_mm:
                        cell = self.cells[layer][gy][gx]
                        cell.is_obstacle = True
                        cell.is_occupied = True

    def set_trace_obstacle(
        self,
        x1_mm: float,
        y1_mm: float,
        x2_mm: float,
        y2_mm: float,
        width_mm: float,
        layer: int,
    ):
        """Mark a trace segment as obstacle with clearance."""
        clearance = self.min_clearance_mm
        gx1, gy1 = self.mm_to_grid(x1_mm, y1_mm)
        gx2, gy2 = self.mm_to_grid(x2_mm, y2_mm)
        width_cells = int(math.ceil((width_mm / 2 + clearance) / self.resolution_mm))

        # Bresenham-like line rasterization
        dx = abs(gx2 - gx1)
        dy = abs(gy2 - gy1)
        sx = 1 if gx1 < gx2 else -1
        sy = 1 if gy1 < gy2 else -1
        err = dx - dy

        cx, cy = gx1, gy1
        while True:
            for off_y in range(-width_cells, width_cells + 1):
                for off_x in range(-width_cells, width_cells + 1):
                    nx = cx + off_x
                    ny = cy + off_y
                    if self.is_valid(nx, ny, layer):
                        self.cells[layer][ny][nx].is_obstacle = True
                        self.cells[layer][ny][nx].is_occupied = True

            if cx == gx2 and cy == gy2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy

    def place_via(self, x_mm: float, y_mm: float, diameter_mm: float = 0.6):
        """Place a via through all layers at given position."""
        gx, gy = self.mm_to_grid(x_mm, y_mm)
        radius_cells = int(math.ceil(diameter_mm / 2 / self.resolution_mm))

        for layer in range(self.num_layers):
            for dy in range(-radius_cells, radius_cells + 1):
                for dx in range(-radius_cells, radius_cells + 1):
                    nx = gx + dx
                    ny = gy + dy
                    if self.is_valid(nx, ny, layer):
                        self.cells[layer][ny][nx].is_obstacle = True
                        self.cells[layer][ny][nx].is_occupied = True

    def occupy_cell(self, gx: int, gy: int, layer: int, net_id: str):
        """Mark a cell as occupied by a specific net."""
        if self.is_valid(gx, gy, layer):
            cell = self.cells[layer][gy][gx]
            cell.is_occupied = True
            cell.net_id = net_id

    def free_cell(self, gx: int, gy: int, layer: int):
        """Free a cell (remove occupation but keep obstacles)."""
        if self.is_valid(gx, gy, layer):
            cell = self.cells[layer][gy][gx]
            if not cell.is_obstacle:
                cell.is_occupied = False
                cell.net_id = None

    def get_neighbors(self, gx: int, gy: int, layer: int) -> list[tuple[int, int, int]]:
        """
        Get valid neighboring cells for pathfinding.

        Returns 4-connected neighbors on same layer + via transitions.
        """
        neighbors = []

        # 4-connected on same layer
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = gx + dx, gy + dy
            if self.is_valid(nx, ny, layer):
                cell = self.cells[layer][ny][nx]
                if not cell.is_occupied:
                    neighbors.append((nx, ny, layer))

        # Via transitions (up and down)
        for dl in [-1, 1]:
            nl = layer + dl
            if self.is_valid(gx, gy, nl):
                cell = self.cells[nl][gy][gx]
                if not cell.is_occupied:
                    neighbors.append((gx, gy, nl))

        return neighbors

    def get_occupied_cells_for_net(self, net_id: str) -> list[tuple[int, int, int]]:
        """Get all cells occupied by a specific net."""
        cells = []
        for layer in range(self.num_layers):
            for y in range(self.grid_height):
                for x in range(self.grid_width):
                    if self.cells[layer][y][x].net_id == net_id:
                        cells.append((x, y, layer))
        return cells

    def free_net(self, net_id: str):
        """Free all cells occupied by a specific net."""
        for layer in range(self.num_layers):
            for y in range(self.grid_height):
                for x in range(self.grid_width):
                    if self.cells[layer][y][x].net_id == net_id:
                        self.free_cell(x, y, layer)

    def get_occupancy_map(self, layer: int) -> list[list[bool]]:
        """Get 2D occupancy map for a layer."""
        return [
            [self.cells[layer][y][x].is_occupied for x in range(self.grid_width)]
            for y in range(self.grid_height)
        ]

    def clone(self) -> "RoutingGrid":
        """Create a deep copy of the grid."""
        new_grid = RoutingGrid(
            self.width_mm,
            self.height_mm,
            self.num_layers,
            self.resolution_mm,
            self.min_clearance_mm,
        )
        for layer in range(self.num_layers):
            for y in range(self.grid_height):
                for x in range(self.grid_width):
                    src = self.cells[layer][y][x]
                    dst = new_grid.cells[layer][y][x]
                    dst.is_occupied = src.is_occupied
                    dst.is_obstacle = src.is_obstacle
                    dst.cost = src.cost
                    dst.net_id = src.net_id
        return new_grid
