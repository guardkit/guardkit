---
id: TASK-AB-COACHVENV01
title: Refresh Coach venv on intra-wave dependency change
status: backlog
task_type: bug
priority: medium
complexity: 4
created: 2026-06-17T11:00:00Z
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

- [ ] Detect when a turn modifies dependency manifests (`pyproject.toml` /
      `requirements*.txt` / `uv.lock`) in the worktree during a wave.
- [ ] On such a change, **reinstall into the worktree venv** (e.g. `uv sync` /
      `uv pip install -e .`) **before** the Coach's independent test run for that turn —
      not only between waves.
- [ ] No-op when no manifest change occurred (avoid per-turn reinstall cost on
      unaffected turns).
- [ ] Regression/integration test: a single-wave task that adds a dependency to
      `pyproject` and imports it → the Coach's pytest finds the module (no
      `ModuleNotFoundError`), gate evaluates on real results.

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
