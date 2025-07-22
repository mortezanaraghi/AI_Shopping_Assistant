"""
Tool: codegen_slow
High‑fidelity code generation for complex calculations or data
transforms.  This is the 'escalation' tier, so we simulate a longer
latency and more verbose output.

In a real deployment we would:
  * Send a prompt to Claude 3 Sonnet or GPT‑4o‑large with tool specifications.
  * Execute returned code inside a secure sandbox (e.g., Pyodide,
    Docker Firecracker micro‑VM).
For the take‑home we:
  * Accept a Python code string.
  * Execute it in a restricted namespace with a 2‑second sleep to mimic
    higher latency and cost.
"""
from typing import Dict, Any
import asyncio, textwrap

schema: Dict[str, Any] = {
    "name": "codegen_slow",
    "description": (
        "Generate and run multi‑line Python code for heavier analysis "
        "(e.g., iterate over list of benchmarks).  Use only when "
        "codegen_fast is insufficient."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute; should assign variable `result`."
            }
        },
        "required": ["code"]
    },
}

SAFE_GLOBALS = {"__builtins__": {"range": range, "len": len, "min": min, "max": max}}

async def run(code: str) -> Dict[str, Any]:
    await asyncio.sleep(2.0)  # simulate slower LLM latency
    loc: Dict[str, Any] = {}
    try:
        exec(textwrap.dedent(code), SAFE_GLOBALS, loc)
        result = loc.get("result", None)
        return {"ok": True, "result": result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
