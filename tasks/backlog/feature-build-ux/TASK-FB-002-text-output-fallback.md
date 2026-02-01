---
id: TASK-FB-002
title: Implement Simple Text Output Fallback for Non-TTY
status: backlog
created: 2025-01-31T16:00:00Z
priority: high
tags: [feature-build, ux, progress, phase-1]
complexity: 4
implementation_mode: task-work
parent_review: TASK-REV-FBA1
feature_id: FEAT-FB-UX
wave: 1
dependencies: [TASK-FB-001]
---

# Task: Implement Simple Text Output Fallback for Non-TTY

## Context

When TTY is not available (Claude Code Bash tool context), Rich library spinners and progress bars don't render properly. We need a simple text-based output that provides meaningful progress without TTY features.

**Parent Review**: [TASK-REV-FBA1](.claude/reviews/TASK-REV-FBA1-review-report.md)

## Requirements

Modify `ProgressDisplay` methods to emit simple text when `is_tty=False`:

1. `start_turn()` - Print timestamped line instead of spinner
2. `update_turn()` - Print timestamped status line
3. `complete_turn()` - Print completion line with status icon (text)
4. `render_summary()` - Print simple text table (no box drawing)

## Acceptance Criteria

- [ ] When `is_tty=False`, `start_turn()` prints: `[HH:MM:SS] Turn N/M: Phase starting...`
- [ ] When `is_tty=False`, `update_turn()` prints: `[HH:MM:SS] Turn N/M: Message`
- [ ] When `is_tty=False`, `complete_turn()` prints: `[HH:MM:SS] Turn N/M: [OK] Summary` or `[FAIL] Summary`
- [ ] When `is_tty=False`, `render_summary()` prints simple text (no Rich tables)
- [ ] When `is_tty=True`, behavior unchanged (Rich library used)
- [ ] Existing tests pass
- [ ] New tests for non-TTY output added

## Implementation Notes

```python
def start_turn(self, turn: int, phase: str) -> None:
    if turn < 1 or turn > self.max_turns:
        raise ValueError(f"Invalid turn number: {turn} (max: {self.max_turns})")

    if self.is_tty:
        self._start_turn_impl(turn, phase)
    else:
        self._start_turn_text(turn, phase)

def _start_turn_text(self, turn: int, phase: str) -> None:
    """Text-based turn start for non-TTY contexts."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Turn {turn}/{self.max_turns}: {phase} starting...")
    self.current_turn = turn
    self.turn_history.append({
        "turn": turn,
        "phase": phase,
        "status": "in_progress",
        "started_at": datetime.now().isoformat(),
    })
```

## Example Non-TTY Output

```
[12:34:56] Turn 1/5: Player Implementation starting...
[12:35:30] Turn 1/5: Writing tests...
[12:36:45] Turn 1/5: [OK] 3 files created, 5 tests passing
[12:36:50] Turn 1/5: Coach Validation starting...
[12:37:15] Turn 1/5: [OK] Coach approved - ready for human review

== AutoBuild Summary ==
Turn 1: Player Implementation - OK - 3 files created, 5 tests passing
Turn 1: Coach Validation - OK - Coach approved
Status: APPROVED
Worktree: .guardkit/worktrees/TASK-XXX
```

## Files to Modify

- `guardkit/orchestrator/progress.py` - Add text fallback methods
- `tests/unit/test_progress.py` - Add non-TTY output tests

## Dependencies

- TASK-FB-001 (TTY detection)
