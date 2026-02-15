---
id: TASK-ASF-008
title: Add dynamic SDK timeout based on implementation mode and complexity
task_type: feature
parent_review: TASK-REV-SFT1
feature_id: FEAT-ASF
wave: 4
implementation_mode: task-work
complexity: 3
dependencies:
  - TASK-ASF-007
priority: low
status: completed
completed: 2026-02-15T12:00:00Z
tags: [autobuild, stall-fix, R7, phase-4, timeout]
---

# Task: Add dynamic SDK timeout based on implementation mode and complexity

## Description

The current SDK timeout is a fixed 1800s for all tasks regardless of implementation mode or complexity. Task-work mode (which wraps a full Claude Code session with CLAUDE.md loading, skill expansion, and multi-phase workflow) requires significantly more time than direct mode. Additionally, higher complexity tasks naturally need more execution time.

This is the lowest-priority fix — for the immediate re-run, R1 (direct mode) eliminates the timeout issue for TASK-SFT-001. This fix prevents future timeouts for Wave 2+ tasks that must use task-work mode.

## Root Cause Addressed

- **F1**: SDK timeout insufficient for task-work mode sessions
- Future prevention for Wave 2 tasks (complexity 4-6) that require task-work mode

## Implementation

```python
# agent_invoker.py — in _invoke_task_work_implement() or invoke_player()
def _calculate_sdk_timeout(self, task: dict) -> int:
    """Calculate SDK timeout based on task characteristics."""
    base_timeout = self.sdk_timeout_seconds  # Default: 1800s

    mode = task.get("implementation_mode", "direct")
    complexity = task.get("complexity", 5)

    if mode == "task-work":
        # Task-work mode needs more time for session preamble + multi-phase
        mode_multiplier = 1.5
    else:
        mode_multiplier = 1.0

    # Scale by complexity (1-10)
    complexity_multiplier = 1.0 + (complexity / 10.0)  # 1.1x to 2.0x

    effective_timeout = int(base_timeout * mode_multiplier * complexity_multiplier)

    # Cap at task-level timeout minus buffer
    max_timeout = self._task_timeout - 300  # Leave 5 min for cleanup
    effective_timeout = min(effective_timeout, max_timeout)

    logger.info(
        f"SDK timeout: {effective_timeout}s "
        f"(base={base_timeout}s, mode={mode} x{mode_multiplier}, "
        f"complexity={complexity} x{complexity_multiplier:.1f})"
    )

    return effective_timeout
```

## Files to Modify

1. `guardkit/orchestrator/agent_invoker.py` — Add `_calculate_sdk_timeout()` method (~line 2524)
2. `guardkit/orchestrator/agent_invoker.py` — Use calculated timeout in `_invoke_task_work_implement()` (~line 2536)

## Acceptance Criteria

- [x] SDK timeout calculated from implementation_mode and complexity
- [x] Task-work mode gets 1.5x base timeout
- [x] Complexity scales timeout from 1.1x (complexity=1) to 2.0x (complexity=10)
- [x] Timeout capped at MAX_SDK_TIMEOUT (3600s)
- [x] Timeout calculation logged for observability
- [x] Direct mode timeout unchanged (1.0x multiplier)
- [x] CLI `--sdk-timeout` flag still works as override

## Regression Risk

**Low** — This is a parameter calculation change. The timeout mechanism (`asyncio.timeout()`) is unchanged. The only risk is timeouts becoming too long, which could delay stall detection. The cap at `task_timeout - 300s` prevents this.

## Reference

- Review report: `.claude/reviews/TASK-REV-SFT1-review-report.md` (Finding 1, Recommendation R7)
- Diagnostic diagrams: `docs/reviews/feature-build/autobuild-diagnostic-diagrams.md` (Diagram 8)
