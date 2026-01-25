---
id: TASK-FBSDK-017
title: Add debug logging for quality gate evaluation in Coach validator
status: completed
created: 2026-01-21T20:00:00Z
completed: 2026-01-21T21:15:00Z
priority: high
tags: [feature-build, autobuild, coach-validation, logging, debugging]
parent_review: TASK-REV-FB18
implementation_mode: task-work
complexity: 1
depends_on:
  - TASK-FBSDK-016
completed_location: tasks/completed/TASK-FBSDK-017/
---

# TASK-FBSDK-017: Add Debug Logging for Quality Gate Evaluation

## Problem Statement

When Coach validation fails, there's insufficient logging to understand:
1. What JSON structure was actually received
2. What paths were attempted
3. What values were extracted
4. Why the decision was made

This makes debugging false negatives extremely difficult.

## Acceptance Criteria

- [x] Log the full task_work_results keys on DEBUG level
- [x] Log actual values extracted for each quality gate
- [x] Log the final gate status with all boolean values
- [x] Logging is structured for easy parsing
- [x] No performance impact at INFO level

## Implementation Notes

### Location

`guardkit/orchestrator/quality_gates/coach_validator.py`

### Changes Required

#### 1. Log input structure at method entry

```python
def verify_quality_gates(self, task_work_results: Dict[str, Any]) -> QualityGateStatus:
    """Verify task-work quality gates passed."""

    # Log input structure for debugging
    logger.debug(f"task_work_results keys: {list(task_work_results.keys())}")
    logger.debug(f"quality_gates content: {task_work_results.get('quality_gates', 'NOT_FOUND')}")
    logger.debug(f"test_results content: {task_work_results.get('test_results', 'NOT_FOUND')}")
```

#### 2. Log extracted values

```python
    # Extract and log test results
    quality_gates = task_work_results.get("quality_gates", {})
    tests_passed = quality_gates.get("all_passed", False)
    logger.debug(f"Extracted tests_passed={tests_passed} from quality_gates.all_passed")

    # Extract and log coverage
    coverage_met = quality_gates.get("coverage_met", True)
    logger.debug(f"Extracted coverage_met={coverage_met} from quality_gates.coverage_met")
```

#### 3. Log final decision

```python
    status = QualityGateStatus(
        tests_passed=tests_passed,
        coverage_met=coverage_met,
        arch_review_passed=arch_review_passed,
        plan_audit_passed=plan_audit_passed,
    )

    logger.info(
        f"Quality gate evaluation complete: "
        f"tests={status.tests_passed}, "
        f"coverage={status.coverage_met}, "
        f"arch={status.arch_review_passed}, "
        f"audit={status.plan_audit_passed}, "
        f"ALL_PASSED={status.all_gates_passed}"
    )

    return status
```

#### 4. Log when results not found

```python
def read_quality_gate_results(self, task_id: str) -> Dict[str, Any]:
    """Read quality gate results from task-work execution."""
    results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)

    logger.debug(f"Looking for task_work_results at: {results_path}")

    if not results_path.exists():
        logger.warning(f"task_work_results.json not found at {results_path}")
        logger.debug(f"Worktree path: {self.worktree_path}")
        logger.debug(f"Task ID: {task_id}")
        return {"error": f"Task-work results not found at {results_path}"}

    # ... rest of method
    logger.debug(f"Successfully loaded task_work_results from {results_path}")
```

### Test File

No new tests required - this is logging only.

Verify manually by running with DEBUG level:
```bash
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild task TASK-XXX
```

## Estimated Effort

- Complexity: 1/10
- Time: 10-15 minutes
- Risk: Low (logging only, no behavior changes)

## Future Enhancements

Consider adding structured logging for automated analysis:
```python
logger.debug(
    "quality_gate_evaluation",
    extra={
        "task_id": task_id,
        "tests_passed": tests_passed,
        "coverage_met": coverage_met,
        "arch_review_passed": arch_review_passed,
        "all_gates_passed": status.all_gates_passed,
    }
)
```
