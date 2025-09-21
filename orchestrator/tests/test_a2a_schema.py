import pytest
from app.schemas.a2a import A2AKind, A2AMessage, make_offer, make_request


def test_make_request_has_defaults_and_fields():
    req = make_request(sender="botA", receiver="botB", action="mine")
    assert req.kind == A2AKind.REQUEST
    assert req.sender == "botA"
    assert req.receiver == "botB"
    # action bleibt für Abwärtskompatibilität gesetzt
    assert req.action == "mine"
    # optional
    assert req.item is None
    assert req.qty is None


def test_make_offer_and_roundtrip():
    offer = make_offer(sender="botA", receiver="botB", item="wood", qty=3)
    assert offer.kind == A2AKind.OFFER
    assert offer.item == "wood"
    assert offer.qty == 3

    # Roundtrip via model_dump/model_validate
    dumped = offer.model_dump()
    rebuilt = A2AMessage.model_validate(dumped)
    assert rebuilt == offer


def test_qty_must_be_non_negative():
    with pytest.raises(ValueError, match="qty must be >= 0"):
        _ = make_offer(sender="botX", receiver="botY", item="stone", qty=-1)


def test_literal_kind_type():
    # sicherstellen, dass nur die erlaubten Werte genutzt werden
    req = make_request(sender="bot1", receiver="bot2", action="chat")
    assert req.kind == A2AKind.REQUEST
    # alternativ ginge auch: assert req.kind.value == "request"
