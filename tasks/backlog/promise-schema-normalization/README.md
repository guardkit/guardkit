# Promise Schema Normalization

## Problem

FEAT-M2P run 1 failed because the Claude Code SDK Player agent emitted completion promises using field names (`ac_id`, `description`, `status: "done"`) that don't match what the guardkit Coach validator expects (`criterion_id`, `criterion_text`, `status: "complete"`). This caused 0/14 criteria to be verified despite all work being correct (28 tests passing, all quality gates passed).

## Root Cause

Context attention degradation at the SDK turn ceiling. The completion promise format instructions are injected once at the start of the task-work session. TASK-M2P-003 was the first task to hit the SDK turn ceiling (102 turns, 327 messages), and the agent lost track of the exact field names, falling back to intuitive but incorrect ones. All previous tasks (27-53 turns) stayed well within the effective attention range.

## Solution

Three-layer fix:
1. **Tolerance** (P0): Normalize field names at the validator boundary
2. **Tolerance** (P0): Normalize status values via alias map
3. **Prevention** (P1): Reinforce format instructions near the turn ceiling

## Parent Review

`specialist-agent/docs/reviews/TASK-REV-D1AE-review-report.md`

## Subtasks

| Task | Priority | Wave | Description |
|------|----------|------|-------------|
| TASK-PSN-001 | P0 (critical) | 1 | Normalize field names: `ac_id` -> `criterion_id`, `description` -> `criterion_text` |
| TASK-PSN-002 | P0 (critical) | 1 | Normalize status values: `"done"` -> `"complete"` via alias map |
| TASK-PSN-003 | P1 (high) | 2 | Add format reinforcement near SDK turn ceiling |

## Execution Strategy

**Wave 1**: TASK-PSN-001 and TASK-PSN-002 in parallel (no dependencies, different files)
- After Wave 1: Resume FEAT-M2P via `guardkit autobuild feature FEAT-M2P --resume`

**Wave 2**: TASK-PSN-003 (depends on Wave 1, addresses root cause prevention)
