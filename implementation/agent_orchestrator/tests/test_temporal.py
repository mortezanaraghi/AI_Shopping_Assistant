#!/usr/bin/env python3
"""
Temporal.io Integration Tests
Tests for workflows, activities, and temporal orchestrator functionality.
"""
import asyncio
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Test imports
from src.models import ConversationContext, UserQuery, Product
from src.workflow_models import (
    ShoppingJourneyState, ShoppingJourneyStage, PriceMonitoringState,
    ProductDiscoveryInput, ProductDiscoveryOutput, UserDecisionSignal,
    WorkflowStatus
)

# Skip all tests if Temporal is not available
try:
    from src.temporal_orchestrator import TemporalOrchestrator
    from src.workflows import ShoppingJourneyWorkflow, PriceMonitoringWorkflow, QuickQueryWorkflow
    from src.activities import (
        product_discovery_activity, price_analysis_activity, 
        send_notification_activity, log_workflow_event_activity
    )
    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False

@pytest.mark.skipif(not TEMPORAL_AVAILABLE, reason="Temporal.io not available")
class TestTemporalWorkflowModels:
    """Test workflow models and data structures."""
    
    def test_shopping_journey_state_creation(self):
        """Test ShoppingJourneyState model creation and methods."""
        state = ShoppingJourneyState(
            user_id="test_user",
            session_id="test_session", 
            initial_query="find laptops"
        )
        
        assert state.user_id == "test_user"
        assert state.session_id == "test_session"
        assert state.initial_query == "find laptops"
        assert state.current_stage == ShoppingJourneyStage.DISCOVERY
        assert isinstance(state.products_considered, list)
        assert len(state.products_considered) == 0
        
        # Test duration calculation
        duration = state.duration
        assert isinstance(duration, timedelta)
        assert duration.total_seconds() >= 0
        
        # Test stale detection
        assert not state.is_stale  # Should not be stale immediately
    
    def test_price_monitoring_state_creation(self):
        """Test PriceMonitoringState model creation and properties."""
        state = PriceMonitoringState(
            user_id="test_user",
            product_ids=[1, 2, 3],
            target_price=500.0
        )
        
        assert state.user_id == "test_user"
        assert state.product_ids == [1, 2, 3]
        assert state.target_price == 500.0
        assert state.check_interval_hours == 6
        assert state.duration_days == 30
        
        # Test calculated properties
        end_time = state.monitoring_end_time
        next_check = state.next_check_time
        assert isinstance(end_time, datetime)
        assert isinstance(next_check, datetime)
    
    def test_user_decision_signal(self):
        """Test UserDecisionSignal model."""
        decision = UserDecisionSignal(
            decision_type="purchase",
            product_id=123,
            reasoning="Good price and features"
        )
        
        assert decision.decision_type == "purchase"
        assert decision.product_id == 123
        assert decision.reasoning == "Good price and features"

@pytest.mark.skipif(not TEMPORAL_AVAILABLE, reason="Temporal.io not available")
class TestTemporalActivities:
    """Test Temporal activities with mocked dependencies."""
    
    @pytest.mark.asyncio
    async def test_product_discovery_activity(self):
        """Test product discovery activity."""
        with patch('src.activities.sg_list_candidates') as mock_sg:
            # Mock product data with all required fields
            mock_products = [
                {"id": 1, "name": "Test Laptop", "price_cents": 100000, "specs": {}, "category_id": 1},
                {"id": 2, "name": "Another Laptop", "price_cents": 150000, "specs": {}, "category_id": 1}
            ]
            mock_sg.run = AsyncMock(return_value=mock_products)
            
            # Test input
            input_data = ProductDiscoveryInput(
                query="gaming laptops",
                max_results=10
            )
            
            # Execute activity
            result = await product_discovery_activity(input_data)
            
            # Verify results
            assert isinstance(result, ProductDiscoveryOutput)
            assert len(result.products) == 2
            assert result.confidence_score > 0
            assert "gaming laptops" in result.search_metadata["original_query"]
            
            # Verify products are properly converted
            for product in result.products:
                assert isinstance(product, Product)
                assert hasattr(product, "id")
                assert hasattr(product, "name")
                assert hasattr(product, "price_cents")
    
    @pytest.mark.asyncio
    async def test_product_discovery_with_budget_filter(self):
        """Test product discovery with budget filtering."""
        with patch('src.activities.sg_list_candidates') as mock_sg:
            mock_products = [
                {"id": 1, "name": "Cheap Laptop", "price_cents": 50000, "specs": {}, "category_id": 1},
                {"id": 2, "name": "Expensive Laptop", "price_cents": 200000, "specs": {}, "category_id": 1}
            ]
            mock_sg.run = AsyncMock(return_value=mock_products)
            
            # Test with budget range $800-$1200
            input_data = ProductDiscoveryInput(
                query="laptops",
                budget_range=(800.0, 1200.0),
                max_results=10
            )
            
            result = await product_discovery_activity(input_data)
            
            # Should filter out products outside budget range
            assert len(result.products) == 0  # Both products are outside $800-$1200 range
            assert result.search_metadata["budget_applied"] is True
    
    @pytest.mark.asyncio 
    async def test_notification_activity(self):
        """Test notification sending activity."""
        from src.workflow_models import NotificationInput, NotificationOutput
        
        notification_input = NotificationInput(
            user_id="test_user",
            notification_type="price_alert",
            message="Test notification",
            urgency="high"
        )
        
        result = await send_notification_activity(notification_input)
        
        assert isinstance(result, NotificationOutput)
        assert result.success is True
        assert result.notification_id.startswith("notif_")
        assert result.delivered_at is not None
    
    @pytest.mark.asyncio
    async def test_log_workflow_event_activity(self):
        """Test workflow event logging activity."""
        result = await log_workflow_event_activity(
            "test-workflow-123",
            "test_event",
            {"key": "value", "timestamp": "2024-01-01T12:00:00"}
        )
        
        assert result is True

