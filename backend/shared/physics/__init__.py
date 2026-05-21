"""PCB Builder - Physics Engines for PCB Validation."""

from shared.physics.power_integrity import PowerIntegrityEngine, PIResult
from shared.physics.timing import TimingAnalyzer, TimingResult
from shared.physics.thermal import ThermalEngine, ThermalResult
from shared.physics.emc import EMIEMCChecker, EMCResult
from shared.physics.constraints import ConstraintExtractor

__all__ = [
    "PowerIntegrityEngine",
    "PIResult",
    "TimingAnalyzer",
    "TimingResult",
    "ThermalEngine",
    "ThermalResult",
    "EMIEMCChecker",
    "EMCResult",
    "ConstraintExtractor",
]
