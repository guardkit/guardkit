---
id: TASK-AB-001
title: "Orchestrator passes python_executable to bdd_runner.run_bdd_for_task"
task_type: feature
parent_review: TASK-REV-8413
feature_id: FEAT-AB-FIX
wave: 1
implementation_mode: task-work
complexity: 3
estimated_minutes: 30
dependencies: []
working_dir: /home/richardwoollcott/Projects/appmilla_github/guardkit
domain_tags:
  - guardkit
  - orchestrator
  - bdd-oracle
status: completed
updated: 2026-05-10T00:00:00Z
completed: 2026-05-10T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/2026-05/autobuild-bdd-oracle-fix/
---

## Implementation Summary

- Added `AgentInvoker._resolve_worktree_python_executable()` helper resolving
  `<worktree>/.venv/bin/python3` → `<worktree>/.venv/bin/python` → `None`+warning.
- Updated `AgentInvoker._run_bdd_oracle()` to log the resolved path at INFO and
  forward it as `python_executable=` to `bdd_runner.run_bdd_for_task`.
- Added 3 integration tests in `tests/integration/task_work/test_bdd_integration.py`
  covering python3 resolution, python fallback, and the no-venv warning path.
- 44/44 tests pass (existing `test_bdd_runner.py` and `test_bdd_scope_boundary.py`
  unaffected).

## Lessons

- The bdd_runner public API already supported `python_executable`; the gap was a
  single uninstrumented orchestrator caller. Worth the once-over of every
  optional-keyword parameter on quality-gate runners — silent fallthrough to
  system tooling is the most common shape of FEAT-FG-001-style stalls.
- `caplog` works against the module logger name (`logging.getLogger(__name__)`),
  not the package name. Filter explicitly with
  `caplog.at_level("WARNING", logger="guardkit.orchestrator.agent_invoker")`.

# TASK-AB-001: Orchestrator passes python_executable to bdd_runner

## Repository

**Working directory:** this repo (`guardkit`). Parent diagnostic review lives in the sibling
`fleet-gateway` repo at `tasks/backlog/TASK-REV-8413-analyse-autobuild-feat-fg-001-stall.md`.

## Problem

[`bdd_runner.run_bdd_for_task`](../../../guardkit/orchestrator/quality_gates/bdd_runner.py)
already accepts an optional `python_executable` parameter and threads it through to
`_invoke_pytest_bdd` (which prepends `[python_executable, "-m", "pytest", ...]` to the argv).
But the orchestrator's caller does **not** populate it. As a result, the BDD subprocess uses
whichever `pytest` is on `PATH` — usually a user-level pytest whose interpreter does not
have the worktree's editable-installed package on `sys.path`.

This was the root cause of the FEAT-FG-001 stall: every BDD oracle run failed to import
`common`, the worktree's editable package, even though the worktree's own `.venv` could
import it fine.

## Scope

Find the orchestrator code path that invokes `run_bdd_for_task`, and resolve the
worktree's interpreter (typically `<worktree>/.venv/bin/python3`, falling back to
`<worktree>/.venv/bin/python` on Windows-friendly setups). Pass that path as
`python_executable` on every call.

## Acceptance Criteria

- [ ] `run_bdd_for_task` is called with `python_executable=<resolved>` for every autobuild run.
- [ ] Resolution order: `<worktree>/.venv/bin/python3` → `<worktree>/.venv/bin/python` → fall back to `None` (current behaviour) with a logged warning.
- [ ] The resolved path is logged at INFO level on each invocation so it shows up in the run log.
- [ ] If `python_executable` is None and no worktree venv exists, the orchestrator logs a warning: "BDD oracle running against system pytest; worktree-local imports may fail".
- [ ] Existing unit tests for `run_bdd_for_task` continue to pass.
- [ ] New unit test: with a fake worktree containing `.venv/bin/python3`, the orchestrator's caller passes that path through.

## Out of Scope

- Auto-creating the worktree venv (assume `pip install -e ".[dev]"` was already run by `feature-build`).
- Changes to the bdd_runner public API (it already supports `python_executable`).

## Verification

After landing, re-run the FEAT-FG-001 BDD oracle command from the worktree:
```bash
cd .guardkit/worktrees/FEAT-FG-001
guardkit autobuild ... # bdd oracle path should now succeed against `.venv/bin/python3`
```
The junit XML at `.guardkit/bdd/TASK-FG-002_junit.xml` should no longer report
`ModuleNotFoundError: No module named 'common'`.
