# ⚡ PCB Builder — AI-Powered Autonomous PCB Design Platform

World-class PCB design platform with AI-assisted routing, real-time DRC, 
3D preview, and instant fabrication quotes.

## 🏗️ Architecture

```
pcbbuilder/
├── backend/                    # Python/FastAPI microservices
│   ├── services/
│   │   ├── gateway/            # API Gateway (main entry point)
│   │   ├── user_service/       # Auth, profiles, teams
│   │   ├── project_service/    # Projects, designs, versions
│   │   ├── ai_service/         # LLM integration (GPT-4o)
│   │   ├── eda_service/        # KiCad integration, DRC, Gerber
│   │   └── fab_service/        # Fabricator quotes & ordering
│   ├── shared/
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic validation
│   │   ├── middleware/         # Auth, logging
│   │   ├── config.py           # Settings management
│   │   └── database.py         # Async DB engine
│   └── scripts/migrations/     # SQL migrations
├── frontend/apps/web/          # React + TypeScript + Vite
│   └── src/
│       ├── components/         # UI components (editor, chat, viewer)
│       ├── pages/              # Dashboard, Editor
│       ├── stores/             # Zustand state management
│       └── lib/api/            # API client
├── rl_training/                # TPU-ready RL pipeline
│   ├── environment.py          # PCB routing gymnasium env
│   ├── physics_reward.py       # FDTD + thermal rewards
│   └── pipeline.py             # PPO training loop
├── infra/k8s/                  # Kubernetes manifests
├── docker-compose.yml          # Local development stack
└── Makefile                    # Build automation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose

### 1. Clone & Configure
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start Infrastructure
```bash
make db-up
# Starts PostgreSQL, Redis, Elasticsearch, MinIO
```

### 3. Start Backend
```bash
cd backend
pip install -e ".[dev,ai]"
make dev
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 4. Start Frontend
```bash
cd frontend/apps/web
npm install
npm run dev
# Web app at http://localhost:5173
```

## 🧠 AI Features

| Feature | Status | Description |
|---------|--------|-------------|
| Intent Parser | ✅ Ready | NL → structured actions |
| Design Chat | ✅ Ready | Contextual AI assistant |
| Auto-Fix | ✅ Ready | LLM-generated DRC fixes |
| Design Review | ✅ Ready | Comprehensive AI review |
| RL Routing | 🔧 TPU-ready | Reinforcement learning router |

## 📐 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Login |
| GET | `/api/v1/projects/` | List projects |
| POST | `/api/v1/projects/` | Create project |
| POST | `/api/v1/ai/chat` | AI chat |
| POST | `/api/v1/ai/parse-intent` | Parse NL intent |
| POST | `/api/v1/ai/auto-fix` | Auto-fix violations |
| POST | `/api/v1/eda/drc` | Run DRC |
| POST | `/api/v1/eda/generate-gerber` | Generate Gerber |
| POST | `/api/v1/fab/quotes` | Get fab quotes |

## 🔧 Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, asyncpg
- **Frontend**: React 19, TypeScript, Vite, Zustand, Three.js
- **Database**: PostgreSQL 16, Redis 7, Elasticsearch 8
- **AI**: OpenAI GPT-4o, JAX/Haiku (RL)
- **Infrastructure**: Docker, Kubernetes, Terraform
- **EDA**: KiCad CLI integration

## 📄 License

Proprietary — All rights reserved.
# XgenPCB
# XgenPCB
