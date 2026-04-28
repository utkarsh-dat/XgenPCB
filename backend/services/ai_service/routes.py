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
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
import asyncio
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from shared.config import get_settings
from shared.database import get_db
from shared.middleware.auth import get_current_user
from shared.middleware.rate_limit import limiter
from shared.models import Job
from shared.schemas import JobResponse, PaginatedResponse
from shared.models import AIGeneration, Design, Project, User
from shared.schemas import (
    AutoFixRequest,
    ChatRequest,
    DesignReviewRequest,
    IntentRequest,
    IntentResult,
    PCBGenerateRequest,
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
    api_key: Optional[str] = None,
    job_id: Optional[str] = None, # Added job_id for live updates
) -> dict:
    """Call NVIDIA NIM API for LLM inference with live status updates."""
    
    # ── Internal Retry Helper ────────────────────────────────
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(HTTPException),
    )
    async def _do_call():
        effective_api_key = api_key or settings.nvidia_api_key
        if not effective_api_key:
            raise HTTPException(status_code=503, detail="NVIDIA API key not configured")
        
        async with httpx.AsyncClient(timeout=600.0, follow_redirects=True) as client:
            body = {
                "model": settings.nvidia_model,
                "messages": [
                    {"role": "system", "content": system_prompt + "\nIMPORTANT: You must start your response with '{' and end with '}'. Output ONLY valid JSON."},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 8192,
                "temperature": 0.1, # Critical for engineering precision
                "top_p": 1.0,
                "stream": False,
            }
            if json_mode:
                body["response_format"] = {"type": "json_object"}

            url = f"{settings.nvidia_base_url}/chat/completions"
            
            try:
                if job_id:
                    await update_job_status(job_id, {"message": "📡 Calling AI (Waiting for NVIDIA Chef to cook)..."})
                
                print(f"DEBUG: Sending POST to NVIDIA for job {job_id}")
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {effective_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
            except Exception as e:
                if job_id:
                    await update_job_status(job_id, {"message": f"⚠️ API Error: {str(e)[:40]}... Retrying."})
                raise HTTPException(status_code=503, detail=str(e))

            if response.status_code != 200:
                if job_id:
                    await update_job_status(job_id, {"message": f"⚠️ NVIDIA {response.status_code} Error. Retrying..."})
                raise HTTPException(status_code=502, detail=f"NVIDIA API error: {response.status_code}")

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise HTTPException(status_code=502, detail="No choices in LLM response")
            
            message = choices[0].get("message", {})
            content = message.get("content")
            usage = data.get("usage", {})
            
            return {
                "content": content,
                "tokens": usage.get("total_tokens", 0),
                "model": data.get("model", settings.nvidia_model),
            }

    return await _do_call()


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
        "examples": examples[:100],
    }


# ━━ PCB Generation System Prompt ━━━━━━━━━━━━━━━━━━━━━━━━
PCB_GENERATION_SYSTEM_PROMPT = """You are an expert PCB design engineer. Given user requirements,
you must output a complete, fabricatable PCB design in JSON format.

CRITICAL RULES:
1. You MUST place all components required by the user. The 'placed_components' list MUST NOT be empty.
2. You MUST define all electrical connections. The 'nets' list MUST NOT be empty.
3. You MUST route all traces. The 'tracks' list MUST NOT be empty.
4. If you output an empty design, it will be rejected. You are a professional, do not skip steps.
5. All coordinates are in millimeters (mm).
6. Ensure standard clearances (0.2mm) and track widths (0.25mm for signal, 0.5mm for power).
ALL nets defined, and ALL tracks routed. Do NOT return empty arrays.

1. COMPONENT PLACEMENT: Place ALL components considering:
   - Power components near edges, ICs in center
   - Connectors at board edges for easy access
   - Decoupling capacitors within 2mm of VCC pins

2. NET ROUTING: Route ALL nets:
   - Power traces: minimum 0.3mm width
   - Signal traces: minimum 0.15mm width
   - Maintain clearance between traces (0.2mm min)
   - Use 45-degree corners

3. FOOTPRINTS: You MUST use official KiCad Library names. Format: `Library:Footprint`.
   Search the entire KiCad library for the best match. 
   Examples for naming style (Inspiration only):
   - MCUs: `MCU_Module:ESP32-WROOM-32E`, `Module:RaspberryPi_Pico_SMD`
   - Parts: `Package_SO:SOIC-14_3.9x8.7mm_P1.27mm`, `Resistor_SMD:R_0805_2012Metric`
   - Connectors: `Connector_JST:JST_PH_S3B-PH-K_1x03_P2.00mm_Horizontal`

4. DRC RULES: If user specifies, use them. Otherwise INFER from needs:
   - "high current", "power", "LED" → thicker traces (0.3-0.5mm)
   - "high speed" → short traces, differential pairs
   - "SMD", "compact" → tighter spacing
   Add inferred DRC rules to "drc_rules" in output.

4. OUTPUT FORMAT - RETURN ALL THESE FIELDS:
{
  "design_reasoning": "A CONCISE bulleted summary (3-5 points) of your engineering strategy. Do NOT repeat yourself.",
  "board_config": {"width_mm": float, "height_mm": float, "layers": int, "thickness_mm": float, "material": "FR4", "surface_finish": "HASL"},
  "drc_rules": {"min_trace_width_mm": float, "min_clearance_mm": float, "min_via_drill_mm": float, "min_edge_clearance_mm": float},
  "placed_components": [{"id": str, "name": str, "mpn": str, "footprint": str, "x": float, "y": float, "rotation": float, "layer": "F"}],
  "nets": [{"name": str, "pins": [{"component_id": str, "pin": str}]}],
  "tracks": [{"start": [x, y], "end": [x, y], "width": float, "layer": "F.Cu", "net": str}],
  "vias": [{"x": float, "y": float, "from_layer": int, "to_layer": int, "diameter": float, "drill": float}]
}

CRITICAL: You MUST write the 'design_reasoning' FIRST. Think like a professional engineer (Gemini/Claude style) before providing data. NO empty arrays. Return ONLY valid JSON."""


def validate_pcb_output(design_data: dict) -> dict:
    """Validate PCB output from LLM."""
    errors = []
    board_config = design_data.get("board_config", {})
    components = design_data.get("placed_components", [])
    nets = design_data.get("nets", [])
    tracks = design_data.get("tracks", [])
    
    if not board_config:
        errors.append("board_config is empty")
    elif board_config.get("width_mm", 0) <= 0 or board_config.get("height_mm", 0) <= 0:
        errors.append("Invalid board dimensions")
    
    if not components or len(components) == 0:
        errors.append("No components placed")
    if not nets or len(nets) == 0:
        errors.append("No nets defined")
    if not tracks or len(tracks) == 0:
        errors.append("No tracks routed")
    
    component_ids = {c.get("id") for c in components if c.get("id")}
    for net in nets:
        for pin in net.get("pins", []):
            cid = pin.get("component_id")
            if cid and cid not in component_ids:
                errors.append(f"Net '{net.get('name')}' references unknown component '{cid}'")
    
    return {"valid": len(errors) == 0, "errors": errors}


# ━━ Redis Connection ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

# ━━ WebSocket Support ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        self.pubsub_task = None

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        
        # Start listening for Redis messages if not already
        if not self.pubsub_task:
            self.pubsub_task = asyncio.create_task(self._listen_to_redis())

    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self.active_connections:
            if websocket in self.active_connections[job_id]:
                self.active_connections[job_id].remove(websocket)

    async def _listen_to_redis(self):
        """Listen to Redis Pub/Sub and broadcast to relevant WebSockets."""
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("pcb_jobs_updates")
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                job_id = data.get("job_id")
                if job_id in self.active_connections:
                    for connection in self.active_connections[job_id]:
                        try:
                            await connection.send_json(data)
                        except:
                            pass

manager = ConnectionManager()

@router.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await manager.connect(websocket, job_id)
    try:
        # Fetch initial state from Redis
        job_data = await redis_client.get(f"job:{job_id}")
        if job_data:
            await websocket.send_json(json.loads(job_data))
        
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, job_id)

