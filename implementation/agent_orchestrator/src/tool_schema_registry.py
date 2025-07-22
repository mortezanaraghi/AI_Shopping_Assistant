"""
Tool Schema Registry
Centralized tool schema management with validation for the ReAct orchestrator.
"""
from __future__ import annotations
from typing import Dict, Any, Tuple, Optional
from .utils.logging import init_logger
from .config import get_settings

settings = get_settings()
log = init_logger(settings.log_level)

class ToolSchemaRegistry:
    """Centralized tool schema management with validation."""
    
    def __init__(self):
        self.tool_schemas = {
            "sg_list_candidates": {
                "description": "Search for products based on query",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                },
                "examples": [
                    {"query": "gaming laptops"},
                    {"query": "wireless headphones under $200"}
                ]
            },
            "sg_price_drop": {
                "description": "Check for price drops on specific products",
                "parameters": {
                    "type": "object", 
                    "properties": {"product_id": {"type": "integer"}},
                    "required": ["product_id"]
                },
                "examples": [
                    {"product_id": 123}
                ]
            },
            "sg_promotions": {
                "description": "Get promotions for a merchant",
                "parameters": {
                    "type": "object",
                    "properties": {"merchant_id": {"type": "integer"}},
                    "required": ["merchant_id"]
                },
                "examples": [
                    {"merchant_id": 456}
                ]
            },
            "sg_variants": {
                "description": "Get variant statistics for a product",
                "parameters": {
                    "type": "object",
                    "properties": {"product_id": {"type": "integer"}},
                    "required": ["product_id"]
                },
                "examples": [
                    {"product_id": 123}
                ]
            },
            "sg_criteria": {
                "description": "Get criteria scores for a product",
                "parameters": {
                    "type": "object",
                    "properties": {"product_id": {"type": "integer"}},
                    "required": ["product_id"]
                },
                "examples": [
                    {"product_id": 123}
                ]
            },
            "sg_category": {
                "description": "Get category path for a category ID",
                "parameters": {
                    "type": "object",
                    "properties": {"cat_id": {"type": "integer"}},
                    "required": ["cat_id"]
                },
                "examples": [
                    {"cat_id": 42}
                ]
            }
        }
        
        # Add codegen tools if available
        try:
            self.tool_schemas.update({
                "codegen_fast": {
                    "description": "Fast code generation for simple queries",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    },
                    "examples": [
                        {"query": "create a simple function"}
                    ]
                },
                "codegen_slow": {
                    "description": "Comprehensive code generation for complex queries",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    },
                    "examples": [
                        {"query": "build a complete web application"}
                    ]
                }
            })
        except ImportError:
            pass
    
    def validate_arguments(self, tool_name: str, args: dict) -> Tuple[bool, str]:
        """Validate tool arguments against schema."""
        if tool_name not in self.tool_schemas:
            return False, f"Unknown tool: {tool_name}"
        
        schema = self.tool_schemas[tool_name]
        required = schema["parameters"].get("required", [])
        
        for param in required:
            if param not in args:
                return False, f"Missing required parameter '{param}'"
        
        return True, "Valid"
    
    def get_tool_description(self, tool_name: str) -> str:
        """Get formatted tool description for prompts."""
        if tool_name not in self.tool_schemas:
            return f"- {tool_name}: Unknown tool"
        
        schema = self.tool_schemas[tool_name]
        params = schema["parameters"]["properties"]
        required = schema["parameters"].get("required", [])
        
        param_desc = ", ".join([f"{k}: {v['type']}" for k, v in params.items()])
        return f"- {tool_name}: {schema['description']} (Params: {param_desc})"
    
    def get_tool_examples(self, tool_name: str) -> list:
        """Get example arguments for a tool."""
        if tool_name not in self.tool_schemas:
            return []
        
        return self.tool_schemas[tool_name].get("examples", [])
    
    def list_available_tools(self) -> list:
        """Get list of all available tool names."""
        return list(self.tool_schemas.keys())
    
    def get_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get the complete schema for a tool."""
        return self.tool_schemas.get(tool_name) 