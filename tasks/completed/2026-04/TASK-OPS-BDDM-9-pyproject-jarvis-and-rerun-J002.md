---
id: TASK-OPS-BDDM-9
title: 'jarvis: add pytest-bdd to pyproject + re-run FEAT-J002 with active BDD verification'
status: completed
created: '2026-04-25T00:00:00Z'
updated: '2026-04-25T18:45:00Z'
completed: '2026-04-25T18:45:00Z'
previous_state: in_review
state_transition_reason: 'AC verified — fix proven working via direct bdd_runner invocation; full autobuild re-run deferred to user post-TASK-OPS-J002-BDD'
completed_location: 'tasks/completed/2026-04/TASK-OPS-BDDM-9-pyproject-jarvis-and-rerun-J002.md'
priority: high
complexity: 4
task_type: bugfix
tags: [bdd, jarvis, cross-repo-remediation, pytest-bdd, critical]
parent_review: TASK-REV-BDDM
feature_id: FEAT-BDDM
implementation_mode: task-work
wave: 3
conductor_workspace: bdd-fix-wave3-jarvis
depends_on: [TASK-FIX-BDDM-1, TASK-FIX-BDDM-2]
target_repo: /Users/richardwoollcott/Projects/appmilla_github/jarvis
followups_filed:
  - 'jarvis:tasks/backlog/TASK-OPS-J002-BDD-pytest-collection-wiring.md'
test_results:
  status: verified_via_direct_invocation
  coverage: null
  last_run: '2026-04-25T18:25:00Z'
  verification_artifact: 'BDDResult(scenarios_passed=0, scenarios_failed=1, scenarios_pending=0) emitted by run_bdd_for_task(TASK-J002-008, jarvis); pre-fix returned None (silent bypass)'
---

# Task: jarvis — add pytest-bdd + re-run FEAT-J002 (CRITICAL)

## Description

**This is the highest-priority Wave 3 task** because jarvis is the only repo audited (2026-04-25) with currently-silent-bypassed BDD verification: **86 `@task:` tags across 3 feature files** for FEAT-J002 / FEAT-J003, with zero pytest-bdd in [pyproject.toml](/Users/richardwoollcott/Projects/appmilla_github/jarvis/pyproject.toml).

Empirical evidence:
- `jarvis/docs/history/autobuild-FEAT-J002-history.md` — 10 occurrences of "pytest-bdd not importable".
- `jarvis/docs/history/autobuild-FEAT-J003-history-cancelled.md` — 11 occurrences.
- jarvis `pyproject.toml` lines 76-78: `pytest, pytest-asyncio, pytest-cov` (no pytest-bdd).

## Acceptance Criteria

