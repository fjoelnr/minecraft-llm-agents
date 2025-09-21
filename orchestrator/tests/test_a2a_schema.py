# orchestrator/tests/test_a2a_schema.py
from __future__ import annotations

from app.schemas.a2a import A2AKind, A2AMessage, make_offer, make_request


def test_make_request_has_defaults_and_fields():
    msg = make_request(sender="botA", receiver="botB", task="collect wood", item="log", qty=4)
    d = msg.model_dump()

    assert isinstance(d["id"], str) and d["id"].startswith("msg_")
    assert isinstance(d["ts"], str) and d["ts"].endswith("Z")

    assert d["sender"] == "botA"
    assert d["receiver"] == "botB"
    assert d["kind"] == "REQUEST"
    assert d["task"] == "collect wood"
    assert d["item"] == "log"
    assert d["qty"] == 4
    assert d["payload"] is None
    assert d["correlation_id"] is None


def test_make_offer_and_roundtrip():
    msg = make_offer(sender="botB", receiver="botA", item="planks", qty=4, payload={"from": "log"})
    d = msg.model_dump()

    # Roundtrip
    msg2 = A2AMessage.model_validate(d)
    d2 = msg2.model_dump()

    assert d2["kind"] == "OFFER"
    assert d2["item"] == "planks"
    assert d2["qty"] == 4
    assert d2["payload"] == {"from": "log"}
    assert d2["sender"] == "botB" and d2["receiver"] == "botA"
    assert d2["id"].startswith("msg_") and d2["ts"].endswith("Z")


def test_qty_must_be_non_negative():
    try:
        _ = make_offer(sender="botX", receiver="botY", item="stone", qty=-1)
        assert False, "negative qty must raise"
    except Exception as e:  # noqa: BLE001
        assert "qty must be >= 0" in str(e)


def test_literal_kind_type():
    # Typprüfung indirekt: stellt sicher, dass nur erlaubte Kinds zugelassen werden
    _ok_kinds: list[A2AKind] = ["REQUEST", "OFFER", "ACCEPT", "REJECT", "INFO"]
    for k in _ok_kinds:
        m = A2AMessage(sender="a", receiver="b", kind=k)
        assert m.kind in _ok_kinds
