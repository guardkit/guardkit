---
id: TASK-BOOT-214B
title: Add requires_infrastructure to FEAT-BA28 database tasks
status: completed
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T22:00:00Z
completed: 2026-02-17T22:05:00Z
priority: high
tags: [autobuild, infrastructure, configuration, feat-ba28]
task_type: feature
complexity: 2
parent_review: TASK-REV-4D57
feature_id: FEAT-BOOT
wave: 2
implementation_mode: direct
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
completed_location: tasks/completed/TASK-BOOT-214B/
---

# Task: Add requires_infrastructure to FEAT-BA28 database tasks

## Description

Update FEAT-BA28.yaml to add `requires_infrastructure: [postgresql]` to tasks that need PostgreSQL. Currently all 5 tasks have `requires_infrastructure: []`, which means the Docker lifecycle is entirely skipped.

See: `.claude/reviews/TASK-REV-4D57-review-report.md` (Revision 3) — Finding 2 and R4.

## Acceptance Criteria

- [x] TASK-DB-003, TASK-DB-004, and TASK-DB-005 in FEAT-BA28.yaml have `requires_infrastructure: [postgresql]`
- [x] TASK-DB-001 (scaffolding) and TASK-DB-002 (config) remain `requires_infrastructure: []` (they create infrastructure, they don't depend on it being running)
- [x] Feature YAML validates correctly after changes

## Key Files

- `guardkit-examples/fastapi/.guardkit/features/FEAT-BA28.yaml` — feature definition

## Implementation Notes

Updated `guardkit-examples/fastapi/.guardkit/features/FEAT-BA28.yaml`:
- TASK-DB-001 (line 18): `requires_infrastructure: []` — unchanged (scaffolding, creates infra)
- TASK-DB-002 (line 36): `requires_infrastructure: []` — unchanged (config, no runtime DB needed)
- TASK-DB-003 (line 54): `requires_infrastructure: [postgresql]` — updated
- TASK-DB-004 (line 74): `requires_infrastructure: [postgresql]` — updated
- TASK-DB-005 (line 89): `requires_infrastructure: [postgresql]` — updated
