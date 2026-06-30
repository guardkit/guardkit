---
id: TASK-MEM08-005
title: "Dual-write soak + audit published == stored [operator]"
task_type: operator_handoff
parent_review: TASK-REV-MEM08
feature_id: FEAT-MEM-08
wave: 4
implementation_mode: task-work
complexity: 3
dependencies:
  - TASK-MEM08-004
---

# TASK-MEM08-005 — Dual-write soak audit (published == stored)

> `task_type: operator_handoff` — AutoBuild will **not** attempt this task. Its acceptance criteria are
> `observed_at_runtime` against **live NATS + Postgres** over a wall-clock soak; the Player↔Coach loop
> (a deterministic file/test checker) cannot satisfy them. The operator runs the soak, verifies the
> criteria below, then marks the task complete via `/task-complete`.

## What to do

With `backend=dual` enabled (TASK-MEM08-004), run real guardkit task completions / ADR captures over a
soak window and confirm every Graphiti write **also** lands in fleet-memory's Postgres store.

1. Enable `backend=dual` in `.guardkit/graphiti.yaml`; export `FLEET_MEMORY_*` + `GUARDKIT_NATS_PASSWORD`.
2. Drive real completions (e.g. complete several tasks / record ADRs) over the soak window.
3. For each Graphiti write, confirm the corresponding fleet-memory record exists (query the store by
   natural key `build_outcome:guardkit:<task_id>` / `adr:guardkit:<id>`).
4. Record the audit: count published vs stored, any divergences, and the relay/DLQ state
   (`fleet-memory` relay logs; `memory.dlq` empty).

## Required operator follow-up

This task is `task_type: operator_handoff` — AutoBuild will not attempt it. The operator must verify the
runtime acceptance criteria below manually, then mark the task complete via `/task-complete`.

- **AC-005-1**: With `backend=dual` live, every Graphiti task-outcome/ADR write over the soak window has a
  matching fleet-memory record (`published == stored`), audited by natural key against live Postgres.
- **AC-005-2**: No dual-write divergence is silently swallowed — divergences (if any) are counted and
  explained; the `memory.dlq` subject is empty (or every DLQ entry is triaged).
- **AC-005-3**: A dual-write soak audit note is recorded under
  `docs/design/specs/memory-cutover/` (published/stored counts, window, sign-off).

## Notes

This is the W2 gate before W3 reads are cut over (brief: "Dual-write soak before cutting reads over").
Rollback during the soak = set `backend=graphiti`; Graphiti stays authoritative throughout.
