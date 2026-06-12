"""
MCP (Model Context Protocol) — schema, builder, validation.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from pydantic import BaseModel, Field, ValidationError


# --- Pydantic schema for MCP ---
class MCPEnv(BaseModel):
    pos: list[int] = Field(default_factory=lambda: [0, 64, 0])
    time_of_day: str = "noon"
    biome: str | None = None
    standing_on: str | None = None
    nearby: list[str] = Field(default_factory=list)
    nearby_blocks: list[str] = Field(default_factory=list)


class MCPTeam(BaseModel):
    teammates: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class MCPContext(BaseModel):
    agent_id: str
    goal: str
    env: MCPEnv
    inventory: dict[str, int] = Field(default_factory=dict)
    skills_index: list[str] = Field(default_factory=list)
    rag_snippets: list[str] = Field(default_factory=list)
    team: MCPTeam = Field(default_factory=MCPTeam)


# --- deterministic key order for prompts/logs ---
MCP_KEY_ORDER = [
    "agent_id",
    "goal",
    "env",
    "inventory",
    "skills_index",
    "rag_snippets",
    "team",
]


def _order_mcp(d: dict[str, Any]) -> OrderedDict[str, Any]:
    """Return dict with deterministic key order for stable prompts/logs."""
    return OrderedDict((k, d[k]) for k in MCP_KEY_ORDER if k in d)


def build_mcp(agent_id: str, goal: str, env: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = MCPContext(agent_id=agent_id, goal=goal, env=MCPEnv(**(env or {})))
    return _order_mcp(ctx.model_dump())


def build_mcp_from_obs(agent_id: str, goal: str, obs: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic MCP context from a live gateway observation.

    Maps the gateway's observation shape (see bot-gateway/src/mcAgent.js) onto MCPEnv
    + inventory, tolerating missing fields.
    """
    env = MCPEnv(
        pos=obs.get("pos") or [0, 64, 0],
        time_of_day=obs.get("time_of_day") or "noon",
        biome=obs.get("biome") or None,
        standing_on=obs.get("standing_on") or None,
        nearby=obs.get("nearby") or [],
        nearby_blocks=obs.get("nearby_blocks") or [],
    )
    ctx = MCPContext(
        agent_id=agent_id,
        goal=goal,
        env=env,
        inventory=obs.get("inventory") or {},
        team=MCPTeam(
            teammates=obs.get("teammates") or [],
            messages=obs.get("recent_chat") or [],
        ),
    )
    return _order_mcp(ctx.model_dump())


def validate_mcp(raw: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        MCPContext.model_validate(raw)
        return True, None
    except ValidationError as e:  # noqa: F841
        return False, e.json()


def mcp_json_schema() -> dict[str, Any]:
    return MCPContext.model_json_schema()
