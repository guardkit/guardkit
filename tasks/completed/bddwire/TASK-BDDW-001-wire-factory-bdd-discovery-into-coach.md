---
id: TASK-BDDW-001
title: Wire factory BDD plugin discovery into the Coach evidence path (core, Python
  end-to-end)
task_type: feature
parent_task: TASK-HMIG-BDDWIRE
feature_id: FEAT-E2CB
wave: 1
implementation_mode: task-work
complexity: 5
dependencies: []
priority: medium
status: completed
updated: '2026-06-12T12:42:10'
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-E2CB
  base_branch: main
  started_at: '2026-06-12T12:35:43.002037'
  last_updated: '2026-06-12T12:58:16.313458'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-06-12T12:35:43.002037'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Wire factory BDD plugin discovery into the Coach evidence path

## Description

`guardkitfactory/src/guardkitfactory/bdd/` is a complete, tested, multi-stack
BDD-oracle plugin subsystem (`BDDPlugin` ABC + `BDDRunResult` contract,
contract-gated `loader.discover(stack_profile)`, plugins for pytest-bdd / reqnroll
/ cucumber-js, 42 tests) that **nothing in the orchestrator consumes**. The Coach's
BDD evidence today comes only from the legacy pytest-hardcoded
`guardkit/orchestrator/quality_gates/bdd_runner.py` + the Player-reported
`task_work_results['bdd_results']`. This task wires the factory plugin discovery
into the Coach evidence path for the Python (pytest-bdd) stack end-to-end,
**preserving** the existing per-task glue, absence-of-failure, and
`scenarios_failed > 0` contracts. (Multi-stack .NET/JS routing is Wave 2,
TASK-BDDW-002.)

## Acceptance Criteria

- [ ] **AC-1**: In the Coach evidence path (`CoachValidator` / `coach_evidence.py`,
  where `bundle.bdd` is populated and `_check_bdd_results` runs), discover the
  plugin for the detected stack via `guardkitfactory.bdd.discover(stack_profile)`,
  invoke it to get a `BDDRunResult`, and map that into the existing `bundle.bdd`
  shape (`scenarios_attempted` / `scenarios_failed` / `scenarios_passed` /
  `failures` / `feature_files`). Verified end-to-end on a Python (pytest-bdd)
  fixture project.
- [ ] **AC-3 (absence-of-failure preserved)**: `scenarios_attempted == 0` still
  surfaces as ABSENT SIGNAL (feedback), never a silent pass; do not coerce a
  missing key to 0 (`.claude/rules/absence-of-failure-is-not-success.md`,
  Pattern-2). The zero-cardinality guard in the Coach prompt still fires.
- [ ] **AC-4 (per-task glue contract preserved)**: the `GUARDKIT_BDD_TASK_ID`
  per-task lookup + the legacy `test_<slug>.py` fallback continue to work, no race
  regression (`.claude/rules/bdd-per-task-glue.md`).
- [ ] **AC-5**: the legacy `bdd_runner.py` is either removed or demoted to an
  explicit, single-documented-switch fallback; no two oracles silently disagree.
- [ ] **AC-6 (Python integration tests)**: integration tests cover plugin
  discovery, the `BDDRunResult → bundle.bdd` mapping, and the `scenarios_failed > 0`
  rejection gate through the Coach (Python stack).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation Notes

- **Seam:** `guardkit/orchestrator/quality_gates/coach_validator.py` (`bundle.bdd`
  population + `_check_bdd_results`, gate at `coach_validator.py:1617`) and
  `guardkit/orchestrator/quality_gates/coach_evidence.py` (the `bdd` field).
- **Consume:** `from guardkitfactory.bdd import discover` (+ `BDDRunResult`,
  `StackProfile`); guardkit already depends on guardkitfactory via the harness, so
  the cross-repo import is structurally available — respect
  `.claude/rules/namespace-hygiene.md` and use a **lazy** import (`try/except
  ImportError` → fall back to legacy / absent-signal) so `pip install guardkit-py`
  without `[autobuild]` still works.
- **Map** `BDDRunResult` (counts-only contract at `guardkitfactory/bdd/plugin.py`)
  into the `bundle.bdd` dict. `scenarios_attempted` is a non-Optional field on the
  contract — preserve it for the absence-of-failure gate.
- **Preserve** the per-task glue env (`GUARDKIT_BDD_TASK_ID`) and the
  `scenarios_failed > 0` rejection.

## Seam Tests

```python
"""Seam test: verify BDDRunResult -> bundle.bdd mapping preserves scenarios_attempted."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("BDDRunResult")
def test_bdd_run_result_maps_attempted_count():
    """A BDDRunResult with scenarios_attempted=0 maps to bundle.bdd as ABSENT SIGNAL,
    never a silent pass. Producer: guardkitfactory.bdd plugin. Contract:
    scenarios_attempted is non-Optional and must not be coerced from a missing key."""
    # mapped = map_bdd_run_result(BDDRunResult(scenarios_attempted=0, ...))
    # assert mapped["scenarios_attempted"] == 0
    # assert "scenarios_attempted" in mapped  # present, not absent-coerced
    pass

## Coach Validation

- `pytest tests/ -k bdd -v` (Python integration tests pass)
- Independent BDD oracle on a pytest-bdd fixture routes through
  `guardkitfactory.bdd.discover`, not the legacy `bdd_runner`.
- Lint/format checks pass with zero errors.
```
