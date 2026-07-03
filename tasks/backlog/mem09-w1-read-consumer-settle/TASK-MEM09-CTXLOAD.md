---
id: TASK-MEM09-CTXLOAD
title: Settle context_loader read-enrichment on fleet-memory + prove the real seam
status: in_review
created: 2026-07-03T00:00:00Z
updated: 2026-07-03T00:00:00Z
priority: medium
feature_id: FEAT-MEM-09
wave: 1
task_type: refactor
complexity: 5
tags: [fleet-memory, degraphiti, read-enrichment, FEAT-MEM-09, per-task-green]
autobuild:
  enabled: true
  max_turns: 5
  base_branch: main
  mode: tdd
---

# Task: Settle context_loader read-enrichment on fleet-memory + prove the real seam

> **READ FIRST:** [`IMPLEMENTATION-GUIDE.md`](./IMPLEMENTATION-GUIDE.md) — the shim routing (§2) and the
> mandatory two-test pattern (§3) are shared and not repeated in full here.

## Description

`guardkit/knowledge/context_loader.py` auto-injects knowledge into task-work / autobuild context. It already
reads fleet-memory via `get_memory_client()` — but its tests **MagicMock the shim**
(`tests/knowledge/test_context_loader.py:155` `mock_client = MagicMock(); mock_client.search = AsyncMock(...)`),
which is the `per-task-green-is-not-feature-green` mocked-primary-seam anti-pattern: they prove nothing about
the real read path. Per **Fork A = Hybrid/repoint** (operator-confirmed), keep these reads (they are the
high-value autobuild priming) and prove they fire against the real seam.

## Scope (exact reads)

`load_critical_context()` ([`context_loader.py:222`](../../../guardkit/knowledge/context_loader.py#L222)) fans
out to (line refs current as of 2026-07-03):

| function | group_ids | disposition (via `fleet_memory_mapping.resolve`) |
|---|---|---|
| `_load_system_context` (:411) | `product_knowledge`, `command_workflows` | retire → whole-store semantic |
| `_load_quality_gates` (:428) | `quality_gate_phases` | retire → whole-store semantic |
| `_load_architecture_decisions` (:445) | `architecture_decisions` | migrate → `adr` / `[system]` |
| `_load_failure_patterns` (:462) | `failure_patterns` | migrate → `warning` / `[failure,pattern]` |
| `_load_feature_build_context` (:479) | `feature_build_architecture` | retire → whole-store semantic |
| `load_feature_overview` (:496) | `feature_overviews` | unmapped → whole-store semantic |
| `load_critical_adrs` (:601) | `architecture_decisions` | migrate → `adr` / `[system]` |
| `load_role_context` (:745) | `role_constraints` | retire → whole-store semantic |

## Acceptance Criteria

- [x] **AC-1 (settle):** Already satisfied by the existing code — every `_load_*` calls
      `graphiti.search(group_ids=[...])` (shim-resolved via `fleet_memory_mapping`, no hardcoded filters), each
      carries a specific query string, and no single call mixes migrate + retire groups. **No production change
      needed** (the reads were correctly wired in FEAT-MEM-08 TASK-MEM08-006).
- [x] **AC-2 (boundary test — real seam):** `TestContextLoaderRealSeam` in `tests/knowledge/test_context_loader.py`
      stubs **only** the external `fleet_memory.retrieval` edge and asserts the real path builds the correct
      `SearchRequest` — `_load_architecture_decisions` → `payload_types==["adr","document"], domain_tags==["system"]`;
      `_load_system_context` (retire) → empty filters + `query=="GuardKit product workflow quality gate"`;
      `_load_failure_patterns` → `["document","warning"]`/`["failure","pattern"]`. Uses a REAL `FleetMemoryClient`,
      no MagicMock of the client.
- [x] **AC-3 (live round-trip — `@pytest.mark.live`):** `test_load_critical_context_returns_real_hits_live`
      asserts a non-empty enrichment field; `pytest.skip(...)` when the store is disabled (skips here).
- [x] **AC-4 (regression):** graceful-degradation tests unchanged/green; full suite **7 pre-existing fails, zero
      new** (12476 passed, +1 skipped = the live test).
- [x] **AC-5:** `grep get_graphiti guardkit/knowledge/context_loader.py` empty (imports `get_memory_client` shim only).

## Outcome (2026-07-03, via `/task-work`)

**No production code change** — `context_loader.py`'s `_load_*` reads were already correctly settled (shim +
real mapping, homogeneous groups, specific queries). The real deliverable was closing the
`per-task-green-is-not-feature-green` gap: the pre-existing tests MagicMock the FM shim (absent integration
evidence). Added `TestContextLoaderRealSeam` (3 boundary + 1 live) exercising the real
`FleetMemoryClient.search()` → `fleet_memory_mapping.resolve()` path, stubbing only the `fleet_memory.retrieval`
edge (reusing the TASK-MEM08-011 helper). 3 boundary pass, 1 live skips (store disabled).

## Non-Goals

- Do NOT drop the read-enrichment (Fork A is *keep/repoint*, not A-all-drop).
- Do NOT re-seed or write knowledge here (read-only consumer).
- Do NOT change `fleet_memory_mapping.py` (shared source of truth; a mapping change is its own task).

## Operator verification (post-merge, store enabled)

```bash
FLEET_MEMORY_ENABLED=true GUARDKIT_MEMORY_BACKEND=fleet_memory \
  .venv/bin/python -m pytest -o addopts="" -m live tests/knowledge/test_context_loader.py -v
```
Confirms `load_critical_context()` returns real harvest-corpus / ADR hits (the FEAT-MEM-08 `operator_handoff`
live-proof split).
