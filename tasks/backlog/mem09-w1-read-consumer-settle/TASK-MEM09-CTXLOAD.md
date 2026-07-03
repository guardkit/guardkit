---
id: TASK-MEM09-CTXLOAD
title: Settle context_loader read-enrichment on fleet-memory + prove the real seam
status: backlog
created: 2026-07-03T00:00:00Z
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

- [ ] **AC-1 (settle):** Each `_load_*` / `load_*` read uses `fleet_memory_mapping.resolve()` (via the shim),
      not a hardcoded payload_type/domain_tags. Retire-group reads carry a **specific query string** (so the
      whole-store semantic search returns relevant harvest-corpus hits); migrate-group reads keep their typed
      filter. **No single `search()` call mixes a migrate group with a retire group** (guide §2 trap) — split
      if needed.
- [ ] **AC-2 (boundary test — real seam, runs in autobuild):** For at least `_load_architecture_decisions`
      (migrate) and `_load_system_context` (retire), a test stubs **only the external `memory_search` MCP edge**
      inside `fleet_memory_client` and asserts the **real** `get_memory_client()`→`search()`→`resolve()` path
      produced the correct `memory_search` args — migrate case: `payload_types==["adr"], domain_tags==["system"]`;
      retire case: empty `payload_types`/`domain_tags` (whole-store) with the expected non-empty `query`.
      MUST NOT MagicMock `get_memory_client`/`FleetMemoryClient`.
- [ ] **AC-3 (live round-trip — `@pytest.mark.live`, skips in autobuild):** `load_critical_context()` returns a
      `CriticalContext` with at least one non-empty field when the store is enabled; `pytest.skip(...)` when
      `get_memory_client()` is None/`not enabled`.
- [ ] **AC-4 (regression):** existing graceful-degradation tests (client None / disabled / exception → empty)
      stay green. Full suite stays at the 7 pre-existing fails, zero new.
- [ ] **AC-5:** no import of any removed graphiti symbol; `grep -n get_graphiti guardkit/knowledge/context_loader.py` empty.

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
