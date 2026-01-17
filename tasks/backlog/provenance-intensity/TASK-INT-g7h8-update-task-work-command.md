---
id: TASK-INT-g7h8
title: Update task-work command to use intensity system
status: backlog
created: 2026-01-17T14:30:00Z
updated: 2026-01-17T14:30:00Z
priority: high
tags:
  - intensity-system
  - task-work
  - integration
complexity: 3
parent_review: TASK-REV-FB16
feature: provenance-intensity
wave: 2
implementation_mode: task-work
estimated_minutes: 150
conductor_workspace: provenance-int-wave2-2
dependencies:
  - TASK-INT-a1b2
  - TASK-INT-c3d4
---

# Update task-work Command to Use Intensity System

## Description

Integrate the intensity system into the `/task-work` command flow:

1. Read provenance fields from task frontmatter
2. Apply auto-detection (or use flag if provided)
3. Configure phases based on intensity level
4. Display intensity information to user

## Acceptance Criteria

- [ ] task-work reads `parent_review` and `feature_id` from task frontmatter
- [ ] Intensity is resolved before phase execution begins
- [ ] Phase configuration respects intensity level
- [ ] User sees intensity level and reason in output
- [ ] Override message shown if --intensity flag used
- [ ] Backwards compatible with existing task files

## Technical Approach

### 1. Early Intensity Resolution

At the start of task-work execution:

```markdown
## Phase 0: Resolve Intensity

**READ** task frontmatter:
- parent_review: {task.parent_review or "none"}
- feature_id: {task.feature_id or "none"}
- complexity: {task.complexity}

**RESOLVE** intensity:
- If --intensity flag provided: Use flag value
- Else: Auto-detect from provenance + complexity

**DISPLAY**:
```
═══════════════════════════════════════════════════════
INTENSITY: {intensity.upper()}
═══════════════════════════════════════════════════════
Detection: {auto-detected | user-specified}
Reason: {detection_reason}
Phases: {active_phases_list}
Duration estimate: {estimated_duration}
═══════════════════════════════════════════════════════
```
```

### 2. Phase Configuration

```markdown
## Intensity-Based Phase Selection

Based on resolved intensity, configure which phases execute:

**IF intensity == MINIMAL:**
  EXECUTE: Phase 1, 3, 4 (quick), 5 (lint)
  SKIP: Phase 2, 2.5A, 2.5B, 2.7, 2.8, 5.5

**IF intensity == LIGHT:**
  EXECUTE: Phase 1, 2 (brief), 2.8 (10s), 3, 4, 5 (quick), 5.5 (50%)
  SKIP: Phase 2.5A, 2.5B, 2.7

**IF intensity == STANDARD:**
  EXECUTE: All phases
  SKIP: Phase 2.5A if no pattern need detected

**IF intensity == STRICT:**
  EXECUTE: All phases with enhanced validation
  BLOCKING: Phase 2.8 checkpoint
```

### 3. Update Existing Micro Mode

Replace `--micro` handling with intensity:

```markdown
## Micro-Task Mode (Legacy Alias)

The `--micro` flag is now an alias for `--intensity=minimal`.

When used:
1. Intensity set to MINIMAL
2. Same phase configuration as --intensity=minimal
3. Same validation and output
```

## Files to Modify

- `installer/core/commands/task-work.md` - Integrate intensity resolution and phase selection

## Test Requirements

- [ ] Task with parent_review executes minimal phases
- [ ] Task with feature_id executes light phases
- [ ] Fresh complex task executes standard phases
- [ ] --intensity flag overrides auto-detection
- [ ] --micro works as minimal alias
- [ ] Phase skip messages shown in output
- [ ] Duration estimate reflects intensity level

## Notes

This task connects the auto-detection logic (TASK-INT-e5f6) to the actual command execution. Focus on clean integration without breaking existing behavior.

The key change is that intensity is resolved ONCE at the start, then phases check the resolved intensity rather than re-evaluating criteria.
