"""
PCB Builder - Agent Framework
Multi-agent pipeline for autonomous PCB design.
"""

from shared.agents.base import (
    BaseAgent,
    GateResult,
    PipelineContext,
    PipelineStage,
    StageResult,
    StageStatus,
)
from shared.agents.orchestrator import AgentOrchestrator

__all__ = [
    "BaseAgent",
    "GateResult",
    "PipelineContext",
    "PipelineStage",
    "StageResult",
    "StageStatus",
    "AgentOrchestrator",
]
