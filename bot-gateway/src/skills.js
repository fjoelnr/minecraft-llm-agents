/**
 * Skill library — multi-step competences the planner composes, instead of the
 * agent emitting one primitive action per tick. Each skill is a parameterized
 * routine over the Mineflayer API that reports a structured result.
 *
 * This is the "skills as gateway capabilities" middle ground toward Voyager-style
 * code-as-action: the LLM chooses skills + args (a plan step), the body executes
 * the multi-step detail (navigation, tool selection, the crafting tech tree).
 */
import pathfinderPkg from 'mineflayer-pathfinder'
import minecraftData from 'minecraft-data'
import { Vec3 } from 'vec3'

const { goals } = pathfinderPkg

/** Collect `count` blocks of a type: find -> navigate -> mine -> pick up drops. */
export async function collect (bot, { type, count = 1 }) {
  const mcData = minecraftData(bot.version)
  const blockType = mcData.blocksByName[type]
  if (!blockType) return { ok: false, error: `unknown block: ${type}` }

  const positions = bot.findBlocks({ matching: blockType.id, maxDistance: 32, count: Math.max(count * 3, 8) })
  if (!positions.length) return { ok: false, error: `no ${type} within range` }

  // Refuse blocks we cannot harvest with current tools (e.g. stone bare-handed):
  // digging would drop nothing, and collectBlock spins itself into OOM retrying.
  if (blockType.harvestTools) {
    const toolIds = Object.keys(blockType.harvestTools).map(Number)
    const hasTool = bot.inventory.items().some((i) => toolIds.includes(i.type))
    if (!hasTool) {
      const toolNames = toolIds.map((id) => mcData.items[id]?.name).filter(Boolean).slice(0, 3)
      return { ok: false, error: `need a proper tool for ${type} (e.g. ${toolNames.join(', ')})` }
    }
  }

  // Success is measured by a full inventory diff, because many blocks drop a
  // different item than their own name (stone -> cobblestone, coal_ore -> coal).
  const before = inventorySnapshot(bot)
  const targets = positions.slice(0, count).map((p) => bot.blockAt(p)).filter(Boolean)
  try {
    await bot.collectBlock.collect(targets, { ignoreNoPath: true })
  } catch (e) {
    // partial success is fine; report what we got
  }
  const gains = inventoryGains(before, inventorySnapshot(bot))
  const gained = Object.values(gains).reduce((s, n) => s + n, 0)
  return {
    ok: gained > 0,
    skill: 'collect',
    type,
    gained,
    gains,
    requested: count,
    ...(gained === 0 ? { error: `dug but nothing collected (drops out of reach?)` } : {})
  }
}

/**
 * Craft `count` of an item. Carries the crafting tech tree: missing intermediate
 * ingredients (logs -> planks -> sticks) are crafted recursively, and a crafting
 * table is crafted + placed when the recipe needs one. The planner can just say
 * craft("wooden_pickaxe") with raw logs in the inventory.
 */
export async function craft (bot, { item, count = 1 }) {
  const mcData = minecraftData(bot.version)
  const target = mcData.itemsByName[item]
  if (!target) return { ok: false, error: `unknown item: ${item}` }
  const r = await craftResolved(bot, target.id, count, 0, new Set())
  if (!r.ok) return r
  return { ok: true, skill: 'craft', item, count, have: countItem(bot, item) }
}

const MAX_CRAFT_DEPTH = 5

