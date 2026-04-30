---
id: TASK-FIX-A7B1
title: Make smoke_gates.run_smoke_gate honour bootstrap venv interpreter
status: completed
task_type: bugfix
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
completed: 2026-04-30T00:00:00Z
completed_location: tasks/completed/TASK-FIX-A7B1/
previous_state: in_review
state_transition_reason: "All 6 acceptance criteria satisfied; 47 tests passing including new venv regression tests"
priority: high
complexity: 3
dependencies: []
external_reference:
  source_repo: appmilla_github/study-tutor
  reports:
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-report.md
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-addendum-source-traced.md
  related_sibling_task: TASK-FIX-AB7A-001 (workaround in sibling repo's feature YAML)
related_features: [autobuild, bootstrap-venv]
tags: [autobuild, smoke-gate, venv, bootstrap, regression]
test_results:
  status: passing
  coverage: null
  last_run: 2026-04-30T00:00:00Z
  suite: tests/unit/orchestrator/test_smoke_gates_venv.py + test_smoke_gates_exit5.py + test_coach_command_verification.py::TestCommandModels + integration smoke-gate tests
  passed: 47
  failed: 0
---

# Task: Make smoke_gates.run_smoke_gate honour bootstrap venv interpreter

## Description

`guardkit/orchestrator/smoke_gates.py:124-170` `run_smoke_gate(config, cwd, wave_number)`
calls `subprocess.run(config.command, shell=True, cwd=str(cwd),
capture_output=True, text=True, timeout=config.timeout)` without an `env=`
argument. When the bootstrap creates a venv (per
`guardkit/orchestrator/environment_bootstrap.py:1078`, path
`<worktree>/.guardkit/venv/bin/python`), the smoke gate inherits the parent
process PATH — on Ubuntu 24+ this means a bare `python` resolves to nothing
(only `python3` exists), and the gate dies with `exit=127`.

**Impact:** This blocked the entire autobuild for FEAT-70A4 in the sibling
study-tutor repo. The smoke gate command was a sane `python -m pytest …`
invocation that would have worked had it been executed under the bootstrap
venv interpreter.

A second, related defect: `guardkit/orchestrator/quality_gates/command_models.py:79-96`
`build_venv_env` only consults `<worktree>/.venv/bin` when constructing the
PATH-prepended environment, but the bootstrap creates the venv at
`<worktree>/.guardkit/venv/bin`. So even callers who do pass an env via
`build_venv_env` miss the bootstrap venv.

## Cross-reference

- Sibling repo workaround: `TASK-FIX-AB7A-001` literal-paths the smoke gate
  command in the feature YAML to `.guardkit/venv/bin/python -m pytest …`.
  That sidesteps but does not fix the upstream bug.
- Diagnostic: `<sibling>/.claude/reviews/TASK-REV-AB7A-report.md` §1
  ("Smoke-gate venv miss"), and `…-addendum-source-traced.md` §2 for the
  source-line trace.

## Acceptance Criteria

- [x] AC-001: `run_smoke_gate` accepts an optional `venv_python:
      Optional[str] = None` parameter.
- [x] AC-002: When `venv_python` is set, `run_smoke_gate` constructs an env
      that PATH-prepends `Path(venv_python).parent` and passes `env=env` to
      `subprocess.run`.
- [x] AC-003: The call site in `guardkit/orchestrator/feature_orchestrator.py`
      (search for `run_smoke_gate(`) passes the bootstrap venv interpreter
      (`self._bootstrap_venv_python` or equivalent state) when available.
- [x] AC-004: `build_venv_env` in
      `guardkit/orchestrator/quality_gates/command_models.py:79-96` consults
      `<worktree>/.guardkit/venv/bin` in addition to `<worktree>/.venv/bin`.
      The bootstrap-created location is preferred when both exist.
- [x] AC-005: Regression test: smoke gate runs successfully on a worktree
      where only `python3` exists in system PATH but a bootstrap venv has
      been created at `.guardkit/venv/bin/python`. The bare `python` in the
      smoke command resolves to the venv interpreter, not the system PATH.
- [x] AC-006: Existing smoke-gate behaviour preserved when no venv is
      bootstrapped (env=None path unchanged).

## Files Likely To Change

- `guardkit/orchestrator/smoke_gates.py` — `run_smoke_gate` signature and
  subprocess invocation (lines 124-170).
- `guardkit/orchestrator/feature_orchestrator.py` — call site that passes
  the bootstrap venv interpreter (search for `run_smoke_gate`).
- `guardkit/orchestrator/quality_gates/command_models.py` — `build_venv_env`
  (lines 79-96) extended to consult `.guardkit/venv/bin`.
- Test additions — likely under `tests/orchestrator/` covering the
  Ubuntu-24-only-`python3` case.

## Out Of Scope

- Restructuring the bootstrap venv path itself (keep `.guardkit/venv/`).
- Replacing `shell=True` invocations elsewhere in the codebase.
- Cross-platform Windows-shell concerns (no current evidence of Windows
  smoke-gate use).
