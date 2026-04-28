"""
PCB Builder - Multi-Candidate Generation
Generates parallel layout candidates for user comparison.
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from shared.config import get_settings
from shared.logging_config import logger
from shared.validation.drc_engine import PhysicsAwareDRC, get_rule_set
from shared.validation.dfm_engine import DFMEngine
from shared.validation.si_analyzer import SignalIntegrityAnalyzer

settings = get_settings()


@dataclass
class CandidateMetrics:
    """Metrics for a single layout candidate."""
    routing_completion: float  # %
    drc_score: float
    drc_violations: int
    drc_critical: int
    drc_warnings: int
    dfm_score: float
    si_score: float
    thermal_score: float
    overall_score: float
    via_count: int
    total_trace_length_mm: float
    board_area_utilization: float
    manufacturing_cost_estimate_usd: float
    estimated_cleanup_time_min: float


@dataclass
class LayoutCandidate:
    """A single PCB layout candidate."""
    candidate_id: str
    design_data: dict
    metrics: CandidateMetrics
    rank: int = 0
    selected: bool = False
    reasoning: str = ""
    differences_from_best: list[str] = field(default_factory=list)


class MultiCandidateGenerator:
    """Generates multiple layout candidates in parallel."""

    def __init__(self, num_candidates: int = 3):
        self.num_candidates = min(num_candidates, 5)  # Max 5
        self.analyzer_drc = PhysicsAwareDRC()
        self.analyzer_dfm = DFMEngine()
        self.analyzer_si = SignalIntegrityAnalyzer()

    async def generate_candidates(
        self,
        requirements: dict,
        schematic: dict,
        board_config: dict,
    ) -> list[LayoutCandidate]:
        """Generate multiple layout candidates."""
        logger.info("Starting multi-candidate generation", num_candidates=self.num_candidates)

        # Create different strategies for each candidate
        strategies = [
            {"name": "compact", "focus": "minimize_board_size", "density": "high"},
            {"name": "balanced", "focus": "balance_density_and_routing", "density": "medium"},
            {"name": "spacious", "focus": "maximize_clearance", "density": "low"},
            {"name": "performance", "focus": "high_speed_optimization", "density": "medium"},
            {"name": "cost", "focus": "minimize_layer_count", "density": "medium"},
        ]

        candidates = []
        tasks = []

        for i in range(min(self.num_candidates, len(strategies))):
            strategy = strategies[i]
            task = self._generate_single_candidate(
                candidate_id=f"candidate_{i+1}",
                requirements=requirements,
                schematic=schematic,
                board_config=board_config,
                strategy=strategy,
            )
            tasks.append(task)

        # Run candidates in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Candidate {i+1} failed", error=str(result))
                continue
            candidates.append(result)

        # Score and rank candidates
        candidates = self._rank_candidates(candidates)

        logger.info(
            "Multi-candidate generation complete",
            generated=len(candidates),
            best_score=candidates[0].metrics.overall_score if candidates else 0,
        )

        return candidates

    async def _generate_single_candidate(
        self,
        candidate_id: str,
        requirements: dict,
        schematic: dict,
        board_config: dict,
        strategy: dict,
    ) -> LayoutCandidate:
        """Generate a single layout candidate with a specific strategy."""
        # Call LLM with strategy-specific prompt
        prompt = self._build_strategy_prompt(requirements, schematic, board_config, strategy)

        design_data = await self._call_llm_for_candidate(prompt)

        # Run validation
        drc_result = self.analyzer_drc.run_full_check(design_data)
        dfm_result = self.analyzer_dfm.analyze(design_data)
        si_result = self.analyzer_si.analyze(design_data)

        # Calculate metrics
        metrics = self._calculate_metrics(design_data, drc_result, dfm_result, si_result)

        return LayoutCandidate(
            candidate_id=candidate_id,
            design_data=design_data,
            metrics=metrics,
            reasoning=f"Generated with {strategy['name']} strategy: {strategy['focus']}",
        )

    def _build_strategy_prompt(
        self,
        requirements: dict,
        schematic: dict,
        board_config: dict,
        strategy: dict,
    ) -> str:
        """Build LLM prompt for a specific strategy."""
        base = f"""Generate a complete PCB layout using the {strategy['name'].upper()} strategy.

STRATEGY: {strategy['focus']}
Density: {strategy['density']}

Requirements: {json.dumps(requirements, indent=2)}
Schematic: {json.dumps(schematic, indent=2)}
Board Config: {json.dumps(board_config, indent=2)}

CRITICAL RULES:
1. ALL components must be placed
2. ALL nets must be routed
3. Use standard clearances and trace widths
4. Return ONLY valid JSON

