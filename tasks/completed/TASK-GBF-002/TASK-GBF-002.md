---
id: TASK-GBF-002
title: Extract remaining seeding categories from seeding.py
status: completed
created: 2026-02-07T12:00:00Z
updated: 2026-02-07T18:00:00Z
completed: 2026-02-07T18:00:00Z
completed_location: tasks/completed/TASK-GBF-002/
priority: low
tags: [graphiti, refactoring, code-organization]
parent_review: TASK-REV-C632
feature_id: FEAT-GBF
complexity: 3
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-07T18:00:00Z
  tests_passed: 46
  tests_skipped: 2
  tests_failed: 0
---

# Task: Extract Remaining Seeding Categories from seeding.py

## Description

The review (TASK-REV-C632, Finding 3) noted that `seeding.py` is the largest module at ~1,446 lines. Several seeding categories have already been extracted to dedicated files (e.g., `seed_feature_overviews.py`, `seed_role_constraints.py`, `seed_failed_approaches.py`), but the core categories remain inline.

This task extracts the remaining inline seeding functions to follow the established pattern.

## Objectives

- [x] Identify which seed functions are still inline in `seeding.py`
- [x] Extract each to its own `seed_*.py` module following the existing pattern
- [x] Keep `seeding.py` as the orchestrator only (marker management + `seed_all_system_context()`)
- [x] Update imports (backward-compatible re-exports in `seeding.py`, `__init__.py` unchanged)

## Scope

### In Scope
- `guardkit/knowledge/seeding.py` - Extract inline seed functions
- New `seed_*.py` files for extracted categories
- `guardkit/knowledge/__init__.py` - Update imports

### Out of Scope
- Changing seeding content or episode structure
- CLI layer changes

## Acceptance Criteria

1. [x] `seeding.py` reduced to orchestration logic only (<200 lines) — 193 lines
2. [x] Each seeding category in its own `seed_*.py` file — 15 new modules created
3. [x] All existing seeding tests pass — 46 passed, 2 skipped, 0 failed
4. [x] `guardkit graphiti seed` produces identical results — same orchestrator, same episode data
