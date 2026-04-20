"""
PCB Builder - Training Pipeline
Orchestrates RL + LLM training for XgenPCB.
"""

import argparse
import json
import time
from pathlib import Path

from environment import PCBRoutingEnv, RoutingConfig, train_agent
from agent import RoutingAgent, DQNConfig, make_agent
from dataset import generate_dataset, generate_llm_finetuning_dataset, export_for_finetuning


def train_routing_agent(
    num_episodes: int = 5000,
    eval_freq: int = 100,
    save_path: str = "models/routing_agent.pt",
):
    """Train the RL routing agent."""
    # Create environment and config
    config = RoutingConfig(
        grid_size=64,  # Smaller for faster training
        num_layers=4,
        max_steps_per_net=200,
        max_total_steps=5000,
    )
    env = PCBRoutingEnv(config)

    # Create agent
    agent_config = DQNConfig(
        grid_size=config.grid_size,
        state_channels=6,
        action_dim=6,
        learning_rate=1e-4,
        gamma=0.99,
        target_update_freq=500,
        replay_buffer_size=50000,
        batch_size=32,
    )
    agent = make_agent(agent_config)

    # Train
    print(f"🧠 Training RL agent for {num_episodes} episodes...")
    history = train_agent(
        env,
        agent,
        num_episodes=num_episodes,
        max_steps=config.max_total_steps,
        eval_freq=eval_freq,
        eval_episodes=5,
        save_path=save_path,
    )

    return history


def prepare_datasets(num_samples: int = 1000):
    """Generate training datasets."""
    print(f"📊 Generating {num_samples} routing examples...")
    from dataset import PCBDatasetConfig
    config = PCBDatasetConfig(num_samples=num_samples)
    dataset = generate_dataset(config, Path("data/pcb_routing_dataset.json"))

    print(f"📊 Generating LLM fine-tuning examples...")
    llm_examples = generate_llm_finetuning_dataset(num_samples)
    export_for_finetuning(llm_examples, Path("data/pcb_llm_dataset.json"))

    print(f"✅ Generated dataset: {len(dataset)} routing, {len(llm_examples)} LLM examples")


def build_knowledge_base():
    """Build RAG knowledge base."""
    print("📚 Building RAG knowledge base...")
    from rag import make_rag_knowledge_base
    kb = make_rag_knowledge_base()
    print(f"Knowledge base ready with {len(kb.knowledge)} entries")


def full_pipeline(args):
    """Run the complete training pipeline."""
    print("🚀 XgenPCB Full Training Pipeline")
    print("=" * 50)

    start_time = time.time()

    # Step 1: Generate datasets
    if args.prepare_data:
        prepare_datasets(args.num_samples)

    # Step 2: Build knowledge base
    if args.build_rag:
        build_knowledge_base()

    # Step 3: Train RL agent
    if args.train_rl:
        train_routing_agent(
            num_episodes=args.episodes,
            save_path=args.save_path,
        )

    elapsed = time.time() - start_time
    print("=" * 50)
    print(f"✅ Pipeline complete in {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XgenPCB Training Pipeline")

    parser.add_argument("--prepare-data", action="store_true", help="Generate training datasets")
    parser.add_argument("--build-rag", action="store_true", help="Build RAG knowledge base")
    parser.add_argument("--train-rl", action="store_true", help="Train RL routing agent")

    parser.add_argument("--num-samples", type=int, default=1000, help="Number of samples to generate")
    parser.add_argument("--episodes", type=int, default=5000, help="Number of training episodes")
    parser.add_argument("--save-path", type=str, default="models/routing_agent.pt", help="Model save path")

    # Parse
    args = parser.parse_args()

    # If no flags, run full pipeline
    if not any([args.prepare_data, args.build_rag, args.train_rl]):
        print("No pipeline step specified, running all...")
        full_pipeline(parser.parse_args(["--prepare-data", "--build-rag", "--train-rl"]))
    else:
        full_pipeline(args)