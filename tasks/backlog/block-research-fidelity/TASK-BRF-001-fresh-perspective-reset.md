---
id: TASK-BRF-001
title: Add Fresh Perspective Reset Option for Anchoring Prevention
status: backlog
task_type: implementation
created: 2026-01-24T16:30:00Z
updated: 2026-01-24T16:30:00Z
priority: high
tags: [autobuild, anchoring-prevention, block-research, orchestration]
complexity: 6
parent_review: TASK-REV-BLOC
feature_id: FEAT-BRF
wave: 1
implementation_mode: task-work
conductor_workspace: block-research-fidelity-wave1-1
dependencies: []
---

# Task: Add Fresh Perspective Reset Option for Anchoring Prevention

## Description

Implement a "fresh perspective reset" mechanism in the AutoBuild orchestrator that periodically resets Player context to prevent anchoring bias from accumulated assumptions.

**Problem**: The current implementation passes feedback forward across all turns, which can anchor the Player to early assumptions even when they prove incorrect. Block research emphasizes fresh perspectives to prevent accumulated bias.

**Solution**: Add an optional mechanism where every N turns (configurable, default turn 3 and 5), the Player receives only the original requirements without prior feedback, allowing perspective reset.

## Acceptance Criteria

- [ ] AC-001: Add `--perspective-reset-turns` CLI flag to configure reset turns (default: [3, 5])
- [ ] AC-002: Implement `_should_reset_perspective(turn: int) -> bool` method in AutoBuildOrchestrator
- [ ] AC-003: When reset is triggered, invoke Player with original requirements only (no feedback history)
- [ ] AC-004: Add `_detect_anchoring_indicators()` method to trigger reset on convergence failure
- [ ] AC-005: Log when perspective reset occurs with turn number and reason
- [ ] AC-006: Document the feature in `docs/guides/autobuild-workflow.md`
- [ ] AC-007: Unit tests for reset logic with ≥80% coverage

## Technical Approach

### Location
- Primary: `guardkit/orchestrator/autobuild.py`
- CLI: `guardkit/cli/autobuild.py`
- Tests: `tests/unit/test_autobuild_perspective_reset.py`

### Implementation

```python
# In AutoBuildOrchestrator.__init__
self.perspective_reset_turns: List[int] = perspective_reset_turns or [3, 5]

def _should_reset_perspective(self, turn: int) -> bool:
    """Check if this turn should get fresh perspective."""
    if turn in self.perspective_reset_turns:
        logger.info(f"Perspective reset triggered at turn {turn} (scheduled)")
        return True
    if self._detect_anchoring_indicators():
        logger.info(f"Perspective reset triggered at turn {turn} (anchoring detected)")
        return True
    return False

def _detect_anchoring_indicators(self) -> bool:
    """Detect signs of anchoring from turn history."""
    if len(self._turn_history) < 2:
        return False
    # Check for repeated similar feedback (sign of non-convergence)
    recent_feedback = [t.feedback for t in self._turn_history[-2:] if t.feedback]
    if len(recent_feedback) == 2:
        # Simple similarity check - could be more sophisticated
        common_words = set(recent_feedback[0].split()) & set(recent_feedback[1].split())
        similarity = len(common_words) / max(len(recent_feedback[0].split()), 1)
        return similarity > 0.7  # High feedback similarity indicates anchoring
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
- `guardkit/cli/autobuild.py` - CLI flag addition
- `docs/guides/autobuild-workflow.md` - Documentation

## Notes

This addresses the "Anchoring Prevention" gap (65/100 score) identified in TASK-REV-BLOC review. Block research emphasizes fresh perspectives each turn; this provides a mechanism to reset when needed.
