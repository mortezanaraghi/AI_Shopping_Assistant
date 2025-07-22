# tests/test_criteria_ranking.py
import pytest, asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.models import UserRequirements
from src import knowledge_integrator as ki

@pytest.mark.asyncio
async def test_criteria_ranking():
    req = UserRequirements(query="easy to clean air fryer", budget_cents=20000)
    recs = await ki.get_expert_recommendations(req)
    assert recs[0].score >= recs[-1].score

 