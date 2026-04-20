"""
PCB Builder - QLoRA Fine-tuning Pipeline
Domain adaptation for PCB design LLMs using QLoRA.
Based on: QLoRA (arxiv:2305.14314), PCB-Bench (ICLR 2026)
"""

import json
import torch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, list
from dataclasses import dataclass
from typing import Optional

# Check for transformers
try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
        HfArgumentParser,
    )
    from peft import LoraConfig, get_peft_model, TaskType
    from datasets import Dataset
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


@dataclass
class FinetuneConfig:
    """Configuration for QLoRA fine-tuning."""

    # Model
    base_model: str = "meta-llama/Llama-3.1-8B-Instruct"
    model_name: str = "xgenpcb-llama"

    # LoRA
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    target_modules: list = field(default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])

    # Training
    output_dir: str = "models/xgenpcb-lora"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 8
    gradient_accumulation_steps: int = 4
    learning_rate: float = 3e-4
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01

    # Quantization (4-bit)
    load_in_4bit: bool = True
    bnb_4bit_compute_dtype: str = "float16"
    bnb_4bit_quant_type: str = "nf4"

    # Dataset
    train_file: str = "data/pcb_llm_dataset.json"
    max_seq_length: int = 2048

    # Evaluation
    eval_steps: int = 100
    save_steps: int = 500
    logging_steps: int = 50


def setup_lora_model(config: FinetuneConfig):
    """Load model with 4-bit quantization and LoRA."""
    if not TRANSFORMERS_AVAILABLE:
        raise ImportError("transformers, peft, bitsandbytes required. Install: pip install transformers peft bitsandbytes")

    # Load base model with 4-bit quantization
    model = AutoModelForCausalLM.from_pretrained(
        config.base_model,
        load_in_4bit=config.load_in_4bit,
        bnb_4bit_compute_dtype=getattr(torch, config.bnb_4bit_compute_dtype),
        bnb_4bit_quant_type=config.bnb_4bit_quant_type,
        device_map="auto",
    )

    # Configure LoRA
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=config.target_modules,
        bias="none",
    )

    # Apply LoRA
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model


def load_tokenizer(config: FinetuneConfig):
    """Load tokenizer."""
    if not TRANSFORMERS_AVAILABLE:
        raise ImportError("transformers required")

    return AutoTokenizer.from_pretrained(config.base_model)


def prepare_dataset(config: FinetuneConfig):
    """Prepare dataset for training."""
    if not TRANSFORMERS_AVAILABLE:
        raise ImportError("datasets required")

    # Load JSON data
    with open(config.train_file, "r") as f:
        data = json.load(f)

    # Convert to HF Dataset format
    def format_example(example):
        text = f"Instruction: {example['instruction']}\nOutput: {example['output']}"
        return {"text": text}

    dataset = Dataset.from_list(data)
    dataset = dataset.map(format_example)

    # Tokenize
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=config.max_seq_length,
            padding="max_length",
        )

    tokenizer = load_tokenizer(config)
    dataset = dataset.map(tokenize_function, batched=True, remove_columns=dataset.column_names)

    # Split train/eval
    train_size = int(0.9 * len(dataset))
    train_dataset = dataset.select(range(train_size))
    eval_dataset = dataset.select(range(train_size, len(dataset)))

    return train_dataset, eval_dataset


