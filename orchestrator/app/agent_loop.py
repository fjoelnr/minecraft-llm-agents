"""End-to-end agent loop — the vertical slice.

One tick threads the full stack:
    gateway.observe()  ->  build MCP  ->  LLM decide  ->  validate  ->  gateway.execute

Run against a live gateway + sandbox server:

    python -m app.agent_loop --goal "Explore and describe what you see" --ticks 5

Env knobs: LLM_PROVIDER, LLM_MODEL, OLLAMA_URL, TICK_INTERVAL, GATEWAY_URL.
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
from .mcp import build_mcp_from_obs, validate_mcp
from .schemas import Action


async def tick(gateway: GatewayClient, agent_id: str, goal: str) -> dict[str, Any]:
    """Run one perceive -> decide -> act cycle for one agent. Returns a structured trace."""
    # 1) Perceive
    obs_resp = await gateway.observe(agent_id)
    obs = obs_resp.get("observation") if obs_resp.get("ok") else None
    if not obs:
        return {"ok": False, "stage": "observe", "detail": obs_resp}

    # 2) Build + validate MCP context
    mcp = build_mcp_from_obs(agent_id, goal, obs)
    ok, err = validate_mcp(mcp)
    if not ok:
        return {"ok": False, "stage": "mcp", "detail": err}

    # 3) Decide (real LLM) — fall back to a chat action if parsing/inference fails
    t0 = time.time()
    try:
        raw = llm.decide(mcp, goal)
        action = Action(**raw).normalize()
        decided = raw
    except Exception as e:  # noqa: BLE001
        action = Action(type="chat", text=f"(fallback: {e})").normalize()
        decided = {"error": str(e)}
    latency_ms = round((time.time() - t0) * 1000)

    # 4) Act (route to this agent)
    result = await gateway.execute_action({**action, "agent": agent_id})

    return {
        "ok": True,
        "pos": obs.get("pos"),
        "decided": decided,
        "action": action,
        "result": result,
        "llm_ms": latency_ms,
    }


def _log_path() -> str:
    runs = os.path.join(os.path.dirname(__file__), "..", "runs")
    os.makedirs(runs, exist_ok=True)
    return os.path.join(runs, f"run-{time.strftime('%Y%m%d-%H%M%S')}.jsonl")


async def run(
    goal: str,
    agents: list[str],
    ticks: int = 0,
    minutes: float = 0.0,
    url: str | None = None,
) -> None:
    """Drive one or more agents round-robin against the live gateway.

    Each agent's tick is appended as a JSON line to runs/run-<ts>.jsonl so the run
    can be observed/replayed. Stops after `ticks` rounds, or after `minutes`.
    """
    gw = GatewayClient(
        url=url or os.getenv("GATEWAY_URL", "ws://localhost:3000"),
        timeout_s=float(os.getenv("GATEWAY_TIMEOUT", "60")),
    )
    interval = float(os.getenv("TICK_INTERVAL", "2"))
    log_path = _log_path()
    deadline = time.time() + minutes * 60 if minutes else None
    print(f"goal: {goal}\nagents: {', '.join(agents)}\nlog: {os.path.abspath(log_path)}\n")

    rnd = 0
    with open(log_path, "a", encoding="utf-8") as log:
        while True:
            rnd += 1
            for agent_id in agents:
                out = await tick(gw, agent_id, goal)
                record = {"ts": time.time(), "round": rnd, "agent": agent_id, "goal": goal, **out}
                log.write(json.dumps(record, ensure_ascii=False) + "\n")
                log.flush()
                act = out.get("action", {})
                res = out.get("result", {})
                print(f"[r{rnd} {agent_id}] {json.dumps(act, ensure_ascii=False)} -> {res.get('type') or res.get('error')}")
                await asyncio.sleep(interval)
            if ticks and rnd >= ticks:
                break
            if deadline and time.time() >= deadline:
                break
    print(f"\nrun complete: {rnd} rounds, log at {os.path.abspath(log_path)}")


def main() -> None:
    p = argparse.ArgumentParser(description="Run the end-to-end multi-agent loop.")
    p.add_argument("--goal", default="Explore the area and build a simple shelter.")
    p.add_argument("--agents", default="Agent1,Agent2", help="comma-separated agent names")
    p.add_argument("--ticks", type=int, default=0, help="number of rounds (0 = use --minutes)")
    p.add_argument("--minutes", type=float, default=0.0, help="run duration in minutes")
    args = p.parse_args()
    agents = [a.strip() for a in args.agents.split(",") if a.strip()]
    ticks = args.ticks or (0 if args.minutes else 5)
    asyncio.run(run(args.goal, agents, ticks=ticks, minutes=args.minutes))


if __name__ == "__main__":
    main()
