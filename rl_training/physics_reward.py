"""
PCB Builder - Physics-Informed Reward Functions
Multi-objective reward combining wirelength, vias, DRC, SI, and thermal analysis.
"""

import numpy as np
from typing import Optional

from rl_training.environment import PCBState, Net


class FDTDEmulator:
    """
    Lightweight FDTD (Finite Difference Time Domain) emulator.
    Approximates crosstalk between parallel traces without full-wave simulation.
    """

    def __init__(self, config: dict = None):
        config = config or {}
        self.grid_res = config.get("grid_resolution", 0.1)  # mm
        self.max_freq = config.get("max_frequency", 10e9)  # Hz
        self.epsilon_0 = 8.85e-12  # F/m
        self.epsilon_r = config.get("epsilon_r", 4.5)  # FR4

    def compute_crosstalk(self, state: PCBState) -> np.ndarray:
        """Compute crosstalk between high-speed nets."""
        hs_nets = state.high_speed_nets
        if len(hs_nets) < 2:
            return np.array([0.0])

        crosstalk = []
        for i, net_a in enumerate(hs_nets):
            worst_xtalk = 0.0
            for j, net_b in enumerate(hs_nets):
                if i >= j:
                    continue
                coupling = self._coupling_capacitance(net_a, net_b, state)
                worst_xtalk = max(worst_xtalk, coupling * 0.5)
            crosstalk.append(worst_xtalk)

        return np.array(crosstalk) if crosstalk else np.array([0.0])

    def _coupling_capacitance(self, net_a: Net, net_b: Net, state: PCBState) -> float:
        """Estimate coupling capacitance between two nets."""
        segments_a = self._get_trace_segments(net_a, state)
        segments_b = self._get_trace_segments(net_b, state)

        coupling = 0.0
        for seg_a in segments_a:
            for seg_b in segments_b:
                if seg_a["layer"] == seg_b["layer"]:
                    # Same layer - check parallel run
                    dist = self._segment_distance(seg_a, seg_b)
                    if dist > 0 and dist < 10:  # Within coupling range
                        overlap = self._overlap_length(seg_a, seg_b)
                        if overlap > 0:
                            width = self.grid_res  # Approximate trace width
                            coupling += (
                                self.epsilon_0 * self.epsilon_r * overlap * width
                            ) / (dist * self.grid_res)
        return coupling

    def _get_trace_segments(self, net: Net, state: PCBState) -> list[dict]:
        """Extract routed trace segments for a net."""
        net_idx = next((i for i, n in enumerate(state.nets) if n.id == net.id), -1)
        segments = []
        tracks = [t for t in state.routed_tracks if t.get("net") == net_idx]

        for i in range(len(tracks) - 1):
            segments.append({
                "x1": tracks[i]["x"], "y1": tracks[i]["y"],
                "x2": tracks[i + 1]["x"], "y2": tracks[i + 1]["y"],
                "layer": tracks[i]["layer"],
            })
        return segments

    def _segment_distance(self, seg_a: dict, seg_b: dict) -> float:
        """Compute minimum distance between two segments."""
        cx_a = (seg_a["x1"] + seg_a["x2"]) / 2
        cy_a = (seg_a["y1"] + seg_a["y2"]) / 2
        cx_b = (seg_b["x1"] + seg_b["x2"]) / 2
        cy_b = (seg_b["y1"] + seg_b["y2"]) / 2
        return np.sqrt((cx_a - cx_b) ** 2 + (cy_a - cy_b) ** 2)

    def _overlap_length(self, seg_a: dict, seg_b: dict) -> float:
        """Compute parallel overlap length between two segments."""
        # Simplified: check X or Y overlap
        x_overlap = max(0, min(seg_a["x2"], seg_b["x2"]) - max(seg_a["x1"], seg_b["x1"]))
        y_overlap = max(0, min(seg_a["y2"], seg_b["y2"]) - max(seg_a["y1"], seg_b["y1"]))
        return max(x_overlap, y_overlap) * self.grid_res


