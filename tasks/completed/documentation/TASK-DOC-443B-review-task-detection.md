---
id: TASK-DOC-443B
title: Document review task detection in task-review.md
status: completed
created: 2025-11-27T02:00:00Z
updated: 2025-11-27T08:10:00Z
completed_at: 2025-11-27T08:10:00Z
priority: high
tags: [documentation, task-review, task-create, detection]
complexity: 2
related_to: [TASK-DOC-F3BA]
completion_metrics:
  implementation_commit: 7a92d13322c41f3a3d7d8ccf218e14bef0fa1523
  merge_commit: 9d9f64c4a69fc0846ea6966e805062983cd7029a
  worktree_branch: RichWoollcott/doc-review-detection
  lines_added: 103
  files_modified: 2
---

# Task: Document Review Task Detection in task-review.md

## Context

Review task TASK-DOC-F3BA identified that task-review.md doesn't explain how `/task-create` automatically detects review tasks and suggests using `/task-review` instead of `/task-work`.

This detection behavior is documented in task-create.md but not referenced in task-review.md, leaving users unaware that the system helps them choose the right command.

## Objective

Add documentation to task-review.md explaining the review task detection system, including detection criteria, suggestion behavior, and examples.

## Scope

### Files to Update

1. **installer/global/commands/task-review.md**:
   - Add new section "Automatic Review Task Detection"
   - Document detection criteria (task_type, decision_required, tags, keywords)
   - Show suggestion behavior with example output
   - Cross-reference to task-create.md

2. **installer/global/commands/task-create.md** (optional):
   - Add cross-reference to task-review.md detection section

## Acceptance Criteria

- [ ] New section "Automatic Review Task Detection" added to task-review.md
- [ ] Detection criteria documented (all four triggers)
- [ ] Suggestion behavior explained with example output
- [ ] Example task creation scenarios shown
- [ ] Cross-reference to task-create.md Review Task Detection section added
- [ ] Consistent formatting with existing sections
- [ ] Clear explanation of why detection is helpful

## Implementation Notes

**Suggested Content Structure**:

```markdown
## Automatic Review Task Detection

When creating tasks with `/task-create`, the system automatically detects review/analysis tasks and suggests using `/task-review` instead of `/task-work`.

### Detection Criteria

A task is detected as a review task if **any** of the following conditions are met:

1. **Explicit task_type field**: `task_type:review` parameter
2. **Decision required flag**: `decision_required:true` parameter
3. **Review-related tags**: `architecture-review`, `code-review`, `decision-point`, `assessment`
4. **Title keywords**: `review`, `analyze`, `evaluate`, `assess`, `audit`, `investigation`

### Suggestion Behavior

When a review task is detected during `/task-create`, you'll see:

```
=========================================================================
REVIEW TASK DETECTED
=========================================================================

Task: Review authentication architecture

This appears to be a review/analysis task.

Suggested workflow:
  1. Create task: /task-create (current command)
  2. Execute review: /task-review TASK-XXX
  3. (Optional) Implement findings: /task-work TASK-YYY

Note: /task-work is for implementation, /task-review is for analysis.
=========================================================================

Create task? [Y/n]:
```

**Important**: The suggestion is **informational only** and doesn't block task creation. You can still create the task and use `/task-work` if desired, though `/task-review` is recommended for analysis tasks.

### Detection Examples

**Example 1: Explicit task_type**
```bash
/task-create "Architectural review of authentication system" task_type:review
# ✅ Detected: Explicit task_type field
```

**Example 2: Decision required flag**
```bash
/task-create "Should we migrate to microservices?" decision_required:true
# ✅ Detected: Decision flag indicates review/analysis needed
```

**Example 3: Review tags**
```bash
/task-create "Code quality assessment" tags:[code-review,assessment]
# ✅ Detected: Tags indicate review task
```

**Example 4: Title keywords**
```bash
/task-create "Evaluate caching strategy options"
# ✅ Detected: "Evaluate" keyword in title
```

**Example 5: Not a review task**
```bash
/task-create "Implement user authentication"
# ❌ Not detected: Implementation task, no review indicators
# Suggestion not shown, proceeds normally
```

### Why Detection Helps

1. **Command Selection**: Helps you choose `/task-review` vs `/task-work`
2. **Workflow Efficiency**: Review tasks skip implementation phases
3. **Better Reports**: Review mode generates structured analysis reports
4. **Decision Support**: Review tasks include decision checkpoints ([A]ccept/[R]evise/[I]mplement/[C]ancel)

### Overriding Detection

If you want to use `/task-work` for a task that was detected as review:

```bash
# Task detected as review, but you want implementation workflow
/task-create "Review authentication architecture"
# [Suggestion shown]
# Choose Y to create task

# Use /task-work instead of /task-review
/task-work TASK-XXX
# Works fine, detection is only a suggestion
```

### See Also

- [task-create.md - Review Task Detection](./task-create.md#review-task-detection)
- [CLAUDE.md - Review Workflow](../../CLAUDE.md#review-workflow-analysisdecision-tasks)
- [Integration with /task-work](#integration-with-task-work) (this document)
```

**Placement**: Add this section after "Overview" and before "Examples"

**Cross-references to add**:
- Link to `task-create.md` Review Task Detection section
- Link to `CLAUDE.md` Review Workflow section

## Source

**Review Report**: [TASK-DOC-F3BA Review Report](../../../.claude/task-plans/TASK-DOC-F3BA-review-report.md)
**Priority**: P2 (High)
**Estimated Effort**: 1-2 hours

## Method

**Claude Code Direct** - Documentation update, no testing needed
