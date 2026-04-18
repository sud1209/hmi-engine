import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_harness_smoke_succeeds_when_graph_returns_results():
    """Smoke run completes with success=True when graph returns report+dashboard."""
    from agents.eval.eval_harness import ResearchEvalHarness

    # Mock graph to return a complete result immediately (bypass LLM)
    mock_snapshot = {"research_plan": ["step 1", "step 2"]}
    mock_result = {
        "report": {"report_markdown": "# Report"},
        "dashboard": {"kpis": {}},
        "messages": [],
        "iteration_count": 5,
    }

    with patch("agents.eval.eval_harness.graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(side_effect=[mock_snapshot, mock_result])
        harness = ResearchEvalHarness()
        await harness.run_benchmark(
            [{"query": "Austin housing market"}],
            smoke=True,
        )

    assert len(harness.results) == 1
    assert harness.results[0]["success"] is True
    assert harness.results[0]["has_report"] is True
    assert harness.results[0]["has_dashboard"] is True


@pytest.mark.asyncio
async def test_harness_smoke_calls_graph_twice_for_hitl():
    """Smoke run must call graph.ainvoke twice: once for plan, once with approval."""
    from agents.eval.eval_harness import ResearchEvalHarness

    mock_snapshot = {"research_plan": ["step 1"]}
    mock_result = {"report": {}, "dashboard": {}, "messages": [], "iteration_count": 3}

    with patch("agents.eval.eval_harness.graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(side_effect=[mock_snapshot, mock_result])
        harness = ResearchEvalHarness()
        await harness.run_benchmark([{"query": "test query"}], smoke=True)

    assert mock_graph.ainvoke.call_count == 2
    # Second call must pass is_approved=True
    second_call_args = mock_graph.ainvoke.call_args_list[1]
    state_arg = second_call_args[0][0]
    assert state_arg.get("is_approved") is True
    # Second call must also pass config with thread_id
    second_call_kwargs = mock_graph.ainvoke.call_args_list[1]
    # config is the second positional arg or a kwarg
    if len(second_call_kwargs[0]) > 1:
        config_arg = second_call_kwargs[0][1]
    else:
        config_arg = second_call_kwargs[1].get("config", {})
    assert "configurable" in config_arg
    assert "thread_id" in config_arg["configurable"]


@pytest.mark.asyncio
async def test_harness_smoke_only_one_case():
    """Smoke=True must only run the first test case."""
    from agents.eval.eval_harness import ResearchEvalHarness

    mock_snapshot = {"research_plan": []}
    mock_result = {"report": {}, "dashboard": {}, "messages": [], "iteration_count": 1}

    with patch("agents.eval.eval_harness.graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(side_effect=[mock_snapshot, mock_result] * 5)
        harness = ResearchEvalHarness()
        await harness.run_benchmark(
            [{"query": "Q1"}, {"query": "Q2"}, {"query": "Q3"}],
            smoke=True,
        )

    assert len(harness.results) == 1  # Only first case


@pytest.mark.asyncio
async def test_harness_records_failure_on_exception():
    """If graph raises, the result entry has success=False."""
    from agents.eval.eval_harness import ResearchEvalHarness

    with patch("agents.eval.eval_harness.graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        harness = ResearchEvalHarness()
        await harness.run_benchmark([{"query": "failing query"}], smoke=False)

    assert len(harness.results) == 1
    assert harness.results[0]["success"] is False
    assert "LLM timeout" in harness.results[0]["error"]


@pytest.mark.asyncio
async def test_harness_initial_state_has_all_required_keys():
    """Initial state passed to graph must include past_context_summary."""
    from agents.eval.eval_harness import ResearchEvalHarness

    captured_states = []

    async def capture_invoke(state, config=None):
        captured_states.append(state)
        if len(captured_states) == 1:
            return {"research_plan": []}
        return {"report": {}, "dashboard": {}, "messages": [], "iteration_count": 1}

    with patch("agents.eval.eval_harness.graph") as mock_graph:
        mock_graph.ainvoke = AsyncMock(side_effect=capture_invoke)
        harness = ResearchEvalHarness()
        await harness.run_benchmark([{"query": "test"}], smoke=False)

    initial = captured_states[0]
    required_keys = [
        "query", "research_plan", "all_tasks_raw", "messages", "pending_tasks",
        "completed_tasks", "mcp_data", "scraped_data", "news_data",
        "research_interpretation", "past_context_summary", "analysis_results",
        "report", "dashboard", "is_approved", "critique", "llm_error",
        "next_agent", "iteration_count",
    ]
    for key in required_keys:
        assert key in initial, f"Missing required state key: {key}"
