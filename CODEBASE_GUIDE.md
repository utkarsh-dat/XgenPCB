# XgenPCB — Codebase Architecture & Guide

*Last updated: 2026-04-28*

## Overview

XgenPCB is a production-grade AI-powered PCB design platform that converts natural language prompts into complete PCB designs through a 6-stage AI agent pipeline with physics-aware validation.

```
User Prompt -> [6-Stage AI Pipeline] -> Physics Validation -> Manufacturing Output
     ^              |                     |                    |
  Frontend     NVIDIA NIM LLM       DRC/DFM/SI           Gerber/Quotes
  (React 19)   (Llama Nemotron)    (IPC Standards)      (JLCPCB/PCBWay)
```

---

## Directory Structure

### Backend (`backend/`)

```
backend/
  services/
    gateway/main.py              -- FastAPI app, mounts 7 routers
    ai_service/routes.py         -- /api/v1/ai/*  (generate-pcb, chat, jobs)
    ai_service/tasks.py          -- Celery pipeline tasks (6-stage agent)
    analytics_service/           -- AnalyticsService class + routes
    component_service/routes.py  -- /api/v1/components/*
    eda_service/routes.py        -- /api/v1/eda/*  (DRC, Gerber, KiCad export)
    eda_service/tasks.py         -- Celery EDA tasks
    eda_service/gerber_service.py-- Gerber generation
    fab_service/routes.py        -- /api/v1/fab/*  (quotes, 3 fabricators)
    project_service/routes.py    -- /api/v1/projects/*  (CRUD projects/designs)
    user_service/routes.py       -- /api/v1/auth/*  (register, login, profile)
    comparison_service.py        -- Design diff engine
    storage_service.py           -- Local file storage

  shared/
    agents/                      -- 6-stage AI pipeline
      base.py                    -- BaseAgent, PipelineContext, GateResult
      orchestrator.py            -- AgentOrchestrator (3 retries, backtracking)
      stages/
        intent.py                -- Stage 0: NLP -> structured requirements
        schematic.py             -- Stage 1: Requirements -> schematic + ERC
        placement.py             -- Stage 2: Schematic -> component placement
        routing.py               -- Stage 3: Placement -> trace routing
        validation.py            -- Stage 4: DRC + DFM + SI validation
        output.py                -- Stage 5: Assemble final deliverables
    validation/                  -- Physics-aware engines
      drc_engine.py              -- IPC Class 1/2/3, JLCPCB/PCBWay rules
      dfm_engine.py              -- Fabrication + assembly checks
      si_analyzer.py             -- Signal integrity (impedance, crosstalk)
      explainability.py          -- Human-readable design justifications
      multi_candidate.py         -- 3-5 parallel layout generations
    middleware/
      auth.py                    -- JWT auth, bcrypt, get_current_user
      correlation.py             -- X-Correlation-ID propagation
      error_handler.py           -- Consistent JSON error format
      idempotency.py             -- Idempotency-Key enforcement
      rate_limit.py              -- Tiered rate limiting (Free/Pro/Enterprise)
    models/__init__.py           -- 16 SQLAlchemy ORM models
    schemas/__init__.py          -- Pydantic request/response schemas
    config.py                    -- Settings (env vars, DB, Redis, AI keys)
    database.py                  -- Async SQLAlchemy engine + session
    celery_app.py                -- Celery config (2 queues: ai, eda)
    logging_config.py            -- Structlog JSON logging
    clients/
      jlcpcb.py                  -- JLCPCB component API client
      lcsc.py                    -- LCSC component API client
      kicad.py                   -- KiCad footprint library client

  init_db.py                     -- Auto-creates tables on startup
  start.sh                       -- Startup: init_db -> uvicorn
  Dockerfile                     -- Ubuntu 22.04 + KiCad 9 + Python 3.11
  footprint_index.json           -- 30k+ KiCad footprints
```

### Frontend (`frontend/apps/web/`)

