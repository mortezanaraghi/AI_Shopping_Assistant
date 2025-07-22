"""
Tool: sg_price_drop
Get price drop information for products.
"""
from typing import Dict, Any, List
from src import shopgraph_api as sg
from src.models import PriceDrop

schema: Dict[str, Any] = {
    "name": "sg_price_drop",
    "description": "Get 7‑day price‑drop and attractiveness score for a product.",
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

async def run(product_id: int) -> Dict[str, Any]:
    drop: PriceDrop | None = await sg.get_price_drop(product_id)
    return drop.model_dump() if drop else {"percent_drop_7d": 0, "attractiveness": 0}
