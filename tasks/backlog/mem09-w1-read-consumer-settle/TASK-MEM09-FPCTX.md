---
id: TASK-MEM09-FPCTX
title: Strip RETIRE-group reads from feature_plan_context + prove the kept reads
status: backlog
created: 2026-07-03T00:00:00Z
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

- [ ] **AC-1 (strip):** No read remains whose group_ids resolve to `retire`. `feature_specs` + `task_outcomes`
      reads remain and resolve via `fleet_memory_mapping` (no hardcoded filters). Removing a read must not
      break `build_feature_plan_context` assembly (adjust the aggregation/shape accordingly).
- [ ] **AC-2 (boundary test — real seam, runs in autobuild):** stub only the external `memory_search` MCP edge
      and assert a kept read (e.g. `feature_specs`) produces `payload_types==["document"]`,
      `domain_tags==["feature","spec"]` through the real shim+mapping. MUST NOT MagicMock
      `get_memory_client`/`FleetMemoryClient`/`FeaturePlanContextBuilder`.
- [ ] **AC-3 (live round-trip — `@pytest.mark.live`):** with the store enabled, the builder returns non-empty
      feature-plan context for a feature that has a spec/outcome; `pytest.skip(...)` when disabled.
- [ ] **AC-4 (regression):** existing feature_plan_context tests stay green (update any that asserted a
      now-removed RETIRE read); full suite stays at 7 pre-existing fails, zero new; no removed-symbol imports.

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
