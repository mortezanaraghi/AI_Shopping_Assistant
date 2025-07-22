"""
Tool: sg_criteria
Get criteria scores for products.
"""
from typing import Dict, Any, List
from src import shopgraph_api as sg
from src.models import CriteriaScore

schema: Dict[str, Any] = {
    "name": "sg_criteria",
    "description": "Get structured quality scores (criteria answers) for a product.",
    "parameters": {
        "type": "object",
        "properties": {
            "product_id": {
                "type": "integer",
                "description": "Product entity ID",
            }
        },
        "required": ["product_id"],
    },
}

async def run(product_id: int) -> List[Dict[str, Any]]:
    criteria: List[CriteriaScore] = await sg.get_criteria_scores(product_id)
    return [c.dict() for c in criteria]
