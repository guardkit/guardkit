---
id: TASK-ABL1-002
title: "Parse FLEET_MEMORY_RETRIEVAL arm and resolve fixture DSN in fleet-memory config"
task_type: feature
feature_id: FEAT-ABL-001
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
status: backlog
---

# Parse FLEET_MEMORY_RETRIEVAL arm and resolve fixture DSN in fleet-memory config

## Context

The memory ablation (FEAT-ABL-001, scope §4) needs a retrieval arm switch
`FLEET_MEMORY_RETRIEVAL=off|fixture:<id>` whose blast radius is **retrieval only**.
The two existing switches (`FLEET_MEMORY_ENABLED=false` env and `--no-context` CLI)
null the entire `AutoBuildContextLoader` — turn-continuation state and
template-pattern injection included — which violates the ablation's
"no other code-path divergence" acceptance. The new switch is therefore read into
config here and enforced **inside** `FleetMemoryClient.search` (TASK-ABL1-003).

Config surface today: `FleetMemoryConfig` dataclass
(`guardkit/knowledge/fleet_memory_client.py:35-58`) and
`_load_fleet_config_from_env()` (`fleet_memory_client.py:622-647`).

## Scope

- `guardkit/knowledge/fleet_memory_client.py`: `FleetMemoryConfig` + `_load_fleet_config_from_env()` only. Do NOT touch `search()` in this task (TASK-ABL1-003 owns it).
- `tests/unit/knowledge/test_fleet_memory_client.py`: extend with config-level tests.
- NO changes to the fleet-memory sibling repo; the toggle lives entirely in guardkit's client.

## Requirements

1. `FleetMemoryConfig` gains two fields with back-compat defaults:
   - `retrieval_arm: Optional[str] = None` — normalised arm: `None` (live/current behaviour), `"off"`, or `"fixture:<id>"`.
   - `fixture_id: Optional[str] = None` — the `<id>` when the fixture arm is active, else `None`.
2. `_load_fleet_config_from_env()` reads `FLEET_MEMORY_RETRIEVAL` and normalises:
   - unset or blank/whitespace-only → `retrieval_arm=None` (current behaviour, byte-identical config otherwise);
   - `"off"` (case-insensitive, stripped) → `retrieval_arm="off"`;
   - `"fixture:<id>"` with non-empty `<id>` → `retrieval_arm="fixture:<id>"`, `fixture_id="<id>"`, and **postgres_dsn is replaced** by the resolved fixture DSN (see 3);
   - anything else that is set-but-invalid (e.g. `"banana"`, `"fixture:"` with empty id) → log a `logger.warning` naming the bad value and **fail closed**: `retrieval_arm="off"`. An expressed ablation intent must never silently run the live corpus.
3. Fixture DSN resolution (fixture arm only): look up `FLEET_MEMORY_FIXTURE_DSN_<ID>` first, where `<ID>` is the fixture id uppercased with every non-alphanumeric character mapped to `_` (e.g. `fixture:v1` → `FLEET_MEMORY_FIXTURE_DSN_V1`); fall back to `FLEET_MEMORY_FIXTURE_DSN`. If neither is set: `logger.warning` and fail closed (`retrieval_arm="off"`, `fixture_id` kept for diagnostics, `postgres_dsn` untouched).
4. `FLEET_MEMORY_ENABLED`, `FLEET_MEMORY_PG_DSN`, embed/nats/project vars keep their exact current semantics and defaults.

## Acceptance Criteria

- [ ] With no `FLEET_MEMORY_RETRIEVAL` in the environment, `_load_fleet_config_from_env()` returns a config with `retrieval_arm is None`, `fixture_id is None`, and every other field identical to the pre-change behaviour (unset arm == current behaviour)
- [ ] With `FLEET_MEMORY_RETRIEVAL=""` (empty string), `retrieval_arm is None`
- [ ] With `FLEET_MEMORY_RETRIEVAL=off`, `retrieval_arm == "off"` and `postgres_dsn` still comes from `FLEET_MEMORY_PG_DSN`/default
- [ ] With `FLEET_MEMORY_RETRIEVAL=fixture:v1` and `FLEET_MEMORY_FIXTURE_DSN_V1=postgresql://fixture/db`, the config has `retrieval_arm == "fixture:v1"`, `fixture_id == "v1"`, and `postgres_dsn == "postgresql://fixture/db"` (DSN swap)
- [ ] With `FLEET_MEMORY_RETRIEVAL=fixture:v1` and only `FLEET_MEMORY_FIXTURE_DSN=postgresql://generic/db` set, `postgres_dsn == "postgresql://generic/db"` (generic fallback)
- [ ] With `FLEET_MEMORY_RETRIEVAL=fixture:v9` and neither fixture DSN var set, `retrieval_arm == "off"` and `postgres_dsn` is unchanged from the live value, and a warning is logged (fail closed, no live-corpus fallback under a fixture selector)
- [ ] With `FLEET_MEMORY_RETRIEVAL=banana` and with `FLEET_MEMORY_RETRIEVAL=fixture:` (empty id), `retrieval_arm == "off"` and a warning is logged
- [ ] Unit tests cover all branches above using `monkeypatch.setenv`/`delenv`
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

Extend `tests/unit/knowledge/test_fleet_memory_client.py` with a dedicated test
class for arm parsing/DSN resolution. Pure env + dataclass tests; no store, no
network, no fleet-memory import required.

## Implementation Notes

- Keep normalisation in a small module-level helper (e.g. `_parse_retrieval_arm(raw: Optional[str], environ) -> tuple[Optional[str], Optional[str], Optional[str]]`) so TASK-ABL1-003's gate and the tests share one source of truth — but do not over-engineer; a straight-line implementation inside `_load_fleet_config_from_env` with a helper for the env-var name mangling is acceptable.
- The uppercased/underscore mapping must be deterministic: `"v1.2-rc"` → `FLEET_MEMORY_FIXTURE_DSN_V1_2_RC`.
- Do not add CLI flags; env-only per the P4 env contract.
