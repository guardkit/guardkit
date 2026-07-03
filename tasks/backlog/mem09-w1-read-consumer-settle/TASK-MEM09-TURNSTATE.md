---
id: TASK-MEM09-TURNSTATE
title: Verify turn_states document-payload capture/load round-trip on fleet-memory
status: backlog
created: 2026-07-03T00:00:00Z
priority: medium
feature_id: FEAT-MEM-09
wave: 1
task_type: refactor
complexity: 5
tags: [fleet-memory, degraphiti, turn-states, fork-b, FEAT-MEM-09, per-task-green]
autobuild:
  enabled: true
  max_turns: 5
  base_branch: main
  mode: tdd
---

# Task: Verify turn_states document-payload capture/load round-trip on fleet-memory

> **READ FIRST:** [`IMPLEMENTATION-GUIDE.md`](./IMPLEMENTATION-GUIDE.md) (shim routing §2; two-test pattern §3).

## Description

`guardkit/knowledge/turn_state_operations.py` persists feature-build per-turn history to fleet-memory
(`capture_turn_state`) and loads it for cross-turn context (`load_turn_continuation_context`,
`load_turn_context`), via the shim `get_memory_client()`. **Fork B = follows A = keep** this as cross-turn
context (Fork A keeps autobuild read-enrichment). `turn_states` maps to `document` / `[turn,state]` (migrate).
Settle the write+read and prove the real round-trip.

> **Fork B rationale (do not re-litigate):** `turn_states` in fleet-memory is the *cross-turn context* signal,
> NOT the fine-tune dataset source. The teacher-pairs live on disk at
> `.guardkit/autobuild/{task}/{player,coach}_turn_N.json` (`orchestrator/paths.py:85-90`). Dropping/keeping
> `turn_states`-in-FM does not touch dataset harvesting. A durable dataset sink is a **separate** follow-up.

## Scope

- `capture_turn_state(client, turn_state)` — writes a `TurnStateEntity` (from
  `guardkit.knowledge.entities.turn_state`) as a `document` payload with `domain_tags=["turn","state"]`,
  resolved via `fleet_memory_mapping.resolve("turn_states")` (NOT hardcoded).
- `load_turn_continuation_context(client, feature_id, task_id, current_turn)` /
  `load_turn_context(...)` — read prior turns back for context.

## Acceptance Criteria

- [ ] **AC-1 (settle):** write + read resolve the `turn_states` payload identity via `fleet_memory_mapping`
      (`document` / `[turn,state]` / `identifier=turn_id`), no hardcoded filters.
- [ ] **AC-2 (boundary test — real seam, runs in autobuild):** a test stubs **only** the external write edge
      (`nats_core.publish_episode`) and the external read edge (`memory_search`), and asserts `capture_turn_state`
      forms a `document` episode with `domain_tags=["turn","state"]` and `load_*` issues a `memory_search` with
      `payload_types==["document"]`, `domain_tags==["turn","state"]` — through the **real** shim + mapping.
      MUST NOT MagicMock `get_memory_client`/`FleetMemoryClient`. (Per `per-task-green-is-not-feature-green`:
      assert a real `nats_core.publish_episode`, not a mock of the client.)
- [ ] **AC-3 (live round-trip — `@pytest.mark.live`):** with the store enabled, `capture_turn_state` for a
      synthetic turn then `load_turn_continuation_context` returns that turn's summary; `pytest.skip(...)` when
      the store is disabled.
- [ ] **AC-4 (regression):** graceful-degradation (client None/disabled/unmapped → no-op returning None) stays
      green; full suite stays at 7 pre-existing fails, zero new; no removed-symbol imports.

## Non-Goals

- Do NOT drop the turn_states write (Fork B = keep).
- Do NOT build the durable cross-machine dataset sink here (separate follow-up; the on-disk turn JSONs already
  serve fine-tune harvesting).
- Do NOT re-architect cross-turn context to read the on-disk turn JSONs directly (separate design change).
- Do NOT edit `fleet_memory_mapping.py`.

## Operator verification (post-merge, store enabled)

```bash
FLEET_MEMORY_ENABLED=true GUARDKIT_MEMORY_BACKEND=fleet_memory \
  .venv/bin/python -m pytest -o addopts="" -m live tests/knowledge/ -k turn_state -v
```
