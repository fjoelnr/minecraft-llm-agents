/**
 * Bot gateway: connects a pool of embodied agents to the sandbox server and bridges
 * the orchestrator + observers over WebSocket (ws://localhost:3000).
 *
 * Agents are named via MC_AGENTS (comma-separated, default "Agent1,Agent2").
 *
 * Protocol (JSON per message):
 *   { "type":"agents" }                                  -> { ok, agents:[...] }
 *   { "type":"scene" }                                   -> { ok, scene }  (all players, agents, recent chat)
 *   { "type":"observe", "agent":"Agent1" }               -> { ok, observation }
 *   { "type":"chat"|"mine"|"move"|"goto", "agent":..., }  -> action result
 * If "agent" is omitted the first agent is used. Unknown agent / bad json -> { ok:false }.
 */
import { WebSocketServer } from 'ws'
import { McAgent } from './mcAgent.js'

const names = (process.env.MC_AGENTS || 'Agent1,Agent2')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)

const agents = new Map()
const chatLog = [] // ring buffer of recent chat lines for observation

for (const name of names) {
  const agent = new McAgent({ username: name })
  console.log(`Connecting ${name} ...`)
  await agent.connect()
  agents.set(name, agent)
  console.log(`  ${name} spawned at ${agent.getObservation().pos}`)
}

// Capture chat once (via the first bot) so observers get the world's narrative.
const firstAgent = agents.get(names[0])
firstAgent.bot.on('messagestr', (message) => {
  chatLog.push({ ts: Date.now(), text: message })
  if (chatLog.length > 100) chatLog.shift()
})

const wss = new WebSocketServer({ port: 3000 })
console.log(`Gateway WS listening on ws://localhost:3000 (agents: ${names.join(', ')})`)

wss.on('connection', (ws) => {
  ws.on('message', async (msg) => {
    let data
    try {
      data = JSON.parse(msg.toString())
    } catch {
      return ws.send(JSON.stringify({ ok: false, error: 'bad json' }))
    }

    if (data.type === 'agents') {
      return ws.send(JSON.stringify({ ok: true, agents: [...agents.keys()] }))
    }
    if (data.type === 'scene') {
      return ws.send(JSON.stringify({ ok: true, scene: buildScene() }))
    }

    const agent = agents.get(data.agent || names[0])
    if (!agent) {
      return ws.send(JSON.stringify({ ok: false, error: `unknown agent: ${data.agent}` }))
    }
    if (data.type === 'observe') {
      const observation = agent.getObservation()
      // A2A context: where the other agents are right now
      observation.teammates = [...agents.entries()]
        .filter(([n]) => n !== (data.agent || names[0]))
        .map(([n, a]) => {
          const o = a.getObservation()
          return `${n}@[${(o.pos || []).join(',')}]`
        })
      return ws.send(JSON.stringify({ ok: true, observation }))
    }
    try {
      if (data.type === 'skill') {
        ws.send(JSON.stringify(await agent.runSkill(data.name, data.args || {})))
      } else {
        ws.send(JSON.stringify(await agent.execute(data)))
      }
    } catch (e) {
      ws.send(JSON.stringify({ ok: false, error: String(e?.message || e) }))
    }
  })
})

/** Aggregate world view: every player (incl. humans + agents) and recent chat. */
function buildScene () {
  const bot = firstAgent.bot
  const players = Object.values(bot.players)
    .filter((p) => p.username)
    .map((p) => ({
      name: p.username,
      is_agent: agents.has(p.username),
      pos: p.entity
        ? [Math.round(p.entity.position.x), Math.round(p.entity.position.y), Math.round(p.entity.position.z)]
        : null
    }))
  return {
    ts: Date.now(),
    players,
    agents: [...agents.values()].map((a) => a.getObservation()),
    recent_chat: chatLog.slice(-15)
  }
}
