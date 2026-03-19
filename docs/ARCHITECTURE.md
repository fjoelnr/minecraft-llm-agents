# Architecture

## Overview

`minecraft-llm-agents` is split into two main runtime zones:

- `bot-gateway/` handles the Minecraft-facing connection layer
- `orchestrator/` handles HTTP APIs, MCP shaping, memory, and coordination logic

This separation is intentional. It keeps game-facing integration concerns independent from planning and reasoning concerns.

## Request Flow

1. A local client or integration sends a goal or event into the system.
2. The orchestrator builds a deterministic MCP payload.
3. Optional memory retrieval enriches that payload with relevant snippets.
4. A2A state can add teammate coordination context.
5. The orchestrator returns a validated next action.
6. The gateway can relay that action into the Minecraft-side integration layer.

## Repository Design

- `orchestrator/app/` contains the FastAPI app, schemas, memory modules, and adapters.
- `orchestrator/tests/` covers the core API and memory behavior.
- `bot-gateway/src/` contains the Node.js runtime entry point.
- `docs/` carries user-facing and operator-facing documentation.

## Design Constraints

- keep interfaces deterministic and inspectable
- favor local reproducibility over opaque hosted dependencies
- keep experimental scope explicit in the docs
- preserve a clean split between runtime layers
