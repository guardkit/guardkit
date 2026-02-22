---
id: TASK-FSRF-001
title: "Commit FalkorDB workaround fix to feature-spec-command branch"
status: completed
task_type: feature
parent_review: TASK-REV-FCA5
feature_id: FEAT-FSRF
created: 2026-02-22T12:00:00Z
updated: 2026-02-22T16:00:00Z
completed: 2026-02-22T16:00:00Z
completed_location: tasks/completed/TASK-FSRF-001/
completion_note: "Changes already committed in 2cad3904. 24/24 tests passing."
priority: high
tags: [falkordb, workaround, graphiti, sanitization]
complexity: 1
wave: 1
implementation_mode: direct
dependencies: []
tests_required: true
---

# Task: Commit FalkorDB workaround fix to feature-spec-command branch

## Description

The working-tree changes to `guardkit/knowledge/falkordb_workaround.py` and `tests/knowledge/test_falkordb_workaround.py` extend the FalkorDB workaround to pre-sanitize backticks, forward slashes, pipes, and backslashes. These changes fix RediSearch syntax errors discovered during FEAT-1253 Graphiti seeding (TASK-REV-661E).

These changes are currently unstaged. They should be committed to the `feature-spec-command` branch since they were directly caused by the FEAT-1253 implementation.

## Acceptance Criteria

- [x] `guardkit/knowledge/falkordb_workaround.py` changes committed
- [x] `tests/knowledge/test_falkordb_workaround.py` changes committed
- [x] All existing tests still pass
- [x] New sanitization tests pass

## Files to Change

- `guardkit/knowledge/falkordb_workaround.py` (stage existing changes)
- `tests/knowledge/test_falkordb_workaround.py` (stage existing changes)
