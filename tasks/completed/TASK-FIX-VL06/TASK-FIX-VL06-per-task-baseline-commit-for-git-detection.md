---
id: TASK-FIX-VL06
title: Record per-task baseline commit hash for accurate git detection
status: completed
created: 2026-02-26T13:00:00Z
updated: 2026-02-26T14:10:00Z
completed: 2026-02-26T14:10:00Z
completed_location: tasks/completed/TASK-FIX-VL06/
previous_state: in_review
state_transition_reason: "All acceptance criteria met, tests passing"
priority: low
tags: [autobuild, vllm, enhancement, git, parallel, race-condition]
complexity: 4
task_type: enhancement
parent_review: TASK-REV-8A94
feature_id: FEAT-VL01
wave: 3
implementation_mode: task-work
dependencies: [TASK-FIX-VL04]
---

# Task: Record per-task baseline commit hash for accurate git detection

## Description

In parallel wave execution, `_detect_git_changes()` runs `git diff HEAD` to find modified files. However, `HEAD` represents the state at the start of the wave, not the state at the start of each individual task. When Task A commits changes before Task B's git detection runs, Task B sees Task A's committed files as part of its own `HEAD` baseline — potentially causing incorrect file attribution.

**Root Cause**: All parallel tasks use the same `HEAD` reference, which moves as tasks commit. There's no per-task snapshot of the baseline state.

**Note**: This is a defence-in-depth improvement. TASK-FIX-VL04 (git threading lock) prevents interleaved git commands but doesn't address the moving `HEAD` problem across sequential git operations by different tasks.

## Requirements

Record a `baseline_commit` hash at the start of each task's execution, and use `git diff {baseline_commit}` instead of `git diff HEAD` in `_detect_git_changes()`.

## Acceptance Criteria

- Each task records `baseline_commit = git rev-parse HEAD` before SDK invocation
- `_detect_git_changes()` uses `git diff {baseline_commit}` instead of `git diff HEAD`
- Baseline commit is stored as an instance variable on the invoker or passed as parameter
- Parallel wave execution still works correctly
- Wave 1 (single task) behaviour unchanged
- Unit test verifies baseline commit prevents cross-task file attribution

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` (`_detect_git_changes()` and task execution entry point)

## Implementation Notes

```python
class AgentInvoker:
    def __init__(self, ...):
        ...
        self._baseline_commit: Optional[str] = None

    def _record_baseline(self) -> None:
        """Record git HEAD before task execution starts."""
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(self.worktree_path),
            capture_output=True, text=True
        )
        if result.returncode == 0:
            self._baseline_commit = result.stdout.strip()

    def _detect_git_changes(self) -> Dict[str, list]:
        with self._git_lock:
            diff_ref = self._baseline_commit or "HEAD"
            result = subprocess.run(
                ["git", "diff", "--name-only", diff_ref],
                cwd=str(self.worktree_path),
                capture_output=True, text=True
            )
            # ... existing logic ...
```
