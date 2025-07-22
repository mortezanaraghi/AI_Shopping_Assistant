"""
ReAct Orchestrator Implementation
Implements the documented ReAct (Reason-Act) pattern as described in ADR-002.
This is the primary orchestrator that provides dynamic, iterative reasoning.
"""
from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI
from opentelemetry import trace

from .config import get_settings
from .utils.logging import init_logger
from .models import ConversationContext, AgentResponse, UserQuery, UserProfile
from .state_manager import DistributedStateManager
from .agent_framework import AgentRegistry, agent_registry
from .react_models import ReActState, ReasoningResult, ActionResult, ReActExecutionPlan
from .tool_schema_registry import ToolSchemaRegistry
from .smart_termination_analyzer import SmartTerminationAnalyzer
from .tools import (
    sg_list_candidates, sg_price_drop, sg_promotions,
    sg_variants, sg_criteria, sg_category,
)

settings = get_settings()
log = init_logger(settings.log_level)
tracer = trace.get_tracer("product_ai.react_orchestrator")

# Legacy tool mapping for backwards compatibility
LEGACY_TOOLS: Dict[str, Any] = {
    "sg_list_candidates": sg_list_candidates.run,
    "sg_price_drop": sg_price_drop.run,
    "sg_promotions": sg_promotions.run,
    "sg_variants": sg_variants.run,
    "sg_criteria": sg_criteria.run,
    "sg_category": sg_category.run,
}

# Import codegen tools with error handling
try:
    from .tools.codegen_fast import run as codegen_fast
    from .tools.codegen_slow import run as codegen_slow
    LEGACY_TOOLS["codegen_fast"] = codegen_fast
    LEGACY_TOOLS["codegen_slow"] = codegen_slow
    CODEGEN_AVAILABLE = True
except ImportError:
    CODEGEN_AVAILABLE = False

