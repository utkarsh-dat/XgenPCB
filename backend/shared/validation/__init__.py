"""
PCB Builder - Validation Framework
Physics-aware validation for PCB designs.
"""

from shared.validation.drc_engine import (
    DRCResult,
    DRCRuleSet,
    DRCViolation,
    PhysicsAwareDRC,
    RuleCategory,
    RuleSeverity,
    get_rule_set,
    run_physics_drc,
)
from shared.validation.dfm_engine import DFMEngine, DFMResult, run_dfm_analysis
from shared.validation.si_analyzer import SIResult, SignalIntegrityAnalyzer, run_si_analysis
from shared.validation.explainability import (
    DesignDecision,
    ExplanationReport,
    ExplainabilityEngine,
    generate_explanation,
)
from shared.validation.multi_candidate import (
    CandidateMetrics,
    LayoutCandidate,
    MultiCandidateGenerator,
    generate_candidates,
)

__all__ = [
    "DRCResult",
    "DRCRuleSet",
    "DRCViolation",
    "PhysicsAwareDRC",
    "RuleCategory",
    "RuleSeverity",
    "get_rule_set",
    "run_physics_drc",
    "DFMEngine",
    "DFMResult",
    "run_dfm_analysis",
    "SIResult",
    "SignalIntegrityAnalyzer",
    "run_si_analysis",
    "DesignDecision",
    "ExplanationReport",
    "ExplainabilityEngine",
    "generate_explanation",
    "CandidateMetrics",
    "LayoutCandidate",
    "MultiCandidateGenerator",
    "generate_candidates",
]
