# Experiments

We provide three initial scenarios to test MCP-Craft.

---

## S1 — Shelter before first night
- Build a 3×3×3 hut (door + torch) before the first night.
- Measure: success rate, number of steps, time-to-achieve.

## S2 — Stone pickaxe from scratch
- From empty inventory → craft a stone pickaxe.
- Measure: steps to achieve, retries, stability across seeds.

## S3 — Cooperative furnace + glass (A2A)
- Two agents coordinate:
  - Agent A: collect wood → fuel
  - Agent B: collect sand + cobblestone
  - Together: craft furnace + smelt glass
- Measure: team vs solo efficiency, comms overhead.

---

## Metrics

- **SR**: success rate
- **TTA**: time-to-achieve
- **AA**: number of actions
- **ERR**: error/repair rate
- **Comms**: messages exchanged (A2A)
