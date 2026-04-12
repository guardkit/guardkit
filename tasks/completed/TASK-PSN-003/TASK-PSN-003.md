---
id: TASK-PSN-003
title: Add completion promise format reinforcement near SDK turn ceiling
task_type: enhancement
parent_review: TASK-REV-D1AE
feature_id: FEAT-PSN
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-PSN-001
- TASK-PSN-002
priority: high
status: completed
updated: "2026-04-12T00:00:00Z"
completed: "2026-04-12T00:00:00Z"
completed_location: tasks/completed/TASK-PSN-003/
tags: [autobuild, agent-invoker, prompt-engineering, P1]
---

# Task: Add completion promise format reinforcement near SDK turn ceiling

## Description

The root cause of the FEAT-M2P run 1 schema drift was context attention degradation: the completion promise format instructions are injected ONCE at the start of the task-work session (`agent_invoker.py:1690-1737`), and at 102 SDK turns (327 messages), the Claude agent lost track of the exact field names and fell back to intuitive but incorrect ones.

This task adds a format reinforcement mechanism that re-injects the completion promise schema reminder when the task-work session approaches the SDK turn ceiling.

## Root Cause Reference

- Review: `specialist-agent/docs/reviews/TASK-REV-D1AE-review-report.md` (Root Cause: WHY This Failed Now)
- Correlation: 5/5 tasks under 100 turns used correct schema; 1/1 task at 102 turns used wrong schema
- Format instructions at `agent_invoker.py:1728-1734` only stated once at conversation start

## Changes Required

### 1. Update: `guardkit/orchestrator/agent_invoker.py`

Add a turn-count check in the SDK invocation management that injects a reminder message when approaching the ceiling. The exact mechanism depends on how the agent_invoker monitors SDK turn count during execution:

**Option A (preferred): Post-hoc reinforcement via conversation injection**

If the agent_invoker can inject messages into the running SDK session at a turn threshold:

```python
PROMISE_FORMAT_REMINDER = """
REMINDER: Your completion_promises MUST use these exact field names:
- criterion_id: The acceptance criterion ID (e.g., "AC-001")
- criterion_text: The full criterion text
- status: "complete" or "incomplete" (NOT "done", NOT "finished")
- evidence: What you did to satisfy this criterion
- test_file: Path to test file (if applicable)
- implementation_files: List of files modified/created
"""

# When SDK turn count >= 80% of max_turns, inject reminder
if current_turn >= int(max_turns * 0.8):
    # Inject as user message before next SDK turn
    inject_message(PROMISE_FORMAT_REMINDER)
```

**Option B (fallback): Append to initial prompt**

If runtime injection is not possible, append the reminder as an additional emphasis block at the end of the initial prompt, with stronger formatting:

```python
# In _build_player_prompt(), add after the IMPORTANT block:
if len(acceptance_criteria) > 10:  # Complex tasks most at risk
    prompt += "\n\n⚠️ CRITICAL SCHEMA REQUIREMENT ⚠️\n"
    prompt += "Your completion_promises MUST use criterion_id (not ac_id), "
    prompt += 'criterion_text (not description), and status "complete" (not "done").\n'
```

### 2. Investigate SDK turn monitoring capability

Determine whether the Claude Code SDK exposes turn count during execution, or whether the agent_invoker can only observe it after completion. This determines whether Option A or Option B is feasible.

Check:
- `claude_agent_sdk` API for turn count callbacks or hooks
- `agent_invoker.py` existing turn monitoring (the log shows `[TASK-M2P-003] task-work implementation in progress... (1500s elapsed)` — there's already a polling mechanism)
- Whether the polling mechanism can inject messages

## Acceptance Criteria

- [ ] Format reinforcement is triggered for task-work sessions approaching SDK turn ceiling
- [ ] Reinforcement message includes exact field names: `criterion_id`, `criterion_text`, `status`
- [ ] Reinforcement message explicitly warns against common wrong values: `ac_id`, `description`, `"done"`
- [ ] Trigger threshold is configurable (default: 80% of max_turns)
- [ ] Complex tasks (>10 acceptance criteria) receive stronger emphasis
- [ ] No impact on short sessions (under threshold)
- [ ] Existing task-work invocation unchanged when under threshold
- [ ] All existing tests pass

## Implementation Notes

- The `agent_invoker.py` log at line ~480-498 shows 30-second interval progress polling. This polling mechanism may be the integration point for Option A.
- SDK turn count is visible in task_work_results.json after completion (`sdk_turns.turns_used`) but the question is whether it's observable during execution.
- If Option A is not feasible, Option B (stronger initial prompt for complex tasks) still provides value by making the format instructions more prominent in the context.
- This task depends on TASK-PSN-001 and TASK-PSN-002 because the defensive normalization should be in place first — reinforcement is prevention, normalization is tolerance.
