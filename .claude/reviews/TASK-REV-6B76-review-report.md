# Review Report: TASK-REV-6B76

## Executive Summary

**15 failing tests** in `tests/unit/test_coach_validator.py` are caused by tests referencing functions and methods that were **intentionally removed** during TASK-GWR-001 (dead code cleanup) but the corresponding tests were never cleaned up. Additionally, 5 tests from TASK-SC-009 reference `validate_with_graphiti_thresholds()` which was also removed as dead code and has not been re-implemented.

**Recommendation**: Remove all 15 tests. They are orphaned tests for deleted code with no re-implementation planned.

## Review Details

- **Mode**: Root Cause Investigation
- **Depth**: Standard
- **Reviewer**: Claude Opus 4.6
- **Date**: 2026-02-15

## Test Results Summary

- **Total tests in file**: 214
- **Passing**: 184
- **Failing**: 15 (+ 15 duplicate failure lines in output = 15 unique)
- **No regressions** in passing tests

## Failing Test Catalogue

### Class 1: `TestGraphitiThresholdIntegration` (7 tests, line 2026)

| # | Test | Error | Root Cause |
|---|------|-------|------------|
| 1 | `test_get_graphiti_thresholds_returns_profile_when_config_found` | `AttributeError: module does not have attribute 'get_quality_gate_config'` | `get_quality_gate_config` was removed |
| 2 | `test_get_graphiti_thresholds_returns_none_when_no_config` | Same as above | Same |
| 3 | `test_get_graphiti_thresholds_returns_none_when_graphiti_disabled` | `AttributeError: module does not have attribute 'GRAPHITI_AVAILABLE'` | `GRAPHITI_AVAILABLE` was removed |
| 4 | `test_get_graphiti_thresholds_handles_query_error` | `AttributeError: module does not have attribute 'get_quality_gate_config'` | `get_quality_gate_config` was removed |
| 5 | `test_get_graphiti_thresholds_uses_default_threshold_when_none` | Same as above | Same |
| 6 | `test_validate_async_uses_graphiti_profile` | `AttributeError: CoachValidator does not have attribute 'get_graphiti_thresholds'` | `get_graphiti_thresholds()` was removed |
| 7 | `test_validate_async_falls_back_to_default_when_graphiti_unavailable` | Same as above | Same |

### Class 2: `TestQualityGateConfigIntegration` (3 tests, line 2181)

| # | Test | Error | Root Cause |
|---|------|-------|------------|
| 8 | `test_scaffolding_task_gets_relaxed_thresholds` | `AttributeError: module does not have attribute 'get_quality_gate_config'` | `get_quality_gate_config` was removed |
| 9 | `test_high_complexity_feature_gets_strict_thresholds` | Same as above | Same |
| 10 | `test_docs_task_bypasses_most_gates` | Same as above | Same |

### Class 3: `TestCoachContextIntegration` (5 tests, line 3467)

| # | Test | Error | Root Cause |
|---|------|-------|------------|
| 11 | `test_coach_context_injected_medium_complexity` | `AttributeError: CoachValidator has no attribute 'validate_with_graphiti_thresholds'` | Method was removed |
| 12 | `test_coach_context_skipped_simple_task` | Same as above | Same |
| 13 | `test_coach_context_import_failure` | Same as above | Same |
| 14 | `test_coach_context_exception_handled` | Same as above | Same |
| 15 | `test_coach_context_graphiti_unavailable` | Same as above | Same |

## Root Cause Analysis

### Timeline of Events

1. **TASK-GE-005** (in_review): Created `get_quality_gate_config()` in `guardkit/knowledge/quality_gate_queries.py`, `get_graphiti_thresholds()` on `CoachValidator`, and `GRAPHITI_AVAILABLE` flag. Tests were written in `test_coach_validator.py` for these features.

2. **TASK-SC-009** (in_review): Added `validate_with_graphiti_thresholds()` to `CoachValidator` and wrote `TestCoachContextIntegration` tests for it.

3. **TASK-REV-GROI**: Reviewed the Graphiti integration and determined that PATH 10 (Quality Gate Config from Graphiti) was **dead code** - the query infrastructure existed but was intentionally disconnected from the validation flow.

