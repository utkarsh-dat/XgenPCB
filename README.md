# XgenPCB — AI-Powered Autonomous PCB Design Platform

## What is XgenPCB?

XgenPCB is an intelligent PCB design platform that combines traditional EDA tools with large language models to assist engineers through every stage of printed circuit board design — from schematic entry to manufacturing output.

Traditional PCB design tools force engineers to manually place components, route traces, run design rule checks, and iterate through violations. XgenPCB reimagines this workflow by embedding an AI assistant directly into the design process, capable of understanding natural language requests, generating design fixes, and even learning to route nets autonomously through reinforcement learning.

The platform targets three distinct users: hardware engineers who need faster iteration cycles, small teams without dedicated layout engineers, and educational institutions teaching PCB design.

## The Problem

PCB design remains a bottleneck in hardware development. A typical 4-layer board requires hundreds of manual routing decisions, each carrying electrical and manufacturability implications. Design rule violations demand iterative fixes. Gerbers must be validated before fabrication. Quotes must be solicited from multiple manufacturers.

Current EDA software automates schematic capture but provides limited intelligence beyond design rule checking. Engineers spend disproportionate time on mechanical tasks — placing decoupling capacitors, maintaining trace clearance, resolving DRC errors — rather than electrical optimization.

Meanwhile,manufacturing quotes are fragmented across dozens of fab houses, each with different capabilities and pricing models. Engineers juggle multiple vendor portals to find competitive quotes.

## The Solution

XgenPCB integrates five functional domains into a unified platform:

**1. Natural Language Design Intent**

Engineers describe what they want in plain English — "place the MCU near the USB connector" or "route the 12V power bus on the inner layers" — and the AI parses this into executable design actions. The intent parser maps natural language to structured operations: component placement, net routing, constraint application, or DRC execution.

**2. Contextual AI Design Assistant**

A conversational interface provides real-time guidance throughout the design process. The assistant understands the current board state — placed components, routed nets, DRC violations — and responds contextually. It suggests trace widths based on current requirements, recommends decoupling capacitor placement, explains violation root causes, and proposes alternative routing strategies.

**3. Autonomous DRC Resolution**

When design rule violations occur, the AI generates targeted fixes rather than forcing engineers to manually adjust geometry. By analyzing the violation type, the affected nets, and surrounding geometry, the auto-fix system proposes specific actions: move components, adjust clearances, modify trace widths, or add supplemental traces.

**4. Intelligent Design Review**

Before fabrication, the AI conducts a comprehensive review across multiple dimensions: schematic completeness, component placement ergonomics, routing density, manufacturing feasibility, and cost optimization. Each category receives a scored assessment with specific issues and actionable suggestions.

**5. Multi-Fabricator Quote Aggregation**

The platform connects to multiple fabrication vendors simultaneously, retrieving capability-matched quotes based on the design specifications. Quote requests are abstracted — engineers describe their requirements (layers, thickness, surface finish) and the system queries compatible fabricators.

## Reinforcement Learning for Routing

Beyond reactive assistance, XgenPCB explores autonomous routing through reinforcement learning. The RL subsystem models PCB routing as a sequential decision problem where an agent learns to navigate a multi-layer grid, placing traces to connect pins while avoiding obstacles.

The routing environment encodes the PCB state as a multi-channel grid: obstacle map, routed traces, target pins, and agent position. The agent receives rewards for completing net connections and penalties for collisions, inefficient routes, and via usage. Over training, the agent learns routing policies that balance completion speed against route quality, with the potential to match or exceed human layout efficiency for standardized topologies.

