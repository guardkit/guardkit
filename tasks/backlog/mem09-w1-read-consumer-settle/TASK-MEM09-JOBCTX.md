---
id: TASK-MEM09-JOBCTX
title: Settle job_context_retriever (GROI) reads on fleet-memory + prove the real seam
status: in_review
created: 2026-07-03T00:00:00Z
updated: 2026-07-03T00:00:00Z
priority: medium
feature_id: FEAT-MEM-09
wave: 1
task_type: refactor
complexity: 6
tags: [fleet-memory, degraphiti, read-enrichment, groi, FEAT-MEM-09, per-task-green]
autobuild:
  enabled: true
  max_turns: 5
  base_branch: main
  mode: tdd
---

# Task: Settle job_context_retriever (GROI) reads on fleet-memory + prove the real seam

> **READ FIRST:** [`IMPLEMENTATION-GUIDE.md`](./IMPLEMENTATION-GUIDE.md) (shim routing §2; two-test pattern §3).

## Description

`guardkit/knowledge/job_context_retriever.py` (GROI) is the autobuild job-context reader — it primes the
Player/Coach with prior outcomes, patterns, architecture, and cross-turn `turn_states`. `memory_search` was
wired into GROI in FEAT-MEM-08 (TASK-MEM08-006); it reads via the shim (`self.graphiti` = `get_memory_client()`).
Per **Fork A = Hybrid/repoint** (keep this — it is the highest-value read-enrichment) and **Fork B = follows A**
(keep `turn_states` cross-turn context), settle the per-category reads and prove the real seam. Its delegating
wrapper `autobuild_context_loader.py` (which passes `self.graphiti` through to GROI + `turn_state_operations`)
is covered by this task's tests — no separate task.

## Scope (exact reads)

- `_query_category` ([`job_context_retriever.py:990`](../../../guardkit/knowledge/job_context_retriever.py#L990))
  — `await self.graphiti.search(...)` over category group_ids (`feature_specs`, `task_outcomes`,
  `project_architecture`, `failure_patterns`, `domain_knowledge` = **migrate**; `patterns`,
  `role_constraints`, `quality_gate_configs`, `implementation_modes` = **retire**). Group list defined ~:586-591.
- `_query_turn_states` ([`:1047`](../../../guardkit/knowledge/job_context_retriever.py#L1047)) —
  `turn_states` = **migrate** → `document` / `[turn,state]`.

## Acceptance Criteria

- [x] **AC-1 (settle + split):** Already satisfied — **every** `_query_category` call and `_query_turn_states`
      passes a **single** `group_id` (`category_configs` + the AutoBuild categories `role_constraints`/
      `quality_gate_configs`/`implementation_modes` each alone, `turn_states` via `_query_turn_states`). There
      is **no** mixed migrate/retire `search()` call anywhere → nothing to split. Reads resolve via the shim +
      `fleet_memory_mapping` (no hardcoded filters). **No production change needed.**
- [x] **AC-2 (boundary test — real seam):** `TestJobContextRetrieverRealSeam` stubs only the external
      `fleet_memory.retrieval` edge and asserts via a REAL `FleetMemoryClient`: `_query_category(["task_outcomes"])`
      → `["build_outcome","document"]`/`["task"]`; `_query_category(["patterns"])` (retire) → empty filters
      (whole-store); `_query_turn_states` → `["document"]`/`["state","turn"]`. No MagicMock of the client/GROI.
- [x] **AC-3 (live round-trip — `@pytest.mark.live`):** `test_retrieve_returns_real_context_live` calls the
      public `retrieve()`; asserts a non-empty category; skips when the store is disabled.
- [x] **AC-4 (delegation):** `test_autobuild_context_loader_threads_real_client_into_groi` asserts
      `AutoBuildContextLoader(graphiti=client).retriever.graphiti is client` — the REAL client threaded into
      GROI (not a MagicMock of GROI).
- [x] **AC-5 (regression):** graceful-degradation paths (existing 90 tests) stay green; full suite stays at 7
      pre-existing fails, zero new; no removed-symbol imports (`self.graphiti` = the FM shim).

## Outcome (2026-07-03, via `/task-work`)

**No production change** — GROI's reads are already correctly settled (single-group `_query_category` /
`_query_turn_states` calls, shim-resolved via `fleet_memory_mapping`, **no migrate/retire mixing**, so the
AC-1 "split" was already satisfied). Fork A Hybrid keeps this (high-value autobuild job context), so no strip.
Added `TestJobContextRetrieverRealSeam` (3 boundary + 1 delegation + 1 live) to `tests/knowledge/
test_job_context_retriever.py`. 4 pass, 1 live-skip; full file 94 passed / 1 skipped.

## Non-Goals

- Do NOT drop GROI read-enrichment (Fork A = keep/repoint).
- Do NOT change `turn_state_operations.py` write path here — that is TASK-MEM09-TURNSTATE (this task only
  *reads* turn_states via GROI).
- Do NOT edit `fleet_memory_mapping.py`.

## Operator verification (post-merge, store enabled)

```bash
FLEET_MEMORY_ENABLED=true GUARDKIT_MEMORY_BACKEND=fleet_memory \
  .venv/bin/python -m pytest -o addopts="" -m live tests/knowledge/test_job_context_retriever.py -v
```
