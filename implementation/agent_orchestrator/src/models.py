from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Literal, List, Dict, Optional, Set, Union
from datetime import datetime
from enum import Enum
import uuid

# ─── Core User and Session Models ─────────────────────────
class ConversationContext(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)  # Changed from Dict[str, str] to Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    user_profile: Optional['UserProfile'] = None  # Add user profile reference

class UserRequirements(BaseModel):
    query: str
    budget_cents: Optional[int] = None
    use_case: Optional[str] = None
    user_id: Optional[str] = None
    urgency: Optional[str] = None  # "low", "medium", "high"

class UserQuery(BaseModel):
    text: str
    user_id: Optional[str] = None
    intent: Optional[str] = None
    embedding: Optional[List[float]] = None
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)

# ─── Enhanced Interaction Tracking Models ──────────────────
class InteractionEvent(BaseModel):
    event_type: str  # "search", "view", "like", "skip", "purchase", "click"
    product_id: Optional[int] = None
    query: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: str
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PurchaseEvent(BaseModel):
    product_id: int
    price_paid_cents: int
    purchase_date: datetime = Field(default_factory=datetime.now)
    category: str
    brand: Optional[str] = None
    satisfaction_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchContext(BaseModel):
    """Extracted context from conversation history"""
    previous_queries: List[str] = Field(default_factory=list)
    mentioned_brands: List[str] = Field(default_factory=list)
    price_discussions: List[str] = Field(default_factory=list)
    category_focus: Optional[str] = None
    recently_viewed: List[int] = Field(default_factory=list)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)

# ─── Enhanced User Profile Models ──────────────────────────
class UserProfile(BaseModel):
    user_id: str
    preferences: Dict[str, float] = Field(default_factory=dict)
    price_sensitivity: float = 0.5  # 0 = price insensitive, 1 = very price sensitive
    brand_preferences: List[str] = Field(default_factory=list)
    recency: int = 0  # Number of interactions
    expertise_level: str = "beginner"  # "beginner", "intermediate", "expert"
    category_expertise: Dict[str, float] = Field(default_factory=dict)
    purchase_history: List[PurchaseEvent] = Field(default_factory=list)
    interaction_history: List[InteractionEvent] = Field(default_factory=list)
    temporal_patterns: Dict[str, Any] = Field(default_factory=dict)
    
    # Enhanced behavioral tracking
    search_patterns: Dict[str, int] = Field(default_factory=dict)
    click_through_rates: Dict[str, float] = Field(default_factory=dict)
    session_durations: List[float] = Field(default_factory=list)
    wishlist: List[int] = Field(default_factory=list)
    
    # Temporal patterns
    active_hours: Dict[int, float] = Field(default_factory=dict)
    seasonal_preferences: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Profile metadata
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    
    @property
    def is_price_sensitive(self) -> bool:
        return self.price_sensitivity > 0.7
    
    @property
    def is_quality_focused(self) -> bool:
        return self.price_sensitivity < 0.3
    
    @property
    def completeness(self) -> float:
        """Calculate how complete the user profile is (0-1)"""
        factors = [
            len(self.preferences) > 0,
            len(self.brand_preferences) > 0,
            self.recency > 0,
            len(self.purchase_history) > 0,
            len(self.category_expertise) > 0,
            len(self.interaction_history) > 0
        ]
        return sum(factors) / len(factors)
    
    def update_search_pattern(self, query: str):
        """Track search patterns"""
        tokens = query.lower().split()
        for token in tokens:
            if len(token) > 2:  # Ignore short words
                self.search_patterns[token] = self.search_patterns.get(token, 0) + 1
        self.last_updated = datetime.now()
    
    def record_interaction(self, event_type: str, product_id: Optional[int] = None, 
                          query: Optional[str] = None, session_id: str = "", 
                          confidence: Optional[float] = None):
        """Record user interaction"""
        event = InteractionEvent(
            event_type=event_type,
            product_id=product_id,
            query=query,
            session_id=session_id,
            confidence=confidence
        )
        self.interaction_history.append(event)
        self.recency += 1
        self.last_updated = datetime.now()
        
        # Update search patterns if query provided
        if query:
            self.update_search_pattern(query)
    
    def add_to_wishlist(self, product_id: int):
        """Add product to wishlist"""
        if product_id not in self.wishlist:
            self.wishlist.append(product_id)
            self.last_updated = datetime.now()
    
    def update_brand_preference(self, brand: str, weight: float = 0.1):
        """Update brand preference based on interaction"""
        if brand and brand not in self.brand_preferences:
            # Add new brand if user shows interest
            if weight > 0.05:  # Threshold for adding to preferences
                self.brand_preferences.append(brand)
                self.last_updated = datetime.now()
    
    def update_category_expertise(self, category: str, interaction_type: str):
        """Update category expertise based on interaction"""
        current = self.category_expertise.get(category, 0.0)
        
        # Different interaction types contribute differently to expertise
        if interaction_type == "purchase":
            increment = 0.2
        elif interaction_type == "like":
            increment = 0.1
        elif interaction_type == "view":
            increment = 0.05
        else:
            increment = 0.02
        
        self.category_expertise[category] = min(1.0, current + increment)
        self.last_updated = datetime.now()
    
    def get_preferred_price_range(self) -> tuple[Optional[float], Optional[float]]:
        """Infer preferred price range from purchase history"""
        if not self.purchase_history:
            return None, None
        
        prices = [p.price_paid_cents / 100 for p in self.purchase_history]
        avg_price = sum(prices) / len(prices)
        
        if self.is_price_sensitive:
            return None, avg_price * 1.2  # 20% above average
        elif self.is_quality_focused:
            return avg_price * 0.8, None  # 20% below average as minimum
        else:
            return avg_price * 0.7, avg_price * 1.3  # 30% range around average

