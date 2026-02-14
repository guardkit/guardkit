---
id: TASK-FIX-STUB-D
title: Add anti-stub acceptance criteria to feature plan template
status: backlog
created: 2026-02-13T12:00:00Z
priority: medium
tags: [feature-plan, templates, stub-detection, quality-gates]
parent_review: TASK-REV-STUB
feature_id: FEAT-STUB-QG
implementation_mode: direct
wave: 2
complexity: 2
task_type: documentation
---

# Task: Add anti-stub acceptance criteria to feature plan template

## Description

Update the feature plan task template to include anti-stub criteria as standard acceptance criteria for FEATURE-type tasks. This ensures that when `/feature-plan` generates task breakdowns, each implementation task includes criteria that prevent stubs from being accepted.

## Template Additions

For FEATURE-type tasks, add these standard acceptance criteria:

1. **Anti-stub**: `Primary function(s) contain meaningful implementation logic (not stubs, pass-only bodies, or TODOs)`
2. **End-to-end test**: `At least one test exercises the primary function without mocking its core logic`
3. **Task type clarity**: "Create X" tasks must state "full working implementation, not scaffolding"

## Files to Change

1. Feature plan task template (identify the template file used by `/feature-plan` for task generation)

## Acceptance Criteria

- [ ] AC-001: Feature plan template includes anti-stub criterion for FEATURE-type tasks
- [ ] AC-002: Feature plan template includes end-to-end test criterion requiring non-mocked execution
- [ ] AC-003: Template criteria use AC-NNN format compatible with structured criteria verification
- [ ] AC-004: SCAFFOLDING and INFRASTRUCTURE task types are NOT affected by anti-stub criteria

## Technical Notes

- The feature plan template is used by `/feature-plan` to generate task breakdowns
- These criteria are enforced by the Coach via acceptance criteria verification (once P0-A is applied)
- Template location needs to be identified — likely in `installer/core/` or `.claude/` templates

## References

- Review report: `.claude/reviews/TASK-REV-STUB-review-report.md` (F-7, P1-B)
- Related task: TASK-FIX-STUB-A (enables criteria verification)
- Related task: TASK-FIX-STUB-B (anti-stub rule definition)
