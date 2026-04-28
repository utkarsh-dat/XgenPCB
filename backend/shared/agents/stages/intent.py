"""
PCB Builder - Stage 0: Intent Parser Agent
Converts natural language user input into structured requirements.
"""

import json
from datetime import datetime, timezone
from typing import Optional

import httpx

from shared.agents.base import BaseAgent, GateResult, PipelineContext, PipelineStage, StageResult, StageStatus
from shared.config import get_settings
from shared.logging_config import logger

settings = get_settings()

INTENT_SYSTEM_PROMPT = """You are an expert PCB requirements analyst.
Given a user's natural language description, extract structured PCB design requirements.

RULES:
1. Identify the main function/purpose of the board
2. List ALL required components with specific part numbers when possible
3. Identify power requirements (voltage rails, current needs)
4. Identify high-speed interfaces (USB, Ethernet, PCIe, DDR, etc.)
5. Identify mechanical constraints (size, mounting, connectors)
6. Infer target IPC class (default Class 2) and manufacturer capabilities
7. Identify environmental requirements (temperature, humidity, vibration)

OUTPUT JSON FORMAT:
{
  "requirements": {
    "purpose": "Brief description of board function",
    "components": [
      {"name": "U1", "type": "MCU", "part_number": "ESP32-WROOM-32E", "function": "Main processor"}
    ],
    "power_rails": [
      {"name": "3.3V", "voltage": 3.3, "current_max": 0.5, "source": "LDO"}
    ],
    "high_speed_interfaces": [
      {"type": "USB2.0", "speed": "480Mbps", "requirement": "differential_pair"}
    ],
    "mechanical": {
      "target_size_mm": {"width": 50, "height": 50},
      "mounting_holes": 4,
      "connectors": ["USB-C", "JST-PH-2pin"]
    },
    "environmental": {
      "operating_temp_c": [-20, 85],
      "ip_rating": "IP20"
    }
  },
  "board_config": {
    "width_mm": float,
    "height_mm": float,
    "layers": int,
    "thickness_mm": float,
    "material": "FR4",
    "surface_finish": "HASL",
    "copper_weight": "1oz"
  },
  "drc_rules": {
    "min_trace_width_mm": float,
    "min_clearance_mm": float,
    "min_via_drill_mm": float,
    "min_edge_clearance_mm": float,
    "ipc_class": "Class 2"
  },
  "target_manufacturer": "JLCPCB Standard",
  "confidence": 0.0,
  "clarifying_questions": ["question1", "question2"],
  "reasoning": "Brief engineering rationale"
}

Only return valid JSON. If requirements are ambiguous, include clarifying_questions."""


class IntentAgent(BaseAgent):
    """Agent that parses natural language into structured PCB requirements."""

    stage = PipelineStage.INTENT
    max_retries = 3

    async def execute(self, context: PipelineContext) -> StageResult:
        """Parse user input into structured requirements."""
        user_input = context.user_input
        board_config_hint = context.board_config

        prompt = f"""Analyze this PCB design request and extract structured requirements:

User Request: {user_input}

Existing Board Config (if any): {json.dumps(board_config_hint, indent=2)}

Return ONLY valid JSON with the requirements format."""

        try:
            result = await self._call_llm(INTENT_SYSTEM_PROMPT, prompt)
            data = json.loads(result)

            # Merge with any existing board config
            if board_config_hint:
                data.setdefault("board_config", {}).update(board_config_hint)

            confidence = data.get("confidence", 0.5)
            questions = data.get("clarifying_questions", [])

            # If confidence too low, fail with questions
            if confidence < 0.5 and questions:
                return StageResult(
                    stage=self.stage,
                    status=StageStatus.FAILED,
                    data=data,
                    confidence=confidence,
                    error_message=f"Ambiguous requirements. Please clarify: {'; '.join(questions[:3])}",
                    reasoning=data.get("reasoning", ""),
                )

            return StageResult(
                stage=self.stage,
                status=StageStatus.PASSED if confidence >= 0.7 else StageStatus.FAILED,
                data=data,
                confidence=confidence,
                reasoning=data.get("reasoning", ""),
            )

        except json.JSONDecodeError as e:
            logger.error("Intent parsing JSON decode error", error=str(e))
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error_message=f"Failed to parse LLM response: {e}",
            )
        except Exception as e:
            logger.error("Intent parsing error", error=str(e), exc_info=True)
            return StageResult(
                stage=self.stage,
                status=StageStatus.FAILED,
                error_message=str(e),
                traceback=traceback.format_exc() if hasattr(__import__('traceback'), 'format_exc') else "",
            )

    async def validate(self, result: StageResult, context: PipelineContext) -> GateResult:
        """Validate that requirements are complete and actionable."""
        data = result.data
        errors = []
        warnings = []

        requirements = data.get("requirements", {})
        board_config = data.get("board_config", {})
        drc_rules = data.get("drc_rules", {})

        # Critical checks
        if not requirements.get("purpose"):
            errors.append({"field": "purpose", "severity": "critical", "message": "Board purpose not defined"})

        if not requirements.get("components"):
            errors.append({"field": "components", "severity": "critical", "message": "No components specified"})

        if not board_config.get("width_mm") or not board_config.get("height_mm"):
            errors.append({"field": "board_size", "severity": "critical", "message": "Board dimensions not specified"})

        if board_config.get("layers", 0) < 1 or board_config.get("layers", 0) > 16:
            errors.append({"field": "layers", "severity": "critical", "message": "Invalid layer count (must be 1-16)"})

        # Warning checks
        if not requirements.get("power_rails"):
            warnings.append({"field": "power_rails", "severity": "warning", "message": "No power rails defined - will infer from components"})

        if not drc_rules.get("min_trace_width_mm"):
            warnings.append({"field": "drc_rules.min_trace_width", "severity": "warning", "message": "Using default trace width (0.25mm)"})

        # Score based on completeness
        score = 100.0
        score -= len(errors) * 25
        score -= len(warnings) * 5
        score = max(0.0, score)

        critical_count = sum(1 for e in errors if e.get("severity") == "critical")

        return GateResult(
            passed=critical_count == 0 and result.confidence >= 0.7,
            score=score,
            errors=errors,
            warnings=warnings,
            critical_count=critical_count,
            warning_count=len(warnings),
        )

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call NVIDIA NIM LLM for intent parsing."""
        async with httpx.AsyncClient(timeout=60.0) as client:
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
                    "max_tokens": 2048,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
