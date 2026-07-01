---
id: TASK-MEM08-007
title: "Prove a real pipeline run reads from fleet-memory (log evidence) [operator] — ACCEPTANCE GATE"
task_type: operator_handoff
parent_review: TASK-REV-MEM08
feature_id: FEAT-MEM-08
wave: 6
implementation_mode: task-work
complexity: 3
dependencies:
  - TASK-MEM08-006
---

# TASK-MEM08-007 — Prove a real run reads from fleet-memory  ⟵ FEATURE ACCEPTANCE GATE

> `task_type: operator_handoff` — AutoBuild will **not** attempt this. This is the **GROI anti-criterion**
> and the **acceptance gate for the whole feature** (brief W3): *don't just build a reader — wire it in and
> prove a real pipeline reads from fleet-memory.* It is `observed_at_runtime` (a real autobuild /
> feature-plan run against live fleet-memory + the query log) and cannot be satisfied by the Player↔Coach
> loop. The operator runs it, verifies the criteria, then marks the task complete via `/task-complete`.

## What to do

1. Set `backend=fleet_memory` (reads from fleet-memory); ensure `FLEET_MEMORY_*` point at the live store
   (PG with the clean 125-doc corpus + any W2 soak-accumulated outcomes) and the embedder (Qwen3-0.6B/1024).
2. Run a **real** pipeline that exercises the GROI reads — e.g. a `/feature-plan` with `--context`
   (drives `feature_plan_context`) and/or an autobuild turn (drives `coach_context_builder`).
3. Capture **log evidence** from `.guardkit/graphiti-query-log.jsonl`: entries with a fleet-memory `source`,
   the query text, `result_count > 0`, and a non-empty context block injected into the prompt.
4. Spot-check the injected context is on-topic for the query (parity eval already passed; this is wiring proof).

## Required operator follow-up

This task is `task_type: operator_handoff` — AutoBuild will not attempt it. The operator must verify the
runtime acceptance criteria below manually, then mark the task complete via `/task-complete`.

- **AC-007-1**: A real `/feature-plan` and/or autobuild run with `backend=fleet_memory` produces query-log
  evidence that `memory_search` fired against fleet-memory (fleet-memory `source`, `result_count > 0`).
- **AC-007-2**: The fleet-memory context block was demonstrably **injected into the prompt** the pipeline
  used (not merely fetched-and-discarded) — captured from the run's context/log.
- **AC-007-3**: The injected context is on-topic for the query (sanity spot-check), and the evidence is
  recorded under `docs/design/specs/memory-cutover/` (run id, query, log excerpt).

## Notes

This is THE gate that sank prior "reads exist on paper" attempts. Until AC-007-1..3 are signed off, do not
proceed to the W4 live config flip (TASK-MEM08-009) or the FEAT-MEM-09 decommission.
