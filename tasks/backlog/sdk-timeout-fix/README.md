# SDK Timeout Fix

**Parent Review**: TASK-REV-A327
**Feature**: FEAT-E4F5 (System Architecture & Design Commands)
**Status**: Backlog

## Problem

FEAT-E4F5 run 1 failed because TASK-SAD-002 (complexity=3, the simplest task) timed out after 39 minutes despite completing all work successfully in ~8 minutes. This blocked all downstream waves, leaving 7/10 tasks unexecuted.

## Root Causes

Three bugs at three integration seams:

1. **SDK stream hang** (`agent_invoker.py`): Missing `break` after receiving `ResultMessage` causes the stream loop to hang if the CLI subprocess doesn't exit cleanly
2. **State recovery data loss** (`state_tracker.py`): Player report's test data (66 tests, 99% coverage) silently discarded when CoachVerifier re-run times out
3. **macOS cleanup disabled** (`agent_invoker.py`): Subprocess cleanup uses Linux-only `/proc` — no cleanup on macOS

## Solution

6 tasks across 3 parallel waves:

| Wave | Tasks | Priority | Impact |
|------|-------|----------|--------|
| 1 | FIX-1206 + FIX-01FC | P0 | Eliminates "completed-but-timed-out" failures |
| 2 | FIX-DFCB | P1 | Prevents zombie processes on macOS |
| 3 | FIX-F053 + FIX-8595 + FIX-F0E3 | P2/P3 | Improves recovery resilience |

## Tasks

- `TASK-FIX-1206` — Break after ResultMessage (P0, C=2)
- `TASK-FIX-01FC` — Player report test fallback (P0, C=2)
- `TASK-FIX-DFCB` — macOS subprocess cleanup (P1, C=4)
- `TASK-FIX-F053` — Increase recovery test timeout (P2, C=2)
- `TASK-FIX-8595` — Scope recovery tests (P2, C=3)
- `TASK-FIX-F0E3` — Add task_id to log (P3, C=1)
