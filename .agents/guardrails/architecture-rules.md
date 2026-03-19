# Architecture Rules

- Keep Minecraft-facing integration concerns in `bot-gateway/`.
- Keep planning, MCP, memory, and API concerns in `orchestrator/`.
- Do not mix setup documentation with speculative product claims.
- Preserve deterministic interfaces where the docs already define them.
- Prefer additive changes to the docs over silent behavioral drift.
