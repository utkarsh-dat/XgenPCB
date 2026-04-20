"""
PCB Builder - Synthetic Dataset Generator
Generates PCB routing datasets for training LLMs and RL agents.
Based on research: few-shot PCB routing (Zhang et al. 2025), PCB-Bench (ICLR 2026)
"""

import json
import random
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class PCBDatasetConfig:
    """Configuration for dataset generation."""
    num_samples: int = 1000
    grid_size: int = 128
    num_layers: int = 4
    min_nets: int = 3
    max_nets: int = 15
    min_pins: int = 2
    max_pins: int = 6

    # Electrical properties
    power_net_ratio: float = 0.1
    ground_net_ratio: float = 0.1
    high_speed_ratio: float = 0.15

    # Component density
    min_components: int = 3
    max_components: int = 25

    # Output format
    output_format: str = "json"  # json or huggingface


@dataclass
class RoutingExample:
    """Single routing example for training."""
    example_id: str

    # Input features
    board_config: dict
    components: list[dict]
    nets: list[dict]

    # Target output
    routed_tracks: list[dict]
    vias: list[dict]
    quality_metrics: dict

    # Metadata
    difficulty: str  # easy, medium, hard
    source: str = "synthetic"


def generate_single_routing_example(
    config: PCBDatasetConfig,
    example_id: str,
    seed: Optional[int] = None,
) -> RoutingExample:
    """Generate a single PCB routing example."""
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    grid_size = config.grid_size
    num_layers = config.num_layers
    margin = 10

    # Generate board dimensions
    width = random.choice([80, 100, 120, 150])
    height = random.choice([60, 80, 100, 120])

    board_config = {
        "width_mm": width,
        "height_mm": height,
        "layers": num_layers,
        "thickness_mm": random.choice([1.2, 1.6, 2.0]),
    }

    # Generate components (obstacles)
    num_components = random.randint(config.min_components, config.max_components)
    components = []
    max_coord = grid_size - margin

    for i in range(num_components):
        # Place component avoiding overlap
        for _ in range(100):  # Max attempts
            cx = random.randint(margin, max_coord)
            cy = random.randint(margin, max_coord)
            w = random.randint(2, 8)
            h = random.randint(2, 8)

            # Check overlap
            overlaps = False
            for comp in components:
                x_dist = abs(cx - comp["x"])
                y_dist = abs(cy - comp["y"])
                if x_dist < (w + comp["width"]) // 2 + 2 and y_dist < (h + comp["height"]) // 2 + 2:
                    overlaps = True
                    break

            if not overlaps:
                break

        component = {
            "id": f"C{i}",
            "x": cx,
            "y": cy,
            "width": w,
            "height": h,
            "type": random.choice(["IC", "CAP", "RES", "LED", "CON"]),
        }
        components.append(component)

    # Generate nets
    num_nets = random.randint(config.min_nets, config.max_nets)
    nets = []

    for i in range(num_nets):
        # Determine net type
        if i < num_nets * config.power_net_ratio:
            net_type = "power"
        elif i < num_nets * (config.power_net_ratio + config.ground_net_ratio):
            net_type = "ground"
        elif i < num_nets * (config.power_net_ratio + config.ground_net_ratio + config.high_speed_ratio):
            net_type = "high_speed"
        else:
            net_type = "signal"

        # Generate pins
        num_pins = random.randint(config.min_pins, config.max_pins)
        pins = []

        for j in range(num_pins):
            for _ in range(100):
                px = random.randint(margin, max_coord)
                py = random.randint(margin, max_coord)

                # Check not on component
                on_component = False
                for comp in components:
                    if comp["x"] - comp["width"]//2 <= px <= comp["x"] + comp["width"]//2 and \
                       comp["y"] - comp["height"]//2 <= py <= comp["y"] + comp["height"]//2:
                        on_component = True
                        break

                if not on_component:
                    break

            pins.append({"x": px, "y": py, "layer": 0})

        net = {
            "id": f"N{i}",
            "name": f"NET_{i}",
            "pins": pins,
            "type": net_type,
            "is_high_speed": net_type == "high_speed",
            "is_power": net_type == "power",
            "is_ground": net_type == "ground",
        }
        nets.append(net)

    # Calculate difficulty
    complexity = (num_nets * num_pins) / (width * height) * 1000
    if complexity < 0.3:
        difficulty = "easy"
    elif complexity < 0.7:
        difficulty = "medium"
    else:
        difficulty = "hard"

    # Generate target (simulated routing result)
    # In production, this would come from actual routing or human annotation
    quality_metrics = {
        "wirelength": random.uniform(0.5, 1.0),  # Normalized
        "via_count": random.randint(0, 10),
        " DRC_violations": random.randint(0, 3),
        "completion_rate": random.uniform(0.7, 1.0),
    }

    return RoutingExample(
        example_id=example_id,
        board_config=board_config,
        components=components,
        nets=nets,
        routed_tracks=[],  # Would be filled by actual router
        vias=[],
        quality_metrics=quality_metrics,
        difficulty=difficulty,
    )


