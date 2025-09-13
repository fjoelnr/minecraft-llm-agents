# orchestrator/app/mcp.py
"""
MCP (Model Context Protocol) — schema, builder, validation.
"""

from typing import Dict, Any, List, OrderedDict as _OrderedDict
from collections import OrderedDict
from pydantic import BaseModel, Field, ValidationError

# --- Pydantic schema for MCP ---
class MCPEnv(BaseModel):
    pos: List[int] = Field(default_factory=lambda: [0, 64, 0])
    time_of_day: str = "noon"
    biome: str | None = None
    nearby: List[str] = Field(default_factory=list)

class MCPTeam(BaseModel):
    teammates: List[str] = Field(default_factory=list)
    messages: List[str] = Field(default_factory=list)

class MCPContext(BaseModel):
    agent_id: str
    goal: str
    env: MCPEnv
    inventory: Dict[str, int] = Field(default_factory=dict)
    skills_index: List[str] = Field(default_factory=list)
    rag_snippets: List[str] = Field(default_factory=list)
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

def _order_mcp(d: Dict[str, Any]) -> _OrderedDict[str, Any]:
    """Return dict with deterministic key order for stable prompts/logs."""
    return OrderedDict((k, d[k]) for k in MCP_KEY_ORDER if k in d)

def build_mcp(agent_id: str, goal: str, env: Dict[str, Any] | None = None) -> Dict[str, Any]:
    ctx = MCPContext(agent_id=agent_id, goal=goal, env=MCPEnv(**(env or {})))
    return _order_mcp(ctx.model_dump())

def validate_mcp(raw: Dict[str, Any]) -> tuple[bool, str | None]:
    try:
        MCPContext.model_validate(raw)
        return True, None
    except ValidationError as e:
        return False, e.json()

def mcp_json_schema() -> Dict[str, Any]:
    return MCPContext.model_json_schema()
