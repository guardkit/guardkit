---
id: TASK-WC-006
title: Update task-work.md with subagent invocation
status: completed
task_type: implementation
created: 2025-12-13T22:45:00Z
updated: 2025-12-13T23:30:00Z
completed: 2025-12-13T23:30:00Z
priority: high
tags: [clarification, task-work, command, wave-2]
complexity: 3
parent_feature: unified-clarification-subagent
parent_review: TASK-REV-CLQ3
wave: 2
implementation_mode: direct
conductor_workspace: unified-clarification-wave2-1
dependencies:
  - TASK-WC-005
test_results:
  status: passed
  coverage: N/A (documentation update)
  last_run: 2025-12-13T23:30:00Z
completed_location: tasks/completed/TASK-WC-006/
organized_files:
  - TASK-WC-006.md
---

# Task: Update task-work.md with Subagent Invocation

## Description

Add Phase 1.6 subagent invocation to the `/task-work` command, invoking the `clarification-questioner` agent for implementation planning clarification.

## File to Modify

`installer/core/commands/task-work.md`

## Location in Workflow

Insert after Phase 1.5 (Load Task Context), before Phase 2 (Implementation Planning).

## Changes Required

### 1. Update Phase 1.6 Section

Replace the existing Phase 1.6 documentation/placeholder with actual subagent invocation:

```markdown
#### Phase 1.6: Clarifying Questions (Complexity-Gated)

**IF** --no-questions flag is set:
  **DISPLAY**: "Clarification skipped (--no-questions flag)"
  Skip to Phase 2

**ELSE IF** --implement-only flag is set:
  **DISPLAY**: "Clarification skipped (using saved design)"
  Skip to Phase 2

**ELSE**:

**INVOKE** Task tool:
```
subagent_type: "clarification-questioner"
description: "Collect implementation planning clarifications for TASK-XXX"
prompt: "Execute clarification for TASK-{task_id}.

CONTEXT TYPE: implementation_planning

TASK CONTEXT:
  Title: {task_context.title}
  Description: {task_context.description}
  Complexity: {task_context.complexity}/10
  Acceptance Criteria: {task_context.acceptance_criteria}
  Stack: {detected_stack}

FLAGS:
  --no-questions: {flags.no_questions}
  --with-questions: {flags.with_questions}
  --defaults: {flags.defaults}
  --answers: {flags.answers}

Execute clarification based on complexity gating:
- Complexity 1-2: Skip unless --with-questions
- Complexity 3-4: Quick mode (15s timeout)
- Complexity 5+: Full mode (blocking)

Return ClarificationContext with user decisions."
```

**WAIT** for agent completion

**STORE** clarification_context for Phase 2 prompt

**DISPLAY**:
```
Phase 1.6: Clarification complete
  Mode: {clarification_context.mode}
  Decisions: {clarification_context.answered_count}
  Defaults used: {len(clarification_context.assumed_defaults)}
```
```

### 2. Update Phase 2 Prompt

Modify Phase 2 planning prompt to include clarification context:

```markdown
{if clarification_context:}
CLARIFICATION CONTEXT (from Phase 1.6):
User provided the following clarifications:
{for decision in clarification_context.explicit_decisions:}
  - {decision.question_text}: {decision.answer_display}
{endfor}

Defaults applied (user did not override):
{for decision in clarification_context.assumed_defaults:}
  - {decision.question_text}: {decision.answer_display} (default)
{endfor}

Use these clarifications to inform your implementation plan.
{endif}
```

## Acceptance Criteria

- [x] Phase 1.6 invokes clarification-questioner agent
- [x] Context type is `implementation_planning`
- [x] All flags are passed to agent
- [x] Clarification context stored for Phase 2
- [x] Phase 2 prompt includes clarification decisions
- [x] Skip conditions work (--no-questions, --implement-only)

## Implementation Summary

Successfully updated `installer/core/commands/task-work.md` with:

1. **Phase 1.6 Subagent Invocation**: Replaced old workflow documentation with Task tool invocation calling the `clarification-questioner` agent
2. **Skip Conditions**: Added proper skip logic for `--no-questions` and `--implement-only` flags
3. **Phase 2 Integration**: Updated Phase 2 prompt to use `clarification_context` with separate sections for explicit decisions and assumed defaults
4. **Flag Passing**: All clarification flags are properly passed to the subagent
5. **Context Type**: Set to `implementation_planning` as specified

## Changes Made

- File: `installer/core/commands/task-work.md`
  - Updated Phase 1.6 workflow section with subagent invocation
  - Removed old integration code
  - Updated Phase 2 AGENT_CONTEXT to use clarification_context
  - Updated Phase 2 prompt to properly display clarification decisions

Commit: [799284d] Update task-work.md with Phase 1.6 subagent invocation
