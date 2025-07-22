#!/usr/bin/env python3
"""
Personalization and Chat History Tests
Tests for user profile management, conversation history, and personalized recommendations.
"""
import asyncio
import pytest
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.models import (
    ConversationContext, UserProfile, InteractionEvent, PurchaseEvent, 
    SearchContext, UserQuery, AgentResponse
)
from src.state_manager import DistributedStateManager
from src.enhanced_orchestrator import EnhancedOrchestrator, ProductDiscoveryAgent, PriceAnalysisAgent

class TestUserProfileManagement:
    """Test user profile creation, updates, and behavioral tracking."""
    
    def test_user_profile_creation(self):
        """Test creating a new user profile."""
        profile = UserProfile(user_id="test_user_123")
        
        assert profile.user_id == "test_user_123"
        assert profile.price_sensitivity == 0.5
        assert profile.expertise_level == "beginner"
        assert len(profile.brand_preferences) == 0
        assert len(profile.interaction_history) == 0
        assert profile.completeness == 0.0  # Empty profile
    
    def test_user_profile_interaction_recording(self):
        """Test recording user interactions."""
        profile = UserProfile(user_id="test_user")
        
        # Record a search interaction
        profile.record_interaction(
            "search", 
            query="gaming laptops", 
            session_id="session123",
            confidence=0.9
        )
        
        assert len(profile.interaction_history) == 1
        assert profile.recency == 1
        
        interaction = profile.interaction_history[0]
        assert interaction.event_type == "search"
        assert interaction.query == "gaming laptops"
        assert interaction.session_id == "session123"
        assert interaction.confidence == 0.9
        
        # Check search patterns were updated
        assert "gaming" in profile.search_patterns
        assert "laptops" in profile.search_patterns
    
    def test_user_profile_brand_preferences(self):
        """Test brand preference updates."""
        profile = UserProfile(user_id="test_user")
        
        # Add brand preference
        profile.update_brand_preference("Apple", 0.8)
        assert "Apple" in profile.brand_preferences
        
        # Don't add if weight is too low
        profile.update_brand_preference("Samsung", 0.02)
        assert "Samsung" not in profile.brand_preferences
    
    def test_user_profile_category_expertise(self):
        """Test category expertise tracking."""
        profile = UserProfile(user_id="test_user")
        
        # Different interaction types contribute differently
        profile.update_category_expertise("computers", "view")
        assert profile.category_expertise["computers"] == 0.05
        
        profile.update_category_expertise("computers", "like")
        assert abs(profile.category_expertise["computers"] - 0.15) < 1e-10  # Use approximate comparison
        
        profile.update_category_expertise("computers", "purchase")
        assert abs(profile.category_expertise["computers"] - 0.35) < 1e-10  # Use approximate comparison
    
    def test_user_profile_price_range_inference(self):
        """Test price range inference from purchase history."""
        profile = UserProfile(user_id="test_user")
        
        # No purchase history
        min_price, max_price = profile.get_preferred_price_range()
        assert min_price is None and max_price is None
        
        # Add purchase history
        profile.purchase_history.append(PurchaseEvent(
            product_id=1,
            price_paid_cents=100000,  # $1000
            category="laptops"
        ))
        profile.purchase_history.append(PurchaseEvent(
            product_id=2,
            price_paid_cents=150000,  # $1500
            category="laptops"
        ))
        
        # Test different price sensitivities
        profile.price_sensitivity = 0.8  # Price sensitive
        min_price, max_price = profile.get_preferred_price_range()
        assert max_price == 1250 * 1.2  # 20% above average
        
        profile.price_sensitivity = 0.2  # Quality focused
        min_price, max_price = profile.get_preferred_price_range()
        assert min_price == 1250 * 0.8  # 20% below average as minimum

class TestConversationHistory:
    """Test conversation history storage and retrieval."""
    
    @pytest.mark.asyncio
    async def test_conversation_history_storage(self):
        """Test storing and retrieving conversation history."""
        # Mock state manager
        state_manager = MagicMock()
        state_manager.append_to_conversation = AsyncMock(return_value=True)
        state_manager.get_conversation_history = AsyncMock(return_value=[
            {
                "role": "user",
                "content": "find gaming laptops",
                "timestamp": "2024-01-01T10:00:00",
                "session_id": "session123",
                "user_id": "user456"
            },
            {
                "role": "assistant",
                "content": "Here are some gaming laptops...",
                "timestamp": "2024-01-01T10:00:05",
                "session_id": "session123",
                "user_id": "user456",
                "agent_id": "product_discovery",
                "confidence": 0.9
            }
        ])
        
        # Test retrieving history
        history = await state_manager.get_conversation_history("session123")
        
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert "user_id" in history[0]
        assert "session_id" in history[0]
    
    @pytest.mark.asyncio
    async def test_cross_session_history(self):
        """Test retrieving conversation history across sessions."""
        state_manager = MagicMock()
        state_manager.get_user_conversation_history = AsyncMock(return_value=[
            {
                "role": "user",
                "content": "show me monitors",
                "timestamp": "2024-01-01T09:00:00",
                "session_id": "old_session",
                "user_id": "user456"
            },
            {
                "role": "user", 
                "content": "find gaming laptops",
                "timestamp": "2024-01-01T10:00:00",
                "session_id": "current_session",
                "user_id": "user456"
            }
        ])
        
        # Test cross-session history retrieval
        history = await state_manager.get_user_conversation_history("user456", limit=10, days_back=7)
        
        assert len(history) == 2
        # Should include messages from different sessions
        sessions = {msg["session_id"] for msg in history}
        assert "old_session" in sessions
        assert "current_session" in sessions

