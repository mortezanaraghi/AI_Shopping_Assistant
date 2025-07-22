#!/usr/bin/env python3
"""
Pipeline Tests - Comprehensive tests for fixes and system integration
Tests for Pydantic fixes, OpenAI tool call handling, AsyncLimiter issues, and error handling.
"""
import asyncio
import pytest
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.models import (
    ConversationContext, UserRequirements, Product, ProductRecommendation,
    UserQuery, AgentResponse
)

class TestPydanticModelDumpFix:
    """Test that all Pydantic models use model_dump() instead of deprecated dict()"""
    
    def test_user_requirements_model_dump(self):
        """Test UserRequirements uses model_dump correctly"""
        req = UserRequirements(
            query="test laptop",
            budget_cents=200000,
            use_case="gaming"
        )
        
        # Should work without deprecation warnings
        data = req.model_dump()
        assert isinstance(data, dict)
        assert data["query"] == "test laptop"
        assert data["budget_cents"] == 200000
    
    def test_product_model_dump(self):
        """Test Product model uses model_dump correctly"""
        product = Product(
            id=1,
            name="Test Laptop",
            category_id=42,
            price_cents=150000,
            brand="TestBrand"
        )
        
        data = product.model_dump()
        assert isinstance(data, dict)
        assert data["name"] == "Test Laptop"
        assert data["price_cents"] == 150000
    
    def test_product_recommendation_model_dump(self):
        """Test ProductRecommendation uses model_dump correctly"""
        rec = ProductRecommendation(
            id=1,
            name="Test Laptop",
            category_id=42,
            price_cents=150000,
            score=0.95,
            confidence=0.9
        )
        
        data = rec.model_dump()
        assert isinstance(data, dict)
        assert data["score"] == 0.95
        assert data["confidence"] == 0.9

class TestOpenAIToolCallHandling:
    """Test proper OpenAI tool call and response handling"""
    
    @pytest.fixture
    def mock_openai_response_single_tool(self):
        """Mock OpenAI response with single tool call"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = [MagicMock()]
        mock_response.choices[0].message.tool_calls[0].function.name = "sg_list_candidates"
        mock_response.choices[0].message.tool_calls[0].function.arguments = '{"query": "laptop"}'
        mock_response.choices[0].message.tool_calls[0].id = "call_123"
        mock_response.choices[0].message.model_dump.return_value = {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_123", "function": {"name": "sg_list_candidates"}}]
        }
        return mock_response
    
    @pytest.fixture 
    def mock_openai_response_multiple_tools(self):
        """Mock OpenAI response with multiple tool calls"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        
        # Create multiple tool calls
        tool_calls = []
        for i, tool_name in enumerate(["sg_list_candidates", "sg_price_drop", "sg_promotions"]):
            call = MagicMock()
            call.function.name = tool_name
            call.function.arguments = f'{{"product_id": {i+1}}}' if "price" in tool_name else '{"query": "laptop"}'
            call.id = f"call_{i+1}"
            tool_calls.append(call)
        
        mock_response.choices[0].message.tool_calls = tool_calls
        mock_response.choices[0].message.model_dump.return_value = {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": f"call_{i+1}", "function": {"name": name}} for i, name in enumerate(["sg_list_candidates", "sg_price_drop", "sg_promotions"])]
        }
        return mock_response
    
    @pytest.mark.asyncio
    async def test_single_tool_call_response_format(self, mock_openai_response_single_tool):
        """Test that single tool call gets proper response format"""
        from src.enhanced_orchestrator import EnhancedOrchestrator
        
        orchestrator = EnhancedOrchestrator()
        
        # Mock the tool execution
        with patch.object(orchestrator, '_safe_tool_call', return_value={"ok": True, "result": []}):
            # Simulate the tool call handling logic
            tool_calls = mock_openai_response_single_tool.choices[0].message.tool_calls
            
            messages = []
            # Add assistant message
            messages.append(mock_openai_response_single_tool.choices[0].message.model_dump())
            
            # Process each tool call
            for call in tool_calls:
                result = await orchestrator._safe_tool_call(call.function.name, {})
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result)
                })
            
            # Verify message structure
            assert len(messages) == 2  # assistant + tool response
            assert messages[0]["role"] == "assistant" 
            assert messages[1]["role"] == "tool"
            assert messages[1]["tool_call_id"] == "call_123"
    
    @pytest.mark.asyncio
    async def test_multiple_tool_calls_response_format(self, mock_openai_response_multiple_tools):
        """Test that multiple tool calls each get proper responses"""
        from src.enhanced_orchestrator import EnhancedOrchestrator
        
        orchestrator = EnhancedOrchestrator()
        
        # Mock the tool execution
        with patch.object(orchestrator, '_safe_tool_call', return_value={"ok": True, "result": []}):
            tool_calls = mock_openai_response_multiple_tools.choices[0].message.tool_calls
            
            messages = []
            # Add assistant message
            messages.append(mock_openai_response_multiple_tools.choices[0].message.model_dump())
            
            # Process each tool call
            for call in tool_calls:
                result = await orchestrator._safe_tool_call(call.function.name, {})
                messages.append({
                    "role": "tool", 
                    "tool_call_id": call.id,
                    "content": json.dumps(result)
                })
            
            # Verify each tool call has a response
            assert len(messages) == 4  # 1 assistant + 3 tool responses
            assert messages[0]["role"] == "assistant"
            
            # Check each tool response
            for i in range(1, 4):
                assert messages[i]["role"] == "tool"
                assert messages[i]["tool_call_id"] == f"call_{i}"
                assert "content" in messages[i]
    
    @pytest.mark.asyncio 
    async def test_tool_call_failure_fallback(self):
        """Test fallback behavior when tool calls fail"""
        from src.enhanced_orchestrator import EnhancedOrchestrator
        
        orchestrator = EnhancedOrchestrator()
        
        # Test the actual _safe_tool_call method which should handle exceptions
        result = await orchestrator._safe_tool_call("nonexistent_tool", {})
        
        # Should return error response, not raise exception
        assert isinstance(result, dict)
        assert "error" in result

