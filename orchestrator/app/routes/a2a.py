from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.schemas.a2a import A2AMessage, make_offer, make_request

router = APIRouter(prefix="/a2a", tags=["a2a"])

# In-Memory Inbox: receiver -> FIFO-Liste von A2AMessage
_INBOX: dict[str, list[A2AMessage]] = {}


def _serialize_msg(msg: A2AMessage) -> dict:
    """
    JSON-freundliche Darstellung.
    - kind als ENUM-NAME (z.B. 'REQUEST'), wie die Tests es erwarten.
      Achtung: Durch use_enum_values=True kann kind bereits str sein.
    - action auch als 'task' spiegeln (Backward-Compat für Tests).
    - None-Felder weglassen.
    """
    data = msg.model_dump()

    # kind -> UPPERCASE Enum-Name
    kind_val = data.get("kind")
    if hasattr(msg.kind, "name"):  # falls doch Enum
        data["kind"] = msg.kind.name
    else:
        # String oder Sonstiges → Uppercase
        data["kind"] = str(kind_val).upper() if kind_val is not None else "REQUEST"

    # 'task' Spiegelung aus 'action'
    if data.get("action") and not data.get("task"):
        data["task"] = data["action"]

    # None-Werte entfernen
    data = {k: v for k, v in data.items() if v is not None}
    return data


class SendPayload(BaseModel):
    # generische Struktur – wir validieren manuell, damit Tests exakt greifen
    kind: str | None = None
    sender: str | None = None
    receiver: str | None = None
    task: str | None = None
    action: str | None = None
    item: str | None = None
    qty: int | None = None
    payload: dict[str, Any] | None = None


@router.post("/send")
async def send_message(body: SendPayload):
    # einfache Validierung wie von den Tests erwartet
    if not body.sender or not body.receiver:
        raise HTTPException(status_code=400, detail="sender and receiver are required")

    kind = (body.kind or "").lower()
    if kind not in {"", "request", "offer"}:
        raise HTTPException(status_code=400, detail="invalid kind")

    if kind in {"", "request"}:
        msg = make_request(
            sender=body.sender,
            receiver=body.receiver,
            action=body.action or body.task,
            item=body.item,
            qty=body.qty,
        )
    else:
        # offer
        if body.item is None or body.qty is None:
            raise HTTPException(status_code=400, detail="offer requires item and qty")
        msg = make_offer(
            sender=body.sender,
            receiver=body.receiver,
            item=body.item,
            qty=body.qty,
            payload=body.payload,
        )

    _INBOX.setdefault(msg.receiver, []).append(msg)
    return {"ok": True, "message": _serialize_msg(msg)}


@router.get("/inbox")
async def get_inbox(agent_id: str = Query(..., alias="agent_id"), max: int = 10):
    msgs = _INBOX.get(agent_id, [])
    # FIFO: älteste zuerst; begrenzen
    take = msgs[: max if max is not None and max > 0 else 10]
    # serialize
    out = [_serialize_msg(m) for m in take]
    # und die genommenen aus der Inbox entfernen (klassisches FIFO-Consume)
    _INBOX[agent_id] = msgs[len(take) :]
    return {"receiver": agent_id, "messages": out}
