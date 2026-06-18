---
id: TASK-AB-COACHVENV01
title: Refresh Coach venv on intra-wave dependency change
status: completed
task_type: bug
priority: medium
complexity: 4
created: 2026-06-17T11:00:00Z
updated: 2026-06-17T13:30:00Z
completed: 2026-06-17T13:30:00Z
completed_location: tasks/completed/TASK-AB-COACHVENV01/
previous_state: in_review
tags: [autobuild, environment-bootstrap, coach, venv, false-red]
source: docs/retro/autobuild-retro-xref-2026-06-17.md
provenance: fleet-memory FEAT-MEM-05 (tiktoken added+used in one wave)
---

# Task: Refresh Coach venv on intra-wave dependency change

## Description

The worktree venv is bootstrapped once per feature and re-bootstrapped **between** waves
(`feature_orchestrator.py:2216`). When a task **adds a dependency and consumes it within
the same wave** (e.g. `tiktoken` in FEAT-MEM-05), the Coach's independent pytest runs
against the **stale** venv → `ModuleNotFoundError` → the Coach rejects every AC → the
loop stalls, even though the implementation + `pyproject` are correct.

This is a false-red: the deliverable is sound, but the Coach's environment lags the
Player's `pyproject` edit by one wave.

## Acceptance Criteria

- [x] Detect when a turn modifies dependency manifests (`pyproject.toml` /
      `requirements*.txt` / `uv.lock`) in the worktree during a wave.
- [x] On such a change, **reinstall into the worktree venv** (e.g. `uv sync` /
      `uv pip install -e .`) **before** the Coach's independent test run for that turn —
      not only between waves.
- [x] No-op when no manifest change occurred (avoid per-turn reinstall cost on
      unaffected turns).
- [x] Regression/integration test: a single-wave task that adds a dependency to
      `pyproject` and imports it → the Coach's pytest finds the module (no
      `ModuleNotFoundError`), gate evaluates on real results.

## Resolution

Per-turn venv refresh wired into the autobuild Player-Coach loop, sitting between
the Player phase and the Coach's independent test run for the same turn.

**`guardkit/orchestrator/environment_bootstrap.py`** (two new module-level
helpers, reusing the existing idempotent bootstrap machinery):

- `changed_dependency_manifests(changed_paths)` — the cheap diff gate. Matches
  dependency manifests by *basename* (so it is robust to repo-relative,
  worktree-relative, absolute, or `<repo>:<path>` repo-qualified strings) across
  `pyproject.toml`, `uv.lock`, `poetry.lock`, `requirements*.txt`, and the
  node/go/rust/flutter lock+manifest names. Returns the matched subset
  (de-duplicated, order-preserving); empty ⇒ no refresh needed.
- `refresh_environment_for_changes(worktree_root, changed_paths, *,
  python_extras=(), relevant_stacks=None)` — no-op (`None`) when no manifest
  changed or none is detected; otherwise re-runs the idempotent
  `EnvironmentBootstrapper.bootstrap`. The content-hash dedup re-executes the
  install because the manifest content differs from the saved state, and the
  eager-venv path reuses the existing `<root>/.venv`, so the interpreter path is
  stable across the refresh. Returns the `BootstrapResult` for the caller to
  inspect; `bootstrap`'s `UvSourcesRequireUvError` /
  `BootstrapEnvironmentLeakError` propagate.

**`guardkit/orchestrator/autobuild.py`**
(`AutoBuildOrchestrator._maybe_refresh_venv_for_manifest_change` + call site in
`_execute_turn`):

- Reads the Player report's `files_modified` + `files_created` (the post-turn
  diff), gates on `changed_dependency_manifests`, and reinstalls before the Coach
  phase. On success it updates `self._venv_python` from the refreshed interpreter
  and proceeds to the Coach. The hook is placed *after* the ablation early-return
  so it only runs when the Coach will actually verify.
- **Absence-of-failure-safe**: a failed reinstall (non-`success` result, a known
  bootstrap exception, or any unexpected error — logged with `exc_info`) returns
  actionable feedback that the call site converts into a turn-1 `feedback`
  `TurnRecord` (Coach skipped), so a failed reinstall is fed back to the Player
  rather than swallowed into a silent pass / a confusing `ModuleNotFoundError`
  from a Coach run against a stale env. See
  `.claude/rules/absence-of-failure-is-not-success.md`.

**Interpreter pinning** is inherited from TASK-AB-BOOTPY01 — the reused
`bootstrap` eager-venv path already threads `requires-python` into `uv venv`, so
the refreshed venv stays on a compatible interpreter.

**Known limitation**: the per-turn refresh does not re-thread feature-declared
`bootstrap_extras` (the `AutoBuildOrchestrator` holds only `feature_id`, not the
`Feature`). Extras installed by the initial feature bootstrap persist through the
editable reinstall, so the FEAT-MEM-05 case (a base dependency added+consumed in
one wave) is fully covered; a *new* test extra added mid-wave would wait for the
next between-wave bootstrap. Acceptable for v1.

**Tests**: `tests/unit/test_environment_bootstrap_coachvenv.py` (19 tests) —
the diff gate, the refresh helper (no-op / reinstall / FEAT-MEM-05
editable-install-picks-up-dep), and the orchestrator hook (no-op / success
updates interpreter / reinstall-failure → actionable feedback / exception
surfaced). Existing bootstrap suites unaffected (`test_environment_bootstrap`,
`_python_pin`, `_ffc6`, `test_inter_wave_bootstrap`: 164 passed, 1 skipped).

## Implementation Notes

- The detection can reuse the post-turn diff already computed by the evidence loop
  (look for manifest paths in `files_modified`).
- Keep it absence-of-failure-safe: a reinstall failure should surface as actionable
  feedback, not be swallowed into a silent pass.
- Interacts with TASK-AB-BOOTPY01 (interpreter selection) — both touch
  `environment_bootstrap` / the venv lifecycle; sequence or share helpers.

## Provenance

FEAT-MEM-05 (fleet-memory). Cross-reference report
`docs/retro/autobuild-retro-xref-2026-06-17.md` §3.4.
