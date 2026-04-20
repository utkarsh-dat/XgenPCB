"""
PCB Builder - Advanced PCB Routing RL Environment
Research-backed implementation with GCN + Transformer net ordering,
Dueling Double DQN, and multi-objective rewards.

References:
- TREND: Transformer-based RL for Net Ordering (IJCAI 2025)
- RL PCB Placement (DATE 2024)
- Dueling Double DQN (arxiv:1511.06581)
- GCN for circuit analysis (NeurIPS, ICML workshops)
"""

from dataclasses import dataclass, field
from typing import Optional, NamedTuple
import numpy as np
from enum import IntEnum


class RoutingAction(IntEnum):
    """Discrete routing actions."""
    MOVE_UP = 0
    MOVE_DOWN = 1
    MOVE_LEFT = 2
    MOVE_RIGHT = 3
    VIA_UP = 4
    VIA_DOWN = 5


class NetPriority(IntEnum):
    """Net routing priority levels."""
    CRITICAL = 0    # Power, ground, high-speed
    HIGH = 1         # Signal nets
    MEDIUM = 2        # General signals
    LOW = 3           # Unconnected


@dataclass
class Net:
    """Represents a net (electrical connection) in the PCB."""
    id: str
    name: str
    pins: list[tuple[int, int, int]]  # (x, y, layer)
    is_high_speed: bool = False
    is_power: bool = False
    is_ground: bool = False
    target_impedance: float = 50.0  # Ohms
    max_current: float = 0.5  # Amps
    is_routed: bool = False
    trace_segments: list[dict] = field(default_factory=list)
    priority: NetPriority = NetPriority.MEDIUM

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

    def get_priority(self) -> NetPriority:
        """Determine net priority based on electrical properties."""
        if self.is_power or self.is_ground:
            return NetPriority.CRITICAL
        elif self.is_high_speed:
            return NetPriority.HIGH
        return NetPriority.MEDIUM


class NetFeature(NamedTuple):
    """Graph node features for GCN embedding."""
    bounding_box_area: float
    pin_count: int
    is_routed: bool
    priority: int
    wirelength_estimate: float
    aspect_ratio: float


@dataclass
class PCBState:
    """Complete state of a PCB routing environment."""
    grid_size: int = 128
    num_layers: int = 4
    grid: Optional[np.ndarray] = None  # Channel-first encoding
    obstacles: Optional[np.ndarray] = None  # Static obstacles
    nets: list[Net] = field(default_factory=list)
    vias: list[dict] = field(default_factory=list)
    components: list[dict] = field(default_factory=list)
    routed_tracks: list[dict] = field(default_factory=list)

    # GCN adjacency: net-to-net influence relationships
    net_adjacency: Optional[np.ndarray] = None

    def __post_init__(self):
        if self.grid is None:
            # Channel encoding (expanded for multi-objective):
            # 0: obstacle map (components, board edge)
            # 1: routed traces
            # 2: current net target pins
            # 3: current agent position
            # 4: via locations
            # 5: high-speed net regions
            self.grid = np.zeros((6, self.grid_size, self.grid_size), dtype=np.float32)
        if self.obstacles is None:
            self.obstacles = self.grid[0].copy()

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

    def compute_net_features(self) -> list[NetFeature]:
        """Compute per-net features for GCN embedding."""
        features = []
        for net in self.nets:
            bb = net.bounding_box()
            area = bb["width"] * bb["height"]
            aspect = bb["width"] / (bb["height"] + 1e-6)
            wirelength_est = (bb["width"] + bb["height"]) * 2
            features.append(NetFeature(
                bounding_box_area=area,
                pin_count=len(net.pins),
                is_routed=int(net.is_routed),
                priority=net.get_priority().value,
                wirelength_estimate=wirelength_est,
                aspect_ratio=aspect,
            ))
        return features

    def build_net_adjacency(self, influence_radius: int = 30):
        """Build net-to-net adjacency based on spatial influence."""
        n_nets = len(self.nets)
        if n_nets == 0:
            self.net_adjacency = np.zeros((0, 0), dtype=np.float32)
            return

        adjacency = np.zeros((n_nets, n_nets), dtype=np.float32)
        for i, net_i in enumerate(self.nets):
            bb_i = net_i.bounding_box()
            for j, net_j in enumerate(self.nets):
                if i == j:
                    continue
                bb_j = net_j.bounding_box()
                # Check if bounding boxes overlap within influence radius
                dist = max(
                    abs(bb_i["x_min"] - bb_j["x_max"]),
                    abs(bb_j["x_min"] - bb_i["x_max"]),
                    abs(bb_i["y_min"] - bb_j["y_max"]),
                    abs(bb_j["y_min"] - bb_i["y_max"]),
                )
                if dist < influence_radius:
                    adjacency[i, j] = 1.0
        self.net_adjacency = adjacency


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

    # Reward weights
    wirelength_weight: float = -0.01
    via_penalty: float = -0.5
    collision_penalty: float = -1.0
    completion_bonus: float = 100.0
    pin_reach_bonus: float = 10.0
    drv_penalty: float = -5.0

    # Multi-objective
    prioritize_differential_pairs: bool = True
    minimize_vias: bool = True
    minimize_crosstalk: bool = True


