# tests/test_noise_resilience.py
import asyncio, random, pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src import shopgraph_api as sg
from src.orchestrator import Orchestrator
from src.models import ConversationContext

@pytest.mark.asyncio
async def test_noise(monkeypatch):
    orig = sg.get_price_drop
    async def noisy(pid:int):
        if random.random()<.5: return None
        return await orig(pid)
    monkeypatch.setattr(sg, "get_price_drop", noisy)
    o = Orchestrator()
    r = await o.process_query("bluetooth earbuds", ConversationContext(session_id="t2"))
    assert r.content

 