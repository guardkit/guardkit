---
id: TASK-CEF-003
title: Add PYTHONPATH to Coach SDK independent test options
status: completed
task_type: implementation
created: 2026-03-07T14:00:00Z
completed: 2026-03-07T15:00:00Z
priority: high
tags: [bug-fix, coach-validator, pythonpath, independent-tests]
complexity: 2
parent_review: TASK-REV-C3F8
feature_id: FEAT-CEF1
wave: 1
implementation_mode: direct
dependencies: []
completed_location: tasks/completed/TASK-CEF-003/
---

# Task: Add PYTHONPATH to Coach SDK independent test options

## Description

Fix the 100% independent test collection failure rate by adding `PYTHONPATH` environment variable to the Coach SDK `ClaudeAgentOptions` in `_run_tests_via_sdk()`. Without this, stale `.pth` files from previous AutoBuild editable installs (`pip install -e .`) pollute `sys.path`, causing pytest to import modules from wrong worktrees.

## Requirements

1. Add `env={"PYTHONPATH": worktree_path}` to `ClaudeAgentOptions` in `_run_tests_via_sdk()`
2. Prepend worktree path to any existing PYTHONPATH (don't replace)
3. Log the PYTHONPATH value at DEBUG level for diagnostics

## Affected Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_run_tests_via_sdk()` method, lines 1179-1191

## Acceptance Criteria

- [x] AC-1: `ClaudeAgentOptions` includes `env` parameter with `PYTHONPATH` set to worktree root
- [x] AC-2: Existing `PYTHONPATH` from environment is preserved (worktree prepended, not replaced)
- [x] AC-3: PYTHONPATH logged at DEBUG level before SDK invocation
- [x] AC-4: No behavior change for tasks without stale `.pth` contamination

## Implementation Summary

Added 6 lines to `_run_tests_via_sdk()` in `coach_validator.py` (lines 1179-1191):
- Reads current `PYTHONPATH` from `os.environ`
- Prepends worktree path with `:` separator (or sets alone if empty)
- Logs at DEBUG level
- Passes via `env={"PYTHONPATH": new_pythonpath}` in `ClaudeAgentOptions`
