# Agent Sandbox Server

A local vanilla **Minecraft 1.20.1** server tuned for headless Mineflayer agents
(`online-mode=false`, `enforce-secure-profile=false`, peaceful). This decouples
agent experiments from the modded survival world, so bots connect over the plain
vanilla protocol with no Forge handshake to fight.

> Runtime artifacts (`server.jar`, `agent-sandbox/` world, logs) are gitignored.
> Only the config and scripts are tracked.

## One-time setup

1. **Java 17** — either install Temurin 17, or let `start.ps1` reuse the Java
   runtime that Prism/Mojang provisions (no install needed if you've run MC once).
2. **Download the server jar** (verified 1.20.1 server):

   ```powershell
   $url = "https://piston-data.mojang.com/v1/objects/84194a2f286ef7c14ed7ce0090dba59902951553/server.jar"
   Invoke-WebRequest $url -OutFile "sandbox-server\server.jar"
   # SHA1 should be 84194a2f286ef7c14ed7ce0090dba59902951553
   ```

## Run

```powershell
# Terminal 1 — start the world (port 25565, offline-mode)
cd sandbox-server
.\start.ps1
```

```powershell
# Terminal 2 — prove embodiment (Stage-0 smoke test)
cd bot-gateway
npm install        # first time only
npm run smoke      # connects one bot, observes, walks, chats

# Or run the gateway that bridges the orchestrator over ws://localhost:3000
npm run dev
```

Environment overrides for the bot: `MC_HOST`, `MC_PORT`, `MC_USERNAME`, `MC_VERSION`.

## Gateway protocol (ws://localhost:3000)

| Message | Result |
|---|---|
| `{"type":"observe"}` | `{ ok, observation }` — MCP-shaped state |
| `{"type":"chat","text":"..."}` | sends chat |
| `{"type":"mine","target":"oak_log","qty":3}` | navigates + mines |
| `{"type":"move","blocks":N}` | walks forward N blocks |

The observation matches the orchestrator's MCP env shape
(`pos`, `time_of_day`, `biome`, `nearby`, plus `inventory`, `health`, `food`).

## Known polish items

- `biome` currently resolves to an empty string near spawn (minecraft-data biome
  name lookup); cosmetic, fix when wiring richer perception.
