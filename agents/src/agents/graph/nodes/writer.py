import datetime
import litellm
import structlog
from typing import Dict, Any
from agents.graph.state import ResearchState
from agents.prompts.writer import WRITER_PROMPT
from agents.tools.memory import EpisodicMemory

log = structlog.get_logger(__name__)

MODEL = "claude-haiku-4-5-20251001"


async def run(state: ResearchState) -> Dict[str, Any]:
    """Writer node: Calls Haiku to synthesize all agent findings into a report."""

    query = state["query"]
    analysis = state.get("analysis_results", {})
    interpretation = state.get("research_interpretation", "")
    past_context_summary = state.get("past_context_summary", "")
    llm_error = state.get("llm_error")

    if llm_error:
        log.warning("writer.abort_llm_error", llm_error=llm_error)
        return {
            "report": {"title": query, "report_markdown": f"# Error\n{llm_error}", "status": "error"},
            "dashboard": {},
            "messages": [("system", f"Writer aborted: {llm_error}")],
            "next_agent": "writer",
            "pending_tasks": state.get("pending_tasks", []),
            "completed_tasks": state.get("completed_tasks", []),
        }

    # Compact context — only what Haiku needs to write the report
    context = (
        f"Query: {query}\n"
        f"Market sentiment: {analysis.get('market_sentiment', 'Neutral')}\n"
        f"Listings analyzed: {analysis.get('total_listings_analyzed', 0)}, "
        f"avg price: ${analysis.get('average_price_in_sample', 0):,.0f}\n"
        f"Est. annual ROI: {analysis.get('sample_roi_estimate', 0):.1f}%\n"
        f"Mortgage rate: {analysis.get('latest_mortgage_rate', 0)}%\n"
        f"Researcher notes: {interpretation}\n"
        f"Analyst notes: {analysis.get('analysis_summary', '')}"
        + (f"\n{past_context_summary}" if past_context_summary else "")
    )

    try:
        response = await litellm.acompletion(
            model=MODEL,
            messages=[
                {"role": "system", "content": WRITER_PROMPT},
                {"role": "user", "content": (
                    f"{context}\n\n"
                    "Write a housing market report in Markdown with these sections: "
                    "## Executive Summary, ## Market Conditions, ## Investment Outlook, ## Key Risks. "
                    "Be specific, cite the numbers above, keep each section to 2-3 sentences."
                )},
            ],
            max_tokens=700,
        )
        report_md = response.choices[0].message.content.strip()
    except Exception as e:
        report_md = f"# Report\nWriter error: {e}"

    report = {
        "title": f"US Housing Market Research: {query}",
        "report_markdown": report_md,
        "summary": analysis.get("analysis_summary", ""),
        "status": "completed",
    }

    dashboard = {
        "kpis": analysis.get("dashboard_kpis", {}),
        "last_updated": datetime.datetime.now().isoformat(),
    }

    log.info("writer.report_generated")

    try:
        memory = EpisodicMemory()
        memory.add_episode(query, report["summary"], f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    except Exception:
        pass

    return {
        "report": report,
        "dashboard": dashboard,
        "messages": [("ai", report_md[:200])],
        "next_agent": "writer",
        "pending_tasks": state.get("pending_tasks", []),
        "completed_tasks": state.get("completed_tasks", []),
    }
