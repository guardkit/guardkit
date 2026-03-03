---
id: TASK-FIX-7539
title: Suppress irrelevant dotnet bootstrap warnings for non-dotnet features
task_type: feature
parent_review: TASK-REV-7535
feature_id: FEAT-CF57
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
status: completed
completed: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:00:00Z
previous_state: in_review
state_transition_reason: "All quality gates passed and acceptance criteria met"
completed_location: tasks/completed/TASK-FIX-7539/
organized_files:
  - TASK-FIX-7539.md
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
---

# Task: Suppress Irrelevant Dotnet Bootstrap Warnings for Non-Dotnet Features

## Description

During FEAT-CF57 (a Python-focused feature), the environment bootstrap phase attempted `dotnet restore` every wave, producing errors about `net8.0-android`/`net8.0-ios` EOL workloads and missing MAUI workloads. These errors are noise — the feature doesn't use .NET at all.

The `dotnet restore` failure is caused by a `tests/fixtures/sample_projects/maui_sample/` fixture project that requires specific .NET MAUI workloads not installed on the build machine.

## Context

From TASK-REV-7535:
> The `dotnet restore` failure occurs every wave and is noise for a Python-focused feature. Consider silencing known-irrelevant bootstrap failures.

The bootstrap runs for every detected stack (dotnet, node, python) regardless of whether the feature's tasks actually use that stack.

## Requirements

### 1. Stack relevance filtering

In `environment_bootstrap.py`, determine which stacks are actually relevant to the current feature's tasks:

- Parse task files for file locations (e.g., `guardkit/*.py` = python, `src/**/*.ts` = node)
- Or use a simpler heuristic: if all tasks are in `guardkit/` or `tests/`, only bootstrap python
- Allow override via feature YAML `stacks:` field

### 2. Graceful bootstrap failure handling

When a non-essential stack fails bootstrap:
- Log at WARNING level (not ERROR)
- Don't count toward `partial` threshold
- Clearly indicate it's a non-relevant stack

### 3. Exclude fixture projects from dotnet restore

The `tests/fixtures/sample_projects/maui_sample/` should be excluded from `dotnet restore` during bootstrap, as it requires workloads that may not be installed. Options:
- Add a `.bootstrapignore` or similar mechanism
- Exclude `tests/fixtures/` from restore discovery
- Use `--ignore-failed-sources` for fixture projects

## Acceptance Criteria

- [x] Non-relevant stacks are either skipped or have failures downgraded to non-blocking warnings
- [x] Bootstrap output clearly indicates which stacks are relevant vs skipped
- [x] The MAUI fixture project doesn't cause bootstrap failures
- [x] Unit tests cover: stack detection, irrelevant stack handling, fixture exclusion

## Implementation Summary

### Changes to `guardkit/orchestrator/environment_bootstrap.py`:

1. **`BootstrapResult`** — 2 new fields:
   - `non_relevant_failures: int = 0` — count of non-blocking failures
   - `skipped_stacks: List[str]` — stacks with non-blocking failures

2. **`ProjectEnvironmentDetector`** — new `exclude_patterns` parameter:
   - Default: `["tests/fixtures"]`
   - Skips directories matching patterns in `_scan_dirs()`
   - Prevents MAUI fixture project from being detected

3. **`EnvironmentBootstrapper.bootstrap()`** — new `relevant_stacks` parameter:
   - Non-relevant stack failures logged at WARNING (not ERROR)
   - Not counted toward `installs_failed`
   - Tracked in `non_relevant_failures` and `skipped_stacks`

### Test Coverage:
- 22 new tests in `tests/unit/test_environment_bootstrap_fix7539.py`
- 127 existing tests pass with zero regressions
- Total: 149/149 tests passing

## File Location

- `guardkit/orchestrator/environment_bootstrap.py`

## Test Location

- `tests/unit/test_environment_bootstrap_fix7539.py`
