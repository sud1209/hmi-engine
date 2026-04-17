import asyncio
import json
from typing import Any, Dict, List

import litellm
import structlog

from agents.a2a.protocol import Task
from agents.a2a.agent_cards import AGENT_CARDS

log = structlog.get_logger(__name__)

# Must match graph node names in agents/src/agents/graph/graph.py
VALID_AGENT_IDS = {"researcher_analyst", "news_analyst", "writer", "evaluator"}

# Map LLM-returned legacy or shorthand names to current graph node names
_AGENT_ID_REMAP = {
    "researcher": "researcher_analyst",
    "analyst": "researcher_analyst",
}

_DEFAULT_TIMEOUT = 15.0  # seconds


def _remap_agent_id(agent_id: str) -> str:
    return _AGENT_ID_REMAP.get(agent_id, agent_id)


async def decompose_query(
    query: str,
    model: str = "claude-haiku-4-5-20251001",
    timeout: float = _DEFAULT_TIMEOUT,
) -> List[Task]:
    """Decomposes a query into A2A Task objects using an LLM.

    Raises asyncio.TimeoutError if LLM call exceeds `timeout` seconds.
    Always returns tasks with agent_ids matching VALID_AGENT_IDS.
    Falls back to a safe default task list on JSON parse errors.
    """
    log.info("a2a.decompose.start", query=query[:100], model=model)

    agent_descriptions = "\n".join([
        f"- {card.agent_id}: {card.role} (Capabilities: {', '.join(card.capabilities)})"
        for card in AGENT_CARDS.values()
    ])

    prompt = f"""Decompose the following research query into 3-5 subtasks for specialized agents.
Research Query: "{query}"

Available Agents:
{agent_descriptions}

Output a JSON object with a "tasks" key containing a list of tasks. Each task must have:
- "type": the task type (string)
- "description": what to do (string)
- "assigned_to": one of: {', '.join(sorted(VALID_AGENT_IDS))}
- "payload": input parameters (object, can be empty)

Return ONLY the JSON object."""

    try:
        response = await asyncio.wait_for(
            litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=400,
            ),
            timeout=timeout,
        )
        content = response.choices[0].message.content
        log.debug("a2a.decompose.llm_response", content_len=len(content or ""))

        tasks_data = json.loads(content).get("tasks", [])
        tasks = []
        for t in tasks_data:
            t["assigned_to"] = _remap_agent_id(t.get("assigned_to", ""))
            if t["assigned_to"] not in VALID_AGENT_IDS:
                log.warning("a2a.decompose.invalid_agent", assigned_to=t["assigned_to"])
                t["assigned_to"] = "researcher_analyst"
            tasks.append(Task(**t))

        log.info("a2a.decompose.complete", num_tasks=len(tasks))
        return tasks

    except asyncio.TimeoutError:
        log.error("a2a.decompose.timeout", timeout=timeout)
        raise

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        log.warning("a2a.decompose.parse_error", error=str(e))
        return [
            Task(type="research", description=f"Collect housing data for: {query}", assigned_to="researcher_analyst"),
            Task(type="news", description=f"Research housing news for: {query}", assigned_to="news_analyst"),
            Task(type="synthesis", description=f"Write report for: {query}", assigned_to="writer"),
        ]


def route_task(task: Task) -> str:
    """Routes a task to the correct graph node name."""
    return _remap_agent_id(task.assigned_to)


def collect_results(completed_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregates TaskResult outputs into a structured state object."""
    results: Dict[str, List] = {}
    for res in completed_tasks:
        agent_id = res.get("agent_id", "unknown")
        results.setdefault(agent_id, []).append(res.get("output"))
    return results
