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

### Memory (Vector/RAG)

### Memory (Vector/RAG) — Collections & Batch

- `GET /memory/collections`
  - list available collections
- `GET /memory/stats?collection=mem_general_v1`
  - item count, persist dir
- `DELETE /memory/collection?collection=mem_foo`
  - drop a collection

- `POST /memory/add_batch`
  ```json
  { "texts": ["recipe: ...", "tip: ..."], "kind": "note", "metadatas": [{"src":"..."}], "collection": "mem_recipes_v1" }
  ```

- `POST /memory/add`
  - body: `{ "text": "...", "kind": "note|recipe|...", "metadata": { "seed": "abc" } }`
  - returns: `{ "ok": true, "id": "m_1" }`

- `POST /memory/query`
  - body: `{ "query": "planks", "top_k": 3 }`
  - returns: `{ "ok": true, "items": [ { id, text, metadata, distance }, ... ] }`

- `POST /step?use_memory=true`
  - injects top-k snippets into `mcp.rag_snippets`.

- `POST /step?use_memory=true&mem_collection=mem_recipes_v1`
  - injects RAG snippets from the given collection
