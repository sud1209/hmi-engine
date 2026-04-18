from typing import TypedDict, Annotated, List, Optional, Dict, Any
from langgraph.graph.message import add_messages

class ResearchState(TypedDict):
    # Input
    query: str                          # Original research question
    research_plan: List[str]            # Supervisor-generated subtasks
    
    # Inter-agent messages (LangGraph message list)
    messages: Annotated[List[Any], add_messages]
    
    # A2A task tracking (Simplified for Phase 2)
    pending_tasks: List[Dict[str, Any]]
    completed_tasks: List[Dict[str, Any]]
    
    # Data collected by researcher
    mcp_data: Dict[str, Any]
    scraped_data: Dict[str, Any]
    news_data: List[Dict[str, Any]]
    research_interpretation: str          # Haiku summary from researcher
    past_context_summary: str             # Episodic memory snippets from prior runs
    
    # Outputs of analyst
    analysis_results: Dict[str, Any]
    
    # Final outputs
    report: Optional[Dict[str, Any]]
    dashboard: Optional[Dict[str, Any]]
    
    # HITL/Self-Correction
    is_approved: bool
    critique: Optional[str]
    llm_error: Optional[str]              # Set if an upstream LLM call failed; writer aborts
    all_tasks_raw: List[Dict[str, Any]]  # Persisted task list across HITL pause

    # Routing control
    next_agent: str                     # "researcher" | "analyst" | "writer" | "END"
    iteration_count: int
