import mineflayer from 'mineflayer'
import pathfinderPkg from 'mineflayer-pathfinder'
import minecraftData from 'minecraft-data'

const { pathfinder, Movements, goals } = pathfinderPkg

/**
 * McAgent — thin embodiment wrapper around a Mineflayer bot.
 *
 * Produces observations in the orchestrator's MCP shape (see orchestrator/app/mcp.py:
 * MCPEnv = {pos, time_of_day, biome, nearby} plus inventory) and executes the
 * orchestrator's Action schema (chat | mine | craft), with a couple of movement
 * helpers used by the Stage-0 smoke test.
 */
export class McAgent {
  constructor (opts = {}) {
    this.opts = {
      host: opts.host || process.env.MC_HOST || 'localhost',
      port: Number(opts.port || process.env.MC_PORT || 25565),
      username: opts.username || process.env.MC_USERNAME || 'Agent1',
      version: opts.version || process.env.MC_VERSION || '1.20.1',
      auth: 'offline'
    }
    this.bot = null
    this.ready = false
  }

  /** Connect and resolve once the bot has spawned into the world. */
  connect () {
    return new Promise((resolve, reject) => {
      const bot = mineflayer.createBot(this.opts)
      this.bot = bot
      bot.loadPlugin(pathfinder)

      bot.once('spawn', () => {
        const mcData = minecraftData(bot.version)
        const moves = new Movements(bot, mcData)
        bot.pathfinder.setMovements(moves)
        this.ready = true
        resolve(this)
      })
      bot.once('error', reject)
      bot.once('kicked', (reason) => reject(new Error(`kicked: ${reason}`)))
      bot.on('end', () => { this.ready = false })
    })
  }

  /** Structured world state in the MCP observation shape. */
  getObservation () {
    const bot = this.bot
    if (!bot || !bot.entity) return { ready: false }
    const p = bot.entity.position
    const mcData = minecraftData(bot.version)
    const here = bot.blockAt(p)
    const under = bot.blockAt(p.offset(0, -1, 0))
    return {
      agent_id: this.opts.username,
      pos: [Math.round(p.x), Math.round(p.y), Math.round(p.z)],
      time_of_day: timeName(bot.time.timeOfDay),
      biome: biomeName(here, mcData),
      standing_on: under?.name ?? null,
      nearby: nearbyNames(bot),
      nearby_blocks: nearbyBlocks(bot, mcData),
      inventory: inventoryMap(bot),
      health: bot.health ?? null,
      food: bot.food ?? null
    }
  }

  /** Execute an action. Accepts the orchestrator Action schema plus move/goto helpers. */
  async execute (action = {}) {
    const bot = this.bot
    if (!this.ready) return { ok: false, error: 'agent not ready' }
    switch (action.type) {
      case 'chat':
        bot.chat(String(action.text ?? ''))
        return { ok: true, type: 'chat' }
      case 'move':
        return await this.moveForward(Number(action.blocks ?? 1))
      case 'goto':
        return await this.goto(action.x, action.y, action.z)
      case 'mine':
        return await this.mine(String(action.target ?? ''), Number(action.qty ?? 1))
      case 'craft':
        return { ok: false, error: 'craft not implemented yet' }
      default:
        return { ok: false, error: `unknown action type: ${action.type}` }
    }
  }

  /**
   * Walk roughly `blocks` blocks forward via control state. Deliberately avoids the
   * pathfinder here: "explore a bit forward" should never fail on rough terrain, and
   * pathfinding to a blind point ahead times out too easily. Pathfinding is reserved
   * for goto()/mine() where a precise destination matters.
   */
  async moveForward (blocks = 1) {
    const bot = this.bot
    const start = bot.entity.position.clone()
    const target = Math.max(1, Math.min(10, blocks))
    const timeoutMs = Math.min(10000, 700 * target + 800)
    bot.setControlState('forward', true)
    bot.setControlState('jump', true) // hop small steps so we don't get stuck
    await new Promise((resolve) => {
      const iv = setInterval(() => {
        if (bot.entity.position.distanceTo(start) >= target) {
          clearInterval(iv)
          clearTimeout(to)
          resolve()
        }
      }, 100)
      const to = setTimeout(() => {
        clearInterval(iv)
        resolve()
      }, timeoutMs)
    })
    bot.setControlState('forward', false)
    bot.setControlState('jump', false)
    const np = bot.entity.position
    return {
      ok: true,
      type: 'move',
      moved: Number(np.distanceTo(start).toFixed(2)),
      pos: [Math.round(np.x), Math.round(np.y), Math.round(np.z)]
    }
  }

