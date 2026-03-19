# MCP-Craft

Windows-first local LLM agents for Minecraft, built around a deterministic Model Context Protocol (MCP), Agent-to-Agent (A2A) coordination, and vector memory.

This repository is an experimental engineering sandbox, not a polished end-user product. The goal is reproducible local agent experiments with a clear separation between the Minecraft-facing gateway and the Python orchestrator.

## What It Does

- runs a FastAPI orchestrator for MCP planning, memory, and A2A flows
- exposes a Node.js gateway layer for Minecraft-side messaging and future Mineflayer integration
- provides starter experiment scenarios for evaluating agent behavior
- keeps the stack local-first and inspectable for development and testing

## Current Focus

The current focus is practical local experimentation:

- MCP-shaped agent context
- strict JSON action flow
- A2A coordination patterns
- vector memory / retrieval support
- reproducible Windows 11 setup

## Quick Start

1. Install Java 17, Node.js 18+, Python 3.11+, and Git.
2. Clone the repository.
3. Start the gateway:

```powershell
cd bot-gateway
npm i
npm run dev
```

4. Start the orchestrator:

```powershell
cd orchestrator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --reload --port 8000
```

5. Open [http://localhost:8000/docs](http://localhost:8000/docs) and verify `/health`.

Primary docs:
- [docs/SETUP_WINDOWS.md](docs/SETUP_WINDOWS.md)
- [docs/API.md](docs/API.md)
- [docs/MCP_SCHEMA.md](docs/MCP_SCHEMA.md)
- [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/STATUS.md](docs/STATUS.md)

## Architecture

High-level flow:

1. The gateway handles Minecraft-facing communication and future bot integration.
2. The orchestrator receives goals and context over HTTP.
3. MCP structures the state passed into the planning loop.
4. Memory and A2A components enrich decision-making.
5. The system returns validated actions or guidance for the next step.

Repository layout:

```text
bot-gateway/    Node.js gateway and Minecraft-facing entry point
orchestrator/   FastAPI app for MCP, memory, schemas, and A2A logic
docs/           setup, API, experiments, status, and architecture notes
paper/          optional research write-up assets
.agents/        ANR context, workflows, and guardrails
```

## Status

`minecraft-llm-agents` is an active prototype.

- the orchestrator and test suite are present
- the gateway is intentionally still a lighter-weight entry point
- documentation is improving, but this is still a builder-oriented repo

See [docs/STATUS.md](docs/STATUS.md) for the current project state.

## ANR Context Layer

This repository now includes a lightweight ANR-compatible context layer:

- [AGENTS.md](AGENTS.md) for repo-wide context
- [.agents/context-index.md](.agents/context-index.md) for navigation
- [.agents/workflows/feature-development.md](.agents/workflows/feature-development.md) for execution flow
- [.agents/guardrails/architecture-rules.md](.agents/guardrails/architecture-rules.md) for structural constraints

The goal is simple: an agent should be able to enter the repo and understand how the system is organized before changing it.

## Branching

- `main` is the stable release branch
- `develop` is the default integration branch
- feature branches should branch from `develop` and merge back into `develop`
- promotion from `develop` to `main` happens via reviewed pull request

## License

MIT, see [LICENSE](LICENSE).