@pytest.mark.skipif(not TEMPORAL_AVAILABLE, reason="Temporal.io not available")
class TestTemporalOrchestrator:
    """Test TemporalOrchestrator functionality."""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator creation and configuration."""
        orchestrator = TemporalOrchestrator()
        
        assert orchestrator.temporal_address == "localhost:7233"
        assert orchestrator.task_queue == "shopping-assistant"
        assert orchestrator.client is None  # Not connected yet
        assert orchestrator.worker is None
        assert isinstance(orchestrator.active_workflows, dict)
        assert len(orchestrator.active_workflows) == 0
        
        # Test fallback orchestrator is available
        assert orchestrator.fallback_orchestrator is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_health_check_without_temporal(self):
        """Test health check when Temporal is not connected."""
        orchestrator = TemporalOrchestrator()
        
        # Health check should work even without Temporal connection
        with patch.object(orchestrator.fallback_orchestrator, 'health_check') as mock_health:
            mock_health.return_value = {
                "orchestrator": "healthy",
                "agents_registered": 2,
                "legacy_tools": 8
            }
            
            health = await orchestrator.health_check()
            
            assert health["temporal_connected"] is False
            assert health["worker_running"] is False
            assert health["active_workflows"] == 0
            assert health["task_queue"] == "shopping-assistant"
    
    @pytest.mark.asyncio
    async def test_orchestrator_fallback_processing(self):
        """Test that orchestrator falls back to enhanced orchestrator when Temporal unavailable."""
        orchestrator = TemporalOrchestrator()
        context = ConversationContext(session_id="test")
        
        # Mock the fallback orchestrator
        with patch.object(orchestrator.fallback_orchestrator, 'process_query') as mock_process:
            mock_response = MagicMock()
            mock_response.content = "Test response from fallback"
            mock_response.agent_id = "fallback_agent"
            mock_process.return_value = mock_response
            
            result = await orchestrator.process_query("test query", context)
            
            assert result.content == "Test response from fallback"
            assert result.agent_id == "fallback_agent"
            mock_process.assert_called_once_with("test query", context)
    
    def test_workflow_type_determination(self):
        """Test automatic workflow type determination."""
        orchestrator = TemporalOrchestrator()
        context = ConversationContext(session_id="test")
        
        # Test journey triggers
        assert orchestrator._determine_workflow_type("help me choose between options", context) == "journey"
        assert orchestrator._determine_workflow_type("I need a comprehensive analysis", context) == "journey"
        assert orchestrator._determine_workflow_type("compare laptops vs desktops", context) == "journey"
        
        # Test monitoring triggers  
        assert orchestrator._determine_workflow_type("monitor price for this laptop", context) == "monitor"
        assert orchestrator._determine_workflow_type("alert me when price drops", context) == "monitor"
        assert orchestrator._determine_workflow_type("watch for deals", context) == "monitor"
        
        # Test quick queries
        assert orchestrator._determine_workflow_type("find laptops", context) == "quick"
        assert orchestrator._determine_workflow_type("what's the weather", context) == "quick"

@pytest.mark.skipif(not TEMPORAL_AVAILABLE, reason="Temporal.io not available")  
class TestWorkflowIntegration:
    """Integration tests for workflow functionality."""
    
    @pytest.mark.asyncio
    async def test_shopping_journey_state_transitions(self):
        """Test shopping journey stage transitions."""
        # Test journey state without creating actual workflow instance
        journey_state = ShoppingJourneyState(
            user_id="test_user",
            session_id="test_session",
            initial_query="find gaming laptops"
        )
        
        # Test stage progression
        assert journey_state.current_stage == ShoppingJourneyStage.DISCOVERY
        
        # Simulate stage transitions
        journey_state.current_stage = ShoppingJourneyStage.ANALYSIS
        assert journey_state.current_stage == ShoppingJourneyStage.ANALYSIS
        
        journey_state.current_stage = ShoppingJourneyStage.COMPARISON
        assert journey_state.current_stage == ShoppingJourneyStage.COMPARISON
        
        journey_state.current_stage = ShoppingJourneyStage.DECISION_SUPPORT
        assert journey_state.current_stage == ShoppingJourneyStage.DECISION_SUPPORT
    
    @pytest.mark.asyncio
    async def test_price_monitoring_workflow_logic(self):
        """Test price monitoring workflow calculations."""
        # Create monitoring state
        state = PriceMonitoringState(
            user_id="test_user",
            product_ids=[1, 2],
            target_price=1000.0,
            check_interval_hours=1,
            duration_days=1
        )
        
        # Test initial state
        assert len(state.current_prices) == 0
        assert len(state.price_history) == 0
        
        # Simulate price updates
        state.current_prices[1] = 950.0  # Below target
        state.current_prices[2] = 1100.0  # Above target
        
        # Test price history tracking with proper timestamps
        state.price_history[1] = [
            {"price": 1000.0, "timestamp": "2024-01-01T10:00:00"},
            {"price": 950.0, "timestamp": "2024-01-01T11:00:00"}
        ]
        
        assert len(state.price_history[1]) == 2
        
        # Test monitoring end time calculation
        end_time = state.monitoring_end_time
        assert isinstance(end_time, datetime)

@pytest.mark.skipif(not TEMPORAL_AVAILABLE, reason="Temporal.io not available")
class TestWorkflowErrorHandling:
    """Test error handling and resilience in workflows."""
    
    @pytest.mark.asyncio
    async def test_activity_error_handling(self):
        """Test activity error handling and retries."""
        with patch('src.activities.sg_list_candidates') as mock_sg:
            # Mock failure followed by success
            mock_sg.run = AsyncMock(side_effect=[
                Exception("Network error"),  # First call fails
                [{"id": 1, "name": "Test", "price_cents": 100000, "specs": {}, "category_id": 1}]  # Second call succeeds
            ])
            
            input_data = ProductDiscoveryInput(query="test", max_results=5)
            
            # First call should raise exception
            with pytest.raises(Exception):
                await product_discovery_activity(input_data)
    
    @pytest.mark.asyncio
    async def test_orchestrator_error_recovery(self):
        """Test orchestrator error recovery and fallback."""
        orchestrator = TemporalOrchestrator()
        context = ConversationContext(session_id="test")
        
        # Mock successful fallback after Temporal failure
        with patch.object(orchestrator.fallback_orchestrator, 'process_query') as mock_fallback:
            mock_response = MagicMock()
            mock_response.content = "Fallback response"
            mock_response.agent_id = "fallback"
            mock_response.confidence = 0.8
            mock_fallback.return_value = mock_response
            
            # Process query when Temporal is not connected
            result = await orchestrator.process_query("test query", context)
            
            assert result.content == "Fallback response"
            assert result.agent_id == "fallback"
            mock_fallback.assert_called_once()

@pytest.mark.skipif(not TEMPORAL_AVAILABLE, reason="Temporal.io not available")
class TestWorkflowPerformance:
    """Performance and scalability tests."""
    
    @pytest.mark.asyncio
    async def test_concurrent_activity_execution(self):
        """Test concurrent execution of multiple activities."""
        import time
        
        # Create multiple notification tasks
        tasks = []
        start_time = time.time()
        
        for i in range(5):
            from src.workflow_models import NotificationInput
            notification = NotificationInput(
                user_id=f"user_{i}",
                notification_type="test",
                message=f"Test notification {i}"
            )
            task = send_notification_activity(notification)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Verify all succeeded
        assert len(results) == 5
        for result in results:
            assert result.success is True
        
        # Should complete much faster than sequential execution
        total_time = end_time - start_time
        assert total_time < 10.0  # Should complete within 10 seconds
    
    def test_workflow_state_memory_usage(self):
        """Test memory efficiency of workflow state objects."""
        import sys
        
        # Create a large journey state
        state = ShoppingJourneyState(
            user_id="test_user",
            session_id="test_session",
            initial_query="find products"
        )
        
        # Add many products with all required fields
        for i in range(100):
            product = Product(
                id=i,
                name=f"Product {i}",
                price_cents=i * 1000,
                specs={"feature": f"value_{i}"},
                category_id=1  # Add required field
            )
            state.products_considered.append(product)
        
        # Memory usage should be reasonable
        state_size = sys.getsizeof(state)
        assert state_size < 50000  # Less than 50KB for 100 products

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 