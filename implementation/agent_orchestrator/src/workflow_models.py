"""
Temporal.io Workflow Models
Defines data structures and state models for durable shopping workflows.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, List, Dict, Optional, Set, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid

from src.models import UserQuery, Product, AgentResponse, ConversationContext, UserProfile

# ─── Workflow State Models ─────────────────────────────────────
class WorkflowStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class ShoppingJourneyStage(str, Enum):
    DISCOVERY = "discovery"
    ANALYSIS = "analysis"
    COMPARISON = "comparison"
    DECISION_SUPPORT = "decision_support"
    PURCHASE_SUPPORT = "purchase_support"
    POST_PURCHASE = "post_purchase"
    COMPLETED = "completed"

class ShoppingJourneyState(BaseModel):
    """State for long-running shopping journey workflows."""
    user_id: str
    session_id: str
    current_stage: ShoppingJourneyStage = ShoppingJourneyStage.DISCOVERY
    
    # Journey data
    initial_query: str
    products_considered: List[Product] = Field(default_factory=list)
    budget_evolution: List[Dict[str, Any]] = Field(default_factory=list)
    preference_evolution: List[Dict[str, Any]] = Field(default_factory=list)
    decision_factors: List[str] = Field(default_factory=list)
    
    # Workflow metadata
    started_at: datetime = Field(default_factory=datetime.now)
    last_activity_at: datetime = Field(default_factory=datetime.now)
    expected_completion: Optional[datetime] = None
    
    # User interaction
    awaiting_user_input: bool = False
    last_user_interaction: Optional[datetime] = None
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity_at = datetime.now()
    
    @property
    def duration(self) -> timedelta:
        """Get current journey duration."""
        return datetime.now() - self.started_at
    
    @property
    def is_stale(self) -> bool:
        """Check if journey has been inactive too long."""
        return (datetime.now() - self.last_activity_at) > timedelta(days=7)

class PriceMonitoringState(BaseModel):
    """State for price monitoring workflows."""
    user_id: str
    product_ids: List[int]
    target_price: float
    current_prices: Dict[int, float] = Field(default_factory=dict)
    price_history: Dict[int, List[Dict[str, Any]]] = Field(default_factory=dict)
    
    # Monitoring configuration
    check_interval_hours: int = 6
    duration_days: int = 30
    started_at: datetime = Field(default_factory=datetime.now)
    
    # Notifications
    notifications_sent: List[Dict[str, Any]] = Field(default_factory=list)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def monitoring_end_time(self) -> datetime:
        """Calculate when monitoring should end."""
        return self.started_at + timedelta(days=self.duration_days)
    
    @property
    def next_check_time(self) -> datetime:
        """Calculate next price check time."""
        if self.price_history:
            last_check = max(
                max(checks[-1]['timestamp'] for checks in self.price_history.values() if checks),
                default=self.started_at
            )
            if isinstance(last_check, str):
                last_check = datetime.fromisoformat(last_check)
            return last_check + timedelta(hours=self.check_interval_hours)
        return self.started_at

# ─── Activity Input/Output Models ──────────────────────────────
class ProductDiscoveryInput(BaseModel):
    """Input for product discovery activity."""
    query: str
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    budget_range: Optional[tuple[float, float]] = None
    category_filters: List[str] = Field(default_factory=list)
    max_results: int = 20

class ProductDiscoveryOutput(BaseModel):
    """Output from product discovery activity."""
    products: List[Product]
    search_metadata: Dict[str, Any]
    confidence_score: float
    recommendations: List[str] = Field(default_factory=list)

class PriceAnalysisInput(BaseModel):
    """Input for price analysis activity."""
    product_ids: List[int]
    analysis_type: str = "comprehensive"  # basic, comprehensive, competitive
    include_history: bool = True
    include_predictions: bool = False

class PriceAnalysisOutput(BaseModel):
    """Output from price analysis activity."""
    price_data: Dict[int, Dict[str, Any]]
    analysis_summary: str
    recommendations: List[str]
    confidence_score: float
    market_insights: Dict[str, Any] = Field(default_factory=dict)

class NotificationInput(BaseModel):
    """Input for user notification activity."""
    user_id: str
    notification_type: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    urgency: str = "normal"  # low, normal, high, urgent
    channel: str = "email"  # email, sms, push, in_app

class NotificationOutput(BaseModel):
    """Output from notification activity."""
    success: bool
    notification_id: str
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None

# ─── Workflow Result Models ────────────────────────────────────
class ShoppingWorkflowResult(BaseModel):
    """Result from shopping workflow execution."""
    workflow_id: str
    status: WorkflowStatus
    journey_state: ShoppingJourneyState
    final_recommendation: Optional[Product] = None
    insights: List[str] = Field(default_factory=list)
    user_satisfaction_score: Optional[float] = None

class PriceMonitoringResult(BaseModel):
    """Result from price monitoring workflow."""
    workflow_id: str
    status: WorkflowStatus
    monitoring_state: PriceMonitoringState
    alerts_triggered: List[Dict[str, Any]] = Field(default_factory=list)
    final_prices: Dict[int, float] = Field(default_factory=dict)
    savings_achieved: Optional[float] = None

# ─── Workflow Configuration Models ─────────────────────────────
class WorkflowConfig(BaseModel):
    """Base configuration for workflows."""
    retry_policy: Dict[str, Any] = Field(default_factory=lambda: {
        "initial_interval": "1s",
        "maximum_interval": "60s", 
        "backoff_coefficient": 2.0,
        "maximum_attempts": 3
    })
    timeout: str = "10m"
    task_queue: str = "shopping-assistant"

class ShoppingWorkflowConfig(WorkflowConfig):
    """Configuration for shopping journey workflows."""
    max_journey_duration_days: int = 30
    user_interaction_timeout_hours: int = 24
    enable_proactive_suggestions: bool = True
    enable_price_monitoring: bool = True

class PriceMonitoringConfig(WorkflowConfig):
    """Configuration for price monitoring workflows."""
    default_check_interval_hours: int = 6
    max_monitoring_duration_days: int = 90
    price_drop_threshold_percent: float = 5.0
    enable_predictive_alerts: bool = False

# ─── Signal and Query Models ───────────────────────────────────
class UserDecisionSignal(BaseModel):
    """Signal sent when user makes a decision."""
    decision_type: str  # purchase, skip, postpone, need_more_info
    product_id: Optional[int] = None
    reasoning: Optional[str] = None
    additional_requirements: Dict[str, Any] = Field(default_factory=dict)

class WorkflowQuery(BaseModel):
    """Query model for workflow status and data."""
    workflow_id: str
    query_type: str  # status, state, history, metrics
    filters: Dict[str, Any] = Field(default_factory=dict)

class WorkflowMetrics(BaseModel):
    """Metrics for workflow performance monitoring."""
    workflow_id: str
    workflow_type: str
    duration: timedelta
    activities_executed: int
    retries_performed: int
    user_interactions: int
    final_status: WorkflowStatus
    created_at: datetime = Field(default_factory=datetime.now) 