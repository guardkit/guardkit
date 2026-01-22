# Review Report: TASK-REV-FB18

## Executive Summary

This review analyzed the Coach validation failures occurring after TASK-FBSDK-014 fix. The analysis identified **three distinct root causes** that combine to create false negatives in the Player-Coach validation loop. All issues are in the validation layer, not the core orchestration - the actual implementation work is being completed successfully.

**Key Finding**: The `task_work_results.json` schema written by `_write_task_work_results()` does NOT match the schema expected by `CoachValidator.verify_quality_gates()`.

## Review Details

- **Mode**: Decision Review
- **Depth**: Comprehensive
- **Duration**: Investigation of codebase and evidence files
- **Files Analyzed**: 6 core files, 1 evidence file

## Critical Findings

### Finding 1: Schema Mismatch Between Writer and Reader (CRITICAL)

**Severity**: Critical - Causes 100% Coach validation failures

**Evidence Location**:
- Writer: `agent_invoker.py:2228-2246`
- Reader: `coach_validator.py:435-437`

**Root Cause Analysis**:

The `_write_task_work_results()` method writes this structure:

```json
{
  "quality_gates": {
    "tests_passing": true,
    "tests_passed": 7,        // INTEGER - count of passing tests
    "tests_failed": 0,
    "coverage": 85.5,
    "coverage_met": true,
    "all_passed": true
  }
}
```

But `CoachValidator.verify_quality_gates()` reads:

```python
# Line 436-437
test_results = task_work_results.get("test_results", {})  # Wrong key!
tests_passed = test_results.get("all_passed", False)
```

**The Coach is looking for `test_results.all_passed` but the writer creates `quality_gates.all_passed`**

This explains why Coach always reports "Tests did not pass" - it's reading an empty dict that defaults to `False`.

### Finding 2: tests_passed Type Mismatch (HIGH)

**Severity**: High - Causes Player report validation failures

**Evidence Location**:
- Schema: `agent_invoker.py:107` expects `"tests_passed": bool`
- Writer: `agent_invoker.py:1187-1189` passes through raw int from parser
- Parser: `agent_invoker.py:248-249` captures count as int

**Root Cause Analysis**:

The `TaskWorkStreamParser` captures `tests_passed` as an **integer** (count of passing tests):

```python
# Line 248-249
self._tests_passed = int(tests_passed_match.group(1))  # e.g., 7
```

This integer is passed through to the Player report:

```python
# Line 1187-1189
if "tests_passed" in output:
    report["tests_passed"] = output["tests_passed"]  # Still an int!
```

But `PLAYER_REPORT_SCHEMA` expects a **boolean**:

```python
# Line 107
"tests_passed": bool,
```

This causes validation to fail with: `Type errors: tests_passed: expected bool, got int`

### Finding 3: Coverage Schema Mismatch (MEDIUM)

**Severity**: Medium - Additional false negative source

**Evidence Location**:
- Writer: `agent_invoker.py:2239` creates `coverage_met` inside `quality_gates`
- Reader: `coach_validator.py:440-441` expects `coverage.threshold_met`

**Root Cause**:

```python
# Writer creates:
"quality_gates": {
    "coverage": 85.5,          # Just the percentage
    "coverage_met": true,      # Boolean inside quality_gates
}

# Reader expects:
coverage = task_work_results.get("coverage", {})  # Expects a dict
coverage_met = coverage.get("threshold_met", True)  # Wrong path
```

## Verification

**Manual Test Confirmation**:
From evidence file, tests actually pass:
```
$ pytest tests/ -v
7 passed ✓
```

But Coach feedback says:
```
Feedback: - Tests did not pass during task-work execution
```

This confirms the schema mismatch is the root cause.

## Recommendations

### TASK-FBSDK-015: Fix tests_passed Type in Player Report Generation

**Priority**: Critical (blocking all feature-build operations)

**Location**: `guardkit/orchestrator/agent_invoker.py`

**Changes Required**:
1. Line 1187-1189: Convert `tests_passed` to boolean before storing in Player report:
   ```python
   if "tests_passed" in output:
       # Convert count to boolean for schema compliance
       tests_passed_count = output["tests_passed"]
       report["tests_passed"] = tests_passed_count > 0 if isinstance(tests_passed_count, int) else tests_passed_count
   ```

2. Consider adding `tests_passed_count` as separate field if count is needed.

**Estimated Complexity**: 2/10 (simple type conversion)

### TASK-FBSDK-016: Fix Schema Mismatch Between task_work_results Writer and Coach Reader

**Priority**: Critical (blocking all Coach validations)

**Location**:
- `guardkit/orchestrator/agent_invoker.py` (writer)
- `guardkit/orchestrator/quality_gates/coach_validator.py` (reader)

**Option A (Recommended)**: Update Writer to Match Reader's Expected Schema

Change `_write_task_work_results()` to produce:
```json
{
  "test_results": {
    "all_passed": true,
    "total": 7,
    "failed": 0
  },
  "coverage": {
    "line": 85.5,
    "threshold_met": true
  },
  "code_review": {
    "score": 75
  },
  "plan_audit": {
    "violations": 0
  }
}
```

**Option B**: Update Reader to Match Writer's Actual Schema

Change `verify_quality_gates()` to read:
```python
quality_gates = task_work_results.get("quality_gates", {})
tests_passed = quality_gates.get("all_passed", False)
coverage_met = quality_gates.get("coverage_met", True)
```

**Recommendation**: Option B is simpler and less risky - only changes one file.

**Estimated Complexity**: 4/10 (need to ensure backward compatibility)

### TASK-FBSDK-017: Add Debug Logging for Quality Gate Evaluation

**Priority**: Medium (helps diagnose future issues)

**Location**: `guardkit/orchestrator/quality_gates/coach_validator.py`

**Changes Required**:
1. Add logging before reading results:
   ```python
   logger.debug(f"task_work_results keys: {task_work_results.keys()}")
   logger.debug(f"test_results: {task_work_results.get('test_results')}")
   logger.debug(f"quality_gates: {task_work_results.get('quality_gates')}")
   ```

2. Log actual values being compared:
   ```python
   logger.info(f"Quality gate evaluation: tests_passed={tests_passed}, coverage_met={coverage_met}")
   ```

**Estimated Complexity**: 1/10 (logging additions only)

## Decision Matrix

| Fix Task | Impact | Effort | Risk | Priority |
|----------|--------|--------|------|----------|
| FBSDK-015 (type fix) | High | Low | Low | 1 - Critical |
| FBSDK-016 (schema fix) | Critical | Medium | Medium | 1 - Critical |
| FBSDK-017 (logging) | Medium | Low | Low | 2 - High |

## Appendix

### Code Locations Summary

| Issue | Writer Location | Reader Location |
|-------|-----------------|-----------------|
| Schema mismatch | agent_invoker.py:2228-2246 | coach_validator.py:435-437 |
| Type mismatch | agent_invoker.py:1187-1189 | agent_invoker.py:107 |
| Coverage path | agent_invoker.py:2239 | coach_validator.py:440-441 |

### Evidence Files

- Test evidence: `docs/reviews/feature-build/after_fix_TASK-FBSDK-014.md`
- Task definition: `tasks/backlog/TASK-REV-FB18-post-fbsdk014-failure-analysis.md`
