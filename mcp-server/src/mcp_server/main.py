import os
import structlog
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from datetime import date, timedelta
from sqlalchemy import select, func, desc
from slowapi.errors import RateLimitExceeded

from .observability import configure_logging, configure_sentry, attach_prometheus

configure_logging()
configure_sentry()

log = structlog.get_logger(__name__)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .db.session import init_db, AsyncSessionLocal
from .db.models import HouseListing, NeighborhoodTrend, MortgageRate, NewsItem, KPISnapshot, MarketHistorySnapshot
from .db.seed import seed_data
from .feeds.news_fetcher import fetch_and_store_news
from .feeds.rate_fetcher import fetch_and_store_rates
from .feeds.kpi_ingestor import ingest_kpis, poll_kpi_file
from .tools.search_houses import search_houses as _search_houses
from .tools.valuation_data import get_valuation_data as _get_valuation_data, get_neighborhood_snapshot as _get_neighborhood_snapshot, get_mortgage_rates as _get_mortgage_rates
from .tools.housing_market import get_housing_market_snapshot as _get_housing_market_snapshot, calculate_roi as _calculate_roi
from .middleware.auth import require_auth
from .middleware.rate_limit import limiter, rate_limit_handler

TOOLS = {
    "search_houses": {
        "fn": _search_houses,
        "description": "Search for house listings.",
        "parameters": {
            "query": str, "city": str, "state": str, "zip_code": str,
            "min_price": int, "max_price": int, "property_type": str,
            "limit": int, "offset": int,
        },
    },
    "get_valuation_data": {
        "fn": _get_valuation_data,
        "description": "Get market valuation trends for a zip code.",
        "parameters": {"zip_code": str},
    },
    "get_neighborhood_snapshot": {
        "fn": _get_neighborhood_snapshot,
        "description": "Get neighborhood snapshot (schools, crime, walkability).",
        "parameters": {"zip_code": str},
    },
    "get_mortgage_rates": {
        "fn": _get_mortgage_rates,
        "description": "Get current mortgage rates.",
        "parameters": {},
    },
    "get_housing_market_snapshot": {
        "fn": _get_housing_market_snapshot,
        "description": "Get housing market snapshot.",
        "parameters": {"city_filter": str},
    },
    "calculate_roi": {
        "fn": _calculate_roi,
        "description": "Calculate ROI for a property.",
        "parameters": {
            "purchase_price": float, "monthly_rent": float,
            "property_tax_annual": float, "insurance_annual": float,
            "maintenance_annual": float,
        },
    },
}

_scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("mcp_server.starting")
    await init_db()
    await seed_data()

    # News: run immediately on startup, then 08:00 and 17:00 daily
    _scheduler.add_job(fetch_and_store_news, "date", id="news_fetch_startup", misfire_grace_time=30)
    _scheduler.add_job(fetch_and_store_news, CronTrigger(hour="8,17"), id="news_fetch", replace_existing=True)
    # Rates: 09:00 daily
    _scheduler.add_job(fetch_and_store_rates, CronTrigger(hour="9"), id="rate_fetch", replace_existing=True)
    # KPI file poll: every 15 minutes
    _scheduler.add_job(poll_kpi_file, IntervalTrigger(minutes=15), id="kpi_poll", replace_existing=True)

    _scheduler.start()
    log.info("mcp_server.ready")
    yield
    _scheduler.shutdown(wait=False)
    log.info("mcp_server.stopped")


app = FastAPI(title="Market Intelligence MCP Server", lifespan=lifespan)

attach_prometheus(app)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# CORS — locked to configured origins (default: localhost dev ports)
_allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8501,http://localhost:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "service": "mcp-server"}


