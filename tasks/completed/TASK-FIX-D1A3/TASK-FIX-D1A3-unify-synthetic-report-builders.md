---
id: TASK-FIX-D1A3
title: Unify synthetic report builders and add file-existence promises to direct mode
status: completed
created: 2026-02-19T00:00:00Z
updated: 2026-02-19T12:00:00Z
completed: 2026-02-19T13:00:00Z
completed_location: tasks/completed/TASK-FIX-D1A3/
previous_state: in_review
state_transition_reason: "All quality gates passed, code review approved"
priority: critical
tags: [autobuild, direct-mode, coach-validator, synthetic-report, bug-fix]
task_type: feature
complexity: 6
parent_review: TASK-REV-F248
feature_id: FEAT-DM-FIX
wave: 1
implementation_mode: task-work
test_results:
  status: passed
  tests_total: 334
  tests_passed: 334
  tests_failed: 0
  new_tests: 18
  last_run: 2026-02-19T13:00:00Z
---

# Task: Unify synthetic report builders and add file-existence promises to direct mode

## Description

Extract a shared synthetic report builder from the two divergent implementations in `autobuild.py` and `agent_invoker.py`, ensuring both the direct mode and state recovery paths produce structurally identical reports with `_synthetic: True` flag and `completion_promises` for scaffolding tasks.

This is the atomic fix for R1+R2+R3 from TASK-REV-F248. R1 alone is useless (Coach hits `_build_all_unmet()` path). R2 alone is incomplete (no `_synthetic` flag). All three must land together.

## Root Cause Reference

- TASK-REV-F248 Findings 1-3, 7-8
- Q1 from SFT-001 diagnostic diagrams (confirmed bug)
- TASK-ASF-006 fix applied to `_build_synthetic_report()` but not `_create_synthetic_direct_mode_report()`

## Implementation Plan

### Step 1: Create shared module `guardkit/orchestrator/synthetic_report.py`

Extract from `autobuild.py:_build_synthetic_report()` and `autobuild.py:_generate_file_existence_promises()`:

```python
def build_synthetic_report(
    task_id: str,
    turn: int,
    files_created: List[str],
    files_modified: List[str],
    tests_written: List[str],
    tests_passed: bool,
    test_count: int,
    test_output_summary: str = "",
    acceptance_criteria: Optional[List[str]] = None,
    task_type: Optional[str] = None,
    source: str = "direct_mode",
    original_error: Optional[str] = None,
    detection_method: str = "git",
    git_changes: Optional[dict] = None,
) -> Dict[str, Any]:
    """Build synthetic Player report with consistent structure.

    Used by both direct mode (agent_invoker) and state recovery (autobuild).
    Always sets _synthetic: True and generates completion_promises when
    acceptance_criteria and task_type are provided.
    """
```

```python
def generate_file_existence_promises(
    files_created: List[str],
    files_modified: List[str],
    acceptance_criteria: List[str],
) -> List[Dict[str, Any]]:
    """Generate file-existence promises for scaffolding tasks.

    Extracted from autobuild._generate_file_existence_promises().
    """
```

### Step 2: Update `agent_invoker._create_synthetic_direct_mode_report()`

Change signature to accept `acceptance_criteria` and `task_type`. Delegate to shared builder.

### Step 3: Update `agent_invoker._invoke_player_direct()`

Pass `acceptance_criteria` and `task_type` through to `_create_synthetic_direct_mode_report()` when SDK doesn't write a report.

### Step 4: Update `agent_invoker._write_direct_mode_results()`

Accept `synthetic: bool` parameter. When True, set `results["_synthetic"] = True` and propagate `completion_promises`.

### Step 5: Update `autobuild._build_synthetic_report()`

Delegate to shared builder. Keep as thin wrapper for backward compatibility.

### Step 6: Update `autobuild._generate_file_existence_promises()`

Delegate to shared function. Keep as thin wrapper.

## Acceptance Criteria

- [x] New `guardkit/orchestrator/synthetic_report.py` module with `build_synthetic_report()` and `generate_file_existence_promises()`
- [x] `_create_synthetic_direct_mode_report()` delegates to shared builder
- [x] `_build_synthetic_report()` delegates to shared builder
- [x] Direct mode `task_work_results.json` includes `_synthetic: True` when report is synthetic
- [x] Direct mode `task_work_results.json` includes `completion_promises` for scaffolding tasks
- [x] Coach validator enters file-existence path for direct mode scaffolding tasks
- [x] All existing autobuild tests pass (no regression)

## Files to Modify

- `guardkit/orchestrator/synthetic_report.py` (NEW)
- `guardkit/orchestrator/agent_invoker.py` (lines 1771-1827, 2539-2632, 2728-2806)
- `guardkit/orchestrator/autobuild.py` (lines 2220-2428)

## Testing Strategy

- Unit tests for `build_synthetic_report()` with various task types
- Unit tests for `generate_file_existence_promises()` with file path matching
- Integration test: direct mode → synthetic report → Coach validation for scaffolding task
- Regression: all existing `test_autobuild*.py` and `test_coach_validator*.py` tests pass
