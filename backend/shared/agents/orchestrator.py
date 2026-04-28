"""
PCB Builder - Pipeline Orchestrator
Manages the full 6-stage agent pipeline with state tracking.
"""

import time
import traceback
from typing import Optional

from shared.agents.base import PipelineContext, PipelineStage, StageResult, StageStatus
from shared.agents.stages.intent import IntentAgent
from shared.agents.stages.schematic import SchematicAgent
from shared.agents.stages.placement import PlacementAgent
from shared.agents.stages.routing import RoutingAgent
from shared.agents.stages.validation import ValidationAgent
from shared.agents.stages.output import OutputAgent
from shared.logging_config import logger


class AgentOrchestrator:
    """Orchestrates the full PCB generation pipeline across 6 stages."""

    STAGES = [
        PipelineStage.INTENT,
        PipelineStage.SCHEMATIC,
        PipelineStage.PLACEMENT,
        PipelineStage.ROUTING,
        PipelineStage.VALIDATION,
        PipelineStage.OUTPUT,
    ]

    AGENTS = {
        PipelineStage.INTENT: IntentAgent,
        PipelineStage.SCHEMATIC: SchematicAgent,
        PipelineStage.PLACEMENT: PlacementAgent,
        PipelineStage.ROUTING: RoutingAgent,
        PipelineStage.VALIDATION: ValidationAgent,
        PipelineStage.OUTPUT: OutputAgent,
    }

    def __init__(self, job_id: str, user_id: str, update_callback=None):
        self.job_id = job_id
        self.user_id = user_id
        self.update_callback = update_callback
        self.context = PipelineContext()

    async def run_pipeline(self, user_input: str, board_config: Optional[dict] = None) -> dict:
        """Run the full pipeline from intent to output."""
        self.context.user_input = user_input
        if board_config:
            self.context.board_config = board_config

        results = []

        for stage in self.STAGES:
            agent_cls = self.AGENTS[stage]
            agent = agent_cls()

            logger.info(
                "Pipeline stage starting",
                job_id=self.job_id,
                stage=stage.value,
            )

            await self._update_job(stage.value, "running", f"Executing {stage.value}...")

            start = time.time()
            try:
                result = await agent.run(self.context)
                result.execution_time_ms = int((time.time() - start) * 1000)
            except Exception as e:
                logger.error(
                    "Pipeline stage crashed",
                    job_id=self.job_id,
                    stage=stage.value,
                    error=str(e),
                    exc_info=True,
                )
                result = StageResult(
                    stage=stage,
                    status=StageStatus.FAILED,
                    error_message=str(e),
                    traceback=traceback.format_exc(),
                    execution_time_ms=int((time.time() - start) * 1000),
                )

            results.append(result)
            self.context.history.append(result)

            if result.status == StageStatus.PASSED:
                # Merge stage data into context
                self._merge_stage_data(stage, result)
                await self._update_job(
                    stage.value,
                    "passed",
                    f"{stage.value} passed (confidence: {result.confidence:.2f})",
                    progress=self._stage_to_progress(stage),
                )
                logger.info(
                    "Pipeline stage passed",
                    job_id=self.job_id,
                    stage=stage.value,
                    confidence=result.confidence,
                    execution_time_ms=result.execution_time_ms,
                )

            elif result.status == StageStatus.RETRYING:
                # Should not happen with agent.run() - retries are internal
                pass

            else:
                # FAILED - attempt backtracking
                logger.warning(
                    "Pipeline stage failed",
                    job_id=self.job_id,
                    stage=stage.value,
                    error=result.error_message,
                )

                backtrack_result = await self._attempt_backtrack(stage, result)
                if backtrack_result and backtrack_result.status == StageStatus.PASSED:
                    results[-1] = backtrack_result
                    self._merge_stage_data(stage, backtrack_result)
                    await self._update_job(
                        stage.value,
                        "passed",
                        f"{stage.value} passed after backtrack",
                        progress=self._stage_to_progress(stage),
                    )
                else:
                    await self._update_job(
                        stage.value,
                        "failed",
                        f"{stage.value} failed: {result.error_message}",
                        error=result.error_message,
                    )
                    return {
                        "status": "failed",
                        "failed_stage": stage.value,
                        "error": result.error_message,
                        "details": result.error_message,
                        "pipeline_results": [self._serialize_result(r) for r in results],
                    }

        # All stages passed
        await self._update_job("completed", "completed", "Pipeline completed successfully", progress=1.0)
        return {
            "status": "completed",
            "design": self._build_final_design(),
            "pipeline_results": [self._serialize_result(r) for r in results],
        }

    async def _attempt_backtrack(self, failed_stage: PipelineStage, failed_result: StageResult) -> Optional[StageResult]:
        """Attempt to backtrack to previous stage and retry."""
        stage_idx = self.STAGES.index(failed_stage)
        if stage_idx == 0:
            return None  # Can't backtrack from first stage

        prev_stage = self.STAGES[stage_idx - 1]
        prev_result = self.context.history[-2] if len(self.context.history) >= 2 else None

        if not prev_result:
            return None

        logger.info(
            "Attempting backtrack",
            job_id=self.job_id,
            from_stage=failed_stage.value,
            to_stage=prev_stage.value,
        )

        # Modify context with adjustment hints
        self.context.metadata["backtrack_from"] = failed_stage.value
        self.context.metadata["backtrack_reason"] = failed_result.error_message

        agent_cls = self.AGENTS[prev_stage]
        agent = agent_cls(max_retries=1)

        await self._update_job(prev_stage.value, "backtracking", f"Backtracking from {failed_stage.value}...")

        try:
            result = await agent.run(self.context)
            if result.status == StageStatus.PASSED:
                self._merge_stage_data(prev_stage, result)
                # Now retry failed stage
                failed_agent_cls = self.AGENTS[failed_stage]
                failed_agent = failed_agent_cls(max_retries=1)
                retry_result = await failed_agent.run(self.context)
                return retry_result
        except Exception:
            logger.error("Backtrack failed", job_id=self.job_id, exc_info=True)

        return None

    def _merge_stage_data(self, stage: PipelineStage, result: StageResult):
        """Merge successful stage data into pipeline context."""
        if stage == PipelineStage.INTENT:
            self.context.requirements = result.data.get("requirements", {})
            self.context.board_config = result.data.get("board_config", self.context.board_config)
            self.context.design_reasoning = result.data.get("reasoning", "")
        elif stage == PipelineStage.SCHEMATIC:
            self.context.schematic = result.data.get("schematic", {})
        elif stage == PipelineStage.PLACEMENT:
            self.context.placement = result.data.get("placement", {})
        elif stage == PipelineStage.ROUTING:
            self.context.routing = result.data.get("routing", {})
        elif stage == PipelineStage.VALIDATION:
            self.context.validation = result.data.get("validation", {})
        elif stage == PipelineStage.OUTPUT:
            self.context.output = result.data.get("output", {})

    def _build_final_design(self) -> dict:
        """Assemble final PCB design from all stage outputs."""
        return {
            "design_reasoning": self.context.design_reasoning,
            "board_config": self.context.board_config,
            "requirements": self.context.requirements,
            "schematic": self.context.schematic,
            "placed_components": self.context.placement.get("placed_components", []),
            "tracks": self.context.routing.get("tracks", []),
            "vias": self.context.routing.get("vias", []),
            "nets": self.context.schematic.get("nets", []),
            "drc_rules": self.context.requirements.get("drc_rules", {}),
            "validation_report": self.context.validation,
            "output_files": self.context.output,
        }

    def _serialize_result(self, result: StageResult) -> dict:
        """Serialize stage result for API response."""
        return {
            "stage": result.stage.value,
            "status": result.status.value,
            "confidence": result.confidence,
            "execution_time_ms": result.execution_time_ms,
            "retry_count": result.retry_count,
            "reasoning": result.reasoning,
            "error_message": result.error_message,
            "gate": {
                "passed": result.gate_result.passed if result.gate_result else False,
                "score": result.gate_result.score if result.gate_result else 0.0,
                "critical_count": result.gate_result.critical_count if result.gate_result else 0,
                "warning_count": result.gate_result.warning_count if result.gate_result else 0,
            } if result.gate_result else None,
        }

    def _stage_to_progress(self, stage: PipelineStage) -> float:
        """Map stage to pipeline progress (0.0 - 1.0)."""
        progress_map = {
            PipelineStage.INTENT: 0.15,
            PipelineStage.SCHEMATIC: 0.30,
            PipelineStage.PLACEMENT: 0.50,
            PipelineStage.ROUTING: 0.70,
            PipelineStage.VALIDATION: 0.85,
            PipelineStage.OUTPUT: 0.95,
        }
        return progress_map.get(stage, 0.0)

    async def _update_job(self, stage: str, status: str, message: str, progress: Optional[float] = None, error: Optional[str] = None):
        """Update job status in database via callback."""
        if self.update_callback:
            await self.update_callback(
                self.job_id,
                {
                    "stage": stage,
                    "status": status,
                    "message": message,
                    "progress": progress,
                    "error": error,
                },
            )
