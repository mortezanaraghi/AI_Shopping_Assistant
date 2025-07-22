"""
Smart Termination Analyzer
Analyzes ReAct state to determine optimal termination conditions.
"""
from __future__ import annotations
from typing import Tuple, List, Dict, Any
from .react_models import ReActState, ReasoningResult
from .utils.logging import init_logger
from .config import get_settings

settings = get_settings()
log = init_logger(settings.log_level)

class SmartTerminationAnalyzer:
    """Analyzes ReAct state to determine optimal termination."""
    
    def __init__(self, max_iterations: int = 5, max_clarifications: int = 2, max_failures: int = 3):
        self.max_iterations = max_iterations
        self.max_clarifications = max_clarifications
        self.max_failures = max_failures
    
    def should_terminate(self, react_state: ReActState, reasoning_result: ReasoningResult) -> Tuple[bool, str]:
        """Determine if loop should terminate early."""
        
        # Check for successful product search with high confidence
        has_products = self._has_product_results(react_state)
        if has_products and reasoning_result.confidence > 0.7:
            return True, "Sufficient product results found with high confidence"
        
        # Check for excessive clarifications
        clarification_count = self._count_clarifications(react_state)
        if clarification_count >= self.max_clarifications:
            return True, f"Too many clarifications requested ({clarification_count})"
        
        # Check for tool failures
        failed_tools = self._count_failed_tools(react_state)
        if failed_tools >= self.max_failures:
            return True, f"Too many tool failures ({failed_tools})"
        
        # Check iteration limit
        if react_state.current_iteration >= self.max_iterations:
            return True, f"Maximum iterations reached ({self.max_iterations})"
        
        # Check if we have any successful results and confidence is reasonable
        if has_products and reasoning_result.confidence > 0.5:
            return True, "Sufficient results found with reasonable confidence"
        
        # Check if we're stuck in a loop (same tool called repeatedly)
        if self._is_stuck_in_loop(react_state):
            return True, "Detected repetitive tool usage pattern"
        
        return False, "Continue"
    
    def _has_product_results(self, react_state: ReActState) -> bool:
        """Check if we have meaningful product results."""
        for entry in react_state.tool_execution_history:
            if (entry.get("success") and 
                entry.get("tool_name") == "sg_list_candidates" and
                entry.get("result")):
                # Check if result contains product information
                result = entry.get("result", "")
                if isinstance(result, str) and ("product" in result.lower() or "laptop" in result.lower() or "found" in result.lower()):
                    return True
                elif isinstance(result, (list, dict)) and len(result) > 0:
                    return True
        return False
    
    def _count_clarifications(self, react_state: ReActState) -> int:
        """Count clarification requests."""
        return sum(1 for r in react_state.tool_execution_history 
                  if r.get("action") == "clarification")
    
    def _count_failed_tools(self, react_state: ReActState) -> int:
        """Count failed tool executions."""
        return sum(1 for r in react_state.tool_execution_history 
                  if not r.get("success"))
    
    def _is_stuck_in_loop(self, react_state: ReActState) -> bool:
        """Check if we're stuck calling the same tool repeatedly."""
        if len(react_state.tool_execution_history) < 3:
            return False
        
        # Get last 3 tool calls
        recent_tools = [r.get("tool_name") for r in react_state.tool_execution_history[-3:] 
                       if r.get("tool_name")]
        
        # Check if same tool called 3 times in a row
        if len(recent_tools) == 3 and len(set(recent_tools)) == 1:
            return True
        
        return False
    
    def get_termination_reason(self, react_state: ReActState) -> str:
        """Get a human-readable reason for termination."""
        if react_state.current_iteration >= self.max_iterations:
            return f"Reached maximum iterations ({self.max_iterations})"
        
        clarification_count = self._count_clarifications(react_state)
        if clarification_count >= self.max_clarifications:
            return f"Too many clarification requests ({clarification_count})"
        
        failed_tools = self._count_failed_tools(react_state)
        if failed_tools >= self.max_failures:
            return f"Too many tool failures ({failed_tools})"
        
        if self._is_stuck_in_loop(react_state):
            return "Detected repetitive tool usage pattern"
        
        return "Unknown termination reason"
    
    def get_state_summary(self, react_state: ReActState) -> Dict[str, Any]:
        """Get a summary of the current ReAct state."""
        return {
            "iteration": react_state.current_iteration,
            "max_iterations": self.max_iterations,
            "successful_tools": len([r for r in react_state.tool_execution_history if r.get("success")]),
            "failed_tools": self._count_failed_tools(react_state),
            "clarifications": self._count_clarifications(react_state),
            "has_products": self._has_product_results(react_state),
            "stuck_in_loop": self._is_stuck_in_loop(react_state),
            "total_actions": len(react_state.tool_execution_history)
        } 