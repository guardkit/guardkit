# FEAT-ASPF: AutoBuild Synthetic Pipeline Fix

**Source**: TASK-REV-953F (Analyse logging_feature_2 autobuild failure for regressions from DMCP fixes)
**Status**: Ready for implementation
**Priority**: Critical

## Problem

AutoBuild runs on GB10 (vLLM backend) fail because the criteria verification pipeline breaks when the Player doesn't write a structured report. Two distinct root causes:

1. **vLLM Player token exhaustion**: The Player exhausts tokens/turns before writing `player_turn_N.json`, triggering the synthetic fallback path which has limited verification capability
2. **State recovery gap**: After Player failure + state recovery, the recovered synthetic data stays in memory only — the Coach reads the stale ERROR-flagged `task_work_results.json` from disk and short-circuits without evaluating criteria

These issues don't affect MacBook builds (Anthropic API) because the Player reliably writes structured reports there.

## Root Cause Architecture

```
MacBook (working):  Player → writes report → Coach reads report → APPROVE
GB10 (failing):     Player → NO report → synthetic fallback → limited verify → FEEDBACK
                    Player → timeout → ERROR on disk → state recovery (memory only) → Coach reads ERROR → SHORT-CIRCUIT
```

## Relationship to DMCP Fixes

The four DMCP fixes (TASK-FIX-DMCP-001 through 004) correctly fix the data pipeline when the Player DOES write a report. They introduce no regressions. This feature addresses the separate scenario where the Player DOESN'T write a report.

**DMCP fixes must be committed first (TASK-FIX-ASPF-001).**

## Tasks

| Task | Wave | Description | Complexity | Mode |
|------|------|-------------|-----------|------|
| TASK-FIX-ASPF-001 | 1 | Commit DMCP fixes | 1 | direct |
| TASK-FIX-ASPF-002 | 1 | State recovery writes task_work_results.json to disk | 3 | task-work |
| TASK-FIX-ASPF-003 | 1 | Fix misleading "not found" log message | 1 | direct |
| TASK-FIX-ASPF-007 | 1 | Eliminate double-write of player_turn_N.json | 1 | direct |
| TASK-FIX-ASPF-004 | 2 | Cancel SDK subprocess on feature timeout | 5 | task-work |
| TASK-FIX-ASPF-005 | 2 | Increase SDK turn limit (50→100) and vLLM context (128K→256K) | 2 | direct |
| TASK-FIX-ASPF-006 | 3 | Enhance synthetic report requirements inference | 6 | task-work |

**TASK-FIX-ASPF-001 + TASK-FIX-ASPF-002 fix the state recovery gap. TASK-FIX-ASPF-005 fixes the turn exhaustion root cause — if the Player has enough turns to write the report, the DMCP fixes handle the rest.**
