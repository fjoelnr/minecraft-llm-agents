import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.memory_vec import DEFAULT_COLLECTION


@pytest.mark.asyncio
async def test_add_and_query_memory_note():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Add
        r = await ac.post(
            "/memory/add",
            json={
                "text": "crafting: 4 planks from 1 log",
                "kind": "recipe",
                "metadata": {"mc_version": "1.19"},
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("ok") is True
        assert isinstance(body.get("id"), str)
        assert body["id"].startswith(f"{DEFAULT_COLLECTION}__")

        # Query
        r = await ac.post("/memory/query", json={"query": "planks", "top_k": 3})
        assert r.status_code == 200
        q = r.json()
        assert q.get("ok") is True
        results = q.get("items", q.get("results", []))
        assert isinstance(results, list)
        assert any("planks" in hit.get("text", "") for hit in results)