This subsystem targets future automation scenarios — auto-routing with human-like judgment rather than geometric optimization alone.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                       │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐   │
│  │Dashboard │  │ Editor   │  │    AI Chat Interface   │   │
│  └──────────┘  └──────────┘  └────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (FastAPI)                     │
│                    /api/v1/*                                │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────┬─────────┬──┴──┬─────────┬─────────┐
        ▼         ▼         ▼          ▼         ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│   User   │ │Project │ │  AI    │ │  EDA   │ │ Fabric  │
│ Service  │ │Service │ │Service │ │Service │ │ Service │
└──────────┘ └────────┘ └────────┘ └────────┘ └──────────┘
        │         │         │          │         │
        ▼         ▼         ▼          ▼         ▼
    PostgreSQL  │     OpenAI     KiCad     Fab Vendors
                │      API        CLI        (API)
                ▼
           S3/MinIO
```

**Service Definitions:**

- **Gateway Service** — API entry point with CORS, authentication middleware, and service router mounting.

- **User Service** — Handles registration, login (JWT + optional Google OAuth), team management, and subscription tiers.

- **Project Service** — Manages projects, designs, and version snapshots. Designs store board configuration, schematic data, and PCB layout as JSON documents.

- **AI Service** — Interfaces with OpenAI GPT-4o for intent parsing, chat responses, auto-fix generation, and design review. Maintains conversation history and tracks token usage.

- **EDA Service** — Provides DRC execution (built-in or KiCad CLI), component library search, and async Gerber generation. Converts design documents between JSON and KiCad S-expression formats.

- **Fabrication Service** — Aggregate quotes from vend ors (JLCPCB, PCB Power, Rush PCB) with pricing models. Returns capability-matched quotes based on board specifications.

**Data Persistence:**

- PostgreSQL stores all relational data: users, teams, projects, designs, components, fabricators, and quotes.
- Redis handles session caching and job queue state.
- Elasticsearch indexes component library and design metadata for full-text search.
- S3/MinIO stores generated Gerbers, 3D models, and design assets.

## Design Document Model

A PCB design is represented as a JSON document with hierarchical structure:

```json
{
  "board_config": {
    "width_mm": 100,
    "height_mm": 80,
    "layers": 4,
    "thickness_mm": 1.6
  },
  "schematic_data": {
    "components": [...],
    "nets": [...]
  },
  "pcb_layout": {
    "placed_components": [...],
    "tracks": [...],
    "vias": [...]
  },
  "constraints": {
    "impedance_controlled_nets": [...],
    "differential_pairs": [...]
  }
}
```

This representation enables stateless processing — the EDA service converts JSON to KiCad format for validation, then extracts results back to JSON for the frontend. The model separates concerns: board configuration, logical connectivity, physical placement, and electrical constraints.

## AI Interaction Patterns

**Intent Parsing:**

The AI receives design context (component positions, net topology, DRC violations) and a natural language request. It returns structured output:

```json
{
  "action_type": "route_net",
  "parameters": {"net_name": "USB_D+", "strategy": "differential_pair"},
  "confidence": 0.92,
  "explanation": "Detected USB differential pair, routing with 2.5mm spacing"
}
```

**Auto-Fix Generation:**

For DRC violations, the AI analyzes each error in context and proposes specific geometric fixes:

```json
{
  "fixes": [
    {"operation": "move_component", "id": "U3", "x": 45, "y": 20},
    {"operation": "adjust_clearance", "component_a": "U3", "component_b": "C12", "min_distance_mm": 0.3}
  ],
  "explanation": "Moved IC U3 to resolve 0.2mm clearance violation with capacitor C12",
  "risk_level": "low"
}
```

**Design Review:**

The AI produces multi-dimensional scoring:

```json
{
  "overall_score": 78,
  "categories": {
    "routing": {"score": 65, "issues": ["Incomplete ground pour"], "suggestions": [...]},
    "manufacturing": {"score": 85, "issues": [], "suggestions": [...]}
  },
  "critical_issues": ["Unrouted net NET_42"],
  "summary": "Design ready for fabrication after addressing routing completeness"
}
```

## Fabricator Integration

The fabrication service abstracts vendor-specific details through a unified connector interface. Each connector implements:

- `get_quote(board_config, options)` — Returns price, lead time, and options
- `get_capabilities()` — Returns supported capabilities

Current connectors:

- **JLCPCB** — Global budget fab, competitive 2-layer pricing
- **PCB Power** — India-based, fast turnaround
- **Rush PCB** — India-based, high-mix capability

Quote requests specify quantity, surface finish, and material. The service filters connectors by capability match and returns sorted quotes.

## Reinforcement Learning Environment

The RL environment models PCB routing as a Markov decision process:

**Observation Space:**

- Channel 0: Obstacle map (components, board edge)
- Channel 1: Routed traces
- Channel 2: Target net pins
- Channel 3: Current agent position

**Action Space:**

- Move up/down/left/right (0-3)
- Place via up/down (4-5)

**Reward Structure:**

- +10.0 per pin reached
- +100.0 for net completion
- -0.01 per step (efficiency penalty)
- -1.0 per collision
- -0.5 per via placed
- -5.0 for net timeout

The environment generates random netlists during training, with procedurally placed obstacles simulating components. Episodes terminate when all nets are routed or step limits are exceeded.

## Scope and Limitations

XgenPCB is currently a design-time tool — it assists with creation and validation but does not directly manufacture PCBs. Gerber output is generated for submission to external fab houses.

The AI capabilities are bounded by GPT-4o's training data. Complex high-speed designs (Gbps SERDES, DDR5 memory) require specialized SI/PI analysis beyond current LLM capacity.

The RL routing system is experimental. It handles simplified single-net routing but does not yet manage multi-net interactions, signal integrity constraints, or differential pair routing.

Component pricing reflects static models and may not reflect real-time distributor inventory or spot pricing.

## Future Directions

- Integrate signal integrity simulation (IBIS, IBIS-AMI) for high-speed validation
- Add cost optimization suggestions (component substitution, panelization)
- Expand RL routing to handle multi-net constraints and differential pairs
- Connect to live distributor APIs for real-time pricing and stock availability
- Build collaborative editing with operational transformation

---

## Quick Start (Clone-Free)

XgenPCB is now fully autonomous. You no longer need to clone the repository or manually configure Docker to get started.

### 1. Installation
```bash
pip install xgenpcb
```

### 2. Run the Agent
Simply type the command below. The CLI will automatically detect if you have a backend running; if not, it will offer to set up a local Docker backend for you!
```bash
xgenpcb
```

### 3. Configuration
When you first run the agent, it will look for an `NVIDIA_API_KEY` in your environment or a local `.env` file. You can also set it directly in the TUI.

---

## Manual Backend Setup (Optional)
If you prefer to manage the infrastructure yourself:
```bash
docker-compose up -d
```

### 3. Run Database Migrations
```bash
docker-compose run backend python -m shared.database init
```

### 4. Start Application
```bash
docker-compose up -d backend frontend
```

### 5. Generate a PCB

**Using text description:**
```bash
curl -X POST http://localhost:8000/api/v1/ai/generate-pcb \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "input_type": "text",
    "description": "USB-C to ESP32 module with 3.3V regulator, 2 LEDs, and reset button"
  }'
```

**Using BOM + netlist:**
```bash
curl -X POST http://localhost:8000/api/v1/ai/generate-pcb \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "bom_netlist",
    "components": [
      {"id": "U1", "name": "ESP32", "mpn": "ESP32-WROOM-32", "footprint": "QFN-48"},
      {"id": "U2", "name": "REG", "mpn": "AMS1117-3.3", "footprint": "SOT-223"},
      {"id": "C1", "name": "C1", "footprint": "0805"}
    ],
    "nets": [
      {"name": "VCC", "pins": [{"component_id": "U1", "pin": "VCC"}, {"component_id": "U2", "pin": "VOUT"}]}
    ]
  }'
```

### 6. Export Files
```bash
# Generate Gerbers
curl -X POST http://localhost:8000/api/v1/eda/generate-gerber?design_id=<id>

# Generate STEP 3D model
curl -X POST http://localhost:8000/api/v1/eda/export-step?design_id=<id>
```

### 7. Access UI
- Frontend: http://localhost:8080
- API Docs: http://localhost:8000/docs

---

**License:** Proprietary — All rights reserved.