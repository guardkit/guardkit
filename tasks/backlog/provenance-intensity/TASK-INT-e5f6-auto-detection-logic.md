---
id: TASK-INT-e5f6
title: Add provenance-aware auto-detection logic
status: backlog
created: 2026-01-17T14:30:00Z
updated: 2026-01-17T14:30:00Z
priority: high
tags:
  - intensity-system
  - auto-detection
  - provenance
complexity: 4
parent_review: TASK-REV-FB16
feature: provenance-intensity
wave: 2
implementation_mode: task-work
estimated_minutes: 150
conductor_workspace: provenance-int-wave2-1
dependencies:
  - TASK-INT-a1b2
  - TASK-INT-c3d4
---

# Add Provenance-Aware Auto-Detection Logic

## Description

Implement the core logic that determines intensity level based on:
1. Task provenance (`parent_review`, `feature_id`)
2. Complexity score
3. High-risk keyword detection

This is the "brain" of the intensity system.

## Acceptance Criteria

- [ ] Tasks with `parent_review` auto-detect to minimal (complexity ≤4) or light (complexity >4)
- [ ] Tasks with `feature_id` auto-detect to light (complexity ≤5) or standard (complexity >5)
- [ ] Fresh tasks use complexity-based detection (current behavior, but with raised threshold)
- [ ] High-risk keywords force strict intensity
- [ ] Detection logic is documented and testable
- [ ] Detection result is displayed to user

## Technical Approach

### 1. Detection Algorithm

```python
def determine_intensity(task: Task) -> Intensity:
    """Determine intensity based on provenance + complexity."""

    # High-risk keywords always force strict
    high_risk = ["security", "authentication", "database", "migration",
                 "breaking", "api", "encryption", "payment"]
    if any(kw in task.description.lower() for kw in high_risk):
        return Intensity.STRICT

    # Check provenance first
    if task.parent_review:
        # Task came from /task-review [I]mplement
        # Review already did architectural analysis
        if task.complexity <= 4:
            return Intensity.MINIMAL
        else:
            return Intensity.LIGHT

    if task.feature_id:
        # Task came from /feature-plan
        # Planning done, but may not have full arch review
        if task.complexity <= 3:
            return Intensity.MINIMAL
        elif task.complexity <= 5:
            return Intensity.LIGHT
        else:
            return Intensity.STANDARD

    # Fresh task from /task-create
    if task.complexity <= 3:
        return Intensity.MINIMAL  # Raised from 1
    elif task.complexity <= 5:
        return Intensity.LIGHT
    elif task.complexity <= 6:
        return Intensity.STANDARD
    else:
        return Intensity.STRICT
```

### 2. User Display

When intensity is auto-detected, show:

```
Intensity: minimal (auto-detected)
  Reason: Task has parent_review: TASK-REV-G001
  Phases skipped: 2, 2.5A, 2.5B, 2.7, 2.8, 5.5

Use --intensity=standard to override.
```

### 3. Override Handling

```python
def resolve_intensity(task: Task, flag_value: Optional[str]) -> Intensity:
    if flag_value:
        # Explicit flag always wins
        return Intensity[flag_value.upper()]
    else:
        # Auto-detect
        return determine_intensity(task)
```

## Files to Modify

- `installer/core/commands/task-work.md` - Add auto-detection spec
- Create new section: "Intensity Auto-Detection"

## Test Requirements

- [ ] Task with parent_review + complexity 3 → minimal
- [ ] Task with parent_review + complexity 6 → light
- [ ] Task with feature_id + complexity 4 → light
- [ ] Fresh task + complexity 2 → minimal
- [ ] Fresh task + complexity 5 → light
- [ ] Fresh task + "security" in description → strict
- [ ] --intensity=strict overrides auto-detection

## Notes

The key insight from user feedback: tasks from `/task-review` already went through architectural analysis (85/100 score in their case). The ceremony was front-loaded, so `/task-work` can use minimal intensity.

This task is the core logic; TASK-INT-g7h8 integrates it into the task-work command flow.
