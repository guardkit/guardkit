---
id: TASK-ABSR-MTBC
title: Make MIN_TURN_BUDGET_SECONDS env-overridable
status: completed
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
completed: 2026-04-28T00:00:00Z
previous_state: in_review
state_transition_reason: "All ACs satisfied; tests passing"
completed_location: tasks/completed/2026-04/
priority: low
tags: [autobuild, configuration, FEAT-ABSR-9C6E, R5]
parent_review: TASK-REV-9D13
feature_id: FEAT-ABSR-9C6E
implementation_mode: direct
task_type: feature
wave: 2
historical_wave: 4
complexity: 1
depends_on: []
test_results:
  status: passing
  coverage: null
  last_run: 2026-04-28T00:00:00Z
---

# TASK-ABSR-MTBC — Make `MIN_TURN_BUDGET_SECONDS` env-overridable

## Description

Replace the hardcoded constant `MIN_TURN_BUDGET_SECONDS: int = 600` at `guardkit/orchestrator/autobuild.py:183` with `int(os.environ.get("GUARDKIT_MIN_TURN_BUDGET", "600"))`. Default unchanged; env override available for experimentation (e.g., reducing to 300 s for tasks where Coach feedback is small).

**Targets**: Bug D in TASK-REV-9D13 v2 §0. **LOW priority — pure configurability, no semantic change at default.**

## Acceptance Criteria

- [x] AC-001: `autobuild.py:183` becomes `MIN_TURN_BUDGET_SECONDS: int = int(os.environ.get("GUARDKIT_MIN_TURN_BUDGET", "600"))`. The `import os` already exists in autobuild.py — no new import needed.
- [x] AC-002: Default behaviour preserved: when `GUARDKIT_MIN_TURN_BUDGET` is not set, `MIN_TURN_BUDGET_SECONDS == 600`.
- [x] AC-003: Env-var override works: when `GUARDKIT_MIN_TURN_BUDGET=300` is set at module-load time, `MIN_TURN_BUDGET_SECONDS == 300`.
- [x] AC-004: Existing tests in `tests/unit/test_autobuild_timeout_budget.py` that pin the constant value (`test_min_turn_budget_is_600`) continue to pass with default env (no override). Add a new test `test_min_turn_budget_env_override` that uses `unittest.mock.patch.dict(os.environ, {"GUARDKIT_MIN_TURN_BUDGET": "300"})` and re-imports / re-evaluates the constant to verify override.
- [x] AC-005: Documentation: add a one-line note in [`docs/guides/autobuild-instrumentation-guide.md`](../../../docs/guides/autobuild-instrumentation-guide.md) (or appropriate existing guide) that `GUARDKIT_MIN_TURN_BUDGET` overrides the 600 s default; useful for tasks with short Coach feedback lists.
- [x] AC-006: `pytest tests/unit/test_autobuild_timeout_budget.py -v` passes.
- [x] AC-007: Lint/format pass.

## Implementation Notes

Single-line change. Mirrors the existing pattern at `agent_invoker.py:250` for `DEFAULT_SDK_TIMEOUT`.

**Regression risk**: Negligible. Default unchanged; no env-var-wins behaviour breaking tests that don't set the var.

**Coordination**: Independent of all other ABSR tasks. Slot in any time. Direct-mode appropriate.

## Implementation Summary

Replaced `MIN_TURN_BUDGET_SECONDS: int = 600` at `guardkit/orchestrator/autobuild.py:183` with `int(os.environ.get("GUARDKIT_MIN_TURN_BUDGET", "600"))`. Mirrors the existing pattern at `agent_invoker.py:250` (`DEFAULT_SDK_TIMEOUT`). Added `test_min_turn_budget_env_override` in `tests/unit/test_autobuild_timeout_budget.py` using `patch.dict(os.environ, {"GUARDKIT_MIN_TURN_BUDGET": "300"}) + importlib.reload(autobuild_module)` to verify the override at module load and reload back to default in cleanup. Documented the tunable in a new "Environment variable tunables" subsection under Troubleshooting in `docs/guides/autobuild-instrumentation-guide.md`. All 5 `TestTimeoutBudgetConstants` tests pass; 31/32 in the broader suite (1 pre-existing `_bootstrap_venv_python` failure unrelated to this change). Zero new lint errors (37 pre-existing baseline preserved).

**Lessons**: `importlib.reload` of a module whose names are imported at top-of-test-file leaves the imported names pointing at the OLD module instance — access the reloaded constant via the module reference (`autobuild_module.MIN_TURN_BUDGET_SECONDS`), not the originally-imported name. Reload back to default at the end of the test so subsequent tests see canonical state.
