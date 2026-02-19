---
id: TASK-FIX-4AB4
title: Strengthen autobuild protocol to make completion_promises mandatory
status: completed
created: 2026-02-18T22:45:00Z
updated: 2026-02-19T00:00:00Z
completed: 2026-02-19T00:00:00Z
priority: high
tags: [autobuild, protocol, completion-promises, player-agent]
complexity: 2
parent_review: TASK-REV-9745
related_tasks:
  - TASK-REV-9745   # Review that identified this gap
  - TASK-FIX-FFE2   # Companion fix: _find_task_file design_approved blind spot
---

# Fix: Strengthen `autobuild_execution_protocol.md` to Make `completion_promises` Mandatory

## Problem

The Player agent non-deterministically omits `completion_promises` from its `player_turn_N.json` report. When it does, all fallback mechanisms fail (see TASK-REV-9745 for full analysis), resulting in `UNRECOVERABLE_STALL` after 3 turns.

The current protocol (`guardkit/orchestrator/prompts/autobuild_execution_protocol.md`) instructs the agent to include `completion_promises` but does not make non-compliance hard to avoid. The field is buried in the schema, there is no self-check step, and there is no explicit warning about what happens if the field is empty.

## Fix

Modify `autobuild_execution_protocol.md` to:

1. **Front-load `completion_promises` as the first field** in the `player_turn_N.json` schema. Agents write fields roughly top-to-bottom; putting it first reduces the chance it is omitted due to context exhaustion or truncation.

2. **Add an explicit mandatory instruction** in the report-writing section:

   > **CRITICAL**: You MUST populate `completion_promises` with one entry per acceptance criterion listed in the task file. Do NOT leave this array empty. An empty `completion_promises` array causes the Coach to use text-based fallback matching, which always fails — the autobuild run will stall after 3 turns. If you cannot determine whether a criterion is met, include it with `"status": "uncertain"` and explain in `"evidence"`.

3. **Add a self-check step** at the end of the report-writing instruction:

   > Before writing your player report, verify: `completion_promises` has exactly one entry for each acceptance criterion ID (AC-001, AC-002, …). If any are missing, add them now before writing the file.

4. **Also add a diagnostic warning log** in `agent_invoker.py` when Fix 5 is invoked but `_find_task_file()` returns `None` (Recommendation 3 from TASK-REV-9745 — trivial addition alongside this task):

   ```python
   task_file = self._find_task_file(task_id)
   if task_file is None:
       logger.warning(
           f"Fix 5: _find_task_file returned None for {task_id} — "
           f"completion_promises fallback unavailable. "
           f"Check that task directories are correctly configured."
       )
   ```

## Acceptance Criteria

- [ ] `autobuild_execution_protocol.md`: `completion_promises` is the first or second field in the player report JSON schema
- [ ] `autobuild_execution_protocol.md`: Mandatory instruction present, explicitly stating that an empty array causes stall
- [ ] `autobuild_execution_protocol.md`: Self-check step present in the report-writing section
- [ ] `agent_invoker.py`: Warning log emitted when `_find_task_file()` returns `None` in the Fix 5 path
- [ ] No functional code changes to criteria-matching logic (protocol changes only + diagnostic log)

## Implementation Notes

- **Primary file**: `guardkit/orchestrator/prompts/autobuild_execution_protocol.md`
- **Secondary file**: `guardkit/orchestrator/agent_invoker.py` (diagnostic warning, ~line 1653)
- **Regression risk**: None — protocol text changes can only improve agent compliance; warning log is additive
- **Testing**: Not directly unit-testable (LLM behaviour). Manual verification: run a fresh autobuild of TASK-DB-001 and confirm `completion_promises` is written on turn 1.
- **Ordering**: Can be done in parallel with TASK-FIX-FFE2 (no code conflicts)

## Context

From TASK-REV-9745 analysis:

- The passing run succeeded because the agent happened to write `completion_promises` on turn 2 (25 SDK turns used)
- The failing run had 3 turns with 50, 42, and 18 SDK turns — the agent omitted promises in all three despite having ample turns on turns 2 and 3
- This confirms the omission is non-deterministic behaviour, not caused by turn exhaustion
- Stronger protocol instructions directly address the root non-determinism
