# HMI Engine — Engineering Log

**Project:** Housing Market Intelligence Engine  
**Date range:** 2026-04-08 → 2026-04-17  
**Engineer:** sudarsh-lang

---

## Summary

Built a production-grade housing market intelligence platform from scratch, progressing from an initial prototype (SQLite, no auth, no live data) to a fully containerised, multi-service system with live data feeds, a multi-agent research pipeline, an interactive dashboard, and observability infrastructure. The platform demonstrates eleven SoTA AI engineering capabilities simultaneously.

---

## Phase 1 — Database: SQLite → PostgreSQL + Alembic

**Date:** 2026-04-08  
**Files changed:** `mcp-server/pyproject.toml`, `mcp-server/src/mcp_server/db/session.py`, `mcp-server/src/mcp_server/db/models.py`, `docker-compose.yml`, `mcp-server/alembic.ini`, `mcp-server/alembic/`

### What was done

Replaced the prototype SQLite backend (`aiosqlite`) with an async PostgreSQL engine (`asyncpg`). The motivation was correctness under concurrent writes and the ability to hold live feed data across container restarts.

- Added `postgres:16-alpine` to `docker-compose.yml` with a `pg_isready` health check and a `pg-data` named volume.
- Wired `agent-runner` to depend on `mcp-server` (which in turn depends on `postgres`), so startup order is enforced.
- Set pool config: `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`.
- Added two new models to support live feeds:
  - `NewsItem` — headline, summary, source, URL, relevance_score, market, published_at
  - `KPISnapshot` — market, JSONB kpis blob, as_of_date (for pipeline push)
  - `MarketHistorySnapshot` — 8 KPI metrics per market per month, for visualization tabs
- Wrote Alembic migrations (`0001_initial.py`, `0002_market_history.py`) — additive only, no destructive DDL.

### Decisions

Chose `MemorySaver` (LangGraph) rather than `AsyncPostgresSaver` for the agent checkpointer at this stage — the graph's in-memory checkpoint state is acceptable for dev and the focus was on the data tier. Noted as a future upgrade for production multi-replica deploys.

---

## Phase 2 — Live Data Feeds

**Date:** 2026-04-09  
**Files changed:** `mcp-server/src/mcp_server/feeds/news_fetcher.py`, `mcp-server/src/mcp_server/feeds/rate_fetcher.py`, `mcp-server/src/mcp_server/feeds/kpi_ingestor.py`, `mcp-server/src/mcp_server/main.py`

### What was done

Three APScheduler jobs registered in the FastAPI lifespan hook:

**News feed** (`news_fetcher.py`): Calls NewsAPI (primary) or RSS fallback (NAR, Redfin Research, HUD) at 08:00 and 17:00 daily. Scores articles by keyword relevance, deduplicates by URL, stores to `NewsItem`, prunes items older than 7 days. `NEWS_API_KEY` is optional — absent means RSS-only mode.

**Rate feed** (`rate_fetcher.py`): Calls Freddie Mac PMMS daily at 09:00. Upserts the weekly 30-year fixed rate into `MortgageRate` with `updated_at` tracking. Keeps 52 weeks of history.

**KPI ingestor** (`kpi_ingestor.py`): Dual-mode — HTTP push (`POST /ingest/kpis`) and file-watch (polls `KPI_IMPORT_PATH` every 15 minutes, imports on mtime change). Writes to `KPISnapshot` table; the `/dashboard` endpoint queries this first before falling back to computed KPIs from listings.

**Bug found and fixed:** NewsAPI returns timezone-aware datetimes (UTC suffix `Z`), but the `published_at` column is `TIMESTAMP WITHOUT TIME ZONE`. Inserting a tz-aware `datetime` raised a psycopg type error. Fix: `.replace(tzinfo=None)` after parsing the ISO string.

---

## Phase 3 — HITL + Dual Output Streams

**Date:** 2026-04-10  
**Files changed:** `agents/src/agents/graph/graph.py`, `agents/src/agents/graph/nodes/supervisor.py`, `agents/src/agents/main.py`, `dashboard/dashboard.py`

### What was done

**HITL (Human-in-the-Loop):** The graph was originally synchronous — it ran `graph.ainvoke()` all the way to completion in a single request. Rewired to a two-pass model:

1. First `ainvoke` with `is_approved=False` → supervisor decomposes the query, writes `research_plan` to state, graph exits.
2. API returns `{run_id, status: "awaiting_approval", plan}`.
3. Client POSTs to `/research/{run_id}/approve`.
4. Second `ainvoke` with `{is_approved: True}` and same `thread_id` → `MemorySaver` checkpointer resumes from the paused state, supervisor routes to agents.

