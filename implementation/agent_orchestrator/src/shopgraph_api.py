"""
ShopGraph API Client
Provides access to the ShopGraph product database and search functionality.
"""
from __future__ import annotations
import asyncio
import json
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from .config import get_settings
from .utils.logging import init_logger
from aiolimiter import AsyncLimiter
from .models import *

settings = get_settings()

# Rate limiter per event loop to avoid reuse warnings
_limiters = {}

def _get_rate_limiter() -> AsyncLimiter:
    """Get or create a rate limiter for the current event loop."""
    try:
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
        
        if loop_id not in _limiters:
            _limiters[loop_id] = AsyncLimiter(300, 1)  # 300 requests/s per key
        
        return _limiters[loop_id]
    except RuntimeError:
        # No event loop running, create a temporary one
        return AsyncLimiter(300, 1)

# ------ helper to mock latency --------------------------------------------------------
async def _sim_network(lat: float = 0.05):
    await asyncio.sleep(lat * random.uniform(0.8, 1.2))

# ------ Search / list ------------------------------------------------------------
async def search_products(query: str) -> List[Product]:
    rate_limiter = _get_rate_limiter()
    async with rate_limiter:
        await _sim_network()
        return [
            Product(id=i, name=f"{query.title()} Model {i}", category_id=42,
                    price_cents=999_99 + i*20_00)
            for i in range(1, 11)
        ]

# ------ Price Drops ----------------------------------------------------------------
async def get_price_drop(product_id: int) -> PriceDrop | None:
    async with _get_rate_limiter():
        await _sim_network(0.02)
        if random.random() < 0.6:
            return PriceDrop(percent_drop_7d=random.uniform(0.05, 0.3),
                             attractiveness=random.uniform(6, 9))
        return None

# ------ Promotions ----------------------------------------------------------------
async def get_promotions(merchant_id: int) -> List[Promotion]:
    async with _get_rate_limiter():
        await _sim_network(0.02)
        return [
            Promotion(id="SAVE20", percent_off=20.0, amount_off=None,
                      health=95, is_storewide=True)
        ]

# ------ Variants stats ----------------------------------------------------------
async def get_variant_stats(product_id: int) -> Dict[str, Any]:
    async with _get_rate_limiter():
        await _sim_network(0.03)
        return {"count": random.randint(3, 12),
                "min_price": 899_99}

# ------ Criteria answers --------------------------------------------------------
async def get_criteria_scores(product_id: int) -> List[CriteriaScore]:
    async with _get_rate_limiter():
        await _sim_network(0.04)
        return [
            CriteriaScore(criteria_id=1, rating=random.uniform(4, 5),
                          response_type="yes"),
            CriteriaScore(criteria_id=2, rating=random.uniform(3, 4.5),
                          response_type="yes"),
        ]

# ------ Merchant ----------------------------------------------------------------
async def get_merchant(merchant_id: int) -> Merchant:
    async with _get_rate_limiter():
        await _sim_network(0.01)
        return Merchant(id=merchant_id, name="Demo Store",
                        rating=4.4, affiliate=True)

# ------ Category path ----------------------------------------------------------
async def get_category_path(cat_id: int) -> List[int]:
    async with _get_rate_limiter():
        await _sim_network(0.01)
        return [1, 12, 34, cat_id]

 