@app.get("/dashboard")
@limiter.limit("60/minute")
async def get_dashboard_data(request: Request, market: str = "National"):
    """Get dashboard KPIs, news from DB, and mortgage rates."""
    try:
        rates = await _get_mortgage_rates()
        rate_30yr = next((r["rate"] for r in rates if r["term_years"] == 30), 6.5)

        async with AsyncSessionLocal() as session:
            city_filter = None if market == "National" else market

            # Check for pipeline KPI snapshot first
            kpi_q = select(KPISnapshot).where(KPISnapshot.market == market).order_by(
                desc(KPISnapshot.as_of_date)
            ).limit(1)
            kpi_row = (await session.execute(kpi_q)).scalar()
            if kpi_row:
                kpis = kpi_row.kpis
            else:
                # Compute KPIs from listings and neighborhood data
                q = select(func.count(HouseListing.id))
                if city_filter:
                    q = q.where(HouseListing.city == city_filter)
                active_listings = (await session.execute(q)).scalar() or 0

                cutoff = date.today() - timedelta(days=30)
                q2 = select(func.count(HouseListing.id)).where(HouseListing.posted_date >= cutoff)
                if city_filter:
                    q2 = q2.where(HouseListing.city == city_filter)
                new_listings = (await session.execute(q2)).scalar() or 0

                q3 = select(HouseListing.price, HouseListing.sqft).where(HouseListing.sqft > 0)
                if city_filter:
                    q3 = q3.where(HouseListing.city == city_filter)
                rows = (await session.execute(q3)).fetchall()
                price_per_sqft = int(sum(r.price / r.sqft for r in rows) / len(rows)) if rows else 0

                q4 = select(
                    func.avg(NeighborhoodTrend.median_listing_price),
                    func.avg(NeighborhoodTrend.median_days_on_market),
                    func.avg(NeighborhoodTrend.inventory_count),
                )
                stats = (await session.execute(q4)).fetchone()
                avg_price = int(stats[0] or 0)
                median_dom = int(stats[1] or 0)
                avg_inventory = int(stats[2] or 0)

                monthly_turnover = active_listings * (30.0 / max(median_dom, 1))
                months_supply = round(avg_inventory / max(monthly_turnover, 1), 1)
                price_reduction_pct = min(int(median_dom / 2.5), 40)

                kpis = {
                    "avg_list_price": f"${avg_price:,}",
                    "active_listings": f"{active_listings:,}",
                    "rate_30yr_fixed": f"{rate_30yr:.2f}%",
                    "median_dom": f"{median_dom} days",
                    "price_per_sqft": f"${price_per_sqft:,}",
                    "new_listings_30d": f"{new_listings:,}",
                    "price_reductions": f"{price_reduction_pct}%",
                    "months_supply": f"{months_supply} mo",
                }

            # News from DB (latest 4, filtered by market or global)
            news_q = (
                select(NewsItem)
                .where((NewsItem.market == market) | (NewsItem.market.is_(None)))
                .order_by(desc(NewsItem.fetched_at))
                .limit(4)
            )
            news_rows = (await session.execute(news_q)).scalars().all()

            if news_rows:
                recent_news = [
                    {
                        "headline": n.headline,
                        "summary": n.summary or "",
                        "source": n.source or "",
                        "relevance_score": n.relevance_score or "medium",
                    }
                    for n in news_rows
                ]
            else:
                # Fallback static news until feeds run
                median_dom_val = int(kpis.get("median_dom", "0 days").split()[0]) if not kpi_row else 0
                recent_news = [
                    {
                        "headline": "Housing Inventory Rises Nationally",
                        "summary": "Active listings up 8% month-over-month.",
                        "source": "HMI Engine",
                        "relevance_score": "high",
                    },
                    {
                        "headline": "First-Time Buyer Programs Expand",
                        "summary": "Multiple states launching assistance programs with down payment grants up to $20K.",
                        "source": "HUD News",
                        "relevance_score": "medium",
                    },
                    {
                        "headline": "Mortgage Rates Hold Steady",
                        "summary": f"30-year fixed remains at {rate_30yr:.2f}% as Fed signals patience.",
                        "source": "Freddie Mac",
                        "relevance_score": "high",
                    },
                    {
                        "headline": "Buyers Return to Sun Belt Markets",
                        "summary": "Dallas, Phoenix, and Atlanta seeing renewed demand.",
                        "source": "Redfin Research",
                        "relevance_score": "medium",
                    },
                ]

        # Derive market_snapshot values from kpis dict for backwards compat
        avg_price_raw = kpis.get("avg_list_price", "$0").replace("$", "").replace(",", "")
        try:
            avg_price_int = int(avg_price_raw)
        except ValueError:
            avg_price_int = 0
        active_raw = kpis.get("active_listings", "0").replace(",", "")
        try:
            active_int = int(active_raw)
        except ValueError:
            active_int = 0

        market_snapshot = {
            "total_listings": active_int,
            "average_median_price": avg_price_int,
            "latest_mortgage_rate": rate_30yr,
            "as_of_date": date.today().isoformat(),
        }

        return {
            "kpis": kpis,
            "recent_news": recent_news,
            "market_snapshot": market_snapshot,
            "mortgage_rates": rates,
        }
    except Exception as e:
        return {
            "kpis": {"error": str(e)},
            "recent_news": [],
            "market_snapshot": {},
            "mortgage_rates": [],
        }