async function craftResolved (bot, itemId, count, depth, visited) {
  const mcData = minecraftData(bot.version)
  const name = mcData.items[itemId]?.name || String(itemId)
  if (depth > MAX_CRAFT_DEPTH) return { ok: false, error: `craft chain too deep at ${name}` }
  if (visited.has(itemId)) return { ok: false, error: `craft cycle at ${name}` }
  visited.add(itemId)

  // 1) Directly craftable in the 2x2 grid with current inventory?
  let recipes = bot.recipesFor(itemId, null, count, null)
  if (recipes.length) return await doCraft(bot, recipes[0], count, null, name)

  // recipesAll ignores inventory. table=null returns only 2x2 recipes, table=truthy
  // returns all — "needs a table" means: no 2x2 recipe exists but a table one does.
  // (Getting this wrong earlier caused an infinite recursion that crashed the gateway.)
  const twoByTwo = bot.recipesAll(itemId, null, null)
  const anyRecipe = bot.recipesAll(itemId, null, true)
  if (!anyRecipe.length) return { ok: false, error: `no recipe for ${name}` }

  let table = null
  if (!twoByTwo.length) {
    // Genuine table recipe: make sure a table stands nearby first.
    table = findNearby(bot, 'crafting_table', 4)
    if (!table) {
      const ensured = await ensureCraftingTable(bot, depth, visited)
      if (!ensured.ok) return { ok: false, error: ensured.error }
      table = findNearby(bot, 'crafting_table', 4)
    }
    recipes = bot.recipesFor(itemId, null, count, table)
    if (recipes.length) return await doCraft(bot, recipes[0], count, table, name)
  }

  // 2) Ingredients missing: try each candidate recipe and craft what it lacks.
  const candidates = twoByTwo.length ? twoByTwo : anyRecipe
  for (const recipe of candidates) {
    const missing = missingIngredients(bot, recipe, count)
    let resolved = true
    for (const { id, need } of missing) {
      const sub = await craftResolved(bot, id, need, depth + 1, new Set(visited))
      if (!sub.ok) { resolved = false; break }
    }
    if (!resolved) continue
    const retry = bot.recipesFor(itemId, null, count, table)
    if (retry.length) return await doCraft(bot, retry[0], count, table, name)
  }
  return { ok: false, error: `missing ingredients for ${name}` }
}

/** Inputs of `recipe` (delta < 0) the inventory cannot cover for `count` crafts. */
function missingIngredients (bot, recipe, count) {
  const out = []
  for (const d of recipe.delta) {
    if (d.count >= 0) continue
    const need = -d.count * count
    const have = bot.inventory.items().filter((i) => i.type === d.id).reduce((s, i) => s + i.count, 0)
    if (have < need) out.push({ id: d.id, need: need - have })
  }
  return out
}

async function doCraft (bot, recipe, count, table, item) {
  try {
    await bot.craft(recipe, count, table || null)
    return { ok: true, skill: 'craft', item, count, have: countItem(bot, item) }
  } catch (e) {
    return { ok: false, error: `craft failed: ${String(e?.message || e)}` }
  }
}

/** Place a block of `type` from inventory on a free spot beside the bot. */
export async function place (bot, { type }) {
  const item = bot.inventory.items().find((i) => i.name === type)
  if (!item) return { ok: false, error: `no ${type} in inventory` }
  await bot.equip(item, 'hand')
  const spot = freeSpotBeside(bot)
  if (!spot) return { ok: false, error: 'no free spot to place against' }
  try {
    await bot.lookAt(spot.place.offset(0.5, 0.5, 0.5), true)
    await bot.placeBlock(spot.ref, spot.face)
    return { ok: true, skill: 'place', type, pos: [spot.place.x, spot.place.y, spot.place.z] }
  } catch (e) {
    return { ok: false, error: `place failed: ${String(e?.message || e)}` }
  }
}

// Solid blocks we are willing to build with, in preference order.
const BUILD_MATERIALS = [
  'cobblestone', 'dirt', 'stone', 'spruce_planks', 'oak_planks', 'birch_planks',
  'jungle_planks', 'acacia_planks', 'dark_oak_planks', 'spruce_log', 'oak_log'
]

/**
 * Build a small hut around the bot's current position: 8 wall columns (2 high)
 * with one door gap, plus a 3x3 roof. Uses whatever solid blocks are in the
 * inventory. The bot ends up standing inside its own shelter.
 */
export async function buildShelter (bot) {
  const have = bot.inventory.items()
    .filter((i) => BUILD_MATERIALS.includes(i.name))
    .reduce((s, i) => s + i.count, 0)
  if (have < 20) return { ok: false, error: `need ~24 solid blocks to build (have ${have}) — collect dirt/cobblestone/planks first` }

  const c = bot.entity.position.floored()
  const ring = [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]]
  const door = [1, 0] // leave the +x middle column open as a doorway

  let placedNew = 0
  let preSolid = 0
  const failedSpots = []
  const spot = async (pos) => {
    const r = await placeAt(bot, pos)
    if (r === 'placed') placedNew++
    else if (r === 'solid') preSolid++
    else failedSpots.push([pos.x, pos.y, pos.z])
  }
  for (const dy of [0, 1]) {
    for (const [dx, dz] of ring) {
      if (dx === door[0] && dz === door[1]) continue
      await spot(c.offset(dx, dy, dz))
    }
  }
  for (let dx = -1; dx <= 1; dx++) {
    for (let dz = -1; dz <= 1; dz++) {
      await spot(c.offset(dx, 2, dz))
    }
  }

  const filled = placedNew + preSolid
  const ok = filled >= 17 // 23 spots total; a few gaps are survivable
  return {
    ok,
    skill: 'build_shelter',
    placed: placedNew,
    already_solid: preSolid,
    failed: failedSpots.length,
    pos: [c.x, c.y, c.z],
    ...(ok ? {} : { error: `shelter incomplete: ${filled}/23 spots filled` })
  }
}

