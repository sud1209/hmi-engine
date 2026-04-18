# HMI Engine — Housing Market Intelligence Platform

A production-grade multi-agent AI system for US housing market research. Combines an MCP data server, a LangGraph multi-agent pipeline with human-in-the-loop approval, live data feeds, and a Next.js interactive dashboard with visualization tabs.

---

## Capabilities

| Capability | Implementation |
|---|---|
| MCP protocol | FastAPI MCP server with housing tools over SSE transport |
| Agent tool use | `mcp_client.py` via official `mcp` Python SDK |
| Computer use | Playwright headless Chromium — Zillow, Redfin, Realtor.com |
| Multi-agent orchestration | LangGraph `StateGraph`: supervisor → researcher_analyst → writer → evaluator |
| A2A protocol | Google A2A spec for structured task delegation |
| Sandboxed code execution | Subprocess Python executor for ROI/quant math |
| HITL breakpoints | `MemorySaver` checkpointer; plan approval before pipeline runs |
| Episodic memory | ChromaDB persistent vector store; prior research injected into prompts |
| Self-correction | Evaluator node: structural + regex report validation, zero LLM tokens |
| Dual output streams | `state["report"]` (Markdown) + `state["dashboard"]` (KPI JSON) |
| Natural language query | `POST /api/query` — Haiku tool-use loop, max 3 rounds, 15s timeout |

---

## Quick Start

### Prerequisites

- Docker Desktop with WSL2 (Windows) or Docker Engine (Linux/Mac)
- `ANTHROPIC_API_KEY` — all LLM calls use Claude Haiku

### 1. Configure

```bash
cp .env.example .env
# Set ANTHROPIC_API_KEY at minimum
```

### 2. Start

```bash
docker-compose up --build
```

Five services start in dependency order: `postgres` → `mcp-server` → `agent-runner` → `dashboard` → `caddy`.

### 3. Access

| URL | Service |
|---|---|
| `http://localhost` | Next.js dashboard |
| `http://localhost/api/health` | MCP server health |
| `http://localhost/agent/health` | Agent runner health |
| `http://localhost/api/docs` | MCP server Swagger |
| `http://localhost/api/metrics` | Prometheus metrics |

### 4. Run a research query

```bash
# Start research (returns plan for approval)
curl -X POST http://localhost/agent/research \
  -H "Content-Type: application/json" \
  -d '{"query": "housing market in Austin Texas"}'

# Approve the plan
curl -X POST http://localhost/agent/research/{run_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

# Poll for result
curl http://localhost/agent/research/{run_id}/status
```

### 5. Run tests

```bash
uv run pytest mcp-server/tests/
uv run pytest agents/tests/
uv run python agents/eval/eval_harness.py --smoke
```

---

## Architecture

```
[Caddy — http://localhost]
        │
        ├── /api/*      → mcp-server:8001   (prefix stripped)
        ├── /agent/*    → agent-runner:8000  (prefix stripped)
        └── /*          → dashboard:3000

[PostgreSQL 16]   ← mcp-server (asyncpg, Alembic migrations)
[ChromaDB vol]    ← agent-runner (episodic memory, persisted)
[APScheduler]     ← mcp-server (news 2×/day, rates 1×/day, KPI 15min)
```

### Agent Pipeline

```
POST /agent/research
       │
  [Supervisor] ── pass 1: decomposes query, writes plan, PAUSES
       │
  (HITL: POST /agent/research/{id}/approve)
       │
  [Supervisor] ── pass 2: routes to agents
       │
  ┌────┴─────────────────┐
  │                      │
[researcher_analyst]  [news_analyst]
  │  MCP tools           │  Playwright
  │  Playwright          │  news sites
  │  Sandbox quant       │
  └────┬─────────────────┘
       │
   [writer]  ── Haiku synthesis, 700 tokens
       │
  [evaluator] ── structural check, 0 LLM tokens
       │
  Markdown report + KPI dashboard JSON
```

---

## Project Structure

```
hmi-engine/
├── docker-compose.yml
├── Caddyfile
├── .env.example
├── mcp-server/
│   ├── src/mcp_server/
│   │   ├── main.py            # All REST endpoints + APScheduler lifespan
│   │   ├── db/                # SQLAlchemy models, session, seed
│   │   ├── feeds/             # news_fetcher, rate_fetcher, kpi_ingestor
│   │   ├── middleware/        # auth.py (JWT + API key), rate_limit.py
│   │   ├── tools/             # MCP tool implementations
│   │   └── observability.py   # structlog, Prometheus, Sentry
│   └── alembic/               # DB migrations (additive only)
├── agents/
│   ├── src/agents/
│   │   ├── main.py            # FastAPI + _runs registry + HITL endpoints
│   │   ├── graph/
│   │   │   ├── graph.py       # LangGraph StateGraph + MemorySaver
│   │   │   ├── state.py       # ResearchState TypedDict
│   │   │   └── nodes/         # supervisor, researcher_analyst, news_analyst, writer, evaluator
│   │   ├── a2a/               # protocol.py, router.py, agent_cards.py
│   │   ├── tools/             # mcp_client, computer_use, sandbox, memory
│   │   └── utils/sentiment.py
│   └── eval/eval_harness.py
└── dashboard/
    ├── src/
    │   ├── app/               # Next.js App Router pages and API route handlers
    │   ├── components/        # UI components (charts, tabs, layout, overview)
    │   ├── hooks/             # TanStack Query data hooks
    │   └── lib/               # types, api client, Zustand store, utils
    ├── Dockerfile
    └── package.json
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Claude Haiku for all LLM calls |
| `NEWS_API_KEY` | No | — | NewsAPI.org; absent = RSS-only (NAR, Redfin, HUD) |
| `DATABASE_URL` | Auto | postgres://hmi:hmi@postgres/hmi | Set by docker-compose |
| `CHROMA_PATH` | Auto | /app/data/chroma | Set by docker-compose |
| `DOMAIN` | No | localhost | Caddy domain; set for real TLS |
| `SECRET_KEY` | Prod | dev-secret | JWT signing key |
| `API_KEY_HASH` | Prod | — | Pipeline ingest API key (SHA-256 hex) |
| `ALLOWED_ORIGINS` | No | http://localhost:3000 | CORS allowlist |
| `SENTRY_DSN` | No | — | Error tracking DSN |
| `LOG_FORMAT` | No | json | `json` or `console` |

---

## Documentation

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, agent state, DB schema |
| [docs/API.md](docs/API.md) | All endpoints with request/response schemas |

---

## License

MIT
