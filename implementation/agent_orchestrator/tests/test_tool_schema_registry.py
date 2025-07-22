"""
Tests for ToolSchemaRegistry
"""
import pytest
from src.tool_schema_registry import ToolSchemaRegistry


class TestToolSchemaRegistry:
    """Test cases for ToolSchemaRegistry."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.registry = ToolSchemaRegistry()
    
    def test_initialization(self):
        """Test that the registry initializes with expected tools."""
        assert self.registry is not None
        assert hasattr(self.registry, 'tool_schemas')
        assert isinstance(self.registry.tool_schemas, dict)
        
        # Check that core tools are present
        expected_tools = [
            "sg_list_candidates", "sg_price_drop", "sg_promotions",
            "sg_variants", "sg_criteria", "sg_category"
        ]
        
        for tool in expected_tools:
            assert tool in self.registry.tool_schemas
    
    def test_list_available_tools(self):
        """Test listing available tools."""
        tools = self.registry.list_available_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 6  # At least the core tools
        
        # Check that all tools are strings
        for tool in tools:
            assert isinstance(tool, str)
    
    def test_validate_arguments_valid(self):
        """Test argument validation with valid arguments."""
        # Test sg_list_candidates with valid args
        is_valid, msg = self.registry.validate_arguments(
            "sg_list_candidates", {"query": "laptops"}
        )
        assert is_valid is True
        assert msg == "Valid"
        
        # Test sg_price_drop with valid args
        is_valid, msg = self.registry.validate_arguments(
            "sg_price_drop", {"product_id": 123}
        )
        assert is_valid is True
        assert msg == "Valid"
        
        # Test sg_promotions with valid args
        is_valid, msg = self.registry.validate_arguments(
            "sg_promotions", {"merchant_id": 456}
        )
        assert is_valid is True
        assert msg == "Valid"
    
    def test_validate_arguments_invalid(self):
        """Test argument validation with invalid arguments."""
        # Test missing required parameter
        is_valid, msg = self.registry.validate_arguments(
            "sg_list_candidates", {"price_limit": 1000}
        )
        assert is_valid is False
        assert "Missing required parameter 'query'" in msg
        
        # Test unknown tool
        is_valid, msg = self.registry.validate_arguments(
            "unknown_tool", {"query": "test"}
        )
        assert is_valid is False
        assert "Unknown tool: unknown_tool" in msg
        
        # Test empty arguments
        is_valid, msg = self.registry.validate_arguments(
            "sg_list_candidates", {}
        )
        assert is_valid is False
        assert "Missing required parameter 'query'" in msg
    
    def test_get_tool_description(self):
        """Test getting tool descriptions."""
        # Test valid tool
        desc = self.registry.get_tool_description("sg_list_candidates")
        assert isinstance(desc, str)
        assert "sg_list_candidates" in desc
        assert "Search for products" in desc
        assert "query: string" in desc
        
        # Test unknown tool
        desc = self.registry.get_tool_description("unknown_tool")
        assert "Unknown tool" in desc
    
    def test_get_tool_examples(self):
        """Test getting tool examples."""
        # Test valid tool
        examples = self.registry.get_tool_examples("sg_list_candidates")
        assert isinstance(examples, list)
        assert len(examples) > 0
        
        # Check example structure
        for example in examples:
            assert isinstance(example, dict)
            assert "query" in example
        
        # Test unknown tool
        examples = self.registry.get_tool_examples("unknown_tool")
        assert examples == []
    
    def test_get_schema(self):
        """Test getting complete tool schema."""
        # Test valid tool
        schema = self.registry.get_schema("sg_list_candidates")
        assert isinstance(schema, dict)
        assert "description" in schema
        assert "parameters" in schema
        assert "examples" in schema
        
        # Test unknown tool
        schema = self.registry.get_schema("unknown_tool")
        assert schema is None
    
    def test_schema_structure(self):
        """Test that all tool schemas have the expected structure."""
        for tool_name, schema in self.registry.tool_schemas.items():
            assert "description" in schema
            assert "parameters" in schema
            assert "examples" in schema
            
            # Check parameters structure
            params = schema["parameters"]
            assert "type" in params
            assert "properties" in params
            assert "required" in params
            
            # Check that required parameters exist in properties
            required = params.get("required", [])
            properties = params.get("properties", {})
            for param in required:
                assert param in properties
    
    def test_codegen_tools_availability(self):
        """Test that codegen tools are handled gracefully."""
        # The registry should handle codegen tools if available
        # This test ensures the try/except block works
        tools = self.registry.list_available_tools()
        
        # Should have at least the core tools
        core_tools = [
            "sg_list_candidates", "sg_price_drop", "sg_promotions",
            "sg_variants", "sg_criteria", "sg_category"
        ]
        
        for tool in core_tools:
            assert tool in tools


class TestToolSchemaRegistryIntegration:
    """Integration tests for ToolSchemaRegistry."""
    
    def test_full_validation_workflow(self):
        """Test a complete validation workflow."""
        registry = ToolSchemaRegistry()
        
        # Test multiple tools in sequence
        test_cases = [
            ("sg_list_candidates", {"query": "gaming laptops"}, True),
            ("sg_price_drop", {"product_id": 123}, True),
            ("sg_promotions", {"merchant_id": 456}, True),
            ("sg_variants", {"product_id": 789}, True),
            ("sg_criteria", {"product_id": 101}, True),
            ("sg_category", {"cat_id": 42}, True),
        ]
        
        for tool_name, args, expected_valid in test_cases:
            is_valid, msg = registry.validate_arguments(tool_name, args)
            assert is_valid == expected_valid, f"Failed for {tool_name}: {msg}"
    
    def test_error_messages_are_helpful(self):
        """Test that error messages provide useful information."""
        registry = ToolSchemaRegistry()
        
        # Test missing parameter
        is_valid, msg = registry.validate_arguments("sg_list_candidates", {})
        assert not is_valid
        assert "Missing required parameter 'query'" in msg
        
        # Test unknown tool
        is_valid, msg = registry.validate_arguments("nonexistent_tool", {"query": "test"})
        assert not is_valid
        assert "Unknown tool: nonexistent_tool" in msg 