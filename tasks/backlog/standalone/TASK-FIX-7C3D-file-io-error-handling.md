---
task_id: TASK-FIX-7C3D
title: Add error handling for task file writes
status: BACKLOG
priority: LOW
complexity: 2
created: 2025-11-20T21:20:00Z
updated: 2025-11-21T00:00:00Z
assignee: null
tags: [bug, phase-8, error-handling]
related_tasks: [TASK-PHASE-8-INCREMENTAL, TASK-FIX-4B2E]
estimated_duration: 1 hour
technologies: [python, file-io]
review_source: docs/reviews/phase-8-implementation-review.md
---

# Add Error Handling for Task File Writes

## Problem Statement

Task file write operations in `_create_agent_enhancement_tasks()` lack error handling. Permission errors, disk full conditions, or I/O errors will cause task creation to fail silently or crash.

**Review Finding** (Section 2, High Priority Issue #2):
> **Problem**: Permission errors, disk full, or I/O errors crash workflow
> **Location**: Line 1016
> **Impact**: Task creation can fail without proper error reporting

**Note**: Agent file writes (line 849) already have error handling via try/except wrapper (lines 855-858). This task only addresses the remaining unhandled task file writes.

## Current State

**Location**: `installer/global/commands/lib/template_create_orchestrator.py`

### Issue: Task File Write (Line 1016)
```python
# Inside _create_agent_enhancement_tasks() method
task_file = tasks_backlog / f"{task_id}.md"
task_file.write_text(task_content)  # ❌ No error handling
task_ids.append(task_id)
```

**Problems**:
- No try/except around file write
- No handling of PermissionError
- No handling of OSError (disk full, etc.)
- Failure will crash the loop or cause silent failure

## Acceptance Criteria

### 1. Task File Error Handling
- [ ] Wrap task file writes in try/except block
- [ ] Catch PermissionError and OSError
- [ ] Log error with task ID and reason
- [ ] Skip task on failure, continue with others
- [ ] Return None for failed task (instead of task_id)

### 2. Error Reporting
- [ ] User-friendly error messages in logs
- [ ] Include file path in error
- [ ] Include reason (permission, disk full, etc.)
- [ ] Report failed tasks in summary (if any failed)

### 3. Graceful Degradation
- [ ] Single task file failure doesn't stop workflow
- [ ] User knows which tasks succeeded/failed
- [ ] Return list with None for failed tasks

## Technical Details

### File to Modify

**`installer/global/commands/lib/template_create_orchestrator.py`**
- Method: `_create_agent_enhancement_tasks()` (around line 950-1021)

### Recommended Implementation

```python
def _create_agent_enhancement_tasks(
    self,
    template_dir: Path,
    agent_files: List[Path]
) -> List[Optional[str]]:
    """
    Creates individual tasks for each agent requiring enhancement.

    Returns:
        List[Optional[str]]: Task IDs for successful creations, None for failures
    """
    import datetime
    from pathlib import Path as PathlibPath

    template_name = template_dir.name
    task_ids = []

    # Create tasks directory if it doesn't exist
    tasks_backlog = PathlibPath("tasks/backlog")
    tasks_backlog.mkdir(parents=True, exist_ok=True)

    for agent_file in agent_files:
        agent_name = agent_file.stem

        # Generate task ID
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        task_id = f"TASK-AGENT-{agent_name[:8].upper()}-{timestamp}"

        # Build task content
        task_content = f"""# {task_id}: Enhance {agent_name} agent for {template_name} template
...
"""

        # Write task file with error handling
        task_file = tasks_backlog / f"{task_id}.md"
        try:
            task_file.write_text(task_content)
            task_ids.append(task_id)
            logger.info(f"  ✓ Created {task_id} for {agent_name}")
        except PermissionError:
            logger.error(f"  ✗ Permission denied creating {task_id}: {task_file}")
            task_ids.append(None)
        except OSError as e:
            logger.error(f"  ✗ I/O error creating {task_id}: {e}")
            task_ids.append(None)
        except Exception as e:
            logger.error(f"  ✗ Unexpected error creating {task_id}: {e}")
            task_ids.append(None)

    # Report summary if there were failures
    failed_count = sum(1 for tid in task_ids if tid is None)
    if failed_count > 0:
        logger.warning(f"⚠️  {failed_count} task(s) could not be created due to errors")

    return task_ids
```

### Error Types to Handle

1. **PermissionError**: Insufficient permissions
   - Log: "Permission denied creating {task_id}: {path}"
   - Continue with remaining tasks

2. **OSError (ENOSPC)**: Disk full
   - Log: "I/O error creating {task_id}: No space left on device"
   - Continue with remaining tasks

3. **OSError (other)**: Other I/O errors
   - Log: "I/O error creating {task_id}: {error}"
   - Continue with remaining tasks

4. **Exception**: Unexpected errors
   - Log: "Unexpected error creating {task_id}: {error}"
   - Continue with remaining tasks

## Success Metrics

### Functional Tests
- [ ] Permission denied on task file (logged, continues)
- [ ] Disk full error (logged, continues)
- [ ] Multiple task creation with some failures (partial success)

### Error Messages
- [ ] Messages are user-friendly (no raw exceptions)
- [ ] Include task ID and file path
- [ ] Summary shows count of failed tasks

## Test Plan

### Unit Tests

```python
def test_task_creation_permission_error(tmp_path, monkeypatch):
    """Test permission error handling during task creation."""
    def mock_write_text(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "write_text", mock_write_text)

    task_ids = orchestrator._create_agent_enhancement_tasks(
        template_dir=tmp_path,
        agent_files=[tmp_path / "agent1.md", tmp_path / "agent2.md"]
    )

    # Should return None for failed tasks
    assert task_ids == [None, None]
    assert "Permission denied" in caplog.text

def test_task_creation_partial_failure(tmp_path):
    """Test multiple task creation with some failures."""
    # Create scenario where second write fails
    # Should get [task_id1, None, task_id3]
    pass

def test_task_creation_disk_full(tmp_path, monkeypatch):
    """Test disk full error handling."""
    def mock_write_text(*args, **kwargs):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(Path, "write_text", mock_write_text)

    task_ids = orchestrator._create_agent_enhancement_tasks(
        template_dir=tmp_path,
        agent_files=[tmp_path / "agent.md"]
    )

    assert task_ids == [None]
    assert "I/O error" in caplog.text
```

## Estimated Effort

**Duration**: 1 hour

**Breakdown**:
- Implementation (30 minutes): Add try/except and error handling
- Testing (20 minutes): Write unit tests
- Documentation (10 minutes): Update docstrings

## Notes

- **Priority**: LOW - Only affects optional task creation feature
- **Impact**: LOW - Task creation is a convenience feature, not critical to template creation
- **Risk**: LOW - Purely additive error handling
- **Related**: Agent file writes (line 849) already have error handling ✓

## Implementation Strategy

1. Add try/except wrapper around `task_file.write_text()`
2. Log specific error types (PermissionError, OSError)
3. Append None to task_ids list for failed tasks
4. Add summary warning if any tasks failed
5. Write unit tests for error scenarios
6. Update method docstring to document return value
