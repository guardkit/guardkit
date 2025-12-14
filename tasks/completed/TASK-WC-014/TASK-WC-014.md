---
id: TASK-WC-014
title: Fix CRITICAL EXECUTION INSTRUCTIONS section in feature-plan.md
status: completed
task_type: implementation
created: 2025-12-14T12:00:00Z
updated: 2025-12-14T19:30:00Z
completed: 2025-12-14T19:30:00Z
priority: critical
tags: [clarification, feature-plan, fix, documentation]
complexity: 3
parent_feature: unified-clarification-subagent
parent_review: TASK-REV-CLQ1E45
dependencies: []
wave: 5
implementation_mode: direct
completed_location: tasks/completed/TASK-WC-014/
---

# Task: Fix CRITICAL EXECUTION INSTRUCTIONS in feature-plan.md

## Problem

The `/feature-plan` command is not showing clarifying questions because the CRITICAL EXECUTION INSTRUCTIONS section (lines 1038-1096 in source, 620-678 in installed) does not include clarification steps.

TASK-WC-007 added clarification to the workflow documentation (Steps 2 and 5c) but did NOT update the CRITICAL section that Claude actually follows.

## Root Cause

The `feature-plan.md` file has two sections:
1. **Workflow Documentation** - Contains clarification-questioner invocations ✅
2. **CRITICAL EXECUTION INSTRUCTIONS** - Does NOT mention clarification ❌

Claude follows the CRITICAL section, not the workflow documentation.

## Files to Modify

1. `installer/core/commands/feature-plan.md` (source - lines 1040-1096)
2. After modification, re-copy to `~/.agentecflow/commands/feature-plan.md`

## Changes Required

### 1. Update Execution Steps (lines 1044-1057)

Replace:
```markdown
### Execution Steps

1. ✅ **Parse feature description** from command arguments
2. ✅ **Execute `/task-create`** with:
   - Title: "Plan: {description}"
   - Flags: `task_type:review priority:high`
3. ✅ **Capture task ID** from output (regex: `TASK-[A-Z0-9-]+`)
4. ✅ **Execute `/task-review`** with captured task ID:
   - Flags: `--mode=decision --depth=standard`
5. ✅ **Present decision checkpoint** (inherited from `/task-review`)
6. ✅ **Handle user decision**:
   - [A]ccept: Save review, show reference message
   - [R]evise: Re-run review with additional focus
   - [I]mplement: Create subfolder + subtasks + guide
   - [C]ancel: Move to cancelled state
```

With:
```markdown
### Execution Steps

1. ✅ **Parse feature description** from command arguments

2. ✅ **Context A: Review Scope Clarification** (IF --no-questions NOT set):

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

3. ✅ **Execute `/task-create`** with:
   - Title: "Plan: {description}"
   - Flags: `task_type:review priority:high`

4. ✅ **Capture task ID** from output (regex: `TASK-[A-Z0-9-]+`)

5. ✅ **Execute `/task-review`** with captured task ID:
   - Flags: `--mode=decision --depth=standard`
   - Pass context_a to review

6. ✅ **Present decision checkpoint** (inherited from `/task-review`)

7. ✅ **Handle user decision**:
   - [A]ccept: Save review, show reference message
   - [R]evise: Re-run review with additional focus
   - [I]mplement: **→ Go to step 8**
   - [C]ancel: Move to cancelled state

8. ✅ **Context B: Implementation Preferences** (IF [I]mplement AND subtasks >= 2):

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

9. ✅ **Create subfolder + subtasks + guide** using context_b preferences
```

### 2. Update Example Execution Trace (lines 1078-1094)

Replace:
```markdown
### Example Execution Trace

```
User: /feature-plan "implement dark mode"

Claude executes internally:
  1. /task-create "Plan: implement dark mode" task_type:review priority:high
     → Captures: TASK-REV-A3F2
  2. /task-review TASK-REV-A3F2 --mode=decision --depth=standard
     → Runs analysis, presents options
  3. User chooses: I
  4. Creates structure:
     - Feature folder
     - Subtasks
     - Implementation guide
  5. Shows completion summary
```
```

With:
```markdown
### Example Execution Trace

```
User: /feature-plan "implement dark mode"

Claude executes internally:
  1. Parse: feature_description = "implement dark mode"

  2. INVOKE Task(clarification-questioner, context_type=review_scope)
     → User answers: Focus=all, Priority=balanced
     → STORE context_a

  3. /task-create "Plan: implement dark mode" task_type:review priority:high
     → Captures: TASK-REV-A3F2

  4. /task-review TASK-REV-A3F2 --mode=decision --depth=standard
     → Runs analysis (uses context_a), presents options

  5. User chooses: I (Implement)

  6. INVOKE Task(clarification-questioner, context_type=implementation_prefs)
     → User answers: Approach=Option1, Parallel=yes, Testing=standard
     → USE context_b

  7. Creates structure (using context_b):
     - Feature folder
     - Subtasks with Conductor workspace names
     - Implementation guide

  8. Shows completion summary
```
```

## Acceptance Criteria

- [x] CRITICAL EXECUTION INSTRUCTIONS section includes Context A invocation (step 2)
- [x] CRITICAL EXECUTION INSTRUCTIONS section includes Context B invocation (step 8)
- [x] Example execution trace shows clarification steps
- [x] Source file updated in `installer/core/commands/feature-plan.md`
- [x] Installed file updated in `~/.agentecflow/commands/feature-plan.md`

## Verification Steps

1. Re-copy to installed location:
   ```bash
   cp installer/core/commands/feature-plan.md ~/.agentecflow/commands/
   ```

2. Test with ambiguous input:
   ```bash
   /feature-plan "lets build out the application infrastructure"
   ```

3. Expected: Context A questions appear before review

4. Choose [I]mplement at decision checkpoint

5. Expected: Context B questions appear before structure creation

6. Test with --no-questions:
   ```bash
   /feature-plan "add authentication" --no-questions
   ```

7. Expected: Skip directly to task creation, no questions

## Notes

- This is a documentation-only fix - no Python code changes needed
- The clarification-questioner agent is already installed and working
- The Task tool invocation syntax in workflow docs (Steps 2 and 5c) is correct
- We're just ensuring the CRITICAL section matches the workflow documentation
