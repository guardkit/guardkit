---
id: TASK-FBSDK-016
title: Fix schema mismatch between task_work_results writer and Coach reader
status: completed
created: 2026-01-21T20:00:00Z
completed: 2026-01-21T21:00:00Z
priority: critical
tags: [feature-build, autobuild, coach-validation, schema-mismatch]
parent_review: TASK-REV-FB18
implementation_mode: task-work
complexity: 4
depends_on:
  - TASK-FBSDK-015
---

# TASK-FBSDK-016: Fix Schema Mismatch Between Writer and Reader

## Problem Statement

Coach validation always fails with "Tests did not pass" even when tests actually pass. This is because `CoachValidator.verify_quality_gates()` reads different JSON paths than what `_write_task_work_results()` creates.

## Root Cause

**Writer creates** (`agent_invoker.py:2228-2246`):
```json
{
  "quality_gates": {
    "tests_passing": true,
    "tests_passed": 7,
    "tests_failed": 0,
    "coverage": 85.5,
    "coverage_met": true,
    "all_passed": true
  }
}
```

**Reader expects** (`coach_validator.py:435-451`):
```python
test_results = task_work_results.get("test_results", {})  # Wrong key!
tests_passed = test_results.get("all_passed", False)       # Returns False

coverage = task_work_results.get("coverage", {})           # Wrong structure!
coverage_met = coverage.get("threshold_met", True)         # Returns True (default)

code_review = task_work_results.get("code_review", {})     # Missing!
arch_score = code_review.get("score", 0)                   # Returns 0
```

## Acceptance Criteria

- [x] Coach correctly reads quality gate results from task_work_results.json
- [x] Coach no longer reports false negatives when tests pass
- [x] Coach no longer reports false negatives for arch review score
- [x] All existing Coach validation tests pass
- [x] New integration test validates end-to-end flow

## Implementation Notes

### Recommended Approach: Update Reader to Match Writer

Modify `verify_quality_gates()` in `coach_validator.py` to read the actual schema:

```python
def verify_quality_gates(self, task_work_results: Dict[str, Any]) -> QualityGateStatus:
    """Verify task-work quality gates passed."""

    # Read from quality_gates object (what writer actually creates)
    quality_gates = task_work_results.get("quality_gates", {})

    # Test results
    tests_passed = quality_gates.get("all_passed", False)
    # Alternative: check tests_failed == 0
    if not tests_passed:
        tests_failed = quality_gates.get("tests_failed", 0)
        tests_passed = tests_failed == 0

    # Coverage
    coverage_met = quality_gates.get("coverage_met", True)

    # Architectural review - may be in separate field or not present
    code_review = task_work_results.get("code_review", {})
    if not code_review:
        # Fall back to quality_gates if code_review not separate
        arch_score = quality_gates.get("arch_score", self.ARCH_REVIEW_THRESHOLD)
    else:
        arch_score = code_review.get("score", 0)
    arch_review_passed = arch_score >= self.ARCH_REVIEW_THRESHOLD

    # Plan audit
    plan_audit = task_work_results.get("plan_audit", {})
    violations = plan_audit.get("violations", 0)
    plan_audit_passed = violations == 0

    # ... rest of method
```

### Files to Modify

1. `guardkit/orchestrator/quality_gates/coach_validator.py`
   - Lines 435-465: Update `verify_quality_gates()` to read correct paths

### Test File

Update: `tests/unit/test_coach_validator.py`

```python
def test_verify_quality_gates_reads_quality_gates_object():
    """Coach should read from quality_gates object, not test_results."""
    task_work_results = {
        "quality_gates": {
            "all_passed": True,
            "tests_passed": 7,
            "tests_failed": 0,
            "coverage_met": True,
        }
    }

    validator = CoachValidator("/path/to/worktree")
    status = validator.verify_quality_gates(task_work_results)

    assert status.tests_passed is True
    assert status.coverage_met is True
    assert status.all_gates_passed is True
```

### Alternative Approach: Update Writer to Match Reader

If changing the reader is too risky, modify `_write_task_work_results()` to create the expected schema:

```python
results = {
    "task_id": task_id,
    "timestamp": datetime.now().isoformat(),
    "completed": completed,
    "test_results": {
        "all_passed": tests_failed == 0,
        "total": tests_passed + tests_failed,
        "failed": tests_failed,
    },
    "coverage": {
        "line": coverage,
        "threshold_met": coverage >= 80 if coverage else True,
    },
    "code_review": {
        "score": 75,  # Default or from parsed data
    },
    "plan_audit": {
        "violations": 0,
    },
    # Keep quality_gates for backward compatibility
    "quality_gates": { ... }
}
```

## Estimated Effort

- Complexity: 4/10
- Time: 30-60 minutes
- Risk: Medium (need to ensure backward compatibility)

## Testing Strategy

1. Unit test: Mock task_work_results with actual schema
2. Integration test: Run full Player-Coach loop with real results
3. Regression test: Ensure old format still works (if applicable)
