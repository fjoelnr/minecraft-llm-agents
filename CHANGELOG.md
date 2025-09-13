# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- (planned) Vector memory (Chroma/Embeddings) integration
- (planned) Agent-to-Agent communication via Gateway/Redis
- (planned) GitHub Actions for CI/CD

---

## [0.2.0] - 2025-09-13
### Added
- **MCP Schema & Validator**
  - Pydantic-based `MCPContext` with deterministic key order
  - JSON schema endpoint (`GET /mcp/schema`)
  - State retrieval endpoint (`GET /state`)

- **Action Schema**
  - Unified schema for `chat`, `mine`, `craft`
  - Validation + normalization of LLM outputs

- **FastAPI Orchestrator**
  - `/step` builds MCP snapshot, validates it, and returns validated action
  - In-memory state storage per agent

- **Tests**
  - Added unit tests for MCP, A2A skeleton, Memory skeleton, and Action schema
  - All tests passing on Windows 11, Python 3.13

- **Documentation**
  - Beginner-friendly setup guide (`docs/SETUP_WINDOWS.md`)
  - MCP schema, API overview, and experiments documentation

### Notes
- First stable baseline, to be tagged as **v0.2.0**
- `main` branch now represents reproducible experimental environment

---

[Unreleased]: https://github.com/fjoelnr/minecraft-llm-agents/compare/main...dev
[0.2.0]: https://github.com/fjoelnr/minecraft-llm-agents/releases/tag/v0.2.0
