---
id: TASK-FIX-BSEXTRAS01
title: Bootstrap per-dependency path drops the [dev] extra (pytest) → Coach independent-test 0.0s "No module named pytest" false-fail
status: completed
task_type: fix
created: 2026-06-14T11:30:00Z
updated: 2026-06-14T11:55:00Z
completed: 2026-06-14T11:55:00Z
completed_location: tasks/completed/TASK-FIX-BSEXTRAS01/
priority: high
complexity: 5
related: [TASK-FIX-BOOTPYTEST01, TASK-GK-BS-001, TASK-FIX-COACHTESTTO, TASK-FIX-COACHCWD01, TASK-FIX-COACHPYENV, FEAT-9DDE]
implementation_mode: direct
tags: [autobuild, bootstrap, extras, pytest, coach, independent-test, absence-of-failure]
---

# Task: bootstrap incomplete-project path drops [dev] extra → Coach can't run pytest

## Why this task exists

FEAT-9DDE **run 6** (2026-06-14; live-validation of the checkpoint false-red
fix). The Coach's independent test failed in **0.0s** every turn with
`coach_turn_3.json` rationale *"independent test verification failed due to a
missing pytest module in the environment."* The deterministic gate said
`tests=True`, the worktree had both test files, and **COACHCWD01 was intact**
(the Coach subprocess at `coach_validator.py:4027-4039` correctly uses the
pinned worktree interpreter + `cwd=worktree` + `env=_pytest_env()`).

The real defect is upstream in **environment bootstrap**: the worktree `.venv`
was created **without pytest**, so `<worktree>/.venv/bin/python -m pytest`
exits non-zero in 0.0s with "No module named pytest".

> **NOT a COACHCWD01 regression.** The "bare `pytest`" in the run-6 log
> (L439) is just the *logged* `test_cmd` string; the actual exec uses the
> pinned interpreter (L437 `resolved_interpreter=<worktree>/.venv/bin/python`).
> COACHCWD01 holds.

## Root cause

1. guardkit-py's pyproject `name = "guardkit-py"` → import name `guardkit_py`,
   but the package dir is `guardkit/` (no `guardkit_py/`, no `src/`). So
   `DetectedManifest._python_pyproject_is_complete()`
   (`environment_bootstrap.py:192-220`) returns **False**.
2. is_complete False → bootstrap takes the **per-dependency** branch
   (`environment_bootstrap.py:1312-1318`) → `get_dependency_install_commands()`
   → `_python_dep_commands()`.
3. `_python_dep_commands()` (was `:238-257`) read **only**
   `[project.dependencies]` and never `[project.optional-dependencies]`. The
   bootstrap's `python_extras=['dev']` (derived by `derive_bootstrap_extras`,
   the TASK-FIX-BOOTPYTEST01 mechanism) reaches **only** the editable
   `_resolve_python_pyproject_install_command` path (`.[dev]`), which is the
   *complete-project* branch — skipped here. So the "Bootstrap will install
   Python extras: ['dev']" log line (run-6 L28) was a planned-but-never-run
   promise on this path, and **pytest (in `[dev]`) was never installed**.
4. Coach `python -m pytest` → "No module named pytest" → returncode!=0, 0.0s →
   classified `tests_passed=False` **without** `signal_absent` → mislabeled as
   a real Player test failure. This is the inverse of the
   `absence-of-failure-is-not-success` rule: an absent oracle read as a
   negative verdict.

Run-3 (COACHCWD01's origin) did not surface this — its venv happened to have
pytest (it produced real coverage artifacts). Run-6 hit the extras-drop.

## Fix (two load-bearing layers)

**Layer 1 — primary (install pytest into the worktree venv).**
`guardkit/orchestrator/environment_bootstrap.py`:
- New `DetectedManifest.python_extras: tuple[str, ...] = ()` field.
- Populated at the pyproject construction site (`detect()`, ~:953) from the
  detector's `self._python_extras`.
- `_python_dep_commands()` now appends each requested extra's
  `[project.optional-dependencies][<extra>]` deps to the base deps (a missing
  group is logged + skipped, never fatal). The incomplete-project path now
  installs `pytest>=7.4.3` into the worktree venv, mirroring the editable
  `.[dev]` path.

**Layer 2 — defence-in-depth (absent runner ≠ test failure).**
`guardkit/orchestrator/quality_gates/coach_validator.py` (subprocess path
~:4050-4068): when a non-zero pytest return is the **runner itself failing to
start** (`"No module named pytest"`) or **no tests collected** (exit code 5),
set `IndependentTestResult.signal_absent=True`. Narrowly scoped — a Player
test importing a missing *app* module ("No module named myapp") is still a
real failure. This makes ANY future "the oracle didn't run" surface as ABSENT
SIGNAL (handled by the sixth absence-of-failure guard), never a false-red.

## Acceptance Criteria

- [x] The incomplete-project per-dependency install path installs requested
      extras (e.g. `[dev]`/pytest), not only base deps.
- [x] A requested extra absent from the manifest is logged + skipped, not fatal.
- [x] `python_extras=()` (default) is unchanged (backward compatible).
- [x] Coach independent test classifies "No module named pytest" / exit-5
      (no tests collected) as `signal_absent=True`, `tests_passed=False`.
- [x] A genuine test failure (ran and failed) and an app-module import error
      remain `signal_absent=False` (real signal).
- [x] No regression to COACHCWD01 / COACHPYENV interpreter+cwd pinning.

## Tests (all green)
- `tests/unit/orchestrator/test_environment_bootstrap_extras.py::TestPerDepPathHonoursExtras` (4).
- `tests/orchestrator/test_coach_independent_test_timeout.py::TestAbsentRunnerMarksAbsent` (4).
- Regression sweep: 595 passed / 7 skipped across bootstrap, coach_validator,
  coach-independent-test, induced-path-filter, and checkpoint suites.

## Evidence
- Run log: `.guardkit/autobuild/FEAT-9DDE-run6-stdout.log` (L28 extras promise,
  L32-41 base-dep installs with no pytest, L437/439/440 the 0.0s fail).
- Preserved: `docs/retro/run6-evidence/` (coach_turn_3.json rationale).
- Related prior art: TASK-FIX-BOOTPYTEST01 / TASK-GK-BS-001 (editable-path
  extras), TASK-FIX-COACHTESTTO (signal_absent for non-completion paths).
- Rule: `.claude/rules/absence-of-failure-is-not-success.md`.
