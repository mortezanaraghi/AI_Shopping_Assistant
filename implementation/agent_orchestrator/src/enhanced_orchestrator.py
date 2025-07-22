"""
Enhanced Orchestrator with Agent Architecture Integration
Provides both the new multi-agent capabilities and backwards compatibility with existing tools.
"""
from __future__ import annotations
import asyncio
import json
import time
from typing import Dict, Callable, Awaitable, Any, List, Optional
from openai import AsyncOpenAI
from opentelemetry import trace
from .config import get_settings
from .utils.logging import init_logger
from .models import (
    ConversationContext, AgentResponse, UserQuery, UserProfile,
    SharedConversationContext, AgentCapability
)
from .state_manager import DistributedStateManager
from .agent_framework import BaseAgent, AgentRegistry, AgentCoordinator, agent_registry
from .tools import (
    sg_list_candidates, sg_price_drop, sg_promotions,
    sg_variants, sg_criteria, sg_category,
)
from datetime import datetime

# Import codegen tools with error handling for missing implementations
try:
    from tools.codegen_fast import run as codegen_fast
    from tools.codegen_slow import run as codegen_slow
    CODEGEN_AVAILABLE = True
except ImportError:
    codegen_fast = None
    codegen_slow = None
    CODEGEN_AVAILABLE = False

settings = get_settings()
log = init_logger(settings.log_level)
tracer = trace.get_tracer("product_ai.orchestrator")
client = AsyncOpenAI(api_key=settings.openai_api_key)

# Legacy tool mapping for backwards compatibility
LEGACY_TOOLS: Dict[str, Callable[..., Awaitable[Any]]] = {
    "sg_list_candidates": sg_list_candidates.run,
    "sg_price_drop": sg_price_drop.run,
    "sg_promotions": sg_promotions.run,
    "sg_variants": sg_variants.run,
    "sg_criteria": sg_criteria.run,
    "sg_category": sg_category.run,
}

if CODEGEN_AVAILABLE:
    LEGACY_TOOLS["codegen_fast"] = codegen_fast
    LEGACY_TOOLS["codegen_slow"] = codegen_slow

THINK_STEP = (
    "Think step: Restate the question; decide if the previous tool output "
    "completes the answer. If so, reply. Otherwise choose another tool."
)

