"""
Main Orchestrator Module
Entry point for shopping assistant that dynamically selects between ReAct orchestration,
Temporal workflow orchestration, enhanced agent-based orchestration, or legacy tool-based fallback.
"""
from __future__ import annotations
import asyncio
import json
from typing import Dict, List, Optional, Union, Any
from openai import AsyncOpenAI

from .config import get_settings
from .utils.logging import init_logger
from .models import ConversationContext, AgentResponse, UserQuery

# Import orchestrator implementations
from .enhanced_orchestrator import EnhancedOrchestrator

try:
    from .temporal_orchestrator import TemporalOrchestrator
    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False
    TemporalOrchestrator = None

try:
    from .react_orchestrator import ReActOrchestrator
    REACT_AVAILABLE = True
except ImportError:
    REACT_AVAILABLE = False
    ReActOrchestrator = None

settings = get_settings()
log = init_logger(settings.log_level)

class Orchestrator:
    """
    Main orchestrator that provides multiple processing modes:
    1. ReAct orchestration (primary for complex queries)
    2. Temporal workflow-based (if available)
    3. Enhanced agent-based
    4. Legacy tool-based fallback
    """
    
    def __init__(self, mode: str = "auto"):
        """
        Initialize orchestrator with specified mode.
        
        Args:
            mode: "auto", "react", "temporal", "enhanced", or "legacy"
        """
        self.mode = mode
        self.react_orchestrator: Optional[ReActOrchestrator] = None
        self.temporal_orchestrator: Optional[TemporalOrchestrator] = None
        self.enhanced_orchestrator = EnhancedOrchestrator()
        self.legacy_orchestrator = LegacyOrchestrator()
        
        # Initialize based on mode and availability
        self._initialize_orchestrators()
    
    def _initialize_orchestrators(self):
        """Initialize orchestrators based on mode and availability."""
        if self.mode == "auto":
            # Auto-select the best available option
            if REACT_AVAILABLE:
                try:
                    self.react_orchestrator = ReActOrchestrator()
                    self.active_mode = "react"
                    log.info("Auto-selected ReAct orchestrator")
                except Exception as e:
                    log.warning(f"Failed to initialize ReAct orchestrator: {e}")
                    self._fallback_to_enhanced()
            elif TEMPORAL_AVAILABLE:
                try:
                    self.temporal_orchestrator = TemporalOrchestrator()
                    self.active_mode = "temporal"
                    log.info("Auto-selected Temporal orchestrator")
                except Exception as e:
                    log.warning(f"Failed to initialize Temporal orchestrator: {e}")
                    self._fallback_to_enhanced()
            else:
                self._fallback_to_enhanced()
                
        elif self.mode == "react":
            if REACT_AVAILABLE:
                try:
                    self.react_orchestrator = ReActOrchestrator()
                    self.active_mode = "react"
                    log.info("Using ReAct orchestrator")
                except Exception as e:
                    log.error(f"ReAct mode requested but failed to initialize: {e}")
                    self._fallback_to_enhanced()
            else:
                log.error("ReAct mode requested but not available, falling back to enhanced")
                self._fallback_to_enhanced()
                
        elif self.mode == "temporal":
            if TEMPORAL_AVAILABLE:
                try:
                    self.temporal_orchestrator = TemporalOrchestrator()
                    self.active_mode = "temporal"
                    log.info("Using Temporal orchestrator")
                except Exception as e:
                    log.error(f"Temporal mode requested but failed to initialize: {e}")
                    self._fallback_to_enhanced()
            else:
                log.error("Temporal mode requested but not available, falling back to enhanced")
                self._fallback_to_enhanced()
                
        elif self.mode == "enhanced":
            self._fallback_to_enhanced()
            
        elif self.mode == "legacy":
            self.active_mode = "legacy"
            log.info("Using Legacy orchestrator")
            
        else:
            log.warning(f"Unknown mode '{self.mode}', defaulting to enhanced")
            self._fallback_to_enhanced()
    
    def _fallback_to_enhanced(self):
        """Fallback to enhanced orchestrator."""
        self.active_mode = "enhanced"
        log.info("Using Enhanced orchestrator")
    
    async def initialize(self):
        """Initialize the active orchestrator."""
        if self.active_mode == "react" and self.react_orchestrator:
            # ReAct orchestrator doesn't need special initialization
            log.info("ReAct orchestrator initialized")
        elif self.active_mode == "temporal" and self.temporal_orchestrator:
            await self.temporal_orchestrator.initialize()
            # Start worker if initialization succeeded
            if self.temporal_orchestrator.client:
                await self.temporal_orchestrator.start_worker()
            else:
                # Temporal failed, fall back to enhanced
                log.warning("Temporal initialization failed, falling back to enhanced mode")
                self.active_mode = "enhanced"
    
    async def process_query(
        self, 
        user_input: str, 
        context: ConversationContext,
        workflow_type: str = "auto"
    ) -> AgentResponse:
        """
        Process query using the appropriate orchestrator based on mode and query complexity.
        """
        try:
            # For auto mode, determine if ReAct should be used based on query complexity
            if self.active_mode == "auto" and REACT_AVAILABLE:
                if self._should_use_react(user_input, context):
                    if not self.react_orchestrator:
                        self.react_orchestrator = ReActOrchestrator()
                    return await self.react_orchestrator.process_query(user_input, context)
            
            # Use the active orchestrator
            if self.active_mode == "react" and self.react_orchestrator:
                return await self.react_orchestrator.process_query(user_input, context)
            elif self.active_mode == "temporal" and self.temporal_orchestrator:
                return await self.temporal_orchestrator.process_query(user_input, context, workflow_type)
            elif self.active_mode == "enhanced":
                return await self.enhanced_orchestrator.process_query(user_input, context)
            elif self.active_mode == "legacy":
                return await self.legacy_orchestrator.process_query(user_input, context)
            else:
                # Fallback to enhanced
                return await self.enhanced_orchestrator.process_query(user_input, context)
                
        except Exception as e:
            log.error(f"Orchestrator processing failed: {e}", exc_info=True)
            return AgentResponse(
                content="I'm sorry, I encountered an error processing your request. Please try again.",
                confidence=0.0
            )
    
    def _should_use_react(self, user_input: str, context: ConversationContext) -> bool:
        """
        Determine if ReAct orchestration is appropriate for this query.
        """
        # Use ReAct for complex, multi-step queries
        complexity_indicators = [
            "compare", "which is better", "analyze", "evaluate",
            "find the best", "recommend based on", "consider",
            "what's the difference", "pros and cons", "trade-offs"
        ]
        
        query_lower = user_input.lower()
        has_complexity = any(indicator in query_lower for indicator in complexity_indicators)
        
        # Use ReAct if query is complex or if we have rich context
        return has_complexity or (context.user_profile and len(context.history or []) > 2)
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for the orchestrator."""
        health_status = {
            "status": "healthy",
            "active_mode": self.active_mode,
            "available_modes": {
                "react": REACT_AVAILABLE,
                "temporal": TEMPORAL_AVAILABLE,
                "enhanced": True,
                "legacy": True
            }
        }
        
        # Add orchestrator-specific health info
        if self.active_mode == "react" and self.react_orchestrator:
            react_health = await self.react_orchestrator.health_check()
            health_status["react"] = react_health
        elif self.active_mode == "temporal" and self.temporal_orchestrator:
            temporal_health = await self.temporal_orchestrator.health_check()
            health_status["temporal"] = temporal_health
        elif self.active_mode == "enhanced":
            enhanced_health = await self.enhanced_orchestrator.health_check()
            health_status["enhanced"] = enhanced_health
        
        return health_status
    
    # Temporal-specific methods (only available in temporal mode)
    async def start_shopping_journey(
        self, 
        user_input: str, 
        context: ConversationContext
    ) -> AgentResponse:
        """Start a shopping journey workflow (Temporal mode only)."""
        if self.active_mode == "temporal" and self.temporal_orchestrator:
            return await self.temporal_orchestrator.process_query(
                user_input, context, workflow_type="journey"
            )
        else:
            return AgentResponse(
                content="Shopping journey workflows are only available in Temporal mode.",
                agent_id="system_message",
                confidence=0.8,
                data={"feature": "shopping_journey", "mode": self.active_mode}
            )
    
    async def start_price_monitoring(
        self, 
        user_input: str, 
        context: ConversationContext
    ) -> AgentResponse:
        """Start price monitoring workflow (Temporal mode only)."""
        if self.active_mode == "temporal" and self.temporal_orchestrator:
            return await self.temporal_orchestrator.process_query(
                user_input, context, workflow_type="monitor"
            )
        else:
            return AgentResponse(
                content="Price monitoring workflows are only available in Temporal mode.",
                agent_id="system_message",
                confidence=0.8,
                data={"feature": "price_monitoring", "mode": self.active_mode}
            )
    
    async def get_active_workflows(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active workflows (Temporal mode only)."""
        if self.active_mode == "temporal" and self.temporal_orchestrator:
            return await self.temporal_orchestrator.list_active_workflows(user_id)
        else:
            return []
    
    async def send_workflow_signal(
        self, 
        workflow_id: str, 
        signal_data: Dict[str, Any]
    ) -> bool:
        """Send signal to workflow (Temporal mode only)."""
        if self.active_mode == "temporal" and self.temporal_orchestrator:
            # Convert signal_data to UserDecisionSignal if needed
            from workflow_models import UserDecisionSignal
            
            if "decision_type" in signal_data:
                decision = UserDecisionSignal(**signal_data)
                return await self.temporal_orchestrator.send_user_decision(workflow_id, decision)
        
        return False
    
    async def cleanup(self):
        """Cleanup all orchestrator resources."""
        if self.temporal_orchestrator:
            await self.temporal_orchestrator.cleanup()
        
        log.info("Orchestrator cleanup completed")

