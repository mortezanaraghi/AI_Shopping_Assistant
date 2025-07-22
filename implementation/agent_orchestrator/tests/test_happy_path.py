# tests/test_happy_path.py
import asyncio, pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.orchestrator import Orchestrator
from src.models import ConversationContext

@pytest.mark.asyncio
async def test_happy():
    o = Orchestrator()
    r = await o.process_query("cheap gaming monitor", ConversationContext(session_id="t1"))
    assert "monitor" in r.content.lower()

 