def train(config: FinetuneConfig = None):
    """Run QLoRA fine-tuning."""
    if not TRANSFORMERS_AVAILABLE:
        print("Installing dependencies...")
        import subprocess
        subprocess.run(["pip", "install", "-q", "transformers", "peft", "bitsandbytes", "datasets", "trl"])
        return

    config = config or FinetuneConfig()

    print(f"Loading model: {config.base_model}")
    model = setup_lora_model(config)

    print("Loading tokenizer...")
    tokenizer = load_tokenizer(config)
    tokenizer.pad_token = tokenizer.eos_token

    print("Preparing dataset...")
    train_dataset, eval_dataset = prepare_dataset(config)

    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Causal LM
    )

    # Training arguments
    training_args = TrainingArguments(
        output_dir=config.output_dir,
        num_train_epochs=config.num_train_epochs,
        per_device_train_batch_size=config.per_device_train_batch_size,
        per_device_eval_batch_size=config.per_device_eval_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        warmup_ratio=config.warmup_ratio,
        weight_decay=config.weight_decay,
        evaluation_strategy="steps",
        eval_steps=config.eval_steps,
        save_steps=config.save_steps,
        logging_steps=config.logging_steps,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        fp16=True,
        report_to="none",
    )

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )

    # Train
    print("Starting training...")
    trainer.train()

    # Save
    print(f"Saving model to {config.output_dir}")
    trainer.save_model(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)

    return model


def merge_and_export(config: FinetuneConfig, output_path: str):
    """Merge LoRA weights and export for inference."""
    if not TRANSFORMERS_AVAILABLE:
        raise ImportError("transformers and peft required")

    from peft import PeftModel

    # Load base model
    base_model = AutoModelForCausalLM.from_pretrained(
        config.base_model,
        torch_dtype=torch.float16,
    )

    # Load LoRA
    model = PeftModel.from_pretrained(base_model, config.output_dir)

    # Merge
    merged_model = model.merge_and_unload()

    # Save
    merged_model.save_pretrained(output_path)
    print(f"Merged model saved to {output_path}")


# Standalone inference (no heavy dependencies)
@dataclass
class PCBIntentModel:
    """Lightweight intent parser using domain-adapted model."""

    def __init__(self, model_path: str = "models/xgenpcb-lora"):
        self.model_path = model_path
        self.available = False

        if TRANSFORMERS_AVAILABLE and Path(model_path).exists():
            try:
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    torch_dtype=torch.float16,
                    device_map="auto",
                )
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                self.available = True
            except Exception as e:
                print(f"Failed to load model: {e}")

    def parse_intent(self, user_input: str, design_context: dict = None) -> dict:
        """Parse user intent into structured action."""
        if not self.available:
            # Fallback to rule-based
            return self._rule_based_parse(user_input)

        # Prepare prompt
        context_str = ""
        if design_context:
            context_str = f"\nDesign context: {json.dumps(design_context)}"

        prompt = f"""Instruction: Parse this PCB design request into a structured action.
Request: {user_input}{context_str}
Output: """

        # Generate
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(**inputs, max_new_tokens=256, do_sample=True, temperature=0.1)
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Parse JSON
        try:
            result = json.loads(response.split("Output: ")[-1])
            return result
        except:
            return {"action_type": "unknown", "parameters": {}, "confidence": 0.5}

    def _rule_based_parse(self, user_input: str) -> dict:
        """Fallback rule-based intent parsing."""
        user_lower = user_input.lower()

        if "place" in user_lower or "put" in user_lower:
            return {"action_type": "place_component", "parameters": {}, "confidence": 0.7}
        elif "route" in user_lower:
            return {"action_type": "route_net", "parameters": {}, "confidence": 0.7}
        elif "drc" in user_lower or "check" in user_lower:
            return {"action_type": "run_drc", "parameters": {}, "confidence": 0.9}
        elif "auto-route" in user_lower or "autoroute" in user_lower:
            return {"action_type": "auto_route", "parameters": {}, "confidence": 0.8}
        elif "fix" in user_lower:
            return {"action_type": "fix_violation", "parameters": {}, "confidence": 0.7}
        else:
            return {"action_type": "unknown", "parameters": {}, "confidence": 0.3}


# Main entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="QLoRA fine-tuning for PCB design LLMs")
    parser.add_argument("--base-model", type=str, default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--train-file", type=str, default="data/pcb_llm_dataset.json")
    parser.add_argument("--output-dir", type=str, default="models/xgenpcb-lora")
    parser.add_argument("--num-epochs", type=int, default=3)
    args = parser.parse_args()

    config = FinetuneConfig(
        base_model=args.base_model,
        train_file=args.train_file,
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
    )

    train(config)