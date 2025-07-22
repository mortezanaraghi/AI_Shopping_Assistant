"""
Temporal Activities
Defines the activities that can be executed within Temporal workflows.
"""
from __future__ import annotations
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from temporalio import activity
from opentelemetry import trace

from src.utils.logging import init_logger
from src.config import get_settings
from src.models import UserQuery, ConversationContext, AgentResponse, UserProfile, Product
from src.state_manager import DistributedStateManager
from src.agent_framework import agent_registry

from src.workflow_models import (
    ProductDiscoveryInput, ProductDiscoveryOutput,
    PriceAnalysisInput, PriceAnalysisOutput, 
    NotificationInput, NotificationOutput
)

# Import existing tools and agents
from src.tools import sg_list_candidates, sg_price_drop, sg_promotions, sg_criteria
from src.enhanced_orchestrator import ProductDiscoveryAgent, PriceAnalysisAgent
import src.shopgraph_api as sg

log = init_logger()

# ─── Product Discovery Activities ──────────────────────────────
@activity.defn(name="product_discovery")
async def product_discovery_activity(input_data: ProductDiscoveryInput) -> ProductDiscoveryOutput:
    """
    Discover products based on user query with enhanced filtering and analysis.
    """
    activity.logger.info(f"Starting product discovery for query: {input_data.query}")
    
    try:
        # Use existing product search
        products_data = await sg_list_candidates.run(input_data.query)
        
        # Convert to Product objects
        products = []
        for product_data in products_data[:input_data.max_results]:
            product = Product(**product_data)
            products.append(product)
        
        # Apply budget filtering if specified
        if input_data.budget_range:
            min_budget, max_budget = input_data.budget_range
            min_cents = int(min_budget * 100)
            max_cents = int(max_budget * 100)
            products = [p for p in products if min_cents <= p.price_cents <= max_cents]
        
        # Generate recommendations based on discovery
        recommendations = []
        if len(products) > 5:
            recommendations.append(f"Found {len(products)} options - consider narrowing your search")
        if input_data.budget_range and len(products) < 3:
            recommendations.append("Consider expanding your budget range for more options")
        
        confidence_score = min(1.0, len(products) / 10.0)  # Confidence based on results
        
        activity.logger.info(f"Product discovery completed: {len(products)} products found")
        
        return ProductDiscoveryOutput(
            products=[p.model_dump() for p in products],
            search_metadata={
                "original_query": input_data.query,
                "total_found": len(products_data),
                "filtered_count": len(products),
                "budget_applied": input_data.budget_range is not None
            },
            confidence_score=confidence_score,
            recommendations=recommendations
        )
        
    except Exception as e:
        activity.logger.error(f"Product discovery failed: {e}")
        raise

