from __future__ import annotations

import asyncio
import json
from typing import Any

try:
    import websockets  # type: ignore
except Exception:  # pragma: no cover
    websockets = None  # optional in Tests/CI


class GatewayClient:
    """Minimaler WS-Client zum bot-gateway.
    In Tests/CI liefert er einen Dry-Run, wenn kein Gateway erreichbar ist oder websockets fehlt.
    """

    def __init__(self, url: str = "ws://localhost:3000", timeout_s: float = 2.5) -> None:
        self.url = url
        self.timeout_s = timeout_s

    async def execute_action(self, action: dict[str, Any]) -> dict[str, Any]:
        # Offline-/CI-Fallback
        if websockets is None:
            return {"ok": True, "dry_run": True, "action": action}
        try:
            async with websockets.connect(self.url) as ws:  # type: ignore[attr-defined]
                await ws.send(json.dumps(action))
                msg = await asyncio.wait_for(ws.recv(), timeout=self.timeout_s)
                return json.loads(msg)
        except Exception:
            # Gateway nicht erreichbar → Dry-Run
            return {"ok": True, "dry_run": True, "action": action}

    async def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        if websockets is None:
            return {"ok": False, "offline": True}
        try:
            async with websockets.connect(self.url) as ws:  # type: ignore[attr-defined]
                await ws.send(json.dumps(payload))
                msg = await asyncio.wait_for(ws.recv(), timeout=self.timeout_s)
                return json.loads(msg)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    async def observe(self, agent: str | None = None) -> dict[str, Any]:
        """Pull the MCP-shaped observation for one embodied agent."""
        payload: dict[str, Any] = {"type": "observe"}
        if agent:
            payload["agent"] = agent
        return await self._request(payload)

    async def scene(self) -> dict[str, Any]:
        """Pull the whole-world view: all players, agents, and recent chat."""
        return await self._request({"type": "scene"})
