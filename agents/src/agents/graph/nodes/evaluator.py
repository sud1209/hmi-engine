import re
from typing import Dict, Any
import structlog
from agents.graph.state import ResearchState

log = structlog.get_logger(__name__)

_REQUIRED_SECTIONS = [
    "Executive Summary",
    "Market Conditions",
    "Investment Outlook",
    "Key Risks",
]

# Report must contain at least one number (prices, rates, percentages)
_HAS_NUMBERS = re.compile(r'\$[\d,]+|[\d.]+%|\d+ day')


async def run(state: ResearchState) -> Dict[str, Any]:
    """Evaluator node: structural + content check — no LLM call needed."""

    query = state["query"]
    report_md = state.get("report", {}).get("report_markdown", "")

    missing_sections = [s for s in _REQUIRED_SECTIONS if s not in report_md]
    has_numbers = bool(_HAS_NUMBERS.search(report_md))
    # Must be long enough to be a real report (>200 chars)
    too_short = len(report_md) < 200

    failures = []
    if missing_sections:
        failures.append(f"Missing sections: {', '.join(missing_sections)}")
    if not has_numbers:
        failures.append("Report contains no quantitative data")
    if too_short:
        failures.append("Report is too short")

    passed = not failures
    critique = "; ".join(failures) if failures else None

    log.info("evaluator.result", passed=passed, critique=critique)

    if passed:
        return {
            "messages": [("system", "Evaluator: PASS")],
            "next_agent": "END",
            "critique": None,
            "pending_tasks": state.get("pending_tasks", []),
            "completed_tasks": state.get("completed_tasks", []),
        }
    else:
        return {
            "messages": [("system", f"Evaluator: FAIL — {critique}")],
            "next_agent": "writer",
            "critique": critique,
            "pending_tasks": state.get("pending_tasks", []),
            "completed_tasks": state.get("completed_tasks", []),
        }
