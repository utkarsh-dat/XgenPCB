"""
PCB Builder - AI Service Routes
LLM integration for intent parsing, design review, auto-fix, and chat.

Enhanced with:
- RAG knowledge base integration
- Domain-adapted prompts (PCB-Bench style)
- Feedback collection for fine-tuning
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from shared.config import get_settings
from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.models import AIGeneration, User
from shared.schemas import (
    AutoFixRequest,
    ChatRequest,
    DesignReviewRequest,
    IntentRequest,
    IntentResult,
)

settings = get_settings()
router = APIRouter()

# RAG Knowledge Base (lazy loaded)
_rag_kb = None


def get_rag_kb():
    """Get RAG knowledge base instance."""
    global _rag_kb
    if _rag_kb is None:
        try:
            from rl_training.rag import make_rag_knowledge_base
            kb_path = Path("data/knowledge.json")
            if kb_path.exists():
                _rag_kb = make_rag_knowledge_base(knowledge_file=kb_path)
            else:
                _rag_kb = make_rag_knowledge_base()
        except ImportError:
            pass
    return _rag_kb


def _get_domain_context(query: str) -> str:
    """Get RAG context for query."""
    kb = get_rag_kb()
    if kb is None:
        return ""
    return kb.get_context(query, max_length=500)


async def call_llm(
    system_prompt: str,
    user_message: str,
    json_mode: bool = False,
    use_rag: bool = False,
) -> dict:
    """Call the LLM API with optional RAG enhancement."""
    # Add RAG context if enabled
    if use_rag:
        rag_context = _get_domain_context(user_message)
        if rag_context:
            user_message = f"{user_message}\n\nRelevant PCB knowledge:\n{rag_context}"

    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="LLM API key not configured")

    async with httpx.AsyncClient(timeout=60.0) as client:
        body = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )

        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"LLM API error: {response.status_code}")

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return {
            "content": content,
            "tokens": usage.get("total_tokens", 0),
            "model": data.get("model", settings.llm_model),
        }


# ━━ Intent Parsing ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INTENT_SYSTEM_PROMPT = """You are an expert PCB design assistant with deep knowledge of:
- PCB layout best practices (IPC standards)
- Component placement rules
- High-speed routing guidelines
- Design for manufacturing

Parse the user's natural language into a structured action with parameters.

Available actions:
- place_component: Place a component (params: component_name, x?, y?, rotation?)
- route_net: Route a specific net (params: net_name, strategy?)
- add_constraint: Add a design constraint (params: constraint_type, value, targets?)
- generate_bom: Generate bill of materials (params: format?)
- run_drc: Run design rule check (params: rules?)
- auto_route: Trigger automatic routing (params: nets?, strategy?)
- fix_violation: Fix a DRC violation (params: violation_id?, auto?)

Key PCB design knowledge:
- Decoupling capacitors (0.1uF) should be within 2mm of VCC pins
- High-speed traces need 45-degree corners, not 90-degree
- Minimum trace width: 0.15mm for signal, 0.3mm for power
- Maintain 2W rule: 2mil per 1A current for 1oz copper

Respond with JSON:
{"action_type": "...", "parameters": {...}, "confidence": 0.0-1.0, "explanation": "..."}
"""


@router.post("/parse-intent", response_model=IntentResult)
async def parse_intent(
    request: IntentRequest,
    current_user: User = Depends(get_current_user),
):
    """Parse natural language into structured design actions."""
    context_str = ""
    if request.design_context:
        context_str = f"\n\nCurrent design context:\n{json.dumps(request.design_context, indent=2)}"

    result = await call_llm(
        INTENT_SYSTEM_PROMPT,
        f"{request.user_input}{context_str}",
        json_mode=True,
    )

    parsed = json.loads(result["content"])
    return IntentResult(
        action_type=parsed.get("action_type", "unknown"),
        parameters=parsed.get("parameters", {}),
        confidence=parsed.get("confidence", 0.5),
        explanation=parsed.get("explanation", ""),
    )


# ━━ Chat ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CHAT_SYSTEM_PROMPT = """You are an expert PCB design assistant integrated into a PCB design tool.
Help users with:
- Component selection and placement suggestions
- Routing strategies and trace width calculations
- Signal integrity and thermal analysis guidance
- DRC violation explanations and fixes
- Design best practices and manufacturing guidelines
- BOM optimization and cost reduction

When suggesting actions, return them as a JSON array in the "actions" field.
Each action should have: {"type": "action_type", "params": {...}}

Be concise, technical, and actionable. Reference specific component values, trace widths,
clearances, and other measurable parameters when applicable.
"""


@router.post("/chat")
async def ai_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chat with AI design assistant."""
    start = time.time()

    context_str = ""
    if request.context:
        context_str = f"\n\nDesign context:\n{json.dumps(request.context, indent=2)}"

    result = await call_llm(
        CHAT_SYSTEM_PROMPT,
        f"{request.message}{context_str}",
    )

    elapsed_ms = int((time.time() - start) * 1000)

    # Log the generation
    gen = AIGeneration(
        design_id=request.design_id,
        user_id=current_user.id,
        generation_type="intent_parse",
        input_prompt=request.message,
        output_data={"response": result["content"]},
        llm_model=result["model"],
        tokens_used=result["tokens"],
        generation_time_ms=elapsed_ms,
        status="completed",
    )
    db.add(gen)

    # Try to extract actions from response
    actions = []
    try:
        if "```json" in result["content"]:
            json_block = result["content"].split("```json")[1].split("```")[0]
            parsed = json.loads(json_block)
            if isinstance(parsed, list):
                actions = parsed
            elif "actions" in parsed:
                actions = parsed["actions"]
    except (json.JSONDecodeError, IndexError, KeyError):
        pass

    return {
        "message": result["content"],
        "actions": actions,
        "tokens_used": result["tokens"],
        "generation_time_ms": elapsed_ms,
    }


