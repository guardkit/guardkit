---
id: TASK-WC-007
title: Update feature-plan.md with subagent invocation
status: completed
task_type: implementation
created: 2025-12-13T22:45:00Z
updated: 2025-12-13T23:15:00Z
completed: 2025-12-13T23:15:00Z
priority: high
tags: [clarification, feature-plan, command, wave-2]
complexity: 4
parent_feature: unified-clarification-subagent
parent_review: TASK-REV-CLQ3
wave: 2
implementation_mode: direct
conductor_workspace: unified-clarification-wave2-2
dependencies:
  - TASK-WC-005
supersedes:
  - TASK-WC-001
test_results:
  status: passed
  coverage: n/a
  last_run: 2025-12-13T23:15:00Z
completion_summary: |
  Successfully integrated two clarification touchpoints into feature-plan.md:
  - Context A (review_scope): Added at Step 2, before /task-review execution
  - Context B (implementation_prefs): Added at Step 5c, after [I]mplement choice
  Both contexts use the unified clarification-questioner agent and respect all flags.
  Step numbering updated throughout document. Feature structure generation now
  incorporates context_b preferences.
---

# Task: Update feature-plan.md with Subagent Invocation

## Description

Add two subagent invocations to the `/feature-plan` command:
1. **Context A** (review_scope): Before /task-review execution
2. **Context B** (implementation_prefs): At [I]mplement decision checkpoint

## File to Modify

`installer/core/commands/feature-plan.md`

## Changes Required

### 1. Add Context A Invocation (Before Review)

Insert after parsing feature description, before executing /task-create:

```markdown
### Step 2: Review Scope Clarification

**IF** --no-questions flag is NOT set:

**INVOKE** Task tool:
```
subagent_type: "clarification-questioner"
description: "Collect review scope clarifications"
prompt: "Execute clarification for feature planning.

CONTEXT TYPE: review_scope

FEATURE: {feature_description}
ESTIMATED COMPLEXITY: {estimated_complexity}/10

FLAGS:
  --no-questions: {flags.no_questions}
  --with-questions: {flags.with_questions}
  --defaults: {flags.defaults}
  --answers: {flags.answers}

Ask about:
1. Review focus (all/technical/architecture/performance/security)
2. Trade-off priority (speed/quality/cost/maintainability/balanced)
3. Any specific concerns to address

Return ClarificationContext with review preferences."
```

**WAIT** for agent completion

**STORE** context_a for /task-review execution

**ELSE**:
  **DISPLAY**: "Review scope clarification skipped (--no-questions)"
```

### 2. Update /task-review Invocation

Pass context_a to the review:

```markdown
### Step 4: Execute Task Review

**EXECUTE** /task-review {task_id} --mode=decision --depth=standard

**PASS** context_a to review analysis (via task frontmatter or inline)
```

### 3. Add Context B Invocation (At [I]mplement)

Insert after [I]mplement choice, before creating feature structure:

```markdown
### Step 6: Implementation Preferences (if [I]mplement chosen)

**IF** user chose [I]mplement:

  **IF** --no-questions flag is NOT set AND subtask_count >= 2:

  **INVOKE** Task tool:
  ```
  subagent_type: "clarification-questioner"
  description: "Collect implementation preferences"
  prompt: "Execute clarification for implementation.

  CONTEXT TYPE: implementation_prefs

  REVIEW FINDINGS:
    Recommendations: {review_recommendations}
    Options identified: {review_options}
    Subtask count: {subtask_count}

  FLAGS:
    --no-questions: {flags.no_questions}
    --with-questions: {flags.with_questions}
    --defaults: {flags.defaults}
    --answers: {flags.answers}

  Ask about:
  1. Approach selection (which recommendation to follow)
  2. Execution preference (parallel vs sequential, Conductor usage)
  3. Testing depth (TDD/standard/minimal)

  Return ClarificationContext with implementation preferences."
  ```

  **WAIT** for agent completion

  **USE** context_b for subtask creation

  **ELSE**:
    **USE** defaults for subtask creation
```

### 4. Update Feature Structure Creation

Use context_b in subtask generation:

```markdown
### Step 7: Create Feature Structure

**CREATE** feature folder at tasks/backlog/{feature_slug}/

**GENERATE** subtasks using:
- Review recommendations
- Context B preferences (approach, parallel execution, testing)

**IF** context_b.parallel_execution:
  Include Conductor workspace names in subtask files
```

## Acceptance Criteria

- [x] Context A invoked before /task-review execution (Step 2)
- [x] Context A decisions passed to /task-review (Step 3)
- [x] Context B invoked at [I]mplement decision (if 2+ subtasks) (Step 5c)
- [x] Context B decisions used in subtask creation (Step 6)
- [x] Both contexts use clarification-questioner agent
- [x] Skip conditions work (--no-questions flag)

## Testing

1. Run `/feature-plan "add authentication"` → Context A questions appear
2. Choose [I]mplement → Context B questions appear
3. Verify subtasks reflect Context B preferences
4. Run with --no-questions → both contexts skipped
