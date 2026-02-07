---
paths: tasks/**/*.md, guardkit/cli/**/*.py
---

# Hash-Based Task IDs

GuardKit uses hash-based task IDs to prevent duplicates and support concurrent creation.

## Format

- **Simple**: `TASK-{hash}` (e.g., `TASK-a3f8`)
- **With prefix**: `TASK-{prefix}-{hash}` (e.g., `TASK-E01-b2c4`, `TASK-FIX-a3f8`)
- **With subtask**: `TASK-{prefix}-{hash}.{number}` (e.g., `TASK-E01-b2c4.1`)

## Benefits

- **Zero duplicates** - Mathematically guaranteed unique IDs
- **Concurrent creation** - Safe for parallel development across worktrees
- **Conductor.build compatible** - No ID collisions in parallel workflows
- **PM tool integration** - Automatic mapping to JIRA, Azure DevOps, Linear, GitHub

## Common Prefixes

- `E{number}`: Epic-related tasks (E01, E02, E03)
- `DOC`: Documentation tasks
- `FIX`: Bug fixes
- `TEST`: Test-related tasks
- Custom prefixes: Any 2-4 uppercase alphanumeric characters

## Examples

```bash
# Simple hash-based ID
/task-create "Fix login bug"
# Created: TASK-a3f8

# With prefix
/task-create "Fix login bug" prefix:FIX
# Created: TASK-FIX-a3f8

# Epic-related task
/task-create "Implement user authentication" prefix:E01
# Created: TASK-E01-b2c4

# Subtask
/task-create "Add unit tests for auth" parent:TASK-E01-b2c4
# Created: TASK-E01-b2c4.1
```

PM tool integration (JIRA, Azure DevOps, Linear, GitHub) automatically maps hash IDs to external sequential IDs bidirectionally.
