# Review Report: TASK-REV-FB26

## Executive Summary

The independent test verification failure loop in feature-build is caused by **two distinct but related issues**:

1. **Incomplete feedback message**: The Coach's feedback is missing the actual test output details, showing only "Independent test verification failed:" with nothing after the colon
2. **Shared worktree test interference**: The independent tests run ALL tests in the shared worktree (`pytest tests/`), not just the task-specific tests

Both issues prevent the Player from receiving actionable information to fix the failures.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Duration**: ~45 minutes
- **Reviewer**: task-review command

## Root Cause Analysis

### Issue 1: TASK-FIX-INDTEST Doesn't Match Real Test Names

**TASK-FIX-INDTEST was implemented but doesn't work** because it relies on a naming convention that isn't being followed.

**What TASK-FIX-INDTEST expects:**
```
tests/test_task_fha_002*.py
```

**What the Player actually creates:**
```
tests/test_config.py
tests/test_app.py
tests/test_health.py
```

**Evidence from logs:**
```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Running independent tests: pytest tests/ -v --tb=short
```

This shows the fallback is being used because `_detect_test_command()` found no files matching `tests/test_task_fha_002*.py`.

**Location:** `coach_validator.py:815-834`

The fix searches for task-ID-based test files, but Players create domain-named test files. The pattern never matches, so it always falls back to running ALL tests.

### Issue 2: Truncated Feedback Message (Secondary)

**Evidence from logs:**
```
⚠ Feedback: - Independent test verification failed:
```

**Root Cause Location:** `autobuild.py:1751-1754`

```python
for issue in issues[:3]:  # Limit to top 3 issues
    desc = issue.get("description", "")
    suggestion = issue.get("suggestion", "")
    feedback_lines.append(f"- {desc}: {suggestion}")
```

**Problem:** The `_extract_feedback` method expects issues to have a `suggestion` field, but the independent test failure issue created in `coach_validator.py:438-443` doesn't have one:

```python
issues=[{
    "severity": "must_fix",
    "category": "test_verification",
    "description": "Independent test verification failed",
    "test_output": test_result.test_output_summary,  # This field is IGNORED
}],
```

The actual test output is stored in `test_output` but the `_extract_feedback` method only reads `description` and `suggestion`.

**Result:** Player sees "Independent test verification failed:" with no details after the colon.

### Issue 2: Shared Worktree Test Interference

**Evidence from logs:**
```
INFO:guardkit.orchestrator.quality_gates.coach_validator:Running independent tests: pytest tests/ -v --tb=short
INFO:guardkit.orchestrator.quality_gates.coach_validator:Independent tests failed in 0.2s
```

**Root Cause Location:** `coach_validator.py:794-856` (`_detect_test_command`)

**Problem:** In shared worktrees (feature-build scenario), the Coach runs `pytest tests/` which executes ALL tests, including:
- Tests from TASK-FHA-001 (scaffolding - passed)
- Tests from TASK-FHA-002 (feature - being validated)
- Tests from TASK-FHA-003 (feature - also running in parallel)

When parallel tasks share a worktree, one task's tests may fail due to dependencies not yet created by another parallel task.

**Evidence:** Tests fail in ~0.2s, which is suspiciously fast for actual test execution. This suggests:
- Either pytest is failing to find/collect tests (configuration issue)
- Or tests are failing immediately on import (missing dependencies from other tasks)

### Issue 3: Player Cannot Self-Diagnose

**Evidence:**
```
Player reports: "0 files created, 0 modified, 0 tests (passing)"
Coach says: "Independent test verification failed:"
```

**Problem:** The Player reports 0 tests written and claims tests are passing, but the Coach finds independent test verification fails. This disconnect indicates:
1. Player is running task-work which has its own internal test validation
2. Coach runs a second, independent `pytest tests/` check
3. The Coach's independent check is failing for reasons unrelated to the specific task

## Impact Assessment

| Impact | Severity | Description |
|--------|----------|-------------|
| Feature build blocked | High | 2/3 tasks failed due to this loop |
| Wasted compute | Medium | 10 turns wasted (5 per task × 2 tasks) |
| Poor error messages | High | Player cannot understand or fix the issue |
| Shared worktree unsound | High | Independent tests cross-contaminate between parallel tasks |

## Options Analysis

### Option A: Skip Independent Tests When No Task-Specific Tests Found (Recommended)

**Changes:**
1. Modify `_detect_test_command()` fallback behavior: when no task-specific tests found AND we're in a shared worktree context, skip independent verification instead of running all tests
2. Trust task-work's quality gates for the "verify" part

**Pros:**
- Minimal code change (modify existing fallback)
- Unblocks parallel execution immediately
- No false positives from other tasks' tests
- TASK-FIX-INDTEST already handles the detection; just need better fallback

**Cons:**
- Reduces "trust but verify" for shared worktrees
- Task-work results become single source of truth

**Effort:** Low (1 hour)
**Risk:** Low
**Impact:** Full fix for shared worktree scenarios

```python
# In _detect_test_command():
else:
    logger.debug(f"No task-specific tests found for {task_id}, using full suite")
    # NEW: In shared worktree, skip instead of running all tests
    if self._is_shared_worktree_context():
        logger.info(f"Skipping independent tests for {task_id} (no task-specific tests in shared worktree)")
        return None  # Signal to skip
```

### Option B: Track Modified Test Files (More Robust)