Added `_runs` dict (run_id → status/plan/result/error) with 60-minute TTL cleanup via `asyncio.create_task`. Added `/research/{run_id}/status` and `/research/{run_id}/approve` endpoints.

**Dual output streams:** Writer node already produced both `state["report"]` and `state["dashboard"]`. Wired the dashboard Research panel to display the Markdown report in an expander and the KPI grid from the dashboard stream.

---

## Phase 4 — Auth & Access Control

**Date:** 2026-04-11  
**Files changed:** `mcp-server/src/mcp_server/middleware/auth.py`, `mcp-server/src/mcp_server/middleware/rate_limit.py`, `mcp-server/src/mcp_server/main.py`

### What was done

**Auth middleware** (`auth.py`): FastAPI dependency that validates either a Bearer JWT (`python-jose`) or a static `X-API-Key` header (HMAC-compared against `API_KEY_HASH` env var). Three tiers:

- Public: `GET /health`, `GET /dashboard`, `GET /sse`
- Pipeline-key: `POST /ingest/kpis` (requires API key)
- JWT: `POST /tools/call/*`, `POST /query`, `POST /research`

**Rate limiting** (`rate_limit.py`, `slowapi`):
- `GET /dashboard` → 60/min per IP
- `POST /tools/call/*` → 20/min per user
- `POST /query` → 10/min auth, 3/min anon
- `POST /research` → 5/min per user

**CORS lockdown:** Origins controlled by `ALLOWED_ORIGINS` env var; defaults to `http://localhost:8501,http://localhost:3000`.

---

## Phase 5 — Observability

**Date:** 2026-04-11  
**Files changed:** `mcp-server/src/mcp_server/observability.py`, both `pyproject.toml` files

### What was done

`structlog` configured for JSON production output, colored console in dev (toggle via `LOG_FORMAT=json|console`). Key structured log events emitted at startup/shutdown, feed runs, and research lifecycle (`research.started`, `research.hitl_pending`, `research.complete`).

Prometheus metrics via `prometheus-fastapi-instrumentator`. Custom counters:
- `hmi_feed_fetch_total{feed, status}`
- `hmi_research_total{status}`
- `hmi_hitl_approval_total{outcome}`

Sentry init gated on `SENTRY_DSN` env var presence — silent no-op in dev.

---

## Phase 6 — HTTPS Reverse Proxy (Caddy)

**Date:** 2026-04-12  
**Files changed:** `Caddyfile`, `docker-compose.yml`

### What was done

Added Caddy as the ingress layer. Routes:
- `/api/*` → `mcp-server:8001` (prefix stripped)
- `/agent/*` → `agent-runner:8000` (prefix stripped)
- `/*` → `dashboard:8501`

**Three bugs encountered:**

1. `{$DOMAIN:localhost}` without `http://` prefix causes Caddy to attempt HTTPS even on localhost, resulting in a redirect loop. Fix: `http://{$DOMAIN:localhost}`.

2. `reverse_proxy /api/* mcp-server:8001` forwards the full path including `/api`. Fix: `handle_path /api/*` which strips the matched prefix before proxying.

3. Initial config included a dedicated SSE block. Audit of mcp-server confirmed there is no `/sse` endpoint (FastMCP was later removed from this build). Removed the SSE block.

Final `Caddyfile`:
```
http://{$DOMAIN:localhost} {
    handle_path /api/* { reverse_proxy mcp-server:8001 }
    handle_path /agent/* { reverse_proxy agent-runner:8000 }
    reverse_proxy /* dashboard:8501
    encode gzip
    log { output stdout; format json }
}
```

---

## Phase 7 — Infrastructure Hardening

**Date:** 2026-04-12  
**Files changed:** `docker-compose.yml`, all `Dockerfile`s

### What was done

- Added `restart: unless-stopped` to all services.
- Added `deploy.resources.limits` per service: postgres (1 CPU / 512M), mcp-server (0.5 / 256M), agent-runner (2.0 / 1G), dashboard (0.5 / 256M), caddy (0.25 / 64M).
- Health checks on all services. **Bug:** mcp-server and agent-runner use `uv`-based Python slim images that do not include `curl`. Initial health checks used `curl -sf`; replaced with `python -c "import urllib.request; urllib.request.urlopen(...)"`.
- `chroma-data` named volume added for agent-runner's ChromaDB — persists episodic memory across container restarts.

---

## Phase 8 — CI/CD

**Date:** 2026-04-13  
**Files changed:** `.github/workflows/ci.yml`, `.github/workflows/test.yml`

