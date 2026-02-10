---
id: TASK-AQG-003
title: Propagate feature ID to turn state capture in AutoBuild
status: completed
created: 2026-02-10T20:30:00Z
updated: 2026-02-10T22:00:00Z
completed: 2026-02-10T22:00:00Z
priority: low
task_type: feature
tags: [autobuild, graphiti, turn-state, feature-id]
parent_review: TASK-REV-7972
feature_id: FEAT-AQG
complexity: 2
wave: 2
implementation_mode: task-work
dependencies: []
---

# Task: Propagate Feature ID to Turn State Capture

## Description

All turn states captured during FEAT-FP-002 AutoBuild use `TURN-FEAT-UNKNOWN-1` instead of `TURN-FEAT-FP002-1`. The feature ID is not propagated from FeatureOrchestrator to AutoBuildOrchestrator.

## Root Cause

1. `_extract_feature_id()` (autobuild.py:2444-2474) tries regex `TASK-([A-Z]+)-` on task ID, fails for IDs like `TASK-FP002-001`
2. Falls back to `self._feature_id` which is never set
3. Returns `"FEAT-UNKNOWN"`
4. `FeatureOrchestrator` has the feature ID but doesn't pass it to `AutoBuildOrchestrator`

## Implementation Plan

1. **`guardkit/orchestrator/autobuild.py`**:
   - Add `feature_id: Optional[str] = None` parameter to `__init__()`
   - Store as `self._feature_id`
   - `_extract_feature_id()` checks `self._feature_id` first (precedence), then regex

2. **`guardkit/orchestrator/feature_orchestrator.py`**:
   - Pass `feature_id=feature.id` when creating `AutoBuildOrchestrator` (3 call sites)

## Acceptance Criteria

- [x] AC1: Turn states use correct feature ID (e.g., `TURN-FEAT-FP-002-1`) when run via feature orchestrator
- [x] AC2: Standalone AutoBuild (no feature context) still falls back to regex extraction or `FEAT-UNKNOWN`
- [x] AC3: No regressions in existing AutoBuild orchestrator tests

## Implementation Summary

### Changes Made

**`guardkit/orchestrator/autobuild.py`** (3 changes):
1. Added `feature_id: Optional[str] = None` parameter to `__init__()`
2. Updated `self._feature_id` assignment to use the parameter (line 598)
3. Fixed `_extract_feature_id()`: moved `self._feature_id` check first (precedence) + improved regex from `[A-Z]+` to `[A-Z][A-Z0-9]*` to match alphanumeric prefixes like `FP002`

**`guardkit/orchestrator/feature_orchestrator.py`** (3 call sites):
- Lines 1357, 1531, 1692: Added `feature_id=feature.id` to all `AutoBuildOrchestrator()` constructor calls

**`tests/unit/test_autobuild_orchestrator.py`** (7 new tests):
- Constructor with/without `feature_id` parameter
- `_extract_feature_id()` precedence when feature_id is provided
- Improved regex: alphanumeric (`TASK-FP002-001`), alpha-only (`TASK-GE-001`), fallback (`TASK-001`)

### Test Results

- Orchestrator: 87 passed, 12 pre-existing failures (git worktree + SDK timeout)
- Feature Orchestrator: 66 passed, 12 pre-existing failures (SDK unavailable + timeout)
- Zero regressions introduced

## Key Files

- `guardkit/orchestrator/autobuild.py` (add parameter, store attribute)
- `guardkit/orchestrator/feature_orchestrator.py` (pass feature_id)
- `tests/unit/test_autobuild_orchestrator.py` (verify)
