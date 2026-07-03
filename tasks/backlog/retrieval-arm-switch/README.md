# Feature: Fleet-Memory Retrieval Arm Switch and Retrieval Logging

**Feature ID**: FEAT-ABL-001 · **Origin**: memory ablation, fleet-memory
`docs/research/ideas/phase-ablation-scope.md` §4 + `phase-ablation-build-plan.md` Step 1
**BDD spec**: `features/retrieval-arm-switch/retrieval-arm-switch.feature`

Adds `FLEET_MEMORY_RETRIEVAL=off|fixture:<id>` read in
`_load_fleet_config_from_env` and enforced inside `FleetMemoryClient.search`
(mirroring the `enabled=false` gate) so ablation arms differ ONLY in retrieval;
plus a structured per-call JSONL retrieval log carrying per-item
`natural_key` + `score` via a new optional `items` field on
`query_logger.log_query`, emitted between `fm_search()` and `assemble_context()`.

## Tasks

| Task | Title | Wave | Complexity | Mode |
|---|---|---|---|---|
| TASK-ABL1-001 | Extend query_logger with optional per-item results field | 1 | 3 | direct |
| TASK-ABL1-002 | Parse FLEET_MEMORY_RETRIEVAL arm + fixture DSN resolution | 1 | 4 | task-work |
| TASK-ABL1-003 | Arm gate + per-item retrieval log inside search() | 2 | 5 | task-work |
| TASK-ABL1-004 | Arm-parity acceptance tests through the loader chain | 3 | 4 | task-work |

## Acceptance (scope §4)

- Off-arm rollout: **zero** retrieval-log entries; loader still constructed
- Fixture arm: item ids (natural keys) + scores logged per call
- No other code-path divergence: ContextStatus "retrieved" in every arm

See `IMPLEMENTATION-GUIDE.md` for diagrams, integration contracts, and the
P4 environment contract table.