@app.post("/ingest/kpis")
@limiter.limit("10/minute")
async def ingest_kpis_endpoint(request: Request, payload: dict, _auth: dict = Depends(require_auth)):
    """Receive KPI snapshot from external pipeline."""
    market = payload.get("market", "National")
    kpis = payload.get("kpis", {})
    as_of_str = payload.get("as_of_date", date.today().isoformat())
    try:
        as_of = date.fromisoformat(as_of_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid as_of_date format (expected YYYY-MM-DD)")
    if not kpis:
        raise HTTPException(status_code=400, detail="kpis dict is required and must not be empty")
    await ingest_kpis(market, kpis, as_of)
    return {"status": "ok", "market": market, "as_of_date": as_of_str}


@app.get("/tools/list")
async def list_tools():
    return {
        "tools": [
            {"name": name, "description": info["description"]}
            for name, info in TOOLS.items()
        ]
    }


@app.post("/tools/call/{tool_name}")
@limiter.limit("20/minute")
async def call_tool(request: Request, tool_name: str, arguments: dict = {}, _auth: dict = Depends(require_auth)):
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    try:
        result = await TOOLS[tool_name]["fn"](**arguments)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Natural Language Query (Haiku-powered) ─────────────────────────────────

_SQL_KEYWORDS = {"drop", "delete", "insert", "update", "exec", "truncate", "alter", "create"}

# Tools available to the NL query endpoint (POST /query).
# Policy: include read-only, non-destructive tools that answer housing questions.
# Excluded:
#   calculate_roi — requires structured numeric inputs; NL → JSON extraction for
#                   financial inputs is unreliable. Users should use the ROI
#                   calculator UI directly for this.
_QUERY_TOOL_NAMES = [
    "search_houses",
    "get_valuation_data",
    "get_neighborhood_snapshot",
    "get_mortgage_rates",
    "get_housing_market_snapshot",
]


def _build_tool_definitions() -> list[dict]:
    """Build Anthropic tool definitions for the NL query whitelist."""
    defs = []
    for name in _QUERY_TOOL_NAMES:
        info = TOOLS.get(name)
        if not info:
            continue
        props = {}
        for param_name, param_type in info["parameters"].items():
            props[param_name] = {
                "type": "string" if param_type is str else "number" if param_type in (int, float) else "string",
                "description": param_name.replace("_", " "),
            }
        defs.append({
            "name": name,
            "description": info["description"],
            "input_schema": {"type": "object", "properties": props},
        })
    return defs


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str
    tools_used: list[str]


@app.post("/query", response_model=QueryResponse)
@limiter.limit("10/minute")
async def nl_query(request: Request, body: QueryRequest):
    """Natural language query over housing data using Haiku tool-use."""
    import asyncio
    import anthropic as _anthropic

    q = body.query.strip()

    # Input validation
    if len(q) > 500:
        raise HTTPException(status_code=400, detail="Query too long (max 500 characters)")
    q_lower = q.lower()
    if any(kw in q_lower for kw in _SQL_KEYWORDS):
        raise HTTPException(status_code=400, detail="Query contains disallowed keywords")

    log.info("nl_query.start", query=q)

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI query service not configured")

    client = _anthropic.AsyncAnthropic(api_key=api_key)
    tool_defs = _build_tool_definitions()
    messages = [{"role": "user", "content": q}]
    tools_used: list[str] = []

    try:
        async with asyncio.timeout(15):
            for _round in range(3):
                resp = await client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=300,
                    tools=tool_defs,
                    messages=messages,
                )

                # Collect assistant message
                messages.append({"role": "assistant", "content": resp.content})

                if resp.stop_reason != "tool_use":
                    # Final text response
                    answer = next(
                        (b.text for b in resp.content if hasattr(b, "text")),
                        "I was unable to answer that question based on available data.",
                    )
                    log.info("nl_query.complete", tools_used=tools_used)
                    return QueryResponse(answer=answer, tools_used=tools_used)

                # Execute tool calls and feed results back
                tool_results = []
                for block in resp.content:
                    if block.type != "tool_use":
                        continue
                    if block.name not in _QUERY_TOOL_NAMES:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Tool not available.",
                        })
                        continue
                    try:
                        result = await TOOLS[block.name]["fn"](**block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result)[:2000],
                        })
                        if block.name not in tools_used:
                            tools_used.append(block.name)
                    except Exception as exc:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {exc}",
                        })

                messages.append({"role": "user", "content": tool_results})

            # Max rounds reached — ask Haiku to synthesize from what it has
            resp = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=messages + [{"role": "user", "content": "Summarize your findings in 1-3 sentences based on the data retrieved so far."}],
            )
            answer = next(
                (b.text for b in resp.content if hasattr(b, "text")),
                "I was unable to complete the analysis within the allowed time.",
            )
            log.info("nl_query.complete", tools_used=tools_used)
            return QueryResponse(answer=answer, tools_used=tools_used)

    except TimeoutError:
        log.warning("nl_query.timeout", query=q)
        return QueryResponse(
            answer="The query took too long to complete. Try a more specific question.",
            tools_used=tools_used,
        )


