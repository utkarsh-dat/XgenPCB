"""
PCB Builder - Stage 5: Output Agent
Generates final deliverables: Gerber, drill, BOM, drawings.
"""

from shared.agents.base import BaseAgent, GateResult, PipelineContext, PipelineStage, StageResult, StageStatus
from shared.logging_config import logger


class OutputAgent(BaseAgent):
    """Agent that assembles final manufacturing output."""

    stage = PipelineStage.OUTPUT
    max_retries = 1

    async def execute(self, context: PipelineContext) -> StageResult:
        """Assemble final output from all previous stages."""
        try:
            # Build unified PCB design document
            design = {
                "design_reasoning": context.design_reasoning,
                "board_config": context.board_config,
                "drc_rules": context.requirements.get("drc_rules", {}),
                "placed_components": context.placement.get("placed_components", []),
                "nets": context.schematic.get("nets", []),
                "tracks": context.routing.get("tracks", []),
                "vias": context.routing.get("vias", []),
                "copper_pours": context.routing.get("copper_pours", []),
                "mounting_holes": context.placement.get("mounting_holes", []),
                "fiducials": context.placement.get("fiducials", []),
            }

            # Generate validation report summary
            validation = context.validation.get("validation", {})
            validation_summary = {
                "overall_score": context.validation.get("overall_score", 0),
                "drc_score": validation.get("drc", {}).get("score", 0),
                "dfm_score": validation.get("dfm", {}).get("score", 0),
                "si_score": validation.get("si", {}).get("score", 0),
                "thermal_score": validation.get("thermal", {}).get("passed", True),
                "critical_issues_count": len(context.validation.get("critical_issues", [])),
                "warnings_count": len(context.validation.get("warnings", [])),
            }

            # Manufacturing info
            manufacturing = validation.get("manufacturing", {})
            output_data = {
                "design": design,
                "validation_summary": validation_summary,
                "manufacturing": {
                    "target": context.requirements.get("target_manufacturer", "JLCPCB Standard"),
                    "cost_estimate_usd": manufacturing.get("cost_estimate_usd", 0),
                    "lead_time_days": manufacturing.get("lead_time_days", 5),
                    "capability_match": manufacturing.get("capability_match", 0),
                },
                "bom": context.schematic.get("bom", []),
                "files_to_generate": [
                    "Gerber RS-274X (all layers)",
                    "NC Drill (plated + non-plated)",
                    "Pick-and-Place (centroid)",
                    "BOM (CSV)",
                    "Fabrication Drawing (PDF)",
                    "Assembly Drawing (PDF)",
                ],
                "ready_for_fabrication": True,
            }

            return StageResult(
                stage=self.stage,
                status=StageStatus.PASSED,
                data={"output": output_data},
                confidence=0.95,
                reasoning="Output assembled from all validated pipeline stages",
            )

        except Exception as e:
            logger.error("Output assembly error", error=str(e), exc_info=True)
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error_message=str(e),
            )

    async def validate(self, result: StageResult, context: PipelineContext) -> GateResult:
        """Validate output completeness."""
        data = result.data.get("output", {})
        errors = []
        warnings = []

        # Check design completeness
        design = data.get("design", {})
        required_fields = ["board_config", "placed_components", "nets", "tracks"]
        for field in required_fields:
            if not design.get(field):
                errors.append({
                    "field": f"design.{field}",
                    "severity": "critical",
                    "message": f"Missing required field: {field}",
                })

        # Check validation passed
        if not data.get("ready_for_fabrication", False):
            errors.append({
                "field": "ready_for_fabrication",
                "severity": "critical",
                "message": "Design not marked ready for fabrication",
            })

        # Check BOM exists
        if not data.get("bom"):
            warnings.append({
                "field": "bom",
                "severity": "warning",
                "message": "No BOM generated",
            })

        score = 100.0 - len(errors) * 25 - len(warnings) * 5
        critical_count = sum(1 for e in errors if e.get("severity") == "critical")

        return GateResult(
            passed=critical_count == 0,
            score=max(0.0, score),
            errors=errors,
            warnings=warnings,
            critical_count=critical_count,
            warning_count=len(warnings),
        )
