# AGENTS.md

## Purpose

This repository contains a local-first Minecraft agent sandbox with a Python orchestrator and a Node.js gateway.
This file is the primary context entry point for coding agents.

## Repository Map

- `orchestrator/` FastAPI application for MCP, memory, schemas, and A2A logic
- `bot-gateway/` Node.js gateway for Minecraft-facing communication
- `docs/` setup, API, experiments, architecture, and status documentation
- `paper/` optional research and write-up material
- `.github/` workflows, issue templates, and repo automation

## Context Hierarchy

1. `AGENTS.md`
2. `.agents/context-index.md`
3. relevant docs in `docs/`
4. `.agents/workflows/`
5. `.agents/guardrails/`

## Working Rules

- Keep the gateway and orchestrator responsibilities clearly separated.
- Prefer small, reviewable changes over broad refactors.
- Update docs when behavior, setup, or workflow changes.
- Treat this repository as an experimental platform, but keep changes reproducible.
