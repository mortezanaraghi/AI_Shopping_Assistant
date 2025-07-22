"""
Tool: codegen_fast
Quick, low‑cost code‑generation + execution for simple numeric
calculations (e.g., $/render‑minute, Watts/hour, pixels per dollar).

Implementation notes
--------------------
* In production this would call an LLM like Gemini Flash or a hosted
  small model.  For the take‑home we:
  1. Accept a *plain‑English math expression* (e.g., "1800 / 120").
  2. Use Python's `eval` in a restricted globals dict.
  3. Return the numeric result or an error string.
* Latency ≈ < 300 ms.
"""
from typing import Dict, Any

schema: Dict[str, Any] = {
    "name": "codegen_fast",
    "description": (
        "Generate and run a short Python expression to answer a simple "
        "numeric question. Use ONLY for quick math (e.g., divide price "
        "by render‑minutes)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Plain‑English numeric expression, e.g. '1800 / 120'"
            }
        },
        "required": ["expression"]
    },
}

SAFE_GLOBALS = {"__builtins__": {}}

async def run(expression: str) -> Dict[str, Any]:
    try:
        result = eval(expression, SAFE_GLOBALS, {})
        return {"ok": True, "result": result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
