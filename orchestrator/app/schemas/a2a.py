from __future__ import annotations

import datetime as _dt
import secrets
from enum import Enum

from pydantic import BaseModel, Field, field_validator

# -- helpers --------------------------------------------------------------


def _new_id() -> str:
    return f"a2a_{secrets.token_hex(6)}"


def _now_ts() -> str:
    # timezone-aware now, dann naive ISO + 'Z'
    return _dt.datetime.now(_dt.UTC).replace(tzinfo=None).isoformat(timespec="microseconds") + "Z"


# -- data model -----------------------------------------------------------


class A2AKind(str, Enum):
    REQUEST = "request"
    OFFER = "offer"


class A2AMessage(BaseModel):
    id: str = Field(default_factory=_new_id)
    kind: A2AKind
    sender: str
    receiver: str
    timestamp: str = Field(default_factory=_now_ts)

    # content
    action: str | None = None
    # Backward-Compat: „task“ als Alias zu action (einige Tests/Caller nutzen das)
    task: str | None = None

    item: str | None = None
    qty: int | None = None
    payload: dict | None = None

    # Wichtig: sender/receiver NICHT hier hart validieren (Tests wollen kaputte
    # Nachrichten bis zur API-Route durchreichen).
    @field_validator("qty")
    @classmethod
    def _qty_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("qty must be >= 0")
        return v


# -- builders -------------------------------------------------------------


def make_request(
    *,
    sender: str,
    receiver: str,
    action: str | None = None,
    task: str | None = None,  # Alias für action
    item: str | None = None,
    qty: int | None = None,
) -> A2AMessage:
    """
    Erzeugt eine REQUEST-Nachricht.
    Wenn sowohl 'action' als auch 'task' gesetzt sind, gewinnt 'action'.
    """
    effective_action = action or task
    return A2AMessage(
        kind=A2AKind.REQUEST,
        sender=sender,
        receiver=receiver,
        action=effective_action,
        task=task,
        item=item,
        qty=qty,
    )


def make_offer(
    *,
    sender: str,
    receiver: str,
    item: str,
    qty: int,
    payload: dict | None = None,
) -> A2AMessage:
    """Erzeugt eine OFFER-Nachricht."""
    return A2AMessage(
        kind=A2AKind.OFFER,
        sender=sender,
        receiver=receiver,
        item=item,
        qty=qty,
        payload=payload,
    )
