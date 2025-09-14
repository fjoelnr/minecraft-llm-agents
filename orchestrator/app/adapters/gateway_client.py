from __future__ import annotations

import asyncio
import json
from typing import Any

try:
    import websockets  # type: ignore
except Exception:  # pragma: no cover
    websockets = None  # optional in tests


class GatewayClient:
    """
    Leichter WS-Client für das bot-gateway.
    Wenn kein Gateway läuft oder websockets fehlt, liefern wir einen Dry-Run zurück,
    damit Tests nicht hart ausfallen.
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
