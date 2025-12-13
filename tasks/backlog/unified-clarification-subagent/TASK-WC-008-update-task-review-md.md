---
id: TASK-WC-008
title: Update task-review.md with subagent invocation
status: backlog
task_type: implementation
created: 2025-12-13T22:45:00Z
updated: 2025-12-13T22:45:00Z
priority: high
tags: [clarification, task-review, command, wave-2]
complexity: 3
parent_feature: unified-clarification-subagent
parent_review: TASK-REV-CLQ3
wave: 2
implementation_mode: direct
conductor_workspace: unified-clarification-wave2-3
dependencies:
  - TASK-WC-005
supersedes:
  - TASK-WC-002
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update task-review.md with Subagent Invocation

## Description

Add subagent invocation for Context A (review scope) to the `/task-review` command, invoking the `clarification-questioner` agent at the start of the review workflow.

## File to Modify

`installer/core/commands/task-review.md`

## Location in Workflow

Insert in Phase 1 (Load Review Context), after loading task but before executing review analysis.

## Changes Required

### 1. Update Phase 1 Section

Add clarification invocation to Phase 1:

```markdown
### Phase 1: Load Review Context (with Optional Clarification)

**READ** task file from: tasks/{state}/TASK-{id}-*.md

**PARSE** task metadata:
- Task ID: {task_id}
- Title: {task_title}
- Complexity: {task_complexity}
- Review mode: {review_mode} (from --mode flag or task frontmatter)

**IF** --no-questions flag is NOT set:

  **INVOKE** Task tool:
  ```
  subagent_type: "clarification-questioner"
  description: "Collect review scope clarifications for TASK-XXX"
  prompt: "Execute clarification for task review.

  CONTEXT TYPE: review_scope

  TASK CONTEXT:
    Task ID: {task_id}
    Title: {task_title}
    Description: {task_description}
    Review Mode: {review_mode}
    Complexity: {task_complexity}/10

  FLAGS:
    --no-questions: {flags.no_questions}
    --with-questions: {flags.with_questions}
    --defaults: {flags.defaults}
    --answers: {flags.answers}

  Ask about:
  1. Review focus (all/technical/architecture/performance/security)
  2. Analysis depth (quick/standard/deep)
  3. Trade-off priority (speed/quality/cost/maintainability/balanced)

  Apply complexity gating:
  - Complexity 0-3: Skip unless --with-questions
  - Complexity 4-6 + decision mode: Ask
  - Complexity 7+: Always ask

  Return ClarificationContext with review preferences."
  ```

  **WAIT** for agent completion

  **STORE** clarification_context for review analysis

  **DISPLAY**:
  ```
  Phase 1: Review context loaded
    Clarification mode: {clarification_context.mode}
    Focus: {clarification_context.get_decision('focus', 'all')}
    Depth: {clarification_context.get_decision('depth', 'standard')}
  ```

**ELSE**:
  **DISPLAY**: "Review scope clarification skipped (--no-questions)"
  **SET** clarification_context = None
```

### 2. Update Phase 2 (Review Analysis)

Pass clarification to review agents:

```markdown
### Phase 2: Execute Review Analysis

**INVOKE** appropriate review agent based on --mode flag:

{if clarification_context:}
REVIEW SCOPE (from clarification):
  Focus: {clarification_context.get_decision('focus', 'all')}
  Depth: {clarification_context.get_decision('depth', 'standard')}
  Trade-off Priority: {clarification_context.get_decision('tradeoff', 'balanced')}
  Specific Concerns: {clarification_context.get_decision('concerns', 'none')}

Prioritize analysis based on these preferences.
{endif}
```

### 3. Update Complexity Gating Documentation

Update the clarification integration section to reflect subagent pattern:

```markdown
## Clarification Integration

The `/task-review` command uses the `clarification-questioner` subagent to collect review scope preferences.

**Gating Rules**:
| Complexity | Review Mode | Behavior |
|------------|-------------|----------|
| 0-3 | Any | Skip (unless --with-questions) |
| 4-6 | decision, architectural | Ask |
| 4-6 | code-quality, technical-debt, security | Skip (unless --with-questions) |
| 7-10 | Any | Always ask (unless --no-questions) |

**Flags**:
- `--no-questions`: Skip clarification entirely
- `--with-questions`: Force clarification
- `--defaults`: Apply defaults without prompting
- `--answers="..."`: Inline answers for automation
```

## Acceptance Criteria

- [ ] Context A invoked at start of Phase 1
- [ ] Complexity gating rules respected
- [ ] Clarification context passed to review agents
- [ ] All flags work correctly
- [ ] Skip conditions work (--no-questions, low complexity)

## Testing

1. Run `/task-review TASK-XXX --mode=decision` with complexity 5+ → questions appear
2. Run `/task-review TASK-XXX --no-questions` → questions skipped
3. Run `/task-review TASK-XXX --mode=code-quality` with complexity 4 → questions skipped
4. Verify review analysis uses clarification preferences
