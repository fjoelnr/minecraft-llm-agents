/**
 * Skill proof: drive one bot through the wooden-pickaxe tech tree via skills only.
 * This de-risks the hard part (collect -> craft chain -> place table -> craft tool)
 * before the LLM planning layer is wired on top.
 *
 *   cd bot-gateway && node ./src/test-skills.js
 */
import { McAgent } from './mcAgent.js'

const agent = new McAgent({ username: process.env.MC_USERNAME || 'SkillBot' })
const log = (label, r) => console.log(label.padEnd(28), JSON.stringify(r))

try {
  await agent.connect()
  console.log('spawned, inv:', JSON.stringify(agent.getObservation().inventory))

  log('collect spruce_log x3', await agent.runSkill('collect', { type: 'spruce_log', count: 3 }))
  log('craft spruce_planks x3', await agent.runSkill('craft', { item: 'spruce_planks', count: 3 }))
  log('craft crafting_table', await agent.runSkill('craft', { item: 'crafting_table', count: 1 }))
  log('craft stick', await agent.runSkill('craft', { item: 'stick', count: 1 }))
  log('place crafting_table', await agent.runSkill('place', { type: 'crafting_table' }))
  log('craft wooden_pickaxe', await agent.runSkill('craft', { item: 'wooden_pickaxe', count: 1 }))

  const inv = agent.getObservation().inventory
  console.log('final inv:', JSON.stringify(inv))
  const ok = (inv.wooden_pickaxe || 0) > 0
  console.log(ok ? 'PICKAXE OK: full tech tree works via skills.' : 'PICKAXE FAIL: see steps above.')
  agent.disconnect()
  process.exit(ok ? 0 : 2)
} catch (e) {
  console.error('SKILL TEST ERROR:', e?.message || e)
  process.exit(1)
}
