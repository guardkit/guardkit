---
id: TASK-FW-001
title: Create /feature-plan command (markdown orchestration)
status: backlog
created: 2025-12-04T11:00:00Z
updated: 2025-12-04T11:00:00Z
priority: high
tags: [feature-workflow, command, quick-win]
complexity: 3
implementation_mode: direct
parallel_group: 1
conductor_workspace: feature-workflow-1
parent_review: TASK-REV-FW01
---

# Create /feature-plan Command

## Description

Create a new slash command `/feature-plan` that orchestrates the feature planning workflow in a single user-facing command.

**Key Insight**: Slash commands are markdown instruction files - no SDK required!

## Acceptance Criteria

- [ ] Create `installer/global/commands/feature-plan.md`
- [ ] Command accepts feature description as argument
- [ ] Automatically executes `/task-create` with `task_type:review` flag
- [ ] Captures task ID from output
- [ ] Automatically executes `/task-review` with `--mode=decision --depth=standard`
- [ ] Clear error handling if either step fails
- [ ] Documentation in command file

## Implementation Details

### Command File Structure

```markdown
# Feature Plan - Single Command Feature Planning

## Command Syntax
\`\`\`bash
/feature-plan "feature description"
\`\`\`

## Execution Flow

When user runs `/feature-plan "implement dark mode"`:

### Step 1: Create Review Task
Execute internally:
\`\`\`
/task-create "Plan: implement dark mode" task_type:review priority:high
\`\`\`

Capture the task ID from output (e.g., TASK-REV-XXXX).

### Step 2: Execute Review
Execute internally:
\`\`\`
/task-review TASK-REV-XXXX --mode=decision --depth=standard
\`\`\`

### Step 3: Present Findings
The review will present findings and decision options:
- [A]ccept
- [R]evise
- [I]mplement (enhanced - creates subfolder + subtasks + guide)
- [C]ancel

## Examples
...
```

## Files to Create/Modify

- `installer/global/commands/feature-plan.md` (NEW)

## Test Plan

1. Run `/feature-plan "test feature"`
2. Verify review task created with correct flags
3. Verify `/task-review` executes automatically
4. Verify decision checkpoint presented

## Notes

This is a **quick win** - provides single-command UX immediately!
Can be completed in 0.5 days.
