"""
PCB Builder - PCB Routing Environment for RL
Gymnasium-compatible environment for training routing agents.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class Net:
    """Represents a net (electrical connection) in the PCB."""
    id: str
    name: str
    pins: list[tuple[int, int, int]]  # (x, y, layer)
    is_high_speed: bool = False
    target_impedance: float = 50.0  # Ohms
    max_current: float = 0.5  # Amps
    is_routed: bool = False
    trace_segments: list[dict] = field(default_factory=list)

    def bounding_box(self) -> dict:
        if not self.pins:
            return {"x_min": 0, "y_min": 0, "x_max": 0, "y_max": 0, "width": 0, "height": 0}
        xs = [p[0] for p in self.pins]
        ys = [p[1] for p in self.pins]
        return {
            "x_min": min(xs), "y_min": min(ys),
            "x_max": max(xs), "y_max": max(ys),
            "width": max(xs) - min(xs),
            "height": max(ys) - min(ys),
        }


@dataclass
class PCBState:
    """Complete state of a PCB routing environment."""
    grid_size: int = 128
    num_layers: int = 4
    grid: Optional[np.ndarray] = None  # (layers, H, W)
    nets: list[Net] = field(default_factory=list)
    vias: list[dict] = field(default_factory=list)
    components: list[dict] = field(default_factory=list)
    routed_tracks: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if self.grid is None:
            # Channel encoding:
            # 0: obstacle map (components, board edge)
            # 1: routed traces
            # 2: current net target pins
            # 3: current agent position
            self.grid = np.zeros((4, self.grid_size, self.grid_size), dtype=np.float32)

    @property
    def high_speed_nets(self) -> list[Net]:
        return [n for n in self.nets if n.is_high_speed]

    @property
    def observation(self) -> np.ndarray:
        return self.grid.copy()

    def is_complete(self) -> bool:
        return all(n.is_routed for n in self.nets)

    def get_routed_fraction(self) -> float:
        if not self.nets:
            return 1.0
        return sum(1 for n in self.nets if n.is_routed) / len(self.nets)


@dataclass
class RoutingConfig:
    """Configuration for the routing environment."""
    grid_size: int = 128
    num_layers: int = 4
    min_trace_width: float = 0.15  # mm
    min_clearance: float = 0.15  # mm
    min_via_diameter: float = 0.3  # mm
    grid_resolution: float = 0.1  # mm per grid cell
    max_steps_per_net: int = 500
    max_total_steps: int = 10000


class PCBRoutingEnv:
    """
    Gymnasium-compatible PCB routing environment.
    
    Observation: (num_layers, grid_size, grid_size) float32 grid
    Action space: 6 discrete actions
        0: Move Up
        1: Move Down
        2: Move Left
        3: Move Right
        4: Place Via (change layer up)
        5: Place Via (change layer down)
    """

    ACTION_UP = 0
    ACTION_DOWN = 1
    ACTION_LEFT = 2
    ACTION_RIGHT = 3
    ACTION_VIA_UP = 4
    ACTION_VIA_DOWN = 5

    def __init__(self, config: RoutingConfig = None):
        self.config = config or RoutingConfig()
        self.state = PCBState(
            grid_size=self.config.grid_size,
            num_layers=self.config.num_layers,
        )
        self.current_net_idx = 0
        self.agent_pos = [0, 0, 0]  # x, y, layer
        self.step_count = 0
        self.total_steps = 0

    def reset(self, netlist: list[dict] = None) -> PCBState:
        """Reset environment with a new (or random) netlist."""
        self.state = PCBState(
            grid_size=self.config.grid_size,
            num_layers=self.config.num_layers,
        )

        if netlist:
            self.state.nets = [
                Net(
                    id=n["id"],
                    name=n.get("name", f"net_{i}"),
                    pins=n["pins"],
                    is_high_speed=n.get("is_high_speed", False),
                    target_impedance=n.get("target_impedance", 50.0),
                )
                for i, n in enumerate(netlist)
            ]
        else:
            # Generate random netlist for training
            self._generate_random_netlist()

        self.current_net_idx = 0
        self.step_count = 0
        self.total_steps = 0
        self._setup_current_net()

        return self.state

    def step(self, action: int) -> tuple[PCBState, float, bool, dict]:
        """Take a routing action."""
        self.step_count += 1
        self.total_steps += 1

        reward = -0.01  # Small step penalty to encourage efficiency
        done = False
        info = {}

        x, y, layer = self.agent_pos

        # Execute action
        if action == self.ACTION_UP and y > 0:
            self.agent_pos[1] -= 1
        elif action == self.ACTION_DOWN and y < self.config.grid_size - 1:
            self.agent_pos[1] += 1
        elif action == self.ACTION_LEFT and x > 0:
            self.agent_pos[0] -= 1
        elif action == self.ACTION_RIGHT and x < self.config.grid_size - 1:
            self.agent_pos[0] += 1
        elif action == self.ACTION_VIA_UP and layer > 0:
            self.agent_pos[2] -= 1
            self.state.vias.append({"x": x, "y": y, "from_layer": layer, "to_layer": layer - 1})
            reward -= 0.5  # Via penalty
        elif action == self.ACTION_VIA_DOWN and layer < self.config.num_layers - 1:
            self.agent_pos[2] += 1
            self.state.vias.append({"x": x, "y": y, "from_layer": layer, "to_layer": layer + 1})
            reward -= 0.5

        new_x, new_y, new_layer = self.agent_pos

        # Check collision
        if self.state.grid[1, new_y, new_x] > 0:
            reward -= 1.0  # Collision penalty
            info["collision"] = True
        else:
            # Place trace
            self.state.grid[1, new_y, new_x] = 1.0
            self.state.routed_tracks.append({
                "x": new_x, "y": new_y, "layer": new_layer,
                "net": self.current_net_idx,
            })

        # Check if reached target pin
        current_net = self.state.nets[self.current_net_idx]
        target_pins = current_net.pins[1:]  # All pins except source
        for pin in target_pins:
            if new_x == pin[0] and new_y == pin[1]:
                reward += 10.0  # Pin reached!
                current_net.is_routed = True
                info["net_completed"] = current_net.name

                # Move to next net
                self.current_net_idx += 1
                self.step_count = 0

                if self.current_net_idx >= len(self.state.nets):
                    # All nets routed!
                    reward += 100.0
                    done = True
                    info["all_routed"] = True
                else:
                    self._setup_current_net()
                break

        # Check step limits
        if self.step_count >= self.config.max_steps_per_net:
            self.current_net_idx += 1
            self.step_count = 0
            reward -= 5.0  # Failed to route net
            info["net_timeout"] = True

            if self.current_net_idx >= len(self.state.nets):
                done = True

        if self.total_steps >= self.config.max_total_steps:
            done = True
            info["total_timeout"] = True

        # Update grid display
        self.state.grid[3, :, :] = 0  # Clear agent position
        self.state.grid[3, self.agent_pos[1], self.agent_pos[0]] = 1.0

        return self.state, reward, done, info

    def _setup_current_net(self):
        """Set up the grid for routing the current net."""
        if self.current_net_idx >= len(self.state.nets):
            return

        net = self.state.nets[self.current_net_idx]

        # Clear target pins display
        self.state.grid[2, :, :] = 0

        # Mark target pins
        for pin in net.pins:
            px, py = pin[0], pin[1]
            if 0 <= px < self.config.grid_size and 0 <= py < self.config.grid_size:
                self.state.grid[2, py, px] = 1.0

        # Set agent to first pin
        if net.pins:
            self.agent_pos = [net.pins[0][0], net.pins[0][1], net.pins[0][2] if len(net.pins[0]) > 2 else 0]

    def _generate_random_netlist(self, num_nets: int = 10):
        """Generate a random netlist for training."""
        rng = np.random.default_rng()
        margin = 10
        max_coord = self.config.grid_size - margin

        # Place random "components" as obstacles
        num_components = rng.integers(5, 20)
        for _ in range(num_components):
            cx = rng.integers(margin, max_coord)
            cy = rng.integers(margin, max_coord)
            w = rng.integers(3, 10)
            h = rng.integers(3, 10)
            x1, y1 = max(0, cx - w // 2), max(0, cy - h // 2)
            x2, y2 = min(self.config.grid_size, cx + w // 2), min(self.config.grid_size, cy + h // 2)
            self.state.grid[0, y1:y2, x1:x2] = 1.0
            self.state.components.append({"x": cx, "y": cy, "w": w, "h": h})

        # Generate nets
        for i in range(num_nets):
            num_pins = rng.integers(2, 4)
            pins = []
            for _ in range(num_pins):
                px = rng.integers(margin, max_coord)
                py = rng.integers(margin, max_coord)
                # Ensure pin is not on an obstacle
                while self.state.grid[0, py, px] > 0:
                    px = rng.integers(margin, max_coord)
                    py = rng.integers(margin, max_coord)
                pins.append((int(px), int(py), 0))

            self.state.nets.append(Net(
                id=f"net_{i}",
                name=f"NET_{i}",
                pins=pins,
                is_high_speed=rng.random() > 0.7,
            ))
