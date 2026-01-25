---
id: TASK-FIX-ARIMPL
title: "Fix: Skip architectural review gate for --implement-only mode"
status: completed
created: 2026-01-23T20:00:00Z
updated: 2026-01-23T23:00:00Z
completed: 2026-01-23T23:00:00Z
priority: high
tags: [fix, feature-build, quality-gates, autobuild, architectural-review]
task_type: feature
complexity: 4
parent_review: TASK-REV-FB23
related_tasks: [TASK-FIX-ARCH, TASK-FIX-SCAF]
previous_state: in_review
state_transition_reason: "All acceptance criteria met, tests pass"
completed_location: tasks/completed/TASK-FIX-ARIMPL/
---

# Fix: Skip architectural review gate for --implement-only mode

## Problem Statement

Feature tasks (TASK-FHA-002, TASK-FHA-003) running via AutoBuild fail with "Architectural review score below threshold" even though the code for TASK-FIX-ARCH is correctly implemented.

**Root Cause**: The `--implement-only` flag skips Phases 2-2.8 (including Phase 2.5B Architectural Review), so no architectural score is ever generated. The CoachValidator then reads `code_review.score` as 0 (default) and fails the arch review gate.

**Evidence from test run**:
```
INFO:guardkit.orchestrator.feature_orchestrator:Task TASK-FHA-002: Pre-loop skipped (enable_pre_loop=False)
...
INFO:coach_validator:Quality gate evaluation complete: tests=True (required=True),
  coverage=True (required=True), arch=False (required=True), audit=True (required=True),
  ALL_PASSED=False
```

## Proposed Solution

When running with `--implement-only` mode (detected via task state or flag), the architectural review gate should be skipped because:

1. Design is already approved (task is in `design_approved` state)
2. Phase 2.5B doesn't run in implement-only mode
3. Feature-build tasks from `/feature-plan` are pre-designed with detailed specs

### Implementation Approach

**Option A: Task State Detection (Recommended)**

In `coach_validator.py`, detect that the task came from `design_approved` state and skip arch review:

```python
def verify_quality_gates(self, task_work_results, profile=None, skip_arch_review=False):
    # ...
    if skip_arch_review or not profile.arch_review_required:
        arch_review_passed = True
        logger.debug("Architectural review skipped (implement-only mode or profile)")
```

**Option B: Frontmatter Flag**

Add `skip_arch_review: true` to task frontmatter for feature-build tasks.

**Option C: Profile-Based**

Create a new task type profile `feature_implement_only` that has `arch_review_required=False`.

## Acceptance Criteria

- [x] Feature tasks running with `--implement-only` pass quality gates when arch score is not available
- [x] Scaffolding tasks continue to work (no regression)
- [x] Feature tasks with pre-loop enabled (where arch review DOES run) still validate arch scores
- [x] Unit tests added for the new behavior
- [x] Integration test with FEAT-A96D passes (see `tests/integration/test_skip_arch_review_implement_only.py`)

## Files Modified

1. `guardkit/orchestrator/quality_gates/coach_validator.py` ✅
   - Added `skip_arch_review` parameter to `verify_quality_gates()`
   - Updated `validate()` to pass the flag based on context

2. `guardkit/orchestrator/autobuild.py` ✅ (was agent_invoker.py)
   - Added `skip_arch_review` parameter to `_invoke_coach_safely()`
   - Added `skip_arch_review` parameter to `_execute_turn()`
   - Pass `skip_arch_review=not self.enable_pre_loop` when invoking Coach

3. `tests/unit/test_coach_validator.py` ✅
   - Added `TestSkipArchReview` class with 6 tests for skip_arch_review behavior

4. `tests/integration/test_skip_arch_review_implement_only.py` ✅ (NEW)
   - Integration tests for skip_arch_review with implement-only mode
   - Tests CoachValidator behavior when enable_pre_loop=False
   - Tests AutoBuildOrchestrator propagation of skip_arch_review flag

## Test Cases

1. **test_implement_only_skips_arch_review**: Feature task with `--implement-only` and no arch score should pass
2. **test_full_workflow_validates_arch_review**: Feature task with pre-loop should validate arch score
3. **test_scaffolding_still_works**: Scaffolding tasks continue to skip arch review via profile

## Notes

This fix addresses the gap identified in TASK-REV-FB23 where TASK-FIX-ARCH code was correct but the architectural review phase doesn't run in `--implement-only` mode.

## Implementation Mode

This should use `/task-work` with TDD mode to ensure proper test coverage.