  /** Pathfind to a coordinate. */
  async goto (x, y, z) {
    await this.bot.pathfinder.goto(new goals.GoalNear(Number(x), Number(y), Number(z), 1))
    const np = this.bot.entity.position
    return { ok: true, type: 'goto', pos: [Math.round(np.x), Math.round(np.y), Math.round(np.z)] }
  }

  /** Find the nearest block of `target` type, walk to it, and mine `qty` of them. */
  async mine (target, qty = 1) {
    const bot = this.bot
    const mcData = minecraftData(bot.version)
    const blockType = mcData.blocksByName[target]
    if (!blockType) return { ok: false, error: `unknown block: ${target}` }

    let mined = 0
    for (let i = 0; i < qty; i++) {
      const block = bot.findBlock({ matching: blockType.id, maxDistance: 32 })
      if (!block) break
      try {
        await bot.pathfinder.goto(new goals.GoalGetToBlock(block.position.x, block.position.y, block.position.z))
        await bot.dig(block)
        mined++
      } catch {
        break
      }
    }
    return { ok: mined > 0, type: 'mine', target, mined, requested: qty }
  }

  disconnect () {
    if (this.bot) this.bot.quit()
  }
}

function timeName (t) {
  // Minecraft day is 24000 ticks; 0 = sunrise.
  if (t < 6000) return 'morning'
  if (t < 12000) return 'noon'
  if (t < 18000) return 'evening'
  return 'night'
}

function nearbyNames (bot) {
  const me = bot.entity.position
  const names = []
  for (const e of Object.values(bot.entities)) {
    if (e === bot.entity || !e.position) continue
    if (e.position.distanceTo(me) <= 16) {
      names.push(e.username || e.name || e.displayName || e.kind || 'entity')
    }
  }
  return names.slice(0, 20)
}

function biomeName (block, mcData) {
  const b = block?.biome
  if (!b) return null
  if (b.name) return b.name
  if (b.id != null && mcData.biomes?.[b.id]) return mcData.biomes[b.id].name
  return null
}

// Block categories worth perceiving for "gather / build" goals.
const WANTED_BLOCKS = [
  'oak_log', 'birch_log', 'spruce_log', 'jungle_log', 'acacia_log', 'dark_oak_log',
  'mangrove_log', 'cherry_log', 'stone', 'cobblestone', 'coal_ore', 'iron_ore',
  'copper_ore', 'gold_ore', 'diamond_ore', 'sand', 'water'
]

/** Nearest instance of each interesting block type within range, as "name@dist". */
function nearbyBlocks (bot, mcData) {
  const ids = WANTED_BLOCKS.map((n) => mcData.blocksByName[n]?.id).filter((x) => x != null)
  if (!ids.length) return []
  const positions = bot.findBlocks({ matching: ids, maxDistance: 12, count: 48 })
  const me = bot.entity.position
  const nearest = {}
  for (const pos of positions) {
    const block = bot.blockAt(pos)
    if (!block) continue
    const d = pos.distanceTo(me)
    if (!(block.name in nearest) || d < nearest[block.name]) nearest[block.name] = d
  }
  return Object.entries(nearest)
    .sort((a, b) => a[1] - b[1])
    .slice(0, 8)
    .map(([name, d]) => `${name}@${Math.round(d)}`)
}

function inventoryMap (bot) {
  const inv = {}
  for (const item of bot.inventory.items()) {
    inv[item.name] = (inv[item.name] || 0) + item.count
  }
  return inv
}
