"""
PCB Builder - Agent Framework Base Classes
Defines the contract for all pipeline stages.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    VALIDATING = "validating"
    PASSED = "passed"
    FAILED = "failed"
    RETRYING = "retrying"
    BACKTRACKING = "backtracking"


class PipelineStage(Enum):
    INTENT = "intent_parsing"
    REQUIREMENTS = "requirements"
    SCHEMATIC = "schematic"
    PLACEMENT = "placement"
    ROUTING = "routing"
    VALIDATION = "validation"
    OUTPUT = "output"


@dataclass
class GateResult:
    """Result of a validation gate check."""
    passed: bool
    score: float  # 0.0 - 100.0
    errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    @property
    def has_critical(self) -> bool:
        return self.critical_count > 0 or any(e.get("severity") == "critical" for e in self.errors)


@dataclass
class StageResult:
    """Result of executing a pipeline stage."""
    stage: PipelineStage
    status: StageStatus
    data: dict = field(default_factory=dict)
    gate_result: Optional[GateResult] = None
    confidence: float = 0.0  # 0.0 - 1.0
    execution_time_ms: int = 0
    retry_count: int = 0
    reasoning: str = ""
    artifacts: dict = field(default_factory=dict)
    error_message: Optional[str] = None
    traceback: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status in (StageStatus.PASSED, StageStatus.PASSED)


@dataclass
class PipelineContext:
    """Shared context across all pipeline stages."""
    user_input: str = ""
    board_config: dict = field(default_factory=dict)
    requirements: dict = field(default_factory=dict)
    schematic: dict = field(default_factory=dict)
    placement: dict = field(default_factory=dict)
    routing: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    design_reasoning: str = ""
    history: list[StageResult] = field(default_factory=list)


class BaseAgent(ABC):
    """Base class for all pipeline stage agents."""

    stage: PipelineStage
    max_retries: int = 3

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    @abstractmethod
    async def execute(self, context: PipelineContext) -> StageResult:
        """Execute the agent's main logic."""
        pass

    @abstractmethod
    async def validate(self, result: StageResult, context: PipelineContext) -> GateResult:
        """Validate the stage output against gate criteria."""
        pass

    async def retry(self, context: PipelineContext, previous_result: StageResult) -> StageResult:
        """Retry with adjusted parameters based on previous failure."""
        previous_result.retry_count += 1
        if previous_result.retry_count > self.max_retries:
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error_message=f"Max retries ({self.max_retries}) exceeded for {self.stage.value}",
            )
        return await self.execute(context)

    async def run(self, context: PipelineContext) -> StageResult:
        """Run the full stage: execute → validate → retry if needed."""
        result = await self.execute(context)
        if result.status == StageStatus.FAILED:
            return result

        gate = await self.validate(result, context)
        result.gate_result = gate

        if gate.passed:
            result.status = StageStatus.PASSED
            return result

        # Gate failed - retry if possible
        if result.retry_count < self.max_retries:
            result.status = StageStatus.RETRYING
            return await self.retry(context, result)

        result.status = StageStatus.FAILED
        result.error_message = f"Gate validation failed after {result.retry_count} retries"
        return result
