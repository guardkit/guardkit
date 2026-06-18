---
id: TASK-AB-BOOTPY01
title: Pin uv venv interpreter to requires-python
status: completed
task_type: bug
priority: medium
complexity: 3
created: 2026-06-17T11:00:00Z
updated: 2026-06-17T12:15:00Z
completed: 2026-06-17T12:15:00Z
completed_location: tasks/completed/TASK-AB-BOOTPY01/
previous_state: in_review
tags: [autobuild, environment-bootstrap, uv, python-version]
source: docs/retro/autobuild-retro-xref-2026-06-17.md
provenance: fleet-memory FEAT-MEM-01 Error 1 (Python 3.10 bootstrap trap)
---

# Task: Pin uv venv interpreter to requires-python

## Description

`uv venv` is invoked with **no `--python` flag** (`environment_bootstrap.py:1675-1681`
and `_ensure_worktree_venv`). On a host with a uv-managed cpython-3.10 (e.g. the
MacBook used for the cloud runs), uv builds the worktree venv on **3.10**, which then
hard-fails the project's `requires-python >=3.12` — every install/test errors and the
feature can't bootstrap.

The machinery to do this correctly already exists — `get_requires_python()`
(`environment_bootstrap.py:313,1328`) reads the manifest — but it is **not threaded
into** the `uv venv` interpreter selection.

## Acceptance Criteria

- [x] `uv venv` is invoked with an explicit `--python` derived from the project's
      `requires-python` (via `get_requires_python()`), so the worktree venv is created
      on a compatible interpreter.
- [x] Applies to **both** the feature bootstrap (`:1675-1681`, `_ensure_uv_venv`) and
      `_ensure_worktree_venv` (eager creation path).
- [x] When `requires-python` is absent/unparseable, behaviour is unchanged (no
      `--python` → uv default); no crash.
- [x] Regression test: a project manifest with `requires-python = ">=3.12"` results in a
      `uv venv` call carrying a `--python` constraint that excludes 3.10.

## Resolution

`_uv_python_request()` (new module-level helper in `environment_bootstrap.py`)
maps a `requires-python` specifier to the lowest `major.minor` it admits
(`>=3.12` → `3.12`, `>=3.12,<4.0` → `3.12`, `^3.11` → `3.11`, `~=3.10` → `3.10`),
returning `None` when absent/unparseable. It is threaded into both `uv venv`
sites:

- `_ensure_worktree_venv(worktree, requires_python=None)` — eager creation; the
  `bootstrap()` call site derives the constraint from the first python manifest
  that declares one. The `python -m venv` fallback (no uv on PATH) is unaffected.
- `_ensure_uv_venv(cwd, requires_python=None)` — AB60 retry; the `_run_install`
  call site passes `manifest.get_requires_python()`.

Both default args preserve the existing call shapes (no `--python` when the
constraint is absent). Tests: `tests/unit/test_environment_bootstrap_python_pin.py`
(18 tests). Full `environment_bootstrap` suite: 230 passed, 12 skipped.

## Implementation Notes

- Map `requires-python` (e.g. `>=3.12`) to a uv `--python` argument (a version like
  `3.12` is sufficient for uv to pick/download a matching interpreter).
- Confirm the same selection is used by any later `uv pip install` / `uv sync` so the
  Coach's independent pytest runs on the same interpreter.

## Provenance

FEAT-MEM-01 Error 1 (fleet-memory). Cross-reference report
`docs/retro/autobuild-retro-xref-2026-06-17.md` §3.3.