### What was done

GitHub Actions workflow: test → build → deploy (main branch only).

- `test` job: `uv run pytest mcp-server/tests/` + `uv run pytest agents/tests/` + eval harness smoke run (1 query, schema validation).
- `build` job: `docker buildx build` + push to GHCR for mcp-server, agent-runner, dashboard. Tags: `sha` + `latest`.
- `deploy` job: SSH to server, `docker-compose pull && docker-compose up -d`.

---

## Phase 9 — Natural Language Query

**Date:** 2026-04-13  
**Files changed:** `mcp-server/src/mcp_server/main.py`, `mcp-server/pyproject.toml`, `dashboard/dashboard.py`

### What was done

`POST /query` endpoint: takes a `{query: str}` body, runs a Haiku (`claude-haiku-4-5-20251001`) tool-use loop (max 3 rounds, 15-second total timeout), returns `{answer: str, tools_used: [str]}`.

Tool whitelist (read-only): `search_houses`, `get_valuation_data`, `get_neighborhood_snapshot`, `get_mortgage_rates`, `get_housing_market_snapshot`. Write/ingest endpoints excluded.

Guardrails:
- Query max 500 chars; SQL keyword rejection before LLM call (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `EXEC`)
- Rate: 10/min auth, 3/min anon
- `max_tokens=300` on synthesis call

Dashboard: search bar triggers `/query`, displays answer via `st.info()`. Removed property card grid. `tools_used` shown as grey subtext.

**Bug:** `ANTHROPIC_API_KEY` was not forwarded to the mcp-server container in `docker-compose.yml`. NL queries returned 503. Fix: added `ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}` to mcp-server environment block.

---

## Phase 10 — Visualization Tabs

**Date:** 2026-04-14 → 2026-04-15  
**Files changed:** `dashboard/dashboard.py`, `mcp-server/src/mcp_server/main.py`, `mcp-server/src/mcp_server/db/models.py`, `mcp-server/data/seed/generate_history.py`, `mcp-server/data/seed/market_history.json`

### What was done

Three new visualization tabs alongside the Overview tab.

**Data layer:** `MarketHistorySnapshot` model (60 months × ~30 MSAs = ~1,800 rows). Eight KPI fields split into two display modes by a strict rule: YoY% for inventory/price/sales/new-listings; absolute for DOM, months supply, price/sqft, rate.

New endpoints:
- `GET /history/{market}?years=5` — monthly time series, YoY fields computed server-side
- `GET /msa/rankings?metric=X&sort=asc|desc` — latest snapshot per market, sorted

