from typing import Dict, Any, List, Optional, Union, Literal
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

class AgentCard(BaseModel):
    """Defines an agent's capabilities and role in the system."""
    agent_id: str
    name: str
    role: str
    capabilities: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

class Task(BaseModel):
    """Represents a delegated unit of work in the A2A protocol."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    description: str
    assigned_to: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class TaskResult(BaseModel):
    """Represents the outcome of a completed task."""
    task_id: str
    agent_id: str
    output: Any
    status: Literal["success", "error"]
    error: Optional[str] = None
    completed_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class A2AMessage(BaseModel):
    """Union type for A2A messages."""
    type: Literal["task", "task_result", "agent_card"]
    content: Union[Task, TaskResult, AgentCard]