# Legacy Orchestrator (existing implementation)
class LegacyOrchestrator:
    """Original tool-based orchestrator for backward compatibility."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.tools = self._load_tools()
    
    def _load_tools(self) -> Dict[str, Callable]:
        """Load all available tools."""
        from .tools import (
            sg_list_candidates, sg_price_drop, sg_promotions,
            sg_variants, sg_criteria, sg_category,
        )
        return {
            "sg_list_candidates": sg_list_candidates.run,
            "sg_price_drop": sg_price_drop.run,
            "sg_promotions": sg_promotions.run,
            "sg_variants": sg_variants.run,
            "sg_criteria": sg_criteria.run,
            "sg_category": sg_category.run,
        }
    
    def _tool_meta(self) -> List[Dict]:
        """Get tool metadata for OpenAI function calling."""
        from .tools import (
            sg_list_candidates, sg_price_drop, sg_promotions,
            sg_variants, sg_criteria, sg_category,
        )
        return [
            {"schema": sg_list_candidates.schema},
            {"schema": sg_price_drop.schema},
            {"schema": sg_promotions.schema},
            {"schema": sg_variants.schema},
            {"schema": sg_criteria.schema},
            {"schema": sg_category.schema},
        ]
    
    async def _safe(self, name: str, args: dict) -> Dict[str, Any]:
        """Safely execute a tool."""
        try:
            if name in self.tools:
                result = await asyncio.wait_for(
                    self.tools[name](**args), 
                    timeout=settings.default_timeout_s
                )
                return {"ok": True, "result": result}
            else:
                return {"ok": False, "error": f"Unknown tool: {name}"}
        except asyncio.TimeoutError:
            return {"ok": False, "error": "Tool execution timed out"}
        except Exception as e:
            log.error(f"Tool {name} failed: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}
    
    async def process_query(self, user_input: str, ctx: ConversationContext) -> AgentResponse:
        """Process query using legacy tool-based approach."""
        msgs = [
            {"role": "system",
             "content": (
               "You are Product.ai. Use tools to fulfill shopping queries. "
               "Call at most 6 tools. After each tool call you MUST think step."
             )},
            {"role": "user", "content": user_input},
        ]
        history: List[str] = []
        
        for step in range(6):
            try:
                llm = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=msgs,
                    tools=[{"type":"function","function":t["schema"]}
                           for t in self._tool_meta()],
                    timeout=settings.default_timeout_s,
                )
                
                if llm.choices[0].message.tool_calls:
                    # Add the assistant's message with tool calls first
                    msgs.append(llm.choices[0].message.model_dump())
                    
                    # Process each tool call and add individual responses
                    for call in llm.choices[0].message.tool_calls:
                        name = call.function.name
                        args = json.loads(call.function.arguments or "{}")
                        
                        # Execute tool with fallback error handling
                        try:
                            out = await self._safe(name, args)
                        except Exception as e:
                            log.error(f"Tool {name} failed: {e}")
                            out = {"ok": False, "error": f"Tool {name} failed: {str(e)}"}
                        
                        history.append(name)
                        
                        # Add tool response for this specific call
                        msgs.append({
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": json.dumps(out)
                        })
                    
                    # Add thinking step after all tool responses
                    msgs.append({"role": "system", "content": THINK_STEP})
                else:
                    return AgentResponse(
                        content=llm.choices[0].message.content,
                        tool_calls=history
                    )
                    
            except Exception as e:
                log.error(f"Processing step {step} failed: {e}")
                break
        
        return AgentResponse(
            content="Sorry, I couldn't process your request completely.",
            tool_calls=history
        )
    
    def handle_black_friday_surge(self, scale_factor: int = 50):
        """Handle traffic surge (fallback does nothing special)."""
        log.info(f"Fallback orchestrator handling surge factor {scale_factor}")

class MockStateManager:
    """Mock state manager when Redis is not available."""
    
    def __init__(self):
        self._cache = {}
        self._conversations = {}
    
    async def health_check(self) -> bool:
        return True
    
    async def append_to_conversation(self, session_id: str, message: dict) -> bool:
        if session_id not in self._conversations:
            self._conversations[session_id] = []
        self._conversations[session_id].append(message)
        return True
    
    async def get_conversation_history(self, session_id: str, limit: int = 50) -> List[dict]:
        return self._conversations.get(session_id, [])[:limit]
    
    async def close(self):
        pass

 