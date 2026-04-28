---
id: TASK-ABSR-MTBC
title: Make MIN_TURN_BUDGET_SECONDS env-overridable
status: backlog
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
priority: low
tags: [autobuild, configuration, FEAT-ABSR-9C6E, R5]
parent_review: TASK-REV-9D13
feature_id: FEAT-ABSR-9C6E
implementation_mode: direct
task_type: feature
wave: 4
complexity: 1
depends_on: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-ABSR-MTBC — Make `MIN_TURN_BUDGET_SECONDS` env-overridable

## Description

Replace the hardcoded constant `MIN_TURN_BUDGET_SECONDS: int = 600` at `guardkit/orchestrator/autobuild.py:183` with `int(os.environ.get("GUARDKIT_MIN_TURN_BUDGET", "600"))`. Default unchanged; env override available for experimentation (e.g., reducing to 300 s for tasks where Coach feedback is small).

**Targets**: Bug D in TASK-REV-9D13 v2 §0. **LOW priority — pure configurability, no semantic change at default.**

## Acceptance Criteria

- [ ] AC-001: `autobuild.py:183` becomes `MIN_TURN_BUDGET_SECONDS: int = int(os.environ.get("GUARDKIT_MIN_TURN_BUDGET", "600"))`. The `import os` already exists in autobuild.py — no new import needed.
- [ ] AC-002: Default behaviour preserved: when `GUARDKIT_MIN_TURN_BUDGET` is not set, `MIN_TURN_BUDGET_SECONDS == 600`.
- [ ] AC-003: Env-var override works: when `GUARDKIT_MIN_TURN_BUDGET=300` is set at module-load time, `MIN_TURN_BUDGET_SECONDS == 300`.
- [ ] AC-004: Existing tests in `tests/unit/test_autobuild_timeout_budget.py` that pin the constant value (`test_min_turn_budget_is_600`) continue to pass with default env (no override). Add a new test `test_min_turn_budget_env_override` that uses `unittest.mock.patch.dict(os.environ, {"GUARDKIT_MIN_TURN_BUDGET": "300"})` and re-imports / re-evaluates the constant to verify override.
- [ ] AC-005: Documentation: add a one-line note in [`docs/guides/autobuild-instrumentation-guide.md`](../../../docs/guides/autobuild-instrumentation-guide.md) (or appropriate existing guide) that `GUARDKIT_MIN_TURN_BUDGET` overrides the 600 s default; useful for tasks with short Coach feedback lists.
- [ ] AC-006: `pytest tests/unit/test_autobuild_timeout_budget.py -v` passes.
- [ ] AC-007: Lint/format pass.

## Implementation Notes

Single-line change. Mirrors the existing pattern at `agent_invoker.py:250` for `DEFAULT_SDK_TIMEOUT`.

**Regression risk**: Negligible. Default unchanged; no env-var-wins behaviour breaking tests that don't set the var.

**Coordination**: Independent of all other ABSR tasks. Slot in any time. Direct-mode appropriate.
