"""
Temporal.io Workflows for Shopping Assistant
Durable, fault-tolerant workflows that orchestrate complex shopping processes.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from temporalio import workflow
from temporalio.common import RetryPolicy

from workflow_models import (
    ShoppingJourneyState, ShoppingJourneyStage, PriceMonitoringState,
    ProductDiscoveryInput, PriceAnalysisInput, NotificationInput,
    ShoppingWorkflowResult, PriceMonitoringResult, UserDecisionSignal,
    WorkflowStatus
)

# Import activities
from activities import (
    product_discovery_activity, enhanced_product_analysis_activity,
    price_monitoring_check_activity, price_analysis_activity,
    send_notification_activity, send_price_alert_activity,
    agent_product_discovery_activity, agent_price_analysis_activity,
    log_workflow_event_activity, validate_user_input_activity
)

# ─── Main Shopping Journey Workflow ────────────────────────────
@workflow.defn
class ShoppingJourneyWorkflow:
    """
    Comprehensive shopping journey workflow that guides users through 
    product discovery, analysis, and decision-making process.
    """
    
    def __init__(self):
        self.journey_state: Optional[ShoppingJourneyState] = None
        self.user_decision: Optional[UserDecisionSignal] = None
    
    @workflow.run
    async def run(
        self, 
        user_id: str, 
        session_id: str, 
        initial_query: str, 
        user_preferences: Dict[str, Any] = None
    ) -> ShoppingWorkflowResult:
        """
        Main workflow execution for shopping journey.
        """
        workflow.logger.info(f"Starting shopping journey for user {user_id}")
        
        # Initialize journey state
        self.journey_state = ShoppingJourneyState(
            user_id=user_id,
            session_id=session_id,
            initial_query=initial_query,
            current_stage=ShoppingJourneyStage.DISCOVERY
        )
        
        workflow_id = workflow.info().workflow_id
        
        # Log workflow start
        await workflow.execute_activity(
            log_workflow_event_activity,
            workflow_id, "journey_started", {"user_id": user_id, "query": initial_query},
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        try:
            # Execute journey stages
            while self.journey_state.current_stage != ShoppingJourneyStage.COMPLETED:
                
                if self.journey_state.current_stage == ShoppingJourneyStage.DISCOVERY:
                    await self._execute_discovery_stage()
                    
                elif self.journey_state.current_stage == ShoppingJourneyStage.ANALYSIS:
                    await self._execute_analysis_stage()
                    
                elif self.journey_state.current_stage == ShoppingJourneyStage.COMPARISON:
                    await self._execute_comparison_stage()
                    
                elif self.journey_state.current_stage == ShoppingJourneyStage.DECISION_SUPPORT:
                    await self._execute_decision_support_stage()
                    
                elif self.journey_state.current_stage == ShoppingJourneyStage.PURCHASE_SUPPORT:
                    await self._execute_purchase_support_stage()
                
                # Update activity timestamp
                self.journey_state.update_activity()
                
                # Check for timeout or user abandonment
                if self.journey_state.is_stale:
                    workflow.logger.info("Journey appears stale, sending re-engagement")
                    await self._handle_journey_timeout()
                    break
            
            # Generate final result
            final_recommendation = None
            if self.journey_state.products_considered:
                # Select best product based on comprehensive analysis
                final_recommendation = self.journey_state.products_considered[0]  # Simplified selection
            
            return ShoppingWorkflowResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.COMPLETED,
                journey_state=self.journey_state,
                final_recommendation=final_recommendation,
                insights=self._generate_journey_insights(),
                user_satisfaction_score=None  # Would be collected separately
            )
            
        except Exception as e:
            workflow.logger.error(f"Shopping journey failed: {e}")
            
            await workflow.execute_activity(
                log_workflow_event_activity,
                workflow_id, "journey_failed", {"error": str(e)},
                start_to_close_timeout=timedelta(seconds=30)
            )
            
            return ShoppingWorkflowResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.FAILED,
                journey_state=self.journey_state,
                insights=[f"Journey failed: {str(e)}"]
            )
    
    async def _execute_discovery_stage(self):
        """Execute product discovery phase."""
        workflow.logger.info("Executing discovery stage")
        
        # Discover products using enhanced activity
        discovery_input = ProductDiscoveryInput(
            query=self.journey_state.initial_query,
            max_results=10
        )
        
        discovery_result = await workflow.execute_activity(
            product_discovery_activity,
            discovery_input,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        # Update journey state
        self.journey_state.products_considered = discovery_result.products
        
        # Send update to user
        if discovery_result.products:
            await workflow.execute_activity(
                send_notification_activity,
                NotificationInput(
                    user_id=self.journey_state.user_id,
                    notification_type="discovery_update",
                    message=f"Found {len(discovery_result.products)} products matching your criteria",
                    data={"products_found": len(discovery_result.products)}
                ),
                start_to_close_timeout=timedelta(seconds=30)
            )
            self.journey_state.current_stage = ShoppingJourneyStage.ANALYSIS
        else:
            # No products found, send suggestions
            await workflow.execute_activity(
                send_notification_activity,
                NotificationInput(
                    user_id=self.journey_state.user_id,
                    notification_type="no_products_found",
                    message="No products found. Consider broadening your search criteria.",
                    urgency="normal"
                ),
                start_to_close_timeout=timedelta(seconds=30)
            )
            self.journey_state.current_stage = ShoppingJourneyStage.COMPLETED
    
    async def _execute_analysis_stage(self):
        """Execute detailed product analysis phase."""
        workflow.logger.info("Executing analysis stage")
        
        if not self.journey_state.products_considered:
            self.journey_state.current_stage = ShoppingJourneyStage.COMPLETED
            return
        
        # Analyze top products
        product_ids = [p.id for p in self.journey_state.products_considered[:5]]
        
        analysis_results = await workflow.execute_activity(
            enhanced_product_analysis_activity,
            product_ids,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=2)
        )
        
        # Store analysis results in journey state
        for product in self.journey_state.products_considered:
            if product.id in analysis_results:
                # Add analysis data to product specs
                product.specs.update({"analysis": analysis_results[product.id]})
        
        # Proceed to comparison if multiple good options
        if len([p for p in self.journey_state.products_considered 
                if p.specs.get("analysis", {}).get("comprehensive_score", 0) > 0.7]) > 1:
            self.journey_state.current_stage = ShoppingJourneyStage.COMPARISON
        else:
            self.journey_state.current_stage = ShoppingJourneyStage.DECISION_SUPPORT
    
    async def _execute_comparison_stage(self):
        """Execute product comparison phase."""
        workflow.logger.info("Executing comparison stage")
        
        # Generate comparison analysis
        comparison_data = self._generate_product_comparison()
        
        # Send comparison to user
        await workflow.execute_activity(
            send_notification_activity,
            NotificationInput(
                user_id=self.journey_state.user_id,
                notification_type="product_comparison",
                message="Here's a detailed comparison of your top product options",
                data=comparison_data
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        self.journey_state.current_stage = ShoppingJourneyStage.DECISION_SUPPORT
    
    async def _execute_decision_support_stage(self):
        """Execute decision support phase with user interaction."""
        workflow.logger.info("Executing decision support stage")
        
        # Wait for user decision with timeout
        try:
            # Use workflow.wait_condition instead of wait_for_signal
            decision_received = await workflow.wait_condition(
                lambda: self.user_decision is not None,
                timeout=timedelta(hours=24)
            )
            
            if decision_received and self.user_decision:
                if self.user_decision.decision_type == "purchase":
                    self.journey_state.current_stage = ShoppingJourneyStage.PURCHASE_SUPPORT
                elif self.user_decision.decision_type == "postpone":
                    # Start price monitoring workflow
                    await self._start_price_monitoring(self.user_decision.product_id)
                    self.journey_state.current_stage = ShoppingJourneyStage.COMPLETED
                else:
                    self.journey_state.current_stage = ShoppingJourneyStage.COMPLETED
            else:
                # Timeout - send reminder
                await workflow.execute_activity(
                    send_notification_activity,
                    NotificationInput(
                        user_id=self.journey_state.user_id,
                        notification_type="decision_reminder",
                        message="Still thinking about your purchase? I'm here to help with any questions.",
                        urgency="low"
                    ),
                    start_to_close_timeout=timedelta(seconds=30)
                )
                self.journey_state.current_stage = ShoppingJourneyStage.COMPLETED
                
        except asyncio.TimeoutError:
            # User didn't respond, send helpful reminder
            await workflow.execute_activity(
                send_notification_activity,
                NotificationInput(
                    user_id=self.journey_state.user_id,
                    notification_type="decision_reminder",
                    message="Still thinking about your purchase? I'm here to help with any questions.",
                    urgency="low"
                ),
                start_to_close_timeout=timedelta(seconds=30)
            )
            self.journey_state.current_stage = ShoppingJourneyStage.COMPLETED
    
    async def _execute_purchase_support_stage(self):
        """Execute purchase support phase."""
        workflow.logger.info("Executing purchase support stage")
        
        # Provide purchase guidance
        await workflow.execute_activity(
            send_notification_activity,
            NotificationInput(
                user_id=self.journey_state.user_id,
                notification_type="purchase_guidance",
                message="Great choice! Here are the next steps for your purchase...",
                urgency="normal"
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        self.journey_state.current_stage = ShoppingJourneyStage.COMPLETED
    
    async def _start_price_monitoring(self, product_id: Optional[int]):
        """Start price monitoring workflow for selected product."""
        if product_id:
            await workflow.execute_child_workflow(
                PriceMonitoringWorkflow.run,
                self.journey_state.user_id,
                [product_id],
                target_price=None,  # Monitor for any significant drops
                duration_days=30,
                id=f"price-monitor-{self.journey_state.user_id}-{product_id}"
            )
    
    def _generate_product_comparison(self) -> Dict[str, Any]:
        """Generate product comparison data."""
        comparison = {
            "products": [],
            "comparison_factors": ["price", "quality", "features"],
            "recommendation": "Based on analysis..."
        }
        
        for product in self.journey_state.products_considered[:3]:
            analysis = product.specs.get("analysis", {})
            comparison["products"].append({
                "id": product.id,
                "name": product.name,
                "price": product.price_cents / 100,
                "score": analysis.get("comprehensive_score", 0),
                "key_strengths": ["mock strength 1", "mock strength 2"]
            })
        
        return comparison
    
    def _generate_journey_insights(self) -> List[str]:
        """Generate insights from the shopping journey."""
        insights = []
        
        if self.journey_state.products_considered:
            insights.append(f"Evaluated {len(self.journey_state.products_considered)} products")
        
        journey_duration = self.journey_state.duration
        if journey_duration > timedelta(days=1):
            insights.append("Took time for careful consideration")
        elif journey_duration < timedelta(hours=1):
            insights.append("Quick decision-making process")
        
        return insights
    
    @workflow.signal
    async def user_decision_signal(self, decision: UserDecisionSignal):
        """Handle user decision signal."""
        workflow.logger.info(f"Received user decision: {decision.decision_type}")
        self.user_decision = decision
    
    async def _handle_journey_timeout(self):
        """Handle journey timeout with re-engagement."""
        await workflow.execute_activity(
            send_notification_activity,
            NotificationInput(
                user_id=self.journey_state.user_id,
                notification_type="re_engagement",
                message="We noticed you haven't completed your shopping journey. Need any help?",
                urgency="low"
            ),
            start_to_close_timeout=timedelta(seconds=30)
        )

# ─── Price Monitoring Workflow ─────────────────────────────────
@workflow.defn
class PriceMonitoringWorkflow:
    """
    Long-running price monitoring workflow that tracks product prices
    and sends alerts when target prices are reached.
    """
    
    @workflow.run
    async def run(
        self,
        user_id: str,
        product_ids: List[int],
        target_price: Optional[float] = None,
        duration_days: int = 30,
        check_interval_hours: int = 6
    ) -> PriceMonitoringResult:
        """
        Main price monitoring workflow execution.
        """
        workflow.logger.info(f"Starting price monitoring for user {user_id}, {len(product_ids)} products")
        
        # Initialize monitoring state
        monitoring_state = PriceMonitoringState(
            user_id=user_id,
            product_ids=product_ids,
            target_price=target_price or 0.0,
            check_interval_hours=check_interval_hours,
            duration_days=duration_days
        )
        
        workflow_id = workflow.info().workflow_id
        alerts_triggered = []
        
        # Log monitoring start
        await workflow.execute_activity(
            log_workflow_event_activity,
            workflow_id, "monitoring_started", {
                "user_id": user_id, 
                "products": product_ids, 
                "duration_days": duration_days
            },
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        try:
            # Monitor until end time
            while workflow.now() < monitoring_state.monitoring_end_time:
                
                # Check current prices
                price_results = await workflow.execute_activity(
                    price_monitoring_check_activity,
                    product_ids,
                    start_to_close_timeout=timedelta(minutes=3),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )
                
                # Process price changes and trigger alerts
                for product_id, price_data in price_results.items():
                    if price_data.get("available") and "error" not in price_data:
                        current_price = price_data["current_price_dollars"]
                        
                        # Update monitoring state
                        monitoring_state.current_prices[product_id] = current_price
                        
                        # Initialize price history if needed
                        if product_id not in monitoring_state.price_history:
                            monitoring_state.price_history[product_id] = []
                        
                        # Add to price history
                        monitoring_state.price_history[product_id].append({
                            "price": current_price,
                            "timestamp": workflow.now().isoformat()
                        })
                        
                        # Check for price alerts
                        should_alert = False
                        alert_reason = ""
                        
                        if target_price and current_price <= target_price:
                            should_alert = True
                            alert_reason = f"Target price ${target_price:.2f} reached"
                        
                        # Check for significant price drops
                        if len(monitoring_state.price_history[product_id]) > 1:
                            previous_price = monitoring_state.price_history[product_id][-2]["price"]
                            price_drop_percent = ((previous_price - current_price) / previous_price) * 100
                            
                            if price_drop_percent > 10:  # 10% drop
                                should_alert = True
                                alert_reason = f"Significant price drop: {price_drop_percent:.1f}%"
                        
                        # Send alert if triggered
                        if should_alert:
                            alert_result = await workflow.execute_activity(
                                send_price_alert_activity,
                                user_id, product_id, current_price, target_price or current_price,
                                price_drop_percent if 'price_drop_percent' in locals() else 0.0,
                                start_to_close_timeout=timedelta(seconds=30)
                            )
                            
                            alert_data = {
                                "product_id": product_id,
                                "trigger_price": current_price,
                                "reason": alert_reason,
                                "timestamp": workflow.now().isoformat(),
                                "notification_success": alert_result.success
                            }
                            alerts_triggered.append(alert_data)
                            
                            workflow.logger.info(f"Price alert triggered: {alert_reason}")
                
                # Wait for next check interval
                await workflow.sleep(timedelta(hours=check_interval_hours))
            
            # Monitoring completed
            final_prices = {pid: monitoring_state.current_prices.get(pid, 0.0) 
                          for pid in product_ids}
            
            return PriceMonitoringResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.COMPLETED,
                monitoring_state=monitoring_state,
                alerts_triggered=alerts_triggered,
                final_prices=final_prices,
                savings_achieved=self._calculate_savings(monitoring_state, alerts_triggered)
            )
            
        except Exception as e:
            workflow.logger.error(f"Price monitoring failed: {e}")
            
            return PriceMonitoringResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.FAILED,
                monitoring_state=monitoring_state,
                alerts_triggered=alerts_triggered
            )
    
    def _calculate_savings(self, state: PriceMonitoringState, alerts: List[Dict]) -> Optional[float]:
        """Calculate potential savings from price monitoring."""
        if not alerts:
            return None
        
        total_savings = 0.0
        for alert in alerts:
            if "price_drop" in alert["reason"]:
                # Estimate savings based on price drop
                total_savings += alert["trigger_price"] * 0.1  # Simplified calculation
        
        return total_savings if total_savings > 0 else None

# ─── Quick Query Workflow ──────────────────────────────────────
@workflow.defn  
class QuickQueryWorkflow:
    """
    Fast workflow for simple queries that don't require long-running processes.
    """
    
    @workflow.run
    async def run(self, query: str, user_id: str, session_id: str) -> Dict[str, Any]:
        """
        Execute quick query processing using existing agents through Temporal.
        """
        workflow.logger.info(f"Processing quick query: {query}")
        
        context_data = {"session_id": session_id, "user_id": user_id}
        
        try:
            # Determine query type and route to appropriate agent
            if any(word in query.lower() for word in ["price", "cost", "deal", "cheap", "expensive"]):
                # Price-related query
                response = await workflow.execute_activity(
                    agent_price_analysis_activity,
                    query, context_data,
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )
            else:
                # General product query
                response = await workflow.execute_activity(
                    agent_product_discovery_activity,
                    query, context_data,
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )
            
            return {
                "status": "completed",
                "response": response.model_dump(),
                "processed_by": "temporal_workflow",
                "execution_time": workflow.now().isoformat()
            }
            
        except Exception as e:
            workflow.logger.error(f"Quick query failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "processed_by": "temporal_workflow"
            } 