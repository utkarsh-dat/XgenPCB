"""
PCB Builder - RAG Knowledge Base
Embeds PCB design knowledge for domain-aware AI responses.
Based on: RAG Enhancement (PCB-Bench, ICLR 2026)
"""

import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

# Check for sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    SEGMENTERS_AVAILABLE = True
except ImportError:
    SEGMENTERS_AVAILABLE = False


@dataclass
class PCBKnowledge:
    """Single knowledge entry."""
    id: str
    content: str
    category: str  # placement, routing, dcr, component, manufacturing
    metadata: dict = field(default_factory=dict)


# Default knowledge base
DEFAULT_KNOWLEDGE = [
    # Placement Rules
    {
        "content": "Place decoupling capacitors (0.1uF) as close as possible to each VCC pin of ICs, preferably within 2mm",
        "category": "placement",
    },
    {
        "content": "For multi-layer PCBs, place ground plane on layer adjacent to signal layers for better return path",
        "category": "placement",
    },
    {
        "content": "Place high-frequency components (crystals, oscillators) away from noisy traces and power supply sections",
        "category": "placement",
    },
    {
        "content": "Arrange components to minimize current return path length for high-speed signals",
        "category": "placement",
    },
    {
        "content": "Leave at least 2mm clearance around board edges for V-cut or邮票分割",
        "category": "placement",
    },

    # Routing Rules
    {
        "content": "High-speed differential pairs (USB, HDMI, PCIe) require 90 ohm characteristic impedance, maintain consistent spacing",
        "category": "routing",
    },
    {
        "content": "Keep trace lengths matched for differential pairs within 150mil (3.81mm) for 1Gbps, tighter for higher speeds",
        "category": "routing",
    },
    {
        "content": "Avoid 90-degree angle corners in high-speed traces; use 45-degree or rounded corners instead",
        "category": "routing",
    },
    {
        "content": "Minimum trace width for 1oz copper: 0.15mm for signal, 0.3mm for power, 0.5mm+ for high-current",
        "category": "routing",
    },
    {
        "content": "Maintain 2W rule for traces: 2mil (0.05mm) width per 1A current for 1oz copper, 10°C rise",
        "category": "routing",
    },
    {
        "content": "Route power and ground as fills or polygon pours for better current capacity and thermal management",
        "category": "routing",
    },
    {
        "content": "Separate analog and digital grounds; connect at single point near ADC reference",
        "category": "routing",
    },

    # DRC Rules
    {
        "content": "Minimum clearance: 0.15mm for standard, 0.2mm forfine-pitch, 0.3mm for high-voltage",
        "category": "drc",
    },
    {
        "content": "Via-to-via clearance: minimum 0.2mm or via drill size, whichever is larger",
        "category": "drc",
    },
    {
        "content": "Ensure solder mask bridge: minimum 0.15mm between pads",
        "category": "dcr",
    },
    {
        "content": "Silkscreen should not overlap pads, maintain 0.15mm clearance",
        "category": "dcr",
    },

    # Component Rules
    {
        "content": "0603 and 0402 capacitors are preferred over 0201 for hand assembly; 0201 best for high-density designs",
        "category": "component",
    },
    {
        "content": "Use Murphy's ratio: at least 1uF per 1000 uF of input capacitance for decoupling",
        "category": "component",
    },
    {
        "content": "ESR of decoupling capacitor should be << than source impedance at switching frequency",
        "category": "component",
    },
    {
        "content": "Use X7R or C0G/NP0 capacitors for decoupling; avoid Y5V, Z5U for precision circuits",
        "category": "component",
    },

    # Manufacturing
    {
        "content": "Standard PCB tolerances: +/- 0.2mm for dimensions, +/- 0.1mm for hole positions",
        "category": "manufacturing",
    },
    {
        "content": "Minimum trace width/spacing: 0.15mm for standard, 0.1mm for advanced, 0.075mm for dife",
        "category": "manufacturing",
    },
    {
        "content": "Standard layer stackups: 2-layer (IPC-4101E), 4-layer (IPC-4101C), 6-layer (IPC-4101D)",
        "category": "manufacturing",
    },
    {
        "content": " castellated edges cost extra but enable module-on-module stacking",
        "category": "manufacturing",
    },
    {
        "content": "For ENIG finish: minimum 2 microinches gold over 120 microinches nickel",
        "category": "manufacturing",
    },
]


