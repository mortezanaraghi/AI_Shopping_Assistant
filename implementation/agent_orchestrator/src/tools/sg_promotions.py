"""
Tool: sg_promotions
Get promotion information for products.
"""
from typing import Dict, Any, List
from src import shopgraph_api as sg
from src.models import Promotion

schema: Dict[str, Any] = {
    "name": "sg_promotions",
    "description": "List active promotions for a merchant with health scores.",
    "parameters": {
        "type": "object",
        "properties": {
            "merchant_id": {
                "type": "integer",
                "description": "Merchant (retailer) ID",
            }
        },
        "required": ["merchant_id"],
    },
}

async def run(merchant_id: int) -> List[Dict[str, Any]]:
    promos: List[Promotion] = await sg.get_promotions(merchant_id)
    return [p.dict() for p in promos]
