---
id: TASK-HARV-007
title: Live GB10 harvest run and G1 verification
task_type: operator_handoff
status: completed
created: 2026-06-25T00:00:00Z
updated: 2026-06-27T00:00:00Z
completed: 2026-06-27T00:00:00Z
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

---

## Status 2026-06-26 — PARTIAL (338/447), BLOCKED on fleet-memory fixes

First live run executed on the GB10 after the nomic→Qwen/1024 embedder switch
(Phases A+B done: embed/1024 served, relay re-pointed, store_vectors rebuilt at
vector(1024)). The harvest published all 447 (stream MEMORY holds 447), but the
relay stored only **338**; **109 multi-chunk episodes were silently dropped**.

**Not a guardkit/harvest defect.** Root cause is in the fleet-memory write path +
embed serving config: the embed model is served at an effective 2048 tok/slot
(`--ctx-size 8192 ÷ -np 4`), the relay batches all of an episode's chunks into ONE
`/v1/embeddings` request (total > 2048 → HTTP 400 `exceed_context_size`), and the
relay mis-classifies that deterministic 400 as transient → nack → silent drop
after `max_deliver=5` (not even DLQ'd).

The 338 stored are correct (dim 1024, `fleet_memory.guardkit%`). Recovery is safe
once the fixes land (stream intact; `ChunkWriter` idempotent via uuid5).

**Blocking fixes (filed in fleet-memory/tasks/backlog/):**
- `TASK-FIX-EMBEDCTX01` — embed effective ctx 2048 too small (config: llama-swap embed block).
- `TASK-FIX-RELAYBATCH01` — relay batches all chunks into one embed request > n_ctx.
- `TASK-FIX-RELAYDROP01` — deterministic embed-400 silently dropped; should poison→DLQ.

AC-007 NOT met (AC-007-3 needs all 447). Re-run / redeliver after the above land.
Evidence + full trace: agent memory `qwen-embed-switch-1024`.

---

## Status 2026-06-27 — COMPLETE (447/447) ✅

Recovery executed on the GB10. **All 447 episodes are stored at dim 1024; AC-007 met.**
Full detail: `fleet-memory/docs/handoffs/HANDOFF-2026-06-27-harvest-recovery-and-graphiti-cutover.md`.

**What it took** (beyond the three filed fixes):
- Relay rebuilt on the fixed image; **RELAYDROP01 validated** — 53 unit + 2 real-store
  Docker integration tests, and live (embed timeouts routed to the DLQ, not silently dropped).
- **Two more root causes found + actioned**: (a) embed cold-start (85–181s) on the shared
  `:9000` llama-swap because qwen3 `embed` was only in the `all` matrix-set → **pinned `embed`
  resident** (dgx-spark `TASK-LLSWAP-EMRESIDENT01`); (b) hardcoded `ack_wait=60s` too short for
  large multi-chunk episodes (a 70+-chunk episode embeds+writes every chunk before the ack) →
  **made `ack_wait` settings-driven (1200s) + `embed_timeout_s` 10→180s** (fleet-memory
  `TASK-FIX-RELAYACKTMO01`).
- Replayed the intact MEMORY stream (447 msgs, seq 19–465) through the fixed relay;
  `redelivered=0`, no silent loss.

**Acceptance (verified 2026-06-27):**
- [x] **AC-007-1** — `--dry-run` reported ~448 publishable episodes (earlier run).
- [x] **AC-007-2** — `guardkit memory harvest` published all 447 as NATS user `guardkit` (earlier run).
- [x] **AC-007-3** — 447 distinct episodes stored across `episode_type`: review_report 323,
  document 78, feature_outcome 25, adr 21.
- [x] **AC-007-4** — embeddings written: `store_vectors` = 2846 chunks, all `vector(1024)`.
- [x] **AC-007-5** — no poison: `memory.dlq.>` empty (15 stale entries from the first
  10s-timeout pass were re-stored, then purged).
- [x] **AC-007-6** — idempotent: replay re-upserted with no duplicates
  (store rows = distinct keys = vectors = 2846).

Downstream now unblocked: **FEAT-MEM-05 parity eval** (lock the Qwen/1024 embedder first) →
FEAT-MEM-08 cutover → FEAT-MEM-09 Graphiti decommission.
