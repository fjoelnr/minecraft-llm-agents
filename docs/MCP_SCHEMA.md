# MCP JSON Schema

The **Model Context Protocol (MCP)** ensures deterministic prompts for the LLM.

```json
{
  "agent_id": "A",
  "goal": "Craft stone pickaxe",
  "env": {"pos":[100,64,-20], "time_of_day":"dusk"},
  "inventory": {"log":6, "cobble":1},
  "skills_index": ["craft_planks","craft_sticks"],
  "rag_snippets": ["recipe: planks=log*4"],
  "team": {"teammates":["B"], "messages":["B: I'll mine stone east."]}
}
````

### Notes

* **Deterministic key order** (always the same order of keys).
* **LLM outputs** must be strict JSON actions (validated).
* **Team** section captures messages from A2A communication.