async def update_job_status(job_id: str, update: dict):
    """Persist job state in Redis and broadcast via Pub/Sub."""
    job_key = f"job:{job_id}"
    
    # Get current state
    current = await redis_client.get(job_key)
    job_state = json.loads(current) if current else {"job_id": job_id}
    
    # Update and save
    job_state.update(update)
    await redis_client.setex(job_key, 86400, json.dumps(job_state)) # TTL 24h
    
    # Broadcast
    await redis_client.publish("pcb_jobs_updates", json.dumps(job_state))


@router.post("/generate-pcb")
@limiter.limit("5/minute")
async def generate_pcb(
    request: Request,
    body: PCBGenerateRequest,
    x_nvidia_api_key: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a complete PCB design - queued as Celery task."""
    if body.input_type not in ["text", "bom_netlist", "existing_design"]:
        raise HTTPException(status_code=400, detail="Invalid input_type")

    job_id = uuid.uuid4()
    request_data = {
        "input_type": body.input_type,
        "description": body.description,
        "components": body.components,
        "nets": body.nets,
        "file_type": body.file_type,
        "file_url": body.file_url,
        "board_config": body.board_config.model_dump() if body.board_config else {},
        "user_id": str(current_user.id),
    }

    # Persist job in database
    job = Job(
        id=job_id,
        user_id=current_user.id,
        job_type="pcb_generation",
        status="queued",
        progress=0.0,
        input_data=request_data,
        stage="queued",
        retries=0,
        max_retries=3,
    )
    db.add(job)
    await db.commit()

    # Queue Celery task
    from services.ai_service.tasks import generate_pcb_task
    generate_pcb_task.delay(str(job_id), request_data, str(current_user.id), x_nvidia_api_key)

    return {
        "job_id": str(job_id),
        "status": "queued",
        "message": "PCB generation queued",
        "links": {
            "self": f"/api/v1/ai/jobs/{job_id}",
            "cancel": f"/api/v1/ai/jobs/{job_id}/cancel",
        },
    }


@router.get("/jobs", response_model=PaginatedResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's jobs."""
    from sqlalchemy import func

    query = select(Job).where(Job.user_id == current_user.id)
    if status:
        query = query.where(Job.status == status)
    query = query.order_by(Job.created_at.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "items": [JobResponse.model_validate(j).model_dump() for j in jobs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": offset + len(jobs) < total,
    }


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get job status from database (primary source of truth)."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return JobResponse.model_validate(job)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a queued or running job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if job.status not in ["queued", "running"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{job.status}'")

    job.status = "cancelled"
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()

    # Also revoke Celery task if possible
    try:
        from shared.celery_app import celery_app
        celery_app.control.revoke(str(job_id), terminate=True)
    except Exception:
        pass

    return {"job_id": str(job_id), "status": "cancelled"}
