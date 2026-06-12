# Agent Loop — the vertical slice

The end-to-end path from world perception to a world action, threaded through every
layer with real components (no stubs). This is the "technological through-line" that
de-risks the integration before we build depth on top of it.

```
sandbox world ──observe──► gateway (Mineflayer) ──WS──► orchestrator
                                                          │
                                            build MCP ◄───┘
                                                │
                                          LLM decide (Ollama)
                                                │
                                          coerce + validate (Action)
                                                │
   world ◄──execute── gateway (Mineflayer) ◄──WS──┘
```

One `tick()` in [`orchestrator/app/agent_loop.py`](../orchestrator/app/agent_loop.py):

1. **perceive** — `GatewayClient.observe()` pulls the MCP-shaped state from the bot.
2. **contextualize** — `build_mcp_from_obs()` maps it onto the MCP schema.
3. **decide** — `llm.decide()` calls the local LLM and returns ONE action.
4. **coerce + validate** — `coerce_action()` + `Action` make the decision robust to
   model output drift, then normalize it.
5. **act** — `GatewayClient.execute_action()` runs it in the world.

## Run it

```powershell
# Terminal 1: sandbox world
cd sandbox-server; .\start.ps1

# Terminal 2: gateway (one embodied bot + WS bridge)
cd bot-gateway; npm run dev

# Terminal 3: the loop
cd orchestrator
.\.venv\Scripts\Activate.ps1
python -m app.agent_loop --goal "Explore the area and comment in chat" --ticks 5
```

Env knobs: `LLM_PROVIDER` (ollama|dummy), `LLM_MODEL`, `OLLAMA_URL`,
`GATEWAY_URL`, `GATEWAY_TIMEOUT`, `TICK_INTERVAL`.

## What the slice surfaced (and how it's handled)

- **LLM key drift** — models emit `{"action":...}` or `{"message":...}` instead of
  the exact schema. `coerce_action()` maps the common variants so a correct decision
  is never lost to a key name. Covered by `tests/test_agent_slice.py`.
- **Vocabulary gap** — the action vocab (`chat/mine/craft/move`) must match across
  LLM ↔ orchestrator ↔ gateway. `move` was added to the `Action` schema.
- **Pathfinder timeouts** — "walk N blocks forward" used pathfinding and failed on
  rough terrain. `moveForward()` now uses control-state walking; pathfinding is kept
  for precise `goto()`/`mine()` only.

## Known limits (next to address)

- Small local models (e.g. gemma) hallucinate state (claiming inventory they lack).
  Mitigate with a stronger model (qwen) and/or tighter prompting + grounding.
- Single agent only. Multi-agent + A2A is the next stage.
- Perception is shallow (position, nearby entities, inventory). Richer perception
  (block scans, reachable resources) comes with the cognitive layer.
