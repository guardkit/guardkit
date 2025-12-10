---
task_id: TASK-FIX-7C3D
title: Create shared file I/O error handling utility
status: COMPLETED
priority: MEDIUM
complexity: 4
created: 2025-11-20T21:20:00Z
updated: 2025-11-22T18:35:00Z
completed: 2025-11-22T18:35:00Z
assignee: null
tags: [standardization, error-handling, file-io, shared-utility]
related_tasks: [TASK-PHASE-8-INCREMENTAL, TASK-STND-773D, TASK-AGENT-VALIDATE, TASK-E359]
estimated_duration: 3.25 hours
actual_duration: 2.5 hours
technologies: [python, file-io]
review_source: docs/reviews/phase-8-implementation-review.md
completion_metrics:
  total_duration: 2.5 hours
  implementation_time: 1.5 hours
  testing_time: 0.5 hours
  review_time: 0.5 hours
  test_iterations: 1
  final_coverage: 100%
  acceptance_criteria_met: 6/6
  files_created: 2
  files_modified: 6
  tests_written: 17
  tests_passing: 55
---

# Create Shared File I/O Error Handling Utility

## Problem Statement

File I/O operations across multiple commands have **inconsistent error handling**. Only `agent_enhancement/applier.py` has proper try/except wrappers, while `agent-validate` and `template-create` have unprotected file operations.

**Current State Analysis** (2025-11-22):

✅ **agent-enhancement/applier.py** (Lines 42-54):
- Has try/except for PermissionError on read_text() and write_text()
- Good reference implementation

❌ **agent-validate** (validator.py line 78, agent-validate.py line 111):
- `agent_file.read_text()` - No error handling
- `output_file.write_text()` - No error handling

❌ **template_create_orchestrator.py** (Lines 850, 1050):
- `agent_path.write_text()` - No error handling
- `task_file.write_text()` - No error handling (original issue)

❌ **agent-format** (Lines 134, 210):
- agent-format.py line 134: `agent_path.write_text()` - No error handling
- agent_formatting/parser.py line 210: `file_path.read_text()` - No error handling

**Impact**: Permission errors, disk full, or I/O errors cause inconsistent behavior across commands.

## Objectives

**Primary**: Create reusable file I/O error handling utility module

**Secondary**: Apply consistent error handling across all commands

**Benefits**:
- Single source of truth for file I/O patterns
- Consistent error messages across all commands
- Easier testing (mock utility instead of each command)
- Future-proof (TASK-E359 can use immediately)

## Current State

### Commands Needing Consistent Error Handling

| File | Line | Operation | Error Handling |
|------|------|-----------|----------------|
| agent_enhancement/applier.py | 42-54 | read/write_text | ✅ Has it (reference) |
| agent_validator/validator.py | 78 | read_text | ❌ Missing |
| agent-validate.py | 111 | write_text | ❌ Missing |
| template_create_orchestrator.py | 850 | write_text | ❌ Missing |
| template_create_orchestrator.py | 1050 | write_text | ❌ Missing (original issue) |
| agent-format.py | 134 | write_text | ❌ Missing |
| agent_formatting/parser.py | 210 | read_text | ❌ Missing |

### Reference Implementation (applier.py)

```python
# Lines 42-45: Read with error handling
try:
    original_content = agent_file.read_text()
except PermissionError:
    raise PermissionError(f"Cannot read agent file: {agent_file}")

# Lines 51-54: Write with error handling
try:
    agent_file.write_text(new_content)
except PermissionError:
    raise PermissionError(f"Cannot write to agent file: {agent_file}")
```

## Acceptance Criteria

### AC1: Shared Utility Module

- [ ] **AC1.1**: Create `installer/core/lib/utils/file_io.py` module
- [ ] **AC1.2**: Implement `safe_read_file(path, encoding='utf-8')` function
- [ ] **AC1.3**: Implement `safe_write_file(path, content, encoding='utf-8')` function
- [ ] **AC1.4**: Both functions handle PermissionError, OSError, UnicodeError
- [ ] **AC1.5**: Functions return (success: bool, error_msg: Optional[str]) tuple
- [ ] **AC1.6**: Functions log errors with context (file path, operation)

### AC2: Apply to template_create_orchestrator.py

- [ ] **AC2.1**: Import file_io utility at top of file
- [ ] **AC2.2**: Replace line 850 write_text with safe_write_file
- [ ] **AC2.3**: Replace line 1050 write_text with safe_write_file
- [ ] **AC2.4**: Handle partial failures gracefully
- [ ] **AC2.5**: Log summary of successes/failures