class ProductDiscoveryAgent(BaseAgent):
    """Agent specialized in product search and discovery."""
    
    def __init__(self):
        super().__init__(
            agent_id="product_discovery",
            capabilities={AgentCapability.SEARCH, AgentCapability.FILTERING, AgentCapability.CATEGORIZATION}
        )
        # Initialize personalization engine with graceful fallback
        try:
            from personalization import PersonalizationEngine
            self.personalization_engine = PersonalizationEngine()
        except ImportError:
            log.warning("PersonalizationEngine not available, using basic ranking")
            self.personalization_engine = None
    
    async def can_handle(self, query: UserQuery, context: ConversationContext) -> float:
        """Evaluate if this agent can handle the query."""
        search_indicators = ["find", "looking for", "need", "want", "search", "show me", "recommend"]
        query_lower = query.text.lower()
        
        score = 0.0
        for indicator in search_indicators:
            if indicator in query_lower:
                score += 0.2
        
        # Higher confidence for product-related queries
        product_indicators = ["laptop", "phone", "camera", "headphones", "monitor", "gaming", "computer"]
        for indicator in product_indicators:
            if indicator in query_lower:
                score += 0.3
        
        # Boost score if we have conversation context (follow-up queries)
        if context.history and len(context.history) > 0:
            score += 0.1
        
        return min(score, 1.0)
    
    def _extract_search_context(self, history: List[Dict]) -> 'SearchContext':
        """Extract search context from conversation history."""
        from models import SearchContext
        
        context = SearchContext()
        
        # Known brands for detection
        known_brands = ["apple", "samsung", "sony", "dell", "hp", "lenovo", "asus", "acer", "microsoft"]
        
        for msg in history[-10:]:  # Last 10 messages
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                context.previous_queries.append(content)
                
                # Extract price mentions
                if any(word in content for word in ["price", "cost", "budget", "$", "cheap", "expensive"]):
                    context.price_discussions.append(content)
                
                # Extract brand mentions  
                for brand in known_brands:
                    if brand in content and brand not in context.mentioned_brands:
                        context.mentioned_brands.append(brand)
                
                # Extract category focus
                if any(word in content for word in ["laptop", "computer"]):
                    context.category_focus = "computers"
                elif any(word in content for word in ["phone", "mobile"]):
                    context.category_focus = "phones"
                elif any(word in content for word in ["gaming", "game"]):
                    context.category_focus = "gaming"
            
            elif msg.get("role") == "assistant":
                # Extract product IDs from previous responses for recently viewed
                data = msg.get("data", {})
                if "products" in data:
                    for product in data["products"][:3]:  # Last 3 products
                        if isinstance(product, dict) and "id" in product:
                            context.recently_viewed.append(product["id"])
        
        return context
    
    def _infer_price_range(self, context: ConversationContext) -> tuple[Optional[float], Optional[float]]:
        """Infer price range from user profile and conversation."""
        min_price, max_price = None, None
        
        # Check user profile first
        if context.user_profile:
            profile_range = context.user_profile.get_preferred_price_range()
            if profile_range != (None, None):
                return profile_range
        
        # Look for price mentions in conversation
        for msg in context.history[-5:]:  # Last 5 messages
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                
                # Simple price extraction
                if "under $" in content or "less than $" in content:
                    try:
                        import re
                        price_match = re.search(r'\$(\d+)', content)
                        if price_match:
                            max_price = float(price_match.group(1))
                    except:
                        pass
                elif "around $" in content or "about $" in content:
                    try:
                        import re
                        price_match = re.search(r'\$(\d+)', content)
                        if price_match:
                            center_price = float(price_match.group(1))
                            min_price = center_price * 0.8
                            max_price = center_price * 1.2
                    except:
                        pass
        
        return min_price, max_price

    async def execute(self, query: UserQuery, context: ConversationContext) -> AgentResponse:
        """Execute product discovery with personalization."""
        try:
            # STEP 1: Extract search context from conversation history
            search_context = self._extract_search_context(context.history)
            
            # STEP 2: Use the existing sg_list_candidates tool for base search
            products = await sg_list_candidates.run(query.text)
            
            if not products:
                return AgentResponse(
                    content=f"I couldn't find any products matching '{query.text}'. Could you try a different search term or be more specific?",
                    agent_id=self.agent_id,
                    confidence=0.3
                )
            
            # STEP 3: Apply personalization if user profile exists
            if context.user_profile and self.personalization_engine and hasattr(self.personalization_engine, 'rank'):
                try:
                    # Convert to ProductRecommendation objects for personalization
                    from models import ProductRecommendation
                    recommendations = []
                    for p in products[:10]:  # Limit for performance
                        rec = ProductRecommendation(
                            id=p.get('id', 0),
                            name=p.get('name', ''),
                            price_cents=p.get('price_cents', 0),
                            score=0.5,  # Base score
                            final_price_cents=p.get('price_cents', 0),
                            merchant_id=p.get('merchant_id', 1),
                            category_id=p.get('category_id', 1),
                            specs=p.get('specs', {}),
                            brand=p.get('brand'),
                            in_stock=p.get('in_stock', True)
                        )
                        recommendations.append(rec)
                    
                    # Apply personalization ranking
                    personalized = await self.personalization_engine.rank(
                        context.user_profile, recommendations
                    )
                    
                    # Convert back to product format
                    products = [p.model_dump() for p in personalized]
                    
                except Exception as e:
                    log.warning(f"Personalization failed, using base results: {e}")
            
            # STEP 4: Filter based on price range if available
            min_price, max_price = self._infer_price_range(context)
            if min_price is not None or max_price is not None:
                filtered_products = []
                for p in products:
                    price_dollars = p.get('price_cents', 0) / 100
                    if min_price and price_dollars < min_price:
                        continue
                    if max_price and price_dollars > max_price:
                        continue
                    filtered_products.append(p)
                
                if filtered_products:
                    products = filtered_products
                    log.info(f"Filtered products by price range: ${min_price}-${max_price}")
            
            # STEP 5: Generate context-aware response
            product_names = [p.get('name', 'Unknown') for p in products[:5]]
            
            # Personalized response based on context
            if search_context.previous_queries:
                content = f"Based on our previous conversation, I found these {query.text} options:\n\n"
            elif context.user_profile and context.user_profile.recency > 0:
                content = f"Welcome back! Here are some {query.text} recommendations for you:\n\n"
            else:
                content = f"I found several {query.text} options:\n\n"
            
            for i, name in enumerate(product_names, 1):
                content += f"{i}. {name}\n"
            
            # Add personalized context
            if context.user_profile:
                if context.user_profile.brand_preferences:
                    preferred_brands = [b for b in context.user_profile.brand_preferences if any(b.lower() in p.get('name', '').lower() for p in products[:5])]
                    if preferred_brands:
                        content += f"\n💡 I noticed some options from your preferred brands: {', '.join(preferred_brands)}"
                
                if context.user_profile.is_price_sensitive:
                    content += "\n💰 I've prioritized budget-friendly options based on your preferences."
                elif context.user_profile.is_quality_focused:
                    content += "\n⭐ I've prioritized high-quality options based on your preferences."
            
            content += "\n\nWould you like more details about any of these products, or would you like me to refine the search?"
            
            # STEP 6: Record interaction for learning
            if context.user_id and context.user_profile:
                context.user_profile.record_interaction(
                    "product_discovery", 
                    query=query.text, 
                    session_id=context.session_id,
                    confidence=0.9
                )
                
                # Update category expertise
                if search_context.category_focus:
                    context.user_profile.update_category_expertise(
                        search_context.category_focus, "search"
                    )
            
            return AgentResponse(
                content=content,
                agent_id=self.agent_id,
                confidence=0.9,
                data={
                    "products": products[:5],
                    "personalized": bool(context.user_profile),
                    "search_context": search_context.model_dump() if search_context else None,
                    "price_filtered": bool(min_price or max_price)
                },
                tool_calls=["sg_list_candidates"]
            )
                
        except Exception as e:
            log.error(f"Product discovery failed: {e}")
            return AgentResponse(
                content="I encountered an error while searching for products. Please try again.",
                agent_id=self.agent_id,
                confidence=0.0
            )

