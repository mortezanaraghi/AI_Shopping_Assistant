# Agent Orchestration Architecture Documentation

## Table of Contents
1. [Overview](#overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Real-Time Orchestration (ReAct)](#real-time-orchestration-react)
4. [Temporal-Based Orchestration](#temporal-based-orchestration)
5. [Enhanced Orchestration](#enhanced-orchestration)
6. [Legacy Orchestration](#legacy-orchestration)
7. [Code Walkthrough with Example](#code-walkthrough-with-example)
8. [Configuration and Settings](#configuration-and-settings)
9. [Error Handling and Resilience](#error-handling-and-resilience)

## Overview

The Agent Orchestration system is a sophisticated multi-layered architecture that provides intelligent shopping assistance through multiple orchestration strategies. The system dynamically selects the most appropriate orchestration method based on query complexity, available resources, and user context.

### Key Features
- **Multi-Modal Orchestration**: Supports ReAct, Temporal, Enhanced, and Legacy modes
- **Dynamic Mode Selection**: Automatically chooses the best orchestration strategy
- **Fault Tolerance**: Graceful fallbacks between orchestration modes
- **Scalability**: Designed for high-throughput shopping queries
- **Observability**: Comprehensive logging and tracing

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Orchestrator                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │   ReAct     │ │  Temporal   │ │ Enhanced    │ │ Legacy  │ │
│  │Orchestrator │ │Orchestrator │ │Orchestrator │ │Orchestr.│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 State Manager                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │Conversation │ │ User Profile│ │ Tool History│            │
│  │  History    │ │             │ │             │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Agent Framework                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Product     │ │ Price       │ │ Deal        │            │
│  │ Discovery   │ │ Analysis    │ │ Detection   │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

## Real-Time Orchestration (ReAct)

The ReAct (Reason-Act) orchestrator implements an iterative reasoning pattern that mimics human problem-solving. It's the primary orchestrator for complex queries requiring multi-step reasoning.

### Architecture Overview

```python
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
```

### ReAct Loop Implementation

The core ReAct loop follows the pattern: **Reason → Act → Observe → Repeat**

```python
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
                    break
                
                # STEP 3: ACT (The "Action Step")
                action_result = await self._act_with_validation(reasoning_result, react_state)
                
                # STEP 4: OBSERVE (The "Learning Step")
                await self._observe(action_result, react_state)
                
                # Increment iteration
                react_state.current_iteration += 1
                
                # Check if we have a final answer
                if action_result.action_type == "final_answer":
                    break
```

### Step-by-Step Breakdown

#### 1. Reason Step (`_reason`)

```python
async def _reason(self, react_state: ReActState) -> ReasoningResult:
    """
    The "thinking" step where the LLM analyzes the current state and decides what to do next.
    """
    try:
        # Build enhanced reasoning prompt with context
        prompt = self._build_enhanced_reasoning_prompt(react_state)
        
        # Call LLM for reasoning
        response = await self.llm_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000
        )
        
        # Parse reasoning result
        content = response.choices[0].message.content
        reasoning_data = json.loads(content)
        
        return ReasoningResult(**reasoning_data)
        
    except Exception as e:
        log.error(f"Reasoning step failed: {e}")
        # Return fallback reasoning
        return ReasoningResult(
            thought="I'm having trouble processing this request",
            action_type="final_answer",
            final_response="I apologize, but I'm having trouble processing your request right now.",
            confidence=0.3
        )
```

#### 2. Act Step (`_act_with_validation`)

```python
async def _act_with_validation(self, reasoning: ReasoningResult, react_state: ReActState) -> ActionResult:
    """
    Enhanced act step with tool argument validation.
    """
    if reasoning.action_type == "use_tool":
        # Validate tool arguments before execution
        is_valid, validation_msg = self.tool_registry.validate_arguments(
            reasoning.tool_name, reasoning.tool_args
        )
        
        if not is_valid:
            return ActionResult(
                action_type="use_tool",
                content=f"Tool validation failed: {validation_msg}",
                success=False,
                tool_name=reasoning.tool_name,
                error_message=validation_msg
            )
    
    # Proceed with normal action execution
    return await self._act(reasoning, react_state)
```

#### 3. Observe Step (`_observe`)

```python
async def _observe(self, action_result: ActionResult, react_state: ReActState):
    """
    The "learning" step where we record the action result and update state.
    """
    # Record the action in tool execution history
    history_entry = {
        "iteration": react_state.current_iteration,
        "action": action_result.action_type,
        "result": action_result.content,
        "success": action_result.success,
        "execution_time_ms": action_result.execution_time_ms
    }
    
    if action_result.tool_name:
        history_entry["tool_name"] = action_result.tool_name
    
    react_state.tool_execution_history.append(history_entry)
    
    # Update accumulated insights
    if action_result.success and action_result.data:
        react_state.accumulated_insights.update(action_result.data)
```

### Enhanced Features

#### Tool Schema Registry

```python
class ToolSchemaRegistry:
    """Centralized tool schema management with validation."""
    
    def __init__(self):
        self.tool_schemas = {
            "sg_list_candidates": {
                "description": "Search for products based on query",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                },
                "examples": [
                    {"query": "gaming laptops under $1500"},
                    {"query": "4K video editing laptops"}
                ]
            },
            # ... other tools
        }
    
    def validate_arguments(self, tool_name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate tool arguments against schema."""
        if tool_name not in self.tool_schemas:
            return False, f"Unknown tool: {tool_name}"
        
        schema = self.tool_schemas[tool_name]
        required_params = schema["parameters"].get("required", [])
        
        for param in required_params:
            if param not in args:
                return False, f"Missing required parameter '{param}'"
        
        return True, "Valid"
```

#### Smart Termination Analyzer

```python
class SmartTerminationAnalyzer:
    """Analyzes ReAct state to determine optimal termination conditions."""
    
    def should_terminate(self, react_state: ReActState, reasoning_result: ReasoningResult) -> Tuple[bool, str]:
        """Determine if the ReAct loop should terminate early."""
        
        # Check max iterations
        if react_state.current_iteration >= self.max_iterations:
            return True, "Maximum iterations reached"
        
        # Check excessive clarifications
        clarification_count = self._count_clarifications(react_state)
        if clarification_count >= self.max_clarifications:
            return True, "Too many clarifications requested"
        
        # Check tool failures
        failed_tools = self._count_failed_tools(react_state)
        if failed_tools >= self.max_failures:
            return True, "Too many tool failures"
        
        # Check for high confidence with product results
        if (reasoning_result.action_type == "final_answer" and 
            reasoning_result.confidence >= 0.8 and 
            self._has_product_results(react_state)):
            return True, "Sufficient product results found with high confidence"
        
        # Check for reasonable confidence with results
        if (reasoning_result.action_type == "final_answer" and 
            reasoning_result.confidence >= 0.6 and 
            self._has_product_results(react_state)):
            return True, "Sufficient results found with reasonable confidence"
        
        # Check for repetitive patterns
        if self._is_stuck_in_loop(react_state):
            return True, "Detected repetitive tool usage pattern"
        
        return False, "Continue"
```

## Temporal-Based Orchestration

The Temporal orchestrator provides durable, fault-tolerant processing for long-running shopping workflows using Temporal.io.

### Architecture Overview

```python
class TemporalOrchestrator:
    """
    Temporal-enabled orchestrator that provides both workflow-based and traditional processing.
    """
    
    def __init__(self, temporal_address: str = "localhost:7233"):
        self.temporal_address = temporal_address
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None
        self.task_queue = "shopping-assistant"
        
        # Fallback orchestrator for backward compatibility
        self.fallback_orchestrator = EnhancedOrchestrator()
        
        # Workflow tracking
        self.active_workflows: Dict[str, WorkflowHandle] = {}
```

### Workflow Types

The Temporal orchestrator supports three main workflow types:

1. **Shopping Journey Workflow**: For complex, multi-step shopping processes
2. **Price Monitoring Workflow**: For long-running price tracking
3. **Quick Query Workflow**: For simple, fast queries

```python
async def process_query(
    self, 
    user_input: str, 
    context: ConversationContext,
    workflow_type: str = "auto"
) -> AgentResponse:
    """
    Process user query using appropriate workflow or fallback processing.
    """
    
    # Determine workflow type if auto
    if workflow_type == "auto":
        workflow_type = self._determine_workflow_type(user_input, context)
    
    # Route to appropriate workflow
    if workflow_type == "quick_query":
        return await self._process_quick_query(user_input, context)
    elif workflow_type == "shopping_journey":
        return await self._start_shopping_journey(user_input, context)
    elif workflow_type == "price_monitoring":
        return await self._start_price_monitoring(user_input, context)
    else:
        # Fallback to enhanced orchestrator
        return await self.fallback_orchestrator.process_query(user_input, context)
```

### Workflow Implementation Example

```python
@workflow.defn
class ShoppingJourneyWorkflow:
    """Workflow for complex shopping journeys with user interaction."""
    
    @workflow.run
    async def run(self, input_data: ShoppingJourneyInput) -> ShoppingJourneyResult:
        """Main workflow execution."""
        
        # Step 1: Initial product discovery
        discovery_result = await workflow.execute_activity(
            product_discovery_activity,
            input_data.user_query,
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        # Step 2: Enhanced analysis
        analysis_result = await workflow.execute_activity(
            enhanced_product_analysis_activity,
            discovery_result.products,
            start_to_close_timeout=timedelta(minutes=10)
        )
        
        # Step 3: Wait for user decision
        user_decision = await workflow.wait_for_signal(
            "user_decision",
            timeout=timedelta(hours=24)
        )
        
        # Step 4: Process user decision
        if user_decision.decision_type == "select_product":
            # Continue with purchase flow
            pass
        elif user_decision.decision_type == "refine_search":
            # Restart with refined criteria
            pass
        
        return ShoppingJourneyResult(
            status="completed",
            selected_products=analysis_result.top_products,
            user_feedback=user_decision
        )
```

### Activity Implementation

```python
@activity.defn
async def product_discovery_activity(user_query: str) -> ProductDiscoveryResult:
    """Activity for discovering products based on user query."""
    
    try:
        # Use enhanced orchestrator for product discovery
        orchestrator = EnhancedOrchestrator()
        context = ConversationContext(session_id=f"workflow_{uuid.uuid4()}")
        
        response = await orchestrator.process_query(user_query, context)
        
        # Extract products from response
        products = extract_products_from_response(response)
        
        return ProductDiscoveryResult(
            products=products,
            total_count=len(products),
            confidence=response.confidence
        )
        
    except Exception as e:
        activity.logger.error(f"Product discovery failed: {e}")
        raise
```

## Enhanced Orchestration

The Enhanced orchestrator provides a sophisticated agent-based approach with specialized agents for different tasks.

### Agent Framework

```python
class AgentRegistry:
    """Registry for managing specialized agents."""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._register_default_agents()
    
    def _register_default_agents(self):
        """Register default specialized agents."""
        self.register_agent("product_discovery", ProductDiscoveryAgent())
        self.register_agent("price_analysis", PriceAnalysisAgent())
        self.register_agent("deal_detection", DealDetectionAgent())
        self.register_agent("personalization", PersonalizationAgent())
        self.register_agent("criteria_ranking", CriteriaRankingAgent())
```

### Agent Implementation Example

```python
class ProductDiscoveryAgent(BaseAgent):
    """Specialized agent for product discovery tasks."""
    
    async def execute(self, query: str, context: AgentContext) -> AgentResponse:
        """Execute product discovery task."""
        
        # Analyze query intent
        intent = await self._analyze_intent(query)
        
        # Extract search criteria
        criteria = await self._extract_criteria(query, context)
        
        # Execute search using appropriate tools
        if intent.category == "laptop":
            results = await self._search_laptops(criteria)
        elif intent.category == "accessory":
            results = await self._search_accessories(criteria)
        else:
            results = await self._general_search(criteria)
        
        # Rank and filter results
        ranked_results = await self._rank_results(results, criteria)
        
        return AgentResponse(
            content=self._format_results(ranked_results),
            confidence=self._calculate_confidence(ranked_results),
            data={"products": ranked_results, "criteria": criteria}
        )
```

## Legacy Orchestration

The Legacy orchestrator provides a simple, tool-based approach for backward compatibility and fallback scenarios.

```python
class LegacyOrchestrator:
    """Legacy tool-based orchestrator for backward compatibility."""
    
    def __init__(self):
        self.tools = self._load_tools()
        self.tool_meta = self._tool_meta()
    
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
    
    async def process_query(self, user_input: str, ctx: ConversationContext) -> AgentResponse:
        """Process query using legacy tool-based approach."""
        
        # Use OpenAI function calling
        response = await self.llm_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_input}],
            functions=self.tool_meta,
            function_call="auto"
        )
        
        # Execute tool calls
        tool_calls = []
        for choice in response.choices:
            if choice.message.function_call:
                tool_name = choice.message.function_call.name
                tool_args = json.loads(choice.message.function_call.arguments)
                
                result = await self._safe(tool_name, tool_args)
                tool_calls.append(tool_name)
        
        return AgentResponse(
            content=response.choices[0].message.content,
            confidence=0.7,
            tool_calls=tool_calls
        )
```

## Code Walkthrough with Example

Let's walk through a complete example using the query: **"I need a laptop for 4K video editing under $2000"**

### 1. Main Orchestrator Entry Point

```python
# From example.py
async def demo_basic_functionality():
    orchestrator = Orchestrator()  # Auto-selects ReAct mode
    
    context = ConversationContext(session_id="demo_session_1")
    response = await orchestrator.process_query(
        "I need a laptop for 4K video editing under $2000", 
        context
    )
```

### 2. Mode Selection Logic

```python
# In orchestrator.py - _should_use_react method
def _should_use_react(self, user_input: str, context: ConversationContext) -> bool:
    """Determine if ReAct orchestration should be used."""
    
    # Complex queries that benefit from iterative reasoning
    complex_keywords = [
        "compare", "best", "recommend", "analysis", "review",
        "4K", "video editing", "gaming", "professional"
    ]
    
    # Check for complex keywords
    if any(keyword in user_input.lower() for keyword in complex_keywords):
        return True
    
    # Check for multiple requirements
    if user_input.count("and") > 0 or user_input.count(",") > 2:
        return True
    
    return False
```

### 3. ReAct Loop Execution

#### Iteration 1: Initial Reasoning

```python
# LLM receives enhanced prompt with tool schemas
prompt = """
You are a shopping assistant. Analyze the user query and decide what action to take.

USER QUERY: I need a laptop for 4K video editing under $2000

AVAILABLE TOOLS:
- sg_list_candidates: Search for products based on query
  Parameters: query: string
  Examples: {"query": "gaming laptops under $1500"}

DECISION CRITERIA:
- Use USE_TOOL when you need to search for products
- Use ASK_CLARIFICATION when you need more information
- Use FINAL_ANSWER when you have sufficient results

TERMINATION RULES:
- Max 5 iterations total
- Stop after 2 clarifications
- Stop if you have high confidence results
"""

# LLM Response:
{
    "thought": "The user needs a laptop for 4K video editing under $2000. I should search for laptops that meet these criteria.",
    "action_type": "use_tool",
    "tool_name": "sg_list_candidates",
    "tool_args": {"query": "4K video editing laptops under $2000"},
    "confidence": 0.9
}
```

#### Iteration 1: Tool Execution

```python
# Tool validation passes
is_valid, msg = tool_registry.validate_arguments(
    "sg_list_candidates", 
    {"query": "4K video editing laptops under $2000"}
)  # Returns (True, "Valid")

# Tool execution
result = await execute_tool("sg_list_candidates", {"query": "4K video editing laptops under $2000"})
# Returns: Found 8 laptops matching criteria
```

#### Iteration 1: Observation

```python
# State updated with results
react_state.tool_execution_history.append({
    "iteration": 0,
    "action": "use_tool",
    "result": "Found 8 laptops matching criteria",
    "success": True,
    "tool_name": "sg_list_candidates"
})

react_state.accumulated_insights.update({
    "products": [laptop1, laptop2, ...],
    "total_count": 8
})
```

#### Iteration 2: Refined Reasoning

```python
# LLM receives updated prompt with tool history
prompt = """
...previous content...

TOOL HISTORY:
✓ sg_list_candidates: Found 8 laptops matching criteria

CURRENT STATE: I have 8 laptops for 4K video editing under $2000. I should analyze their specifications and prices to provide recommendations.
"""

# LLM Response:
{
    "thought": "I have found 8 laptops. Now I should analyze their specifications to recommend the best options for 4K video editing.",
    "action_type": "use_tool",
    "tool_name": "sg_criteria",
    "tool_args": {"product_id": 123},
    "confidence": 0.8
}
```

#### Final Iteration: Synthesis

```python
# After multiple iterations, LLM decides to provide final answer
{
    "thought": "I have analyzed multiple laptops and found the best options for 4K video editing under $2000. I can now provide a comprehensive recommendation.",
    "action_type": "final_answer",
    "final_response": "Based on your requirements for 4K video editing under $2000, I recommend...",
    "confidence": 0.9
}

# Smart termination analyzer approves early termination
should_terminate, reason = termination_analyzer.should_terminate(react_state, reasoning_result)
# Returns (True, "Sufficient product results found with high confidence")
```

### 4. Final Response Synthesis

```python
async def _synthesize_final_response(self, react_state: ReActState) -> AgentResponse:
    """Synthesize final response from accumulated insights."""
    
    # Build comprehensive response
    response_content = f"""
Based on your query "{react_state.original_query}", I found {len(react_state.accumulated_insights.get('products', []))} products.

{format_product_recommendations(react_state.accumulated_insights)}

Tools used: {', '.join(set(h['tool_name'] for h in react_state.tool_execution_history if 'tool_name' in h))}
    """
    
    return AgentResponse(
        content=response_content,
        confidence=0.9,
        agent_id="react_orchestrator",
        tool_calls=list(set(h['tool_name'] for h in react_state.tool_execution_history if 'tool_name' in h))
    )
```

## Configuration and Settings

The system uses a centralized configuration system:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    # API Keys
    openai_api_key: str = Field(description="OpenAI API key")
    shopgraph_api_key: str = Field(description="ShopGraph API key")
    
    # ReAct Configuration
    react_max_iterations: int = Field(5, description="Maximum iterations for ReAct loop")
    react_confidence_threshold: float = Field(0.7, description="Confidence threshold for ReAct")
    
    # Temporal Configuration
    temporal_address: str = Field("localhost:7233", description="Temporal server address")
    
    # Performance Settings
    default_timeout_s: float = 8.0
    cb_failure_threshold: int = 3
    cb_recovery_s: int = 60
```

## Error Handling and Resilience

The system implements comprehensive error handling:

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenException()
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise
```

### Graceful Degradation

```python
async def process_query(self, user_input: str, context: ConversationContext) -> AgentResponse:
    """Process query with graceful degradation."""
    
    try:
        # Try ReAct first
        if self.react_orchestrator:
            return await self.react_orchestrator.process_query(user_input, context)
    except Exception as e:
        log.warning(f"ReAct failed, falling back to enhanced: {e}")
    
    try:
        # Try Enhanced
        return await self.enhanced_orchestrator.process_query(user_input, context)
    except Exception as e:
        log.warning(f"Enhanced failed, falling back to legacy: {e}")
    
    # Final fallback to Legacy
    return await self.legacy_orchestrator.process_query(user_input, context)
```

This architecture provides a robust, scalable, and intelligent shopping assistance system that can handle a wide variety of queries while maintaining high availability and performance. 