def generate_dataset(
    config: PCBDatasetConfig,
    output_path: Optional[Path] = None,
) -> list[RoutingExample]:
    """Generate complete PCB routing dataset."""
    examples = []

    for i in range(config.num_samples):
        example = generate_single_routing_example(
            config,
            f"pcb_{i:05d}",
            seed=config.num_samples + i,
        )
        examples.append(example)

    # Convert to output format
    if config.output_format == "huggingface":
        data = [
            {
                "id": ex.example_id,
                "board_config": ex.board_config,
                "components": json.dumps(ex.components),
                "nets": json.dumps(ex.nets),
                "difficulty": ex.difficulty,
                "quality": ex.quality_metrics,
            }
            for ex in examples
        ]
    else:
        data = [
            {
                "id": ex.example_id,
                "board_config": ex.board_config,
                "components": ex.components,
                "nets": ex.nets,
                "difficulty": ex.difficulty,
                "quality_metrics": ex.quality_metrics,
            }
            for ex in examples
        ]

    # Save if path provided
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    return examples


# Fine-tuning dataset for LLMs
@dataclass
class PCBTextExample:
    """Text-based example for LLM fine-tuning."""
    prompt: str
    response: str
    category: str  # intent_parsing, auto_fix, design_review, routing_suggestion


def generate_llm_finetuning_dataset(
    num_examples: int = 1000,
) -> "list[PCBTextExample]":
    """
    Generate text-based examples for LLM domain adaptation.

    Based on PCB-Bench task formulations.
    """
    examples = []

    # Intent parsing examples
    intent_examples = [
        ("Place the MCU near the USB connector", "place_component", {"component": "MCU", "constraint": "near_USB"}),
        ("Route the 12V power bus on inner layers", "route_net", {"net": "12V_POWER", "layers": [2, 3]}),
        ("Add a 0.1uF decoupling capacitor near each VCC pin", "add_constraint", {"type": "decoupling", "value": "0.1uF"}),
        ("Route the USB differential pair with 2.5mm spacing", "route_net", {"net": "USB_DP", "spacing": 2.5}),
        ("Run DRC check", "run_drc", {}),
        ("Auto-route all remaining nets", "auto_route", {}),
    ]

    for i in range(num_examples // 6):
        for prompt, action, params in intent_examples:
            examples.append(PCBTextExample(
                prompt=f"Design: {prompt}",
                response=json.dumps({
                    "action": action,
                    "parameters": params,
                    "confidence": random.uniform(0.7, 0.99),
                }),
                category="intent_parsing",
            ))

    # Auto-fix examples
    fix_examples = [
        ("Clearance violation between IC U1 and capacitor C5 (0.1mm < 0.2mm minimum)", "move_component", {"id": "C5", "x": "+2mm"}),
        ("Trace width too narrow for 3A current (0.15mm < 0.3mm)", "change_trace_width", {"net": "12V", "width": "0.3mm"}),
        ("Unrouted net NET_42", "route_net", {"net": "NET_42"}),
    ]

    for i in range(num_examples // 6):
        for violation, fix, params in fix_examples:
            examples.append(PCBTextExample(
                prompt=f"Violation: {violation}\nFix this: {fix}",
                response=json.dumps({
                    "operation": fix,
                    "parameters": params,
                    "risk": "low" if random.random() > 0.3 else "medium",
                }),
                category="auto_fix",
            ))

    # Design review examples
    review_questions = [
        "Is the decoupling capacitor placement adequate?",
        "Are high-speed traces properly impedance-matched?",
        "What is the estimated manufacturing cost?",
    ]

    for i in range(num_examples // 6):
        for question in review_questions:
            examples.append(PCBTextExample(
                prompt=f"Design review: {question}",
                response=json.dumps({
                    "finding": "Needs improvement" if random.random() > 0.5 else "Adequate",
                    "score": random.randint(60, 95),
                    "suggestion": "Consider adding more bypass capacitors near the MCU.",
                }),
                category="design_review",
            ))

    random.shuffle(examples)
    return examples


# Export for training
def export_for_finetuning(
    examples: list[PCBTextExample],
    output_path: Path,
    format: str = "alpaca",  # alpaca or sharegpt
):
    """Export examples in LLM fine-tuning format."""
    if format == "alpaca":
        data = [
            {
                "instruction": ex.prompt,
                "output": ex.response,
                "category": ex.category,
            }
            for ex in examples
        ]
    elif format == "sharegpt":
        data = [
            {
                "conversations": [
                    {"from": "human", "value": ex.prompt},
                    {"from": "gpt", "value": ex.response},
                ],
                "category": ex.category,
            }
            for ex in examples
        ]
    else:
        raise ValueError(f"Unknown format: {format}")

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    return data


# Main entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--num-samples", type=int, default=1000)
    parser.add_argument("--output", type=str, default="data/pcb_routing_dataset.json")
    parser.add_argument("--output-llm", type=str, default="data/pcb_llm_dataset.json")
    parser.add_argument("--format", type=str, default="json")
    args = parser.parse_args()

    # Generate routing dataset
    config = PCBDatasetConfig(num_samples=args.num_samples)
    examples = generate_dataset(config, Path(args.output))

    print(f"Generated {len(examples)} routing examples -> {args.output}")

    # Generate LLM fine-tuning dataset
    llm_examples = generate_llm_finetuning_dataset(args.num_samples)
    export_for_finetuning(llm_examples, Path(args.output_llm))

    print(f"Generated {len(llm_examples)} LLM examples -> {args.output_llm}")