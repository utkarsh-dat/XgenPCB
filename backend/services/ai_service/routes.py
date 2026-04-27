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
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import asyncio
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


from shared.config import get_settings
from shared.database import get_db
from shared.middleware.auth import get_current_user
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
async def generate_pcb(
    request: PCBGenerateRequest,
    background_tasks: BackgroundTasks,
    x_nvidia_api_key: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a complete PCB design - processes in background."""
    import time
    
    if request.input_type not in ["text", "bom_netlist", "existing_design"]:
        raise HTTPException(status_code=400, detail="Invalid input_type")
    
    job_id = str(uuid.uuid4())
    request_data = {
        "input_type": request.input_type,
        "description": request.description,
        "components": request.components,
        "nets": request.nets,
        "file_type": request.file_type,
        "file_url": request.file_url,
        "board_config": request.board_config.model_dump() if request.board_config else {},
        "user_id": str(current_user.id),
    }
    
    await update_job_status(job_id, {
        "status": "queued",
        "progress": 0.0,
        "request": request_data,
    })
    
    background_tasks.add_task(_generate_pcb_task, job_id, request_data, current_user.id, x_nvidia_api_key)
    
    return {"job_id": job_id, "status": "queued", "message": "PCB generation started"}


@router.get("/generate-pcb/{job_id}")
async def get_generate_pcb_status(job_id: str):
    """Check status of PCB generation job from Redis."""
    job_data = await redis_client.get(f"job:{job_id}")
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(job_data)


async def _generate_pcb_task(job_id: str, request_data: dict, user_id: uuid.UUID, api_key: Optional[str] = None):
    """Background task for PCB generation with real KiCad validation + retry."""
    from sqlalchemy import select
    
    try:
        await update_job_status(job_id, {"status": "processing", "progress": 0.1})
        
        input_type = request_data["input_type"]
        
        if input_type == "text":
            user_message = f"""Generate a complete PCB design for this description:
{request_data.get('description', '')}

Board config:
{json.dumps(request_data.get('board_config', {}), indent=2)}"""
        
        elif input_type == "bom_netlist":
            component_list = json.dumps(request_data.get("components", []), indent=2)
            net_list = json.dumps(request_data.get("nets", []), indent=2)
            user_message = f"""Generate a complete PCB design from BOM and netlist:

Components:
{component_list}

Netlist:
{net_list}

Board config:
{json.dumps(request_data.get('board_config', {}), indent=2)}"""
        
        else:
            user_message = f"""Convert existing design:
File type: {request_data.get('file_type')}
File URL: {request_data.get('file_url', 'content to be provided')}

Board config:
{json.dumps(request_data.get('board_config', {}), indent=2)}"""
        
        await update_job_status(job_id, {"progress": 0.2})
        
        # ── Initialize AI Context ────────────────────────────
        messages = [
            {"role": "system", "content": PCB_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        actual_api_key = api_key or settings.nvidia_api_key
        # ──────────────────────────────────────────────────
        
        MAX_RETRIES = 5
        design_data = None
        last_validation = {"valid": False, "errors": []}
        last_drc_errors = []
        import traceback
        
        for attempt in range(MAX_RETRIES + 1):
            print(f"LLM attempt {attempt + 1}/{MAX_RETRIES + 1} for job {job_id}...")
            
            # If this is a retry, append feedback to the conversation history
            if attempt > 0:
                feedback = "Previous attempt had issues:\n"
                if not last_validation.get("valid"):
                    feedback += f"Format Errors: {last_validation.get('errors', [])}\n"
                if last_drc_errors:
                    feedback += "DRC Violations (Fix these by moving components or adjusting traces!):\n"
                    for v in last_drc_errors:
                        feedback += f"- {v['type']}: {v['message']} at {v.get('location')}\n"
                
                feedback += "\nRe-generate a COMPLETE PCB with all components, nets, and tracks, fixing the above issues."
                messages.append({"role": "user", "content": feedback})
                
                await update_job_status(job_id, {"status": "self_correcting", "message": f"Retry {attempt}/5: Resolving violations..."})
            
            try:
                # ── Neural Streaming Engine ──────────────────────
                full_response = ""
                reasoning_captured = False
                in_reasoning_block = False
                
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST",
                        f"{settings.nvidia_base_url}/chat/completions",
                        json={
                            "model": settings.nvidia_model,
                            "messages": messages,
                            "temperature": 0.1,
                            "max_tokens": 4096,
                            "stream": True,
                            "response_format": {"type": "json_object"}
                        },
                        headers={
                            "Authorization": f"Bearer {actual_api_key}",
                            "Accept": "text/event-stream"
                        }
                    ) as response:
                        print(f"DEBUG: NVIDIA Stream Response Status: {response.status_code}")
                        async for line in response.aiter_lines():
                            if line.startswith("data: ") and not line.endswith("[DONE]"):
                                try:
                                    chunk = json.loads(line[6:])
                                    content = chunk["choices"][0]["delta"].get("content", "")
                                    full_response += content
                                    
                                    # ── Single-Use Precision Catcher ──────────────
                                    if not reasoning_captured:
                                        if not in_reasoning_block:
                                            # Look for the start of the reasoning field
                                            if '"design_reasoning"' in full_response and '"' in full_response.split('"design_reasoning"')[-1].split(':')[-1]:
                                                in_reasoning_block = True
                                                print(f"DEBUG: [REASONING STARTED]")
                                                # Send only the part that is actually reasoning
                                                initial_part = full_response.split('"design_reasoning"')[-1].split('"')[-1]
                                                if initial_part:
                                                    await update_job_status(job_id, {"design_reasoning_delta": initial_part})
                                        else:
                                            # We are streaming reasoning. Stop if we hit the end.
                                            if '",' in full_response or '"}' in full_response:
                                                in_reasoning_block = False
                                                reasoning_captured = True # LOCK THE DOOR FOREVER
                                                print(f"DEBUG: [REASONING FINISHED]")
                                                if '",' in content: content = content.split('",')[0]
                                                elif '"}' in content: content = content.split('"}')[0]
                                                elif '"' in content: content = content.split('"')[0]
                                            
                                            if (in_reasoning_block or content) and content.strip() not in ['":', '']:
                                                await update_job_status(job_id, {"design_reasoning_delta": content})
                                    # ──────────────────────────────────────────────
                                except:
                                    continue
                
                raw_content = full_response
                print(f"DEBUG: FULL AI RESPONSE (first 500 chars):\n{raw_content[:500]}")
                print(f"DEBUG: FULL AI RESPONSE (last 500 chars):\n{raw_content[-500:]}")
                
                # ── Robust JSON Extraction ──────────────────────────
                start_idx = raw_content.find("{")
                end_idx = raw_content.rfind("}")
                
                if start_idx != -1 and end_idx != -1:
                    json_str = raw_content[start_idx:end_idx + 1]
                    design_data = json.loads(json_str)
                    
                    # 🔍 Aggressive Validation
                    found_keys = list(design_data.keys())
                    print(f"DEBUG: Parsed JSON keys: {found_keys}")
                    
                    if not any(k in design_data for k in ["board_config", "placed_components", "pcb_layout", "components"]):
                        print(f"DEBUG: Rejected minimal/empty JSON. Found keys: {found_keys}")
                        design_data = {}
                    else:
                        print(f"DEBUG: Successfully validated design data structure.")
                        # ── Cement Reasoning in Status ──────────────────
                        reasoning = design_data.get("design_reasoning", "")
                        if reasoning:
                            await update_job_status(job_id, {
                                "message": "Strategy finalized.",
                                "design_reasoning": reasoning
                            })
                        # ──────────────────────────────────────────────
                else:
                    design_data = {}
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                last_validation = {"valid": False, "errors": [f"Invalid JSON: {e}"]}
                if attempt == MAX_RETRIES:
                    await update_job_status(job_id, {
                        "status": "failed",
                        "error": "Failed to generate valid PCB after multiple attempts.",
                    })
                    return
                continue
            print(f"Validation (attempt {attempt + 1}): valid={last_validation['valid']}, errors={last_validation['errors']}")
            
            if last_validation["valid"]:
                # Run Real KiCad DRC check
                await update_job_status(job_id, {"status": "verifying", "message": "Running deterministic KiCad DRC..."})
                
                from services.eda_service.routes import run_drc
                from shared.schemas import DRCRequest
                
                drc_result = await run_drc(DRCRequest(design_data=design_data))
                last_drc_errors = [v for v in drc_result.violations if v.get("severity") == "error"]
                
                if not last_drc_errors:
                    await update_job_status(job_id, {"status": "verified", "message": "DRC Passed! Finalizing design..."})
                    break
                else:
                    # Append DRC errors to history for next attempt
                    error_msg = f"Your last design had DRC errors: {', '.join([e['message'] for e in last_drc_errors[:3]])}. Please FIX these in your next JSON output."
                    messages.append({"role": "assistant", "content": raw_content})
                    messages.append({"role": "user", "content": error_msg})
                    await update_job_status(job_id, {"status": "violating", "message": f"Found {len(last_drc_errors)} DRC violations. Auto-fixing..."})
            else:
                # Append Validation errors to history for next attempt
                error_msg = f"Your last JSON was invalid: {', '.join(last_validation['errors'])}. Please provide a FULL industrial-grade board design."
                messages.append({"role": "assistant", "content": raw_content})
                messages.append({"role": "user", "content": error_msg})
            
            if attempt == MAX_RETRIES:
                print(f"Failed after {MAX_RETRIES + 1} attempts")
                await update_job_status(job_id, {
                    "status": "failed",
                    "error": "Generation incomplete after max retries",
                    "validation_errors": last_validation["errors"],
                    "partial_data": design_data,
                })
                return
        
        if not design_data or not last_validation.get("valid") or last_drc_errors:
            await update_job_status(job_id, {
                "status": "failed",
                "error": "No valid design data or DRC constraints failed after all attempts",
            })
            return
        
        await update_job_status(job_id, {"progress": 0.6})
        
        board_cfg = design_data.get("board_config", {})
        bc = request_data.get("board_config", {})
        for k, v in bc.items():
            if v is not None:
                board_cfg[k] = v
        design_data["board_config"] = board_cfg
        
        drc_rules = design_data.get("drc_rules", {})
        
        from shared.database import async_session_factory
        
        async with async_session_factory() as db:
            result_proj = await db.execute(
                select(Project).where(Project.created_by == user_id).order_by(Project.created_at.desc())
            )
            project = result_proj.scalar_one_or_none()
            if not project:
                project = Project(name="AI Generated", created_by=user_id)
                db.add(project)
                await db.flush()
            
            design = Design(
                name=f"PCB {int(time.time())}",
                project_id=project.id,
                board_config=board_cfg,
                schematic_data={"components": design_data.get("placed_components", []), "nets": design_data.get("nets", [])},
                design_reasoning=design_data.get("design_reasoning", "No reasoning provided."),
                pcb_layout={
                    "placed_components": design_data.get("placed_components", []),
                    "tracks": design_data.get("tracks", []),
                    "vias": design_data.get("vias", []),
                },
                created_by=user_id,
                status="generated",
            )
            db.add(design)
            await db.commit()
            await db.refresh(design)
            
            from services.storage_service import storage_service
            
            with tempfile.TemporaryDirectory() as tmpdir:
                project_path = Path(tmpdir) / "design"
                project_path.mkdir()
                from services.eda_service.routes import write_kicad_board
                kicad_path = write_kicad_board(project_path, board_cfg, design.pcb_layout)
                content = kicad_path.read_text()
                filename = f"{design.name}.kicad_pcb"
                storage_result = await storage_service.upload_dual(design.id, filename, content.encode("utf-8"), "application/octet-stream")
                design.local_path = storage_result["local_path"]
                design.minio_key = storage_result.get("minio_key")
                await db.commit()
            
            await update_job_status(job_id, {
                "status": "completed",
                "progress": 1.0,
                "design_id": str(design.id),
                "tokens_used": result.get("tokens", 0),
            })
    
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"ERROR in _generate_pcb_task: {error_msg}")
        await update_job_status(job_id, {
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
        })
