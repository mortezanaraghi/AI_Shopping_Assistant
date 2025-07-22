"""
Tool: sg_variants
Get variant information for products.
"""
from typing import Dict, Any
from src import shopgraph_api as sg

schema: Dict[str, Any] = {
    "name": "sg_variants",
    "description": "Get count and min‑price of all SKUs / variants for a product.",
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
    stats: Dict[str, Any] = await sg.get_variant_stats(product_id)
    return stats
