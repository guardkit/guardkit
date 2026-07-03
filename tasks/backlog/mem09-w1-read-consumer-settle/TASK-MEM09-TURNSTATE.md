---
id: TASK-MEM09-TURNSTATE
title: Verify turn_states document-payload capture/load round-trip on fleet-memory
status: in_review
created: 2026-07-03T00:00:00Z
updated: 2026-07-03T00:00:00Z
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

- [x] **AC-1 (settle):** Already satisfied — `capture_turn_state` → `add_episode(group_id="turn_states")` and
      `_load_from_graphiti`/`load_turn_context` → `search(group_ids=["turn_states"])` both resolve the payload
      identity via `fleet_memory_mapping` (document / [turn, state] / migrate), no hardcoded filters. Fork B =
      keep; **no production change needed.**
- [x] **AC-2 (boundary test — real seam):** `TestTurnStateRealSeam` (`tests/knowledge/test_turn_state.py`):
      the WRITE test uses a REAL `FleetMemoryClient` and stubs **only** the external publish edge
      (`harvest_publisher.publish_episodes`), asserting `capture_turn_state` reaches publish with a real
      `MemoryEpisodeV1` — since a retired/unmapped group returns None *before* publish, publishing proves the
      real mapping resolved `turn_states` as migrate + built the real episode ("real nats path, not a client
      mock"). The READ test stubs only `fleet_memory.retrieval` and asserts `_load_from_graphiti` builds a
      `SearchRequest` with `payload_types==["document"], domain_tags==["state","turn"]`. No MagicMock of the client.
- [x] **AC-3 (live round-trip — `@pytest.mark.live`):** `test_turn_state_round_trip_live` captures then loads a
      turn back; skips when the store is disabled.
- [x] **AC-4 (regression):** graceful-degradation (existing 66 tests: client None/disabled/unmapped → no-op)
      stay green; full suite stays at 7 pre-existing fails, zero new; no removed-symbol imports.

## Outcome (2026-07-03, via `/task-work`)

**No production change** — the `turn_states` write (`add_episode`) and read (`search`) already resolve via
`fleet_memory_mapping` (document/[turn,state]). Fork B = keep. Added `TestTurnStateRealSeam` (write boundary +
read boundary + live round-trip). The write boundary is the first to exercise the real WRITE seam
(`capture_turn_state` → real `add_episode` → resolve + `build_memory_episode` → publish), stubbing only the
external NATS publish edge. 2 pass, 1 live-skip; full file 68 passed / 1 skipped.

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