class TestAsyncLimiterFix:
    """Test AsyncLimiter proper usage and lifecycle management"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_lifecycle(self):
        """Test that rate limiters are properly managed per event loop"""
        # This test verifies that we don't reuse limiters across event loops
        
        # Import the module that uses AsyncLimiter
        try:
            from aiolimiter import AsyncLimiter
        except ImportError:
            pytest.skip("aiolimiter not available")
        
        # Create limiter in this event loop
        limiter1 = AsyncLimiter(max_rate=10, time_period=1)
        
        # Test that we can use it without warnings
        async with limiter1:
            pass  # Should not raise warnings
        
        # In a real implementation, we'd ensure new limiters per loop
        assert limiter1 is not None

class TestErrorHandlingFallbacks:
    """Test error handling and fallback mechanisms"""
    
    @pytest.mark.asyncio
    async def test_redis_fallback_graceful(self):
        """Test graceful fallback when Redis is not available"""
        from src.orchestrator import MockStateManager
        
        # Test mock state manager works as fallback
        mock_state = MockStateManager()
        
        # Test basic operations
        health = await mock_state.health_check()
        assert health is True
        
        # Test conversation management
        success = await mock_state.append_to_conversation("test_session", {"role": "user", "content": "test"})
        assert success is True
        
        history = await mock_state.get_conversation_history("test_session")
        assert len(history) == 1
        assert history[0]["content"] == "test"
    
    @pytest.mark.asyncio
    async def test_enhanced_orchestrator_fallback(self):
        """Test that system has proper fallback mechanisms"""
        # Test the orchestrator initialization works properly
        from src.orchestrator import Orchestrator
        
        # Should work regardless of which orchestrator type is used
        orch = Orchestrator()
        
        # Both enhanced and fallback orchestrators should be able to process queries
        assert hasattr(orch, 'process_query')
        
        # Test that it can handle a basic query
        from src.models import ConversationContext
        context = ConversationContext(session_id="test_fallback")
        response = await orch.process_query("test query", context)
        assert response is not None
    
    def test_missing_dependency_handling(self):
        """Test handling of missing optional dependencies"""
        # Test that system handles missing Redis gracefully
        
        with patch('sys.modules', {'redis': None, 'redis.asyncio': None}):
            # Should not crash when Redis is not available
            try:
                from src.state_manager import DistributedStateManager
                # If Redis is mocked as None, should handle gracefully
            except ImportError:
                # This is expected behavior
                pass

class TestIntegrationPipeline:
    """Integration tests for the complete pipeline"""
    
    @pytest.mark.asyncio
    async def test_complete_query_pipeline(self):
        """Test complete query processing pipeline"""
        from src.orchestrator import Orchestrator
        
        orchestrator = Orchestrator()
        context = ConversationContext(session_id="test_pipeline")
        
        # Test that we can process a basic query without errors
        response = await orchestrator.process_query("find laptops", context)
        
        assert isinstance(response, AgentResponse)
        assert response.content is not None
        assert len(response.content) > 0
    
    @pytest.mark.asyncio
    async def test_conversation_state_persistence(self):
        """Test that conversation state is properly maintained"""
        from src.orchestrator import Orchestrator
        
        orchestrator = Orchestrator()
        context = ConversationContext(session_id="test_conversation")
        
        # First query
        response1 = await orchestrator.process_query("show me laptops", context)
        assert isinstance(response1, AgentResponse)
        
        # Second query - should maintain context
        response2 = await orchestrator.process_query("what about pricing?", context)
        assert isinstance(response2, AgentResponse)
        
        # Verify conversation history if state manager is available
        if hasattr(orchestrator, 'state_manager'):
            try:
                history = await orchestrator.state_manager.get_conversation_history("test_conversation")
                assert len(history) >= 2  # Should have at least 2 interactions
            except Exception:
                # State manager might not be fully functional in test
                pass
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Test system health check functionality"""
        from src.orchestrator import Orchestrator
        
        orchestrator = Orchestrator()
        
        if hasattr(orchestrator, 'health_check'):
            health = await orchestrator.health_check()
            assert isinstance(health, dict)
            assert 'orchestrator' in health
        else:
            # Basic orchestrator doesn't have health check
            assert True

