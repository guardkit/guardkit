---
id: TASK-006
title: "Modify task-status.md - Remove Epic/Feature Filters"
created: 2025-10-27
status: backlog
priority: medium
complexity: 3
parent_task: none
subtasks: []
estimated_hours: 1.5
---

# TASK-006: Modify task-status.md - Remove Epic/Feature Filters

## Description

Simplify task-status.md by removing epic/feature/requirements filtering and visualization, keeping only task-focused kanban board and status views.

## Changes Required

### 1. Remove Filter Flags

**Remove**:
- `--epic EPIC-XXX`
- `--feature FEAT-XXX`
- `--requirements REQ-XXX`

**Keep**:
- `--status backlog|in_progress|in_review|blocked|completed`
- `--priority high|medium|low`
- `--complexity N`
- `--parent TASK-XXX` (for subtask filtering)

### 2. Remove View Types

**Remove views**:
- Epic rollup view
- Feature progress view
- Requirements traceability view
- PM tool sync status

**Keep views**:
- Kanban board (default)
- Task list view
- Complexity distribution
- Parent/subtask hierarchy

### 3. Simplify Output Format

**Remove columns from kanban board**:
- Epic
- Feature
- Requirements

**Keep columns**:
- Task ID
- Title
- Status
- Priority
- Complexity
- Parent Task (if applicable)

## Implementation Steps

### 1. Backup Current File

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.conductor/kuwait
cp installer/global/commands/task-status.md installer/global/commands/task-status.md.backup
```

### 2. Edit Filter Documentation

Remove documentation for:
- Epic filtering
- Feature filtering
- Requirements filtering
- PM tool sync status

### 3. Update Output Examples

Simplify kanban board examples to show only task-focused columns:

**Change FROM**:
```
| Task ID | Title | Epic | Feature | Status | Priority |
|---------|-------|------|---------|--------|----------|
| TASK-001| Auth  | EPIC-001 | FEAT-005 | in_progress | high |
```

**TO**:
```
| Task ID | Title | Status | Priority | Complexity |
|---------|-------|--------|----------|------------|
| TASK-001| Auth  | in_progress | high | 5 |
```

### 4. Remove View Types

Remove documentation and implementation for:
- `--view=epic-rollup`
- `--view=feature-progress`
- `--view=requirements-trace`

Keep:
- `--view=kanban` (default)
- `--view=list`
- `--view=complexity`
- `--view=hierarchy` (parent/subtask)

## Validation Checklist

### Filters
- [ ] --epic filter removed
- [ ] --feature filter removed
- [ ] --requirements filter removed
- [ ] Task-focused filters retained

### Views
- [ ] Epic rollup view removed
- [ ] Feature progress view removed
- [ ] Requirements trace view removed
- [ ] Kanban/list/complexity/hierarchy views retained

### Output Format
- [ ] Epic column removed from kanban
- [ ] Feature column removed from kanban
- [ ] Requirements column removed from kanban
- [ ] Task-focused columns retained

## Acceptance Criteria

- [ ] task-status.md modified
- [ ] No epic/feature/requirements filters
- [ ] No epic/feature/requirements views
- [ ] Simplified kanban board output
- [ ] Task-focused filtering retained
- [ ] Grep verification passes

## Testing

```bash
# Test basic status command
cd /tmp/test-project
/task-create "Test task 1"
/task-create "Test task 2" priority:high
/task-status

# Should show simple kanban without epic/feature columns

# Test filters
/task-status --status backlog
/task-status --priority high
/task-status --complexity 5

# Should NOT accept:
/task-status --epic EPIC-001  # Should error or warn
```

## Related Tasks

- TASK-002: Remove requirements management commands
- TASK-004: Modify task-create.md
- TASK-005: Modify task-work.md

## Estimated Time

1.5 hours

## Notes

- Simpler than task-work.md modifications
- Focus on output format simplification
- Keep hierarchy view for parent/subtask relationships
- Test output formatting after changes
