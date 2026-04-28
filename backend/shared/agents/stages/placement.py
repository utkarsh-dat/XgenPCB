"""
PCB Builder - Stage 2: Placement Agent
Places components on the board with thermal and fit validation.
"""

import json

import httpx

from shared.agents.base import BaseAgent, GateResult, PipelineContext, PipelineStage, StageResult, StageStatus
from shared.config import get_settings
from shared.logging_config import logger

settings = get_settings()

PLACEMENT_SYSTEM_PROMPT = """You are an expert PCB placement engineer.
Given a schematic and board config, place all components optimally.

CRITICAL PLACEMENT RULES:
1. ALL components must be placed (0 unplaced)
2. Connectors at board edges for easy access
3. Decoupling caps within 2mm of VCC pins (minimize loop area)
4. Fixed components first (connectors, switches, LEDs, mounting holes)
5. Critical ICs second (processors, memory, PHYs)
6. Power circuitry third (regulators, inductors, bulk caps)
7. Remaining passives last
8. Component courtyard clearances: 0.3mm min
9. Polarized components correctly oriented
10. Component height constraints respected
11. Fiducials placed (3 global min)
12. Mounting holes at corners

OUTPUT JSON FORMAT:
{
  "placement": {
    "placed_components": [
      {"id": "U1", "name": "ESP32", "footprint": "MCU_Module:ESP32-WROOM-32", "x": 25.0, "y": 25.0, "rotation": 0, "layer": "F", "reasoning": "Centered for optimal routing"}
    ],
    "mounting_holes": [
      {"x": 2.5, "y": 2.5, "diameter": 3.0}
    ],
    "fiducials": [
      {"x": 5.0, "y": 5.0, "type": "global"}
    ],
    "board_outline": {
      "width_mm": 50,
      "height_mm": 50
    }
  },
  "thermal_analysis": {
    "junction_temps": {"U1": 65.0},
    "max_temp_c": 85,
    "passed": true
  },
  "reasoning": "Placement rationale"
}

All coordinates in millimeters from bottom-left origin.
Return ONLY valid JSON."""


class PlacementAgent(BaseAgent):
    """Agent that places components on the board."""

    stage = PipelineStage.PLACEMENT
    max_retries = 3

    async def execute(self, context: PipelineContext) -> StageResult:
        """Place components from schematic."""
        schematic = context.schematic
        board_config = context.board_config
        requirements = context.requirements

        prompt = f"""Place all components for this PCB:

Schematic: {json.dumps(schematic, indent=2)}

Board Config: {json.dumps(board_config, indent=2)}

Requirements: {json.dumps(requirements, indent=2)}

Return ONLY valid JSON with placement data. Ensure ALL components are placed.
Board size: {board_config.get('width_mm', 100)}mm x {board_config.get('height_mm', 100)}mm."""

        try:
            result = await self._call_llm(PLACEMENT_SYSTEM_PROMPT, prompt)
            data = json.loads(result)
            return StageResult(
                stage=self.stage,
                status=StageStatus.PASSED,
                data=data,
                confidence=0.88,
                reasoning=data.get("reasoning", ""),
            )
        except Exception as e:
            logger.error("Placement generation error", error=str(e), exc_info=True)
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error_message=str(e),
            )

    async def validate(self, result: StageResult, context: PipelineContext) -> GateResult:
        """Validate placement: fit, clearances, thermal."""
        data = result.data
        errors = []
        warnings = []

        placement = data.get("placement", {})
        components = placement.get("placed_components", [])
        board_outline = placement.get("board_outline", context.board_config)
        board_w = board_outline.get("width_mm", context.board_config.get("width_mm", 100))
        board_h = board_outline.get("height_mm", context.board_config.get("height_mm", 100))

        # Critical: All components placed
        schematic_components = context.schematic.get("components", [])
        schematic_ids = {c.get("id") for c in schematic_components}
        placed_ids = {c.get("id") for c in components}
        missing = schematic_ids - placed_ids
        if missing:
            errors.append({
                "field": "placed_components",
                "severity": "critical",
                "message": f"Unplaced components: {', '.join(missing)}",
            })

        # Check components fit within board
        for comp in components:
            x, y = comp.get("x", 0), comp.get("y", 0)
            if x < 0 or x > board_w or y < 0 or y > board_h:
                errors.append({
                    "field": f"{comp['id']}.position",
                    "severity": "critical",
                    "message": f"Component {comp['id']} at ({x}, {y}) outside board ({board_w}x{board_h})",
                })

        # Check courtyard clearances
        min_clearance = context.requirements.get("drc_rules", {}).get("min_clearance_mm", 0.2)
        for i, comp_a in enumerate(components):
            for comp_b in components[i + 1:]:
                dx = abs(comp_a.get("x", 0) - comp_b.get("x", 0))
                dy = abs(comp_a.get("y", 0) - comp_b.get("y", 0))
                dist = (dx ** 2 + dy ** 2) ** 0.5
                if dist < min_clearance:
                    errors.append({
                        "field": f"clearance.{comp_a['id']}-{comp_b['id']}",
                        "severity": "critical",
                        "message": f"Clearance violation: {comp_a['id']} and {comp_b['id']} are {dist:.2f}mm apart (min {min_clearance}mm)",
                    })

        # Check decoupling cap proximity
        decoupling = context.schematic.get("decoupling_caps", [])
        for cap in decoupling:
            cap_id = cap.get("component_id", "")
            near_pin = cap.get("near_pin", "")
            cap_comp = next((c for c in components if c["id"] == cap_id), None)
            if cap_comp and near_pin:
                target_comp_id = near_pin.split(".")[0] if "." in near_pin else near_pin
                target_comp = next((c for c in components if c["id"] == target_comp_id), None)
                if cap_comp and target_comp:
                    dx = abs(cap_comp["x"] - target_comp["x"])
                    dy = abs(cap_comp["y"] - target_comp["y"])
                    dist = (dx ** 2 + dy ** 2) ** 0.5
                    if dist > 5.0:  # Should be within 2mm ideally
                        warnings.append({
                            "field": f"{cap_id}.proximity",
                            "severity": "warning",
                            "message": f"Decoupling cap {cap_id} is {dist:.1f}mm from {target_comp_id} (should be <2mm)",
                        })

        # Thermal check
        thermal = data.get("thermal_analysis", {})
        if not thermal.get("passed", True):
            max_temp = thermal.get("max_temp_c", 0)
            errors.append({
                "field": "thermal",
                "severity": "critical",
                "message": f"Thermal analysis failed: max junction temp {max_temp}C exceeds limit",
            })

        # Mounting holes check
        holes = placement.get("mounting_holes", [])
        if len(holes) < 2:
            warnings.append({
                "field": "mounting_holes",
                "severity": "warning",
                "message": "Fewer than 2 mounting holes recommended",
            })

        score = 100.0 - len(errors) * 25 - len(warnings) * 3
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
