"""LLM client with a small provider abstraction.

The vertical slice needs a *real* decision-maker, not a stub, so this wires the
local Ollama HTTP API by default and forces JSON output. A deterministic dummy
provider keeps tests/CI offline-safe.

Configured via environment:
  LLM_PROVIDER : "ollama" (default) | "dummy"
  LLM_MODEL    : Ollama model tag (default below)
  OLLAMA_URL   : base URL (default http://localhost:11434)
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

DEFAULT_MODEL = os.getenv("LLM_MODEL", "gemma4:e4b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

ACTION_INSTRUCTIONS = (
    "You control a single Minecraft agent. Given the OBSERVATION and GOAL, choose "
    "exactly ONE next action. Respond with a single minified JSON object and nothing "
    "else. Allowed actions:\n"
    '  {"type":"chat","text":"<short message>"}\n'
    '  {"type":"move","blocks":<integer 1-10>}\n'
    '  {"type":"mine","target":"<block_name>","qty":<integer 1-8>}\n'
    "Choose the action that best advances the goal. Prefer chat when unsure."
)


def decide(
    mcp: dict[str, Any],
    goal: str,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Return a coerced action dict decided by the configured LLM provider."""
    provider = provider or os.getenv("LLM_PROVIDER", "ollama")
    if provider == "dummy":
        return {"type": "chat", "text": f"(dummy) pursuing goal: {goal}"}
    return coerce_action(_ollama_decide(mcp, goal, model or DEFAULT_MODEL))


_TYPE_KEYS = ("type", "action", "name", "tool", "command")
_VALID_TYPES = {"chat", "mine", "craft", "move"}


def _as_int(v: Any, default: int = 1, lo: int = 1, hi: int = 64) -> int:
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def coerce_action(raw: Any) -> dict[str, Any]:
    """Map a model's loose JSON onto the strict Action shape.

    LLMs reliably return slight variants (``action`` vs ``type``, ``message`` vs
    ``text``, nested ``action`` objects). This keeps the decision layer robust so a
    semantically correct choice is never lost to a key-name mismatch.
    """
    if not isinstance(raw, dict):
        return {"type": "chat", "text": str(raw)}

    # nested {"action": {...}}
    if isinstance(raw.get("action"), dict):
        return coerce_action(raw["action"])

    kind = None
    for k in _TYPE_KEYS:
        val = raw.get(k)
        if isinstance(val, str) and val.lower().strip() in _VALID_TYPES:
            kind = val.lower().strip()
            break
    kind = kind or "chat"

    out: dict[str, Any] = {"type": kind}
    text = raw.get("text") or raw.get("message") or raw.get("say")
    target = raw.get("target") or raw.get("block") or raw.get("item")
    qty = raw.get("qty") or raw.get("quantity") or raw.get("count") or raw.get("amount")

    if kind == "chat":
        out["text"] = str(text or "")
    elif kind == "mine":
        out["target"] = str(target or "")
        out["qty"] = _as_int(qty, default=1, hi=8)
    elif kind == "craft":
        out["recipe"] = str(raw.get("recipe") or target or "")
        out["qty"] = _as_int(qty, default=1, hi=8)
    elif kind == "move":
        out["blocks"] = _as_int(raw.get("blocks") or raw.get("distance") or qty, default=1, hi=10)
    return out


def _ollama_decide(mcp: dict[str, Any], goal: str, model: str) -> dict[str, Any]:
    prompt = (
        f"GOAL: {goal}\n"
        f"OBSERVATION:\n{json.dumps(mcp, ensure_ascii=False)}\n\n"
        f"{ACTION_INSTRUCTIONS}"
    )
    resp = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.7},
        },
        timeout=float(os.getenv("LLM_TIMEOUT", "120")),
    )
    resp.raise_for_status()
    content = resp.json()["message"]["content"]
    return json.loads(content)
