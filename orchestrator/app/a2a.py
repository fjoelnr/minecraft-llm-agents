"""
A2A (Agent-to-Agent) — skeleton.
Defines message schema for cooperative tasks.
"""

from typing import Dict, Any
from pydantic import BaseModel

class A2AMessage(BaseModel):
    sender: str
    receiver: str
    kind: str  # REQUEST, OFFER, HANDOFF
    task: str | None = None
    item: str | None = None
    qty: int | None = None

def make_request(sender: str, receiver: str, task: str, item: str, qty: int) -> Dict[str, Any]:
    return A2AMessage(sender=sender, receiver=receiver, kind="REQUEST", task=task, item=item, qty=qty).dict()

def make_offer(sender: str, receiver: str, item: str, qty: int) -> Dict[str, Any]:
    return A2AMessage(sender=sender, receiver=receiver, kind="OFFER", item=item, qty=qty).dict()