class PriceAnalysisAgent(BaseAgent):
    """Agent specialized in price analysis and deal finding."""
    
    def __init__(self):
        super().__init__(
            agent_id="price_analysis",
            capabilities={AgentCapability.ANALYSIS, AgentCapability.COMPARISON}
        )
    
    async def can_handle(self, query: UserQuery, context: ConversationContext) -> float:
        """Evaluate if this agent can handle the query."""
        price_indicators = ["price", "cost", "deal", "discount", "cheap", "expensive", "budget", "save", "compare prices"]
        query_lower = query.text.lower()
        
        score = 0.0
        for indicator in price_indicators:
            if indicator in query_lower:
                score += 0.3
        
        # Check for specific product mentions in combination with price queries
        if any(word in query_lower for word in ["laptop", "phone", "monitor", "headphones"]):
            if any(word in query_lower for word in ["price", "cost", "deal"]):
                score += 0.4
        
        # Boost score if user has price sensitivity in profile
        if context.user_profile and context.user_profile.is_price_sensitive:
            score += 0.2
        
        # Check conversation history for price-related context
        if context.history:
            recent_messages = context.history[-3:]  # Last 3 messages
            for msg in recent_messages:
                if msg.get("role") == "assistant" and "products" in msg.get("data", {}):
                    score += 0.3  # Price analysis after product discovery
                    break
        
        return min(score, 1.0)
    
    def _extract_product_context(self, context: ConversationContext) -> List[Dict]:
        """Extract recently mentioned products from conversation."""
        products = []
        
        # Look for products in recent assistant responses
        for msg in context.history[-5:]:  # Last 5 messages
            if msg.get("role") == "assistant":
                data = msg.get("data", {})
                if "products" in data:
                    products.extend(data["products"])
        
        return products[:5]  # Limit to 5 most recent products

    async def execute(self, query: UserQuery, context: ConversationContext) -> AgentResponse:
        """Execute price analysis with personalization."""
        try:
            # STEP 1: Extract product context from conversation
            recent_products = self._extract_product_context(context)
            
            # STEP 2: Determine analysis approach
            if recent_products:
                # Analyze recently discussed products
                product_ids = [p.get('id') for p in recent_products if p.get('id')]
                
                if not product_ids:
                    return AgentResponse(
                        content="I'd love to help with price analysis, but I need specific products to analyze. Could you search for some products first?",
                        agent_id=self.agent_id,
                        confidence=0.6
                    )
                
                # Use price analysis tools
                price_analyses = []
                product_names = []
                
                for product_id in product_ids[:3]:  # Analyze top 3 products
                    try:
                        # Get price drop analysis
                        price_drop = await sg_price_drop.run(product_id)
                        
                        # Find product name from recent products
                        product_name = next(
                            (p.get('name', f'Product {product_id}') 
                             for p in recent_products if p.get('id') == product_id), 
                            f'Product {product_id}'
                        )
                        product_names.append(product_name)
                        
                        if price_drop and price_drop.get('ok'):
                            drop_data = price_drop.get('result', {})
                            price_analyses.append({
                                'product_id': product_id,
                                'product_name': product_name,
                                'price_drop': drop_data
                            })
                        
                    except Exception as e:
                        log.warning(f"Price analysis failed for product {product_id}: {e}")
                
                if not price_analyses:
                    return AgentResponse(
                        content="I couldn't retrieve price analysis for the recent products. The pricing service might be temporarily unavailable.",
                        agent_id=self.agent_id,
                        confidence=0.3
                    )
                
                # STEP 3: Generate personalized analysis
                content = self._generate_price_analysis_response(
                    price_analyses, context.user_profile, query.text
                )
                
                # STEP 4: Record interaction for learning
                if context.user_id and context.user_profile:
                    context.user_profile.record_interaction(
                        "price_analysis", 
                        query=query.text, 
                        session_id=context.session_id,
                        confidence=0.8
                    )
                    
                    # Update price sensitivity based on query intent
                    if any(word in query.text.lower() for word in ["cheap", "budget", "save", "deal"]):
                        # User is showing price sensitivity
                        current_sensitivity = context.user_profile.price_sensitivity
                        context.user_profile.price_sensitivity = min(1.0, current_sensitivity + 0.05)
                
                return AgentResponse(
                    content=content,
                    agent_id=self.agent_id,
                    confidence=0.8,
                    data={
                        "price_analyses": price_analyses,
                        "analyzed_products": product_names,
                        "personalized": bool(context.user_profile)
                    },
                    tool_calls=["sg_price_drop"]
                )
            
            else:
                # No recent products - provide general price guidance
                content = "I'd be happy to help with price analysis! "
                
                if context.user_profile and context.user_profile.is_price_sensitive:
                    content += "I can see you're budget-conscious, so I'll focus on finding the best deals. "
                elif context.user_profile and context.user_profile.is_quality_focused:
                    content += "I can see you prioritize quality, so I'll help you find the best value for premium products. "
                
                content += "Please search for some products first, and then I can analyze their prices, deals, and help you find the best value."
                
                return AgentResponse(
                    content=content,
                    agent_id=self.agent_id,
                    confidence=0.7,
                    data={"guidance": True, "personalized": bool(context.user_profile)}
                )
                
        except Exception as e:
            log.error(f"Price analysis failed: {e}")
            return AgentResponse(
                content="I encountered an error while analyzing prices. Please try again.",
                agent_id=self.agent_id,
                confidence=0.0
            )
    
    def _generate_price_analysis_response(
        self, 
        price_analyses: List[Dict], 
        user_profile: Optional['UserProfile'], 
        original_query: str
    ) -> str:
        """Generate personalized price analysis response."""
        content = "Here's the price analysis for the products we've been discussing:\n\n"
        
        best_deal = None
        best_deal_score = 0
        
        for analysis in price_analyses:
            name = analysis['product_name']
            drop_data = analysis['price_drop']
            
            percent_drop = drop_data.get('percent_drop_7d', 0) * 100
            attractiveness = drop_data.get('attractiveness', 0)
            days_since = drop_data.get('days_since_drop', 0)
            
            content += f"📊 **{name}**\n"
            
            if percent_drop > 0:
                content += f"   💰 Price dropped {percent_drop:.1f}% in the last 7 days\n"
                if days_since:
                    content += f"   📅 Drop occurred {days_since} days ago\n"
            else:
                content += f"   📈 No recent price drops\n"
            
            content += f"   ⭐ Deal attractiveness: {attractiveness}/10\n"
            
            # Track best deal
            deal_score = percent_drop + (attractiveness * 2)  # Weight attractiveness more
            if deal_score > best_deal_score:
                best_deal_score = deal_score
                best_deal = name
            
            content += "\n"
        
        # Add personalized recommendations
        if user_profile:
            if user_profile.is_price_sensitive and best_deal:
                content += f"💡 **Recommendation for you**: Based on your preference for value, I'd suggest the **{best_deal}** as it offers the best deal right now.\n\n"
            elif user_profile.is_quality_focused:
                content += f"💡 **Recommendation for you**: Since you prioritize quality, I'd suggest focusing on the product with the highest attractiveness score rather than just the biggest discount.\n\n"
            
            # Brand preferences
            if user_profile.brand_preferences:
                preferred_products = []
                for analysis in price_analyses:
                    name = analysis['product_name'].lower()
                    for brand in user_profile.brand_preferences:
                        if brand.lower() in name:
                            preferred_products.append(analysis['product_name'])
                            break
                
                if preferred_products:
                    content += f"🎯 **Your preferred brands**: I found {', '.join(preferred_products)} from brands you've shown interest in before.\n\n"
        
        # General advice based on query intent
        if any(word in original_query.lower() for word in ["deal", "discount", "cheap"]):
            content += "🔍 **Deal hunting tip**: I recommend checking back in a few days to see if any prices drop further, or setting up price monitoring if available."
        elif any(word in original_query.lower() for word in ["compare", "vs", "difference"]):
            content += "⚖️ **Comparison tip**: Consider not just the price, but also the attractiveness score which factors in overall value and market conditions."
        
        return content