# ━━ Auto-Fix ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AUTOFIX_SYSTEM_PROMPT = """You are an expert PCB designer. Given DRC violations,
generate a JSON fix plan using these available operations:

- move_component: {id, x, y, rotation?}
- delete_track: {id}
- add_track: {net, points: [[x,y],...], layer, width_mm}
- add_via: {net, x, y, from_layer, to_layer}
- adjust_clearance: {component_a, component_b, min_distance_mm}
- change_trace_width: {net, width_mm}

Return ONLY a JSON object with:
{"fixes": [...operations...], "explanation": "...", "risk_level": "low|medium|high"}
"""


@router.post("/auto-fix")
async def auto_fix(
    request: AutoFixRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate automated fixes for DRC violations."""
    violations_text = "\n".join(
        f"- {v['type']}: {v['message']} at ({v.get('location', 'unknown')})"
        for v in request.violations
    )

    result = await call_llm(
        AUTOFIX_SYSTEM_PROMPT,
        f"Violations:\n{violations_text}\n\nDesign data:\n{json.dumps(request.design_data)}",
        json_mode=True,
    )

    parsed = json.loads(result["content"])

    return {
        "fixes": parsed.get("fixes", []),
        "explanation": parsed.get("explanation", ""),
        "risk_level": parsed.get("risk_level", "medium"),
        "tokens_used": result["tokens"],
    }


# ━━ Design Review ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REVIEW_SYSTEM_PROMPT = """You are an expert PCB design reviewer.
Analyze the design and provide structured feedback as JSON:

{
  "overall_score": 0-100,
  "categories": {
    "schematic": {"score": 0-100, "issues": [...], "suggestions": [...]},
    "placement": {"score": 0-100, "issues": [...], "suggestions": [...]},
    "routing": {"score": 0-100, "issues": [...], "suggestions": [...]},
    "manufacturing": {"score": 0-100, "issues": [...], "suggestions": [...]},
    "cost": {"score": 0-100, "issues": [...], "suggestions": [...]}
  },
  "critical_issues": [...],
  "summary": "..."
}

Be specific, actionable, and prioritize critical issues.
"""


@router.post("/design-review")
async def design_review(
    request: DesignReviewRequest,
    current_user: User = Depends(get_current_user),
):
    """Comprehensive AI design review."""
    result = await call_llm(
        REVIEW_SYSTEM_PROMPT,
        f"Review type: {request.review_type}\n\nDesign:\n{json.dumps(request.design_data)}",
        json_mode=True,
    )

    return json.loads(result["content"])


# ━━ Feedback Collection ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FEEDBACK_SYSTEM_PROMPT = """You are an expert PCB design assistant.
Collect feedback on AI suggestions to improve the model over time.

When users provide feedback:
- thumbs_up: The suggestion was helpful/correct
- thumbs_down: The suggestion was incorrect or unhelpful
- modified: The suggestion was used but modified

Categorize and store for fine-tuning."""


class FeedbackRequest(BaseModel):
    generation_id: uuid.UUID
    feedback: str  # "thumbs_up", "thumbs_down", "modified"
    comment: Optional[str] = None
    corrected_output: Optional[dict] = None


class FeedbackResponse(BaseModel):
    status: str
    stored_for_finetuning: bool


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Collect user feedback on AI suggestions for fine-tuning."""
    # Look up the original generation
    from sqlalchemy import select

    result = await db.execute(
        select(AIGeneration).where(AIGeneration.id == request.generation_id)
    )
    gen = result.scalar_one_or_none()

    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found")

    # Update with feedback
    feedback_entry = {
        "feedback": request.feedback,
        "comment": request.comment,
        "corrected_output": request.corrected_output,
        "user_id": str(current_user.id),
    }

    # Store feedback (append to existing metadata)
    existing_feedback = gen.output_data.get("feedback", [])
    if isinstance(existing_feedback, list):
        existing_feedback.append(feedback_entry)
    else:
        existing_feedback = [feedback_entry]

    gen.output_data["feedback"] = existing_feedback
    await db.commit()

    # Could trigger retraining when enough feedback accumulated
    return FeedbackResponse(
        status="stored",
        stored_for_finetuning=True,
    )


# ━━ Export Feedback for Fine-tuning ━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/export-feedback")
async def export_feedback_for_finetuning(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export accumulated feedback for fine-tuning dataset."""
    from sqlalchemy import select

    result = await db.execute(
        select(AIGeneration).where(
            AIGeneration.output_data.contains("feedback")
        )
    )
    generations = result.scalars().all()

    # Extract feedback examples
    examples = []
    for gen in generations:
        feedback_data = gen.output_data.get("feedback", [])
        if isinstance(feedback_data, list):
            for fb in feedback_data:
                if fb.get("feedback") in ["thumbs_down", "modified"] and fb.get("corrected_output"):
                    examples.append({
                        "instruction": f"Correct this PCB design action: {gen.input_prompt}",
                        "output": json.dumps(fb["corrected_output"]),
                        "original": gen.output_data.get("response"),
                        "feedback": fb.get("feedback"),
                    })

    return {
        "count": len(examples),
        "examples": examples[:100],  # Limit response size
    }
