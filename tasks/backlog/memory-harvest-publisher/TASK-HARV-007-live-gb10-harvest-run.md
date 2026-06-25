---
id: TASK-HARV-007
title: Live GB10 harvest run and G1 verification
task_type: operator_handoff
status: backlog
created: 2026-06-25T00:00:00Z
updated: 2026-06-25T00:00:00Z
complexity: 3
parent_review: TASK-REV-HARV
feature_id: FEAT-HARV
parent_feature: memory-harvest-publisher
wave: 5
implementation_mode: manual
depends_on:
  - TASK-HARV-005
  - TASK-HARV-006
---

# TASK-HARV-007: Live GB10 harvest run and G1 verification

## Objective

Run the harvest on the GB10 against the **live** broker + NAS Postgres and verify the
episodes landed (the brief's headline deliverable — "run the harvest on the GB10").

## Required operator follow-up

This task is `task_type: operator_handoff` — AutoBuild will **not** attempt it (it
depends on live infrastructure and human observation). The operator runs the steps below
post-merge and ticks each off, then marks the task complete via `/task-complete`.

- **AC-007-1**: `guardkit memory harvest --dry-run` on the GB10 reports sane
  counts-per-type (~448 publishable episodes; ~8 oversized skipped) and connects to
  nothing.
- **AC-007-2**: `guardkit memory harvest` on the GB10, connecting as NATS user
  `guardkit` (`GUARDKIT_NATS_PASSWORD` from `nats-infrastructure/.env`), completes and
  prints a publish summary.
- **AC-007-3**: Rows landed in the live store —
  ```sql
  select value->>'episode_type', value->>'episode_id', left(value->>'content',60)
  from store where prefix like 'fleet_memory.guardkit%'
  order by updated_at desc limit 20;
  ```
  returns guardkit episodes across the expected `episode_type`s.
- **AC-007-4**: Embeddings were written (confirm via the `store_vectors` join for the
  guardkit prefix).
- **AC-007-5**: No poison — `nats stream subjects MEMORY 'memory.dlq.>'` shows no
  guardkit episodes parked on the DLQ.
- **AC-007-6**: Idempotency — re-run `guardkit memory harvest`; row counts stay stable
  and no duplicates appear (JetStream dedupe on `Nats-Msg-Id = episode_id`).

## Context

Live environment (running on the GB10 as of 2026-06-25): broker `ships-computer-nats`,
`MEMORY` stream, relay `fleet-memory-relay`, Postgres+pgvector at
`whitestocks.tailebf801.ts.net:5433/fleet_memory`, embed service at
`http://promaxgb10-41b1:9000`. Connecting as `guardkit` and publishing was already
verified end-to-end (G1/G3) on 2026-06-25 — this task confirms the *real harvest corpus*
flows through.

## Downstream

Unblocks **FEAT-MEM-07** (re-index) → **FEAT-MEM-05** (parity eval vs the Graphiti
baseline) → cutover.
