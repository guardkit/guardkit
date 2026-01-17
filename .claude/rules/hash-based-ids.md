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

## PM Tool Integration

GuardKit automatically maps internal hash IDs to external sequential IDs:

**Internal ID**: `TASK-E01-b2c4`

**External IDs** (automatic):
- JIRA: `PROJ-456`
- Azure DevOps: `#1234`
- Linear: `TEAM-789`
- GitHub: `#234`

This mapping is:
- Automatic when tasks are exported
- Bidirectional (internal <-> external)
- Persistent across sessions
- Transparent to users

## For Developers

If you're implementing the hash-based ID system:
- **Implementation Guide**: [Implementation Tasks Summary](docs/research/implementation-tasks-summary.md) - Wave-based execution plan
- **Parallel Development**: [Conductor.build Workflow](docs/guides/hash-id-parallel-development.md) - 20-33% faster completion
- **PM Tool Integration**: [External ID Mapping](docs/guides/hash-id-pm-tools.md) - Integration patterns
- **Technical Details**: [Strategy Analysis](docs/research/task-id-strategy-analysis.md) - Architecture and design decisions
- **Decision Rationale**: [Decision Guide](docs/research/task-id-decision-guide.md) - Why hash-based IDs?

## FAQ

**Q: Why hash-based instead of sequential?**
A: Prevents duplicates in concurrent and distributed workflows. Critical for Conductor.build support and parallel development.

**Q: Will users hate typing TASK-a3f8?**
A: Users rarely type IDs manually. Shell completion, copy/paste, and IDE integration handle this automatically.

**Q: What about parallel development?**
A: Hash-based IDs enable safe concurrent task creation across multiple Conductor.build worktrees with zero collision risk.
