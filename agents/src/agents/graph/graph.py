import structlog
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agents.graph.state import ResearchState
from agents.graph.nodes import supervisor, researcher_analyst, writer, news_analyst, evaluator

log = structlog.get_logger(__name__)

def route_from_supervisor(state: ResearchState) -> str:
    """Conditional routing based on supervisor node's next_agent."""
    next_agent = state.get("next_agent", "END")
    log.debug("router.decision", next_agent=next_agent)

    if next_agent == "supervisor":
        return "supervisor"
    elif next_agent in ("researcher", "analyst"):
        return "researcher_analyst"  # both route to merged node
    elif next_agent == "news_analyst":
        return "news_analyst"
    elif next_agent == "writer":
        return "writer"
    elif next_agent == "evaluator":
        return "evaluator"
    else:
        log.warning("router.default_end", next_agent=next_agent)
        return "__end__"

builder = StateGraph(ResearchState)

builder.add_node("supervisor", supervisor.run)
builder.add_node("researcher_analyst", researcher_analyst.run)
builder.add_node("news_analyst", news_analyst.run)
builder.add_node("writer", writer.run)
builder.add_node("evaluator", evaluator.run)

builder.set_entry_point("supervisor")

builder.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "researcher_analyst": "researcher_analyst",
        "news_analyst": "news_analyst",
        "writer": "writer",
        "evaluator": "evaluator",
        "__end__": END,
    }
)

builder.add_edge("researcher_analyst", "supervisor")
builder.add_edge("news_analyst", "supervisor")
builder.add_edge("writer", "evaluator")
builder.add_edge("evaluator", "supervisor")

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)