```
src/
  App.tsx                        -- BrowserRouter with 14 routes
  main.tsx                       -- ReactDOM entry
  index.css                      -- Global styles + Tailwind directives

  pages/                         -- 14 page components
    LandingPage.tsx              -- Marketing hero, features, pricing, CTA  (static)
    Dashboard.tsx                -- AI prompt section + project grid  (API calls)
    Editor.tsx                   -- 2D/3D PCB editor with AI chat  (API calls)
    SchematicEditor.tsx          -- Schematic view prototype  (static demo)
    Templates.tsx                -- Template gallery  (static)
    Viewer3D.tsx                 -- 3D board viewer  (static)
    DesignReview.tsx             -- Design review feed  (static)
    Marketplace.tsx              -- Component marketplace  (static)
    Pricing.tsx                  -- Pricing plans  (static)
    Community.tsx                -- Community hub  (static)
    Forum.tsx                    -- Forum listing  (static)
    TutorialView.tsx             -- Tutorials  (static)
    UserProfile.tsx              -- User profile  (static)
    AdminPanel.tsx               -- Admin dashboard  (static)

  components/
    ai/ChatInterface.tsx         -- AI chat panel (NVIDIA NIM integration)
    editor/
      PCBCanvas.tsx              -- 2D PCB canvas
      ThreeDViewer.tsx           -- 3D board viewer
      ComponentLibrary.tsx       -- Component sidebar
      LayerPanel.tsx             -- Layer visibility panel
      PropertyPanel.tsx          -- Selected object properties
    ui/                          -- Shadcn-inspired UI primitives
      badge.tsx, button.tsx, card.tsx, input.tsx, tabs.tsx

  lib/
    api/client.ts                -- Full API client (all endpoints, retry logic)
    api/config.ts                -- API base URL config
    utils.ts                     -- cn() utility (clsx + tailwind-merge)

  stores/index.ts                -- Zustand: DesignStore, UIStore, AIStore, UserStore
  engines/                       -- Engine coordinator pattern
```

### Infrastructure (`infra/`)

```
nginx/nginx.conf                  -- Main Nginx config (gzip, rate limits, upstreams)
nginx/default.conf                 -- Frontend SPA + API proxy + WebSocket
prometheus/prometheus.yml         -- Metrics scraping config
grafana/provisioning/             -- Datasources + dashboards
```

---

## API Endpoints

### Health

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Basic health |
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness (DB check) |
| GET | `/health/deep` | Deep check (DB + Redis + Celery) |

### Authentication (`/api/v1/auth`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/register` | Register new user |
| POST | `/login` | Login, returns JWT token |
| GET | `/me` | Current user profile |
| PATCH | `/me` | Update profile |
| POST | `/teams` | Create team |
| GET | `/teams` | List user's teams |

### Projects & Designs (`/api/v1/projects`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/` | Create project |
| GET | `/` | List user's projects |
| GET | `/{id}` | Get project |
| PATCH | `/{id}` | Update project |
| DELETE | `/{id}` | Delete project |
| POST | `/{id}/designs` | Create design in project |
| GET | `/{id}/designs` | List project designs |
| GET | `/{id}/designs/{did}` | Get design |
| PATCH | `/{id}/designs/{did}` | Update design |

### AI Services (`/api/v1/ai`) — Core PCB Generation

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/generate-pcb` | Generate complete PCB from text/BOM/existing design, returns job_id |
| GET | `/jobs` | List user's jobs |
| GET | `/jobs/{id}` | Poll job status (progress, stage, output_data) |
| POST | `/jobs/{id}/cancel` | Cancel running job |
| POST | `/parse-intent` | Parse natural language into design actions |
| POST | `/chat` | AI chat with design assistant |
| POST | `/design-review` | Comprehensive AI design review |
| WS | `/ws/jobs/{id}` | Real-time WebSocket job updates |

### EDA Services (`/api/v1/eda`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/drc` | Run Design Rule Check |
| POST | `/generate-gerber` | Generate Gerber files |
| GET | `/download/{id}` | Download .kicad_pcb file |
| GET | `/job/{id}` | EDA job status |
| POST | `/components/search` | Search component library |

### Components (`/api/v1/components`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/search?q=` | Search JLCPCB/LCSC components |
| GET | `/categories` | List component categories |
| GET | `/footprints/{pkg}` | Footprints by package type |
| GET | `/{id}` | Component details |

### Fabrication (`/api/v1/fab`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/quotes` | Get quotes from multiple fabricators |
| GET | `/fabricators` | List all fabricators |
| GET | `/capabilities/{name}` | Fab capabilities |

### Analytics (`/api/v1/analytics`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/dashboard` | User dashboard analytics |
| GET | `/designs/{id}/metrics` | Design metrics |
| GET | `/platform` | Platform-wide stats (admin) |

## 6-Stage AI Pipeline

