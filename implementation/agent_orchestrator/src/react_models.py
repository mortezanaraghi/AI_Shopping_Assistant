"""
ReAct Orchestration Data Models
Defines the data structures for the ReAct (Reason-Act) pattern implementation.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field

from .models import UserProfile

class ReActState(BaseModel):
    """State maintained throughout the ReAct loop."""
    original_query: str
    conversation_history: List[Dict[str, Any]]
    user_profile: Optional[UserProfile]
    tool_execution_history: List[Dict[str, Any]]
    current_iteration: int
    accumulated_insights: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None

class ReasoningResult(BaseModel):
    """Output of the reasoning step."""
    thought: str  # LLM's reasoning about current state
    action_type: Literal["use_tool", "ask_clarification", "final_answer"]
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    clarification_question: Optional[str] = None
    final_response: Optional[str] = None
    confidence: float = 0.0

class ActionResult(BaseModel):
    """Result of executing an action."""
    action_type: str
    content: str
    success: bool = True
    error_message: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    tool_name: Optional[str] = None
    execution_time_ms: float = 0.0

class ReActExecutionPlan(BaseModel):
    """Plan for ReAct execution."""
    query: str
    estimated_iterations: int
    required_tools: List[str]
    complexity_score: float
    can_parallelize: bool = False 