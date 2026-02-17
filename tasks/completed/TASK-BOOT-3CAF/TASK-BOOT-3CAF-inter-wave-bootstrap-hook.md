---
id: TASK-BOOT-3CAF
title: Add inter-wave bootstrap hook for greenfield projects
status: completed
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
completed: 2026-02-17T00:00:00Z
priority: critical
tags: [autobuild, environment-bootstrap, feature-orchestrator, greenfield]
task_type: feature
complexity: 3
parent_review: TASK-REV-4D57
feature_id: FEAT-BOOT
wave: 1
implementation_mode: task-work
dependencies: [TASK-BOOT-E3C0]
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-17T00:00:00Z
  tests_passed: 63
  tests_failed: 0
---

# Task: Add inter-wave bootstrap hook for greenfield projects

## Description

After each wave completes in `_wave_phase()`, re-run the environment bootstrap to detect and install dependencies from manifests that were created during that wave.

This handles the greenfield case: Wave 1 (scaffolding) creates `pyproject.toml`, but without an inter-wave hook, Wave 2 tasks launch into an environment where those dependencies aren't installed.

See: `.claude/reviews/TASK-REV-4D57-review-report.md` (Revision 3) — Finding 0b and R2.

## Context

The FEAT-BA28 timing gap:
1. Wave 1: TASK-DB-001 creates `pyproject.toml` with sqlalchemy
2. **NO inter-wave hook** — nobody detects or installs from the new manifest
3. Wave 2: TASK-DB-003 Coach runs pytest → `ModuleNotFoundError: No module named 'sqlalchemy'`

## Acceptance Criteria

- [x] `_wave_phase()` in `feature_orchestrator.py` calls `_bootstrap_environment()` after each wave completes
- [x] Bootstrap only installs if NEW manifests appeared since last check (uses `_already_bootstrapped()` hash check from TASK-BOOT-E3C0)
- [x] No redundant installs when manifests haven't changed between waves
- [x] Integration test: mock a two-wave scenario where Wave 1 creates a manifest, verify bootstrap detects and installs before Wave 2
- [x] Existing tests continue to pass

## Key Files

- `guardkit/orchestrator/feature_orchestrator.py` — `_wave_phase()` integration (lines 1120-1123)
- `guardkit/orchestrator/environment_bootstrap.py` — reuses detector from TASK-BOOT-E3C0
- `tests/unit/test_inter_wave_bootstrap.py` — NEW: 8 integration tests

## Completion Notes

The inter-wave bootstrap hook was already implemented in `feature_orchestrator.py` (lines 1120-1123). The missing piece was the integration test suite (`tests/unit/test_inter_wave_bootstrap.py`), which now verifies:

1. **TestInterWaveBootstrapHook** (3 tests): `_bootstrap_environment` called at correct times in `_wave_phase`
2. **TestInterWaveBootstrapDedup** (3 tests): Hash-based dedup prevents redundant installs
3. **TestInterWaveBootstrapGreenfield** (2 tests): End-to-end scenario where Wave 1 creates pyproject.toml

All 63 tests pass (55 existing + 8 new).