class TestContextAwareAgents:
    """Test context-aware agent behavior."""
    
    @pytest.mark.asyncio
    async def test_product_discovery_agent_context_extraction(self):
        """Test ProductDiscoveryAgent extracting context from conversation history."""
        agent = ProductDiscoveryAgent()
        
        # Mock conversation history
        history = [
            {
                "role": "user",
                "content": "I need a gaming laptop under $1500 from Apple or Dell",
                "timestamp": "2024-01-01T10:00:00"
            },
            {
                "role": "assistant",
                "content": "Here are some laptops...",
                "data": {
                    "products": [
                        {"id": 1, "name": "Dell Gaming Laptop"},
                        {"id": 2, "name": "Apple MacBook Pro"}
                    ]
                }
            }
        ]
        
        search_context = agent._extract_search_context(history)
        
        assert "gaming laptop under $1500" in search_context.previous_queries[0]
        assert "apple" in search_context.mentioned_brands
        assert "dell" in search_context.mentioned_brands
        assert search_context.category_focus == "computers"  # "gaming laptop" is categorized as "computers"
        assert 1 in search_context.recently_viewed
        assert 2 in search_context.recently_viewed
    
    @pytest.mark.asyncio
    async def test_product_discovery_agent_price_inference(self):
        """Test price range inference from conversation."""
        agent = ProductDiscoveryAgent()
        
        # Create context with price mentions
        context = ConversationContext(
            session_id="test",
            user_id="user123",
            history=[
                {
                    "role": "user",
                    "content": "find laptops under $1200",
                    "timestamp": "2024-01-01T10:00:00"
                }
            ]
        )
        
        min_price, max_price = agent._infer_price_range(context)
        
        assert max_price == 1200.0
        assert min_price is None
    
    @pytest.mark.asyncio
    async def test_product_discovery_agent_personalized_execution(self):
        """Test ProductDiscoveryAgent with personalization."""
        agent = ProductDiscoveryAgent()
        
        # Mock the sg_list_candidates tool
        with patch('src.enhanced_orchestrator.sg_list_candidates') as mock_sg:
            mock_products = [
                {
                    "id": 1, 
                    "name": "Dell Gaming Laptop", 
                    "price_cents": 120000,
                    "category_id": 1,
                    "brand": "Dell",
                    "specs": {}
                },
                {
                    "id": 2, 
                    "name": "Apple MacBook Pro", 
                    "price_cents": 200000,
                    "category_id": 1,
                    "brand": "Apple", 
                    "specs": {}
                }
            ]
            mock_sg.run = AsyncMock(return_value=mock_products)
            
            # Create user profile with preferences
            user_profile = UserProfile(user_id="user123")
            user_profile.brand_preferences = ["Dell"]
            user_profile.price_sensitivity = 0.8  # Price sensitive
            
            # Create context
            context = ConversationContext(
                session_id="test",
                user_id="user123",
                user_profile=user_profile,
                history=[]
            )
            
            query = UserQuery(text="gaming laptops", user_id="user123")
            
            response = await agent.execute(query, context)
            
            assert response.confidence == 0.9
            assert "Dell" in response.content  # Should mention preferred brand
            assert "budget-friendly" in response.content  # Should mention price sensitivity
            assert response.data["personalized"] is True
    
    @pytest.mark.asyncio
    async def test_price_analysis_agent_context_extraction(self):
        """Test PriceAnalysisAgent extracting product context."""
        agent = PriceAnalysisAgent()
        
        # Mock conversation with product data
        context = ConversationContext(
            session_id="test",
            user_id="user123",
            history=[
                {
                    "role": "assistant",
                    "content": "Here are some laptops...",
                    "data": {
                        "products": [
                            {"id": 1, "name": "Dell Gaming Laptop"},
                            {"id": 2, "name": "HP Pavilion"}
                        ]
                    }
                }
            ]
        )
        
        products = agent._extract_product_context(context)
        
        assert len(products) == 2
        assert products[0]["id"] == 1
        assert products[0]["name"] == "Dell Gaming Laptop"
    
    @pytest.mark.asyncio
    async def test_price_analysis_agent_personalized_response(self):
        """Test PriceAnalysisAgent generating personalized responses."""
        agent = PriceAnalysisAgent()
        
        # Mock price analyses
        price_analyses = [
            {
                "product_id": 1,
                "product_name": "Dell Gaming Laptop",
                "price_drop": {
                    "percent_drop_7d": 0.15,  # 15% drop
                    "attractiveness": 8,
                    "days_since_drop": 3
                }
            },
            {
                "product_id": 2,
                "product_name": "Apple MacBook Pro",
                "price_drop": {
                    "percent_drop_7d": 0.05,  # 5% drop
                    "attractiveness": 6,
                    "days_since_drop": 1
                }
            }
        ]
        
        # Price sensitive user
        user_profile = UserProfile(user_id="user123")
        user_profile.price_sensitivity = 0.9
        user_profile.brand_preferences = ["Dell"]
        
        response = agent._generate_price_analysis_response(
            price_analyses, user_profile, "find deals"
        )
        
        assert "Dell Gaming Laptop" in response
        assert "15.0% in the last 7 days" in response
        assert "Recommendation for you" in response
        assert "preferred brands" in response

