---
id: TASK-MEM09-JOBCTX
title: Settle job_context_retriever (GROI) reads on fleet-memory + prove the real seam
status: backlog
created: 2026-07-03T00:00:00Z
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

- [ ] **AC-1 (settle + split):** Category reads resolve through `fleet_memory_mapping` (no hardcoded
      filters). **Migrate and retire group_ids are NOT mixed in one `search()` call** (guide §2 trap — the
      migrate filter would silently narrow the retire whole-store intent): issue a typed `search()` for the
      migrate groups and a separate whole-store `search()` (specific query) for the retire groups, then merge.
- [ ] **AC-2 (boundary test — real seam, runs in autobuild):** For a migrate category (e.g. `task_outcomes` →
      `payload_types==["build_outcome"]`, `domain_tags==["task"]`) and for `_query_turn_states` (`turn_states`
      → `payload_types==["document"]`, `domain_tags==["turn","state"]`), stub **only** the external
      `memory_search` MCP edge and assert the real shim+mapping produced those args. MUST NOT MagicMock
      `get_memory_client`/`FleetMemoryClient`/`JobContextRetriever`.
- [ ] **AC-3 (live round-trip — `@pytest.mark.live`):** with the store enabled, GROI's public retrieval entry
      returns non-empty context for a task that has prior outcomes/turn_states; `pytest.skip(...)` when the
      store is disabled.
- [ ] **AC-4 (delegation):** an `autobuild_context_loader` test confirms it threads the **real**
      `get_memory_client()` into GROI + `turn_state_operations` (boundary-level, not a MagicMock of GROI).
- [ ] **AC-5 (regression):** graceful-degradation paths (None/disabled/exception → empty) stay green; full
      suite stays at 7 pre-existing fails, zero new; no removed-symbol imports.

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
