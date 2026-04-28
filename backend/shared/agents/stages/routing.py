"""
PCB Builder - Stage 3: Routing Agent
Routes all nets with DRC validation.
"""

import json

import httpx

from shared.agents.base import BaseAgent, GateResult, PipelineContext, PipelineStage, StageResult, StageStatus
from shared.config import get_settings
from shared.logging_config import logger

settings = get_settings()

ROUTING_SYSTEM_PROMPT = """You are an expert PCB routing engineer.
Given placement and schematic, route ALL nets optimally.

CRITICAL ROUTING RULES:
1. ALL nets must be fully routed (0 unrouted)
2. Power/Ground planes first
3. Critical signals first (clocks, high-speed differentials, RF)
4. Memory interfaces next
5. Remaining digital signals
6. Power traces: min 0.3mm width
7. Signal traces: min 0.15mm width
8. Maintain clearance: 0.2mm min
9. Use 45-degree corners
10. Minimize vias
11. Differential pairs: matched length, proper spacing
12. Return path: continuous ground plane under high-speed signals

OUTPUT JSON FORMAT:
{
  "routing": {
    "tracks": [
      {"start": [x, y], "end": [x, y], "width": 0.25, "layer": "F.Cu", "net": "VCC"}
    ],
    "vias": [
      {"x": 25.0, "y": 25.0, "from_layer": 0, "to_layer": 31, "diameter": 0.6, "drill": 0.3}
    ],
    "copper_pours": [
      {"net": "GND", "layer": "B.Cu", "points": [[0,0], [50,0], [50,50], [0,50]]}
    ],
    "routing_order": ["VCC", "GND", "USB_D+", ...],
    "differential_pairs": [
      {"net_pos": "USB_D+", "net_neg": "USB_D-", "matched": true, "length_diff_mm": 0.0}
    ]
  },
  "drc_summary": {
    "errors": [],
    "warnings": [],
    "passed": true
  },
  "reasoning": "Routing rationale"
}

All coordinates in millimeters.
Return ONLY valid JSON. Ensure ALL nets from schematic are routed."""


class RoutingAgent(BaseAgent):
    """Agent that routes all nets on the board."""

    stage = PipelineStage.ROUTING
    max_retries = 5

    async def execute(self, context: PipelineContext) -> StageResult:
        """Route nets from placement and schematic."""
        schematic = context.schematic
        placement = context.placement
        board_config = context.board_config
        requirements = context.requirements

        prompt = f"""Route ALL nets for this PCB:

Schematic Nets: {json.dumps(schematic.get('nets', []), indent=2)}

Placement: {json.dumps(placement.get('placed_components', []), indent=2)}

Board Config: {json.dumps(board_config, indent=2)}

DRC Rules: {json.dumps(requirements.get('drc_rules', {}), indent=2)}

Return ONLY valid JSON with routing data. Ensure EVERY net is routed.
Board size: {board_config.get('width_mm', 100)}mm x {board_config.get('height_mm', 100)}mm.
Layers: {board_config.get('layers', 2)}."""

        try:
            result = await self._call_llm(ROUTING_SYSTEM_PROMPT, prompt)
            data = json.loads(result)
            return StageResult(
                stage=self.stage,
                status=StageStatus.PASSED,
                data=data,
                confidence=0.82,
                reasoning=data.get("reasoning", ""),
            )
        except Exception as e:
            logger.error("Routing generation error", error=str(e), exc_info=True)
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error_message=str(e),
            )

    async def validate(self, result: StageResult, context: PipelineContext) -> GateResult:
        """Validate routing: DRC, net completeness, SI."""
        data = result.data
        errors = []
        warnings = []

        routing = data.get("routing", {})
        tracks = routing.get("tracks", [])
        vias = routing.get("vias", [])

        schematic_nets = context.schematic.get("nets", [])
        drc_rules = context.requirements.get("drc_rules", {})
        min_trace = drc_rules.get("min_trace_width_mm", 0.15)
        min_clearance = drc_rules.get("min_clearance_mm", 0.2)
        min_via = drc_rules.get("min_via_drill_mm", 0.3)
        board_w = context.board_config.get("width_mm", 100)
        board_h = context.board_config.get("height_mm", 100)

        # Critical: Check all nets are routed
        routed_nets = set()
        for track in tracks:
            if track.get("net"):
                routed_nets.add(track["net"])

        for net in schematic_nets:
            net_name = net.get("name", "")
            if net_name and net_name not in routed_nets:
                # Check if it's a power/ground net that might be in copper pour
                if not any(p in net_name.upper() for p in ["GND", "VCC", "3V3", "5V", "VDD"]):
                    errors.append({
                        "field": f"net.{net_name}",
                        "severity": "critical",
                        "message": f"Net '{net_name}' has no routed tracks",
                    })

        # Check trace widths
        for track in tracks:
            width = track.get("width", 0.25)
            net = track.get("net", "")
            is_power = any(p in net.upper() for p in ["VCC", "3V3", "5V", "VDD", "VBAT", "PWR"])
            min_width = 0.3 if is_power else min_trace
            if width < min_width:
                errors.append({
                    "field": f"track.{net}",
                    "severity": "critical",
                    "message": f"Trace width {width}mm < minimum {min_width}mm for net '{net}'",
                })

        # Check tracks within board bounds
        for track in tracks:
            start = track.get("start", [0, 0])
            end = track.get("end", [0, 0])
            for pt in [start, end]:
                if pt[0] < -0.1 or pt[0] > board_w + 0.1 or pt[1] < -0.1 or pt[1] > board_h + 0.1:
                    errors.append({
                        "field": f"track.{track.get('net', '')}",
                        "severity": "critical",
                        "message": f"Track endpoint ({pt[0]}, {pt[1]}) outside board bounds",
                    })

        # Check via sizes
        for via in vias:
            drill = via.get("drill", 0.3)
            if drill < min_via:
                errors.append({
                    "field": f"via.({via.get('x', 0)}, {via.get('y', 0)})",
                    "severity": "critical",
                    "message": f"Via drill {drill}mm < minimum {min_via}mm",
                })

        # Check differential pairs
        diff_pairs = routing.get("differential_pairs", [])
        for pair in diff_pairs:
            if not pair.get("matched", False):
                warnings.append({
                    "field": f"diff_pair.{pair.get('net_pos', '')}",
                    "severity": "warning",
                    "message": f"Differential pair {pair['net_pos']}/{pair['net_neg']} not length matched",
                })

        # Track count sanity check
        expected_tracks = max(len(schematic_nets) * 2, 5)
        if len(tracks) < expected_tracks:
            warnings.append({
                "field": "tracks",
                "severity": "warning",
                "message": f"Low track count ({len(tracks)}) for {len(schematic_nets)} nets",
            })

        score = 100.0 - len(errors) * 25 - len(warnings) * 2
        critical_count = sum(1 for e in errors if e.get("severity") == "critical")

        return GateResult(
            passed=critical_count == 0,
            score=max(0.0, score),
            errors=errors,
            warnings=warnings,
            critical_count=critical_count,
            warning_count=len(warnings),
        )

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
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
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4096,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
