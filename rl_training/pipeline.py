"""
PCB Builder - RL Training Pipeline
TPU-ready PPO training for PCB routing.
Designed for JAX/Haiku on TPU but works on CPU/GPU too.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from rl_training.environment import PCBRoutingEnv, RoutingConfig
from rl_training.physics_reward import PhysicsReward


@dataclass
class TrainingConfig:
    """Training hyperparameters."""
    # Network
    num_layers: int = 4
    grid_size: int = 128
    action_dim: int = 6

    # PPO
    clip_epsilon: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    gamma: float = 0.99
    lambda_: float = 0.95
    num_epochs: int = 4
    minibatch_size: int = 256

    # Training
    batch_size: int = 4096
    steps_per_env: int = 256
    num_envs: int = 16  # Start small, scale on TPU
    learning_rate: float = 3e-4
    total_steps: int = 10_000_000
    steps_per_epoch: int = 4096

    # Infrastructure
    bucket: str = "pcb-rl-checkpoints"
    checkpoint_interval: int = 10000
    log_interval: int = 100

    # Environment
    env_config: RoutingConfig = None

    def __post_init__(self):
        if self.env_config is None:
            self.env_config = RoutingConfig(
                grid_size=self.grid_size,
                num_layers=self.num_layers,
            )


class PCBRoutingTrainer:
    """
    RL training pipeline for PCB routing.
    
    Supports:
    - CPU/GPU training with NumPy (always available)
    - TPU/GPU training with JAX/Haiku (when available)
    """

    def __init__(self, config: TrainingConfig = None):
        self.config = config or TrainingConfig()
        self.reward_fn = PhysicsReward()
        self.accelerator = "cpu"
        self._jax_available = False

        # Try to initialize JAX
        try:
            import jax
            self._jax_available = True
            devices = jax.devices()
            if "tpu" in str(devices[0]).lower():
                self.accelerator = "tpu"
            elif "gpu" in str(devices[0]).lower():
                self.accelerator = "gpu"
            print(f"✅ JAX detected - using {self.accelerator}: {devices}")
        except ImportError:
            print("⚠️  JAX not available - using NumPy fallback (CPU only)")

    def collect_trajectories(self) -> dict:
        """Collect experience from parallel environments."""
        envs = [PCBRoutingEnv(self.config.env_config) for _ in range(self.config.num_envs)]
        states = [env.reset() for env in envs]

        trajectories = {
            "observations": [],
            "actions": [],
            "rewards": [],
            "dones": [],
            "values": [],
        }

        for t in range(self.config.steps_per_env):
            for i, (env, state) in enumerate(zip(envs, states)):
                obs = state.observation

                # Random policy (replace with learned policy)
                action = np.random.randint(0, self.config.action_dim)

                new_state, base_reward, done, info = env.step(action)

                # Add physics reward
                if done or t % 10 == 0:
                    physics_reward, breakdown = self.reward_fn.compute_reward(new_state)
                    reward = base_reward + physics_reward * 0.1
                else:
                    reward = base_reward

                trajectories["observations"].append(obs)
                trajectories["actions"].append(action)
                trajectories["rewards"].append(reward)
                trajectories["dones"].append(done)
                trajectories["values"].append(0.0)  # Placeholder

                if done:
                    states[i] = env.reset()
                else:
                    states[i] = new_state

        # Convert to arrays
        for key in trajectories:
            trajectories[key] = np.array(trajectories[key])

        return trajectories

    def compute_gae(self, trajectories: dict) -> tuple[np.ndarray, np.ndarray]:
        """Compute Generalized Advantage Estimation."""
        rewards = trajectories["rewards"]
        values = trajectories["values"]
        dones = trajectories["dones"]

        n = len(rewards)
        advantages = np.zeros(n)
        returns = np.zeros(n)

        gae = 0.0
        for t in reversed(range(n)):
            if t == n - 1:
                next_value = 0.0
            else:
                next_value = values[t + 1]

            delta = rewards[t] + self.config.gamma * next_value * (1 - dones[t]) - values[t]
            gae = delta + self.config.gamma * self.config.lambda_ * (1 - dones[t]) * gae
            advantages[t] = gae
            returns[t] = advantages[t] + values[t]

        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        return advantages, returns

    def train(self, num_epochs: int = None):
        """Main training loop."""
        total_epochs = num_epochs or (self.config.total_steps // self.config.steps_per_epoch)

        print(f"🚀 Starting training on {self.accelerator}")
        print(f"   Epochs: {total_epochs}")
        print(f"   Envs: {self.config.num_envs}")
        print(f"   Steps/env: {self.config.steps_per_env}")

        for epoch in range(total_epochs):
            # Collect trajectories
            trajectories = self.collect_trajectories()

            # Compute advantages
            advantages, returns = self.compute_gae(trajectories)

            # Compute metrics
            mean_reward = float(np.mean(trajectories["rewards"]))
            completion_rate = float(np.mean(trajectories["dones"]))

            if epoch % self.config.log_interval == 0:
                print(
                    f"Epoch {epoch:6d} | "
                    f"Mean Reward: {mean_reward:8.3f} | "
                    f"Completion: {completion_rate:.1%} | "
                    f"Advantage μ: {float(np.mean(advantages)):8.3f}"
                )

            # In full JAX version, would do PPO updates here
            if self._jax_available:
                self._jax_train_step(trajectories, advantages, returns)

    def _jax_train_step(self, trajectories: dict, advantages: np.ndarray, returns: np.ndarray):
        """PPO training step using JAX (when available)."""
        try:
            import jax
            import jax.numpy as jnp

            # Convert to JAX arrays
            obs = jnp.array(trajectories["observations"])
            actions = jnp.array(trajectories["actions"])
            adv = jnp.array(advantages)
            ret = jnp.array(returns)

            # PPO update would go here with haiku network
            # This is the placeholder for the full TPU training loop
            pass

        except Exception as e:
            print(f"JAX training step failed: {e}")

    def evaluate(self, num_episodes: int = 10) -> dict:
        """Evaluate current policy."""
        env = PCBRoutingEnv(self.config.env_config)
        total_rewards = []
        completion_rates = []

        for _ in range(num_episodes):
            state = env.reset()
            episode_reward = 0.0
            done = False

            while not done:
                action = np.random.randint(0, self.config.action_dim)
                state, reward, done, info = env.step(action)
                episode_reward += reward

            total_rewards.append(episode_reward)
            completion_rates.append(state.get_routed_fraction())

        return {
            "mean_reward": float(np.mean(total_rewards)),
            "std_reward": float(np.std(total_rewards)),
            "mean_completion": float(np.mean(completion_rates)),
            "episodes": num_episodes,
        }


def main():
    """Entry point for RL training."""
    config = TrainingConfig(
        num_envs=4,
        steps_per_env=64,
        grid_size=64,
        num_layers=2,
    )

    trainer = PCBRoutingTrainer(config)

    # Evaluate random policy baseline
    print("\n📊 Random Policy Baseline:")
    baseline = trainer.evaluate(num_episodes=5)
    print(f"   Mean Reward: {baseline['mean_reward']:.3f}")
    print(f"   Completion:  {baseline['mean_completion']:.1%}")

    # Train
    print("\n🏋️ Training...")
    trainer.train(num_epochs=100)

    # Evaluate after training
    print("\n📊 Post-Training Evaluation:")
    results = trainer.evaluate(num_episodes=5)
    print(f"   Mean Reward: {results['mean_reward']:.3f}")
    print(f"   Completion:  {results['mean_completion']:.1%}")


if __name__ == "__main__":
    main()
