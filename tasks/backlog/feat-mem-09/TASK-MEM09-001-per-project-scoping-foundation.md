---
id: TASK-MEM09-001
title: WS-0 — per-project + per-group scoping foundation for fleet-memory
status: in_review
created: '2026-07-01'
updated: '2026-07-01'
priority: high
feature_id: FEAT-MEM-09
implementation_mode: task-work
wave: 0
complexity: 3
task_type: feature
tags: [memory-cutover, fleet-memory, scoping, FEAT-MEM-09]
depends_on: []
---

# TASK-MEM09-001 — Per-project + per-group scoping foundation

> Source: FEAT-MEM-09 investigation §1 (Appendix A). fleet-memory ALREADY scopes by project
> end-to-end at the SQL level (`prefix = fleet_memory.{project}.{payload_type}`, project baked
> into every `natural_key`/`uuid5`, retrieval filters `store.prefix LIKE 'fleet_memory.{project}%'`).
> The only gap is guardkit hardcoding the literal `"guardkit"`. Blocks every other WS (the
> graph export and all fleet-consumer migrations need to write/read under their OWN project).

## Goal

Make the fleet-memory project a runtime property threaded from config, not a per-group static
`"guardkit"` — so guardkit (and, generalised, every consumer) writes/reads under its own project
namespace, with group-scoped retrieval preserved.

## Acceptance criteria

- [x] `FleetMemoryConfig.project: str = "guardkit"` (back-compat default).
- [x] `_load_fleet_config_from_env()` sources it from `GUARDKIT_MEMORY_PROJECT` (default `"guardkit"`).
- [x] `build_memory_episode(..., project: str | None = None)` uses `project or mapping.project`
      on BOTH the structured (json) and prose (markdown) paths (`project_id`, `natural_key`, body).
- [x] `FleetMemoryClient.add_episode` threads `self.config.project` into `build_memory_episode`.
- [x] `FleetMemoryClient.search` uses `SearchRequest(project=self.config.project, …)` (was `"guardkit"`).
- [x] `FleetMemoryClient.health_check` probes `("fleet_memory", self.config.project, "chunk")`.
- [x] Unit tests prove: explicit project scopes natural_key/project_id; `None` → back-compat
      `"guardkit"`; env override; client threads config.project into the write path.
      (`tests/unit/knowledge/test_fleet_memory_project_scoping.py`, 9 tests green; existing 65 green.)
- [x] **fleet-memory (sibling repo):** add an exact-project post-filter (`_matches_project`)
      in `retrieval/core.py` so `project="guardkit"` cannot `LIKE`-prefix-match
      `guardkit_factory` (namespace-segment exact match, langgraph-independent, covers chunk
      + typed records). Done in fleet-memory commit `7945d9d`; 3 tests, 516 unit tests green.
- [ ] (optional, cleanup) remove the static `GroupMapping.project` field entirely once all
      callers thread `project` — currently retained for back-compat and as the default.

## Implementation notes

- Files touched (guardkit, DONE): `guardkit/knowledge/fleet_memory_payloads.py`
  (`build_memory_episode` + `_build_prose_episode` project param),
  `guardkit/knowledge/fleet_memory_client.py` (`FleetMemoryConfig.project`,
  `_load_fleet_config_from_env`, `search` L~395, `health_check` L~301, `add_episode` L~487).
- Non-breaking: every default remains `"guardkit"`, so current single-project behaviour is
  byte-identical (verified: 65 pre-existing fleet-memory tests still green).
- Anti-pattern guard (`per-task-green-is-not-feature-green.md`): the client-threading test
  asserts the REAL `project` kwarg reaches `build_memory_episode`, not a mocked-away call.

## Remaining before this WS is "done"

WS-0 is **code-complete** across both repos (guardkit `0de43a86`, fleet-memory `7945d9d`).
Only an OPTIONAL cleanup is deferred:

1. (optional, deferred) drop the static `GroupMapping.project` field once all callers thread
   `project` explicitly — currently retained as the back-compat default. Not required for the
   scoping behaviour, which is fully working and tested.

## Notes

Part of FEAT-MEM-09 (`.guardkit/features/FEAT-MEM-09.yaml`). Next: WS-1 graph_export
(`TASK-MEM09-002`) depends on this so exported episodes carry the source graph's project.