class RAGKnowledgeBase:
    """
    Retrieval-augmented generation for PCB design knowledge.

    Uses FAISS for efficient similarity search.
    """

    def __init__(
        self,
        embedding_model: str = "BAAI/bge-small-en-v1.5",
        knowledge_path: Optional[Path] = None,
    ):
        self.embedding_model_name = embedding_model
        self.index = None
        self.knowledge: list[PCBKnowledge] = []
        self.ids: list[str] = []

        if SEGMENTERS_AVAILABLE:
            # Load embedding model
            self.model = SentenceTransformer(embedding_model)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
        else:
            self.model = None
            self.embedding_dim = 384  # Default for bge-small

        # Load knowledge
        if knowledge_path and knowledge_path.exists():
            self.load(knowledge_path)
        else:
            self._load_default_knowledge()

        # Build index
        self._build_index()

    def _load_default_knowledge(self):
        """Load default PCB design knowledge."""
        for i, entry in enumerate(DEFAULT_KNOWLEDGE):
            self.knowledge.append(PCBKnowledge(
                id=f"kb_{i:03d}",
                content=entry["content"],
                category=entry.get("category", "general"),
                metadata=entry,
            ))
            self.ids.append(f"kb_{i:03d}")

    def _build_index(self):
        """Build FAISS index."""
        if not self.model:
            print("Warning: sentence-transformers not available, using fake embeddings")
            return

        # Encode all knowledge
        texts = [k.content for k in self.knowledge]
        embeddings = self.model.encode(texts, show_progress_bar=True)

        # Build FAISS index
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index.add(embeddings.astype(np.float32))

        print(f"Built RAG index with {len(self.knowledge)} entries")

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
    ) -> list[PCBKnowledge]:
        """Retrieve relevant knowledge for query."""
        if not self.model or self.index is None:
            # Fallback: return all
            results = self.knowledge
            return results[:top_k] if category is None else [
                k for k in results if k.category == category
            ][:top_k]

        # Encode query
        query_embedding = self.model.encode([query]).astype(np.float32)

        # Search
        distances, indices = self.index.search(query_embedding, top_k * 2)  # Extra for filtering

        # Filter by category
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.knowledge):
                entry = self.knowledge[idx]
                if category is None or entry.category == category:
                    results.append((entry, dist))
            if len(results) >= top_k:
                break

        return [r[0] for r in results]

    def get_context(self, query: str, max_length: int = 1000) -> str:
        """Get formatted context for query."""
        retrieved = self.retrieve(query)

        context_parts = []
        current_length = 0

        for knowledge in retrieved:
            if current_length + len(knowledge.content) > max_length:
                break
            context_parts.append(knowledge.content)
            current_length += len(knowledge.content) + 2

        return " ".join(context_parts)

    def add_knowledge(self, content: str, category: str, metadata: dict = None):
        """Add new knowledge entry."""
        knowledge_id = f"kb_{len(self.knowledge):03d}"
        entry = PCBKnowledge(
            id=knowledge_id,
            content=content,
            category=category,
            metadata=metadata or {},
        )
        self.knowledge.append(entry)
        self.ids.append(knowledge_id)

        # Rebuild index
        self._build_index()

    def save(self, path: Path):
        """Save knowledge base."""
        data = [
            {
                "id": k.id,
                "content": k.content,
                "category": k.category,
                "metadata": k.metadata,
            }
            for k in self.knowledge
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: Path):
        """Load knowledge base."""
        with open(path, "r") as f:
            data = json.load(f)

        self.knowledge = [
            PCBKnowledge(
                id=entry["id"],
                content=entry["content"],
                category=entry["category"],
                metadata=entry.get("metadata", {}),
            )
            for entry in data
        ]
        self.ids = [k.id for k in self.knowledge]


# Convenience function
def make_rag_knowledge_base(
    embedding_model: str = "BAAI/bge-small-en-v1.5",
    knowledge_file: Optional[Path] = None,
) -> RAGKnowledgeBase:
    """Create RAG knowledge base."""
    return RAGKnowledgeBase(embedding_model, knowledge_file)


# Integration with AI service
def enhance_prompt_with_rag(
    base_prompt: str,
    query_context: str,
    knowledge_base: RAGKnowledgeBase,
    max_context_length: int = 500,
) -> str:
    """Enhance prompt with RAG context."""
    rag_context = knowledge_base.get_context(query_context, max_context_length)

    if not rag_context:
        return base_prompt

    enhanced = f"""{base_prompt}

PCB Design Knowledge:
{rag_context}
"""
    return enhanced


# Main entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RAG knowledge base for PCB design")
    parser.add_argument("--model", type=str, default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--output", type=str, default="data/knowledge.json")
    parser.add_argument("--query", type=str, default="How do I place decoupling capacitors?")
    args = parser.parse_args()

    print(f"Creating knowledge base with {args.model}...")
    kb = make_rag_knowledge_base(args.model)

    print(f"\nQuery: {args.query}")
    print("Retrieved:")
    for result in kb.retrieve(args.query, top_k=3):
        print(f"  [{result.category}] {result.content}")

    if args.output:
        print(f"\nSaving to {args.output}")
        kb.save(Path(args.output))