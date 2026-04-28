"""
PCB Builder - Stage 4: Validation Agent (Physics-Aware)
Runs DRC, DFM, SI analysis using physics-aware engines.
"""

import json

from shared.agents.base import BaseAgent, GateResult, PipelineContext, PipelineStage, StageResult, StageStatus
from shared.config import get_settings
from shared.logging_config import logger
from shared.validation import (
    DFMEngine,
    PhysicsAwareDRC,
    SignalIntegrityAnalyzer,
    get_rule_set,
    run_dfm_analysis,
    run_physics_drc,
    run_si_analysis,
)

settings = get_settings()


class ValidationAgent(BaseAgent):
    """Agent that validates the complete PCB design using physics-aware engines."""

    stage = PipelineStage.VALIDATION
    max_retries = 2

    async def execute(self, context: PipelineContext) -> StageResult:
        """Run comprehensive validation using physics-aware engines."""
        # Build unified design data
        design_data = {
            "board_config": context.board_config,
            "placed_components": context.placement.get("placed_components", []),
            "tracks": context.routing.get("tracks", []),
            "vias": context.routing.get("vias", []),
            "nets": context.schematic.get("nets", []),
            "routing": context.routing,
            "drc_rules": context.requirements.get("drc_rules", {}),
        }

        # Determine rule set
        target_manufacturer = context.requirements.get("target_manufacturer", "JLCPCB Standard")
        rule_set_name = self._map_manufacturer_to_rules(target_manufacturer)
        ipc_class = context.requirements.get("drc_rules", {}).get("ipc_class", "Class 2")

        logger.info(
            "Running physics-aware validation",
            manufacturer=target_manufacturer,
            rule_set=rule_set_name,
            ipc_class=ipc_class,
        )

        # Run DRC
        drc_result = run_physics_drc(design_data, rule_set_name)

        # Run DFM
        dfm_result = run_dfm_analysis(design_data)

        # Run SI analysis
        si_result = run_si_analysis(design_data)

        # Calculate overall score
        overall_score = (
            drc_result.score * 0.35 +
            dfm_result.score * 0.25 +
            si_result.score * 0.20 +
            20.0  # Base score for completion
        )

        # Check readiness
        critical_count = (
            len(drc_result.by_severity.get("critical", [])) +
            sum(1 for i in dfm_result.fabrication_issues if i.severity.value == "critical") +
            sum(1 for i in si_result.impedance_issues if i.severity.value == "critical")
        )

        ready_for_fab = (
            critical_count == 0 and
            drc_result.score >= 60 and
            dfm_result.score >= 60 and
            si_result.score >= 50
        )

        # Collect critical issues
        critical_issues = []
        for v in drc_result.violations:
            if v.severity.value == "critical":
                critical_issues.append(f"DRC: {v.message}")
        for i in dfm_result.fabrication_issues:
            if i.severity.value == "critical":
                critical_issues.append(f"DFM: {i.message}")

        # Collect warnings
        warnings = []
        for v in drc_result.violations:
            if v.severity.value == "warning":
                warnings.append(f"DRC: {v.message}")
        for i in dfm_result.fabrication_issues + dfm_result.assembly_issues:
            if i.severity.value == "warning":
                warnings.append(f"DFM: {i.message}")

        # Recommendations
        recommendations = dfm_result.manufacturer_recommendations + [
            f"IPC Compliance: IPC-2221 = {drc_result.ipc_compliance.get('ipc_2221', 0):.1f}%",
        ]

        validation_data = {
            "validation": {
                "drc": {
                    "passed": drc_result.passed,
                    "score": drc_result.score,
                    "violations_count": len(drc_result.violations),
                    "critical": len(drc_result.by_severity.get("critical", [])),
                    "error": len(drc_result.by_severity.get("error", [])),
                    "warning": len(drc_result.by_severity.get("warning", [])),
                    "rule_set": drc_result.summary.get("rule_set", ""),
                },
                "dfm": {
                    "passed": dfm_result.passed,
                    "score": dfm_result.score,
                    "fabrication_issues": len(dfm_result.fabrication_issues),
                    "assembly_issues": len(dfm_result.assembly_issues),
                    "test_point_coverage": dfm_result.test_point_coverage,
                },
                "si": {
                    "passed": si_result.passed,
                    "score": si_result.score,
                    "high_speed_nets": len(si_result.high_speed_nets),
                    "impedance_issues": len(si_result.impedance_issues),
                    "crosstalk_issues": len(si_result.crosstalk_issues),
                },
                "manufacturing": {
                    "target": target_manufacturer,
                    "cost_estimate_usd": dfm_result.summary.get("cost_estimate", 0),
                },
            },
            "overall_score": round(overall_score, 1),
            "critical_issues": critical_issues,
            "warnings": warnings,
            "recommendations": recommendations,
            "ready_for_fab": ready_for_fab,
            "reasoning": f"Validation complete: DRC={drc_result.score:.1f}, DFM={dfm_result.score:.1f}, SI={si_result.score:.1f}. {len(critical_issues)} critical issues, {len(warnings)} warnings.",
        }

        return StageResult(
            stage=self.stage,
            status=StageStatus.PASSED,
            data=validation_data,
            confidence=0.92 if ready_for_fab else 0.6,
            reasoning=validation_data["reasoning"],
        )

    async def validate(self, result: StageResult, context: PipelineContext) -> GateResult:
        """Validate the validation results - ensure zero critical issues."""
        data = result.data
        errors = []
        warnings = []

        overall_score = data.get("overall_score", 0)
        ready_for_fab = data.get("ready_for_fab", False)
        critical_issues = data.get("critical_issues", [])

        # Critical: No critical issues allowed
        if critical_issues:
            for issue in critical_issues[:3]:  # Show first 3
                errors.append({
                    "field": "critical_issues",
                    "severity": "critical",
                    "message": str(issue),
                })

        # Overall score threshold
        if overall_score < 60:
            errors.append({
                "field": "overall_score",
                "severity": "critical",
                "message": f"Overall validation score {overall_score} below threshold (60)",
            })

        # Must be ready for fabrication
        if not ready_for_fab:
            errors.append({
                "field": "ready_for_fab",
                "severity": "critical",
                "message": "Design not ready for fabrication",
            })

        # Warnings
        validation_warnings = data.get("warnings", [])
        for w in validation_warnings[:5]:
            warnings.append({
                "field": "validation",
                "severity": "warning",
                "message": str(w),
            })

        score = float(overall_score) if isinstance(overall_score, (int, float)) else 0.0
        critical_count = len(errors)

        return GateResult(
            passed=critical_count == 0,
            score=score,
            errors=errors,
            warnings=warnings,
            critical_count=critical_count,
            warning_count=len(warnings),
        )

    def _map_manufacturer_to_rules(self, manufacturer: str) -> str:
        """Map manufacturer name to rule set name."""
        mapping = {
            "JLCPCB Standard": "jlcpcb_standard",
            "JLCPCB Advanced": "jlcpcb_advanced",
            "PCBWay": "pcbway_standard",
            "PCBWay Standard": "pcbway_standard",
        }
        return mapping.get(manufacturer, "ipc_class_2")
