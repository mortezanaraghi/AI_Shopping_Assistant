"""
Temporal-Enabled Shopping Assistant Orchestrator
Integrates Temporal.io workflows with the existing agent system for durable, fault-tolerant processing.
"""
from __future__ import annotations
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from temporalio import workflow
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

from .utils.logging import init_logger
from .config import get_settings
from .models import ConversationContext, AgentResponse, UserQuery
from .workflow_models import (
    ShoppingJourneyState, UserDecisionSignal, WorkflowStatus,
    ShoppingWorkflowResult, PriceMonitoringResult
)
from .workflows import ShoppingJourneyWorkflow, PriceMonitoringWorkflow, QuickQueryWorkflow
from .activities import *  # Import all activities

# Fallback to enhanced orchestrator for non-workflow operations
from .enhanced_orchestrator import EnhancedOrchestrator

settings = get_settings()
log = init_logger(settings.log_level)

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
        
    async def initialize(self):
        """Initialize Temporal client and worker."""
        try:
            # Connect to Temporal server
            self.client = await Client.connect(self.temporal_address)
            log.info(f"Connected to Temporal server at {self.temporal_address}")
            
            # Create worker for executing workflows and activities
            self.worker = Worker(
                self.client,
                task_queue=self.task_queue,
                workflows=[ShoppingJourneyWorkflow, PriceMonitoringWorkflow, QuickQueryWorkflow],
                activities=[
                    product_discovery_activity,
                    enhanced_product_analysis_activity,
                    price_monitoring_check_activity,
                    price_analysis_activity,
                    send_notification_activity,
                    send_price_alert_activity,
                    agent_product_discovery_activity,
                    agent_price_analysis_activity,
                    log_workflow_event_activity,
                    validate_user_input_activity
                ]
            )
            
            log.info("Temporal worker configured successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize Temporal: {e}")
            log.warning("Falling back to enhanced orchestrator only")
            self.client = None
            self.worker = None
    
    async def start_worker(self):
        """Start the Temporal worker (non-blocking)."""
        if self.worker:
            log.info("Starting Temporal worker...")
            # Start worker in background
            asyncio.create_task(self.worker.run())
            log.info("Temporal worker started")
        else:
            log.warning("No Temporal worker to start")
    
    async def process_query(
        self, 
        user_input: str, 
        context: ConversationContext,
        workflow_type: str = "auto"
    ) -> AgentResponse:
        """
        Process user query using appropriate workflow or fallback processing.
        
        Args:
            user_input: User's query text
            context: Conversation context
            workflow_type: "auto", "quick", "journey", "monitor", or "fallback"
        """
        log.info(f"Processing query with workflow_type: {workflow_type}")
        
        # If Temporal is not available, use fallback
        if not self.client:
            log.info("Temporal not available, using fallback orchestrator")
            return await self.fallback_orchestrator.process_query(user_input, context)
        
        # Determine processing approach
        if workflow_type == "auto":
            workflow_type = self._determine_workflow_type(user_input, context)
        
        if workflow_type == "fallback":
            return await self.fallback_orchestrator.process_query(user_input, context)
        
        try:
            if workflow_type == "quick":
                return await self._process_quick_query(user_input, context)
            elif workflow_type == "journey":
                return await self._start_shopping_journey(user_input, context)
            elif workflow_type == "monitor":
                return await self._start_price_monitoring(user_input, context)
            else:
                # Default to quick processing
                return await self._process_quick_query(user_input, context)
                
        except Exception as e:
            log.error(f"Temporal workflow processing failed: {e}")
            log.info("Falling back to enhanced orchestrator")
            return await self.fallback_orchestrator.process_query(user_input, context)
    
    async def _process_quick_query(self, user_input: str, context: ConversationContext) -> AgentResponse:
        """Process query using QuickQueryWorkflow."""
        log.info("Processing quick query via Temporal workflow")
        
        workflow_id = f"quick-{context.session_id}-{uuid.uuid4().hex[:8]}"
        
        try:
            # Start quick query workflow
            handle = await self.client.start_workflow(
                QuickQueryWorkflow.run,
                user_input,
                context.user_id or "anonymous",
                context.session_id,
                id=workflow_id,
                task_queue=self.task_queue,
                execution_timeout=timedelta(minutes=5)
            )
            
            # Wait for completion
            result = await handle.result()
            
            # Convert result to AgentResponse
            if result["status"] == "completed":
                workflow_response = result["response"]
                return AgentResponse(
                    content=workflow_response["content"],
                    agent_id="temporal_workflow",
                    confidence=workflow_response.get("confidence", 0.8),
                    tool_calls=workflow_response.get("tool_calls", []),
                    data={
                        "workflow_id": workflow_id,
                        "processed_by": "temporal",
                        "execution_time": result.get("execution_time")
                    }
                )
            else:
                return AgentResponse(
                    content="Sorry, I encountered an error processing your request.",
                    agent_id="temporal_workflow", 
                    confidence=0.0,
                    data={"workflow_id": workflow_id, "error": result.get("error")}
                )
                
        except Exception as e:
            log.error(f"Quick query workflow failed: {e}")
            return AgentResponse(
                content="Sorry, I encountered an error processing your request.",
                agent_id="temporal_workflow",
                confidence=0.0,
                data={"workflow_id": workflow_id, "error": str(e)}
            )
    
    async def _start_shopping_journey(self, user_input: str, context: ConversationContext) -> AgentResponse:
        """Start a comprehensive shopping journey workflow."""
        log.info("Starting shopping journey workflow")
        
        workflow_id = f"journey-{context.user_id or 'anon'}-{uuid.uuid4().hex[:8]}"
        
        try:
            # Start shopping journey workflow
            handle = await self.client.start_workflow(
                ShoppingJourneyWorkflow.run,
                context.user_id or "anonymous",
                context.session_id,
                user_input,
                {},  # user_preferences
                id=workflow_id,
                task_queue=self.task_queue,
                execution_timeout=timedelta(days=30)  # Long-running workflow
            )
            
            # Store workflow handle for later interaction
            self.active_workflows[workflow_id] = handle
            
            # Return immediate response
            return AgentResponse(
                content=f"I've started a comprehensive shopping journey to help you find the perfect product. "
                       f"I'll analyze your options and guide you through the decision-making process. "
                       f"Journey ID: {workflow_id}",
                agent_id="temporal_shopping_journey",
                confidence=0.9,
                data={
                    "workflow_id": workflow_id,
                    "workflow_type": "shopping_journey",
                    "status": "started",
                    "can_receive_signals": True
                },
                needs_user_input=True
            )
            
        except Exception as e:
            log.error(f"Shopping journey workflow failed to start: {e}")
            return AgentResponse(
                content="Sorry, I couldn't start your shopping journey. Let me help you directly instead.",
                agent_id="temporal_workflow",
                confidence=0.0,
                data={"error": str(e)}
            )
    
    async def _start_price_monitoring(self, user_input: str, context: ConversationContext) -> AgentResponse:
        """Start a price monitoring workflow."""
        log.info("Starting price monitoring workflow")
        
        # Extract product IDs and target price from user input (simplified)
        # In a real implementation, this would use NLP to extract structured data
        product_ids = [1, 2, 3]  # Mock extraction
        target_price = None
        
        workflow_id = f"monitor-{context.user_id or 'anon'}-{uuid.uuid4().hex[:8]}"
        
        try:
            # Start price monitoring workflow
            handle = await self.client.start_workflow(
                PriceMonitoringWorkflow.run,
                context.user_id or "anonymous",
                product_ids,
                target_price,
                30,  # duration_days
                6,   # check_interval_hours
                id=workflow_id,
                task_queue=self.task_queue,
                execution_timeout=timedelta(days=35)
            )
            
            # Store workflow handle
            self.active_workflows[workflow_id] = handle
            
            return AgentResponse(
                content=f"I've started monitoring prices for your selected products. "
                       f"I'll notify you when I find good deals or significant price drops. "
                       f"Monitoring will continue for 30 days. Monitor ID: {workflow_id}",
                agent_id="temporal_price_monitor",
                confidence=0.9,
                data={
                    "workflow_id": workflow_id,
                    "workflow_type": "price_monitoring",
                    "product_ids": product_ids,
                    "duration_days": 30
                }
            )
            
        except Exception as e:
            log.error(f"Price monitoring workflow failed to start: {e}")
            return AgentResponse(
                content="Sorry, I couldn't start price monitoring. Let me help you with current prices instead.",
                agent_id="temporal_workflow",
                confidence=0.0,
                data={"error": str(e)}
            )
    
    def _determine_workflow_type(self, user_input: str, context: ConversationContext) -> str:
        """Automatically determine the appropriate workflow type."""
        user_input_lower = user_input.lower()
        
        # Long-running journey indicators
        journey_indicators = [
            "help me choose", "comparing options", "decision", "research",
            "best option", "comprehensive analysis", "guide me through"
        ]
        
        # Price monitoring indicators
        monitor_indicators = [
            "monitor price", "watch for deals", "alert me when", "track price",
            "notify when cheaper", "price drops"
        ]
        
        # Complex query indicators
        complex_indicators = [
            "vs", "compare", "difference between", "pros and cons",
            "which is better", "recommendation"
        ]
        
        if any(indicator in user_input_lower for indicator in monitor_indicators):
            return "monitor"
        elif any(indicator in user_input_lower for indicator in journey_indicators):
            return "journey"
        elif any(indicator in user_input_lower for indicator in complex_indicators):
            return "journey"
        else:
            return "quick"
    
    async def send_user_decision(self, workflow_id: str, decision: UserDecisionSignal) -> bool:
        """Send user decision signal to a running workflow."""
        if workflow_id not in self.active_workflows:
            log.warning(f"Workflow {workflow_id} not found in active workflows")
            return False
        
        try:
            handle = self.active_workflows[workflow_id]
            await handle.signal(ShoppingJourneyWorkflow.user_decision_signal, decision)
            log.info(f"Sent decision signal to workflow {workflow_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to send decision signal: {e}")
            return False
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a running workflow."""
        if workflow_id not in self.active_workflows:
            return None
        
        try:
            handle = self.active_workflows[workflow_id]
            description = await handle.describe()
            
            return {
                "workflow_id": workflow_id,
                "status": description.status,
                "start_time": description.start_time,
                "execution_time": description.execution_time,
                "history_length": len(description.history_events) if description.history_events else 0
            }
            
        except Exception as e:
            log.error(f"Failed to get workflow status: {e}")
            return None
    
    async def list_active_workflows(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active workflows, optionally filtered by user."""
        workflows = []
        
        for workflow_id, handle in self.active_workflows.items():
            try:
                description = await handle.describe()
                
                workflow_info = {
                    "workflow_id": workflow_id,
                    "status": description.status,
                    "start_time": description.start_time,
                    "workflow_type": description.workflow_type
                }
                
                # Filter by user if specified
                if user_id is None or user_id in workflow_id:
                    workflows.append(workflow_info)
                    
            except Exception as e:
                log.warning(f"Failed to describe workflow {workflow_id}: {e}")
        
        return workflows
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        if workflow_id not in self.active_workflows:
            return False
        
        try:
            handle = self.active_workflows[workflow_id]
            await handle.cancel()
            del self.active_workflows[workflow_id]
            log.info(f"Cancelled workflow {workflow_id}")
            return True
            
        except Exception as e:
            log.error(f"Failed to cancel workflow: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check system health including Temporal connectivity."""
        health_status = await self.fallback_orchestrator.health_check()
        
        # Add Temporal-specific health checks
        temporal_health = {
            "temporal_connected": self.client is not None,
            "worker_running": self.worker is not None,
            "active_workflows": len(self.active_workflows),
            "task_queue": self.task_queue
        }
        
        if self.client:
            try:
                # Test Temporal connectivity
                await self.client.service.get_system_info()
                temporal_health["temporal_service"] = "healthy"
            except Exception as e:
                temporal_health["temporal_service"] = f"error: {str(e)}"
        
        health_status.update(temporal_health)
        return health_status
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.worker:
            await self.worker.shutdown()
        
        if self.client:
            await self.client.close()
        
        log.info("Temporal orchestrator cleaned up")

# Factory function for backwards compatibility
def Orchestrator(use_temporal: bool = True) -> Union[TemporalOrchestrator, EnhancedOrchestrator]:
    """
    Factory function that returns appropriate orchestrator based on configuration.
    """
    if use_temporal:
        log.info("Creating Temporal-enabled orchestrator")
        return TemporalOrchestrator()
    else:
        log.info("Creating enhanced orchestrator (no Temporal)")
        return EnhancedOrchestrator() 