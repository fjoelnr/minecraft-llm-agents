# orchestrator/app/schemas/a2a.py
from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

A2AKind = Literal["REQUEST", "OFFER", "ACCEPT", "REJECT", "INFO"]


def _now_iso_z() -> str:
    # timezone-aware, stabil mit Z-Suffix
    return _dt.datetime.now(_dt.UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _gen_id() -> str:
    return f"msg_{uuid.uuid4().hex}"


class A2AMessage(BaseModel):
    """
    Minimales, stabilisiertes A2A-Schema v1.

    - id: stabile, clientseitige Message-ID
    - ts: ISO8601 UTC Timestamp mit 'Z'
    - sender/receiver: Agent-IDs (frei wählbar, z.B. 'botA', 'botB')
    - kind: REQUEST | OFFER | ACCEPT | REJECT | INFO
    - optionale Felder (task/item/qty) + payload (freies JSON)
    - correlation_id: zum Verketten von Antworten auf eine ursprüngliche Nachricht
    """

    id: str = Field(default_factory=_gen_id)
    ts: str = Field(default_factory=_now_iso_z)

    sender: str
    receiver: str
    kind: A2AKind

    task: str | None = None
    item: str | None = None
    qty: int | None = None

    payload: dict[str, Any] | None = None
    correlation_id: str | None = None

    @field_validator("qty")
    @classmethod
    def _qty_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("qty must be >= 0")
        return v


def make_request(
    sender: str,
    receiver: str,
    task: str,
    item: str | None = None,
    qty: int | None = None,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> A2AMessage:
    return A2AMessage(
        sender=sender,
        receiver=receiver,
        kind="REQUEST",
        task=task,
        item=item,
        qty=qty,
        payload=payload,
        correlation_id=correlation_id,
    )


def make_offer(
    sender: str,
    receiver: str,
    item: str,
    qty: int | None = None,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> A2AMessage:
    return A2AMessage(
        sender=sender,
        receiver=receiver,
        kind="OFFER",
        item=item,
        qty=qty,
        payload=payload,
        correlation_id=correlation_id,
    )