# ──────────────────────────────────────────────────────────────────────────

# ── Visualization API endpoints ────────────────────────────────────────────

_YOY_METRICS = {"active_listings", "median_sale_price", "sales_volume", "new_listings"}
_ABS_METRICS = {"median_dom", "months_supply", "price_per_sqft", "mortgage_rate_30yr"}
_ALL_METRICS = _YOY_METRICS | _ABS_METRICS


def _row_to_dict(row: MarketHistorySnapshot) -> dict:
    return {
        "market": row.market,
        "month": row.month.isoformat(),
        "median_dom": row.median_dom,
        "months_supply": row.months_supply,
        "mortgage_rate_30yr": row.mortgage_rate_30yr,
        "price_per_sqft": row.price_per_sqft,
        "active_listings": row.active_listings,
        "median_sale_price": row.median_sale_price,
        "sales_volume": row.sales_volume,
        "new_listings": row.new_listings,
    }


@app.get("/history/all")
@limiter.limit("10/minute")
async def get_all_history(request: Request, years: int = 5):
    """Return monthly history for ALL markets keyed by market name."""
    from datetime import date as _date2
    years = min(max(years, 1), 10)
    cutoff = _date2.today().replace(day=1)
    from dateutil.relativedelta import relativedelta as _rd_all
    cutoff = cutoff - _rd_all(years=years)

    async with AsyncSessionLocal() as session:
        q = (
            select(MarketHistorySnapshot)
            .where(MarketHistorySnapshot.month >= cutoff)
            .order_by(MarketHistorySnapshot.market, MarketHistorySnapshot.month)
        )
        rows = (await session.execute(q)).scalars().all()

    if not rows:
        return {}

    # Group by market and compute YoY inline
    by_market: dict[str, list] = {}
    for r in rows:
        by_market.setdefault(r.market, []).append(r)

    result: dict[str, list] = {}
    for market_name, market_rows in by_market.items():
        month_index = {r.month.isoformat(): _row_to_dict(r) for r in market_rows}
        market_result = []
        for r in market_rows:
            from dateutil.relativedelta import relativedelta as _rd_y
            d = _row_to_dict(r)
            prev_month = (r.month - _rd_y(years=1)).replace(day=1).isoformat()
            prev = month_index.get(prev_month)
            for m in _YOY_METRICS:
                curr_val = d.get(m)
                prev_val = prev.get(m) if prev else None
                if curr_val is not None and prev_val and prev_val != 0:
                    d[f"yoy_{m}"] = round((curr_val - prev_val) / prev_val * 100, 1)
                else:
                    d[f"yoy_{m}"] = None
            market_result.append(d)
        result[market_name] = market_result

    return result


