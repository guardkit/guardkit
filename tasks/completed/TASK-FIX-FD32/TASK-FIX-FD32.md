---
id: TASK-FIX-FD32
title: Fix uv bootstrap command — use `uv sync --frozen` for uv.lock projects
status: completed
task_type: fix
created: 2026-05-02T00:00:00Z
updated: 2026-05-02T00:00:00Z
completed: 2026-05-02T00:00:00Z
completed_location: tasks/completed/TASK-FIX-FD32/
priority: high
complexity: 2
dependencies: []
previous_state: in_review
state_transition_reason: "All in-scope acceptance criteria satisfied; tests passing"
external_reference:
  source_repo: appmilla_github/study-tutor
  parent_review: TASK-REV-FD32
  reports:
    - /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tasks/in_review/TASK-REV-FD32-investigate-autobuild-bootstrap-failure.md
  failure_history:
    - /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/history/autobuild-FEAT-FD32-failed-run-1-history.md
  blocked_features:
    - study-tutor:FEAT-FD32 (Graphiti Runtime Integration Repair)
    - study-tutor:FEAT-1773
related_features: [autobuild, bootstrap-venv]
tags: [autobuild, bootstrap, environment, uv, lockfile, regression-fix]
test_results:
  status: passed
  coverage: null
  last_run: 2026-05-02T00:00:00Z
  suites_run:
    - tests/unit/test_environment_bootstrap.py
    - tests/unit/test_inter_wave_bootstrap.py
    - tests/orchestrator/test_bootstrap_gating.py
  total_passed: 182
  total_failed: 0
---

# Task: Fix uv bootstrap command — use `uv sync --frozen` for uv.lock projects

## Description

`environment_bootstrap.py` selects the wrong uv subcommand when a Python
project ships both `pyproject.toml` and `uv.lock`. It emits

```
uv pip sync uv.lock
```

…but `uv pip sync` accepts only `requirements.txt` or PEP 751
`pylock.toml` — not uv's native `uv.lock` format. The pip-sync front-end
tries to parse `uv.lock` as a PEP 508 requirements file and rejects its
first line (`version = 1`) because `=` is not a valid PEP 508 comparison
operator. This breaks bootstrap for any uv-managed Python project, hard-
failing the entire feature run when `requires-python` is declared (the
smart default sets `bootstrap_failure_mode: block` in that case).

The correct command for a `pyproject.toml` + `uv.lock` project is
`uv sync` — project-aware, reads both files, provisions the venv. Use
`--frozen` so the orchestrator never silently re-locks during bootstrap.

This was diagnosed in study-tutor review **TASK-REV-FD32** (see
`external_reference.reports`). Full root-cause + evidence chain is in
that report; this task is the implementation.

## Root Cause Summary (from review)

- File: `guardkit/orchestrator/environment_bootstrap.py`
- Function: `_resolve_python_pyproject_install_command`
- Buggy line: 481 — `return ["uv", "pip", "sync", "uv.lock"]`
- Stale doc comment row claiming this is correct: lines 396-404 (row 2
  of the behaviour matrix).
- Existing regression test that pins the buggy argv:
  `tests/unit/test_environment_bootstrap.py:321` (and matrix doc at
  `:285`).

## Scope

1. **Code change** — `guardkit/orchestrator/environment_bootstrap.py:481`:
   ```diff
   -    if has_uv_lock and uv_available:
   -        return ["uv", "pip", "sync", "uv.lock"]
   +    if has_uv_lock and uv_available:
   +        return ["uv", "sync", "--frozen"]
   ```

2. **Doc-comment update** — same file, lines 396-404 behaviour matrix:
   - Row 2 (`absent | present | yes`) → install command becomes
     `uv sync --frozen` (not `uv pip sync uv.lock`).
   - Tighten any nearby narrative that still references `uv pip sync`
     as the "lockfile" command.

3. **Test updates** — `tests/unit/test_environment_bootstrap.py`:
   - Update the test at line 321 ("Row 2: no uv-sources, uv.lock
     present, uv on PATH …") to assert the new argv
     `["uv", "sync", "--frozen"]`.
   - Update the matrix doc-block at line 285 to match.
   - Audit the rest of the file for any other assertion pinning the old
     argv.

4. **Regression / smoke test** (recommended):
   - Add a fixture-based test that creates a temp dir with a real
     minimal `pyproject.toml` + `uv.lock` and verifies the resolved
     install command is `["uv", "sync", "--frozen"]`. (Optional but
     cheap; the existing tests already exercise this path
     symbolically.)

5. **Reinstall guardkit** after the patch lands so the `guardkit` CLI on
   the user's PATH picks up the fix. (Note for the implementer — the
   user's environment installs guardkit from this checkout; verify with
   `pip show guardkit` / `uvx guardkit --version` after install.)

## Why `--frozen` (not `--locked`)

`--frozen`: install exactly what `uv.lock` says, do not re-lock, do not
even check whether `pyproject.toml` and `uv.lock` agree. This is the
right choice for an *orchestrator* bootstrap step — it must be
deterministic, must never mutate the lockfile, and the lockfile is
authoritative.

`--locked`: error if `uv.lock` is out of date relative to
`pyproject.toml`. Acceptable alternative — louder failure mode if a
consumer forgot to commit a lockfile update. Either is valid; flag the
choice in the PR description.

`uv sync` with no flag: would *re-lock* on the fly if it deems necessary
— **do not use** in an orchestrator context.

## Acceptance Criteria

- [ ] Line 481 of `environment_bootstrap.py` returns
      `["uv", "sync", "--frozen"]`.
- [ ] Behaviour-matrix comment at lines 396-404 updated to match.
- [ ] `tests/unit/test_environment_bootstrap.py` no longer asserts the
      old argv anywhere; full file passes (`pytest
      tests/unit/test_environment_bootstrap.py -v`).
- [ ] Full unit suite passes
      (`pytest tests/unit/test_environment_bootstrap*.py
       tests/unit/test_inter_wave_bootstrap.py
       tests/orchestrator/test_bootstrap_gating.py -v`).
- [ ] Manual verification (cross-repo):
      1. Reinstall guardkit (`pip install -e
         /Users/richardwoollcott/Projects/appmilla_github/guardkit` or
         however the user's CLI install is wired).
      2. From `/Users/richardwoollcott/Projects/appmilla_github/study-tutor`,
         remove the leftover failed worktree:
         `rm -rf .guardkit/worktrees/FEAT-FD32` (and any matching
         git worktree entry — `git worktree list` /
         `git worktree remove`).
      3. Re-run `guardkit autobuild feature FEAT-FD32 --verbose`.
      4. Confirm Phase 1 Setup completes: bootstrap log shows
         `uv sync --frozen` (not `uv pip sync uv.lock`), worktree venv
         is populated, and Wave 1 dispatches.

## Out of Scope

- Migrating `uv pip sync` callers anywhere else in the codebase — there
  are none (the buggy line was the only `uv … sync` reference per
  `grep -rn "uv.*sync" guardkit/`).
- Changing the smart-default `bootstrap_failure_mode` logic — that gate
  behaved correctly given the broken signal; the bug is purely the
  install command.
- Changes to study-tutor — once the fix is installed, FEAT-FD32 and
  FEAT-1773 unblock with no repo-side action.

## Related

- Parent review: study-tutor `TASK-REV-FD32` (full report + evidence
  chain in `external_reference.reports`).
- Sibling autobuild bootstrap fix already in this repo:
  `TASK-FIX-A7B6-bootstrap-install-optional-extras.md` — adjacent code
  area, useful prior-art reference.
- Failure transcript: `external_reference.failure_history`.