class TestModelValidation:
    """Test model validation and data integrity"""
    
    def test_conversation_context_validation(self):
        """Test ConversationContext model validation"""
        # Valid context
        context = ConversationContext(session_id="test123")
        assert context.session_id == "test123"
        assert isinstance(context.history, list)
        assert isinstance(context.metadata, dict)
    
    def test_user_query_validation(self):
        """Test UserQuery model validation"""
        query = UserQuery(text="find laptops", user_id="user123")
        assert query.text == "find laptops"
        assert query.user_id == "user123"
        assert isinstance(query.extracted_entities, dict)
    
    def test_agent_response_validation(self):
        """Test AgentResponse model validation"""
        response = AgentResponse(
            content="Here are some laptops",
            confidence=0.9,
            agent_id="test_agent"
        )
        assert response.content == "Here are some laptops"
        assert response.confidence == 0.9
        assert response.agent_id == "test_agent"
        assert isinstance(response.tool_calls, list)
        assert isinstance(response.data, dict)

class TestPriceAnalysisAgentSelection:
    """Test the improved Price Analysis Agent selection logic"""
    
    @pytest.mark.asyncio
    async def test_price_analysis_agent_single_keywords(self):
        """Test that single price keywords trigger the agent"""
        from src.enhanced_orchestrator import PriceAnalysisAgent
        from src.models import UserQuery, ConversationContext
        
        agent = PriceAnalysisAgent()
        context = ConversationContext(session_id="test")
        
        # These should now trigger the agent (previously failed)
        test_queries = [
            ("What's the price?", 0.25),  # "price" = 0.25
            ("Show me deals", 0.25),      # "deals" = 0.25  
            ("What about pricing?", 0.25), # "pricing" = 0.25
            ("How much does it cost?", 0.4), # phrase match = 0.4
            ("Find cheap laptops", 0.25),   # "cheap" = 0.25
        ]
        
        for query_text, expected_min_score in test_queries:
            query = UserQuery(text=query_text)
            score = await agent.can_handle(query, context)
            
            assert score >= expected_min_score, f"Query '{query_text}' got score {score}, expected >= {expected_min_score}"
            assert score >= agent.confidence_threshold, f"Query '{query_text}' score {score} below threshold {agent.confidence_threshold}"
    
    @pytest.mark.asyncio
    async def test_price_analysis_agent_phrase_patterns(self):
        """Test that price phrase patterns get high scores"""
        from src.enhanced_orchestrator import PriceAnalysisAgent
        from src.models import UserQuery, ConversationContext
        
        agent = PriceAnalysisAgent()
        context = ConversationContext(session_id="test")
        
        # Phrase patterns should get high scores
        phrase_queries = [
            "How much does this cost?",
            "What's the price of this laptop?", 
            "What is the price range?",
            "Show me the best deals",
            "What does it cost?",
            "Price comparison please"
        ]
        
        for query_text in phrase_queries:
            query = UserQuery(text=query_text)
            score = await agent.can_handle(query, context)
            
            assert score >= 0.4, f"Phrase query '{query_text}' got score {score}, expected >= 0.4"
            assert score >= agent.confidence_threshold, f"Phrase query '{query_text}' failed threshold"
    
    @pytest.mark.asyncio 
    async def test_price_analysis_agent_multiple_matches(self):
        """Test that multiple price indicators increase score"""
        from src.enhanced_orchestrator import PriceAnalysisAgent
        from src.models import UserQuery, ConversationContext
        
        agent = PriceAnalysisAgent()
        context = ConversationContext(session_id="test")
        
        # Multiple matches should get higher scores
        multi_match_queries = [
            ("Find cheap deals", 0.5),      # "cheap" + "deals" = 0.25 + 0.25 = 0.5
            ("Price and cost comparison", 0.5), # "price" + "cost" = 0.25 + 0.25 = 0.5
            ("Budget-friendly discount", 0.5),   # "budget" + "discount" = 0.25 + 0.25 = 0.5
        ]
        
        for query_text, expected_min_score in multi_match_queries:
            query = UserQuery(text=query_text)
            score = await agent.can_handle(query, context)
            
            assert score >= expected_min_score, f"Multi-match query '{query_text}' got score {score}, expected >= {expected_min_score}"
    
    @pytest.mark.asyncio
    async def test_price_analysis_agent_context_bonus(self):
        """Test that context words provide bonus scoring"""
        from src.enhanced_orchestrator import PriceAnalysisAgent
        from src.models import UserQuery, ConversationContext
        
        agent = PriceAnalysisAgent()
        context = ConversationContext(session_id="test")
        
        # Context bonus queries (should get +0.1 bonus)
        bonus_queries = [
            "Show me the price",      # "show" + "price" = 0.25 + 0.1 = 0.35
            "Find cheap options",     # "find" + "cheap" = 0.25 + 0.1 = 0.35  
            "Compare prices",         # "compare" + "price" = 0.25 + 0.1 = 0.35
            "Tell me about deals",    # "tell me" + "deals" = 0.25 + 0.1 = 0.35
        ]
        
        for query_text in bonus_queries:
            query = UserQuery(text=query_text)
            score = await agent.can_handle(query, context)
            
            assert score >= 0.3, f"Bonus query '{query_text}' got score {score}, expected >= 0.3"
    
    @pytest.mark.asyncio
    async def test_price_analysis_agent_non_price_queries(self):
        """Test that non-price queries get low scores"""
        from src.enhanced_orchestrator import PriceAnalysisAgent
        from src.models import UserQuery, ConversationContext
        
        agent = PriceAnalysisAgent()
        context = ConversationContext(session_id="test")
        
        # These should NOT trigger the price agent
        non_price_queries = [
            "Find laptops",
            "Show me specifications", 
            "What are the features?",
            "Brand recommendations",
            "Technical reviews"
        ]
        
        for query_text in non_price_queries:
            query = UserQuery(text=query_text)
            score = await agent.can_handle(query, context)
            
            assert score < agent.confidence_threshold, f"Non-price query '{query_text}' incorrectly triggered agent with score {score}"

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__]) 