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

## CI lint: orchestrator task-ID references must resolve

Orchestrator code (`guardkit/orchestrator/**/*.py`) routinely names task IDs
in comments, docstrings, and runtime-advice strings. Every such hardcoded
literal must correspond to a filed task under `tasks/` or a state dir under
`docs/state/`. This is enforced by
`tests/rules/test_no_dead_task_id_references.py`, which greps the orchestrator
tree for the TASK-ID pattern and asserts every match resolves to a file.

- **Scope**: `guardkit/orchestrator/**/*.py` only for the first pass. Broader
  scope (CLI, `guardkit/knowledge`, tests) can be a follow-up if valuable.
- **Placeholders skipped**: any ID containing `XXX`, `YYY`, `ZZZ`, or `NNN`;
  any ID body with no digits (e.g. `TASK-FIX`, `TASK-ID`). Use
  `TASK-XXX-YYYY` in docstring examples rather than a real-looking ID.
- **Seeded by**: TASK-FIX-7A0A, triggered by the forge-run-3 analysis
  (TASK-REV-F3D7) which surfaced a dead `TASK-FIX-7A08` reference hardcoded
  in two orchestrator modules before the task existed.