OUTPUT FORMAT:
{{
  "design_reasoning": "Concise engineering rationale",
  "board_config": {{"width_mm": float, "height_mm": float, "layers": int}},
  "placed_components": [{{"id": str, "x": float, "y": float, "rotation": float, "layer": str}}],
  "nets": [{{"name": str, "pins": [{{"component_id": str, "pin": str}}]}}],
  "tracks": [{{"start": [x,y], "end": [x,y], "width": float, "layer": str, "net": str}}],
  "vias": [{{"x": float, "y": float, "diameter": float, "drill": float}}],
  "drc_rules": {{"min_trace_width_mm": float, "min_clearance_mm": float}}
}}"""
        return base

    async def _call_llm_for_candidate(self, prompt: str) -> dict:
        """Call LLM to generate a single candidate."""
        system_prompt = "You are an expert PCB layout engineer. Generate complete, fabricatable PCB designs in JSON format."

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.nvidia_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.nvidia_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.nvidia_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 4096,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Extract JSON
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                return json.loads(content[start:end+1])
            return json.loads(content)

    def _calculate_metrics(
        self,
        design_data: dict,
        drc_result,
        dfm_result,
        si_result,
    ) -> CandidateMetrics:
        """Calculate comprehensive metrics for a candidate."""
        tracks = design_data.get("tracks", [])
        vias = design_data.get("vias", [])
        components = design_data.get("placed_components", [])
        board = design_data.get("board_config", {})
        board_w = board.get("width_mm", 100)
        board_h = board.get("height_mm", 100)
        board_area = board_w * board_h

        # Trace length
        total_length = sum(
            ((t["end"][0] - t["start"][0]) ** 2 + (t["end"][1] - t["start"][1]) ** 2) ** 0.5
            for t in tracks
        )

        # Area utilization (rough estimate)
        comp_area = len(components) * 25  # Approx 5x5mm per component
        utilization = min(1.0, comp_area / board_area)

        # Routing completion
        nets = design_data.get("nets", [])
        routed_nets = set(t.get("net", "") for t in tracks)
        completion = len(routed_nets) / max(len(nets), 1) * 100

        # Overall score (weighted)
        overall = (
            drc_result.score * 0.35 +
            dfm_result.score * 0.25 +
            si_result.score * 0.20 +
            completion * 0.10 +
            max(0, 100 - len(vias)) * 0.10
        )

        return CandidateMetrics(
            routing_completion=round(completion, 1),
            drc_score=round(drc_result.score, 1),
            drc_violations=len(drc_result.violations),
            drc_critical=len(drc_result.by_severity.get("critical", [])),
            drc_warnings=len(drc_result.by_severity.get("warning", [])),
            dfm_score=round(dfm_result.score, 1),
            si_score=round(si_result.score, 1),
            thermal_score=round(dfm_result.summary.get("thermal", 100), 1),
            overall_score=round(overall, 1),
            via_count=len(vias),
            total_trace_length_mm=round(total_length, 1),
            board_area_utilization=round(utilization * 100, 1),
            manufacturing_cost_estimate_usd=round(self._estimate_cost(board, len(components), len(vias)), 2),
            estimated_cleanup_time_min=round(self._estimate_cleanup_time(drc_result, dfm_result), 1),
        )

    def _rank_candidates(self, candidates: list[LayoutCandidate]) -> list[LayoutCandidate]:
        """Rank candidates by overall score."""
        # Sort by overall score descending
        candidates.sort(key=lambda c: c.metrics.overall_score, reverse=True)

        for i, candidate in enumerate(candidates):
            candidate.rank = i + 1
            if i == 0:
                candidate.selected = True

        # Calculate differences from best
        if candidates:
            best = candidates[0]
            for candidate in candidates[1:]:
                diffs = []
                if candidate.metrics.drc_score < best.metrics.drc_score:
                    diffs.append(f"DRC score lower by {best.metrics.drc_score - candidate.metrics.drc_score:.1f}")
                if candidate.metrics.dfm_score < best.metrics.dfm_score:
                    diffs.append(f"DFM score lower by {best.metrics.dfm_score - candidate.metrics.dfm_score:.1f}")
                if candidate.metrics.via_count > best.metrics.via_count:
                    diffs.append(f"More vias ({candidate.metrics.via_count} vs {best.metrics.via_count})")
                if candidate.metrics.total_trace_length_mm > best.metrics.total_trace_length_mm:
                    diffs.append(f"Longer traces ({candidate.metrics.total_trace_length_mm:.1f}mm vs {best.metrics.total_trace_length_mm:.1f}mm)")
                candidate.differences_from_best = diffs

        return candidates

    def _estimate_cost(self, board_config: dict, comp_count: int, via_count: int) -> float:
        """Estimate manufacturing cost."""
        layers = board_config.get("layers", 2)
        w = board_config.get("width_mm", 50)
        h = board_config.get("height_mm", 50)
        area_cm2 = (w * h) / 100

        # Base cost per cm2
        base_cost = {2: 0.5, 4: 1.2, 6: 2.5, 8: 4.0}.get(layers, 0.5)
        cost = area_cm2 * base_cost
        cost += comp_count * 0.05  # Assembly cost
        cost += via_count * 0.01  # Via cost
        return max(2.0, cost)  # Minimum $2

    def _estimate_cleanup_time(self, drc_result, dfm_result) -> float:
        """Estimate human cleanup time in minutes."""
        critical = len(drc_result.by_severity.get("critical", []))
        errors = len(drc_result.by_severity.get("error", []))
        warnings = len(drc_result.by_severity.get("warning", []))
        return critical * 30 + errors * 10 + warnings * 2


def generate_candidates(requirements: dict, schematic: dict, board_config: dict, num: int = 3) -> list[LayoutCandidate]:
    """Convenience function to generate candidates."""
    import asyncio
    gen = MultiCandidateGenerator(num)
    return asyncio.run(gen.generate_candidates(requirements, schematic, board_config))
