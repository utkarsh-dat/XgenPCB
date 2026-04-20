"""
PCB Builder - Dueling Double DQN Agent
Research-backed implementation for PCB routing.

References:
- Dueling Double DQN: arxiv:1511.06581
- Deep Q-Learning from demonstrations
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import random
from collections import deque
import copy


@dataclass
class DQNConfig:
    """Configuration for DQN agent."""
    state_channels: int = 6
    grid_size: int = 128
    action_dim: int = 6

    # Network
    hidden_dim: int = 512
    num_hidden: int = 3

    # Training
    learning_rate: float = 1e-4
    gamma: float = 0.99
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay: float = 1e-5
    target_update_freq: int = 1000
    replay_buffer_size: int = 100000
    batch_size: int = 64
    min_replay_size: int = 1000

    # Double DQN
    use_double_dqn: bool = True

    # Prioritized replay
    use_prioritized_replay: bool = True
    alpha: float = 0.6
    beta_start: float = 0.4
    beta_frames: int = 100000


class ReplayBuffer:
    """Prioritized replay buffer for DQN."""

    def __init__(self, capacity: int, alpha: float = 0.6):
        self.capacity = capacity
        self.alpha = alpha
        self.buffer = deque(maxlen=capacity)
        self.priorities = deque(maxlen=capacity)
        self.priorities_sum = 0.0

    def push(self, state, action, reward, next_state, done):
        """Add experience to buffer."""
        max_priority = max(self.priorities) if self.priorities else 1.0
        self.buffer.append((state, action, reward, next_state, done))
        self.priorities.append(max_priority)
        self.priorities_sum += max_priority

    def sample(self, batch_size: int, beta: float = 0.4):
        """Sample batch with prioritized experience."""
        if len(self.buffer) < batch_size:
            return None

        # Compute sampling probabilities
        probs = np.array(list(self.priorities)[:len(self.buffer)])
        probs = probs ** self.alpha
        probs = probs / probs.sum()

        # Sample indices
        indices = np.random.choice(len(self.buffer), batch_size, p=probs, replace=False)

        # Compute importance sampling weights
        weights = (len(self.buffer) * probs[indices]) ** (-beta)
        weights = weights / weights.max()

        batch = [self.buffer[i] for i in indices]
        states, actions, rewards, next_states, dones = zip(*batch)

        return (
            np.array(states),
            np.array(actions),
            np.array(rewards),
            np.array(next_states),
            np.array(dones),
            weights,
            indices,
        )

    def update_priorities(self, indices, priorities):
        """Update priorities after training."""
        for i, p in zip(indices, priorities):
            self.priorities[i] = p + 1e-5
            self.priorities_sum += p - self.priorities[i - len(indices)]

    def __len__(self):
        return len(self.buffer)


class DuelingDQN(nn.Module):
    """
    Dueling Double DQN with dueling architecture:
    Q(s,a) = V(s) + A(s,a) - mean(A(s,*))

    Separates value and advantage streams.
    """

    def __init__(self, config: DQNConfig):
        super().__init__()
        self.config = config

        # Convolutional backbone
        self.conv1 = nn.Conv2d(config.state_channels, 32, 8, stride=4)
        self.conv2 = nn.Conv2d(32, 64, 4, stride=2)
        self.conv3 = nn.Conv2d(64, 64, 3, stride=1)

        # Calculate conv output size
        self.conv_out_size = self._get_conv_out_size(config)

        # Shared fully connected
        self.fc = nn.Sequential(
            nn.Linear(self.conv_out_size, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, config.hidden_dim),
            nn.ReLU(),
        )

        # Value stream: V(s)
        self.value_stream = nn.Sequential(
            nn.Linear(config.hidden_dim, config.hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(config.hidden_dim // 2, 1),
        )

        # Advantage stream: A(s,a)
        self.advantage_stream = nn.Sequential(
            nn.Linear(config.hidden_dim, config.hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(config.hidden_dim // 2, config.action_dim),
        )

    def _get_conv_out_size(self, config: DQNConfig) -> int:
        """Calculate output size of conv layers."""
        with torch.no_grad():
            x = torch.zeros(1, config.state_channels, config.grid_size, config.grid_size)
            x = F.relu(self.conv1(x))
            x = F.relu(self.conv2(x))
            x = F.relu(self.conv3(x))
            return x.flatten(1).shape[1]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass with dueling architecture.
        Q(s,a) = V(s) + A(s,a) - mean(A(s,*))
        """
        # Convolutional features
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = x.view(x.size(0), -1)

        # Shared features
        shared = self.fc(x)

        # Value and advantage
        value = self.value_stream(shared)
        advantage = self.advantage_stream(shared)

        # Dueling: Q = V + A - mean(A)
        q_values = value + advantage - advantage.mean(dim=1, keepdim=True)
        return q_values

    def get_value(self, x: torch.Tensor) -> torch.Tensor:
        """Get V(s) without computing full forward pass."""
        with torch.no_grad():
            x = F.relu(self.conv1(x))
            x = F.relu(self.conv2(x))
            x = F.relu(self.conv3(x))
            x = x.view(x.size(0), -1)
            shared = self.fc(x)
            return self.value_stream(shared)

    def get_q_values(self, x: torch.Tensor) -> torch.Tensor:
        """Get all Q values for a state."""
        return self.forward(x)


