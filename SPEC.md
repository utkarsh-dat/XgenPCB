# XgenPCB Implementation Specification

## Phase 1: MVP (Week 1-2)

### 1.1 Frontend Cleanup & Enhancement

**Files to modify:**
- `frontend/apps/web/src/pages/Dashboard.tsx` — Clean up + add design cards
- `frontend/apps/web/src/pages/Editor.tsx` — Integrate basic canvas
- `frontend/apps/web/src/components/ChatInterface.tsx` — Connect to AI service

**MVP Features:**
- [ ] Design list/create/delete
- [ ] Basic PCB canvas (read-only visual)
- [ ] AI chat panel (real-time)
- [ ] Simple DRC display
- [ ] Export to JSON/KiCad

**Frontend Tech Stack:**
- React 19 + TypeScript
- Zustand (existing)
- Tailwind CSS (existing)
- TLD Canvas for PCB rendering (new)

### 1.2 Backend Integration

**Files to modify:**
- `backend/services/ai_service/routes.py` — Ensure RAG + feedback integration
- `backend/services/eda_service/routes.py` — DRC + Gerber generation
- `backend/services/project_service/routes.py` — CRUD operations

**API Endpoints Required:**
```
POST /api/v1/projects/          — Create project
GET  /api/v1/projects/          — List projects
GET  /api/v1/projects/{id}      — Get project
PUT  /api/v1/projects/{id}      — Update project
DELETE /api/v1/projects/{id}     — Delete project
POST /api/v1/designs/          — Create design
GET  /api/v1/designs/{id}       — Get design
PUT  /api/v1/designs/{id}       — Update design
POST /api/v1/ai/chat           — AI chat
POST /api/v1/ai/intent         — Intent parsing
POST /api/v1/ai/auto-fix      — Auto-fix DRC
POST /api/v1/ai/design-review — Design review
POST /api/v1/ai/feedback      — Submit feedback
POST /api/v1/eda/drc          — Run DRC
```

### 1.3 Database Schema

**Add to migrations:**
```sql
-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    team_id UUID,
    visibility VARCHAR(50),
    tags JSONB,
    created_by UUID,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Designs  
CREATE TABLE designs (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    name VARCHAR(255),
    board_config JSONB,
    schematic_data JSONB,
    pcb_layout JSONB,
    constraints JSONB,
    version INTEGER,
    status VARCHAR(50),
    created_by UUID,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- AI Feedback
ALTER TABLE ai_generations ADD COLUMN feedback JSONB;
```

### 1.4 Deployment Config

**Vercel (Frontend):**
- `vercel.json` in frontend/apps/web
- Build: `npm run build`
- Output: `.output`

**Render/Railway (Backend):**
- Dockerfile already exists
- Add: `gunicorn` to requirements

---

## Phase 2: Pro Features (Week 3-4)

### 2.1 Domain-Adapted Model

**Fine-tuning Pipeline:**
```bash
# 1. Collect feedback data
python -c "
from backend.services.ai_service.routes import export_feedback_for_finetuning
# Export to data/pcb_feedback_dataset.json
"

# 2. Fine-tune with QLoRA
python rl_training/finetune.py \
    --base-model meta-llama/Llama-3.1-8B-Instruct \
    --train-file data/pcb_feedback_dataset.json \
    --output-dir models/xgenpcb-lora-pro

# 3. Deploy as HuggingFace Space or local inference
```

### 2.2 RL Routing Integration

**Backend endpoint:**
```python
@router.post("/ai/route")
async def route_pcb(request: RouteRequest):
    """Run RL routing on design."""
    from rl_training.environment import PCBRoutingEnv, RoutingConfig
    from rl_training.agent import RoutingAgent
    
    # Load trained agent
    agent = RoutingAgent()
    agent.load("models/routing_agent.pt")
    
    # Run routing
    env = PCBRoutingEnv()
    state = env.reset(netlist=request.nets)
    
    for _ in range(1000):
        action = agent.select_eval_action(state)
        state, reward, done, info = env.step(action)
        if done:
            break
    
    return {"layout": state.routed_tracks, "metrics": env.metrics}
```

### 2.3 Enhanced DRC

**Add to EDA service:**
```python
@router.post("/eda/validate")
async def validate_design(request: ValidateRequest):
    """Comprehensive DFM validation."""
    checks = [
        "trace_clearance",
        "trace_width",
        "via_spacing",
        "annular_ring",
        "silkscreen_clearance",
        "solder_mask_bridge",
        "component_spacing",
        "high_speed_rules",
    ]
    results = []
    for check in checks:
        result = await run_check(check, request.design_data)
        results.append(result)
    
    return {
        "overall_pass": all(r["passed"] for r in results),
        "checks": results,
    }
```

---

## Phase 3: Scale (Month 2+)

### 3.1 Multitenancy

**Team-based permissions:**
```python
@router.post("/teams/")
async def create_team(request: TeamCreate, db: AsyncSession):
    team = Team(
        name=request.name,
        owner_id=current_user.id,
        plan_type="free",  # free, pro, enterprise
    )
    db.add(team)
    await db.commit()
    return team
```

### 3.2 Stripe Integration

**Pricing tiers:**
- Free: 3 designs/month
- Pro: $15/mo, unlimited designs
- Enterprise: Custom pricing

**Webhook endpoint:**
```python
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    event = stripe.Event.construct_from(
        request.json(), 
        stripe.api_key
    )
    
    if event.type == "customer.subscription.updated":
        # Update team plan_type
    elif event.type == "invoice.payment_failed":
        # Downgrade to free tier
    
    return {"status": "success"}
```

---

## Quick Start Commands

```bash
# Development
make db-up
make dev

# Build & Deploy
cd frontend/apps/web
npm run build
vercel deploy --prod

# Backend (Render/Railway)
git push origin main  # Auto-deploy

# Training
make generate-data
make build-rag
make train-rl
```

---

## File Priorities

### High Priority (Week 1)
1. `frontend/apps/web/src/pages/Dashboard.tsx` — MVP design list
2. `frontend/apps/web/src/pages/Editor.tsx` — Basic canvas
3. `backend/services/project_service/routes.py` — Full CRUD
4. Database migration script

### Medium Priority (Week 2)
1. `frontend/apps/web/src/components/ChatInterface.tsx` — AI chat
2. `backend/services/ai_service/routes.py` — RAG integration
3. `backend/services/eda_service/routes.py` — DRC endpoint

### Lower Priority (Week 3+)
1. RL routing integration
2. Domain adaptation
3. Stripe integration