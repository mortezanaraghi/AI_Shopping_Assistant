"""
Tests for SmartTerminationAnalyzer
"""
import pytest
from src.smart_termination_analyzer import SmartTerminationAnalyzer
from src.react_models import ReActState, ReasoningResult


class TestSmartTerminationAnalyzer:
    """Test cases for SmartTerminationAnalyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = SmartTerminationAnalyzer(
            max_iterations=5,
            max_clarifications=2,
            max_failures=3
        )
    
    def test_initialization(self):
        """Test that the analyzer initializes with correct parameters."""
        assert self.analyzer.max_iterations == 5
        assert self.analyzer.max_clarifications == 2
        assert self.analyzer.max_failures == 3
    
    def test_should_terminate_max_iterations(self):
        """Test termination when max iterations is reached."""
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[],
            current_iteration=5,  # At max
            session_id="test_session"
        )
        
        reasoning_result = ReasoningResult(
            thought="test",
            action_type="use_tool",
            confidence=0.5
        )
        
        should_terminate, reason = self.analyzer.should_terminate(react_state, reasoning_result)
        assert should_terminate is True
        assert "Maximum iterations reached" in reason
    
    def test_should_terminate_excessive_clarifications(self):
        """Test termination when too many clarifications are requested."""
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[
                {"action": "clarification", "success": True},
                {"action": "clarification", "success": True},
                {"action": "clarification", "success": True},  # 3 clarifications
            ],
            current_iteration=1,
            session_id="test_session"
        )
        
        reasoning_result = ReasoningResult(
            thought="test",
            action_type="ask_clarification",
            confidence=0.5
        )
        
        should_terminate, reason = self.analyzer.should_terminate(react_state, reasoning_result)
        assert should_terminate is True
        assert "Too many clarifications requested" in reason
    
    def test_should_terminate_tool_failures(self):
        """Test termination when too many tool failures occur."""
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[
                {"success": False, "tool_name": "tool1"},
                {"success": False, "tool_name": "tool2"},
                {"success": False, "tool_name": "tool3"},
                {"success": False, "tool_name": "tool4"},  # 4 failures
            ],
            current_iteration=1,
            session_id="test_session"
        )
        
        reasoning_result = ReasoningResult(
            thought="test",
            action_type="use_tool",
            confidence=0.5
        )
        
        should_terminate, reason = self.analyzer.should_terminate(react_state, reasoning_result)
        assert should_terminate is True
        assert "Too many tool failures" in reason
    
    def test_should_terminate_high_confidence_with_products(self):
        """Test termination when high confidence and product results are found."""
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[
                {
                    "success": True,
                    "tool_name": "sg_list_candidates",
                    "result": "Found 5 laptops under $1000"
                }
            ],
            current_iteration=1,
            session_id="test_session"
        )
        
        reasoning_result = ReasoningResult(
            thought="test",
            action_type="final_answer",
            confidence=0.8  # High confidence
        )
        
        should_terminate, reason = self.analyzer.should_terminate(react_state, reasoning_result)
        assert should_terminate is True
        assert "Sufficient product results found with high confidence" in reason
    
    def test_should_terminate_reasonable_confidence_with_products(self):
        """Test termination when reasonable confidence and product results are found."""
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[
                {
                    "success": True,
                    "tool_name": "sg_list_candidates",
                    "result": "Found 3 laptops"
                }
            ],
            current_iteration=1,
            session_id="test_session"
        )
        
        reasoning_result = ReasoningResult(
            thought="test",
            action_type="final_answer",
            confidence=0.6  # Reasonable confidence
        )
        
        should_terminate, reason = self.analyzer.should_terminate(react_state, reasoning_result)
        assert should_terminate is True
        assert "Sufficient results found with reasonable confidence" in reason
    
    def test_should_terminate_stuck_in_loop(self):
        """Test termination when stuck in a repetitive loop."""
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[
                {"tool_name": "sg_list_candidates", "success": True},
                {"tool_name": "sg_list_candidates", "success": True},
                {"tool_name": "sg_list_candidates", "success": True},  # Same tool 3 times
            ],
            current_iteration=1,
            session_id="test_session"
        )
        
        reasoning_result = ReasoningResult(
            thought="test",
            action_type="use_tool",
            confidence=0.5
        )
        
        should_terminate, reason = self.analyzer.should_terminate(react_state, reasoning_result)
        assert should_terminate is True
        assert "Detected repetitive tool usage pattern" in reason
    
    def test_should_not_terminate_normal_operation(self):
        """Test that normal operation doesn't trigger termination."""
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[
                {"tool_name": "sg_list_candidates", "success": True}
            ],
            current_iteration=1,
            session_id="test_session"
        )
        
        reasoning_result = ReasoningResult(
            thought="test",
            action_type="use_tool",
            confidence=0.5
        )
        
        should_terminate, reason = self.analyzer.should_terminate(react_state, reasoning_result)
        assert should_terminate is False
        assert reason == "Continue"
    
    def test_has_product_results(self):
        """Test product result detection."""
        # Test with product results
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[
                {
                    "success": True,
                    "tool_name": "sg_list_candidates",
                    "result": "Found 5 laptops under $1000"
                }
            ],
            current_iteration=1,
            session_id="test_session"
        )
        
        has_products = self.analyzer._has_product_results(react_state)
        assert has_products is True
        
        # Test without product results
        react_state.tool_execution_history = [
            {
                "success": True,
                "tool_name": "sg_price_drop",
                "result": "Price check completed"
            }
        ]
        
        has_products = self.analyzer._has_product_results(react_state)
        assert has_products is False
    
    def test_count_clarifications(self):
        """Test clarification counting."""
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[
                {"action": "clarification", "success": True},
                {"action": "use_tool", "success": True},
                {"action": "clarification", "success": True},
            ],
            current_iteration=1,
            session_id="test_session"
        )
        
        count = self.analyzer._count_clarifications(react_state)
        assert count == 2
    
    def test_count_failed_tools(self):
        """Test failed tool counting."""
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[
                {"success": True, "tool_name": "tool1"},
                {"success": False, "tool_name": "tool2"},
                {"success": True, "tool_name": "tool3"},
                {"success": False, "tool_name": "tool4"},
            ],
            current_iteration=1,
            session_id="test_session"
        )
        
        count = self.analyzer._count_failed_tools(react_state)
        assert count == 2
    
    def test_is_stuck_in_loop(self):
        """Test loop detection."""
        # Test stuck in loop
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[
                {"tool_name": "sg_list_candidates", "success": True},
                {"tool_name": "sg_list_candidates", "success": True},
                {"tool_name": "sg_list_candidates", "success": True},
            ],
            current_iteration=1,
            session_id="test_session"
        )
        
        is_stuck = self.analyzer._is_stuck_in_loop(react_state)
        assert is_stuck is True
        
        # Test not stuck in loop
        react_state.tool_execution_history = [
            {"tool_name": "sg_list_candidates", "success": True},
            {"tool_name": "sg_price_drop", "success": True},
            {"tool_name": "sg_list_candidates", "success": True},
        ]
        
        is_stuck = self.analyzer._is_stuck_in_loop(react_state)
        assert is_stuck is False
    
    def test_get_termination_reason(self):
        """Test getting termination reasons."""
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[],
            current_iteration=5,  # At max
            session_id="test_session"
        )
        
        reason = self.analyzer.get_termination_reason(react_state)
        assert "Reached maximum iterations" in reason
    
    def test_get_state_summary(self):
        """Test getting state summary."""
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[
                {"success": True, "tool_name": "tool1"},
                {"success": False, "tool_name": "tool2"},
                {"action": "clarification", "success": True},
            ],
            current_iteration=2,
            session_id="test_session"
        )
        
        summary = self.analyzer.get_state_summary(react_state)
        
        assert summary["iteration"] == 2
        assert summary["max_iterations"] == 5
        assert summary["successful_tools"] == 2  # Fixed: 2 successful tools (tool1 and clarification)
        assert summary["failed_tools"] == 1
        assert summary["clarifications"] == 1
        assert summary["total_actions"] == 3
        assert "has_products" in summary
        assert "stuck_in_loop" in summary


class TestSmartTerminationAnalyzerEdgeCases:
    """Test edge cases for SmartTerminationAnalyzer."""
    
    def test_empty_tool_history(self):
        """Test behavior with empty tool history."""
        analyzer = SmartTerminationAnalyzer()
        react_state = ReActState(
            original_query="test query",
            conversation_history=[],
            user_profile=None,
            tool_execution_history=[],
            current_iteration=0,
            session_id="test_session"
        )
        
        reasoning_result = ReasoningResult(
            thought="test",
            action_type="use_tool",
            confidence=0.5
        )
        
        should_terminate, reason = analyzer.should_terminate(react_state, reasoning_result)
        assert should_terminate is False
        assert reason == "Continue"
    
    def test_custom_limits(self):
        """Test custom limit configuration."""
        analyzer = SmartTerminationAnalyzer(
            max_iterations=10,
            max_clarifications=5,
            max_failures=7
        )
        
        assert analyzer.max_iterations == 10
        assert analyzer.max_clarifications == 5
        assert analyzer.max_failures == 7 