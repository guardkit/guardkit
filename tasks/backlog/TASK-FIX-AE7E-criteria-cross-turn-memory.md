---
id: TASK-FIX-AE7E
title: Add cross-turn criteria memory to prevent criteria verification stalls
status: backlog
task_type: implementation
created: 2026-02-18T16:00:00Z
updated: 2026-02-18T16:00:00Z
priority: high
tags: [autobuild, coach-validator, criteria-verification, stall-prevention]
complexity: 6
parent_review: TASK-REV-7EB05
feature_id: FEAT-REV7EB05-fixes
wave: 1
implementation_mode: task-work
related_tasks:
  - TASK-REV-7EB05
  - TASK-FIX-A7F1
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add cross-turn criteria memory to prevent criteria verification stalls

## Description

When the Player produces iterative fix turns (code changes only, no `completion_promises`), the Coach sees `requirements_met: []` and `completion_promises: (not used)` every turn, causing 0/6 criteria rejection each turn. Since the feedback is identical, the stall detector fires after 3 turns — even when the Player's work was correct from turn 1.

The root cause is that `task_work_results.json` is a **single-turn artifact**: the Player overwrites it fresh each turn, discarding any enrichment from prior turns. The Coach has no memory of previously verified criteria.

Two fixes required (implement both):

**Fix 1 (Quick fix — `_load_completion_promises`)**: When current turn's `task_work_results` has no `completion_promises`, fall back to reading the most recent existing `player_turn_N.json` for N < current turn. The Player's turn 1 report contained all 6 correct promises; they should be usable on subsequent turns.

**Fix 2 (Orchestrator fix — `autobuild.py`)**: Track which criteria have been verified across turns at the orchestrator level. When Coach gives feedback but some criteria were verified (even partially), those verified criteria should not be re-evaluated in subsequent turns — or at minimum, the previously-verified set should be preserved to break the identical-feedback stall.

**Source**: Finding F3 + F4 from TASK-REV-7EB05 review report.

## Acceptance Criteria

- [ ] When current turn's `task_work_results` has no `completion_promises`, `_load_completion_promises` falls back to reading the most recent prior `player_turn_N.json` and returns its promises
- [ ] Fallback is logged at INFO level: `"No completion_promises in current turn — recovered from player_turn_{N}.json"`
- [ ] If no prior player report exists, behaviour is unchanged (returns empty list, text fallback proceeds)
- [ ] Autobuild orchestrator accumulates verified criteria across turns — criteria verified in turn N remain verified in turn N+1 even if Coach gives feedback
- [ ] A stall where the Player's turn 1 output had all criteria met but subsequent turns omit promises does NOT trigger UNRECOVERABLE_STALL (criteria preserved from turn 1)
- [ ] Existing tests pass
- [ ] New tests cover: (a) fallback to prior player report, (b) criteria accumulation across feedback turns

## Implementation Notes

### Fix 1: `_load_completion_promises` in `coach_validator.py`

**Location**: [coach_validator.py:1537-1580](guardkit/orchestrator/quality_gates/coach_validator.py#L1537-L1580)

```python
def _load_completion_promises(self, task_work_results, turn):
    # ... existing logic checking task_work_results ...

    # NEW: if no promises found and turn > 1, check prior player reports
    if turn and turn > 1:
        for prev_turn in range(turn - 1, 0, -1):
            prev_path = (
                self.worktree_path
                / ".guardkit" / "autobuild" / self.task_id
                / f"player_turn_{prev_turn}.json"
            )
            if prev_path.exists():
                try:
                    agent_written = json.loads(prev_path.read_text())
                    promises = agent_written.get("completion_promises", [])
                    if promises:
                        logger.info(
                            "No completion_promises in current turn — "
                            "recovered from player_turn_%d.json (%d promises)",
                            prev_turn, len(promises)
                        )
                        return promises
                except (json.JSONDecodeError, IOError):
                    pass
    return []
```

Note: `self.task_id` is already available on the validator instance.

### Fix 2: Autobuild orchestrator criteria accumulation

**Location**: `guardkit/orchestrator/autobuild.py` — criteria progress tracking logic

The orchestrator already tracks criteria progress. When a turn's Coach decision is `feedback` but some criteria were individually verified, those verified criteria IDs should be stored in a persistent set and excluded from the "pending" pool on subsequent turns. The exact location depends on how `criteria_progress` is currently updated — trace from `autobuild.py` criteria-related code.

Minimum viable version: if a turn results in `feedback` but the criteria results from that turn include any `verified: True`, carry those forward to the next turn's context. This prevents the stall where 0 criteria pass not because they're wrong but because the matching data was lost.
