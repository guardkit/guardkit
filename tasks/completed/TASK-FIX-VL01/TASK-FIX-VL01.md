---
id: TASK-FIX-VL01
title: Path-hardened player report recovery (check worktree + repo root)
status: completed
created: 2026-02-26T13:00:00Z
updated: 2026-02-26T14:15:00Z
completed: 2026-02-26T14:15:00Z
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria met"
completed_location: tasks/completed/TASK-FIX-VL01/
priority: high
tags: [autobuild, vllm, bug-fix, player-report, path-recovery]
complexity: 2
task_type: bug-fix
parent_review: TASK-REV-8A94
feature_id: FEAT-VL01
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Path-hardened player report recovery

## Description

When the SDK agent writes `player_turn_N.json` to the **repo root** instead of the **worktree** path, the Fix 2 recovery code at `agent_invoker.py:1848` can't find the file. This causes 0% criteria verification.

**Root Cause**: The recovery code only checks `player_report_path` (constructed from the worktree path). When Qwen3/vLLM writes to the repo root, the file exists at a different location.

## Requirements

Modify the Fix 2 recovery block in `_create_player_report_from_task_work()` to search for the agent-written player report at **both** the worktree path and the repo root fallback path.

## Acceptance Criteria

- `_create_player_report_from_task_work()` checks worktree path first, then repo root fallback
- When player report found at repo root, completion_promises and requirements_addressed are recovered
- Existing behaviour unchanged when player report is at the correct worktree path
- Log message indicates which path the report was recovered from
- Unit test covers repo-root fallback scenario

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` (lines 1844-1879, Fix 2 block)

## Implementation Notes

```python
# Current (line 1848):
if not report.get("completion_promises") and player_report_path.exists():

# Proposed:
candidate_paths = [player_report_path]
if self.worktree_path and self.repo_root:
    repo_root_fallback = self.repo_root / ".guardkit" / "autobuild" / task_id / f"player_turn_{turn}.json"
    if repo_root_fallback != player_report_path:
        candidate_paths.append(repo_root_fallback)

for candidate in candidate_paths:
    if not report.get("completion_promises") and candidate.exists():
        # existing recovery logic, using candidate instead of player_report_path
        ...
        if candidate != player_report_path:
            logger.warning(f"Recovered player report from repo root fallback: {candidate}")
        break
```