class DQNReplayBuffer:
    """Standard replay buffer (fallback)."""

    def __init__(self, capacity: int):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int):
        if len(self.buffer) < batch_size:
            return None

        indices = random.sample(range(len(self.buffer)), batch_size)
        batch = [self.buffer[i] for i in indices]
        states, actions, rewards, next_states, dones = zip(*batch)

        return (
            np.array(states),
            np.array(actions),
            np.array(rewards),
            np.array(next_states),
            np.array(dones),
        )

    def __len__(self):
        return len(self.buffer)


class RoutingAgent:
    """
    Dueling Double DQN agent for PCB routing.

    Features:
    - Dueling architecture for better value estimation
    - Double DQN for reduced overestimation
    - Prioritized experience replay
    - Target network for stable training
    """

    def __init__(self, config: DQNConfig = None):
        self.config = config or DQNConfig()

        # Initialize networks
        self.policy_net = DuelingDQN(self.config)
        self.target_net = DuelingDQN(self.config)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        # Optimizer
        self.optimizer = optim.Adam(
            self.policy_net.parameters(),
            lr=self.config.learning_rate,
        )

        # Replay buffer
        if self.config.use_prioritized_replay:
            self.replay_buffer = ReplayBuffer(
                self.config.replay_buffer_size,
                self.config.alpha,
            )
        else:
            self.replay_buffer = DQNReplayBuffer(self.config.replay_buffer_size)

        # Training state
        self.steps_done = 0
        self.episode_count = 0
        self.train_count = 0

        # Epsilon for exploration
        self.epsilon = self.config.epsilon_start
        self.beta = self.config.beta_start

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """Select action using epsilon-greedy policy."""
        if training and random.random() < self.epsilon:
            return random.randint(0, self.config.action_dim - 1)

        with torch.no_grad():
            state_tensor = torch.from_numpy(state).float().unsqueeze(0)
            q_values = self.policy_net.get_q_values(state_tensor)
            return q_values.argmax(dim=1).item()

    def select_eval_action(self, state: np.ndarray) -> int:
        """Select action greedily (for evaluation)."""
        return self.select_action(state, training=False)

    def store_transition(self, state, action, reward, next_state, done):
        """Store transition in replay buffer."""
        self.replay_buffer.push(state, action, reward, next_state, done)

    def train_step(self) -> Optional[float]:
        """Perform one training step."""
        # Check if enough samples
        if len(self.replay_buffer) < self.config.min_replay_size:
            return None

        # Sample batch
        if isinstance(self.replay_buffer, ReplayBuffer):
            batch = self.replay_buffer.sample(self.config.batch_size, self.beta)
            if batch is None:
                return None
            states, actions, rewards, next_states, dones, weights, indices = batch
            weights = torch.from_numpy(weights).float().unsqueeze(1)
            indices = indices
        else:
            batch = self.replay_buffer.sample(self.config.batch_size)
            if batch is None:
                return None
            states, actions, rewards, next_states, dones = batch
            weights = None
            indices = None

        # Convert to tensors
        states = torch.from_numpy(states).float()
        actions = torch.from_numpy(actions).long().unsqueeze(1)
        rewards = torch.from_numpy(rewards).float().unsqueeze(1)
        next_states = torch.from_numpy(next_states).float()
        dones = torch.from_numpy(dones).float().unsqueeze(1)

        # Compute current Q values
        current_q = self.policy_net(states).gather(1, actions)

        # Double DQN: use policy net to select, target net to evaluate
        with torch.no_grad():
            if self.config.use_double_dqn:
                # Policy net selects best action
                next_actions = self.policy_net(next_states).argmax(dim=1, keepdim=True)
                # Target net evaluates
                next_q = self.target_net(next_states).gather(1, next_actions)
            else:
                # Standard DQN
                next_q = self.target_net(next_states).max(dim=1, keepdim=True)[0]

            # Bellman equation
            target_q = rewards + self.config.gamma * (1 - dones) * next_q

        # Compute loss
        if weights is not None:
            # Prioritized replay loss
            td_errors = (current_q - target_q).abs()
            loss = (weights * td_errors ** 2).mean()
        else:
            loss = F.mse_loss(current_q, target_q)

        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()

        # Update priorities
        if indices is not None and isinstance(self.replay_buffer, ReplayBuffer):
            priorities = td_errors.squeeze().detach().cpu().numpy()
            self.replay_buffer.update_priorities(indices, priorities)

        # Update target network
        if self.steps_done % self.config.target_update_freq == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())

        # Decay epsilon
        self.epsilon = max(
            self.config.epsilon_end,
            self.epsilon - self.config.epsilon_decay,
        )

        # Increase beta for prioritized replay
        self.beta = min(
            1.0,
            self.beta + self.config.beta_frames ** -1,
        )

        self.train_count += 1
        return loss.item()

    def update_target(self):
        """Manually update target network."""
        self.target_net.load_state_dict(self.policy_net.state_dict())

    def save(self, path: str):
        """Save model weights."""
        torch.save({
            "policy_net": self.policy_net.state_dict(),
            "target_net": self.target_net.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "steps": self.steps_done,
            "epsilon": self.epsilon,
        }, path)

    def load(self, path: str):
        """Load model weights."""
        checkpoint = torch.load(path)
        self.policy_net.load_state_dict(checkpoint["policy_net"])
        self.target_net.load_state_dict(checkpoint["target_net"])
        self.optimizer.load_state_dict(checkpoint["optimizer"])
        self.steps_done = checkpoint["steps"]
        self.epsilon = checkpoint["epsilon"]


