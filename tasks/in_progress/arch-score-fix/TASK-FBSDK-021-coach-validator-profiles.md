---
id: TASK-FBSDK-021
title: Modify CoachValidator to apply task type profiles
status: in_progress
created: 2025-01-21T16:30:00Z
updated: 2025-01-22T08:45:00Z
priority: high
tags: [autobuild, quality-gates, coach-validator, task-types]
parent_review: TASK-REV-FB19
feature_id: FEAT-ARCH-SCORE-FIX
implementation_mode: task-work
wave: 2
conductor_workspace: arch-score-fix-wave2-2
complexity: 5
depends_on: [TASK-FBSDK-020]
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
---

# Task: Modify CoachValidator to apply task type profiles

## Description

Update CoachValidator to read the task type from task metadata and apply the appropriate quality gate profile. This ensures scaffolding tasks skip architectural review while feature tasks maintain full quality gates.

## Acceptance Criteria

- [ ] CoachValidator reads `task_type` from task metadata
- [ ] Applies QualityGateProfile based on task type
- [ ] Defaults to `feature` profile if task_type not specified
- [ ] Quality gate evaluation respects profile settings
- [ ] Feedback messages indicate which gates were skipped vs failed
- [ ] Unit tests verify profile-based validation
- [ ] Integration tests verify end-to-end behavior

## Implementation Notes

### Modify `CoachValidator.validate()`

```python
def validate(
    self,
    task_id: str,
    turn: int,
    task: Dict[str, Any],
) -> CoachValidationResult:
    """Validate with task type profile."""

    # Determine task type and get profile
    task_type_str = task.get("task_type", "feature")
    task_type = TaskType(task_type_str)
    profile = QualityGateProfile.for_type(task_type)

    logger.info(f"Using quality gate profile for task type: {task_type.value}")

    # ... existing validation logic with profile checks ...
```

### Modify `verify_quality_gates()`

```python
def verify_quality_gates(
    self,
    task_work_results: Dict[str, Any],
    profile: QualityGateProfile,
) -> QualityGateStatus:
    """Verify quality gates based on profile."""

    # Architectural review - respect profile
    if profile.arch_review_required:
        code_review = task_work_results.get("code_review", {})
        arch_score = code_review.get("score", 0)
        arch_review_passed = arch_score >= profile.arch_review_threshold
    else:
        arch_review_passed = True  # Skipped for this task type
        logger.debug("Architectural review skipped per task type profile")

    # Coverage - respect profile
    if profile.coverage_required:
        coverage = quality_gates.get("coverage", 0)
        coverage_met = coverage >= profile.coverage_threshold
    else:
        coverage_met = True  # Skipped for this task type
        logger.debug("Coverage check skipped per task type profile")

    # ... similar for tests and plan audit ...
```

### Files to Modify

1. `guardkit/orchestrator/quality_gates/coach_validator.py`
   - Import TaskType and QualityGateProfile
   - Modify `validate()` to accept and use profile
   - Modify `verify_quality_gates()` to apply profile settings
   - Update `_feedback_from_gates()` to indicate skipped gates

2. `tests/unit/test_coach_validator.py`
   - Add tests for each task type profile
   - Test default behavior (no task_type specified)
   - Test profile override scenarios

### Feedback Message Format

For skipped gates, provide clear feedback:
```
Quality gates evaluated (task type: scaffolding):
  ✓ Tests: Passed (optional for scaffolding)
  ⊘ Coverage: Skipped (not required for scaffolding)
  ⊘ Architectural Review: Skipped (not required for scaffolding)
  ✓ Plan Audit: Passed
```

## Related Files

- `guardkit/models/task_types.py` (created in TASK-FBSDK-020)
- `guardkit/orchestrator/autobuild.py` (passes task to validator)

## Notes

This is a key implementation task that makes the task type profiles functional. It depends on TASK-FBSDK-020 for the schema definitions.
