---
id: TASK-MEM09-FPCTX
title: Strip RETIRE-group reads from feature_plan_context + prove the kept reads
status: in_review
created: 2026-07-03T00:00:00Z
updated: 2026-07-03T00:00:00Z
priority: medium
feature_id: FEAT-MEM-09
wave: 1
task_type: refactor
complexity: 4
tags: [fleet-memory, degraphiti, read-enrichment, feature-plan, FEAT-MEM-09, per-task-green]
autobuild:
  enabled: true
  max_turns: 5
  base_branch: main
  mode: tdd
---

# Task: Strip RETIRE-group reads from feature_plan_context + prove the kept reads

> **READ FIRST:** [`IMPLEMENTATION-GUIDE.md`](./IMPLEMENTATION-GUIDE.md) (shim routing §2; two-test pattern §3).

## Description

`guardkit/knowledge/feature_plan_context.py` builds `/feature-plan` context. It is **already on fleet-memory**
— the `graphiti_client` property ([`:311`](../../../guardkit/knowledge/feature_plan_context.py#L311)) lazily
returns `get_memory_client()`. Per the disposition map (§2b) and **Fork A = Hybrid/repoint**: keep the
**high-value** reads (`feature_specs`, `task_outcomes`) and **strip the RETIRE-group reads** (the ones the
harvest corpus now covers and that add noise/latency without typed value). Then prove the kept reads fire
against the real seam (replacing any mocked-shim tests —
`tests/unit/knowledge/test_feature_plan_context_fleet_memory.py`).

## Scope

- Audit every `self.graphiti_client.search(...)` / `upsert_episode(...)` call in the module and the group_ids
  each uses. **Keep** `feature_specs` (migrate → `document`/`[feature,spec]`) and `task_outcomes`
  (migrate → `build_outcome`/`[task]`). **Remove** reads whose group_ids resolve to `disposition == "retire"`
  (guide §2 / `fleet_memory_mapping`).
- The `query_logger.log_query` call ([imported at `:13`](../../../guardkit/knowledge/feature_plan_context.py#L13))
  stays (live memory-query logging).

## Acceptance Criteria

- [x] **AC-1 (strip):** The 4 RETIRE-group reads (`patterns`, `role_constraints`, `quality_gate_configs`,
      `implementation_modes`) removed from `build_context`. Kept reads (`feature_specs`, `failure_patterns`/
      `failed_approaches`, `project_overview`/`project_architecture`, `task_outcomes`) resolve via
      `fleet_memory_mapping` (no hardcoded filters); none resolves to `retire`. Assembly preserved: the 4
      `FeaturePlanContext` fields remain (defaulting empty) so the output shape is unchanged (zero API break).
- [x] **AC-2 (boundary test — real seam):** `test_feature_specs_read_resolves_migrate_group` stubs only the
      external `fleet_memory.retrieval` edge and asserts the kept `feature_specs` read builds
      `payload_types==["document"], domain_tags==["feature","spec"]` via a REAL `FleetMemoryClient` (no MagicMock).
      `test_retire_group_reads_are_stripped` proves the 4 fields stay empty even when retrieval returns hits.
- [x] **AC-3 (live round-trip — `@pytest.mark.live`):** `test_build_context_returns_real_hits_live` asserts a
      kept enrichment field non-empty; skips when the store is disabled.
- [x] **AC-4 (regression):** existing feature_plan_context tests stay green (none asserted a stripped read as
      populated — they only asserted `== []`); full suite stays at 7 pre-existing fails, zero new; no removed-symbol imports.

## Outcome (2026-07-03, via `/task-work`)

Stripped the 4 RETIRE reads from `build_context` (patterns/role_constraints/quality_gate_configs/
implementation_modes → harvest corpus, not feature-specific). Kept the migrate reads. Chose the safe shape:
the `FeaturePlanContext` fields remain (defaulting empty via their init) so no consumer/formatter breaks — only
the *reads* are gone. `tech_stack` param retained for API stability (now unused post-strip). Added
`TestFeaturePlanContextRealSeam` (1 boundary + 1 strip-proof + 1 live). 8 passed / 1 live-skip.

## Non-Goals

- Do NOT rename the `graphiti_client` property (a public property with call-sites; cosmetic rename is a
  separate optional task).
- Do NOT touch the write/seed path beyond removing dead RETIRE reads.
- Do NOT edit `fleet_memory_mapping.py`.

## Operator verification (post-merge, store enabled)

```bash
FLEET_MEMORY_ENABLED=true GUARDKIT_MEMORY_BACKEND=fleet_memory \
  .venv/bin/python -m pytest -o addopts="" -m live tests/unit/knowledge/test_feature_plan_context_fleet_memory.py -v
```
