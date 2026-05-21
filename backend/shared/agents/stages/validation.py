"""
PCB Builder - Stage 4: Validation Agent (Full Physics Suite)
Runs DRC, DFM, SI, PI, Timing, Thermal, and EMI/EMC analysis.
"""

from shared.agents.base import BaseAgent, GateResult, PipelineContext, PipelineStage, StageResult, StageStatus
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
from shared.physics import (
    PowerIntegrityEngine,
    TimingAnalyzer,
    ThermalEngine,
    EMIEMCChecker,
)


class ValidationAgent(BaseAgent):
    """
    Agent that validates the complete PCB design using full physics suite.

    Runs 7 validation engines:
    1. DRC - Design rule checking (IPC standards)
    2. DFM - Design for manufacturing
    3. SI - Signal integrity (impedance, crosstalk)
    4. PI - Power integrity (IR drop, PDN)
    5. Timing - Propagation delay, setup/hold, clock skew
    6. Thermal - Junction temperature, heat dissipation
    7. EMI/EMC - Return paths, loop area, radiation
    """

    stage = PipelineStage.VALIDATION
    max_retries = 2

    async def execute(self, context: PipelineContext) -> StageResult:
        """Run comprehensive validation using all physics engines."""
        design_data = {
            "board_config": context.board_config,
            "placed_components": context.placement.get("placed_components", []),
            "tracks": context.routing.get("tracks", []),
            "vias": context.routing.get("vias", []),
            "nets": context.schematic.get("nets", []),
            "routing": context.routing,
            "drc_rules": context.requirements.get("drc_rules", {}),
        }

        target_manufacturer = context.requirements.get("target_manufacturer", "JLCPCB Standard")
        rule_set_name = self._map_manufacturer_to_rules(target_manufacturer)

        logger.info(
            "Running full physics validation suite",
            manufacturer=target_manufacturer,
            rule_set=rule_set_name,
        )

        # 1. DRC
        drc_result = run_physics_drc(design_data, rule_set_name)

        # 2. DFM
        dfm_result = run_dfm_analysis(design_data)

        # 3. Signal Integrity
        si_result = run_si_analysis(design_data)

        # 4. Power Integrity
        pi_engine = PowerIntegrityEngine()
        pi_result = pi_engine.analyze(design_data)

        # 5. Timing Analysis
        timing_analyzer = TimingAnalyzer()
        timing_result = timing_analyzer.analyze(design_data)

        # 6. Thermal Analysis
        thermal_engine = ThermalEngine()
        thermal_result = thermal_engine.analyze(design_data)

        # 7. EMI/EMC
        emc_checker = EMIEMCChecker()
        emc_result = emc_checker.analyze(design_data)

        # Calculate overall score (weighted)
        overall_score = (
            drc_result.score * 0.25 +
            dfm_result.score * 0.15 +
            si_result.score * 0.15 +
            pi_result.score * 0.15 +
            timing_result.score * 0.10 +
            thermal_result.score * 0.10 +
            emc_result.score * 0.10
        )

        # Count critical issues across all engines
        critical_count = (
            len(drc_result.by_severity.get("critical", [])) +
            sum(1 for i in dfm_result.fabrication_issues if i.severity.value == "critical") +
            sum(1 for i in si_result.impedance_issues if i.severity.value == "critical") +
            sum(1 for i in pi_result.ir_drop_issues if i.severity == "critical") +
            sum(1 for i in pi_result.current_capacity_issues if i.get("severity") == "critical") +
            sum(1 for i in timing_result.propagation_issues if i.severity == "critical") +
            sum(1 for i in timing_result.setup_hold_issues if i.severity == "critical") +
            sum(1 for i in timing_result.clock_skew_issues if i.severity == "critical") +
            sum(1 for i in thermal_result.issues if i.severity == "critical") +
            sum(1 for i in emc_result.return_path_issues if i.severity == "critical")
        )

        error_count = (
            len(drc_result.by_severity.get("error", [])) +
            sum(1 for i in si_result.impedance_issues if i.severity.value == "error") +
            sum(1 for i in pi_result.pdn_issues if i.severity == "warning") +
            sum(1 for i in timing_result.ddr_timing_issues if i.severity == "error") +
            sum(1 for i in thermal_result.issues if i.severity == "warning") +
            sum(1 for i in emc_result.loop_area_issues if i.severity == "warning")
        )

        ready_for_fab = (
            critical_count == 0 and
            drc_result.score >= 60 and
            dfm_result.score >= 60 and
            si_result.score >= 50 and
            pi_result.score >= 60 and
            thermal_result.score >= 60
        )

        # Collect critical issues
        critical_issues = []
        for v in drc_result.violations:
            if v.severity.value == "critical":
                critical_issues.append(f"DRC: {v.message}")
        for i in dfm_result.fabrication_issues:
            if i.severity.value == "critical":
                critical_issues.append(f"DFM: {i.message}")
        for i in pi_result.ir_drop_issues:
            if i.severity == "critical":
                critical_issues.append(f"PI: {i.message}")
        for i in pi_result.current_capacity_issues:
            if i.get("severity") == "critical":
                critical_issues.append(f"PI: {i.get('message', '')}")
        for i in timing_result.propagation_issues:
            if i.severity == "critical":
                critical_issues.append(f"TIMING: {i.message}")
        for i in timing_result.clock_skew_issues:
            if i.severity == "critical":
                critical_issues.append(f"TIMING: {i.message}")
        for i in thermal_result.issues:
            if i.severity == "critical":
                critical_issues.append(f"THERMAL: {i.message}")

        # Collect warnings
        warnings = []
        for v in drc_result.violations:
            if v.severity.value == "warning":
                warnings.append(f"DRC: {v.message}")
        for i in dfm_result.fabrication_issues + dfm_result.assembly_issues:
            if i.severity.value == "warning":
                warnings.append(f"DFM: {i.message}")
        for i in si_result.crosstalk_issues:
            if i.severity.value == "warning":
                warnings.append(f"SI: {i.message}")
        for i in pi_result.ir_drop_issues:
            if i.severity == "warning":
                warnings.append(f"PI: {i.message}")
        for i in thermal_result.issues:
            if i.severity == "warning":
                warnings.append(f"THERMAL: {i.message}")
        for i in emc_result.return_path_issues:
            if i.severity == "warning":
                warnings.append(f"EMC: {i.message}")

        # Recommendations
        recommendations = dfm_result.manufacturer_recommendations + [
            f"IPC Compliance: IPC-2221 = {drc_result.ipc_compliance.get('ipc_2221', 0):.1f}%",
        ]

        if pi_result.decoupling_analysis:
            for da in pi_result.decoupling_analysis:
                if not da.get("adequate", True):
                    recommendations.append(f"Power: {da.get('recommendation', '')}")

        if thermal_result.copper_pour_recommendations:
            recommendations.extend(thermal_result.copper_pour_recommendations)

        if thermal_result.thermal_via_recommendations:
            for tvr in thermal_result.thermal_via_recommendations:
                recommendations.append(
                    f"Thermal: Add {tvr['recommended_vias']} thermal vias under {tvr['component_id']}"
                )

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
                "pi": {
                    "passed": pi_result.passed,
                    "score": pi_result.score,
                    "ir_drop_issues": len(pi_result.ir_drop_issues),
                    "pdn_issues": len(pi_result.pdn_issues),
                    "current_capacity_issues": len(pi_result.current_capacity_issues),
                    "max_ir_drop_mv": pi_result.summary.get("ir_drop_max_mv", 0),
                    "decoupling_adequate": all(
                        d.get("adequate", False) for d in pi_result.decoupling_analysis
                    ) if pi_result.decoupling_analysis else True,
                },
                "timing": {
                    "passed": timing_result.passed,
                    "score": timing_result.score,
                    "propagation_issues": len(timing_result.propagation_issues),
                    "setup_hold_issues": len(timing_result.setup_hold_issues),
                    "clock_skew_issues": len(timing_result.clock_skew_issues),
                    "ddr_timing_issues": len(timing_result.ddr_timing_issues),
                    "timing_critical_nets": timing_result.summary.get("timing_critical_nets", 0),
                },
                "thermal": {
                    "passed": thermal_result.passed,
                    "score": thermal_result.score,
                    "max_junction_temp_c": thermal_result.summary.get("max_junction_temp_c", 25),
                    "thermal_issues": len(thermal_result.issues),
                    "thermal_vias_recommended": thermal_result.summary.get("thermal_vias_recommended", 0),
                },
                "emc": {
                    "passed": emc_result.passed,
                    "score": emc_result.score,
                    "return_path_issues": len(emc_result.return_path_issues),
                    "loop_area_issues": len(emc_result.loop_area_issues),
                    "ground_plane_issues": len(emc_result.ground_plane_issues),
                    "emi_risk_nets": len(emc_result.radiation_estimates),
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
            "reasoning": (
                f"Full physics validation: DRC={drc_result.score:.1f}, DFM={dfm_result.score:.1f}, "
                f"SI={si_result.score:.1f}, PI={pi_result.score:.1f}, "
                f"Timing={timing_result.score:.1f}, Thermal={thermal_result.score:.1f}, "
                f"EMC={emc_result.score:.1f}. "
                f"{critical_count} critical, {error_count} errors, {len(warnings)} warnings."
            ),
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

        if critical_issues:
            for issue in critical_issues[:5]:
                errors.append({
                    "field": "critical_issues",
                    "severity": "critical",
                    "message": str(issue),
                })

        if overall_score < 60:
            errors.append({
                "field": "overall_score",
                "severity": "critical",
                "message": f"Overall validation score {overall_score} below threshold (60)",
            })

        if not ready_for_fab:
            errors.append({
                "field": "ready_for_fab",
                "severity": "critical",
                "message": "Design not ready for fabrication",
            })

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