```
User Prompt (natural language)
    |
    v
Stage 0: Intent Parser  -> Requirements Gate (confidence >= 0.7)
    |
    v
Stage 1: Schematic Agent -> ERC Gate (0 critical electrical errors)
    |
    v
Stage 2: Placement Agent -> Thermal/Fit Gate
    |
    v
Stage 3: Routing Agent   -> DRC Gate (0 critical violations, all nets routed)
    |
    v
Stage 4: Validation Agent -> DFM/SI Gate (score >= 60, ready for fabrication)
    |
    v
Stage 5: Output Agent    -> Completeness Gate (all deliverables present)
    |
    v
Post-Pipeline: Physics DRC + DFM + SI Analysis + XAI Justifications + Multi-Candidate
    |
    v
KiCad .kicad_pcb file + Gerber + BOM + Quotes
```

Key behaviors:
- Max 3 retries per stage, then backtrack to previous stage
- Each stage validates via specialized gate check
- Pipeline context shared across all stages
- Job status persisted in PostgreSQL (not just Redis)

---

## Data Models (16 tables)

| Model | Table | Purpose |
|-------|-------|---------|
| User | users | User accounts, subscription tiers |
| Team | teams | Team collaboration |
| TeamMember | team_members | Team membership |
| Project | projects | User projects |
| Design | designs | PCB designs (board_config, schematic, pcb_layout, constraints) |
| DesignVersion | design_versions | Version history snapshots |
| AIGeneration | ai_generations | AI generation records with feedback for fine-tuning |
| AICandidate | ai_candidates | Multi-candidate layouts |
| Component | components | Component library (MPN, footprints, datasheets, pricing) |
| ComponentPricing | component_pricing | Distributor pricing data |
| Fabricator | fabricators | Supported PCB manufacturers |
| FabQuote | fab_quotes | Historical quote records |
| Job | jobs | Background job tracking (pipeline, Gerber, DRC) |
| IdempotencyKey | idempotency_keys | Safe retry mechanism (24h TTL) |
| Subscription | subscriptions | Stripe subscription data |
| UsageLog | usage_logs | API usage tracking |
| Notification | notifications | User notifications |
| AuditLog | audit_logs | Security audit trail |

---

## How to Generate a PCB

### From the Dashboard (Recommended)

1. Navigate to `http://localhost:8080/dashboard`
2. Type your PCB requirements in the AI prompt textarea
   - Example: *"A compact ESP32 temperature sensor board with USB-C power, OLED display, and I2C sensor"*
3. Click **"Generate Full PCB"**
4. Watch the progress bar across 6 pipeline stages
5. When complete, the editor opens with your generated PCB design

### From the API

```bash
# Register first (creates JWT token)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","full_name":"Test User"}'

# Start a PCB generation job
curl -X POST http://localhost:8000/api/v1/ai/generate-pcb \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -d '{
    "input_type": "text",
    "description": "ESP32 IoT board with USB-C, temperature sensor, and WiFi",
    "board_config": {"layers": 2, "width_mm": 50, "height_mm": 50}
  }'
# Returns: {"job_id": "...", "status": "queued", ...}

# Poll job status
curl http://localhost:8000/api/v1/ai/jobs/<JOB_ID> \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>"
# Returns: {"id": "...", "status": "running", "progress": 0.45, "stage": "placement", ...}
```

### The pipeline output includes

- `board_config` — dimensions, layers, material, surface finish
- `placed_components` — all parts with positions and footprints
- `nets` — all electrical connections between pins
- `tracks` — all routed traces with widths and layers
- `vias` — layer transition vias with drill sizes
- `validation.drc` — DRC violations, score, IPC compliance
- `validation.dfm` — DFM issues, copper balance, test point coverage
- `validation.si` — impedance issues, crosstalk, length mismatch
- `explanation` — human-readable design philosophy, risk assessment, optimization notes
- `candidates` — alternative layout variants (if multi_candidate enabled)

---

## Where PCB Generation Lives in the Frontend

The **Dashboard page** (`frontend/apps/web/src/pages/Dashboard.tsx`) has a prominent "AI POWERED" section at the top with:

1. A textarea with placeholder: *"e.g., An ESP32 based IoT weather station with USB-C, 2 LEDs, and a reset button..."*
2. A **"Generate Full PCB"** button with a Wand2 icon
3. When clicked, it calls `api.generatePCB()` which POSTs to `/api/v1/ai/generate-pcb`
4. The API returns a `job_id`, and the frontend **polls** `api.getJobStatus()` every 3 seconds
5. Progress is shown with a progress bar and stage name (e.g., "Executing placement...")
6. On completion, it navigates to `/editor/ai-generated/design-1`