### AC3: Apply to agent-validate

- [ ] **AC3.1**: Import file_io utility in validator.py
- [ ] **AC3.2**: Replace line 78 read_text with safe_read_file
- [ ] **AC3.3**: Import file_io utility in agent-validate.py
- [ ] **AC3.4**: Replace line 111 write_text with safe_write_file
- [ ] **AC3.5**: Exit with code 2 on file I/O errors

### AC3B: Apply to agent-format

- [ ] **AC3B.1**: Import file_io utility in agent-format.py
- [ ] **AC3B.2**: Replace line 134 write_text with safe_write_file
- [ ] **AC3B.3**: Import file_io utility in agent_formatting/parser.py
- [ ] **AC3B.4**: Replace line 210 read_text with safe_read_file
- [ ] **AC3B.5**: Handle errors gracefully in batch operations

### AC4: Refactor agent-enhancement/applier.py

- [ ] **AC4.1**: Import file_io utility
- [ ] **AC4.2**: Replace lines 42-45 with safe_read_file
- [ ] **AC4.3**: Replace lines 51-54 with safe_write_file
- [ ] **AC4.4**: Maintain existing error semantics (raise PermissionError)
- [ ] **AC4.5**: All existing tests still pass

### AC5: Testing

- [ ] **AC5.1**: Unit tests for safe_read_file (permission, not found, encoding errors)
- [ ] **AC5.2**: Unit tests for safe_write_file (permission, disk full, path issues)
- [ ] **AC5.3**: Integration test: template_create handles file errors
- [ ] **AC5.4**: Integration test: agent-validate handles file errors
- [ ] **AC5.5**: Integration test: agent-format handles file errors
- [ ] **AC5.6**: Integration test: agent-enhance still works with utility

### AC6: Documentation

- [ ] **AC6.1**: Docstrings for safe_read_file and safe_write_file
- [ ] **AC6.2**: Usage examples in module docstring
- [ ] **AC6.3**: Document error return format
- [ ] **AC6.4**: Add to CLAUDE.md development best practices

## Technical Design

### Shared Utility Module

**File**: `installer/core/lib/utils/file_io.py`

```python
"""
Shared file I/O utilities with consistent error handling.

Provides safe_read_file() and safe_write_file() functions that handle
common file I/O errors consistently across all commands.

Usage:
    from utils.file_io import safe_read_file, safe_write_file

    # Reading
    success, content = safe_read_file(path)
    if not success:
        logger.error(f"Failed to read: {content}")  # content is error msg
        return

    # Writing
    success, error_msg = safe_write_file(path, content)
    if not success:
        logger.error(f"Failed to write: {error_msg}")
        return
"""

from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def safe_read_file(
    file_path: Path,
    encoding: str = 'utf-8'
) -> Tuple[bool, str]:
    """
    Safely read file with comprehensive error handling.

    Args:
        file_path: Path to file
        encoding: Text encoding (default: utf-8)

    Returns:
        Tuple of (success: bool, content_or_error: str)
        - On success: (True, file_content)
        - On failure: (False, error_message)

    Errors Handled:
        - FileNotFoundError: File doesn't exist
        - PermissionError: No read permission
        - UnicodeDecodeError: Encoding issues
        - OSError: I/O errors (disk, network, etc.)
    """
    try:
        content = file_path.read_text(encoding=encoding)
        return (True, content)

    except FileNotFoundError:
        error_msg = f"File not found: {file_path}"
        logger.error(error_msg)
        return (False, error_msg)

    except PermissionError:
        error_msg = f"Permission denied reading {file_path}"
        logger.error(error_msg)
        return (False, error_msg)

    except UnicodeDecodeError as e:
        error_msg = f"Encoding error in {file_path}: {e}"
        logger.error(error_msg)
        return (False, error_msg)

    except OSError as e:
        error_msg = f"I/O error reading {file_path}: {e}"
        logger.error(error_msg)
        return (False, error_msg)

    except Exception as e:
        error_msg = f"Unexpected error reading {file_path}: {e}"
        logger.error(error_msg)
        return (False, error_msg)


def safe_write_file(
    file_path: Path,
    content: str,
    encoding: str = 'utf-8'
) -> Tuple[bool, Optional[str]]:
    """
    Safely write file with comprehensive error handling.

    Args:
        file_path: Path to file
        content: Content to write
        encoding: Text encoding (default: utf-8)

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
        - On success: (True, None)
        - On failure: (False, error_message)

    Errors Handled:
        - PermissionError: No write permission
        - OSError (ENOSPC): Disk full
        - OSError (ENAMETOOLONG): Path too long
        - UnicodeEncodeError: Encoding issues
        - OSError: Other I/O errors
    """
    try:
        file_path.write_text(content, encoding=encoding)
        return (True, None)

    except PermissionError:
        error_msg = f"Permission denied writing to {file_path}"
        logger.error(error_msg)
        return (False, error_msg)

    except UnicodeEncodeError as e:
        error_msg = f"Encoding error writing {file_path}: {e}"
        logger.error(error_msg)
        return (False, error_msg)

    except OSError as e:
        # Disk full, path too long, etc.
        error_msg = f"I/O error writing {file_path}: {e}"
        logger.error(error_msg)
        return (False, error_msg)

    except Exception as e:
        error_msg = f"Unexpected error writing {file_path}: {e}"
        logger.error(error_msg)
        return (False, error_msg)
```