4. **TASK-GWR-001** (completed): Executed the dead code removal:
   - Deleted `guardkit/knowledge/quality_gate_queries.py` (containing `get_quality_gate_config`)
   - Deleted `guardkit/knowledge/seed_quality_gate_configs.py`
   - Removed `get_graphiti_thresholds()` static method from `CoachValidator`
   - Removed `validate_with_graphiti_thresholds()` async method from `CoachValidator`
   - Removed `GRAPHITI_AVAILABLE` import block from `coach_validator.py`
   - **Did NOT remove the corresponding tests**

### Missing Functions (confirmed not in source)

| Function | Was In | Status |
|----------|--------|--------|
| `get_quality_gate_config()` | `guardkit/knowledge/quality_gate_queries.py` | File deleted (TASK-GWR-001) |
| `CoachValidator.get_graphiti_thresholds()` | `coach_validator.py` | Removed (TASK-GWR-001) |
| `CoachValidator.validate_with_graphiti_thresholds()` | `coach_validator.py` | Removed (TASK-GWR-001) |
| `GRAPHITI_AVAILABLE` | `coach_validator.py` | Removed (TASK-GWR-001) |

None of these exist anywhere in the current `guardkit/` source tree.

## Relationship to Graphiti Roadmap

- **TASK-GE-005** (Quality Gate Config Facts): Still `in_review`, but its implementation was deleted by TASK-GWR-001. The task spec describes the feature aspirationally but the code was determined to be dead/disconnected.
- **TASK-SC-009** (Wire Coach Integration): Still `in_review`, implemented `validate_with_graphiti_thresholds()` which was also removed. However, TASK-SC-009's other deliverables (ARCH_CONTEXT_AVAILABLE, build_coach_context import) are still present and working.
- **No re-implementation is planned**: There are no backlog tasks to re-create `get_quality_gate_config`, `get_graphiti_thresholds`, or `validate_with_graphiti_thresholds`.

## Recommendation: Remove All 15 Tests

### Why Remove (Not Skip/xfail)

| Option | Verdict | Rationale |
|--------|---------|-----------|
| **Remove tests** | **Recommended** | Tests exercise deleted code with no re-implementation planned. They are pure noise. |
| Mark as `xfail` | Not recommended | xfail implies the tests should eventually pass. These tests test code that was deliberately deleted as dead code. |
| Mark as `skip` | Not recommended | Same issue - implies temporary skip with intent to re-enable. |
| Implement the functions | Not recommended | TASK-REV-GROI proved these were dead code. Re-implementing would reintroduce dead code. |

### Impact Assessment

- **Risk**: Zero. Tests exercise non-existent code paths. Removing them cannot cause regressions.
- **Coverage**: No impact on coverage since the code being tested doesn't exist.
- **184 passing tests remain** - full validation suite intact.

### Recommended Cleanup Scope

1. Remove `TestGraphitiThresholdIntegration` class (lines 2026-2178)
2. Remove `TestQualityGateConfigIntegration` class (lines 2181-2244)
3. Remove `TestCoachContextIntegration` class (lines 3467-end of class ~3660)
4. Close TASK-GE-005 and TASK-SC-009 with notes that their test artifacts were cleaned up

### Verification After Cleanup

```bash
# Should show 0 failures, ~184 passing (minus removed tests = ~184)
pytest tests/unit/test_coach_validator.py -v
```

## Appendix

### Related Tasks

| Task | Status | Relationship |
|------|--------|-------------|
| TASK-GWR-001 | Completed | Removed the source code these tests exercise |
| TASK-GE-005 | In Review | Created `get_quality_gate_config` (now deleted) |
| TASK-SC-009 | In Review | Created `validate_with_graphiti_thresholds` (now deleted) |
| TASK-REV-GROI | Completed | Review that identified PATH 10 as dead code |

### Key Files

| File | Lines | Description |
|------|-------|-------------|
| `tests/unit/test_coach_validator.py` | 2026-2244, 3467-3660 | Orphaned test classes |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | All | Source module (missing functions confirmed) |