class ThermalSimulator:
    """Simplified thermal analysis for PCB routing rewards."""

    def __init__(self, config: dict = None):
        config = config or {}
        self.k = config.get("thermal_conductivity", 0.3)  # W/mK (FR4)
        self.ambient_temp = config.get("ambient_temp", 25.0)  # °C

    def evaluate(self, state: PCBState) -> float:
        """
        Evaluate thermal performance. Returns score 0-1.
        1.0 = perfect thermal distribution, 0.0 = dangerous hotspots.
        """
        thermal_map = self._build_thermal_map(state)
        max_temp = np.max(thermal_map)

        if max_temp > 85:
            return 0.0
        if max_temp > 70:
            return 0.3

        variance = np.var(thermal_map)
        uniformity = 1.0 / (1.0 + variance * 0.1)
        return min(1.0, uniformity)

    def _build_thermal_map(self, state: PCBState) -> np.ndarray:
        """Build temperature distribution map."""
        thermal = np.full((state.grid_size, state.grid_size), self.ambient_temp, dtype=np.float32)

        # Add heat from components
        for comp in state.components:
            x, y = comp.get("x", 0), comp.get("y", 0)
            w, h = comp.get("w", 5), comp.get("h", 5)
            power = comp.get("power_w", 0.5)

            x1 = max(0, x - w // 2)
            y1 = max(0, y - h // 2)
            x2 = min(state.grid_size, x + w // 2)
            y2 = min(state.grid_size, y + h // 2)

            area = max(1, (x2 - x1) * (y2 - y1))
            thermal[y1:y2, x1:x2] += power * 50.0 / area

        # Simple diffusion (3 iterations)
        kernel = np.array([[0.05, 0.1, 0.05], [0.1, 0.4, 0.1], [0.05, 0.1, 0.05]])
        for _ in range(3):
            padded = np.pad(thermal, 1, mode="edge")
            new_thermal = np.zeros_like(thermal)
            for di in range(3):
                for dj in range(3):
                    new_thermal += kernel[di, dj] * padded[di:di + state.grid_size, dj:dj + state.grid_size]
            thermal = new_thermal

        return thermal


class DRCChecker:
    """Fast DRC checking for RL reward computation."""

    def __init__(self, min_clearance: int = 2, min_trace_width: int = 1):
        self.min_clearance = min_clearance  # grid cells
        self.min_trace_width = min_trace_width

    def check(self, state: PCBState) -> int:
        """Count DRC violations. Returns violation count."""
        violations = 0

        # Check trace-to-trace clearance
        trace_map = state.grid[1]  # Routed traces channel
        obstacle_map = state.grid[0]  # Obstacles

        # Trace overlapping obstacles
        overlap = trace_map * obstacle_map
        violations += int(np.sum(overlap > 0))

        # Clearance violations (simplified)
        from scipy.ndimage import binary_dilation
        try:
            struct = np.ones((self.min_clearance * 2 + 1, self.min_clearance * 2 + 1))
            dilated_obstacles = binary_dilation(obstacle_map > 0, structure=struct)
            clearance_violations = trace_map * dilated_obstacles
            violations += int(np.sum(clearance_violations > 0))
        except ImportError:
            # scipy not available, skip clearance check
            pass

        return violations


class PhysicsReward:
    """
    Multi-objective physics-informed reward for PCB routing RL.
    Combines geometric (wirelength, vias) and physics (SI, thermal) objectives.
    """

    def __init__(
        self,
        fdtd_config: dict = None,
        thermal_config: dict = None,
        weights: dict = None,
    ):
        self.fdtd = FDTDEmulator(fdtd_config)
        self.thermal = ThermalSimulator(thermal_config)
        self.drc = DRCChecker()

        self.weights = weights or {
            "wirelength": 0.30,
            "via_count": 0.15,
            "drc_violations": 0.25,
            "crosstalk": 0.15,
            "thermal": 0.10,
            "impedance": 0.05,
        }

    def compute_reward(self, state: PCBState) -> tuple[float, dict]:
        """Compute comprehensive multi-objective reward."""

        # 1. Wirelength (HPWL)
        wirelength = sum(
            (n.bounding_box()["width"] + n.bounding_box()["height"])
            for n in state.nets if n.is_routed
        )
        r_wirelength = -self.weights["wirelength"] * wirelength * 0.01

        # 2. Via count
        via_count = len(state.vias)
        r_vias = -self.weights["via_count"] * via_count

        # 3. DRC violations
        drc_violations = self.drc.check(state)
        r_drc = -self.weights["drc_violations"] * drc_violations * 10

        # 4. Crosstalk
        crosstalk = self.fdtd.compute_crosstalk(state)
        r_crosstalk = -self.weights["crosstalk"] * float(np.sum(crosstalk)) * 100

        # 5. Thermal
        thermal_score = self.thermal.evaluate(state)
        r_thermal = self.weights["thermal"] * thermal_score * 10

        # 6. Impedance matching
        impedance_penalty = self._compute_impedance_penalty(state)
        r_impedance = -self.weights["impedance"] * impedance_penalty

        # Completion bonus
        completion_bonus = 100.0 if state.is_complete() else 0.0
        partial_bonus = state.get_routed_fraction() * 20.0

        total = (
            r_wirelength + r_vias + r_drc + r_crosstalk
            + r_thermal + r_impedance + completion_bonus + partial_bonus
        )

        breakdown = {
            "wirelength": r_wirelength,
            "vias": r_vias,
            "drc": r_drc,
            "crosstalk": r_crosstalk,
            "thermal": r_thermal,
            "impedance": r_impedance,
            "completion": completion_bonus,
            "partial": partial_bonus,
            "total": total,
        }

        return total, breakdown

    def _compute_impedance_penalty(self, state: PCBState) -> float:
        """Compute impedance mismatch penalty for high-speed nets."""
        penalty = 0.0
        for net in state.nets:
            if net.is_high_speed and net.is_routed:
                target_z = net.target_impedance
                # Simplified impedance estimate from trace geometry
                actual_z = self._estimate_impedance(net, state)
                mismatch = abs(actual_z - target_z) / target_z
                penalty += mismatch ** 2
        return penalty

    def _estimate_impedance(self, net: Net, state: PCBState) -> float:
        """Estimate trace impedance using microstrip model."""
        # Simplified microstrip impedance formula
        # Z0 ≈ (87 / √(εr + 1.41)) * ln(5.98h / (0.8w + t))
        h = 0.2  # dielectric height in mm (typical inner layer)
        w = 0.15  # trace width in mm
        t = 0.035  # copper thickness in mm
        er = 4.5  # FR4

        z0 = (87.0 / np.sqrt(er + 1.41)) * np.log(5.98 * h / (0.8 * w + t))
        return max(20.0, min(150.0, z0))  # Clamp to reasonable range