### Updated template_create_orchestrator.py

```python
# At top of file
from lib.utils.file_io import safe_write_file

# Line 850 (agent file write)
success, error_msg = safe_write_file(agent_path, markdown_content)
if not success:
    logger.error(f"  ✗ Failed to write {agent_path.name}: {error_msg}")
    continue  # Skip this agent, continue with others
agent_paths.append(agent_path)

# Lines 1048-1053 (task file write)
task_file = tasks_backlog / f"{task_id}.md"
success, error_msg = safe_write_file(task_file, task_content)
if not success:
    logger.error(f"  ✗ Failed to create {task_id}: {error_msg}")
    failed_count += 1
    continue

task_ids.append(task_id)
logger.info(f"  ✓ Created {task_id} for {agent_name}")

# After loop
if failed_count > 0:
    logger.warning(f"⚠️  {failed_count} task(s) could not be created due to file errors")
```

### Updated agent-validate validator.py

```python
# At top of file
from utils.file_io import safe_read_file

# Line 77-78
def validate(self, agent_file: Path) -> ValidationReport:
    # Read file
    success, content = safe_read_file(agent_file)
    if not success:
        # content is error message
        raise ValueError(f"Cannot read agent file: {content}")

    # ... rest of validation
```

### Updated agent-validate.py

```python
# At top of file (add to imports)
from lib.utils.file_io import safe_write_file

# Lines 110-112
if args.output_file:
    success, error_msg = safe_write_file(args.output_file, output)
    if not success:
        print(f"Error writing report: {error_msg}", file=sys.stderr)
        sys.exit(2)
    print(f"Report written to: {args.output_file}")
```

### Updated agent-format.py

```python
# At top of file (add to imports)
from lib.utils.file_io import safe_write_file

# Line 134 (write formatted content)
# Write formatted content
success, error_msg = safe_write_file(agent_path, formatted_content)
if not success:
    return False, f'Failed to write formatted content: {error_msg}', validation

before_status = validation.metrics_before.get_status()
after_status = validation.metrics_after.get_status()

return True, f'{before_status} → {after_status}', validation
```

### Updated agent_formatting/parser.py

```python
# At top of file (add to imports)
from utils.file_io import safe_read_file

# Lines 209-210 (in parse_agent function)
# Read file content
success, content = safe_read_file(file_path)
if not success:
    # content is error message
    raise ValueError(f"Cannot read agent file: {content}")

# Parse components
frontmatter, frontmatter_end = extract_frontmatter(content)
# ... rest of parsing
```

## Implementation Plan

### Phase 1: Create Shared Utility (1 hour)

1. Create `installer/core/lib/utils/` directory
2. Create `__init__.py` in utils/
3. Implement `file_io.py` with safe_read_file and safe_write_file
4. Write comprehensive docstrings
5. Add module-level usage examples

### Phase 2: Unit Tests (45 minutes)

1. Create `tests/unit/lib/utils/test_file_io.py`
2. Test safe_read_file:
   - File not found
   - Permission denied
   - Unicode decode error
   - OSError (simulated)
   - Success case
3. Test safe_write_file:
   - Permission denied
   - Disk full (mocked)
   - Path too long (mocked)
   - Unicode encode error
   - Success case

### Phase 3: Apply to Commands (1 hour)

1. Update template_create_orchestrator.py (lines 850, 1050)
2. Update agent-validate validator.py (line 78)
3. Update agent-validate.py (line 111)
4. Update agent-format.py (line 134)
5. Update agent_formatting/parser.py (line 210)
6. Update agent-enhancement/applier.py (lines 42-54) - optional refactor

### Phase 4: Integration Tests (30 minutes)

