# API Overview

## Orchestrator (FastAPI)

- `GET /health`  
  Returns `{"status":"ok","ts":...}`

- `POST /step {goal, agent_id}`  
  Returns JSON with:
  - `action`: suggested action (e.g., chat/mine/craft)
  - `mcp_snapshot`: full MCP state for that step

Example:
```json
{
  "ok": true,
  "agent_id": "A",
  "goal": "demo",
  "action": {"type": "chat", "text": "Hello from A"},
  "mcp_snapshot": {...}
}
````

## Gateway (WebSocket)

* URL: `ws://localhost:3000`
* Message format:

  ```json
  {"type": "chat", "text": "Hello world"}
  ```
* Current behavior: Echoes message back (mock).
* Later: Full Mineflayer integration.
