---
id: TASK-004
title: "Modify task-create.md - Remove Epic/Feature Frontmatter"
created: 2025-10-27
status: backlog
priority: high
complexity: 3
parent_task: none
subtasks: []
estimated_hours: 1.5
---

# TASK-004: Modify task-create.md - Remove Epic/Feature Frontmatter

## Description

Simplify task-create.md by removing epic/feature/requirements frontmatter fields and related documentation, focusing on standalone task creation.

## Changes Required

### 1. Simplify Frontmatter Template

**Change FROM**:
```yaml
---
id: {TASK_ID}
title: "{title}"
created: {date}
status: backlog
priority: {priority}
complexity: 0
epic: {epic_id}
feature: {feature_id}
requirements: [{requirement_ids}]
parent_task: none
subtasks: []
---
```

**TO**:
```yaml
---
id: {TASK_ID}
title: "{title}"
created: {date}
status: backlog
priority: {priority}
complexity: 0
parent_task: none
subtasks: []
---
```

### 2. Remove Command Flags

**Remove**:
- `epic:EPIC-XXX`
- `feature:FEAT-XXX`
- `requirements:[REQ-001,REQ-002]`

**Keep**:
- `priority:high|medium|low`
- `--parent TASK-XXX` (for subtasks)

### 3. Remove Documentation Sections

Remove or simplify:
- Epic/feature linking instructions
- Requirements validation logic
- PM tool sync prompts
- Traceability documentation

### 4. Update Examples

**Change FROM**:
```bash
/task-create "Add user authentication" epic:EPIC-001 feature:FEAT-005 requirements:[REQ-012,REQ-013]
```

**TO**:
```bash
/task-create "Add user authentication"
/task-create "Add user authentication" priority:high
/task-create "Fix login bug" --parent TASK-042
```

## Implementation Steps

### 1. Backup Current File

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.conductor/kuwait
cp installer/global/commands/task-create.md installer/global/commands/task-create.md.backup
```

### 2. Edit task-create.md

Edit the file to:
- Remove epic/feature/requirements from frontmatter template
- Remove validation logic for epic/feature linking
- Remove documentation about requirements traceability
- Simplify usage examples

### 3. Verify No Requirements References

```bash
# Check for forbidden references
grep -i "epic\|feature.*link\|requirement.*trace\|ears\|bdd" \
  installer/global/commands/task-create.md | \
  grep -v "# Historical" | grep -v "# Related"

# Should return empty or only acceptable historical context
```

### 4. Test Command Syntax

Create a test to verify the command still works:
```bash
# The command should accept:
/task-create "Test task"
/task-create "Test task" priority:high
/task-create "Subtask" --parent TASK-001

# The command should NOT accept:
/task-create "Task" epic:EPIC-001  # Should warn or ignore
```

## Validation Checklist

- [ ] Frontmatter simplified (6 fields remaining)
- [ ] No epic/feature/requirements fields in template
- [ ] Command flags updated (removed epic/feature/requirements)
- [ ] Examples updated to show standalone task creation
- [ ] Documentation references removed
- [ ] Test scenarios pass
- [ ] File is clear and concise

## Acceptance Criteria

- [ ] task-create.md modified
- [ ] Frontmatter contains only: id, title, created, status, priority, complexity, parent_task, subtasks
- [ ] No references to epic/feature/requirements in active instructions
- [ ] Usage examples show simplified workflow
- [ ] Grep verification passes (no forbidden terms)

## Related Tasks

- TASK-002: Remove requirements management commands
- TASK-005: Modify task-work.md
- TASK-006: Modify task-status.md

## Estimated Time

1.5 hours

## Notes

- Keep historical context if useful (e.g., "This differs from full agentecflow-requirements")
- Focus on clarity and simplicity
- Ensure backward compatibility isn't broken for existing tasks
