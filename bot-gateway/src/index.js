/**
 * Bot gateway: connects one embodied agent to the sandbox server and bridges
 * the orchestrator over WebSocket (ws://localhost:3000).
 *
 * Protocol (JSON per message):
 *   { "type": "observe" }                      -> { ok, observation }
 *   { "type": "chat", "text": "..." }          -> executes, returns result
 *   { "type": "mine", "target": "...", "qty": } -> executes, returns result
 *   { "type": "move", "blocks": N }            -> movement helper
 * Unknown / malformed messages return { ok: false, error }.
 */
import { WebSocketServer } from 'ws'
import { McAgent } from './mcAgent.js'

const agent = new McAgent()

console.log(`Connecting agent to ${agent.opts.host}:${agent.opts.port} as ${agent.opts.username} ...`)
await agent.connect()
console.log('Agent spawned in world.')

const wss = new WebSocketServer({ port: 3000 })
console.log('Gateway WS listening on ws://localhost:3000')

wss.on('connection', (ws) => {
  ws.on('message', async (msg) => {
    let data
    try {
      data = JSON.parse(msg.toString())
    } catch {
      return ws.send(JSON.stringify({ ok: false, error: 'bad json' }))
    }

    if (data.type === 'observe') {
      return ws.send(JSON.stringify({ ok: true, observation: agent.getObservation() }))
    }

    try {
      const result = await agent.execute(data)
      ws.send(JSON.stringify(result))
    } catch (e) {
      ws.send(JSON.stringify({ ok: false, error: String(e?.message || e) }))
    }
  })
})
