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


async def run(
    goal: str,
    agents: list[str],
    ticks: int = 0,
    minutes: float = 0.0,
    url: str | None = None,
) -> None:
    """Drive one or more agents round-robin, each with its own step memory."""
    gw = GatewayClient(
        url=url or os.getenv("GATEWAY_URL", "ws://localhost:3000"),
        timeout_s=float(os.getenv("GATEWAY_TIMEOUT", "90")),
    )
    interval = float(os.getenv("TICK_INTERVAL", "1"))
    histories: dict[str, list[dict[str, Any]]] = {a: [] for a in agents}
    done: set[str] = set()
    log_path = _log_path()
    deadline = time.time() + minutes * 60 if minutes else None
    print(f"goal: {goal}\nagents: {', '.join(agents)}\nlog: {os.path.abspath(log_path)}\n")

    rnd = 0
    with open(log_path, "a", encoding="utf-8") as log:
        while True:
            rnd += 1
            for agent_id in agents:
                if agent_id in done:
                    continue
                out = await skill_tick(gw, agent_id, goal, histories[agent_id])
                log.write(json.dumps({"ts": time.time(), "round": rnd, "agent": agent_id, **out}, ensure_ascii=False) + "\n")
                log.flush()
                if out.get("done"):
                    print(f"[r{rnd} {agent_id}] DONE — inventory: {out.get('inventory')}")
                    done.add(agent_id)
                    continue
                print(f"[r{rnd} {agent_id}] {out.get('skill')}({out.get('args')}) -> {_summary(out.get('result', {}))}")
                await asyncio.sleep(interval)
            if len(done) == len(agents):
                break
            if ticks and rnd >= ticks:
                break
            if deadline and time.time() >= deadline:
                break
    for agent_id in agents:
        inv = (await gw.observe(agent_id)).get("observation", {}).get("inventory", {})
        print(f"final {agent_id}: {json.dumps(inv, ensure_ascii=False)}")


def main() -> None:
    p = argparse.ArgumentParser(description="Run the skill-planning agent loop.")
    p.add_argument("--goal", default="Craft a wooden pickaxe, then mine some stone.")
    p.add_argument("--agents", default="Agent1", help="comma-separated agent names")
    p.add_argument("--ticks", type=int, default=0, help="number of rounds (0 = use --minutes)")
    p.add_argument("--minutes", type=float, default=0.0, help="run duration in minutes")
    args = p.parse_args()
    agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    ticks = args.ticks or (0 if args.minutes else 14)
    asyncio.run(run(args.goal, agents, ticks=ticks, minutes=args.minutes))


if __name__ == "__main__":
    main()