- [x] Add `"pytest-bdd>=8.1,<9"` to jarvis `pyproject.toml` test/dev dependencies (matching forge's declaration at `forge/pyproject.toml:34`). — committed in jarvis as `46b9ce4` (`chore(deps): add pytest-bdd>=8.1,<9 to dev group (TASK-OPS-BDDM-9)`).
- [x] Reinstall the jarvis dev environment. — `uv sync --group dev` installed `pytest-bdd==8.1.0` + `gherkin-official==29.0.0`.
- [x] Verify `import pytest_bdd` succeeds in jarvis's worktree env. — confirmed via `from importlib.metadata import version; version('pytest-bdd')` → `'8.1.0'` (the original `__version__` probe in the AC fails on pytest-bdd 8.x because the package no longer exposes the attribute, but the underlying import succeeds).
- [~] ~~Re-run AutoBuild on a representative FEAT-J002 task~~ — **deferred / verified equivalently**. `guardkit autobuild feature FEAT-J002 --task TASK-J002-008 --fresh --verbose` failed at upfront feature validation because jarvis's `.guardkit/features/FEAT-J002.yaml` references `tasks/backlog/...J002-013` and `J002-014` but those files have been moved to `tasks/design_approved/` (pre-existing jarvis state drift unrelated to FEAT-BDDM). The `--task` scope flag does NOT bypass feature-validation. **Verification was instead performed via direct invocation** of the same code path autobuild uses — see "Verification" section below. User authorised deferral of full autobuild re-run until **TASK-OPS-J002-BDD** lands.
- [x] Confirm the resulting result emission now includes a non-vacuous `bdd_results` block. — `BDDResult(scenarios_passed=0, scenarios_failed=1, scenarios_pending=0)` returned by `run_bdd_for_task('TASK-J002-008', jarvis)`. Pre-fix: returned `None` (the silent bypass). Post-fix: real result with one `failures` entry. Structure matches what `agent_invoker._run_bdd_oracle` writes into `task_work_results["bdd_results"]`.
- [x] File follow-up tasks for jarvis-side gaps. — **TASK-OPS-J002-BDD** filed at `jarvis:tasks/backlog/TASK-OPS-J002-BDD-pytest-collection-wiring.md` to address the `[tool.pytest.ini_options].testpaths = ["tests"]` collection gap (the cause of the `pytest_runner_error: exit=4` surfaced by the verification call — pytest-bdd cannot collect from `features/` while testpaths is restricted to `tests/`).
- [x] Document the FEAT-J003 BDD-verification gap as a retrospective. — appended a "Retrospective Note (2026-04-25)" section to `jarvis/docs/history/autobuild-FEAT-J003-history-cancelled.md` explaining the 11 "pytest-bdd not importable" log entries are evidence of silent-bypass on cancelled work; FEAT-J003 will not be re-run.
- [x] Add a comment to jarvis's `pyproject.toml` naming TASK-OPS-BDDM-9 / FEAT-BDDM. — included as a 6-line block above the new pin (and a parallel comment in `tests/test_phase2_dependencies.py::PHASE_1_DEV_PINS`, since the AC-004 guard test required updating to permit the addition).

## Implementation Notes

**Target:** `/Users/richardwoollcott/Projects/appmilla_github/jarvis/`

**Pre-requisite:** TASK-FIX-BDDM-1 must be merged to GuardKit `main` AND jarvis's installed GuardKit version must be updated to include the fix. Otherwise the silent-bypass would continue masking any real BDD failures during the re-run.

**Workflow:**
1. cd to jarvis worktree.
2. Edit `pyproject.toml`. Match forge's pattern. Likely location: in the `[project.optional-dependencies] test` or `[dependency-groups] dev` table — depends on jarvis's setup.
3. Reinstall.
4. Verify import.
5. Pick TASK-J002-008 (or similar) — confirm it's still in jarvis backlog.
6. Run `guardkit autobuild task TASK-J002-008` (or whatever jarvis's invocation is).
7. Inspect `.guardkit/worktrees/.../task_work_results.json` for `bdd_results` key.
8. Document outcome.

**Risk if TASK-FIX-BDDM-1 not yet merged:** the re-run would still silent-bypass. Block this task on Wave 1 GuardKit core fix (already encoded in `depends_on`).

**Risk on jarvis pyproject change:** isolated, well-bounded — adding a dev dependency cannot break runtime jarvis behaviour, only test execution. Verify jarvis's own test suite still passes after the dep is added.

## Notes

- See [.claude/reviews/TASK-REV-BDDM-review-report.md](../../../.claude/reviews/TASK-REV-BDDM-review-report.md) §F.7 + recommendation R7 for context.
- jarvis is in scope because it's the canonical example of the defect this whole feature addresses.

## Verification (2026-04-25)

Pre-flight confirmed `TASK-FIX-BDDM-1` (commit `68bee41f` on guardkit `main`) is in
the editable-installed `guardkit-py` that jarvis's CLI dispatches to. Then ran the
fix's code path directly against jarvis:

```python
from guardkit.orchestrator.quality_gates.bdd_runner import has_pytest_bdd, run_bdd_for_task

JARVIS_PY = '/Users/richardwoollcott/Projects/appmilla_github/jarvis/.venv/bin/python'
assert has_pytest_bdd(JARVIS_PY) is True   # post TASK-OPS-BDDM-9 install ✅

result = run_bdd_for_task(
    task_id='TASK-J002-008',
    worktree_path='/Users/richardwoollcott/Projects/appmilla_github/jarvis',
    python_executable=JARVIS_PY,
)
# result is NOT None → silent bypass closed ✅
# result.scenarios_failed == 1 → non-vacuous bdd_results emission ✅
# result.failures[0].reason starts with 'pytest_runner_error: exit=4' ⚠ jarvis-side gap (TASK-OPS-J002-BDD)
```

Why this is equivalent to the autobuild path: `agent_invoker._run_bdd_oracle()` is
literally a wrapper that calls `run_bdd_for_task()` and assigns its return value to
`results["bdd_results"]`. Same Python function, same input args, same return shape;
only the surrounding orchestration (worktree mgmt, Player/Coach turns) differs.

User direction: full `autobuild feature FEAT-J002 --fresh` to be performed by user
themselves once **TASK-OPS-J002-BDD** lands the pytest-bdd collection wiring in
jarvis. At that point the synthetic `pytest_runner_error` will be replaced with real
scenario pass/fail/pending counts and the strict-AC re-run will surface real BDD
outcomes.

## Files Changed

**jarvis** (committed as `46b9ce4`):
- `pyproject.toml` — added `"pytest-bdd>=8.1,<9"` + 6-line TASK-OPS-BDDM-9 comment block
- `tests/test_phase2_dependencies.py` — extended `PHASE_1_DEV_PINS` with the new pin + reason comment

**jarvis** (uncommitted, alongside the FEAT-J003 doc work that was already uncommitted on jarvis main):
- `tasks/backlog/TASK-OPS-J002-BDD-pytest-collection-wiring.md` — new follow-up task
- `docs/history/autobuild-FEAT-J003-history-cancelled.md` — appended retrospective note

**guardkit** (this task file):
- Status `in_progress` → `in_review`; ACs marked; verification recorded.

Full jarvis test suite: 1003 passed, 2 skipped (no regressions from the dep add).
