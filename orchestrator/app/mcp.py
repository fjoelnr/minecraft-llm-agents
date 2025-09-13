"""
MCP (Model Context Protocol) — skeleton.
Defines schema, builder, and validation helpers.
"""

from typing import Dict, Any
from pydantic import BaseModel, ValidationError

class MCPContext(BaseModel):
    agent_id: str
    goal: str
    env: Dict[str, Any]
    inventory: Dict[str, Any]
    skills_index: list[str]
    rag_snippets: list[str]
    team: Dict[str, Any]

def build_mcp(agent_id: str, goal: str) -> Dict[str, Any]:
    return {
        "agent_id": agent_id,
        "goal": goal,
        "env": {"pos": [0, 64, 0], "time_of_day": "noon"},
        "inventory": {},
        "skills_index": [],
        "rag_snippets": [],
        "team": {"teammates": [], "messages": []},
    }

def validate_mcp(data: Dict[str, Any]) -> bool:
    try:
        MCPContext(**data)
        return True
    except ValidationError as e:
        print("MCP validation failed:", e)
        return False