/** Fill `pos` with a build material. Returns 'placed' | 'solid' | false. */
async function placeAt (bot, pos) {
  const at = bot.blockAt(pos)
  if (!at) return false
  if (at.boundingBox === 'block') return 'solid' // terrain already covers this spot
  const dirs = [[0, -1, 0], [0, 1, 0], [1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1]]
  let ref = null
  let face = null
  for (const [dx, dy, dz] of dirs) {
    const n = bot.blockAt(pos.offset(dx, dy, dz))
    if (n && n.boundingBox === 'block') { ref = n; face = new Vec3(-dx, -dy, -dz); break }
  }
  if (!ref) return false
  const item = bot.inventory.items().find((i) => BUILD_MATERIALS.includes(i.name))
  if (!item) return false
  try {
    await bot.equip(item, 'hand')
    await bot.lookAt(pos.offset(0.5, 0.5, 0.5), true)
    await bot.placeBlock(ref, face)
    return 'placed'
  } catch {
    return false
  }
}

/** Equip the named tool/item to the hand. */
export async function equip (bot, { type }) {
  const item = bot.inventory.items().find((i) => i.name === type)
  if (!item) return { ok: false, error: `no ${type} in inventory` }
  await bot.equip(item, 'hand')
  return { ok: true, skill: 'equip', type }
}

// --- helpers ---------------------------------------------------------------

function countItem (bot, name) {
  return bot.inventory.items().filter((i) => i.name === name).reduce((s, i) => s + i.count, 0)
}

function inventorySnapshot (bot) {
  const snap = {}
  for (const i of bot.inventory.items()) snap[i.name] = (snap[i.name] || 0) + i.count
  return snap
}

function inventoryGains (before, after) {
  const gains = {}
  for (const [name, n] of Object.entries(after)) {
    const d = n - (before[name] || 0)
    if (d > 0) gains[name] = d
  }
  return gains
}

function findNearby (bot, name, dist) {
  const mcData = minecraftData(bot.version)
  const b = mcData.blocksByName[name]
  if (!b) return null
  return bot.findBlock({ matching: b.id, maxDistance: dist })
}

async function ensureCraftingTable (bot, depth = 0, visited = new Set()) {
  if (findNearby(bot, 'crafting_table', 3)) return { ok: true }
  if (!bot.inventory.items().some((i) => i.name === 'crafting_table')) {
    const mcData = minecraftData(bot.version)
    const c = await craftResolved(bot, mcData.itemsByName.crafting_table.id, 1, depth + 1, new Set(visited))
    if (!c.ok) return { ok: false, error: c.error }
  }
  return await place(bot, { type: 'crafting_table' })
}

// Find an empty cell near the bot that has a solid neighbour to build against,
// scanning a 3x3x2 region and all 6 faces — robust on slopes / among trees.
function freeSpotBeside (bot) {
  const base = bot.entity.position.floored()
  const dirs = [[0, -1, 0], [0, 1, 0], [1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1]]
  const candidates = []
  for (let dy = -1; dy <= 0; dy++) {
    for (let dx = -1; dx <= 1; dx++) {
      for (let dz = -1; dz <= 1; dz++) {
        if (dx === 0 && dz === 0 && dy === 0) continue // bot's own feet
        candidates.push(base.offset(dx, dy, dz))
      }
    }
  }
  for (const place of candidates) {
    const at = bot.blockAt(place)
    if (!at || (at.name !== 'air' && at.boundingBox !== 'empty')) continue
    for (const [dx, dy, dz] of dirs) {
      const ref = bot.blockAt(place.offset(dx, dy, dz))
      if (ref && ref.boundingBox === 'block' && ref.name !== 'crafting_table') {
        return { place, ref, face: new Vec3(-dx, -dy, -dz) }
      }
    }
  }
  return null
}

export const SKILLS = { collect, craft, place, equip, build_shelter: buildShelter }
export const SKILL_NAMES = Object.keys(SKILLS)

export async function runSkill (bot, name, args = {}) {
  const fn = SKILLS[name]
  if (!fn) return { ok: false, error: `unknown skill: ${name}` }
  return await fn(bot, args)
}

// keep pathfinder goals importable for skills that navigate explicitly later
export { goals }
