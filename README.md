# MCP-Craft: Local LLM Minecraft Agents (Windows 11)

This repository contains a **practical, Windows-first** setup to run and evaluate LLM agents in Minecraft,
using a **Model Context Protocol (MCP)**, **Agent-to-Agent (A2A)** messaging, and a **vector memory (RAG)**.

> Goal: From zero → a working *experimental environment* with clear docs and reproducibility.

---

## 🌱 Branching Strategy

- **`main`** → stable, tagged releases (e.g. `v0.1.0`).  
- **`dev`** → active development branch.  
- **Feature branches** → always branched from `dev`, merged back into `dev` via PR.  
  Example:  
  - `feat/mcp`  
  - `feat/a2a`  
  - `feat/memory`  
  - `paper/...`  

---

## 🚀 Quickstart

1. **Install** (Windows 11):
   - Java 17, Node.js ≥ 18, Python ≥ 3.11, Git
   - (Optional) Docker Desktop (for Redis/Chroma services)

2. **Clone & open** in VS Code:
   ```powershell
   git clone https://github.com/<YOUR_USERNAME>/minecraft-llm-agents.git
   cd minecraft-llm-agents
    ```

3. **Start gateway**:

   ```powershell
   cd bot-gateway
   npm i
   npm run dev
   ```

4. **Start orchestrator**:

   ```powershell
   cd orchestrator
   python -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   pip install -e .
   uvicorn app.main:app --reload --port 8000
   ```

5. Open **Swagger UI** → [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📂 Repository Layout

```
orchestrator/   # Python FastAPI orchestrator (MCP, Planner, Memory, A2A)
bot-gateway/    # Node.js + (future) Mineflayer gateway (WS/RPC)
server/         # Minecraft server configs (Paper/Fabric)
docs/           # Beginner-friendly docs for setup & experiments
scripts/        # Convenience scripts (PowerShell & Python)
paper/          # NeurIPS-style paper (optional, research write-up)
compose.yaml    # Optional services (Redis, Chroma)
```

---

## 🧪 Experiments

We provide three starter scenarios:

* **S1** Shelter before first night
* **S2** Stone pickaxe from scratch
* **S3** Cooperative furnace + glass (A2A)

Details: [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)

---

## 📑 Documentation

* [Setup Guide (Windows 11)](docs/SETUP_WINDOWS.md)
* [MCP Schema](docs/MCP_SCHEMA.md)
* [API Overview](docs/API.md)
* [Experiments](docs/EXPERIMENTS.md)

---

## 📜 License

MIT (see [LICENSE](LICENSE)).
