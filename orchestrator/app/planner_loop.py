"""Planner loop — the agent composes SKILLS toward a goal, with short-term memory.

This is the shift from reactive single-actions to multi-step competence: each tick
the LLM picks the next skill (collect/craft/place/equip/move/chat) given the goal,
current state, and recent steps. Skills carry the multi-step detail (navigation,
the crafting tech tree), so goals like "get a wooden pickaxe" become reachable.

    python -m app.planner_loop --goal "Craft a wooden pickaxe, then mine stone" --agent Agent1 --ticks 12
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from typing import Any

from . import llm
from .adapters.gateway_client import GatewayClient
from .mcp import build_mcp_from_obs

_SKILL_NAMES = {"collect", "craft", "place", "equip", "build_shelter"}


def _summary(result: dict[str, Any]) -> str:
    if not isinstance(result, dict):
        return str(result)
    if not result.get("ok"):
        return f"FAIL {result.get('error', '')}"[:80]
    bits = [f"{k}={v}" for k, v in result.items() if k in ("gained", "have", "count", "pos", "type", "item", "moved")]
    return " ".join(bits)[:80] or "ok"


async def skill_tick(
    gw: GatewayClient, agent_id: str, goal: str, history: list[dict[str, Any]]
) -> dict[str, Any]:
    obs_resp = await gw.observe(agent_id)
    obs = obs_resp.get("observation") if obs_resp.get("ok") else None
    if not obs:
        return {"ok": False, "stage": "observe", "detail": obs_resp}

    mcp = build_mcp_from_obs(agent_id, goal, obs)
    t0 = time.time()
    try:
        plan = llm.plan_next_skill(mcp, goal, history)
    except Exception as e:  # noqa: BLE001
        plan = {"skill": "chat", "args": {"text": f"(plan error: {e})"}}
    latency_ms = round((time.time() - t0) * 1000)

    skill = plan.get("skill", "chat")
    args = plan.get("args", {}) or {}

    if skill == "done":
        return {"ok": True, "done": True, "inventory": obs.get("inventory"), "llm_ms": latency_ms}

    if skill in _SKILL_NAMES:
        result = await gw.skill(skill, args, agent_id)
    elif skill == "move":
        result = await gw.execute_action({"type": "move", "blocks": int(args.get("blocks", 3)), "agent": agent_id})
    elif skill == "chat":
        result = await gw.execute_action({"type": "chat", "text": str(args.get("text", "")), "agent": agent_id})
    else:
        result = {"ok": False, "error": f"unknown skill: {skill}"}

    history.append({"skill": skill, "args": args, "ok": result.get("ok"), "summary": _summary(result)})
    return {
        "ok": True,
        "skill": skill,
        "args": args,
        "result": result,
        "inventory": obs.get("inventory"),
        "llm_ms": latency_ms,
    }


def _log_path() -> str:
    runs = os.path.join(os.path.dirname(__file__), "..", "runs")
    os.makedirs(runs, exist_ok=True)
    return os.path.join(runs, f"plan-{time.strftime('%Y%m%d-%H%M%S')}.jsonl")


async def run(goal: str, agent_id: str, ticks: int, url: str | None = None) -> None:
    gw = GatewayClient(
        url=url or os.getenv("GATEWAY_URL", "ws://localhost:3000"),
        timeout_s=float(os.getenv("GATEWAY_TIMEOUT", "90")),
    )
    interval = float(os.getenv("TICK_INTERVAL", "1"))
    history: list[dict[str, Any]] = []
    log_path = _log_path()
    print(f"goal: {goal}\nagent: {agent_id}\nlog: {os.path.abspath(log_path)}\n")

    with open(log_path, "a", encoding="utf-8") as log:
        for i in range(ticks):
            out = await skill_tick(gw, agent_id, goal, history)
            log.write(json.dumps({"ts": time.time(), "tick": i + 1, "agent": agent_id, **out}, ensure_ascii=False) + "\n")
            log.flush()
            if out.get("done"):
                print(f"[tick {i + 1}] DONE — inventory: {out.get('inventory')}")
                break
            print(f"[tick {i + 1}] {out.get('skill')}({out.get('args')}) -> {_summary(out.get('result', {}))}")
            await asyncio.sleep(interval)
    print("\nfinal inventory:", json.dumps((await gw.observe(agent_id)).get("observation", {}).get("inventory", {})))


def main() -> None:
    p = argparse.ArgumentParser(description="Run the skill-planning agent loop.")
    p.add_argument("--goal", default="Craft a wooden pickaxe, then mine some stone.")
    p.add_argument("--agent", default="Agent1")
    p.add_argument("--ticks", type=int, default=14)
    args = p.parse_args()
    asyncio.run(run(args.goal, args.agent, args.ticks))


if __name__ == "__main__":
    main()