class TestPersonalizationIntegration:
    """Test end-to-end personalization workflows."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_loads_user_context(self):
        """Test that orchestrator loads user profile and history."""
        # Mock state manager
        mock_state_manager = MagicMock()
        mock_state_manager.get_conversation_history = AsyncMock(return_value=[])
        mock_state_manager.get_user_profile = AsyncMock(return_value=UserProfile(user_id="user123"))
        mock_state_manager.record_user_interaction = AsyncMock(return_value=True)
        mock_state_manager.append_to_conversation = AsyncMock(return_value=True)
        mock_state_manager.health_check = AsyncMock(return_value=True)
        
        # Create orchestrator with mock state manager
        orchestrator = EnhancedOrchestrator()
        orchestrator.state_manager = mock_state_manager
        
        # Mock agent processing
        with patch.object(orchestrator, '_process_with_agents') as mock_process:
            mock_response = AgentResponse(
                content="Test response",
                agent_id="test_agent",
                confidence=0.8
            )
            mock_process.return_value = mock_response
            
            # Create context
            context = ConversationContext(
                session_id="test_session",
                user_id="user123"
            )
            
            # Process query
            response = await orchestrator.process_query("find laptops", context)
            
            # Verify state manager calls
            mock_state_manager.get_conversation_history.assert_called_once()
            mock_state_manager.get_user_profile.assert_called_once_with("user123")
            mock_state_manager.record_user_interaction.assert_called()
            
            # Verify context was populated
            assert context.user_profile is not None
            assert response.content == "Test response"
    
    @pytest.mark.asyncio
    async def test_user_interaction_learning(self):
        """Test that user interactions update the profile."""
        profile = UserProfile(user_id="user123")
        
        # Simulate search interactions
        profile.record_interaction("search", query="gaming laptops", session_id="session1")
        profile.record_interaction("search", query="apple macbook", session_id="session1")
        profile.record_interaction("like", product_id=1, session_id="session1")
        
        # Check profile updates
        assert profile.recency == 3
        assert "gaming" in profile.search_patterns
        assert "laptops" in profile.search_patterns
        assert "apple" in profile.search_patterns
        assert "macbook" in profile.search_patterns
        
        # Check that profile completeness increased
        assert profile.completeness > 0.0
    
    @pytest.mark.asyncio
    async def test_conversation_continuity(self):
        """Test that conversation context enables continuity."""
        # Simulate conversation flow
        history = [
            {
                "role": "user",
                "content": "find gaming laptops",
                "timestamp": "2024-01-01T10:00:00"
            },
            {
                "role": "assistant",
                "content": "Here are some gaming laptops...",
                "data": {"products": [{"id": 1, "name": "Dell Gaming Laptop"}]}
            },
            {
                "role": "user",
                "content": "what's the price of the first one?",
                "timestamp": "2024-01-01T10:01:00"
            }
        ]
        
        # Create context with history
        context = ConversationContext(
            session_id="test",
            user_id="user123",
            history=history
        )
        
        # Test PriceAnalysisAgent can handle follow-up
        agent = PriceAnalysisAgent()
        score = await agent.can_handle(
            UserQuery(text="what's the price of the first one?"), 
            context
        )
        
        # Should have high confidence due to context
        assert score > 0.5
        
        # Extract products from context
        products = agent._extract_product_context(context)
        assert len(products) == 1
        assert products[0]["name"] == "Dell Gaming Laptop"

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 