1. Test template_create with file write errors
2. Test agent-validate with file read/write errors
3. Test agent-format with file read/write errors
4. Test agent-enhance still works
5. Verify consistent error messages across commands

**Total**: 3.25 hours

## Success Metrics

### Code Quality
- [ ] Single source of truth for file I/O error handling
- [ ] All commands use consistent error handling pattern
- [ ] Error messages are user-friendly and actionable

### Test Coverage
- [ ] 100% branch coverage for file_io.py utility
- [ ] Integration tests verify all commands handle errors
- [ ] No regressions in existing functionality

### Documentation
- [ ] Utility module has comprehensive docstrings
- [ ] Usage examples provided
- [ ] CLAUDE.md updated with file I/O best practices

## Testing Strategy

### Unit Tests (file_io.py)

```python
def test_safe_read_file_not_found(tmp_path):
    """Test file not found error."""
    missing_file = tmp_path / "missing.txt"
    success, msg = safe_read_file(missing_file)
    assert success is False
    assert "File not found" in msg

def test_safe_read_file_permission_denied(tmp_path, monkeypatch):
    """Test permission denied error."""
    file = tmp_path / "test.txt"
    file.write_text("content")

    def mock_read_text(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Path, "read_text", mock_read_text)
    success, msg = safe_read_file(file)
    assert success is False
    assert "Permission denied" in msg

def test_safe_write_file_disk_full(tmp_path, monkeypatch):
    """Test disk full error."""
    file = tmp_path / "test.txt"

    def mock_write_text(*args, **kwargs):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(Path, "write_text", mock_write_text)
    success, msg = safe_write_file(file, "content")
    assert success is False
    assert "I/O error" in msg
```

### Integration Tests

```python
def test_template_create_handles_write_errors(tmp_path, monkeypatch):
    """Test template-create handles agent file write errors gracefully."""
    # Mock safe_write_file to fail for second agent
    call_count = 0
    def mock_safe_write(path, content):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            return (False, "Permission denied")
        return (True, None)

    monkeypatch.setattr("file_io.safe_write_file", mock_safe_write)

    # Run template-create
    # Verify first agent created, second failed, third created
    # Verify summary shows partial success

def test_agent_validate_handles_read_error(tmp_path):
    """Test agent-validate handles file read errors."""
    missing_file = tmp_path / "missing.md"

    # Run agent-validate on missing file
    # Verify exit code 1
    # Verify error message is clear
```

## Migration Strategy

### Backward Compatibility

- All changes are **additive** (new utility module)
- Existing commands refactored to use utility
- No breaking changes to command interfaces
- All existing tests should pass

### Rollout Plan

1. **Implement utility** (Phase 1) - standalone, no impact
2. **Add tests** (Phase 2) - verify utility works
3. **Apply to template-create** (Phase 3a) - fix original issue
4. **Apply to agent-validate** (Phase 3b) - consistency
5. **Optionally refactor agent-enhance** (Phase 3c) - consistency

### Rollback Plan

If issues arise:
- Utility module is isolated (can be removed)
- Each command updated independently (can revert individually)
- Tests verify no regressions

## Future Work

After this task, the utility can be extended for:

1. **Atomic writes**: Add safe_atomic_write (write to temp, then rename)
3. **Backup support**: Add safe_write_with_backup (create .bak before write)
4. **Directory operations**: Add safe_mkdir, safe_rmdir

## Notes

### Priority Change

**Original**: LOW (1 hour, narrow fix)
**Updated**: MEDIUM (3 hours, comprehensive solution)

**Rationale**:
- TASK-STND-773D and TASK-AGENT-VALIDATE now implemented
- Both lack consistent error handling
- Shared utility benefits all commands
- Prevents future inconsistencies (TASK-E359 can use immediately)

### Related Tasks

- ✅ TASK-STND-773D: Completed (boundary sections)
- ✅ TASK-AGENT-VALIDATE: Completed (validation command) - needs utility
- ✅ TASK-E359: Completed (agent-format command) - needs utility
- ✅ TASK-PHASE-8-INCREMENTAL: Completed (agent-enhance) - can refactor to use utility

### Benefits

1. **Consistency**: All commands handle errors the same way
2. **Maintainability**: Single source of truth
3. **Testability**: Mock utility instead of individual commands
4. **Future-proof**: New commands can use immediately
5. **User Experience**: Consistent error messages

---

**Status**: BACKLOG
**Priority**: MEDIUM
**Estimated Effort**: 3.25 hours
**Complexity**: 4/10
**Ready for Implementation**: YES

**Updated**: 2025-11-22T16:30:00Z (added agent-format command to scope)
