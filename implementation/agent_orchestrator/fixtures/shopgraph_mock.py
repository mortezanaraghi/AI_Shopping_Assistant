"""
Mock implementation of ShopGraph API for testing and development.
Provides realistic data patterns while avoiding external dependencies.
"""
import json
import random
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class MockShopGraphClient:
    """Mock client that simulates ShopGraph API behavior with realistic latency and data patterns."""
    
    def __init__(self):
        self.fixture_path = Path(__file__).parent / "sample_data.json"
        self.data = self._load_fixture_data()
        
    def _load_fixture_data(self) -> Dict[str, Any]:
        """Load test data from fixtures."""
        try:
            with open(self.fixture_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback data if fixture file not found
            return {
                "sample_products": [],
                "sample_merchants": [],
                "sample_promotions": [],
                "sample_user_profiles": [],
                "sample_criteria_scores": []
            }
    
    async def _simulate_network_latency(self, base_latency: float = 0.05):
        """Simulate realistic network latency with some variation."""
        latency = base_latency * random.uniform(0.8, 1.2)
        await asyncio.sleep(latency)
    
    async def search_products(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Mock product search with query matching."""
        await self._simulate_network_latency(0.1)
        
        products = self.data.get("sample_products", [])
        
        # Simple query matching
        query_lower = query.lower()
        query_tokens = query_lower.split()
        
        # Score products based on query match
        scored_products = []
        for product in products:
            score = 0
            product_text = f"{product['name']} {product.get('brand', '')}".lower()
            
            # Exact matches get higher scores
            for token in query_tokens:
                if token in product_text:
                    score += 1
                    if token in product['name'].lower():
                        score += 2  # Name matches are more important
            
            if score > 0:
                scored_products.append((product, score))
        
        # Sort by score and return top results
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        # Generate additional products if needed to simulate larger catalog
        results = [p[0] for p in scored_products[:limit]]
        
        # Fill with generated products if we don't have enough matches
        while len(results) < min(limit, 5):
            generated_product = self._generate_product_for_query(query, len(results) + 1)
            results.append(generated_product)
            
        return results
    
    def _generate_product_for_query(self, query: str, index: int) -> Dict[str, Any]:
        """Generate a synthetic product that matches the query."""
        base_price = random.randint(50000, 300000)  # $500 to $3000
        
        return {
            "id": 1000 + index,
            "name": f"{query.title()} Model {index}",
            "category_id": 42,
            "price_cents": base_price,
            "specs": {
                "generated": True,
                "query_match": query
            },
            "brand": random.choice(["TechCorp", "ValueTech", "ProSystems", "BudgetBrand"]),
            "in_stock": random.choice([True, True, False]),  # 75% in stock
            "fast_shipping": random.choice([True, False])
        }
    
    async def get_price_drop(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Mock price drop data."""
        await self._simulate_network_latency(0.02)
        
        # 60% chance of having price drop data
        if random.random() < 0.6:
            return {
                "percent_drop_7d": random.uniform(0.05, 0.3),
                "attractiveness": random.uniform(6.0, 9.0),
                "days_since_drop": random.randint(1, 7)
            }
        return None
    
    async def get_promotions(self, merchant_id: int) -> List[Dict[str, Any]]:
        """Mock promotional data."""
        await self._simulate_network_latency(0.02)
        
        # Look for promotions for this merchant
        promotions = [
            p for p in self.data.get("sample_promotions", [])
            if p.get("merchant_id") == merchant_id
        ]
        
        # Generate some random promotions if none found
        if not promotions and random.random() < 0.7:  # 70% chance of promotions
            promotions = [
                {
                    "id": f"SAVE{random.randint(10, 50)}",
                    "percent_off": random.uniform(10, 30),
                    "amount_off": None,
                    "health": random.randint(80, 100),
                    "is_storewide": random.choice([True, False]),
                    "merchant_id": merchant_id
                }
            ]
        
        return promotions
    
    async def get_variant_stats(self, product_id: int) -> Dict[str, Any]:
        """Mock product variant statistics."""
        await self._simulate_network_latency(0.03)
        
        return {
            "count": random.randint(3, 15),
            "min_price": random.randint(80000, 120000),  # Variants usually cheaper
            "max_price": random.randint(200000, 400000),
            "avg_price": random.randint(150000, 250000),
            "in_stock_variants": random.randint(2, 10)
        }
    
    async def get_criteria_scores(self, product_id: int) -> List[Dict[str, Any]]:
        """Mock criteria/quality scores."""
        await self._simulate_network_latency(0.04)
        
        # Check if we have pre-defined criteria for this product
        for product_criteria in self.data.get("sample_criteria_scores", []):
            if product_criteria["product_id"] == product_id:
                return product_criteria["criteria"]
        
        # Generate random criteria scores
        criteria_types = [
            "build_quality", "performance", "value_for_money", 
            "user_experience", "reliability", "features"
        ]
        
        criteria = []
        for i, criterion in enumerate(criteria_types[:random.randint(3, 6)]):
            criteria.append({
                "criteria_id": i + 1,
                "rating": random.uniform(3.0, 5.0),
                "response_type": random.choice(["yes", "yes", "maybe", "no"]),
                "criterion_name": criterion
            })
        
        return criteria
    
    async def get_merchant(self, merchant_id: int) -> Dict[str, Any]:
        """Mock merchant information."""
        await self._simulate_network_latency(0.01)
        
        # Look for predefined merchant
        for merchant in self.data.get("sample_merchants", []):
            if merchant["id"] == merchant_id:
                return merchant
        
        # Generate random merchant
        return {
            "id": merchant_id,
            "name": f"Store {merchant_id}",
            "rating": random.uniform(3.5, 4.8),
            "affiliate": random.choice([True, False]),
            "verified": random.choice([True, True, False]),  # 75% verified
            "total_reviews": random.randint(100, 50000)
        }
    
    async def get_category_path(self, category_id: int) -> List[int]:
        """Mock category hierarchy path."""
        await self._simulate_network_latency(0.01)
        
        # Generate a realistic category path
        if category_id == 42:  # Electronics/Laptops
            return [1, 12, 34, 42]  # Root > Electronics > Computers > Laptops
        else:
            # Generate random path
            path = [1]  # Root category
            current = 1
            for _ in range(random.randint(2, 4)):
                current = current * 10 + random.randint(1, 9)
                path.append(current)
            path.append(category_id)
            return path
    
    async def get_product_alternatives(self, product_id: int) -> List[Dict[str, Any]]:
        """Mock alternative product suggestions."""
        await self._simulate_network_latency(0.05)
        
        # Generate 2-5 alternatives
        alternatives = []
        for i in range(random.randint(2, 5)):
            alternatives.append({
                "id": product_id + 1000 + i,
                "name": f"Alternative Product {i+1}",
                "price_cents": random.randint(80000, 300000),
                "similarity_score": random.uniform(0.6, 0.9),
                "reason": random.choice([
                    "Similar specifications",
                    "Same price range",
                    "Same brand",
                    "Frequently bought together"
                ])
            })
        
        return alternatives
    
    async def get_product_bundles(self, product_id: int) -> List[Dict[str, Any]]:
        """Mock product bundle suggestions."""
        await self._simulate_network_latency(0.03)
        
        # 40% chance of having bundles
        if random.random() < 0.4:
            return []
        
        bundles = []
        for i in range(random.randint(1, 3)):
            bundles.append({
                "bundle_id": f"bundle_{product_id}_{i}",
                "bundle_name": f"Complete Setup Bundle {i+1}",
                "additional_products": [
                    {"id": product_id + 2000 + i, "name": f"Accessory {i+1}"},
                    {"id": product_id + 3000 + i, "name": f"Software {i+1}"}
                ],
                "total_discount_percent": random.uniform(5, 15),
                "bundle_price_cents": random.randint(100000, 400000)
            })
        
        return bundles
    
    def get_user_profile_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile data from fixtures."""
        for profile in self.data.get("sample_user_profiles", []):
            if profile["user_id"] == user_id:
                return profile
        return None

# Global instance for easy importing
mock_shopgraph = MockShopGraphClient() 