# ─── ShopGraph Entity Models ───────────────────────────────
class Promotion(BaseModel):
    id: str
    percent_off: Optional[float]
    amount_off: Optional[int]
    health: int  # 0‑100
    is_storewide: bool
    merchant_id: Optional[int] = None

class PriceDrop(BaseModel):
    percent_drop_7d: float
    attractiveness: float
    days_since_drop: Optional[int] = None

class CriteriaScore(BaseModel):
    criteria_id: int
    rating: float
    response_type: Literal["yes", "no", "maybe"]
    criterion_name: Optional[str] = None

class Merchant(BaseModel):
    id: int
    name: str
    rating: float
    affiliate: bool
    verified: Optional[bool] = True
    total_reviews: Optional[int] = None

class Product(BaseModel):
    id: int
    name: str
    category_id: int
    price_cents: int
    specs: Dict[str, Any] = Field(default_factory=dict)
    brand: Optional[str] = None
    in_stock: bool = True
    fast_shipping: bool = False

class ProductVariant(BaseModel):
    id: int
    product_entity_id: int
    merchants: List[int]
    price_cents: int
    in_stock: bool

class ProductRecommendation(Product):
    score: float
    final_price_cents: Optional[int] = None
    merchant_id: Optional[int] = None
    recommendation_type: Optional[str] = "content_based"
    explanation: Optional[str] = None
    confidence: float = 1.0

# ─── Agent System Models ───────────────────────────────────
class AgentCapability(str, Enum):
    SEARCH = "search"
    FILTERING = "filtering"
    CATEGORIZATION = "categorization"
    PRICING = "pricing"
    DEALS = "deals"
    DISCOUNTS = "discounts"
    PERSONALIZATION = "personalization"
    RANKING = "ranking"
    COMPATIBILITY = "compatibility_analysis"
    REVIEW_ANALYSIS = "review_analysis"
    SPECIFICATION_EXTRACTION = "specification_extraction"
    ANALYSIS = "analysis"
    COMPARISON = "comparison"

