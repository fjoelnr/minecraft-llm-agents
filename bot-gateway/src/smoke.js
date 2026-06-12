/**
 * Stage-0 smoke test: prove embodiment end-to-end without the orchestrator.
 *
 * Connects one bot to the sandbox server, prints an MCP-shaped observation,
 * sends a chat line, walks forward for a few seconds, and reports the distance
 * actually travelled. Exit code 0 = embodiment works.
 *
 *   cd bot-gateway && npm run smoke
 */
import { McAgent } from './mcAgent.js'

const agent = new McAgent({ username: process.env.MC_USERNAME || 'SmokeBot' })

try {
  console.log(`Connecting to ${agent.opts.host}:${agent.opts.port} as ${agent.opts.username} ...`)
  await agent.connect()
  console.log('Spawned. Observation:')
  console.log(JSON.stringify(agent.getObservation(), null, 2))

  agent.bot.chat('Hello world — MCP-Craft agent online.')

  const start = agent.bot.entity.position.clone()
  agent.bot.setControlState('forward', true)
  await sleep(3000)
  agent.bot.setControlState('forward', false)
  const dist = agent.bot.entity.position.distanceTo(start)
  console.log(`Walked ${dist.toFixed(2)} blocks.`)
  console.log('Observation after move:')
  console.log(JSON.stringify(agent.getObservation(), null, 2))

  await sleep(500)
  agent.disconnect()
  console.log(dist > 0.5 ? 'SMOKE OK: agent is embodied and moving.' : 'SMOKE WARN: agent connected but did not move.')
  process.exit(dist > 0.5 ? 0 : 2)
} catch (e) {
  console.error('SMOKE FAIL:', e?.message || e)
  process.exit(1)
}

function sleep (ms) {
  return new Promise((r) => setTimeout(r, ms))
}
