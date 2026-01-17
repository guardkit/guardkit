---
id: TASK-INT-a1b2
title: Add provenance fields to task frontmatter schema
status: backlog
created: 2026-01-17T14:30:00Z
updated: 2026-01-17T14:30:00Z
priority: high
tags:
  - intensity-system
  - frontmatter
  - schema
complexity: 2
parent_review: TASK-REV-FB16
feature: provenance-intensity
wave: 1
implementation_mode: task-work
estimated_minutes: 90
conductor_workspace: provenance-int-wave1-1
dependencies: []
---

# Add Provenance Fields to Task Frontmatter Schema

## Description

Add two new optional fields to the task frontmatter schema to track where tasks originate:

- `parent_review`: Task ID of the review that created this task (via [I]mplement)
- `feature_id`: Feature ID if task was created from `/feature-plan`

These fields enable provenance-aware intensity detection.

## Acceptance Criteria

- [ ] `parent_review` field documented in task-workflow.md rules file
- [ ] `feature_id` field documented in task-workflow.md rules file
- [ ] Both fields are optional (backwards compatible)
- [ ] `/task-review` [I]mplement flow sets `parent_review` on created tasks
- [ ] `/feature-plan` sets `feature_id` on created tasks
- [ ] Example frontmatter updated in documentation

## Technical Approach

### 1. Update Task Workflow Rules

In `.claude/rules/task-workflow.md`, add to Optional Fields:

```yaml
### Optional Fields
- parent_review: Task ID of review that created this task (TASK-REV-XXX)
- feature_id: Feature ID if from /feature-plan (FEAT-XXX)
```

### 2. Update task-review [I]mplement Handler

When creating subtasks from [I]mplement, add:

```yaml
parent_review: TASK-REV-G001  # The review task ID
```

### 3. Update feature-plan Task Creation

When creating tasks from /feature-plan, add:

```yaml
feature_id: FEAT-A1B2  # The feature ID
```

## Files to Modify

- `.claude/rules/task-workflow.md` - Add field documentation
- `installer/core/commands/task-review.md` - Update [I]mplement handler
- `installer/core/commands/feature-plan.md` - Update task creation

## Test Requirements

- [ ] Verify backwards compatibility (tasks without fields still work)
- [ ] Verify parent_review is set when [I]mplement creates tasks
- [ ] Verify feature_id is set when /feature-plan creates tasks
- [ ] Verify fields are preserved when tasks move between states

## Notes

This is a low-risk schema addition. The fields are optional, so existing tasks remain valid. The intensity detection logic (TASK-INT-e5f6) will use these fields.