This is the ONLY place in the frontend that triggers PCB generation.

The **Editor page** (`pages/Editor.tsx`) is where you view and interact with the generated PCB. It has:
- 2D/3D view modes (PCBCanvas / ThreeDViewer)
- Component library sidebar
- Layer visibility panel
- Properties panel
- AI chat panel (Calls `/api/v1/ai/chat`)

---

## Frontend Page States

| Page | API Integration | Status |
|------|----------------|--------|
| Dashboard | YES (projects, generate-pcb, jobs) | Working |
| Editor | YES (design loading, AI chat) | Working |
| LandingPage | NO | Static marketing page |
| SchematicEditor | NO | Hardcoded demo data (ESP32, AMS1117, USB-C symbols) |
| Templates | NO | Static template cards |
| Viewer3D | NO | Static Three.js 3D scene |
| DesignReview | NO | Static review cards |
| Marketplace | NO | Static product listings |
| Pricing | NO | Static pricing plans |
| Community | NO | Static section cards |
| Forum | NO | Static forum posts |
| TutorialView | NO | Static tutorial cards |
| UserProfile | NO | Static profile data |
| AdminPanel | NO | Static admin data |

---

## Docker Services

```
xgenpcb-frontend    Port 8080  -- Nginx serving React SPA + API proxy
xgenpcb-backend     Port 8000  -- FastAPI with 7 routers, 35+ endpoints
xgenpcb-postgres    Port 5432  -- PostgreSQL 16 with 16 tables
xgenpcb-redis       Port 6379  -- Celery broker + job cache + Pub/Sub
celery-worker-ai               -- AI pipeline queue (1h timeout, 2 concurrency)
celery-worker-eda              -- EDA queue (Gerber generation, DRC)
celery-beat                    -- Scheduled task runner
nginx               Port 80    -- Reverse proxy with gzip, rate limiting
prometheus          Port 9090  -- Metrics collection
grafana             Port 3000  -- Dashboards
minio               Port 9000  -- Object storage (optional)
```

---

## Running the Stack

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env: add your NVIDIA_API_KEY

# 2. Start core services
docker-compose up -d --build postgres redis backend frontend

# 3. Verify health
curl http://localhost:8000/health        # Backend
curl http://localhost:8080/health        # Frontend

# 4. Start Celery workers (required for PCB generation)
docker-compose up -d celery-worker-ai celery-worker-eda

# 5. Open web app
# Go to http://localhost:8080/dashboard
# Type your PCB requirements and click "Generate Full PCB"

# 6. Monitor logs
docker-compose logs -f backend
docker-compose logs -f celery-worker-ai
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn (4 workers) |
| Frontend | React 19, TypeScript 5.6, Vite 6, Tailwind CSS 3 |
| Database | PostgreSQL 16, SQLAlchemy 2.0 (async) |
| Cache/Queue | Redis 7, Celery 5 |
| AI/LLM | NVIDIA NIM (Llama 3.1 Nemotron 70B) |
| EDA | KiCad 9 CLI |
| Container | Docker, Docker Compose |
| Monitoring | Prometheus, Grafana |
| Logging | Structlog (JSON), correlation IDs |
| Auth | JWT (python-jose + bcrypt) |
| Rate Limiting | SlowAPI (Free: 10/min, Pro: 60/min, Enterprise: 300/min) |

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `backend/services/gateway/main.py` | App factory with all middleware and router mounts |
| `backend/services/ai_service/routes.py` | AI endpoints including generate-pcb |
| `backend/services/ai_service/tasks.py` | Full 6-stage pipeline as Celery task |
| `backend/shared/agents/orchestrator.py` | Pipeline executor with backtracking |
| `backend/shared/validation/drc_engine.py` | Physics-aware DRC (531 lines) |
| `backend/shared/models/__init__.py` | All 16 database models |
| `backend/shared/schemas/__init__.py` | All Pydantic schemas |
| `backend/init_db.py` | Database table creation script |
| `frontend/apps/web/src/pages/Dashboard.tsx` | Main AI prompt + PCB generation UI |
| `frontend/apps/web/src/pages/Editor.tsx` | PCB editor with 2D/3D views |
| `frontend/apps/web/src/lib/api/client.ts` | Complete API client |
| `docker-compose.yml` | Full Docker deployment |
