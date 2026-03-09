---
id: TASK-EMB-004
title: Fix coach_validator env stripping — merge instead of replace
status: completed
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
completed: 2026-03-09T00:00:00Z
priority: high
tags: [autobuild, coach, env, bug]
task_type: implementation
complexity: 2
parent_review: TASK-REV-D2B5
feature_id: FEAT-EMB
wave: 2
implementation_mode: task-work
dependencies: []
---

# Task: Fix coach_validator env stripping

## Description

In `guardkit/orchestrator/quality_gates/coach_validator.py:1191`, the `ClaudeAgentOptions` for SDK-based coach test execution passes `env={"PYTHONPATH": new_pythonpath}`. This **replaces** the entire inherited environment, stripping all env vars (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `EMBEDDING_PROVIDER`, etc.) from the subprocess.

## Acceptance Criteria

- [x] `env=` parameter merges with `os.environ` instead of replacing it
- [x] `PYTHONPATH` override still takes effect (worktree root has priority)
- [x] Existing tests pass
- [x] New test verifies env merge behavior

## Implementation

In `coach_validator.py:1191`, changed:

```python
env={"PYTHONPATH": new_pythonpath},
```

to:

```python
env={**os.environ, "PYTHONPATH": new_pythonpath},
```

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py:1191`
- `tests/unit/test_coach_validator.py` (added `TestSdkEnvMerge` class)

## Test Plan

- Unit test: mock `ClaudeAgentOptions` creation, verify `env` dict contains both `os.environ` keys and the `PYTHONPATH` override
- Verify `PYTHONPATH` value matches expected `worktree_str:original_pythonpath`

## Completion Notes

- Added `TestSdkEnvMerge` class with 2 tests in `test_coach_validator.py`
- All 253 tests pass
