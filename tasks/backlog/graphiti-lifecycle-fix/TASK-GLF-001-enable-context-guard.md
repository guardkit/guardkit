---
id: TASK-GLF-001
title: Add enable_context guard to _capture_turn_state
task_type: fix
parent_review: TASK-REV-50E1
feature_id: FEAT-408A
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
status: completed
completed: 2026-02-16T00:00:00Z
priority: high
tags: [graphiti, autobuild, quick-win]
---

# Task: Add enable_context guard to _capture_turn_state

## Description

The `_capture_turn_state()` method in `autobuild.py` checks `graphiti.enabled` but does NOT check `self.enable_context`. When the health check fails and sets `enable_context=False`, turn state capture still attempts Graphiti operations, producing 11 unnecessary "Episode creation request failed" warnings per run.

## Root Cause (from TASK-REV-50E1 Finding 2)

**File**: `guardkit/orchestrator/autobuild.py`, line 2895

```python
if graphiti and graphiti.enabled:  # ← Missing self.enable_context check
```

Two other methods correctly use the pattern:
- `_invoke_player_safely` (line 3261): `if self.enable_context and thread_loader is not None`
- `_get_thread_local_loader` (line 3140): `if not self.enable_context or self._factory is None`

## Acceptance Criteria

- [x] AC-001: `_capture_turn_state()` line 2902 checks `self.enable_context` in addition to `graphiti.enabled`
- [x] AC-002: When `enable_context=False`, `_capture_turn_state()` skips all Graphiti operations and logs at DEBUG level
- [x] AC-003: When `enable_context=True` and `graphiti.enabled=True`, behavior is unchanged (21 existing tests pass)
- [x] AC-004: Test verifies that `_capture_turn_state` respects `enable_context=False`

## Implementation Notes

One-line change at line 2895:

```python
# Change from:
if graphiti and graphiti.enabled:
# To:
if graphiti and graphiti.enabled and self.enable_context:
```

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/autobuild.py` | Add `and self.enable_context` at line 2895 |

## Test Scope

`tests/**/test_*autobuild*capture*` or `tests/**/test_*turn_state*`