class EnhancedOrchestrator:
    """
    Enhanced orchestrator that supports both agent-based and legacy tool-based execution.
    """
    
    def __init__(self, state_manager: Optional[DistributedStateManager] = None):
        # Initialize state management
        self.state_manager = state_manager or DistributedStateManager()
        
        # Initialize agent system
        self.agent_coordinator = AgentCoordinator(agent_registry, self.state_manager)
        
        # Register core agents
        self._register_core_agents()
        
        # Legacy tool support
        self.legacy_tools = LEGACY_TOOLS
        self._fail = 0
    
    def _register_core_agents(self):
        """Register the core agents in the system."""
        # Register product discovery agent
        product_agent = ProductDiscoveryAgent()
        agent_registry.register_agent(product_agent)
        
        # Register price analysis agent
        price_agent = PriceAnalysisAgent()
        agent_registry.register_agent(price_agent)
        
        log.info("Core agents registered successfully")
    
    async def process_query(self, user_input: str, ctx: ConversationContext) -> AgentResponse:
        """
        Process query using the enhanced agent architecture with fallback to legacy tools.
        """
        try:
            # STEP 1: Load conversation history if not already loaded
            if not ctx.history and ctx.session_id:
                ctx.history = await self.state_manager.get_conversation_history(
                    ctx.session_id, limit=10  # Last 10 exchanges
                )
            
            # STEP 2: Load or create user profile if user_id exists
            if ctx.user_id and not ctx.user_profile:
                ctx.user_profile = await self.state_manager.get_user_profile(ctx.user_id)
                if not ctx.user_profile:
                    ctx.user_profile = await self.state_manager.create_user_profile(
                        ctx.user_id, user_input
                    )
            
            # STEP 3: Record user interaction (search query)
            if ctx.user_id:
                await self.state_manager.record_user_interaction(
                    ctx.user_id, "search", query=user_input, session_id=ctx.session_id
                )
            
            # Create user query object
            user_query = UserQuery(
                text=user_input,
                user_id=ctx.user_id
            )
            
            # Try agent-based processing first
            response = await self._process_with_agents(user_query, ctx)
            
            # If agents can't handle it well, fall back to legacy tool processing
            if response.confidence < 0.5:
                log.info("Agent confidence low, falling back to legacy tool processing")
                response = await self._process_with_legacy_tools(user_input, ctx)
            
            # Save conversation state
            await self._save_conversation_state(ctx.session_id, user_input, response, ctx.user_id)
            
            return response
            
        except Exception as e:
            log.error(f"Orchestrator processing failed: {e}", exc_info=True)
            return AgentResponse(
                content="I'm sorry, I encountered an error processing your request. Please try again.",
                confidence=0.0
            )
    
    async def _process_with_agents(self, query: UserQuery, context: ConversationContext) -> AgentResponse:
        """Process query using the agent architecture."""
        try:
            with tracer.start_as_current_span("orchestrator.agent_processing") as span:
                span.set_attribute("query.text", query.text)
                
                # Use agent coordinator to handle the query
                response = await self.agent_coordinator.orchestrate_multi_agent_response(query, context)
                
                span.set_attribute("response.confidence", response.confidence)
                span.set_attribute("response.agent_id", response.agent_id or "unknown")
                
                return response
                
        except Exception as e:
            log.error(f"Agent processing failed: {e}")
            return AgentResponse(
                content="Agent processing encountered an error.",
                confidence=0.0
            )
    
    async def _process_with_legacy_tools(self, user_input: str, ctx: ConversationContext) -> AgentResponse:
        """Fallback to legacy tool-based processing (original orchestrator logic)."""
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
                llm = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=msgs,
                    tools=[{"type": "function", "function": t} 
                           for t in self._get_legacy_tool_schemas()],
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
                            out = await self._safe_tool_call(name, args)
                        except Exception as e:
                            log.error(f"Tool {name} failed: {e}")
                            out = {"error": f"Tool {name} failed: {str(e)}"}
                        
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
                        tool_calls=history,
                        confidence=0.7  # Default confidence for LLM responses
                    )
                    
            except Exception as e:
                log.error(f"Legacy tool processing step {step} failed: {e}")
                break
        
        return AgentResponse(
            content="Sorry, I couldn't process your request completely.",
            tool_calls=history,
            confidence=0.3
        )
    
    def _get_legacy_tool_schemas(self) -> List[Dict]:
        """Get schemas for legacy tools."""
        schemas = []
        for name, func in self.legacy_tools.items():
            try:
                schema = func.__globals__.get("schema")
                if schema:
                    schemas.append(schema)
            except AttributeError:
                log.warning(f"Tool {name} missing schema")
        return schemas
    
    async def _safe_tool_call(self, name: str, args: dict) -> Dict[str, Any]:
        """Safely execute a legacy tool call."""
        try:
            if name in self.legacy_tools:
                return await asyncio.wait_for(
                    self.legacy_tools[name](**args), 
                    timeout=settings.default_timeout_s
                )
            else:
                return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            log.error(f"Tool {name} failed: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _save_conversation_state(self, session_id: str, user_input: str, response: AgentResponse, user_id: Optional[str] = None):
        """Save conversation interaction to state."""
        try:
            # Save user message
            user_message = {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            }
            if user_id:
                user_message["user_id"] = user_id
                
            await self.state_manager.append_to_conversation(session_id, user_message)
            
            # Save assistant response
            assistant_message = {
                "role": "assistant", 
                "content": response.content,
                "agent_id": response.agent_id,
                "confidence": response.confidence,
                "tool_calls": response.tool_calls,
                "timestamp": datetime.now().isoformat()
            }
            if user_id:
                assistant_message["user_id"] = user_id
                
            await self.state_manager.append_to_conversation(session_id, assistant_message)

            # Record user interaction for response if user_id is provided
            if user_id:
                await self.state_manager.record_user_interaction(
                    user_id, "assistant_response", 
                    session_id=session_id, 
                    confidence=response.confidence
                )
            
        except Exception as e:
            log.error(f"Failed to save conversation state: {e}")
    
    def handle_black_friday_surge(self, scale_factor: int = 50):
        """Handle traffic surge by disabling resource-intensive operations."""
        if scale_factor >= 50:
            # Remove slow tools
            if "codegen_slow" in self.legacy_tools:
                self.legacy_tools.pop("codegen_slow")
            
            # Reduce agent execution timeouts
            for agent in agent_registry.get_all_agents():
                agent.max_execution_time = min(agent.max_execution_time, 15.0)
            
            log.info(f"Surge handling activated for scale factor {scale_factor}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check system health."""
        health_status = {
            "orchestrator": "healthy",
            "agents_registered": len(agent_registry.get_all_agents()),
            "legacy_tools": len(self.legacy_tools),
            "state_manager": "unknown"
        }
        
        # Check state manager
        try:
            if await self.state_manager.health_check():
                health_status["state_manager"] = "healthy"
            else:
                health_status["state_manager"] = "unhealthy"
        except Exception:
            health_status["state_manager"] = "error"
        
        return health_status

# Backwards compatible class name
class Orchestrator(EnhancedOrchestrator):
    """Backwards compatible orchestrator class."""
    pass 