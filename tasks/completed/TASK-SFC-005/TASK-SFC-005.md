---
id: TASK-SFC-005
title: Update COACH_CONSTRAINTS fact with new must_do items
task_type: implementation
status: completed
created: 2026-02-23T14:00:00Z
updated: 2026-02-27T00:00:00Z
completed: 2026-02-27T00:00:00Z
priority: medium
tags: [graphiti, seeding, autobuild-coach, role-constraints]
complexity: 1
parent_review: TASK-REV-5FA4
feature_id: FEAT-SFC
wave: 2
implementation_mode: task-work
dependencies: [TASK-SFC-002]
completed_location: tasks/completed/TASK-SFC-005/
---

# Task: Update COACH_CONSTRAINTS Fact with New Capabilities

## Description

Update the `COACH_CONSTRAINTS` `RoleConstraintFact` in `facts/role_constraint.py` to include the Coach's new Promise Verification and Honesty Verification capabilities in the `must_do` list.

This addresses finding F12 (LOW) from the TASK-REV-5FA4 review.

## Context

- Source of truth: `.claude/agents/autobuild-coach.md`
- The `COACH_CONSTRAINTS` fact is seeded via `seed_role_constraints.py`
- The agent definition is the primary source of truth; these facts should stay in sync

## Changes Required

### 1. Update `COACH_CONSTRAINTS.must_do` list

Add two new items to the `must_do` list:

```python
COACH_CONSTRAINTS = RoleConstraintFact(
    role="coach",
    context="feature-build",
    primary_responsibility="Validate Player's task-work results independently with read-only access",
    must_do=[
        "Read task_work_results.json from Player's execution",
        "Run tests independently (trust but verify)",
        "Verify ALL acceptance criteria met",
        "Check code quality (SOLID/DRY/YAGNI)",
        "Create criteria_verification entry for each completion_promise",
        "Factor Honesty Verification results (honesty_score) into decisions",
        "Either APPROVE or provide specific FEEDBACK"
    ],
    # ... rest unchanged
)
```

### 2. Add good_example for Promise Verification

Add to the `good_examples` list:

```python
"Coach: Created criteria_verification for 4/4 criteria, all verified - APPROVED"
```

## Acceptance Criteria

- [x] `COACH_CONSTRAINTS.must_do` includes "Create criteria_verification entry for each completion_promise"
- [x] `COACH_CONSTRAINTS.must_do` includes "Factor Honesty Verification results (honesty_score) into decisions"
- [x] A good_example referencing criteria_verification is added
- [x] `ruff check guardkit/knowledge/facts/role_constraint.py` passes

## Files Modified

| File | Action |
|------|--------|
| `guardkit/knowledge/facts/role_constraint.py` | Modified (updated COACH_CONSTRAINTS) |
