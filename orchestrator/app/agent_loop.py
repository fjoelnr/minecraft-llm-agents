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
    """Run one perceive -> decide -> act cycle. Returns a structured trace."""
    # 1) Perceive
    obs_resp = await gateway.observe()
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

    # 4) Act
    result = await gateway.execute_action(action)

    return {
        "ok": True,
        "pos": obs.get("pos"),
        "decided": decided,
        "action": action,
        "result": result,
        "llm_ms": latency_ms,
    }


async def run(goal: str, ticks: int, agent_id: str = "A", url: str | None = None) -> None:
    gw = GatewayClient(
        url=url or os.getenv("GATEWAY_URL", "ws://localhost:3000"),
        timeout_s=float(os.getenv("GATEWAY_TIMEOUT", "60")),
    )
    interval = float(os.getenv("TICK_INTERVAL", "2"))
    for i in range(ticks):
        out = await tick(gw, agent_id, goal)
        line = json.dumps(out, ensure_ascii=False)
        print(f"[tick {i + 1}/{ticks}] {line[:400]}")
        await asyncio.sleep(interval)


def main() -> None:
    p = argparse.ArgumentParser(description="Run the end-to-end agent loop.")
    p.add_argument("--goal", default="Explore your surroundings and comment on what you see in chat.")
    p.add_argument("--ticks", type=int, default=5)
    p.add_argument("--agent", default="A")
    args = p.parse_args()
    asyncio.run(run(args.goal, args.ticks, args.agent))


if __name__ == "__main__":
    main()
