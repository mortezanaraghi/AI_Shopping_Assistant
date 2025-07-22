"""
Agent Abstraction Framework
Provides the foundation for building specialized shopping assistant agents.
"""
from __future__ import annotations
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Optional, Any, Callable
from datetime import datetime
from opentelemetry import trace
from .state_manager import DistributedStateManager
from .utils.logging import init_logger
from .models import (
    UserQuery, ConversationContext, AgentResponse, AgentInsight, 
    AgentMetrics, UserProfile, ExecutionPlan, CollaborationResult,
    AgentCapability, SharedConversationContext
)

log = init_logger()
tracer = trace.get_tracer("product_ai.agents")

class BaseAgent(ABC):
    """
    Abstract base class for all shopping assistant agents.
    Provides common functionality and enforces the agent contract.
    """
    
    def __init__(self, 
                 agent_id: str, 
                 capabilities: Set[AgentCapability],
                 confidence_threshold: float = 0.3):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.confidence_threshold = confidence_threshold
        
        # Dependencies injected during initialization
        self.state_manager: Optional[DistributedStateManager] = None
        self.metrics = AgentMetrics(agent_id=agent_id)
        
        # Agent-specific configuration
        self.max_execution_time = 30.0  # seconds
        self.requires_user_profile = False
        self.can_collaborate = True
        
    def configure(self, state_manager: DistributedStateManager):
        """Configure agent with required dependencies."""
        self.state_manager = state_manager
    
    @abstractmethod
    async def can_handle(self, query: UserQuery, context: ConversationContext) -> float:
        """
        Determine if this agent can handle the given query.
        Returns confidence score (0.0 - 1.0).
        """
        pass
    
    @abstractmethod
    async def execute(self, query: UserQuery, context: ConversationContext) -> AgentResponse:
        """Execute the agent's main functionality."""
        pass
    
    async def get_context_memory(self, session_id: str) -> Dict[str, Any]:
        """Retrieve agent-specific context for the session."""
        if not self.state_manager:
            return {}
        
        insights = await self.state_manager.get_agent_insights(session_id)
        agent_insight = insights.get(self.agent_id)
        
        return agent_insight.data if agent_insight else {}
    
    async def store_context_memory(self, session_id: str, data: Dict[str, Any]):
        """Store agent-specific context for future use."""
        if not self.state_manager:
            return
        
        insight = AgentInsight(
            agent_id=self.agent_id,
            insight_type="context_memory",
            data=data,
            confidence=1.0
        )
        
        await self.state_manager.store_agent_insight(session_id, insight)
    
    async def record_execution_metrics(self, execution_time: float, success: bool):
        """Record performance metrics for this agent."""
        self.metrics.total_executions += 1
        self.metrics.last_execution = datetime.now()
        
        # Update success rate with exponential moving average
        alpha = 0.1  # Learning rate
        new_success = 1.0 if success else 0.0
        self.metrics.success_rate = (1 - alpha) * self.metrics.success_rate + alpha * new_success
        
        # Update average latency
        self.metrics.avg_latency_ms = (1 - alpha) * self.metrics.avg_latency_ms + alpha * (execution_time * 1000)
    
    async def safe_execute(self, query: UserQuery, context: ConversationContext) -> AgentResponse:
        """Execute agent with timeout and error handling."""
        start_time = time.time()
        
        try:
            with tracer.start_as_current_span(f"agent.{self.agent_id}.execute") as span:
                span.set_attribute("agent.id", self.agent_id)
                span.set_attribute("query.text", query.text[:100])  # Truncate for logging
                
                # Execute with timeout
                response = await asyncio.wait_for(
                    self.execute(query, context),
                    timeout=self.max_execution_time
                )
                
                execution_time = time.time() - start_time
                await self.record_execution_metrics(execution_time, True)
                
                span.set_attribute("execution.success", True)
                span.set_attribute("execution.time_ms", execution_time * 1000)
                
                return response
                
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            await self.record_execution_metrics(execution_time, False)
            
            log.warning(f"Agent {self.agent_id} timed out after {execution_time:.2f}s")
            
            return AgentResponse(
                content=f"Sorry, the {self.agent_id} agent took too long to respond. Please try again.",
                agent_id=self.agent_id,
                confidence=0.0
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            await self.record_execution_metrics(execution_time, False)
            
            log.error(f"Agent {self.agent_id} execution failed: {e}", exc_info=True)
            
            return AgentResponse(
                content=f"I encountered an error while processing your request. Please try again.",
                agent_id=self.agent_id,
                confidence=0.0
            )
    
    async def collaborate_with(self, other_agents: List['BaseAgent'], shared_context: SharedConversationContext) -> Optional[CollaborationResult]:
        """Collaborate with other agents on a complex query."""
        if not self.can_collaborate:
            return None
        
        # Default implementation - can be overridden by specific agents
        collaboration_data = {
            "agent_id": self.agent_id,
            "capabilities": [cap.value for cap in self.capabilities],
            "confidence": await self.can_handle(shared_context.current_query, 
                                              ConversationContext(session_id=shared_context.session_id))
        }
        
        return CollaborationResult(
            participating_agents=[self.agent_id] + [agent.agent_id for agent in other_agents],
            shared_insights={self.agent_id: collaboration_data},
            success=True
        )

class AgentRegistry:
    """
    Central registry for managing and discovering agents.
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.capability_index: Dict[AgentCapability, List[str]] = {}
        self.agent_dependencies: Dict[str, Set[str]] = {}
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent in the system."""
        self.agents[agent.agent_id] = agent
        
        # Index by capabilities
        for capability in agent.capabilities:
            if capability not in self.capability_index:
                self.capability_index[capability] = []
            self.capability_index[capability].append(agent.agent_id)
        
        log.info(f"Registered agent: {agent.agent_id} with capabilities: {agent.capabilities}")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def find_agents_by_capability(self, capabilities: List[AgentCapability]) -> List[BaseAgent]:
        """Find agents that have the specified capabilities."""
        matching_agents = []
        
        for capability in capabilities:
            agent_ids = self.capability_index.get(capability, [])
            for agent_id in agent_ids:
                agent = self.agents.get(agent_id)
                if agent and agent not in matching_agents:
                    matching_agents.append(agent)
        
        return matching_agents
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Get all registered agents."""
        return list(self.agents.values())
    
    async def evaluate_agents_for_query(self, query: UserQuery, context: ConversationContext) -> List[tuple[BaseAgent, float]]:
        """Evaluate all agents for their ability to handle a query."""
        agent_scores = []
        
        for agent in self.agents.values():
            try:
                confidence = await agent.can_handle(query, context)
                if confidence >= agent.confidence_threshold:
                    agent_scores.append((agent, confidence))
            except Exception as e:
                log.warning(f"Error evaluating agent {agent.agent_id}: {e}")
        
        # Sort by confidence score descending
        agent_scores.sort(key=lambda x: x[1], reverse=True)
        return agent_scores

class AgentCoordinator:
    """
    Coordinates agent execution, manages dependencies, and handles collaboration.
    """
    
    def __init__(self, registry: AgentRegistry, state_manager: DistributedStateManager):
        self.registry = registry
        self.state_manager = state_manager
        
        # Configure all agents with state manager
        for agent in registry.get_all_agents():
            agent.configure(state_manager)
    
    async def select_agents_for_query(self, query: UserQuery, context: ConversationContext, max_agents: int = 3) -> List[BaseAgent]:
        """Select the best agents to handle a query."""
        # Get agent evaluations
        agent_scores = await self.registry.evaluate_agents_for_query(query, context)
        
        # Select top agents up to max_agents
        selected_agents = [agent for agent, score in agent_scores[:max_agents]]
        
        log.info(f"Selected agents for query: {[agent.agent_id for agent in selected_agents]}")
        return selected_agents
    
    async def execute_agents_parallel(self, agents: List[BaseAgent], query: UserQuery, context: ConversationContext) -> List[AgentResponse]:
        """Execute multiple agents in parallel."""
        if not agents:
            return []
        
        # Create execution tasks
        tasks = []
        for agent in agents:
            task = asyncio.create_task(
                agent.safe_execute(query, context),
                name=f"execute_{agent.agent_id}"
            )
            tasks.append(task)
        
        # Wait for all agents to complete
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid responses
        valid_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                log.error(f"Agent {agents[i].agent_id} failed with exception: {response}")
                # Create error response
                error_response = AgentResponse(
                    content="I encountered an error processing your request.",
                    agent_id=agents[i].agent_id,
                    confidence=0.0
                )
                valid_responses.append(error_response)
            else:
                valid_responses.append(response)
        
        return valid_responses
    
    async def execute_agents_sequential(self, agents: List[BaseAgent], query: UserQuery, context: ConversationContext) -> List[AgentResponse]:
        """Execute agents sequentially (when dependencies exist)."""
        responses = []
        
        for agent in agents:
            response = await agent.safe_execute(query, context)
            responses.append(response)
            
            # Update context with agent insights for next agent
            if response.data:
                await self.state_manager.store_agent_insight(
                    context.session_id,
                    AgentInsight(
                        agent_id=agent.agent_id,
                        insight_type="execution_result",
                        data=response.data,
                        confidence=response.confidence
                    )
                )
        
        return responses
    
    async def create_execution_plan(self, agents: List[BaseAgent], query: UserQuery) -> ExecutionPlan:
        """Create an execution plan for the selected agents."""
        # For now, default to parallel execution
        # In a more sophisticated implementation, this would analyze dependencies
        
        plan = ExecutionPlan(
            phases=[
                {
                    "phase": 1,
                    "agents": [agent.agent_id for agent in agents],
                    "execution_type": "parallel",
                    "estimated_duration_ms": 3000  # Rough estimate
                }
            ],
            estimated_duration_ms=3000,
            can_parallelize=True
        )
        
        return plan
    
    async def orchestrate_multi_agent_response(self, query: UserQuery, context: ConversationContext) -> AgentResponse:
        """Orchestrate multiple agents to provide a comprehensive response."""
        # Select appropriate agents
        selected_agents = await self.select_agents_for_query(query, context)
        
        if not selected_agents:
            return AgentResponse(
                content="I'm not sure how to help with that request. Could you please rephrase or provide more details?",
                confidence=0.0
            )
        
        # Create execution plan
        plan = await self.create_execution_plan(selected_agents, query)
        
        # Execute agents based on plan
        if plan.can_parallelize:
            responses = await self.execute_agents_parallel(selected_agents, query, context)
        else:
            responses = await self.execute_agents_sequential(selected_agents, query, context)
        
        # Synthesize responses
        return await self.synthesize_agent_responses(responses, query, context)
    
    async def synthesize_agent_responses(self, responses: List[AgentResponse], query: UserQuery, context: ConversationContext) -> AgentResponse:
        """Combine multiple agent responses into a coherent final response."""
        if not responses:
            return AgentResponse(content="No agents were able to process your request.", confidence=0.0)
        
        if len(responses) == 1:
            return responses[0]
        
        # For multiple responses, combine them intelligently
        # This is a simplified version - in production, this would be more sophisticated
        
        # Find the highest confidence response as the primary
        primary_response = max(responses, key=lambda r: r.confidence)
        
        # Combine content from all responses
        combined_content = primary_response.content
        
        # Add insights from other agents if they have high confidence
        for response in responses:
            if response != primary_response and response.confidence > 0.7:
                combined_content += f"\n\nAdditionally, {response.content}"
        
        # Combine tool calls and data
        all_tool_calls = []
        combined_data = {}
        
        for response in responses:
            all_tool_calls.extend(response.tool_calls)
            combined_data.update(response.data)
        
        return AgentResponse(
            content=combined_content,
            tool_calls=all_tool_calls,
            agent_id="multi_agent_coordinator",
            confidence=primary_response.confidence,
            data=combined_data
        )

# Global registry instance
agent_registry = AgentRegistry() 