class AgentResponse(BaseModel):
    content: str
    tool_calls: List[str] = Field(default_factory=list)
    agent_id: Optional[str] = None
    confidence: float = 1.0
    reasoning: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    needs_user_input: bool = False

class AgentInsight(BaseModel):
    agent_id: str
    insight_type: str
    data: Dict[str, Any]
    confidence: float
    timestamp: datetime = Field(default_factory=datetime.now)

class AgentMetrics(BaseModel):
    agent_id: str
    total_executions: int = 0
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    last_execution: Optional[datetime] = None

# ─── Knowledge Integration Models ───────────────────────────
class RankingWeights(BaseModel):
    deal: float = 0.35
    quality: float = 0.25
    merchant: float = 0.20
    variant: float = 0.10
    budget: float = 0.10
    
    def normalize(self) -> 'RankingWeights':
        """Ensure weights sum to 1.0"""
        total = self.deal + self.quality + self.merchant + self.variant + self.budget
        if total > 0:
            return RankingWeights(
                deal=self.deal / total,
                quality=self.quality / total,
                merchant=self.merchant / total,
                variant=self.variant / total,
                budget=self.budget / total
            )
        return self

class UserIntent(BaseModel):
    product_category: Optional[str] = None
    budget_range: Optional[tuple[int, int]] = None
    specifications: Dict[str, Any] = Field(default_factory=dict)
    use_case: Optional[str] = None
    urgency: str = "medium"
    confidence: float = 0.0

# ─── Conversation and Context Models ───────────────────────
class SessionContext(BaseModel):
    device: str = "web"
    location: str = "US"
    timestamp: datetime = Field(default_factory=datetime.now)
    user_agent: Optional[str] = None

class SharedConversationContext(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    current_query: Optional[UserQuery] = None
    agent_insights: Dict[str, AgentInsight] = Field(default_factory=dict)
    user_profile: Optional[UserProfile] = None
    session_metadata: SessionContext = Field(default_factory=SessionContext)

# ─── Performance and Monitoring Models ─────────────────────
class PerformanceMetrics(BaseModel):
    latency_ms: float
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class SystemHealth(BaseModel):
    overall_status: str
    component_statuses: Dict[str, str]
    active_alerts: List[str] = Field(default_factory=list)
    last_check: datetime = Field(default_factory=datetime.now)

# ─── Integration and Coordination Models ────────────────────
class ExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    phases: List[Dict[str, Any]] = Field(default_factory=list)
    estimated_duration_ms: float = 0.0
    can_parallelize: bool = False

class CollaborationResult(BaseModel):
    participating_agents: List[str]
    shared_insights: Dict[str, Any]
    final_recommendation: Optional[Dict[str, Any]] = None
    success: bool = True

# ─── Cache and State Models ─────────────────────────────────
class CacheEntry(BaseModel):
    key: str
    data: Any
    ttl_seconds: int
    created_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def is_expired(self) -> bool:
        from datetime import timedelta
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry

# ─── Error and Fallback Models ─────────────────────────────
class ComponentFailure(BaseModel):
    component: str
    error_type: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    fallback_used: bool = False

class GracefulDegradationResponse(BaseModel):
    response: AgentResponse
    degradation_level: str  # "none", "partial", "significant"
    failed_components: List[str] = Field(default_factory=list)
    fallback_strategy: Optional[str] = None

# ─── Security and Code Execution Models ────────────────────
class CodeExecutionRequest(BaseModel):
    code: str
    execution_type: Literal["expression", "script"] = "expression"
    timeout_seconds: int = 5
    allowed_operations: Set[str] = Field(default_factory=set)

class CodeExecutionResult(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    security_violations: List[str] = Field(default_factory=list)

# ─── Utility Models ────────────────────────────────────────
class PaginatedResponse(BaseModel):
    items: List[Any]
    total_count: int
    page: int = 1
    page_size: int = 10
    has_next: bool = False
    has_previous: bool = False

 