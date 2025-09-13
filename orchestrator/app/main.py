from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, Optional
import time

app = FastAPI(title="MCP-Craft Orchestrator", version="0.1.0")

class StepRequest(BaseModel):
    goal: str = "demo"
    agent_id: str = "A"

class StepResponse(BaseModel):
    ok: bool
    agent_id: str
    goal: str
    action: Dict[str, Any]
    mcp_snapshot: Dict[str, Any]
    note: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok", "ts": time.time()}

@app.post("/step", response_model=StepResponse)
def step(req: StepRequest):
    mcp = {"agent_id": req.agent_id, "goal": req.goal, "env":{"pos":[0,64,0]}, "inventory":{}, "skills_index":["move","chat"], "rag_snippets":[]}
    action = {"type":"chat","text": f"Hello from {req.agent_id}, goal: {req.goal}"}
    return StepResponse(ok=True, agent_id=req.agent_id, goal=req.goal, action=action, mcp_snapshot=mcp, note="skeleton")