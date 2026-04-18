import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agents.graph.graph import graph


def _configure_logging() -> None:
    log_format = os.getenv("LOG_FORMAT", "json")
    shared = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    renderer = structlog.dev.ConsoleRenderer() if log_format == "console" else structlog.processors.JSONRenderer()
    structlog.configure(
        processors=shared + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(processor=renderer, foreign_pre_chain=shared)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


_configure_logging()


# ── Pydantic models ────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)

class ApproveRequest(BaseModel):
    approved: bool = True


# ── In-memory run registry ─────────────────────────────────────────────────
# run_id → {status, plan, thread_id, result, finished_at}
# status: "awaiting_approval" | "running" | "complete" | "rejected" | "error"

_TERMINAL = {"complete", "rejected", "error"}
_TTL = timedelta(minutes=60)   # keep terminal runs for 60 min then discard

_runs: Dict[str, Dict[str, Any]] = {}


def _schedule_cleanup(run_id: str) -> None:
    """Delete a terminal run entry after TTL."""
    async def _delete():
        await asyncio.sleep(_TTL.total_seconds())
        _runs.pop(run_id, None)
    asyncio.create_task(_delete())


# ── Background runner ──────────────────────────────────────────────────────

async def _run_to_completion(run_id: str, config: dict) -> None:
    """Resume graph after approval and run to completion."""
    try:
        result = await graph.ainvoke({"is_approved": True}, config)
        _runs[run_id]["status"] = "complete"
        _runs[run_id]["result"] = {
            "report": result.get("report"),
            "dashboard": result.get("dashboard"),
            "messages": result.get("messages", []),
        }
    except Exception as exc:
        _runs[run_id]["status"] = "error"
        _runs[run_id]["error"] = str(exc)
    finally:
        _schedule_cleanup(run_id)


# ── FastAPI app ────────────────────────────────────────────────────────────

app = FastAPI(title="Market Research Agent Runner")


@app.post("/research")
async def research(request: ResearchRequest):
    """
    Start a research run.  Returns immediately with run_id + research plan.
    Status will be 'awaiting_approval' until the caller POSTs to /research/{id}/approve.
    """
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}

    initial_state = {
        "query": request.query,
        "research_plan": [],
        "all_tasks_raw": [],
        "messages": [],
        "pending_tasks": [],
        "completed_tasks": [],
        "mcp_data": {},
        "scraped_data": {},
        "news_data": [],
        "research_interpretation": "",
        "past_context_summary": "",
        "analysis_results": {},
        "report": None,
        "dashboard": None,
        "is_approved": False,
        "critique": None,
        "llm_error": None,
        "next_agent": "supervisor",
        "iteration_count": 0,
    }

    # First pass: supervisor decomposes query, writes plan, returns (next_agent="END")
    snapshot = await graph.ainvoke(initial_state, config)
    plan = snapshot.get("research_plan", [])

    _runs[run_id] = {
        "status": "awaiting_approval",
        "plan": plan,
        "thread_id": run_id,
        "result": None,
        "error": None,
    }

    return {
        "run_id": run_id,
        "status": "awaiting_approval",
        "plan": plan,
    }


@app.get("/research/{run_id}/status")
async def research_status(run_id: str):
    """Poll the status of a research run."""
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return {
        "run_id": run_id,
        "status": run["status"],
        "plan": run.get("plan"),
        "result": run.get("result"),
        "error": run.get("error"),
    }


@app.post("/research/{run_id}/approve")
async def research_approve(run_id: str, body: ApproveRequest = ApproveRequest()):
    """Approve or reject a research plan.  Approval resumes the graph."""
    run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    if run["status"] != "awaiting_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Run is not awaiting approval (current status: {run['status']})",
        )

    if not body.approved:
        run["status"] = "rejected"
        _schedule_cleanup(run_id)
        return {"run_id": run_id, "status": "rejected"}

    run["status"] = "running"
    config = {"configurable": {"thread_id": run["thread_id"]}}
    asyncio.create_task(_run_to_completion(run_id, config))

    return {"run_id": run_id, "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
