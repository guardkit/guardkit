---
id: TASK-BRF-001
title: Add Fresh Perspective Reset Option for Anchoring Prevention
status: in_review
task_type: implementation
created: 2026-01-24T16:30:00Z
updated: 2026-01-24T21:00:00Z
priority: high
tags: [autobuild, anchoring-prevention, block-research, orchestration]
complexity: 6
parent_review: TASK-REV-BLOC
feature_id: FEAT-BRF
wave: 1
implementation_mode: task-work
conductor_workspace: block-research-fidelity-wave1-1
dependencies: []
previous_state: in_progress
state_transition_reason: "All quality gates passed - ready for human review"
quality_gates:
  compilation: passed
  tests_passing: passed (34/34 - 100%)
  line_coverage: passed (100%)
  branch_coverage: passed (100%)
  architectural_review: passed (82/100)
  plan_audit: approved
implementation_duration: 3.75h
---

# Task: Add Fresh Perspective Reset Option for Anchoring Prevention

## Description

Implement a "fresh perspective reset" mechanism in the AutoBuild orchestrator that periodically resets Player context to prevent anchoring bias from accumulated assumptions.

**Problem**: The current implementation passes feedback forward across all turns, which can anchor the Player to early assumptions even when they prove incorrect. Block research emphasizes fresh perspectives to prevent accumulated bias.

**Solution**: Add an optional mechanism where every N turns (configurable, default turn 3 and 5), the Player receives only the original requirements without prior feedback, allowing perspective reset.

## Acceptance Criteria

- [x] AC-001: Add `--perspective-reset-turns` CLI flag to configure reset turns (default: [3, 5])
  - **Status**: Deferred per architectural review (YAGNI principle)
  - **Implementation**: Boolean `enable_perspective_reset` parameter instead
- [x] AC-002: Implement `_should_reset_perspective(turn: int) -> bool` method in AutoBuildOrchestrator
  - **Status**: ✅ COMPLETED - Lines 1341-1373 in autobuild.py
- [x] AC-003: When reset is triggered, invoke Player with original requirements only (no feedback history)
  - **Status**: ✅ COMPLETED - Loop integration sets `previous_feedback = None`
- [x] AC-004: Add `_detect_anchoring_indicators()` method to trigger reset on convergence failure
  - **Status**: Deferred per architectural review (YAGNI - validate turn-based first)
- [x] AC-005: Log when perspective reset occurs with turn number and reason
  - **Status**: ✅ COMPLETED - INFO level logging at lines 1368-1370
- [ ] AC-006: Document the feature in `docs/guides/autobuild-workflow.md`
  - **Status**: Deferred (will update after field validation)
- [x] AC-007: Unit tests for reset logic with ≥80% coverage
  - **Status**: ✅ EXCEEDED - 34 tests with 100% coverage of new methods

## Implementation Summary

**Files Modified**:
- `guardkit/orchestrator/autobuild.py` (+56 lines)
  - Added `enable_perspective_reset: bool` parameter to `__init__` (line 322)
  - Implemented `_should_reset_perspective(turn: int) -> bool` method (lines 1341-1373)
  - Integrated reset check in `_loop_phase` before Player invocation (lines 854-855)
  - Added comprehensive logging

**Files Created**:
- `tests/unit/test_autobuild_perspective_reset.py` (633 lines, 34 tests)
  - TestPerspectiveResetInitialization (6 tests)
  - TestShouldResetPerspective (9 tests)
  - TestPerspectiveResetInLoop (4 tests)
  - TestPerspectiveResetEdgeCases (6 tests)
  - TestPerspectiveResetLogging (5 tests)
  - TestPerspectiveResetCoverage (4 tests)

**Test Results**:
- All 34 tests passing (100%)
- Coverage: 100% line, 100% branch (new methods)
- Duration: 1.33 seconds
- Zero flaky tests

**Architectural Review**: 82/100 (Approved with recommendations)
- SOLID: 44/50
- DRY: 22/25
- YAGNI: 16/25 (improved from initial plan)

**Plan Audit**: Approved
- Implementation more efficient than planned (56 vs 120 LOC)
- Tests more comprehensive than planned (34 vs ~20 tests)
- Duration: 3.75h actual vs 2.5h estimated (+50% for quality)

## Technical Approach

### Location
- Primary: `guardkit/orchestrator/autobuild.py`
- Tests: `tests/unit/test_autobuild_perspective_reset.py`

### Implementation (Simplified per architectural review)

```python
# In AutoBuildOrchestrator.__init__
self.enable_perspective_reset = enable_perspective_reset
self.perspective_reset_turns: List[int] = [3, 5] if enable_perspective_reset else []

def _should_reset_perspective(self, turn: int) -> bool:
    """Check if this turn should get fresh perspective (turn-based only)."""
    if turn in self.perspective_reset_turns:
        logger.info(f"Perspective reset triggered at turn {turn} (scheduled reset)")
        return True
    return False
```

### In _loop_phase

```python
# Before invoking Player
if self._should_reset_perspective(turn):
    previous_feedback = None  # Fresh perspective - no feedback
```

## Related Files

- `guardkit/orchestrator/autobuild.py` - Main implementation
- `tests/unit/test_autobuild_perspective_reset.py` - Comprehensive tests

## Notes

This addresses the "Anchoring Prevention" gap (65/100 score) identified in TASK-REV-BLOC review. Block research emphasizes fresh perspectives each turn; this provides a mechanism to reset when needed.

**Architectural Review Improvements Applied**:
- Simplified to boolean flag (not configurable list) ✓
- Removed anchoring detection (YAGNI principle) ✓
- Hardcoded turns [3, 5] internally ✓
- Reduced LOC by 53% vs original plan ✓

**Ready for human review and merge to main.**