**Tab 2 — Market Trends:** Plotly line chart, all ~30 MSA lines as grey mass, selected market highlighted in accent blue (#3479f5), National in medium grey.

**Tab 3 — MSA Rankings:** Horizontal Plotly bar chart. **Bug:** Plotly sorts categorical y-axis alphabetically by default. Fix: `yaxis=dict(categoryorder="array", categoryarray=list(reversed(markets_list)))` to enforce value-sort. **Second bug:** sort radio button used `st.rerun()` which reset to the first tab. Fix: changed to `st.radio(horizontal=True)` — Plotly re-renders on widget change without a full rerun.

**Third bug:** Rankings for YoY metrics (e.g. active_listings) were ranked by absolute value, not by YoY%. Fix: moved prior-year row fetch before the sort step, computed YoY% in the sort key for YoY metrics. Added `_yoy_pct()` helper.

**Tab 4 — Historical Comparison:** Multi-select markets, distinct color palette per market, range slider, current-value annotation. Rendered as a seasonality chart (months on x-axis, year-per-line legend) instead of a raw time series — more useful for spotting seasonal patterns.

**Shared state:** `st.session_state.market`, `st.session_state.viz_metric`, `st.session_state.compare_markets` initialized once at top. Market filter on Overview tab writes to session state; all viz tabs react.

**Caching:** `@st.cache_data(ttl=60)` on dashboard/rankings fetches; `@st.cache_data(ttl=300)` on history fetches.

---

## Multi-Agent Pipeline — Design Review and Optimization Pass

**Date:** 2026-04-16  
**Files changed:** Multiple agent nodes, `agents/src/agents/utils/sentiment.py` (new), `agents/src/agents/main.py`, `agents/src/agents/graph/graph.py`, `agents/src/agents/graph/state.py`, `agents/src/agents/a2a/router.py`

### What was done

A design review of the entire agent pipeline identified nine improvements. All were implemented.

**1 — Researcher + Analyst merge.**  
The `researcher.py` and `analyst.py` nodes were separate but always ran sequentially on the same raw data. Merged into `researcher_analyst.py`: one MCP + browser collection pass, one sandbox quant pass, one Haiku call producing two `---`-separated paragraphs (market signals + investment outlook). Saves one full LLM round-trip. Both `"researcher"` and `"analyst"` routing targets in the graph now resolve to the same `researcher_analyst` node.

**2 — Double-run guard.**  
Supervisor decomposes queries into 2–3 tasks (e.g. "collect data", "analyze data") which all route to `researcher_analyst`. The second invocation re-ran the full MCP + browser collection, burning ~5 seconds and an API call. Added guard at top of `run()`: if `mcp_data` and `analysis_results` both present in state, return immediately.

**3 — All agent nodes use Haiku.**  
Previously: supervisor and A2A router used `gpt-4o` (OpenAI key not set, causing 500s). Changed all nodes to `claude-haiku-4-5-20251001` via litellm. Token budgets: router=300, researcher_analyst=500, writer=700, evaluator=0 (regex). Total per full pipeline run: ~1,500 tokens.

**4 — Evaluator converted to regex.**  
The evaluator node called Haiku to grade the report — circular (LLM grading LLM output, same token budget). Replaced with structural checks: required sections present (`Executive Summary`, `Market Conditions`, `Investment Outlook`, `Key Risks`), report ≥ 200 chars, at least one numeric pattern (`$X,XXX`, `X.X%`, `N days`). Zero LLM tokens.

**5 — Shared sentiment utility.**  
`news_analyst.py` and `researcher_analyst.py` had separate inline sentiment logic with different vocabularies. Extracted to `agents/src/agents/utils/sentiment.py` with a broader word set (bullish/positive/optimistic vs bearish/negative/pessimistic).

**6 — `llm_error` propagation.**  
If `researcher_analyst` Haiku call fails, it sets `state["llm_error"]`. Writer checks this at entry and aborts with an error report rather than producing a hallucinated synthesis on missing data.

**7 — Episodic memory wired to prompts.**  
`supervisor.py` already retrieves ChromaDB snippets but was discarding them. Now builds `past_context_summary` (up to 3 prior-query snippets) and writes it to state. Both `researcher_analyst` and `writer` include it in their prompts.

**8 — `_runs` TTL cleanup.**  
The `_runs` dict grew unbounded. Added `_schedule_cleanup(run_id)` — `asyncio.create_task` that sleeps 3600s (60 min) then pops the entry. Called in `_run_to_completion`'s `finally` block and in the reject path.

**9 — `ResearchRequest` validation.**  
Added `min_length=3, max_length=500` to the `query` field. Prevents empty/trivially short queries and aligns with the NL query endpoint's own 500-char cap.

### Outcome

End-to-end smoke test after all changes: `POST /agent/research {"query": "housing market in Austin Texas"}` → `{status: "awaiting_approval", plan: [...3 items...]}` in ~2s.

---

## Known Limitations

| Item | Detail |
|---|---|
| `_runs` + `MemorySaver` are both in-memory | Graph checkpoints and run registry are lost on agent-runner restart. Fixing one without the other is half a solution — swap both to `AsyncPostgresSaver` + DB-backed run table for true persistence. |
| No OAuth in this build | `st.login()` Streamlit OAuth is a placeholder; `dashboard.py` does not currently enforce login. Auth is enforced at the API layer (JWT/API key). |
| Playwright in Docker on Windows | Chromium runs correctly inside the Linux container; host-side `docker-compose up` on Windows 11 requires WSL2 backend. Native Windows Playwright without WSL2 may need additional flags. |
| NewsAPI free tier | Free tier limits to 100 requests/day and articles from the last 30 days. Production use requires a paid plan. |

---

## Tech Stack Summary

| Component | Technology |
|---|---|
| Package manager | `uv` |
| Agent orchestration | LangGraph + MemorySaver checkpointer |
| LLM | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) via litellm |
| MCP server | FastAPI + FastMCP |
| Database | PostgreSQL 16 (asyncpg + SQLAlchemy 2) |
| Migrations | Alembic |
| Browser automation | Playwright (headless Chromium) |
| Vector DB | ChromaDB (persistent volume) |
| Dashboard | Streamlit 1.42+ |
| Visualization | Plotly 6 |
| Reverse proxy | Caddy 2 |
| Observability | structlog (JSON), Prometheus, Sentry |
| Rate limiting | slowapi |
| Auth | python-jose (JWT) + API key |
| Scheduler | APScheduler 3.x (async) |
| CI/CD | GitHub Actions → GHCR → SSH deploy |
