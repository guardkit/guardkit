---
task_id: TASK-FIX-7C3D
title: Add comprehensive file I/O error handling
status: BACKLOG
priority: HIGH
complexity: 3
created: 2025-11-20T21:20:00Z
updated: 2025-11-20T21:20:00Z
assignee: null
tags: [bug, phase-8, production-blocker, error-handling]
related_tasks: [TASK-PHASE-8-INCREMENTAL, TASK-FIX-4B2E]
estimated_duration: 4 hours
technologies: [python, file-io]
review_source: docs/reviews/phase-8-implementation-review.md
---

# Add Comprehensive File I/O Error Handling

## Problem Statement

Multiple file write operations in the template creation orchestrator lack error handling. Permission errors, disk full conditions, or I/O errors will crash the entire workflow instead of being handled gracefully.

**Review Finding** (Section 2, High Priority Issue #2):
> **Problem**: Permission errors, disk full, or I/O errors crash workflow
> **Locations**: Lines 849, 1012-1013
> **Impact**: Single file error kills entire template creation

## Current State

**Location**: `installer/global/commands/lib/template_create_orchestrator.py`

### Issue 1: Agent File Write (Line 849)
```python
agent_path.write_text(markdown_content, encoding='utf-8')
```

### Issue 2: Task File Write (Lines 1012-1013)
```python
task_file.write_text(task_content)
task_ids.append(task_id)
```

**Problems**:
- No try/except around file writes
- No handling of PermissionError
- No handling of OSError (disk full, etc.)
- Failure crashes entire orchestrator

## Acceptance Criteria

### 1. Agent File Error Handling
- [ ] Wrap agent file writes in try/except
- [ ] Catch PermissionError and OSError
- [ ] Log error with file path and reason
- [ ] Return None or raise custom exception
- [ ] Don't crash workflow - continue with other agents

### 2. Task File Error Handling
- [ ] Wrap task file writes in try/except
- [ ] Catch PermissionError and OSError
- [ ] Log error with task ID and reason
- [ ] Skip task on failure, continue with others
- [ ] Report failed tasks in summary

### 3. Directory Creation Error Handling
- [ ] Wrap `mkdir()` calls in try/except
- [ ] Handle permission denied on parent directory
- [ ] Handle read-only filesystem
- [ ] Provide actionable error messages

### 4. Error Reporting
- [ ] User-friendly error messages
- [ ] Include file path in error
- [ ] Include reason (permission, disk full, etc.)
- [ ] Suggest remediation steps
- [ ] Aggregate errors in final summary

### 5. Graceful Degradation
- [ ] Single file failure doesn't stop workflow
- [ ] Collect all errors and report at end
- [ ] Exit code reflects partial failure (e.g., exit 1)
- [ ] User knows which operations succeeded/failed

## Technical Details

### Files to Modify

**1. `installer/global/commands/lib/template_create_orchestrator.py`**

### Recommended Implementation

#### Pattern 1: Agent File Write
```python
def _write_agent_file(self, agent_path: Path, markdown_content: str) -> bool:
    """Write agent file with error handling.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        agent_path.write_text(markdown_content, encoding='utf-8')
        logger.info(f"Created agent file: {agent_path}")
        return True
    except PermissionError:
        logger.error(f"Permission denied writing {agent_path}")
        return False
    except OSError as e:
        if e.errno == errno.ENOSPC:
            logger.error(f"Disk full - cannot write {agent_path}")
        else:
            logger.error(f"I/O error writing {agent_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error writing {agent_path}: {e}")
        return False
```

#### Pattern 2: Task File Write
```python
def _create_agent_enhancement_task(self, agent_name: str, ...) -> Optional[str]:
    """Creates individual task for agent enhancement.

    Returns:
        Optional[str]: Task ID if successful, None if failed
    """
    # ... build task content ...

    try:
        task_file.write_text(task_content)
        logger.info(f"Created task: {task_id}")
        return task_id
    except (PermissionError, OSError) as e:
        logger.error(f"Failed to create task {task_id}: {e}")
        return None
```

#### Pattern 3: Directory Creation
```python
def _ensure_directory_exists(self, directory: Path) -> bool:
    """Ensure directory exists, create if needed.

    Returns:
        bool: True if directory exists or was created, False otherwise
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return True
    except PermissionError:
        logger.error(f"Permission denied creating directory {directory}")
        logger.error("Please check directory permissions and try again")
        return False
    except OSError as e:
        logger.error(f"Cannot create directory {directory}: {e}")
        return False
```

#### Pattern 4: Error Summary
```python
def _print_task_summary(self, task_ids: List[Optional[str]], total_agents: int):
    """Print summary of task creation with error reporting."""
    successful = [tid for tid in task_ids if tid is not None]
    failed = total_agents - len(successful)

    if successful:
        print(f"\nCreated {len(successful)} enhancement tasks:")
        for task_id in successful:
            print(f"  - {task_id}")

    if failed > 0:
        print(f"\nWarning: {failed} tasks could not be created due to errors")
        print("Check logs for details")
```

### Error Types to Handle

1. **PermissionError**: Insufficient permissions
   - User-friendly: "Cannot write to {path} - permission denied"
   - Remediation: "Run with appropriate permissions or choose different directory"

2. **OSError (ENOSPC)**: Disk full
   - User-friendly: "Disk full - cannot write {path}"
   - Remediation: "Free up disk space and try again"

3. **OSError (EROFS)**: Read-only filesystem
   - User-friendly: "Cannot write to read-only filesystem"
   - Remediation: "Choose a writable location"

4. **OSError (other)**: Other I/O errors
   - User-friendly: "I/O error writing {path}: {error}"
   - Remediation: "Check filesystem and try again"

## Success Metrics

### Functional Tests
- [ ] Permission denied on agent file (logged, continues)
- [ ] Permission denied on task file (logged, continues)
- [ ] Permission denied on directory creation (fails gracefully)
- [ ] Disk full error (fails gracefully with clear message)
- [ ] Read-only filesystem (fails gracefully)

### Edge Cases
- [ ] Multiple file errors (all reported)
- [ ] Partial success (some files written, others failed)
- [ ] Directory creation after file write error
- [ ] Unicode in error messages

### Error Messages
- [ ] Messages are user-friendly (no raw exceptions)
- [ ] Include actionable remediation steps
- [ ] Include full file paths
- [ ] No sensitive information exposed

## Dependencies

**Related To**:
- TASK-FIX-4B2E (task creation workflow) - uses this error handling
- TASK-PHASE-8-INCREMENTAL (main implementation)

## Related Review Findings

**From**: `docs/reviews/phase-8-implementation-review.md`

- **Section 2**: Code Quality Review - High Priority Issue #2
- **Lines 849, 1012-1013**: Unhandled file write errors
- **Section 6.1**: Immediate Priority #3 (must fix)

## Estimated Effort

**Duration**: 4 hours

**Breakdown**:
- Implementation (2 hours): Add error handling to all file operations
- Testing (1.5 hours): Test all error scenarios
- Documentation (0.5 hours): Update docstrings

## Test Plan

### Unit Tests

```python
def test_write_agent_file_permission_error(tmp_path):
    """Test permission error handling."""
    agent_path = tmp_path / "readonly" / "agent.md"
    agent_path.parent.mkdir()
    agent_path.parent.chmod(0o444)  # Read-only

    result = orchestrator._write_agent_file(agent_path, "content")
    assert result is False
    assert "Permission denied" in caplog.text

def test_write_agent_file_disk_full(tmp_path, monkeypatch):
    """Test disk full error handling."""
    def mock_write_text(*args, **kwargs):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(Path, "write_text", mock_write_text)

    result = orchestrator._write_agent_file(tmp_path / "agent.md", "content")
    assert result is False
    assert "Disk full" in caplog.text

def test_task_creation_multiple_errors(tmp_path):
    """Test multiple task creation failures."""
    # Simulate 5 agents, 2 fail to write
    task_ids = orchestrator._create_tasks_for_agents(agents)

    assert len([t for t in task_ids if t]) == 3  # 3 succeeded
    assert len([t for t in task_ids if not t]) == 2  # 2 failed
    assert "Warning: 2 tasks could not be created" in output
```

### Integration Tests

```python
def test_template_create_with_readonly_directory(tmp_path):
    """Test template creation when tasks directory is read-only."""
    tasks_dir = tmp_path / "tasks" / "backlog"
    tasks_dir.mkdir(parents=True)
    tasks_dir.chmod(0o444)

    result = run_template_create(args=["--create-agent-tasks"])

    assert result.returncode == 1  # Partial failure
    assert "Permission denied" in result.stderr
    assert "Check logs for details" in result.stdout
```

## Notes

- **Priority**: HIGH - production blocker per review
- **Impact**: LOW - doesn't change functionality, improves reliability
- **Risk**: LOW - purely additive error handling
- **Urgency**: 15 minutes per review estimate, but 4 hours for comprehensive solution

## Implementation Strategy

1. **Start with agent file writes** (highest impact)
2. **Add task file writes** (related to TASK-FIX-4B2E)
3. **Add directory creation** (foundation for above)
4. **Add error summary reporting** (user experience)
5. **Write comprehensive tests** (validate all scenarios)
6. **Update documentation** (reflect error handling behavior)
