---
id: TASK-SFC-006
title: Bump SEEDING_VERSION to force re-seed
task_type: implementation
status: completed
created: 2026-02-23T14:00:00Z
updated: 2026-02-27T00:00:00Z
completed: 2026-02-27T00:00:00Z
completed_location: tasks/completed/TASK-SFC-006/
priority: medium
tags: [graphiti, seeding, version]
complexity: 1
parent_review: TASK-REV-5FA4
feature_id: FEAT-SFC
wave: 2
implementation_mode: task-work
dependencies: [TASK-SFC-001, TASK-SFC-002, TASK-SFC-003, TASK-SFC-004, TASK-SFC-005]
---

# Task: Bump SEEDING_VERSION to Force Re-Seed

## Description

Increment the `SEEDING_VERSION` constant in `seed_helpers.py` so that the next `guardkit graphiti seed` run detects that the seed data has changed and forces a re-seed of all system context.

This addresses recommendation R10 from the TASK-REV-5FA4 review.

## Context

- `SEEDING_VERSION` is defined in `guardkit/knowledge/seed_helpers.py`
- The version check is in `seeding.py`'s `is_seeded()` / `mark_seeded()` functions
- The marker file at `.guardkit/seeding/.graphiti_seeded.json` stores the version
- When the version changes, `--force` is not needed — the version mismatch triggers re-seed

## Changes Required

### 1. Bump `SEEDING_VERSION`

Find the current value and increment the minor version. For example, if currently `"1.5.0"`, change to `"1.6.0"`.

## Acceptance Criteria

- [x] `SEEDING_VERSION` in `seed_helpers.py` is incremented
- [x] `ruff check guardkit/knowledge/seed_helpers.py` passes

## Files to Modify

| File | Action |
|------|--------|
| `guardkit/knowledge/seed_helpers.py` | Modify (bump SEEDING_VERSION) |
