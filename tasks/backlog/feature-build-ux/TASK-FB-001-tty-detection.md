---
id: TASK-FB-001
title: Add TTY Detection to ProgressDisplay
status: backlog
created: 2025-01-31T16:00:00Z
priority: high
tags: [feature-build, ux, progress, phase-1]
complexity: 2
implementation_mode: direct
parent_review: TASK-REV-FBA1
feature_id: FEAT-FB-UX
wave: 1
---

# Task: Add TTY Detection to ProgressDisplay

## Context

When `/feature-build` runs via Claude Code Bash tool, there's no TTY available. The Rich library features (spinners, progress bars) require TTY and fail silently. We need to detect this and route to an appropriate fallback.

**Parent Review**: [TASK-REV-FBA1](.claude/reviews/TASK-REV-FBA1-review-report.md)

## Requirements

Add TTY detection to `ProgressDisplay` class in `guardkit/orchestrator/progress.py`:

1. Detect if stdout is a TTY at initialization
2. Store detection result as instance attribute
3. Expose method to check TTY status
4. Log TTY status at initialization

## Acceptance Criteria

- [ ] `ProgressDisplay.__init__` detects TTY status via `sys.stdout.isatty()`
- [ ] Instance attribute `self.is_tty: bool` available
- [ ] Method `is_interactive() -> bool` returns TTY status
- [ ] INFO log message at init: "ProgressDisplay: TTY={True/False}"
- [ ] Existing tests pass
- [ ] Unit test for TTY detection added

## Implementation Notes

```python
# In ProgressDisplay.__init__
import sys

self.is_tty = sys.stdout.isatty()
logger.info(f"ProgressDisplay initialized: TTY={self.is_tty}, max_turns={max_turns}")

def is_interactive(self) -> bool:
    """Check if display is in interactive (TTY) mode."""
    return self.is_tty
```

## Files to Modify

- `guardkit/orchestrator/progress.py` - Add TTY detection
- `tests/unit/test_progress.py` - Add TTY detection tests

## Dependencies

None - this is foundational for Phase 1.
