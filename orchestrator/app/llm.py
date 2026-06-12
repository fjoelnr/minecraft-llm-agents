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
    "The OBSERVATION field `nearby_blocks` lists resources you can see as "
    '"name@distance" (e.g. "spruce_log@3"). To gather, `mine` a block name that '
    "appears there. If `nearby_blocks` has no useful resource, `move` to look "
    "elsewhere. Occasionally `chat` to narrate your intent. Advance the goal."
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


SKILL_INSTRUCTIONS = (
    "You are the planner for a Minecraft agent. Choose the single NEXT skill that "
    "best advances the GOAL, given the current STATE and what you have already done "
    "(RECENT_STEPS). Think about prerequisites: to craft you need ingredients; a "
    "wooden_pickaxe needs planks+sticks and a crafting table; to mine stone/ores you "
    "need a pickaxe first.\n"
    "IMPORTANT: check STATE.inventory FIRST — if it already contains what the goal "
    "asks for, do not gather more; report via chat and use done. "
    "If STATE.env.time_of_day is night, monsters are out: prefer build_shelter or "
    "staying put over wandering.\n"
    "Available skills:\n"
    '  {"skill":"collect","args":{"type":"<block>","count":<int>}}  gather blocks (e.g. spruce_log, stone)\n'
    '  {"skill":"craft","args":{"item":"<item>","count":<int>}}     craft (auto-handles the crafting table)\n'
    '  {"skill":"place","args":{"type":"<block>"}}                  place a block from inventory\n'
    '  {"skill":"equip","args":{"type":"<item>"}}                   equip a tool\n'
    '  {"skill":"build_shelter","args":{}}                          build a small hut around yourself (needs ~24 solid blocks like dirt/cobblestone)\n'
    '  {"skill":"move","args":{"blocks":<int>}}                     walk forward to explore\n'
    '  {"skill":"chat","args":{"text":"<msg>"}}                     say something\n'
    '  {"skill":"done","args":{}}                                  goal already satisfied\n'
    "Respond with a single minified JSON object and nothing else. Avoid repeating a "
    "step that already succeeded.\n"
    "STATE.team shows your teammates (name@position) and recent chat messages. You "
    "may coordinate: use chat to tell teammates what you are doing or to split work "
    "(e.g. one gathers wood while the other builds). React to teammate messages."
)


def plan_next_skill(
    mcp: dict[str, Any],
    goal: str,
    history: list[dict[str, Any]] | None = None,
    model: str | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    """Return the next skill call {skill, args} to advance the goal."""
    provider = provider or os.getenv("LLM_PROVIDER", "ollama")
    if provider == "dummy":
        return {"skill": "chat", "args": {"text": f"(dummy) {goal}"}}

    steps = history or []
    recent = "\n".join(
        f"  {i + 1}. {s.get('skill')}({s.get('args')}) -> {'ok' if s.get('ok') else 'fail'}: {s.get('summary', '')}"
        for i, s in enumerate(steps[-8:])
    ) or "  (none yet)"
    prompt = (
        f"GOAL: {goal}\n"
        f"STATE:\n{json.dumps(mcp, ensure_ascii=False)}\n"
        f"RECENT_STEPS:\n{recent}\n\n"
        f"{SKILL_INSTRUCTIONS}"
    )
    raw = _ollama_chat(prompt, model or DEFAULT_MODEL)
    return coerce_skill(raw)


_SKILL_KEYS = ("skill", "name", "tool", "action")
_VALID_SKILLS = {"collect", "craft", "place", "equip", "build_shelter", "move", "chat", "done"}


def coerce_skill(raw: Any) -> dict[str, Any]:
    """Normalize a model's loose JSON onto {skill, args}."""
    if not isinstance(raw, dict):
        return {"skill": "chat", "args": {"text": str(raw)}}
    name = None
    for k in _SKILL_KEYS:
        v = raw.get(k)
        if isinstance(v, str) and v.lower().strip() in _VALID_SKILLS:
            name = v.lower().strip()
            break
    name = name or "chat"
    args = raw.get("args") if isinstance(raw.get("args"), dict) else {}
    # tolerate flat fields (type/item/count/blocks/text at top level)
    for k in ("type", "item", "count", "blocks", "text", "recipe", "target"):
        if k in raw and k not in args:
            args[k] = raw[k]
    if "item" not in args and "target" in args:
        args["item"] = args["target"]
    return {"skill": name, "args": args}


def _ollama_chat(prompt: str, model: str) -> dict[str, Any]:
    resp = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.5},
        },
        timeout=float(os.getenv("LLM_TIMEOUT", "120")),
    )
    resp.raise_for_status()
    return json.loads(resp.json()["message"]["content"])


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