class ReActOrchestrator:
    """
    Implements the documented ReAct (Reason-Act) pattern as described in ADR-002.
    This is the primary orchestrator that should replace the current agent coordination approach.
    """
    
    def __init__(self, state_manager: Optional[DistributedStateManager] = None):
        self.state_manager = state_manager or DistributedStateManager()
        self.max_iterations = getattr(settings, 'react_max_iterations', 5)  # Reduced from 10
        self.confidence_threshold = getattr(settings, 'react_confidence_threshold', 0.7)
        self.llm_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.agent_registry = agent_registry
        
        # Enhanced components
        self.tool_registry = ToolSchemaRegistry()
        self.termination_analyzer = SmartTerminationAnalyzer(
            max_iterations=self.max_iterations,
            max_clarifications=2,
            max_failures=3
        )
        
    async def process_query(self, user_input: str, ctx: ConversationContext) -> AgentResponse:
        """
        Enhanced ReAct loop implementation with smart termination and validation.
        """
        try:
            with tracer.start_as_current_span("react_orchestrator.process_query") as span:
                span.set_attribute("query.text", user_input)
                span.set_attribute("session_id", ctx.session_id)
                
                # Initialize ReAct state
                react_state = ReActState(
                    original_query=user_input,
                    conversation_history=ctx.history or [],
                    user_profile=ctx.user_profile,
                    tool_execution_history=[],
                    current_iteration=0,
                    session_id=ctx.session_id
                )
                
                # Main ReAct loop
                while react_state.current_iteration < self.max_iterations:
                    span.set_attribute(f"iteration.{react_state.current_iteration}", True)
                    
                    # STEP 1: REASON (The "Thinking Step")
                    reasoning_result = await self._reason(react_state)
                    
                    # STEP 2: Check for early termination
                    should_terminate, reason = self.termination_analyzer.should_terminate(
                        react_state, reasoning_result
                    )
                    
                    if should_terminate:
                        log.info(f"Early termination: {reason}")
                        final_response = await self._synthesize_final_response(react_state)
                        span.set_attribute("response.confidence", final_response.confidence)
                        span.set_attribute("termination.reason", reason)
                        return final_response
                    
                    # STEP 3: ACT with validation
                    action_result = await self._act_with_validation(reasoning_result, react_state)
                    
                    # STEP 4: OBSERVE
                    await self._observe(action_result, react_state)
                    
                    # Check if we should terminate
                    if reasoning_result.action_type == "final_answer":
                        final_response = await self._synthesize_final_response(react_state)
                        span.set_attribute("response.confidence", final_response.confidence)
                        return final_response
                    
                    react_state.current_iteration += 1
                
                # Safety fallback
                log.warning(f"ReAct loop reached max iterations ({self.max_iterations})")
                return await self._synthesize_final_response(react_state)
                
        except Exception as e:
            log.error(f"ReAct orchestration failed: {e}", exc_info=True)
            return AgentResponse(
                content="I encountered an error while processing your request. Please try again.",
                confidence=0.0
            )
    
    async def _reason(self, react_state: ReActState) -> ReasoningResult:
        """
        The "Thinking Step" - LLM analyzes current state and decides next action.
        """
        try:
            prompt = self._build_enhanced_reasoning_prompt(react_state)
            
            response = await self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=30
            )
            
            result_json = response.choices[0].message.content
            return ReasoningResult.model_validate_json(result_json)
            
        except Exception as e:
            log.error(f"Reasoning step failed: {e}")
            # Fallback reasoning
            return ReasoningResult(
                thought="Error in reasoning step, providing basic response",
                action_type="final_answer",
                final_response="I'm having trouble processing that request. Could you please rephrase it?",
                confidence=0.3
            )
    
    async def _act_with_validation(self, reasoning: ReasoningResult, react_state: ReActState) -> ActionResult:
        """
        Execute the action with tool argument validation.
        """
        if reasoning.action_type == "use_tool":
            # Validate tool arguments
            is_valid, error_msg = self.tool_registry.validate_arguments(
                reasoning.tool_name, reasoning.tool_args
            )
            
            if not is_valid:
                return ActionResult(
                    action_type="use_tool",
                    content=f"Tool validation failed: {error_msg}",
                    success=False,
                    error_message=error_msg,
                    tool_name=reasoning.tool_name
                )
        
        # Proceed with normal execution
        return await self._act(reasoning, react_state)
    
    async def _act(self, reasoning: ReasoningResult, react_state: ReActState) -> ActionResult:
        """
        Execute the action decided by the reasoning step.
        """
        start_time = time.time()
        
        try:
            if reasoning.action_type == "use_tool":
                return await self._execute_tool(reasoning.tool_name, reasoning.tool_args, start_time, react_state)
            elif reasoning.action_type == "ask_clarification":
                return ActionResult(
                    action_type="clarification",
                    content=reasoning.clarification_question or "Could you please provide more details?",
                    success=True
                )
            elif reasoning.action_type == "final_answer":
                return ActionResult(
                    action_type="final_answer",
                    content=reasoning.final_response or "I've completed the analysis.",
                    success=True
                )
            else:
                return ActionResult(
                    action_type="error",
                    content="Unknown action type",
                    success=False,
                    error_message=f"Unknown action type: {reasoning.action_type}"
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ActionResult(
                action_type="error",
                content=f"Action execution failed: {str(e)}",
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time
            )
    
    async def _observe(self, action_result: ActionResult, react_state: ReActState):
        """
        Record the result of the action for the next reasoning step.
        """
        react_state.tool_execution_history.append({
            "iteration": react_state.current_iteration,
            "action": action_result.action_type,
            "result": action_result.content,
            "success": action_result.success,
            "tool_name": action_result.tool_name,
            "execution_time_ms": action_result.execution_time_ms,
            "timestamp": time.time()
        })
        
        # Accumulate insights
        if action_result.data:
            react_state.accumulated_insights.update(action_result.data)
    
    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any], start_time: float, react_state: ReActState) -> ActionResult:
        """
        Execute a tool using the existing agent registry or legacy tools.
        """
        try:
            # First try to find an agent that can handle this tool
            agent = self._find_agent_for_tool(tool_name)
            if agent:
                # Use agent-based execution
                query = UserQuery(text=f"Execute {tool_name} with {tool_args}")
                context = ConversationContext(
                    session_id=react_state.session_id or "react_session",
                    user_profile=react_state.user_profile
                )
                response = await agent.execute(query, context)
                execution_time = (time.time() - start_time) * 1000
                
                return ActionResult(
                    action_type="use_tool",
                    content=response.content,
                    success=response.confidence > 0.5,
                    data=response.data,
                    tool_name=tool_name,
                    execution_time_ms=execution_time
                )
            else:
                # Fall back to legacy tool execution
                result = await self._safe_tool_call(tool_name, tool_args)
                execution_time = (time.time() - start_time) * 1000
                
                return ActionResult(
                    action_type="use_tool",
                    content=str(result),
                    success=result.get("ok", False),
                    data=result,
                    tool_name=tool_name,
                    execution_time_ms=execution_time
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ActionResult(
                action_type="use_tool",
                content=f"Tool execution failed: {str(e)}",
                success=False,
                error_message=str(e),
                tool_name=tool_name,
                execution_time_ms=execution_time
            )
    
    def _find_agent_for_tool(self, tool_name: str):
        """Find an agent that can handle the specified tool."""
        # Simple mapping for now - could be enhanced with capability matching
        tool_to_agent = {
            "sg_list_candidates": "product_discovery",
            "sg_price_drop": "price_analysis",
            "sg_promotions": "price_analysis",
            "sg_variants": "product_discovery",
            "sg_criteria": "product_discovery",
            "sg_category": "product_discovery",
            "codegen_fast": "codegen",
            "codegen_slow": "codegen"
        }
        
        agent_id = tool_to_agent.get(tool_name)
        if agent_id:
            return self.agent_registry.get_agent(agent_id)
        return None
    
    async def _safe_tool_call(self, name: str, args: dict) -> Dict[str, Any]:
        """Safely execute a legacy tool call."""
        try:
            if name in LEGACY_TOOLS:
                return await asyncio.wait_for(
                    LEGACY_TOOLS[name](**args), 
                    timeout=30
                )
            else:
                return {"ok": False, "error": f"Unknown tool: {name}"}
        except Exception as e:
            log.error(f"Tool {name} failed: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}
    
    async def _synthesize_final_response(self, react_state: ReActState) -> AgentResponse:
        """
        Synthesize the final response from accumulated insights and tool results.
        """
        # Use the last successful action result as the primary response
        successful_results = [r for r in react_state.tool_execution_history if r["success"]]
        
        if successful_results:
            last_result = successful_results[-1]
            content = last_result["result"]
            confidence = 0.8 if len(successful_results) > 1 else 0.6
        else:
            content = "I wasn't able to complete the analysis. Please try rephrasing your question."
            confidence = 0.3
        
        # Collect all tool calls
        tool_calls = [r["tool_name"] for r in react_state.tool_execution_history if r["tool_name"]]
        
        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            agent_id="react_orchestrator",
            confidence=confidence,
            data=react_state.accumulated_insights
        )
    
    def _build_enhanced_reasoning_prompt(self, react_state: ReActState) -> str:
        """
        Build enhanced reasoning prompt with shopping-specific guidance.
        """
        # Analyze current state
        successful_tools = [r for r in react_state.tool_execution_history if r["success"]]
        clarification_count = sum(1 for r in react_state.tool_execution_history 
                                if r.get("action") == "clarification")
        
        prompt = f"""
You are Product.ai, a shopping assistant using ReAct (Reason and Act) pattern.

CURRENT STATE:
- Query: {react_state.original_query}
- Iteration: {react_state.current_iteration}/{self.max_iterations}
- Successful tools: {len(successful_tools)}
- Clarifications asked: {clarification_count}

TOOL HISTORY:
{self._format_tool_history(react_state.tool_execution_history)}

AVAILABLE TOOLS:
{self._format_available_tools_with_schemas()}

DECISION CRITERIA:

**Use FINAL_ANSWER when:**
✅ You have product results from sg_list_candidates
✅ You have sufficient information to help the user
✅ User's question has been answered
✅ You have at least 1 successful tool execution

**Use ASK_CLARIFICATION when:**
❓ Query is ambiguous (e.g., "find laptops" - need budget/brand/use case)
❓ Missing critical info (budget, brand preferences, specific requirements)
❓ Query too broad and needs narrowing

**Use USE_TOOL when:**
🔍 Need to search for products (sg_list_candidates)
🔧 Need price/promotion info for found products
🔧 Haven't executed any tools yet

TERMINATION RULES:
- Max {self.max_iterations} iterations total
- Stop after 2 clarifications
- Stop if you have product results and confidence > 0.7

RESPONSE FORMAT (JSON):
{{
    "thought": "Your reasoning",
    "action_type": "use_tool|ask_clarification|final_answer",
    "confidence": 0.0-1.0,
    "tool_name": "tool_name" (if use_tool),
    "tool_args": {{"query": "search term"}} (if use_tool),
    "clarification_question": "question" (if ask_clarification),
    "final_response": "complete answer" (if final_answer)
}}
"""
        return prompt
    
    def _format_user_profile(self, profile: Optional[UserProfile]) -> str:
        """Format user profile for the prompt."""
        if not profile:
            return "No user profile available"
        
        return f"""
- User ID: {profile.user_id}
- Price Sensitivity: {profile.price_sensitivity}
- Brand Preferences: {profile.brand_preferences}
- Expertise Level: {profile.expertise_level}
- Recent Interactions: {len(profile.interaction_history)}
"""
    
    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """Format conversation history for the prompt."""
        if not history:
            return "No conversation history"
        
        formatted = []
        for msg in history[-5:]:  # Last 5 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]  # Truncate long messages
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _format_tool_history(self, history: List[Dict[str, Any]]) -> str:
        """Format tool execution history for the prompt."""
        if not history:
            return "No tools executed yet"
        
        formatted = []
        for entry in history:
            tool_name = entry.get("tool_name", "unknown")
            success = entry.get("success", False)
            result = entry.get("result", "")[:50]  # Truncate long results
            formatted.append(f"- {tool_name}: {'✓' if success else '✗'} {result}")
        
        return "\n".join(formatted)
    
    def _format_available_tools_with_schemas(self) -> str:
        """Format available tools with their schemas for the prompt."""
        tools = []
        for tool_name in self.tool_registry.list_available_tools():
            tools.append(self.tool_registry.get_tool_description(tool_name))
        return "\n".join(tools)
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the ReAct orchestrator."""
        return {
            "status": "healthy",
            "orchestrator": "react",
            "max_iterations": self.max_iterations,
            "confidence_threshold": self.confidence_threshold,
            "available_tools": len(self.tool_registry.list_available_tools()),
            "codegen_available": CODEGEN_AVAILABLE,
            "enhanced_features": {
                "tool_validation": True,
                "smart_termination": True,
                "schema_registry": True
            }
        } 