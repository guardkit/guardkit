---
id: TASK-ABL1-004
title: "Arm-parity acceptance tests through the AutoBuild context chain"
task_type: testing
feature_id: FEAT-ABL-001
wave: 3
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-ABL1-003
status: backlog
---

# Arm-parity acceptance tests through the AutoBuild context chain

## Context

FEAT-ABL-001's acceptance (scope §4) is stated at the chain level, not the unit
level: off-arm rollouts show zero retrieval-log entries; fixture-arm rollouts log
item ids + scores; and there is **no other code-path divergence** between arms —
the `AutoBuildContextLoader`, turn-continuation and template-pattern paths must be
exercised identically whichever arm is active. Tasks 001-003 unit-tested the
pieces; this task proves the composed behaviour through
`AutoBuildContextLoader.get_player_context` for all three arm states
(the per-task-green-vs-feature-green gap).

## Scope

- New module `tests/unit/knowledge/test_retrieval_arm_parity.py` only. No production code changes. If a composed-level defect is found, report it via Coach feedback rather than patching production files in this task.

## Acceptance Criteria

- [ ] **Unset arm (current behaviour)**: with `FleetMemoryConfig(enabled=True)` (no arm) and mocked `fleet_memory.retrieval` returning items, `AutoBuildContextLoader(graphiti=client).get_player_context(...)` completes, `loader.retriever is not None`, and one retrieval-log entry with populated `items` is written
- [ ] **Off arm**: with `retrieval_arm="off"` (enabled=True), the same call completes with `loader.retriever is not None` (loader still constructed — NOT the `--no-context`/`FLEET_MEMORY_ENABLED=false` nulling), `client.search` returned `[]` for every query, and the retrieval log contains **zero** entries
- [ ] **Fixture arm**: with `retrieval_arm="fixture:v1"` and the DSN swapped by config, the same call completes and every logged entry's `items` carry the mocked natural keys and scores
- [ ] **Parity**: the off-arm and fixture-arm runs both return an `AutoBuildContextResult` (no exception, no None), from the identical loader code path — assert both runs constructed a `JobContextRetriever` and neither short-circuited at the loader level (e.g. via the `_empty_result` graceful-degradation branch counter/log or equivalent observable)
- [ ] Env-driven variant: at least one test drives the three states purely via `monkeypatch.setenv("FLEET_MEMORY_RETRIEVAL", ...)` + `_load_fleet_config_from_env()` to prove the env contract end-to-end (P4: rollouts set env vars, not dataclasses)
- [ ] The module runs green with `pytest tests/unit/knowledge/test_retrieval_arm_parity.py -q` — no live Postgres, no network, fleet_memory.retrieval mocked

## Test Requirements

- Use the same mocking approach as `tests/unit/knowledge/test_fleet_memory_client.py`
  for the `fleet_memory.retrieval` surface, plus `query_logger` `base_dir`/path
  injection with `tmp_path` to read back the JSONL entries per arm.
- `JobContextRetriever` may issue several searches per context load — assertions on
  the retrieval log should be aggregate (zero entries vs ≥1 entries with correct
  shape), not exact counts, to avoid coupling to retriever internals.
- Turn-continuation/template-pattern paths: for `turn_number=1` and no
  `worktree_path`, both are no-ops by design in every arm; asserting the loader
  reaches `_build_result` (a real `AutoBuildContextResult` with `context.task_id`
  set) in both arms is sufficient parity evidence at this level.

## Implementation Notes

The `ContextStatus` dataclass itself lives in `orchestrator/autobuild.py` and is set
by the orchestrator when the loader returns; driving the full orchestrator in a unit
test is out of scope. The parity acceptance is discharged by proving the loader
returns a real result (which the orchestrator maps to `status="retrieved"`) in every
arm — i.e. no arm ever falls into the `retriever is None` / disabled branches.
