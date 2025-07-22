"""
Tool: sg_list_candidates
Search for products based on user requirements.
"""
from src.models import UserRequirements, Product
from src import shopgraph_api as sg

schema = {
    "name": "sg_list_candidates",
    "description": "ShopGraph search returning rough price & category",
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
}

async def run(query: str) -> list[dict]:
    prods = await sg.search_products(query)
    return [p.model_dump() for p in prods]

 