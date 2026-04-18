# HMI Engine — Architecture

---

## System Overview

HMI Engine is a five-service Docker Compose application. Each service has a single responsibility and communicates over the internal Docker network except for the Caddy ingress which handles all external traffic.

```
[Browser / API Client]
         │
         ▼
   [Caddy :80/:443]
    ├── /api/*      → mcp-server:8001   (prefix stripped)
    ├── /agent/*    → agent-runner:8000  (prefix stripped)
    └── /*          → dashboard:3000
         │
    ┌────┴─────────────────────────┐
    │                              │
[mcp-server:8001]         [agent-runner:8000]
    │                              │
    └──── postgres:5432 ───────────┘
    │
[dashboard:3000]
         │
    (proxies /api/* and /agent/* via Next.js route handlers)
```

---

## Service Responsibilities

### mcp-server (port 8001)

FastAPI application. Three roles:

1. **MCP tool server** — exposes six housing market tools callable by agents via the `mcp` Python SDK's `sse_client` transport. Tools query PostgreSQL.

2. **REST API for the dashboard** — `/dashboard`, `/history/all`, `/history/{market}`, `/msa/rankings`, `/query` endpoints serve the Next.js UI.

3. **Live data feed scheduler** — APScheduler runs three background jobs in the FastAPI lifespan:
   - `news_fetcher`: NewsAPI + RSS (NAR, Redfin Research, HUD) at startup, then 08:00 and 17:00 daily → `NewsItem` table
   - `rate_fetcher`: Freddie Mac PMMS at 09:00 daily → `MortgageRate` table
   - `kpi_ingestor`: file-watch every 15 min + HTTP push endpoint → `KPISnapshot` table

### agent-runner (port 8000)

FastAPI application with a LangGraph multi-agent pipeline. Three roles:

1. **Research orchestration** — `POST /research` starts a LangGraph run. After the first pass (plan creation), execution pauses. Client approves via `POST /research/{id}/approve`, then the graph resumes in a background asyncio task.

2. **Run registry** — `_runs` dict tracks all active/completed runs (run_id → status/plan/result/error) with 60-minute TTL cleanup.

3. **LangGraph host** — holds the compiled `StateGraph` and `MemorySaver` checkpointer in process memory.

### dashboard (port 3000)

Next.js 15 (App Router) application. Four tabs built with Recharts, shadcn/ui, Tailwind CSS v4, TanStack Query v5, and Zustand v5:

- **Overview** — KPI tiles, news panel, mortgage rate table, natural language search bar (Haiku), HITL research panel
- **Trends** — Recharts line chart: all ~30 MSAs as grey mass, National and selected market highlighted; custom tooltip
- **Rankings** — Horizontal bar chart, all markets sorted by selected metric; YoY metrics display % change, absolute metrics display raw values
- **Yearly Comparison** — Multi-market multi-year seasonal overlay; raw absolute values, one color per market fading by year

All backend calls are proxied through Next.js route handlers (`/app/api/*`) to avoid browser CORS issues on the internal Docker network.

### postgres (port 5432)

PostgreSQL 16. Schema managed by Alembic (additive-only migrations). Holds all persistent structured data: listings, neighborhood trends, mortgage rates, news items, KPI snapshots, and market history.

### caddy (ports 80/443)

Caddy 2. Terminates HTTP (and TLS if `DOMAIN` is set to a real domain). Routes and strips prefixes to the appropriate upstream service.

---

## Database Schema

```
HouseListing
  id           UUID PK
  address      String
  city         String
  state        String
  zip_code     String
  price        Integer
  sqft         Integer
  beds         Integer
  baths        Float
  property_type String
  posted_date  Date

NeighborhoodTrend
  id           UUID PK
  zip_code     String
  school_rating Float
  crime_index   Integer
  walkability   Integer
  median_listing_price Integer
  median_days_on_market Integer
  inventory_count Integer

MortgageRate
  id           UUID PK
  term_years   Integer
  rate         Float
  rate_type    String
  updated_at   DateTime

NewsItem
  id           UUID PK
  headline     String
  summary      String
  source       String
  url          String (unique)
  relevance_score String
  market       String (nullable — null = national)
  published_at DateTime
  fetched_at   DateTime

KPISnapshot
  id           UUID PK
  market       String
  kpis         JSONB
  as_of_date   Date
  ingested_at  DateTime

MarketHistorySnapshot
  id                  UUID PK
  market              String
  month               Date (first of month)
  median_dom          Integer
  months_supply       Float
  mortgage_rate_30yr  Float
  price_per_sqft      Integer
  active_listings     Integer
  median_sale_price   Integer
  sales_volume        Integer
  new_listings        Integer
```

