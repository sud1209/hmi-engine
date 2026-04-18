import json
from typing import Dict, Any
import litellm
import structlog
from agents.graph.state import ResearchState
from agents.tools.mcp_client import MCPHousingClient
from agents.tools.computer_use import BrowserSession, browser_search_housing
from agents.tools.sandbox import SandboxRunner
from agents.a2a.protocol import TaskResult
from agents.utils.sentiment import extract as extract_sentiment

log = structlog.get_logger(__name__)

MODEL = "claude-haiku-4-5-20251001"

_SANDBOX_CODE = """
listings = input_data.get("mcp_data", {}).get("search_results", {}).get("listings", [])
market_snapshot = input_data.get("mcp_data", {}).get("market_snapshot", {})
total = len(listings)
avg_price = sum(h["price"] for h in listings) / total if total > 0 else 0
roi = (3000 * 12) / avg_price * 100 if avg_price > 0 else 0
result = {
    "total_listings_analyzed": total,
    "average_price_in_sample": avg_price,
    "sample_roi_estimate": roi,
    "latest_mortgage_rate": market_snapshot.get("latest_mortgage_rate", 0),
    "total_market_listings": market_snapshot.get("total_listings", 0),
    "average_median_price": market_snapshot.get("average_median_price", 0),
}
"""


async def run(state: ResearchState) -> Dict[str, Any]:
    """Merged researcher+analyst node: collect data, run sandbox math, one Haiku call.

    On first call: collects MCP + browser data, runs quant, calls Haiku.
    On second call (supervisor re-routes "analyst" task): data already in state,
    skip collection entirely and return immediately — analysis is already done.
    """

    query = state["query"]
    completed_tasks = state.get("completed_tasks", [])

    # ── Guard: skip if collection already done this run ──────────────────────
    if state.get("mcp_data") and state.get("analysis_results"):
        log.info("researcher_analyst.skip_rerun")
        return {
            "completed_tasks": completed_tasks,
            "pending_tasks": state.get("pending_tasks", []),
            "messages": [("system", "researcher_analyst: skipped re-run (data already present)")],
            "next_agent": "researcher",
        }

    client = MCPHousingClient()
    session = BrowserSession(headless=True)

    # ── 1. Collect raw data ──────────────────────────────────────────────────
    try:
        await session.start()
        search_results = await client.search_houses(query=query)
        market_snapshot = await client.get_market_snapshot()
        scraped_data = await browser_search_housing(session, query)
        await session.stop()
    except Exception as e:
        if session.browser:
            await session.stop()
        return {
            "messages": [("system", f"Data collection failed: {e}")],
            "next_agent": "END",
        }

    mcp_data = {"search_results": search_results, "market_snapshot": market_snapshot}

    # ── 2. Sandbox quant metrics ─────────────────────────────────────────────
    try:
        runner = SandboxRunner()
        quant = await runner.execute_python(_SANDBOX_CODE, {"mcp_data": mcp_data})
    except Exception as e:
        quant = {"error": str(e)}

    # ── 3. Single Haiku call: signals + qualitative analysis ─────────────────
    past_context_summary = state.get("past_context_summary", "")
    listings = search_results.get("listings", [])
    context = json.dumps({
        "query": query,
        "listings_count": len(listings),
        "price_range": {
            "min": min((l["price"] for l in listings), default=0),
            "max": max((l["price"] for l in listings), default=0),
            "avg": int(quant.get("average_price_in_sample", 0)),
        },
        "roi_estimate_pct": round(quant.get("sample_roi_estimate", 0), 1),
        "mortgage_rate": quant.get("latest_mortgage_rate", 0),
        "market_listings": quant.get("total_market_listings", 0),
        "web_results": len(scraped_data) if isinstance(scraped_data, list) else 0,
    }, default=str)

    try:
        response = await litellm.acompletion(
            model=MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a housing market researcher and analyst. "
                    "Be concise, data-driven, and specific."
                )},
                {"role": "user", "content": (
                    f"Data: {context}\n"
                    + (f"{past_context_summary}\n" if past_context_summary else "")
                    + "\nWrite two short paragraphs separated by '---':\n"
                    "1. Key market signals (inventory, pricing, demand trends)\n"
                    "2. Investment outlook: sentiment (Bullish/Bearish/Neutral), "
                    "top risk, top opportunity"
                )},
            ],
            max_tokens=500,
        )
        combined = response.choices[0].message.content.strip()
        parts = combined.split("---", 1)
        interpretation = parts[0].strip()
        analysis_text = parts[1].strip() if len(parts) > 1 else combined
    except Exception as e:
        error_msg = f"Haiku call failed in researcher_analyst: {e}"
        log.error("researcher_analyst.llm_error", exc=str(e))
        return {
            "mcp_data": mcp_data,
            "scraped_data": {"web_search_results": scraped_data},
            "llm_error": error_msg,
            "completed_tasks": completed_tasks,
            "pending_tasks": state.get("pending_tasks", []),
            "messages": [("system", error_msg)],
            "next_agent": "researcher",
        }

    sentiment = extract_sentiment(analysis_text)

    log.info("researcher_analyst.done", sentiment=sentiment)

    analysis_results = {
        **quant,
        "analysis_summary": analysis_text,
        "market_sentiment": sentiment,
        "dashboard_kpis": {
            "national": {
                "mortgage_rate": quant.get("latest_mortgage_rate", 0),
                "avg_median_price": quant.get("average_median_price", 0),
                "market_status": "Low Inventory" if quant.get("total_market_listings", 0) < 100 else "Balanced",
            },
            "metro_specific": {
                "sample_size": quant.get("total_listings_analyzed", 0),
                "avg_price": quant.get("average_price_in_sample", 0),
                "estimated_roi": quant.get("sample_roi_estimate", 0),
            },
        },
    }

    result = TaskResult(
        task_id="research_analysis_task",
        agent_id="researcher_analyst",
        output={"mcp": mcp_data, "analysis": analysis_results},
        status="success",
    )

    return {
        "mcp_data": mcp_data,
        "scraped_data": {"web_search_results": scraped_data},
        "research_interpretation": interpretation,
        "analysis_results": analysis_results,
        "completed_tasks": completed_tasks + [result.model_dump()],
        "pending_tasks": state.get("pending_tasks", []),
        "messages": [("ai", f"{interpretation}\n\n{analysis_text}")],
        "next_agent": "researcher",
    }
