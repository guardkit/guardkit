---
id: TASK-TWP-c3d4
title: Lower micro-mode auto-detection threshold to complexity ≤3
status: completed
created: 2026-01-16T12:00:00Z
updated: 2026-01-16T15:45:00Z
completed: 2026-01-16T15:45:00Z
priority: high
tags:
  - performance
  - micro-mode
  - auto-detection
complexity: 3
parent_review: TASK-REV-FB15
feature: task-work-performance
wave: 1
implementation_mode: task-work
estimated_minutes: 90
actual_minutes: 45
dependencies: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, 53/53 tests passing"
completed_location: tasks/completed/TASK-TWP-c3d4/
---

# Lower Micro-Mode Threshold

## Description

The current micro-mode auto-detection threshold is complexity=1, which is too restrictive. Tasks with complexity 3/10 (like TASK-INFRA-001 in the trace) are classified as "Simple" but still run the full workflow, taking 65+ minutes instead of 3-5 minutes.

## Problem Evidence

From `stand_alone_manual_design.md` trace:
```
Complexity: 3/10
Title: Create core configuration with Pydantic Settings
Duration: 65+ minutes (full workflow)
```

With `--micro` mode, this would complete in 3-5 minutes.

## Current Behavior

From `task-work.md`:
```
**Criteria for micro-tasks** (ALL must be true):
- Complexity: 1/10 (single file, <1 hour, low risk)
- Files: Single file modification (or documentation-only)
- Risk: No high-risk keywords
```

This means complexity=2 and complexity=3 tasks don't qualify, even though they're still "simple."

## Proposed Change

Update micro-mode criteria:
- Complexity: **≤3/10** (was 1/10)
- Files: ≤3 files (was single file)
- Risk: No high-risk keywords (unchanged)
- Estimated time: <2 hours (was <1 hour)

## Objectives

- Lower micro-mode threshold from complexity=1 to complexity≤3
- Update file count threshold from 1 to ≤3
- Keep high-risk keyword filtering
- Ensure existing escalation mechanism handles edge cases

## Acceptance Criteria

- [x] Micro-mode auto-detection triggers for complexity ≤3
- [x] Complexity 3 tasks get "Suggest using --micro" prompt
- [x] Complexity 4+ tasks do NOT get micro-mode suggestion
- [x] High-risk keywords (security, database, API) still escalate to full workflow
- [x] Existing `--micro` flag validation still works
- [x] Tests updated for new threshold

## Technical Approach

### 1. Update Auto-Detection Logic

In `task-work.md` or equivalent implementation:

```python
def should_suggest_micro_mode(task_context):
    """Determine if micro-mode should be suggested."""

    # New threshold: complexity ≤3 (was =1)
    if task_context.complexity > 3:
        return False

    # New file threshold: ≤3 files (was =1)
    if task_context.files_affected > 3:
        return False

    # Keep high-risk keyword check
    high_risk_keywords = [
        'security', 'authentication', 'authorization',
        'database', 'migration', 'schema',
        'api', 'breaking', 'encryption'
    ]
    description_lower = task_context.description.lower()
    if any(kw in description_lower for kw in high_risk_keywords):
        return False

    # New time threshold: <2 hours (was <1)
    if task_context.estimated_hours >= 2:
        return False

    return True
```

### 2. Update Documentation

Update `task-work.md` section "Micro-Task Mode":

```markdown
**Criteria for micro-tasks** (ALL must be true):
- Complexity: ≤3/10 (simple tasks)
- Files: ≤3 file modifications
- Risk: No high-risk keywords (security, database, API, etc.)
- Estimated time: <2 hours
```

### 3. Update Validation Logic

The escalation mechanism should remain but with updated thresholds:

```python
def validate_micro_mode(task_context):
    """Validate if task qualifies for micro-mode."""
    if task_context.complexity > 3:
        return False, f"Complexity {task_context.complexity}/10 > 3"
    # ... rest of validation
```

## Files to Modify

- `installer/core/commands/task-work.md` - Update criteria documentation
- Implementation files (if Python orchestration exists)
- Tests for micro-mode detection

## Test Requirements

- [x] Complexity 1 → suggests micro-mode
- [x] Complexity 2 → suggests micro-mode
- [x] Complexity 3 → suggests micro-mode
- [x] Complexity 4 → does NOT suggest micro-mode
- [x] Complexity 3 with "security" keyword → does NOT suggest micro-mode
- [x] Complexity 3 with 4+ files → does NOT suggest micro-mode
- [x] Escalation still works when --micro used on ineligible task

## Notes

This is a low-risk, high-impact change. The existing escalation mechanism ensures that if `--micro` is misused, the system will escalate to full workflow with a warning.

Expected improvement: 90% of simple tasks (complexity ≤3) complete in 3-5 minutes.
