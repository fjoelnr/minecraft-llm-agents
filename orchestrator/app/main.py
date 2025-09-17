# orchestrator/app/main.py
from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

try:
    from .adapters.gateway_client import GatewayClient
except Exception:  # noqa: BLE001
    class GatewayClient:  # type: ignore[no-redef]
        async def execute_action(self, action: dict[str, object]) -> dict[str, object]:
            return {"ok": True, "dry_run": True, "action": action}
from .mcp import build_mcp, mcp_json_schema, validate_mcp
from .memory_vec import (
    DEFAULT_COLLECTION,
    add_batch as vec_add_batch,
    add_memory as vec_add_memory,
    drop_collection as vec_drop_collection,
    list_collections as vec_list_collections,
    query_memory as vec_query_memory,
    stats as vec_stats,
)
from .schemas import Action

app = FastAPI(title="MCP-Craft Orchestrator", version="0.3.0")

# In-memory state store (per agent)
_STATE: dict[str, dict[str, Any]] = {}

_GATEWAY = GatewayClient()


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


class MemoryAddRequest(BaseModel):
    text: str
    kind: str | None = "note"
    metadata: dict[str, Any] | None = None
    collection: str | None = None


class MemoryAddBatchRequest(BaseModel):
    texts: list[str]
    kind: str | None = "note"
    metadatas: list[dict[str, Any]] | None = None
    collection: str | None = None


class MemoryQueryRequest(BaseModel):
    query: str
    top_k: int = 3
    collection: str | None = None


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


@app.get("/memory/collections")
def memory_collections():
    return {"ok": True, "collections": vec_list_collections()}


@app.get("/memory/stats")
def memory_stats(collection: str = DEFAULT_COLLECTION):
    return {"ok": True, "stats": vec_stats(collection)}


@app.delete("/memory/collection")
def memory_drop_collection(collection: str):
    try:
        ok = vec_drop_collection(collection)
        return {"ok": ok, "dropped": collection}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail={"memory_error": str(e)}) from e


@app.post("/step", response_model=StepResponse)
def step(
    req: StepRequest,
    execute: bool = Query(default=False),
    use_memory: bool = Query(default=False),
    mem_collection: str = Query(default=DEFAULT_COLLECTION),
):
    # 1) Build deterministic MCP
    mcp = build_mcp(req.agent_id, req.goal)

    # 1b) Optionaler RAG-Hook aus Vektorspeicher
    if use_memory:
        try:
            hits = vec_query_memory(req.goal, top_k=3, collection=mem_collection)
            mcp["rag_snippets"] = [h["text"] for h in hits]
        except Exception:
            mcp["rag_snippets"] = []

    # 2) MCP validieren
    ok, err = validate_mcp(mcp)
    if not ok:
        raise HTTPException(status_code=400, detail={"mcp_validation_error": err})

    # 3) Dummy-Planung (später Planner/LLM)
    if "shelter" in req.goal.lower():
        raw_action = {"type": "mine", "target": "oak_log", "qty": 5}
    else:
        raw_action = {
            "type": "chat",
            "text": f"Hello from {req.agent_id}, pursuing goal: {req.goal}",
        }

    # 4) Action validieren/normalisieren
    try:
        action = Action(**raw_action).normalize()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail={"action_validation_error": str(e)}) from e

    # 5) Optional ausführen
    gateway_result: dict[str, Any] | None = None
    if execute:
        try:
            gateway_result = asyncio.run(_GATEWAY.execute_action(action))
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502, detail={"gateway_error": str(e)}) from e

    # 6) Snapshot ablegen
    _STATE[req.agent_id] = {"mcp": mcp, "last_action": action, "ts": time.time()}

    return StepResponse(
        ok=True,
        agent_id=req.agent_id,
        goal=req.goal,
        action=action,
        mcp_snapshot=mcp,
        note="feat/memory",
        gateway_result=gateway_result,
    )


@app.post("/memory/add")
def memory_add(req: MemoryAddRequest):
    try:
        mem_id = vec_add_memory(
            req.text,
            kind=req.kind or "note",
            metadata=req.metadata or {},
            collection=req.collection or DEFAULT_COLLECTION,
        )
        return {"ok": True, "id": mem_id}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail={"memory_error": str(e)}) from e


@app.post("/memory/add_batch")
def memory_add_batch(req: MemoryAddBatchRequest):
    try:
        ids = vec_add_batch(
            req.texts,
            kind=req.kind or "note",
            metadatas=req.metadatas,
            collection=req.collection or DEFAULT_COLLECTION,
        )
        return {"ok": True, "ids": ids}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail={"memory_error": str(e)}) from e


@app.post("/memory/query")
def memory_query(req: MemoryQueryRequest):
    try:
        items = vec_query_memory(
            req.query,
            top_k=req.top_k,
            collection=req.collection or DEFAULT_COLLECTION,
        )
        return {"ok": True, "items": items}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail={"memory_error": str(e)}) from e
