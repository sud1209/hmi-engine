"""
Research pipeline eval harness.

Usage:
  # Full benchmark (all test cases):
  uv run python agents/eval/eval_harness.py

  # Smoke test (CI — single query, validates schema, exits 0/1):
  uv run python agents/eval/eval_harness.py --smoke
"""
import asyncio
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List

from agents.graph.graph import graph


class ResearchEvalHarness:
    """Testing & eval infrastructure for benchmarking the research pipeline."""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    async def run_benchmark(
        self,
        test_cases: List[Dict[str, str]],
        smoke: bool = False,
    ) -> None:
        """Run test cases end-to-end, bypassing HITL for non-interactive evaluation.

        In smoke mode, only the first test case is run and the process exits
        with code 1 if it fails (for CI integration).
        """
        cases = test_cases[:1] if smoke else test_cases
        print(f"Starting {'smoke' if smoke else 'full'} benchmark: {len(cases)} case(s)")

        for case in cases:
            query = case["query"]
            run_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": run_id}}
            start = time.time()
            print(f"Query: {query}")

            initial_state = {
                "query": query,
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

            try:
                # Pass 1: supervisor decomposes query, pauses at HITL
                snapshot = await graph.ainvoke(initial_state, config)
                plan = snapshot.get("research_plan", [])
                print(f"  Plan: {len(plan)} step(s)")

                # Pass 2: resume with approval (HITL bypassed for eval)
                result = await graph.ainvoke({"is_approved": True}, config)

                duration = round(time.time() - start, 2)
                has_report = result.get("report") is not None
                has_dashboard = result.get("dashboard") is not None

                entry = {
                    "query": query,
                    "duration_sec": duration,
                    "success": has_report and has_dashboard,
                    "num_steps": result.get("iteration_count", 0),
                    "num_messages": len(result.get("messages", [])),
                    "has_report": has_report,
                    "has_dashboard": has_dashboard,
                }
                self.results.append(entry)
                status = "OK" if entry["success"] else "WARN"
                print(f"[{status}] {duration}s — report={has_report}, dashboard={has_dashboard}")

            except Exception as e:
                import traceback
                traceback.print_exc()
                self.results.append({
                    "query": query,
                    "duration_sec": round(time.time() - start, 2),
                    "success": False,
                    "error": str(e),
                })
                print(f"[FAIL] {e}")

        self._save_results()

        if smoke:
            failed = [r for r in self.results if not r.get("success")]
            if failed:
                print(f"\nSmoke test FAILED: {failed[0].get('error', 'report or dashboard missing')}")
                sys.exit(1)
            print("\nSmoke test passed.")

    def _save_results(self) -> None:
        output_dir = "agents/eval"
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "benchmark_results.json")
        with open(path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to {path}")


async def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Run smoke test for CI")
    args = parser.parse_args()

    harness = ResearchEvalHarness()
    test_cases = [
        {"query": "Austin real estate ROI for 78701"},
        {"query": "Seattle housing market sentiment 2026"},
    ]
    await harness.run_benchmark(test_cases, smoke=args.smoke)


if __name__ == "__main__":
    asyncio.run(main())
