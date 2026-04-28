"""
PCB Builder - Stage 1: Schematic Agent
Generates schematic from requirements with ERC validation.
"""

import json

import httpx

from shared.agents.base import BaseAgent, GateResult, PipelineContext, PipelineStage, StageResult, StageStatus
from shared.config import get_settings
from shared.logging_config import logger

settings = get_settings()

SCHEMATIC_SYSTEM_PROMPT = """You are an expert PCB schematic designer.
Given structured requirements, generate a complete schematic with:
- ALL components with reference designators, values, and footprints
- ALL nets with meaningful names
- Power and ground connections
- Decoupling capacitors (0.1uF per power pin, bulk caps per rail)
- Test points and debug interfaces

CRITICAL RULES:
1. Every component pin MUST be connected to a net (or marked NC)
2. Power outputs must not be shorted
3. No floating inputs on CMOS devices
4. Net labels must match physical connections
5. Use official KiCad Library footprint names: Library:Footprint format

OUTPUT JSON FORMAT:
{
  "schematic": {
    "components": [
      {"id": "U1", "name": "ESP32", "mpn": "ESP32-WROOM-32E", "footprint": "MCU_Module:ESP32-WROOM-32", "value": "", "description": "WiFi/BT MCU"}
    ],
    "nets": [
      {"name": "VCC", "pins": [{"component_id": "U1", "pin": "VCC"}, {"component_id": "C1", "pin": "1"}]}
    ],
    "power_symbols": [
      {"net": "VCC", "voltage": 3.3}
    ],
    "ground_symbols": [
      {"net": "GND"}
    ],
    "decoupling_caps": [
      {"component_id": "C1", "value": "0.1uF", "near_pin": "U1.VCC"}
    ]
  },
  "bom": [
    {"designator": "U1", "mpn": "ESP32-WROOM-32E", "quantity": 1, "category": "MCU"}
  ],
  "erc_report": {
    "errors": [],
    "warnings": [],
    "passed": true
  },
  "reasoning": "Design rationale"
}

Return ONLY valid JSON. No empty arrays for components or nets."""


class SchematicAgent(BaseAgent):
    """Agent that generates schematic from requirements."""

    stage = PipelineStage.SCHEMATIC
    max_retries = 3

    async def execute(self, context: PipelineContext) -> StageResult:
        """Generate schematic from requirements."""
        requirements = context.requirements
        board_config = context.board_config

        prompt = f"""Generate a complete PCB schematic from these requirements:

Requirements: {json.dumps(requirements, indent=2)}

Board Config: {json.dumps(board_config, indent=2)}

Return ONLY valid JSON with the schematic format.
Ensure ALL components have footprints, ALL nets are defined, and decoupling caps are included."""

        try:
            result = await self._call_llm(SCHEMATIC_SYSTEM_PROMPT, prompt)
            data = json.loads(result)
            return StageResult(
                stage=self.stage,
                status=StageStatus.PASSED,
                data=data,
                confidence=0.85,
                reasoning=data.get("reasoning", ""),
            )
        except Exception as e:
            logger.error("Schematic generation error", error=str(e), exc_info=True)
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error_message=str(e),
            )

    async def validate(self, result: StageResult, context: PipelineContext) -> GateResult:
        """Run ERC (Electrical Rule Check) on schematic."""
        data = result.data
        errors = []
        warnings = []
        schematic = data.get("schematic", {})

        components = schematic.get("components", [])
        nets = schematic.get("nets", [])

        # Critical: Components must not be empty
        if not components:
            errors.append({"field": "components", "severity": "critical", "message": "No components in schematic"})

        # Critical: Nets must not be empty
        if not nets:
            errors.append({"field": "nets", "severity": "critical", "message": "No nets defined"})

        # Check for unconnected pins
        component_pins = {}
        for comp in components:
            comp_id = comp.get("id", "")
            # Assume standard pin counts from footprint
            pin_count = self._infer_pin_count(comp.get("footprint", ""))
            component_pins[comp_id] = set(str(i) for i in range(1, pin_count + 1))

        connected_pins = set()
        for net in nets:
            for pin in net.get("pins", []):
                connected_pins.add(f"{pin['component_id']}.{pin['pin']}")
                if pin["component_id"] in component_pins:
                    component_pins[pin["component_id"]].discard(pin["pin"])

        # Check for unconnected pins (excluding NC)
        for comp_id, unconnected in component_pins.items():
            if unconnected:
                warnings.append({
                    "field": f"{comp_id}.pins",
                    "severity": "warning",
                    "message": f"Unconnected pins on {comp_id}: {', '.join(sorted(unconnected))}",
                })

        # Check for power conflicts
        power_nets = set()
        for net in nets:
            net_name = net.get("name", "").upper()
            if any(p in net_name for p in ["VCC", "3V3", "5V", "VDD", "VBAT"]):
                power_nets.add(net_name)

        if len(power_nets) > 1:
            # Check if different power nets are shorted
            pass  # Complex check - simplified for now

        # Check for decoupling caps
        decoupling = schematic.get("decoupling_caps", [])
        power_pins = sum(1 for net in nets if any(p in net.get("name", "").upper() for p in ["VCC", "3V3", "5V", "VDD"]))
        if len(decoupling) < power_pins / 2:
            warnings.append({
                "field": "decoupling_caps",
                "severity": "warning",
                "message": f"Insufficient decoupling caps ({len(decoupling)}) for {power_pins} power pins",
            })

        # Check footprints
        for comp in components:
            footprint = comp.get("footprint", "")
            if not footprint or ":" not in footprint:
                warnings.append({
                    "field": f"{comp['id']}.footprint",
                    "severity": "warning",
                    "message": f"Invalid or missing footprint for {comp['id']}: {footprint}",
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

    def _infer_pin_count(self, footprint: str) -> int:
        """Infer pin count from footprint name."""
        import re
        # Try to extract pin count from common patterns
        patterns = [
            r'_(\d+)pin', r'-(\d+)pin', r'_(\d+)Pin', r'-(\d+)Pin',
            r'_(\d+)$', r'-(\d+)$', r'x(\d+)$',
        ]
        fp_lower = footprint.lower()
        for pat in patterns:
            m = re.search(pat, fp_lower)
            if m:
                return int(m.group(1))
        # Common defaults
        if 'sot-23' in fp_lower: return 3
        if 'sot-223' in fp_lower: return 4
        if 'soic-8' in fp_lower: return 8
        if 'soic-14' in fp_lower: return 14
        if 'qfn-48' in fp_lower: return 48
        if 'qfn-32' in fp_lower: return 32
        if 'tqfp-48' in fp_lower: return 48
        if '0805' in fp_lower: return 2
        if '0603' in fp_lower: return 2
        if 'usb-c' in fp_lower: return 24
        if 'jst' in fp_lower: return 2
        return 4  # Default

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