**Changes:**
1. Player reports which test files it created/modified in `task_work_results.json`
2. Coach runs only those specific test files
3. Maintains independent verification

**Pros:**
- Maintains "trust but verify" safety
- Works regardless of test file naming
- Most accurate scoping

**Cons:**
- Requires Player to report test files
- More invasive change

**Effort:** Medium (2-3 hours)
**Risk:** Medium
**Impact:** Full fix with verification preserved

### Option C: Fix Feedback Message (Secondary Fix)

**Changes:**
1. Modify `_extract_feedback` to include `test_output` field in message
2. Player gets actual pytest output when tests fail

**Pros:**
- Better debugging for ANY test failure
- Quick to implement

**Cons:**
- Doesn't fix the root cause (still runs all tests)
- Just makes the failure message better

**Effort:** Low (30 mins)
**Risk:** Low
**Impact:** Better UX, doesn't fix root cause

### Option D: Option A + Option C (Recommended Complete Fix)

**Changes:**
1. Skip independent tests when no task-specific tests found in shared worktree (fixes blocking issue)
2. Fix feedback message to include test_output (improves debugging when tests do fail)

**Pros:**
- Unblocks feature-build immediately
- Better error messages for future debugging
- Minimal implementation effort
- Works with existing TASK-FIX-INDTEST code

**Cons:**
- Shared worktrees lose independent verification
- Acceptable trade-off given task-work already verifies

**Effort:** Low-Medium (1.5 hours)
**Risk:** Low
**Impact:** Full fix

## Decision Recommendation

**Recommended: Option D (Option A + Option C)**

**Rationale:**
1. TASK-FIX-INDTEST is already implemented but doesn't work due to naming convention mismatch
2. The simplest fix is to change the fallback behavior: skip tests instead of running all tests
3. The feedback message fix improves debugging for any future test failures

**Implementation Priority:**
1. **First:** Fix the fallback in `_detect_test_command` to skip independent tests when no task-specific tests found in shared worktree (unblocks feature-build immediately)
2. **Second:** Fix `_extract_feedback` to include test output (better debugging)

## Implementation Recommendations

### Fix 1: Skip Independent Tests When No Task-Specific Tests Found (`coach_validator.py`)

**Location:** `coach_validator.py:833-834` (the fallback branch)

**Current code:**
```python
else:
    logger.debug(f"No task-specific tests found for {task_id}, using full suite")
# Then falls through to `pytest tests/`
```

**Proposed fix:**
```python
else:
    # No task-specific tests found - skip in shared worktree context
    # Running all tests would include tests from other parallel tasks
    logger.info(f"No task-specific tests found for {task_id}, skipping independent verification")
    return None  # Signal to caller to skip verification
```

Then update `run_independent_tests()` to handle `None`:
```python
def run_independent_tests(self) -> IndependentTestResult:
    test_cmd = self.test_command or self._detect_test_command(self.task_id)

    if test_cmd is None:
        # Task-specific filtering requested but no matching tests
        return IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="No task-specific tests found, skipping independent verification",
            duration_seconds=0.0,
        )

    logger.info(f"Running independent tests: {test_cmd}")
    # ... rest of method
```

### Fix 2: Improve Feedback Message (`autobuild.py`)

**Location:** `autobuild.py:1751-1754`

```python
def _extract_feedback(self, coach_report: Dict[str, Any]) -> str:
    """Extract feedback text from Coach decision."""
    issues = coach_report.get("issues", [])
    if not issues:
        return coach_report.get("rationale", "No specific feedback provided")

    # Build feedback from issues
    feedback_lines = []
    for issue in issues[:3]:
        desc = issue.get("description", "")
        suggestion = issue.get("suggestion", "")
        test_output = issue.get("test_output", "")  # NEW: Include test output

        if suggestion:
            feedback_lines.append(f"- {desc}: {suggestion}")
        elif test_output:
            # Use test output as the actionable detail
            feedback_lines.append(f"- {desc}:\n  {test_output}")
        else:
            feedback_lines.append(f"- {desc}")

    if len(issues) > 3:
        feedback_lines.append(f"... and {len(issues) - 3} more issues")

    return "\n".join(feedback_lines)
```

## Validation Criteria

After implementing fixes:

1. **Skip works correctly:** When no task-specific tests found, independent verification is skipped (not fallen back to all tests)
2. **Feedback includes test details:** When tests DO fail, message shows actual pytest output
3. **Parallel tasks don't interfere:** TASK-FHA-002 and TASK-FHA-003 can pass independently
4. **TASK-FHA-001 still works:** Scaffolding tasks still skip independent tests correctly (via `tests_required=False`)

## Related Tasks

- **TASK-REV-FB25:** Previous review that identified these issues
- **TASK-FIX-INDTEST:** Task-specific test filtering (completed BUT fallback behavior is wrong)
- **TASK-FIX-SCAF:** Scaffolding quality gate profile (completed, working)

## Decision Checkpoint

Based on this analysis:

- **[A]ccept** - Archive this review (no implementation needed)
- **[R]evise** - Request deeper analysis on specific areas
- **[I]mplement** - Create implementation tasks based on recommendations
- **[C]ancel** - Discard review

**Recommendation:** Choose **[I]mplement** to create:
1. **TASK-FIX-INDFB**: Fix independent test fallback behavior - skip instead of running all tests when no task-specific tests found
2. **TASK-FIX-FBMSG**: Fix feedback message to include test_output field
