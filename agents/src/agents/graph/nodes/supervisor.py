from typing import Dict, Any
from agents.graph.state import ResearchState
from agents.a2a.router import decompose_query, route_task
from agents.a2a.protocol import Task, TaskResult
from agents.tools.memory import EpisodicMemory
import litellm
import structlog
import traceback

log = structlog.get_logger(__name__)

async def run(state: ResearchState) -> Dict[str, Any]:
    """Supervisor node: Orchestrates US housing research tasks using A2A."""

    try:
        query = state["query"]
        pending_tasks = list(state.get("pending_tasks", []))
        completed_tasks = state.get("completed_tasks", [])
        messages = state.get("messages", [])
        iteration_count = state.get("iteration_count", 0)
        is_approved = state.get("is_approved", False)

        log.info("supervisor.tick", iteration=iteration_count, approved=is_approved, pending=len(pending_tasks), completed=len(completed_tasks))

        # ── Pass 1: Decompose query and pause for HITL approval ──────────────
        if iteration_count == 0:
            log.info("supervisor.decompose_start")
            memory = EpisodicMemory()
            past_context = memory.search_memory(query)
            # Summarise past episodes into a compact string for downstream prompts
            past_context_summary = ""
            if past_context:
                snippets = [
                    f"- {ep.get('query', '')}: {ep.get('summary', '')[:120]}"
                    for ep in past_context[:3]
                ]
                past_context_summary = "Prior research:\n" + "\n".join(snippets)

            new_tasks = await decompose_query(query)
            log.info("supervisor.decomposed", task_count=len(new_tasks))

            plan = [t.description for t in new_tasks]
            all_tasks_raw = [t.model_dump() for t in new_tasks]

            return {
                "research_plan": plan,
                "all_tasks_raw": all_tasks_raw,
                "past_context_summary": past_context_summary,
                "pending_tasks": [],
                "next_agent": "END",
                "iteration_count": 1,
                "is_approved": False,
                "messages": messages + [
                    ("system", f"Supervisor decomposed query. {len(past_context)} past reports found."),
                    ("system", "HITL: Research plan ready for approval."),
                ],
            }

        # ── Pass 2: Resume after HITL approval ───────────────────────────────
        if iteration_count == 1 and is_approved:
            all_tasks_raw = state.get("all_tasks_raw", [])
            log.info("supervisor.resume_after_approval", task_count=len(all_tasks_raw))

            if not all_tasks_raw:
                log.warning("supervisor.no_tasks_after_approval")
                return {
                    "next_agent": "END",
                    "iteration_count": 2,
                    "messages": messages + [("system", "No tasks to execute after approval.")],
                }

            tasks = [Task(**t) for t in all_tasks_raw]
            first_task = tasks[0]
            remaining = tasks[1:]

            log.info("supervisor.dispatch_first_task", agent=first_task.assigned_to)
            return {
                "all_tasks_raw": [],  # consumed
                "pending_tasks": [t.model_dump() for t in remaining],
                "next_agent": first_task.assigned_to,
                "iteration_count": 2,
                "messages": messages + [
                    ("system", "HITL approved. Dispatching first research task."),
                ],
            }

        # ── Pass 3+: Route through remaining tasks, then write → evaluate ───
        if pending_tasks:
            next_task_data = pending_tasks.pop(0)
            next_task = Task(**next_task_data)
            log.info("supervisor.route_next_task", agent=next_task.assigned_to)
            return {
                "pending_tasks": pending_tasks,
                "next_agent": next_task.assigned_to,
                "iteration_count": iteration_count + 1,
                "messages": messages + [
                    ("system", f"Routing to: {next_task.assigned_to}"),
                ],
            }

        # ── All tasks done — route to writer → evaluator → END ───────────────
        last_agent = state.get("next_agent")
        log.info("supervisor.all_tasks_complete", last_agent=last_agent)

        if last_agent not in ("writer", "evaluator", "END"):
            log.info("supervisor.route_to_writer")
            return {
                "next_agent": "writer",
                "messages": messages + [("system", "All research done. Routing to writer.")],
            }
        elif last_agent == "writer":
            log.info("supervisor.route_to_evaluator")
            return {
                "next_agent": "evaluator",
                "messages": messages + [("system", "Writer finished. Routing to evaluator.")],
            }
        elif last_agent == "evaluator":
            log.info("supervisor.route_to_end")
            return {
                "next_agent": "END",
                "messages": messages + [("system", "Evaluation complete. Research finished.")],
            }

        log.warning("supervisor.fallback_to_end")
        return {
            "next_agent": "END",
            "messages": messages + [("system", "Housing research complete.")],
        }

    except Exception as e:
        log.exception("supervisor.exception", exc=str(e))
        raise Exception(f"Supervisor failed: {e}")
