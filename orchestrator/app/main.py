# orchestrator/app/main.py
from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .mcp import build_mcp, mcp_json_schema, validate_mcp
from .schemas import Action

app = FastAPI(title="MCP-Craft Orchestrator", version="0.2.0")

# In-memory state store (per agent)
_STATE: dict[str, dict[str, Any]] = {}


class StepRequest(BaseModel):
    goal: str = "demo"
    agent_id: str = "A"


class StepResponse(BaseModel):
    ok: bool
    agent_id: str
    goal: str
    action: dict[str, Any]
    mcp_snapshot: dict[str, Any]
    note: str | None = None


@app.get("/health")
def health():
    return {"status": "ok", "ts": time.time()}


@app.get("/mcp/schema")
def mcp_schema_endpoint():
    return mcp_json_schema()


@app.get("/state")
def get_state(agent_id: str = "A"):
    snap = _STATE.get(agent_id)
    if not snap:
        return {"ok": False, "agent_id": agent_id, "state": None, "note": "no snapshot yet"}
    return {"ok": True, "agent_id": agent_id, "state": snap}


@app.post("/step", response_model=StepResponse)
def step(req: StepRequest):
    # 1) Build deterministic MCP
    mcp = build_mcp(req.agent_id, req.goal)

    # 2) Validate MCP
    ok, err = validate_mcp(mcp)
    if not ok:
        raise HTTPException(status_code=400, detail={"mcp_validation_error": err})

    # 3) Dummy planner
    if "shelter" in req.goal.lower():
        raw_action = {"type": "mine", "target": "oak_log", "qty": 5}
    else:
        raw_action = {
            "type": "chat",
            "text": f"Hello from {req.agent_id}, pursuing goal: {req.goal}",
        }

    # 4) Validate & normalize action
    try:
        action = Action(**raw_action).normalize()
    except Exception as e:  # noqa: BLE001
        # B904: mit 'from e' raisen
        raise HTTPException(status_code=400, detail={"action_validation_error": str(e)}) from e

    # 5) Store state snapshot
    _STATE[req.agent_id] = {"mcp": mcp, "last_action": action, "ts": time.time()}

    return StepResponse(
        ok=True,
        agent_id=req.agent_id,
        goal=req.goal,
        action=action,
        mcp_snapshot=mcp,
        note="feat/mcp",
    )