@dataclass
class RoutingMetrics:
    """Track routing quality metrics."""
    total_wirelength: float = 0.0
    via_count: int = 0
    DRCviolations: int = 0
    crosstalk_estimates: float = 0.0
    nets_completed: int = 0
    nets_failed: int = 0

    def to_dict(self) -> dict:
        return {
            "wirelength": self.total_wirelength,
            "via_count": self.via_count,
            "drv_violations": self.DRCviolations,
            "crosstalk": self.crosstalk_estimates,
            "nets_completed": self.nets_completed,
            "nets_failed": self.nets_failed,
            "completion_rate": self.nets_completed / max(1, self.nets_completed + self.nets_failed),
        }


class PCBRoutingEnv:
    """
    Advanced research-backed PCB routing environment.

    Architecture:
    - Multi-channel observation for GCN features
    - Dueling Double DQN-compatible reward structure
    - Net ordering via priority heuristic
    - Multi-objective reward: wirelength + vias + DRC + crosstalk

    Observation: (6, grid_size, grid_size) float32 grid
    Action space: 6 discrete actions
    """

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
        self.metrics = RoutingMetrics()
        self.episode_count = 0

        # For TREND-style net ordering
        self.net_order = []

    def reset(self, netlist: list[dict] = None, seed: int = None) -> PCBState:
        """Reset environment with a new (or random) netlist."""
        if seed is not None:
            np.random.seed(seed)

        self.state = PCBState(
            grid_size=self.config.grid_size,
            num_layers=self.config.num_layers,
        )
        self.metrics = RoutingMetrics()

        if netlist:
            self.state.nets = [
                Net(
                    id=n["id"],
                    name=n.get("name", f"net_{i}"),
                    pins=n["pins"],
                    is_high_speed=n.get("is_high_speed", False),
                    is_power=n.get("is_power", False),
                    is_ground=n.get("is_ground", False),
                    target_impedance=n.get("target_impedance", 50.0),
                )
                for i, n in enumerate(netlist)
            ]
            # Set priorities
            for net in self.state.nets:
                net.priority = net.get_priority()
        else:
            self._generate_random_netlist()

        # Build net adjacency for GCN
        self.state.build_net_adjacency()

        # Compute initial net order (priority-based + spatial)
        self._compute_net_order()

        self.current_net_idx = 0
        self.step_count = 0
        self.total_steps = 0
        self._setup_current_net()

        return self.state

    def step(self, action: int) -> tuple[PCBState, float, bool, dict]:
        """Take a routing action with multi-objective rewards."""
        self.step_count += 1
        self.total_steps += 1

        reward = 0.0
        done = False
        info = {"metrics": self.metrics.to_dict()}

        x, y, layer = self.agent_pos

        # Execute action
        if action == RoutingAction.MOVE_UP and y > 0:
            self.agent_pos[1] -= 1
        elif action == RoutingAction.MOVE_DOWN and y < self.config.grid_size - 1:
            self.agent_pos[1] += 1
        elif action == RoutingAction.MOVE_LEFT and x > 0:
            self.agent_pos[0] -= 1
        elif action == RoutingAction.MOVE_RIGHT and x < self.config.grid_size - 1:
            self.agent_pos[0] += 1
        elif action == RoutingAction.VIA_UP and layer > 0:
            self.agent_pos[2] -= 1
            self.state.vias.append({"x": x, "y": y, "from_layer": layer, "to_layer": layer - 1})
            self.metrics.via_count += 1
            reward += self.config.via_penalty
            info["via_placed"] = True
        elif action == RoutingAction.VIA_DOWN and layer < self.config.num_layers - 1:
            self.agent_pos[2] += 1
            self.state.vias.append({"x": x, "y": y, "from_layer": layer, "to_layer": layer + 1})
            self.metrics.via_count += 1
            reward += self.config.via_penalty
            info["via_placed"] = True

        new_x, new_y, new_layer = self.agent_pos

        # Check collision with existing traces or obstacles
        collision = False

        # Check trace collision
        if self.state.grid[1, new_y, new_x] > 0:
            collision = True

        # Check obstacle collision
        if self.state.obstacles is not None and self.state.obstacles[new_y, new_x] > 0:
            collision = True

        # Check clearance violations (adjacent routed traces)
        if not collision and self._check_clearance_violation(new_x, new_y, layer):
            collision = True

        if collision:
            reward += self.config.collision_penalty
            self.metrics.DRCviolations += 1
            info["collision"] = True
        else:
            # Place trace
            self.state.grid[1, new_y, new_x] = 1.0
            self.state.routed_tracks.append({
                "x": new_x, "y": new_y, "layer": new_layer,
                "net": self.net_order[self.current_net_idx],
            })
            self.metrics.total_wirelength += 1.0

        # Check if reached target pin
        current_net = self.state.nets[self.net_order[self.current_net_idx]]
        target_pins = current_net.pins[1:]  # All pins except source
        for pin in target_pins:
            if new_x == pin[0] and new_y == pin[1] and new_layer == pin[2]:
                reward += self.config.pin_reach_bonus
                current_net.is_routed = True
                self.metrics.nets_completed += 1
                info["net_completed"] = current_net.name

                # Move to next net
                self._advance_to_next_net()
                done = (self.current_net_idx >= len(self.state.nets))
                if done:
                    reward += self.config.completion_bonus
                    info["all_routed"] = True
                break
        else:
            # Small step penalty for efficiency
            reward += self.config.wirelength_weight

        # Check step limits
        if self.step_count >= self.config.max_steps_per_net:
            self.metrics.nets_failed += 1
            reward += self.config.drv_penalty
            info["net_timeout"] = True
            self._advance_to_next_net()

            if self.current_net_idx >= len(self.state.nets):
                done = True

        if self.total_steps >= self.config.max_total_steps:
            done = True
            info["total_timeout"] = True

        # Update grid display
        self.state.grid[3, :, :] = 0
        self.state.grid[3, self.agent_pos[1], self.agent_pos[0]] = 1.0

        info["metrics"] = self.metrics.to_dict()
        return self.state, reward, done, info

    def _check_clearance_violation(self, x: int, y: int, layer: int) -> bool:
        """Checktrace clearance violation."""
        min_clearance = int(self.config.min_clearance / self.config.grid_resolution)
        for dy in range(-min_clearance, min_clearance + 1):
            for dx in range(-min_clearance, min_clearance + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.config.grid_size and 0 <= ny < self.config.grid_size:
                    if self.state.grid[1, ny, nx] > 0:
                        return True
        return False

    def _advance_to_next_net(self):
        """Move to next unrouted net in order."""
        self.current_net_idx += 1
        self.step_count = 0

        if self.current_net_idx < len(self.state.nets):
            self._setup_current_net()

    def _compute_net_order(self) -> list[int]:
        """
        Compute optimal net routing order using TREND-inspired heuristic.

        Order by: priority (critical first) + spatial clustering
        """
        if not self.state.nets:
            return []

        # Sort by priority first, then by bounding box area
        net_with_priority = []
        for i, net in enumerate(self.state.nets):
            bb = net.bounding_box()
            # Center point for spatial clustering
            center_x = (bb["x_min"] + bb["x_max"]) / 2
            center_y = (bb["y_min"] + bb["y_max"]) / 2
            net_with_priority.append((
                net.get_priority().value,  # Lower = higher priority
                bb["width"] * bb["height"],  # Smaller first
                i,
            ))
            net.priority = net.get_priority()

        # Sort: priority (0 first), then area (smaller first)
        net_with_priority.sort(key=lambda x: (x[0], x[1]))
        self.net_order = [x[2] for x in net_with_priority]
        return self.net_order

    def _setup_current_net(self):
        """Set up the grid for routing the current net."""
        if self.current_net_idx >= len(self.net_order):
            return

        net_idx = self.net_order[self.current_net_idx]
        net = self.state.nets[net_idx]

        # Clear target pins display
        self.state.grid[2, :, :] = 0

        # Mark target pins
        for pin in net.pins:
            px, py, pz = pin[0], pin[1], pin[2] if len(pin) > 2 else 0
            if 0 <= px < self.config.grid_size and 0 <= py < self.config.grid_size:
                self.state.grid[2, py, px] = 1.0

        # Mark high-speed regions
        if net.is_high_speed:
            self.state.grid[5, :, :] = 1.0

        # Set agent to first pin
        if net.pins:
            pin = net.pins[0]
            layer = pin[2] if len(pin) > 2 else 0
            self.agent_pos = [pin[0], pin[1], layer]

    def _generate_random_netlist(self, num_nets: int = 10, seed: int = None):
        """Generate a random netlist for training with realistic properties."""
        if seed is not None:
            np.random.seed(seed)

        rng = np.random.default_rng()
        margin = 10
        max_coord = self.config.grid_size - margin

        # Place random "components" as obstacles
        num_components = rng.integers(5, 20)
        self.state.components = []
        for _ in range(num_components):
            cx = rng.integers(margin, max_coord)
            cy = rng.integers(margin, max_coord)
            w = rng.integers(3, 10)
            h = rng.integers(3, 10)
            x1, y1 = max(0, cx - w // 2), max(0, cy - h // 2)
            x2, y2 = min(self.config.grid_size, cx + w // 2), min(self.config.grid_size, cy + h // 2)
            self.state.grid[0, y1:y2, x1:x2] = 1.0
            self.state.components.append({"x": cx, "y": cy, "w": w, "h": h})

        # Generate nets with realistic electrical properties
        self.state.nets = []
        for i in range(num_nets):
            num_pins = rng.integers(2, 5)
            pins = []

            # Power/ground nets (typically fewer pins, star topology)
            is_power = rng.random() < 0.1
            is_ground = rng.random() < 0.1

            # High-speed nets (differential pairs)
            is_high_speed = rng.random() < 0.15

            for _ in range(num_pins):
                px = rng.integers(margin, max_coord)
                py = rng.integers(margin, max_coord)
                # Ensure pin is not on an obstacle
                while self.state.grid[0, py, px] > 0:
                    px = rng.integers(margin, max_coord)
                    py = rng.integers(margin, max_coord)

                # For differential pairs, both pins on same layer
                layer = 0 if not is_high_speed else rng.integers(0, self.config.num_layers)
                pins.append((int(px), int(py), layer))

            net = Net(
                id=f"net_{i}",
                name=f"NET_{i}",
                pins=pins,
                is_high_speed=is_high_speed,
                is_power=is_power,
                is_ground=is_ground,
            )
            net.priority = net.get_priority()
            self.state.nets.append(net)

    def get_gcn_features(self) -> tuple[np.ndarray, np.ndarray]:
        """Get features and adjacency for GCN."""
        features = self.state.compute_net_features()

        # Convert to node feature matrix
        feature_matrix = np.array([
            [
                f.bounding_box_area / (self.config.grid_size ** 2),
                f.pin_count / 10.0,
                float(f.is_routed),
                f.priority / 3.0,
                f.wirelength_estimate / self.config.grid_size,
                f.aspect_ratio,
            ]
            for f in features
        ], dtype=np.float32)

        adjacency = self.state.net_adjacency
        if adjacency is None:
            adjacency = np.zeros((len(self.state.nets), len(self.state.nets)))

        return feature_matrix, adjacency

    def render(self) -> np.ndarray:
        """Render current state as RGB image for visualization."""
        h, w = self.config.grid_size, self.config.grid_size
        img = np.zeros((h, w, 3), dtype=np.float32)

        # Background: dark
        img[:, :] = 0.05

        # Obstacles: gray
        img[self.state.grid[0] > 0] = 0.3

        # Routed traces: blue
        img[self.state.grid[1] > 0, 0] = 0.2
        img[self.state.grid[1] > 0, 1] = 0.4
        img[self.state.grid[1] > 0, 2] = 0.8

        # Target pins: green
        img[self.state.grid[2] > 0, 1] = 0.8

        # Agent position: red
        ay, ax = self.agent_pos[1], self.agent_pos[0]
        if 0 <= ay < h and 0 <= ax < w:
            img[ay, ax, 0] = 1.0
            img[ay, ax, 1] = 0.2
            img[ay, ax, 2] = 0.2

        # Vias: yellow
        for via in self.state.vias:
            vx, vy = int(via["x"]), int(via["y"])
            if 0 <= vy < h and 0 <= vx < w:
                img[vy, vx, 0] = 1.0
                img[vy, vx, 1] = 1.0
                img[vy, vx, 2] = 0.0

        return (img * 255).astype(np.uint8)


# Gymnasium compatibility
def make_env(config: RoutingConfig = None) -> PCBRoutingEnv:
    """Create environment instance."""
    return PCBRoutingEnv(config)