/**
 * Regression test for the crash that killed the gateway: crafting with missing
 * ingredients must return a clean error (not recurse until the stack overflows).
 */
import { McAgent } from './mcAgent.js'

const agent = new McAgent({ username: 'GuardBot' })
await agent.connect()
console.log('inv:', JSON.stringify(agent.getObservation().inventory))

// 1) the old crash case: nothing in inventory -> needs table -> needs planks -> ...
const r1 = await agent.runSkill('craft', { item: 'wooden_pickaxe', count: 1 })
console.log('craft pickaxe (empty inv):', JSON.stringify(r1))

// 2) unknown item stays a clean error
const r2 = await agent.runSkill('craft', { item: 'definitely_not_an_item' })
console.log('craft unknown item:      ', JSON.stringify(r2))

// 3) collecting an unmineable-without-tool block must end, not hang forever
const r3 = await agent.runSkill('collect', { type: 'stone', count: 1 })
console.log('collect stone (no tool): ', JSON.stringify(r3))

agent.disconnect()
const pass = !r1.ok && !r2.ok && typeof r3.ok === 'boolean'
console.log(pass ? 'GUARD OK: failures are clean, no crash.' : 'GUARD FAIL')
process.exit(pass ? 0 : 2)
