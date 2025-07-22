"""
Tool: sg_category
Get category information for products.
"""
from typing import Dict, Any, List
from src import shopgraph_api as sg

schema: Dict[str, Any] = {
    "name": "sg_category",
    "description": "Resolve full ancestor path for a category (for breadcrumbs or similarity).",
    "parameters": {
        "type": "object",
        "properties": {
            "category_id": {
                "type": "integer",
                "description": "Leaf category ID",
            }
        },
        "required": ["category_id"],
    },
}

async def run(category_id: int) -> List[int]:
    path: List[int] = await sg.get_category_path(category_id)
    return path