YoY fields (`yoy_active_listings`, `yoy_median_sale_price`, `yoy_sales_volume`, `yoy_new_listings`) are computed at query time by the API — not stored in the table.

---

## Agent Pipeline

### Graph Topology

```python
StateGraph(ResearchState)

Nodes: supervisor, researcher_analyst, news_analyst, writer, evaluator

Entry: supervisor

Edges:
  supervisor → researcher_analyst  (when next_agent in ["researcher", "analyst"])
  supervisor → news_analyst        (when next_agent == "news_analyst")
  supervisor → writer              (when next_agent == "writer")
  supervisor → END                 (when next_agent == "END")
  researcher_analyst → supervisor
  news_analyst → supervisor
  writer → evaluator
  evaluator → supervisor           (if critique set — writer retry)
  evaluator → END                  (if report passes)

Checkpointer: MemorySaver (in-memory, dev-grade)
```

### Shared State (`ResearchState`)

```python
class ResearchState(TypedDict):
    query: str
    research_plan: List[str]
    messages: Annotated[List[Any], add_messages]
    pending_tasks: List[Dict]
    completed_tasks: List[Dict]
    mcp_data: Dict
    scraped_data: Dict
    news_data: List[Dict]
    research_interpretation: str
    past_context_summary: str
    analysis_results: Dict
    report: Optional[Dict]
    dashboard: Optional[Dict]
    is_approved: bool
    critique: Optional[str]
    llm_error: Optional[str]
    all_tasks_raw: List[Dict]
    next_agent: str
    iteration_count: int
```

### Node Descriptions

**supervisor** — First pass: calls Haiku to decompose the query into 2–4 subtasks, writes `research_plan` and `pending_tasks`, returns (graph pauses). Second pass (after `is_approved=True`): routes to appropriate agent based on task type. Reads ChromaDB episodic memory and writes `past_context_summary` to state.

**researcher_analyst** — Merged node (formerly separate researcher + analyst). Guards against double-run via `mcp_data` presence check. Collects data via `MCPHousingClient` + `BrowserSession` (Playwright). Runs `SandboxRunner` for quant metrics (avg price, ROI, inventory). One Haiku call (max 500 tokens) producing two `---`-separated paragraphs: market signals + investment outlook. Uses `extract_sentiment()` shared utility.

**news_analyst** — `BrowserSession` scraping of housing news sources. Keyword-based relevance scoring. `extract_sentiment()` on combined article text. Writes `news_data` to state.

**writer** — Checks `llm_error` at entry (aborts if set). Reads all state fields including `past_context_summary`. Haiku call (max 700 tokens) producing structured Markdown report. Writes both `state["report"]` and `state["dashboard"]` (KPI JSON).

**evaluator** — Zero LLM tokens. Structural checks only:
- Required sections present: `Executive Summary`, `Market Conditions`, `Investment Outlook`, `Key Risks`
- Report length ≥ 200 chars
- At least one numeric pattern (`$X,XXX`, `X.X%`, or `N days`)
- If any check fails: writes `critique` to state, sets `next_agent="writer"` for retry
- If all pass: sets `next_agent="END"`

### HITL Flow

```
POST /agent/research
  → graph.ainvoke(initial_state, {thread_id: run_id})
  → supervisor runs, writes plan, returns
  → _runs[run_id] = {status: "awaiting_approval", plan: [...]}
  → return {run_id, status, plan}

POST /agent/research/{id}/approve {"approved": true}
  → asyncio.create_task(_run_to_completion(run_id, config))
  → return {status: "running"} immediately

_run_to_completion:
  → graph.ainvoke({"is_approved": True}, {thread_id: run_id})
  → MemorySaver replays state, supervisor sees is_approved=True
  → pipeline runs to completion
  → _runs[run_id].status = "complete"
  → _schedule_cleanup(run_id) — delete after 60 min
```

---

## Tool Layer

### MCPHousingClient (`tools/mcp_client.py`)

Wraps the `mcp` SDK's `sse_client` + `ClientSession`. Creates a fresh session per call. Available methods:
- `search_houses(query, city, state, ...)` → listings
- `get_market_snapshot()` → aggregate KPIs
- `get_valuation_data(zip_code)` → price trends
- `get_neighborhood_snapshot(zip_code)` → school/crime/walk
- `get_mortgage_rates()` → rate table
- `calculate_roi(purchase_price, monthly_rent, ...)` → ROI %