def train_agent(
    env,
    agent: RoutingAgent,
    num_episodes: int = 1000,
    max_steps: int = 10000,
    eval_freq: int = 100,
    eval_episodes: int = 10,
    save_path: str = "models/routing_agent.pt",
) -> dict:
    """
    Train the DQN agent on the PCB routing environment.
    """
    history = {
        "episode_rewards": [],
        "episode_lengths": [],
        "train_losses": [],
        "eval_scores": [],
    }

    best_score = float("-inf")

    for episode in range(num_episodes):
        state = env.reset()
        episode_reward = 0
        episode_length = 0

        for step in range(max_steps):
            # Select action
            action = agent.select_action(state)

            # Take action
            next_state, reward, done, info = env.step(action)

            # Store transition
            agent.store_transition(state, action, reward, next_state, done)

            # Train
            loss = agent.train_step()
            if loss is not None:
                history["train_losses"].append(loss)

            state = next_state
            episode_reward += reward
            episode_length += 1
            agent.steps_done += 1

            if done:
                break

        agent.episode_count += 1
        history["episode_rewards"].append(episode_reward)
        history["episode_lengths"].append(episode_length)

        # Evaluate
        if episode % eval_freq == 0:
            eval_scores = []
            for _ in range(eval_episodes):
                eval_state = env.reset()
                eval_reward = 0
                for _ in range(max_steps):
                    action = agent.select_eval_action(eval_state)
                    eval_state, reward, done, _ = env.step(action)
                    eval_reward += reward
                    if done:
                        break
                eval_scores.append(eval_reward)

            avg_score = np.mean(eval_scores)
            history["eval_scores"].append(avg_score)

            if avg_score > best_score:
                best_score = avg_score
                agent.save(save_path)

            print(f"Episode {episode}: train_reward={episode_reward:.1f}, eval_score={avg_score:.1f}, epsilon={agent.epsilon:.3f}")

    return history


# Convenience function to create agent
def make_agent(config: DQNConfig = None) -> RoutingAgent:
    """Create a new routing agent."""
    return RoutingAgent(config)