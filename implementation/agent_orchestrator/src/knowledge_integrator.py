"""
Knowledge Integrator
Integrates ShopGraph data with the agent system for enhanced product insights.
"""
from __future__ import annotations
import asyncio, statistics, hashlib, json
from typing import List
from src.utils.logging import init_logger
from src.models import Product, SearchContext, UserProfile, ProductRecommendation, UserRequirements
import src.shopgraph_api as sg

log = init_logger()

# ───── caching in‑mem (replace with RedisJSON in prod) ─────────
_cache: dict[str, List[ProductRecommendation]] = {}

def _cache_key(req: UserRequirements) -> str:
    blob = json.dumps(req.model_dump(), sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()

# ───── public API ──────────────────────────────────────────────
async def get_expert_recommendations(
    requirements: UserRequirements
) -> List[ProductRecommendation]:
    key = _cache_key(requirements)
    if key in _cache:
        return _cache[key]

    # 1️⃣ candidate search
    products = await sg.search_products(requirements.query)

    # 2️⃣ parallel enrichment
    async def enrich(p: Product):
        price_drop, criteria, variant = await asyncio.gather(
            sg.get_price_drop(p.id),
            sg.get_criteria_scores(p.id),
            sg.get_variant_stats(p.id),
        )
        deal = (price_drop.percent_drop_7d if price_drop else 0)
        quality = statistics.mean([c.rating for c in criteria]) if criteria else 0
        variant_bonus = 0.1 if variant["count"] > 5 else 0
        merchant = await sg.get_merchant(12345)
        p.specs |= {
            "deal": deal,
            "quality": quality,
            "variant": variant["count"],
            "merchant_rating": merchant.rating,
        }
        score = (
            0.35*deal +
            0.25*quality +
            0.20*merchant.rating +
            0.10*variant_bonus +
            0.10*(1 if (requirements.budget_cents and p.price_cents<=requirements.budget_cents) else 0)
        )
        return ProductRecommendation(**p.model_dump(), score=score,
                                     final_price_cents=p.price_cents,
                                     merchant_id=merchant.id)
    ranked = sorted(await asyncio.gather(*map(enrich, products)),
                    key=lambda x: x.score, reverse=True)
    _cache[key] = ranked[:5]
    return _cache[key]
 