### BrowserSession (`tools/computer_use.py`)

Playwright async Chromium session. Per-node lifecycle (created at start, closed in finally). Docker-safe flags: `--no-sandbox`, `--disable-dev-shm-usage`. Functions:
- `browser_search_housing(session, query)` → scraped listings from Zillow/Redfin
- `browser_search_housing_news(session, query)` → news articles

### SandboxRunner (`tools/sandbox.py`)

Subprocess-based Python executor. Wraps user code in a generated script passed to `python -c`; output captured from stdout. Pre-execution AST scan blocks dangerous imports before any subprocess is spawned. Allowed imports: `pandas`, `numpy`, `statistics`, `json`, `datetime`, `collections`. Blocked: `os`, `subprocess`, `sys`, `socket`, `requests`, and others. 30-second timeout (configurable via `SANDBOX_TIMEOUT_SECONDS`).

### EpisodicMemory (`tools/memory.py`)

ChromaDB `PersistentClient` at `CHROMA_PATH` (default: `/app/data/chroma`, mounted as Docker named volume). Methods:
- `store(query, report_markdown)` — embeds and stores research result
- `retrieve(query, n=3)` — semantic search over past results

---

## Natural Language Query (`POST /api/query`)

```
[User query]
     │
     ▼
Input validation (max 500 chars, SQL keyword rejection)
     │
     ▼
Haiku tool-use loop (max 3 rounds, 15s total timeout)
  Tools available (read-only):
    search_houses, get_valuation_data, get_neighborhood_snapshot,
    get_mortgage_rates, get_housing_market_snapshot
     │
     ▼
Final synthesis (max_tokens=300)
     │
     ▼
{"answer": str, "tools_used": [str]}
```

---

## Dashboard — Next.js Proxy Layer

The Next.js dashboard cannot call `mcp-server:8001` or `agent-runner:8000` directly from the browser (internal Docker hostnames are not reachable from the user's machine). All API calls go through Next.js route handlers at `/app/api/*` which proxy to the internal services using server-side `fetch`.

```
Browser → GET /api/dashboard?market=Austin
        → Next.js route handler (/app/api/dashboard/route.ts)
        → fetch("http://mcp-server:8001/dashboard?market=Austin")
        → JSON response forwarded to browser
```

Route handlers: `dashboard`, `history/[market]`, `msa/rankings`, `query`, `research`, `research/[runId]/status`, `research/[runId]/approve`, `health`.

---

## Observability

**Logging:** `structlog` JSON output in production, colored console in dev (`LOG_FORMAT=console`). Key event names: `mcp_server.starting`, `mcp_server.ready`, `feed.news.complete`, `feed.rates.updated`, `research.started`, `research.complete`.

**Metrics:** `prometheus-fastapi-instrumentator` auto-instruments all HTTP routes. Custom counters:
- `hmi_feed_fetch_total{feed, status}`
- `hmi_research_total{status}`
- `hmi_hitl_approval_total{outcome}`

Endpoint: `GET /api/metrics`

**Error tracking:** Sentry initialized if `SENTRY_DSN` env var is present; silent otherwise.

---

## Security Model

**Auth:** `require_auth` FastAPI dependency. Validates Bearer JWT (HS256, `SECRET_KEY`) or `X-API-Key` header (HMAC-compared against `API_KEY_HASH`).

- Public (no auth): `GET /health`, `GET /dashboard`, `GET /history/*`, `GET /msa/rankings`
- API key: `POST /ingest/kpis`
- JWT: `POST /tools/call/*`, `POST /query`

**Rate limits** (slowapi):

| Endpoint | Auth limit | Anon limit |
|---|---|---|
| `GET /dashboard` | 60/min | 60/min |
| `POST /tools/call/*` | 20/min | — |
| `POST /query` | 10/min | 3/min |
| `POST /research` | 5/min | — |

**CORS:** `ALLOWED_ORIGINS` env var; defaults to `http://localhost:3000`.

---

## Resource Limits

| Service | CPU | Memory |
|---|---|---|
| postgres | 1.0 | 512M |
| mcp-server | 0.5 | 256M |
| agent-runner | 2.0 | 1G |
| dashboard | 0.5 | 256M |
| caddy | 0.25 | 64M |
