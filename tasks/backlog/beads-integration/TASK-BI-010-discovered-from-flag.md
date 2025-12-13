---
id: TASK-BI-010
title: Implement --discovered-from flag in /task-create
status: backlog
priority: high
type: task
parent_id: beads-integration
blocking_ids: [TASK-BI-003]
labels: [beads, agent-memory, critical]
created_at: 2025-12-13
complexity: 5
methodology_mode: standard
---

# TASK-BI-010: Implement --discovered-from Flag in /task-create

## Problem Statement

During implementation work, agents frequently discover follow-up tasks, edge cases, or bugs. Currently, there's no way to preserve the **provenance** of where this discovered work came from.

**Without this:**
- Agent discovers bug during TASK-A work
- Creates TASK-B for the bug
- Next session: Agent has no context that TASK-B came from TASK-A
- Work origin is lost, reducing agent effectiveness

**With Beads' discovered-from dependency:**
- Agent creates TASK-B with `--discovered-from TASK-A`
- Beads records the relationship
- Future sessions: `bd show TASK-B` shows "Discovered from: TASK-A"
- Full context preservation across sessions

This is a **critical feature** for multi-session agent workflows.

## Acceptance Criteria

1. Add `--discovered-from TASK-ID` flag to `/task-create` command spec

2. When Beads backend is active:
   - Create task via `bd create`
   - Add discovered-from dependency via `bd dep add --discovered-from`

3. When Markdown backend is active:
   - Store `discovered_from: TASK-ID` in frontmatter
   - No dependency tracking (graceful degradation)

4. Validate that source task exists before creating dependency

5. Update `/task-create` command documentation

6. Add integration test for the workflow

## Technical Approach

### Command Spec Update

```markdown
# In installer/core/commands/task-create.md

## Flags

| Flag | Description |
|------|-------------|
| `--discovered-from TASK-ID` | Link new task to source task where it was discovered |

## Examples

```bash
# During /task-work TASK-A1B2, agent discovers edge case
/task-create "Fix authentication edge case" --discovered-from TASK-A1B2

# Creates task with provenance link
# Beads: bd-c3d4 discovered-from bd-a1b2
# Markdown: discovered_from: TASK-A1B2 in frontmatter
```
```

### Backend Implementation

```python
# In backends/beads.py

class BeadsBackend(TaskBackend):
    def create(self, task: TaskMetadata, discovered_from: str = None) -> TaskMetadata:
        """Create task with optional discovered-from link."""
        # Create the task
        result = self._run_bd(["create", task.title, "--json"])
        created_task = self._parse_task(result)

        # Add discovered-from dependency if specified
        if discovered_from:
            # Validate source exists
            source = self.get(discovered_from)
            if not source:
                raise ValueError(f"Source task {discovered_from} not found")

            self._run_bd([
                "dep", "add",
                created_task.id,
                "--discovered-from", discovered_from
            ])
            created_task.discovered_from = discovered_from

        return created_task
```

```python
# In backends/markdown.py

class MarkdownBackend(TaskBackend):
    def create(self, task: TaskMetadata, discovered_from: str = None) -> TaskMetadata:
        """Create task with optional discovered-from metadata."""
        if discovered_from:
            task.discovered_from = discovered_from
            # Note: No dependency graph in markdown, just metadata

        # Write task file with frontmatter including discovered_from
        self._write_task_file(task)
        return task
```

### TaskBackend Interface Update

```python
# In backends/base.py

class TaskBackend(ABC):
    @abstractmethod
    def create(
        self,
        task: TaskMetadata,
        discovered_from: Optional[str] = None
    ) -> TaskMetadata:
        """
        Create a new task.

        Args:
            task: Task metadata
            discovered_from: Optional ID of task where this was discovered

        Returns:
            Created task with ID assigned
        """
        pass
```

## User Story

```
As an AI coding agent
When I discover follow-up work during task implementation
I want to create a linked task with provenance
So that future sessions preserve the context of where work originated
```

## Dependencies

- **Depends on:** TASK-BI-003 (BeadsBackend implementation)
- **Depends on:** TASK-BI-009 (TaskMetadata with discovered_from field)
- **Blocks:** None

## Effort Estimate

- **Complexity:** 5/10
- **Effort:** 3-4 hours
- **Wave:** Wave 3 (after Beads backend complete)

## Testing

```python
# tests/backends/test_discovered_from.py

def test_beads_discovered_from(beads_backend):
    """Test discovered-from creates dependency in Beads."""
    # Create source task
    source = beads_backend.create(TaskMetadata(
        id="",
        title="Source task",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.HIGH
    ))

    # Create discovered task
    discovered = beads_backend.create(
        TaskMetadata(
            id="",
            title="Discovered edge case",
            status=TaskStatus.BACKLOG,
            priority=Priority.MEDIUM
        ),
        discovered_from=source.id
    )

    # Verify link
    assert discovered.discovered_from == source.id

    # Verify Beads dependency exists
    deps = beads_backend.get_dependencies(discovered.id)
    assert source.id in deps.discovered_from


def test_markdown_discovered_from_graceful(markdown_backend):
    """Test markdown backend stores metadata without dependency tracking."""
    source = markdown_backend.create(TaskMetadata(
        id="TASK-A1B2",
        title="Source task",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.HIGH
    ))

    discovered = markdown_backend.create(
        TaskMetadata(
            id="",
            title="Discovered edge case",
            status=TaskStatus.BACKLOG,
            priority=Priority.MEDIUM
        ),
        discovered_from=source.id
    )

    # Verify metadata stored
    assert discovered.discovered_from == source.id

    # Verify in frontmatter
    task_file = markdown_backend._get_task_path(discovered.id)
    content = task_file.read_text()
    assert "discovered_from: TASK-A1B2" in content
```

## References

- Review finding: G4 (Critical gap - `--discovered-from` missing)
- [TASK-REV-b8c3 Review Report](../../../.claude/reviews/TASK-REV-b8c3-review-report.md)
- [Beads discovered-from documentation](https://github.com/steveyegge/beads#dependencies)