@activity.defn(name="enhanced_product_analysis")
async def enhanced_product_analysis_activity(product_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Perform detailed analysis on selected products including reviews, criteria, and variants.
    """
    activity.logger.info(f"Starting enhanced analysis for {len(product_ids)} products")
    
    analysis_results = {}
    
    for product_id in product_ids:
        try:
            # Gather comprehensive product data
            analysis_tasks = [
                sg_price_drop.run(product_id),
                sg_criteria.run(product_id),
                sg.get_variant_stats(product_id)
            ]
            
            price_drop, criteria_scores, variant_stats = await asyncio.gather(*analysis_tasks)
            
            analysis_results[product_id] = {
                "price_analysis": price_drop,
                "quality_scores": criteria_scores,
                "variant_info": variant_stats,
                "analysis_timestamp": datetime.now().isoformat(),
                "comprehensive_score": _calculate_comprehensive_score(price_drop, criteria_scores)
            }
            
        except Exception as e:
            activity.logger.warning(f"Analysis failed for product {product_id}: {e}")
            analysis_results[product_id] = {
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat()
            }
    
    activity.logger.info(f"Enhanced analysis completed for {len(analysis_results)} products")
    return analysis_results

# ─── Price Monitoring Activities ───────────────────────────────
@activity.defn(name="price_monitoring_check")
async def price_monitoring_check_activity(product_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Check current prices for monitored products.
    """
    activity.logger.info(f"Checking prices for {len(product_ids)} products")
    
    price_results = {}
    
    for product_id in product_ids:
        try:
            # Get current product data
            products = await sg.search_products(f"product_id:{product_id}")
            
            if products:
                product = products[0]
                price_drop_data = await sg_price_drop.run(product_id)
                
                price_results[product_id] = {
                    "current_price_cents": product.price_cents,
                    "current_price_dollars": product.price_cents / 100,
                    "price_drop_data": price_drop_data,
                    "timestamp": datetime.now().isoformat(),
                    "available": True
                }
            else:
                price_results[product_id] = {
                    "available": False,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            activity.logger.warning(f"Price check failed for product {product_id}: {e}")
            price_results[product_id] = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    return price_results

@activity.defn(name="price_analysis")  
async def price_analysis_activity(input_data: PriceAnalysisInput) -> PriceAnalysisOutput:
    """
    Perform comprehensive price analysis including trends, comparisons, and recommendations.
    """
    activity.logger.info(f"Starting price analysis for {len(input_data.product_ids)} products")
    
    try:
        price_data = {}
        all_recommendations = []
        
        for product_id in input_data.product_ids:
            # Get price information
            price_drop_data = await sg_price_drop.run(product_id)
            
            # Calculate price insights
            insights = {
                "price_drop_info": price_drop_data,
                "analysis_type": input_data.analysis_type,
                "timestamp": datetime.now().isoformat()
            }
            
            if price_drop_data and price_drop_data.get("ok"):
                drop_data = price_drop_data.get("result", {})
                percent_drop = drop_data.get("percent_drop_7d", 0)
                
                if percent_drop > 0.1:  # 10% drop
                    all_recommendations.append(f"Product {product_id} has significant price drop: {percent_drop*100:.1f}%")
                elif percent_drop < -0.05:  # Price increase
                    all_recommendations.append(f"Product {product_id} price increased recently")
                
                insights["price_trend"] = "decreasing" if percent_drop > 0 else "stable"
                insights["attractiveness_score"] = drop_data.get("attractiveness", 0)
            
            price_data[product_id] = insights
        
        # Generate analysis summary
        total_products = len(input_data.product_ids)
        products_with_drops = sum(1 for data in price_data.values() 
                                if data.get("price_drop_info", {}).get("ok") and 
                                   data.get("price_drop_info", {}).get("result", {}).get("percent_drop_7d", 0) > 0)
        
        analysis_summary = f"Analyzed {total_products} products. {products_with_drops} showing price decreases."
        
        confidence_score = min(1.0, len([d for d in price_data.values() if "error" not in d]) / total_products)
        
        return PriceAnalysisOutput(
            price_data=price_data,
            analysis_summary=analysis_summary,
            recommendations=all_recommendations,
            confidence_score=confidence_score,
            market_insights={
                "total_analyzed": total_products,
                "with_price_drops": products_with_drops,
                "analysis_timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        activity.logger.error(f"Price analysis failed: {e}")
        raise

# ─── Notification Activities ───────────────────────────────────
@activity.defn(name="send_notification")
async def send_notification_activity(input_data: NotificationInput) -> NotificationOutput:
    """
    Send notification to user through specified channel.
    """
    activity.logger.info(f"Sending {input_data.notification_type} notification to user {input_data.user_id}")
    
    try:
        # Simulate notification sending (in real implementation, integrate with notification service)
        notification_id = f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{input_data.user_id}"
        
        # Log the notification (in production, this would send actual notifications)
        activity.logger.info(f"Notification sent: {input_data.message}")
        
        # Simulate delivery delay based on urgency
        if input_data.urgency == "urgent":
            await asyncio.sleep(0.1)  # Immediate
        elif input_data.urgency == "high":
            await asyncio.sleep(0.5)  # Fast
        else:
            await asyncio.sleep(1.0)  # Normal
        
        return NotificationOutput(
            success=True,
            notification_id=notification_id,
            delivered_at=datetime.now()
        )
        
    except Exception as e:
        activity.logger.error(f"Notification failed: {e}")
        return NotificationOutput(
            success=False,
            notification_id="",
            error_message=str(e)
        )

@activity.defn(name="send_price_alert")
async def send_price_alert_activity(
    user_id: str, 
    product_id: int, 
    current_price: float, 
    target_price: float,
    price_drop_percent: float
) -> NotificationOutput:
    """
    Send price alert notification when target price is reached.
    """
    activity.logger.info(f"Sending price alert for product {product_id} to user {user_id}")
    
    message = f"🎉 Price Alert! Product {product_id} is now ${current_price:.2f} "
    message += f"(target: ${target_price:.2f}, {price_drop_percent:.1f}% drop)"
    
    notification_input = NotificationInput(
        user_id=user_id,
        notification_type="price_alert",
        message=message,
        data={
            "product_id": product_id,
            "current_price": current_price,
            "target_price": target_price,
            "price_drop_percent": price_drop_percent
        },
        urgency="high",
        channel="email"
    )
    
    return await send_notification_activity(notification_input)

# ─── Agent Integration Activities ──────────────────────────────
@activity.defn(name="agent_product_discovery")
async def agent_product_discovery_activity(query: str, context_data: Dict[str, Any]) -> AgentResponse:
    """
    Use ProductDiscoveryAgent through Temporal activity.
    """
    activity.logger.info(f"Running ProductDiscoveryAgent for query: {query}")
    
    try:
        agent = ProductDiscoveryAgent()
        user_query = UserQuery(text=query)
        context = ConversationContext(session_id=context_data.get("session_id", "temporal_session"))
        
        response = await agent.execute(user_query, context)
        
        activity.logger.info(f"ProductDiscoveryAgent completed with confidence: {response.confidence}")
        return response
        
    except Exception as e:
        activity.logger.error(f"Agent product discovery failed: {e}")
        raise

@activity.defn(name="agent_price_analysis")
async def agent_price_analysis_activity(query: str, context_data: Dict[str, Any]) -> AgentResponse:
    """
    Use PriceAnalysisAgent through Temporal activity.
    """
    activity.logger.info(f"Running PriceAnalysisAgent for query: {query}")
    
    try:
        agent = PriceAnalysisAgent()
        user_query = UserQuery(text=query)
        context = ConversationContext(session_id=context_data.get("session_id", "temporal_session"))
        
        response = await agent.execute(user_query, context)
        
        activity.logger.info(f"PriceAnalysisAgent completed with confidence: {response.confidence}")
        return response
        
    except Exception as e:
        activity.logger.error(f"Agent price analysis failed: {e}")
        raise

# ─── Utility Activities ────────────────────────────────────────
@activity.defn(name="log_workflow_event")
async def log_workflow_event_activity(
    workflow_id: str, 
    event_type: str, 
    event_data: Dict[str, Any]
) -> bool:
    """
    Log workflow events for monitoring and analytics.
    """
    log_entry = {
        "workflow_id": workflow_id,
        "event_type": event_type,
        "event_data": event_data,
        "timestamp": datetime.now().isoformat()
    }
    
    activity.logger.info(f"Workflow event: {json.dumps(log_entry)}")
    return True

@activity.defn(name="validate_user_input")
async def validate_user_input_activity(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and process user input for workflow decisions.
    """
    activity.logger.info(f"Validating user input: {user_input[:50]}...")
    
    validation_result = {
        "is_valid": True,
        "input_type": "unknown",
        "extracted_data": {},
        "confidence": 0.0
    }
    
    # Simple input validation logic
    user_input_lower = user_input.lower().strip()
    
    if any(word in user_input_lower for word in ["yes", "proceed", "continue", "buy", "purchase"]):
        validation_result.update({
            "input_type": "confirmation",
            "extracted_data": {"decision": "proceed"},
            "confidence": 0.8
        })
    elif any(word in user_input_lower for word in ["no", "skip", "pass", "not interested"]):
        validation_result.update({
            "input_type": "rejection", 
            "extracted_data": {"decision": "skip"},
            "confidence": 0.8
        })
    elif any(word in user_input_lower for word in ["wait", "postpone", "later", "think about"]):
        validation_result.update({
            "input_type": "postponement",
            "extracted_data": {"decision": "postpone"},
            "confidence": 0.7
        })
    elif "?" in user_input or any(word in user_input_lower for word in ["what", "how", "why", "when"]):
        validation_result.update({
            "input_type": "question",
            "extracted_data": {"question": user_input},
            "confidence": 0.6
        })
    
    return validation_result

# ─── Helper Functions ───────────────────────────────────────────
def _calculate_comprehensive_score(price_drop_data: Dict, criteria_scores: List[Dict]) -> float:
    """Calculate comprehensive product score from various factors."""
    score = 0.5  # Base score
    
    # Price factor
    if price_drop_data and price_drop_data.get("ok"):
        drop_data = price_drop_data.get("result", {})
        percent_drop = drop_data.get("percent_drop_7d", 0)
        attractiveness = drop_data.get("attractiveness", 5) / 10  # Normalize to 0-1
        
        score += min(0.3, percent_drop * 2)  # Up to 0.3 for price drops
        score += attractiveness * 0.2  # Up to 0.2 for attractiveness
    
    # Quality factor
    if criteria_scores:
        avg_rating = sum(item.get("rating", 0) for item in criteria_scores) / len(criteria_scores)
        score += (avg_rating / 5.0) * 0.3  # Up to 0.3 for quality (assuming 5-point scale)
    
    return min(1.0, score) 