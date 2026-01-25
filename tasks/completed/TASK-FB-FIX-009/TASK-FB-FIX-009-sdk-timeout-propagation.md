---
id: TASK-FB-FIX-009
title: Fix sdk_timeout propagation to TaskWorkInterface
status: completed
created: 2026-01-12T00:00:00Z
updated: 2026-01-12T12:00:00Z
completed: 2026-01-12T12:30:00Z
completed_location: tasks/completed/TASK-FB-FIX-009/
priority: critical
complexity: 3
tags: [feature-build, sdk-timeout, config-propagation, bug-fix]
parent_review: TASK-REV-FB08
organized_files: [
  "TASK-FB-FIX-009-sdk-timeout-propagation.md"
]
---

# Task: Fix sdk_timeout propagation to TaskWorkInterface

## Description

The `--sdk-timeout` CLI flag and YAML config values are being ignored. Despite users specifying `--sdk-timeout 1800`, the hardcoded default of 600s in `TaskWorkInterface` is always used.

**Root Cause:** The `sdk_timeout` value is correctly passed from CLI through `FeatureOrchestrator` to `AutoBuildOrchestrator`, but never passed further to `PreLoopQualityGates` or `TaskWorkInterface`.

## Bug Locations

1. **`guardkit/orchestrator/autobuild.py:722-723`**
   - `PreLoopQualityGates` instantiated without `sdk_timeout` parameter

2. **`guardkit/orchestrator/quality_gates/pre_loop.py:135-151`**
   - `__init__` doesn't accept `sdk_timeout` parameter
   - `TaskWorkInterface` instantiated without `sdk_timeout`

## Requirements

1. Add `sdk_timeout` parameter to `PreLoopQualityGates.__init__`
2. Store `sdk_timeout` as instance variable in `PreLoopQualityGates`
3. Pass `sdk_timeout` when creating `TaskWorkInterface` in `PreLoopQualityGates`
4. Pass `self.sdk_timeout` when creating `PreLoopQualityGates` in `AutoBuildOrchestrator._pre_loop_phase`

## Acceptance Criteria

- [x] `PreLoopQualityGates.__init__` accepts optional `sdk_timeout: int = 600` parameter
- [x] `PreLoopQualityGates` passes `sdk_timeout` to `TaskWorkInterface` constructor
- [x] `AutoBuildOrchestrator._pre_loop_phase` passes `self.sdk_timeout` to `PreLoopQualityGates`
- [x] CLI `--sdk-timeout 1200` results in `TaskWorkInterface` using 1200s timeout
- [x] Unit tests verify sdk_timeout propagation through the chain
- [x] Existing tests continue to pass

## Implementation Summary

### Changes Made

1. **`guardkit/orchestrator/quality_gates/pre_loop.py`**:
   - Added `sdk_timeout: int = 600` parameter to `__init__`
   - Stored `self.sdk_timeout = sdk_timeout`
   - Passed `sdk_timeout_seconds=sdk_timeout` to `TaskWorkInterface`

2. **`guardkit/orchestrator/autobuild.py`**:
   - Updated `_pre_loop_phase` to pass `sdk_timeout=self.sdk_timeout` to `PreLoopQualityGates`

3. **`tests/unit/test_pre_loop_delegation.py`**:
   - Added `TestSdkTimeoutPropagation` test class with 6 tests

4. **`tests/unit/test_autobuild_orchestrator.py`**:
   - Added `TestSdkTimeoutPropagationToPreLoop` test class with 4 tests

### Test Results

All 10 SDK timeout propagation tests pass:
- `test_default_sdk_timeout_is_600`
- `test_custom_sdk_timeout_stored`
- `test_sdk_timeout_passed_to_task_work_interface`
- `test_injected_interface_bypasses_sdk_timeout`
- `test_sdk_timeout_min_value`
- `test_sdk_timeout_max_value`
- `test_pre_loop_phase_passes_sdk_timeout`
- `test_default_sdk_timeout_propagated`
- `test_sdk_timeout_stored_in_orchestrator`
- `test_sdk_timeout_default_value`

All 114 tests in affected files pass.

## Files Modified

- `guardkit/orchestrator/quality_gates/pre_loop.py`
- `guardkit/orchestrator/autobuild.py`
- `tests/unit/test_pre_loop_delegation.py`
- `tests/unit/test_autobuild_orchestrator.py`