@app.get("/history/{market}")
@limiter.limit("60/minute")
async def get_market_history(request: Request, market: str, years: int = 5):
    """Return monthly history for a market with YoY fields computed server-side."""
    from datetime import date as _date
    years = min(max(years, 1), 10)
    cutoff = _date.today().replace(day=1)
    from dateutil.relativedelta import relativedelta as _rd
    cutoff = cutoff - _rd(years=years)

    async with AsyncSessionLocal() as session:
        q = (
            select(MarketHistorySnapshot)
            .where(MarketHistorySnapshot.market == market)
            .where(MarketHistorySnapshot.month >= cutoff)
            .order_by(MarketHistorySnapshot.month)
        )
        rows = (await session.execute(q)).scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No history for market '{market}'")

    # Build a month→values index for YoY computation
    month_index: dict[str, dict] = {r.month.isoformat(): _row_to_dict(r) for r in rows}

    result = []
    for r in rows:
        d = _row_to_dict(r)
        # Compute YoY for applicable metrics
        from dateutil.relativedelta import relativedelta as _rd2
        prev_month = (r.month - _rd2(years=1)).replace(day=1).isoformat()
        prev = month_index.get(prev_month)
        for m in _YOY_METRICS:
            curr_val = d.get(m)
            prev_val = prev.get(m) if prev else None
            if curr_val is not None and prev_val and prev_val != 0:
                d[f"yoy_{m}"] = round((curr_val - prev_val) / prev_val * 100, 1)
            else:
                d[f"yoy_{m}"] = None
        result.append(d)

    return result


@app.get("/msa/rankings")
@limiter.limit("60/minute")
async def get_msa_rankings(
    request: Request,
    metric: str = "median_sale_price",
    sort: str = "desc",
    limit: int = 100,
):
    """Return latest snapshot per market sorted by the requested metric."""
    if metric not in _ALL_METRICS:
        raise HTTPException(status_code=400, detail=f"metric must be one of: {sorted(_ALL_METRICS)}")
    if sort not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="sort must be 'asc' or 'desc'")
    limit = min(max(limit, 1), 200)

    async with AsyncSessionLocal() as session:
        # Latest month per market via subquery
        latest_subq = (
            select(
                MarketHistorySnapshot.market,
                func.max(MarketHistorySnapshot.month).label("latest_month"),
            )
            .group_by(MarketHistorySnapshot.market)
            .subquery()
        )
        q = (
            select(MarketHistorySnapshot)
            .join(
                latest_subq,
                (MarketHistorySnapshot.market == latest_subq.c.market)
                & (MarketHistorySnapshot.month == latest_subq.c.latest_month),
            )
        )
        rows = (await session.execute(q)).scalars().all()

    is_yoy = metric in _YOY_METRICS

    # For YoY metrics fetch prior-year rows up front so we can sort by YoY %
    from dateutil.relativedelta import relativedelta as _rd3
    market_prev: dict[str, float | None] = {}
    if is_yoy:
        latest_by_market = {r.market: r.month for r in rows}
        async with AsyncSessionLocal() as session2:
            for market_name, latest_m in latest_by_market.items():
                prev_m = (latest_m - _rd3(years=1)).replace(day=1)
                prev_row = (await session2.execute(
                    select(MarketHistorySnapshot)
                    .where(MarketHistorySnapshot.market == market_name)
                    .where(MarketHistorySnapshot.month == prev_m)
                )).scalar()
                market_prev[market_name] = getattr(prev_row, metric) if prev_row else None

    def _yoy_pct(r) -> float | None:
        curr = getattr(r, metric)
        prev = market_prev.get(r.market)
        if curr is not None and prev and prev != 0:
            return (curr - prev) / prev * 100
        return None

    def _sort_key(r):
        if is_yoy:
            v = _yoy_pct(r)
        else:
            v = getattr(r, metric)
        return v if v is not None else -1e18

    sorted_rows = sorted(rows, key=_sort_key, reverse=(sort == "desc"))[:limit]

    result = []
    for rank, r in enumerate(sorted_rows, 1):
        value = getattr(r, metric)
        yoy_change = None
        if is_yoy:
            yoy_change_raw = _yoy_pct(r)
            yoy_change = round(yoy_change_raw, 1) if yoy_change_raw is not None else None
        result.append({
            "rank": rank,
            "market": r.market,
            "value": value,
            "yoy_change": yoy_change,
            "month": r.month.isoformat(),
        })

    return result


# ──────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
