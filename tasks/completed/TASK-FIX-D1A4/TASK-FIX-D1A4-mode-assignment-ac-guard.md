---
id: TASK-FIX-D1A4
title: Add acceptance criteria count guard to direct mode assignment
status: completed
created: 2026-02-19T00:00:00Z
updated: 2026-02-19T12:00:00Z
completed: 2026-02-19T12:05:00Z
completed_location: tasks/completed/TASK-FIX-D1A4/
priority: medium
tags: [autobuild, direct-mode, feature-plan, mode-assignment]
task_type: feature
complexity: 3
parent_review: TASK-REV-F248
feature_id: FEAT-DM-FIX
wave: 2
dependencies: [TASK-FIX-D1A3]
implementation_mode: task-work
test_results:
  status: passed
  coverage: 100
  last_run: 2026-02-19T12:00:00Z
---

# Task: Add acceptance criteria count guard to direct mode assignment

## Description

Update the mode assignment logic in both `generate_feature_yaml.py` (planning time) and `agent_invoker._auto_detect_direct_mode()` (runtime) to consider the number of acceptance criteria when deciding between direct and task-work mode.

Tasks with >=2 acceptance criteria should default to `task-work` regardless of complexity, because direct mode synthetic reports historically cannot verify criteria (even after TASK-FIX-D1A3, task-work produces richer agent-written reports).

## Root Cause Reference

- TASK-REV-F248 Finding 7: Mode assignment ignores acceptance criteria count
- `generate_feature_yaml.py:268-269`: `if complexity <= 3: mode = "direct"`
- `agent_invoker.py:2446`: Same complexity-only heuristic

## Implementation Plan

### Step 1: Update `generate_feature_yaml.py` (planning time)

```python
# Line 268-271 - current:
if complexity <= 3:
    mode = "direct"
else:
    mode = "task-work"

# Proposed:
ac_count = len(task_data.get("acceptance_criteria", []))
if complexity <= 3 and ac_count < 2:
    mode = "direct"
else:
    mode = "task-work"
```

Also update the `--from-json` path at line 503.

### Step 2: Update `agent_invoker._auto_detect_direct_mode()` (runtime)

Add acceptance criteria count check after complexity check. Read AC from task frontmatter.

### Step 3: Update tests

Update `tests/unit/test_direct_mode_detection.py` and `tests/unit/test_generate_feature_yaml.py`.

## Acceptance Criteria

- [x] Tasks with >=2 acceptance criteria are assigned `task-work` mode at planning time
- [x] Tasks with >=2 acceptance criteria are assigned `task-work` mode at runtime auto-detection
- [x] Tasks with 0-1 acceptance criteria and complexity <=3 still get `direct` mode
- [x] Existing tests updated and passing

## Files to Modify

- `installer/core/commands/lib/generate_feature_yaml.py` (lines 268-271, 503)
- `guardkit/orchestrator/agent_invoker.py` (lines 2411-2469)
- `tests/unit/test_direct_mode_detection.py`
- `tests/unit/test_generate_feature_yaml.py`
