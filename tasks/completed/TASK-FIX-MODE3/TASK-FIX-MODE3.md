---
id: TASK-FIX-MODE3
title: Default to task-work mode for non-trivial tasks (complexity >= 2)
status: completed
created: 2026-03-20T23:30:00Z
updated: 2026-03-20T23:30:00Z
completed: 2026-03-20T23:45:00Z
priority: medium
tags: [autobuild, implementation-mode, routing, configuration, P1]
parent_review: TASK-REV-8BC0
feature_id: FEAT-8BC0
implementation_mode: task-work
wave: 2
complexity: 3
depends_on:
  - TASK-FIX-GEN1
---

# Task: Default to Task-Work Mode for Non-Trivial Tasks

## Description

The FEAT-5606 analysis revealed significant structural advantages of task-work mode over direct mode:
- Natural generator exhaustion (no cancel scope race condition)
- 1.5x SDK timeout multiplier
- Agent-written reports with real completion_promises (vs synthetic reports)
- Rich stream parsing with tool use tracking

Direct mode's only advantage is lower overhead for trivial tasks. For complexity >= 2, the reliability benefits of task-work mode far outweigh the setup cost.

## Acceptance Criteria

- [x] Implementation mode routing logic defaults to `task-work` for tasks with complexity >= 2
- [x] Direct mode is only used when: (a) explicitly set in task frontmatter as `implementation_mode: direct`, OR (b) task type is `scaffolding` and complexity <= 1
- [x] The routing logic change is in `AgentInvoker._get_implementation_mode()` or equivalent
- [x] Feature YAML `implementation_mode` field still overrides the default
- [x] Add logging when mode is auto-selected vs explicitly set
- [x] Existing tests updated for new default behaviour

## Key Files

- `guardkit/orchestrator/agent_invoker.py` (`_get_implementation_mode`)
- `guardkit/orchestrator/feature_loader.py` (feature YAML parsing)

## Notes

This depends on TASK-FIX-GEN1 because if the generator lifecycle is fixed, direct mode becomes more reliable — but task-work is still structurally superior for non-trivial tasks.

## Completion Summary

### Changes Made
- `agent_invoker.py`: Simplified `_auto_detect_direct_mode()` — direct mode now only for `task_type: scaffolding` with `complexity <= 1`. All other tasks default to task-work.
- `agent_invoker.py`: Changed `logger.debug` → `logger.info` in `_get_implementation_mode()` for explicit vs auto-selected mode visibility.
- `test_direct_mode_detection.py`: Fully rewritten (29 tests) for new routing logic.
- `test_agent_invoker.py`: Updated 4 tests in `TestDirectModeAutoDetection` class.

### Test Results
- 29/29 passed (test_direct_mode_detection.py)
- 493/493 passed across all related test files (3 pre-existing failures in unrelated test_cancelled_error_guard_points.py)
