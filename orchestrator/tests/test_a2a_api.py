# orchestrator/tests/test_a2a_api.py
from __future__ import annotations

import httpx
import pytest

from app.main import app
from app.schemas.a2a import make_offer, make_request


@pytest.mark.anyio
async def test_send_and_fetch_inbox_fifo():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # zwei Nachrichten an botB
        m1 = make_request(
            sender="botA", receiver="botB", task="collect wood", item="log", qty=2
        ).model_dump()
        m2 = make_offer(
            sender="botC", receiver="botB", item="planks", qty=4, payload={"from": "log"}
        ).model_dump()

        r1 = await ac.post("/a2a/send", json=m1)
        r2 = await ac.post("/a2a/send", json=m2)
        assert r1.status_code == 200 and r1.json()["ok"] is True
        assert r2.status_code == 200 and r2.json()["ok"] is True

        # Inbox abholen (FIFO)
        inbox = await ac.get("/a2a/inbox", params={"agent_id": "botB", "max": 10})
        assert inbox.status_code == 200
        data = inbox.json()
        msgs = data["messages"]
        assert data["receiver"] == "botB"
        assert len(msgs) == 2

        # FIFO-Reihenfolge prüfen
        assert msgs[0]["kind"] == "REQUEST"
        assert msgs[0]["task"] == "collect wood"
        assert msgs[1]["kind"] == "OFFER"
        assert msgs[1]["item"] == "planks"

        # erneuter Abruf → leer
        inbox2 = await ac.get("/a2a/inbox", params={"agent_id": "botB"})
        assert inbox2.status_code == 200
        assert inbox2.json()["messages"] == []


@pytest.mark.anyio
async def test_send_rejects_missing_sender_or_receiver():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        bad = make_request(sender="", receiver="", task="x").model_dump()
        resp = await ac.post("/a2a/send", json=bad)
        assert resp.status_code == 400
