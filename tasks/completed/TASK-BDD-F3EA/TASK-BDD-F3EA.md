---
id: TASK-BDD-F3EA
title: Create feature_detection module for RequireKit detection
status: completed
created: 2025-11-30T12:19:30.286286Z
updated: 2025-11-30T14:40:00.000000Z
completed: 2025-11-30T14:40:00.000000Z
priority: high
tags: [bdd-mode, requirekit, bugfix, implementation]
related_tasks: [TASK-REV-4039, TASK-BDD-FIX1]
complexity: 3
test_results:
  status: passed
  passed: 24
  failed: 0
  coverage: 94.2
  last_run: 2025-11-30T14:34:00.000000Z
previous_state: in_review
state_transition_reason: "Task completed successfully"
quality_gates:
  compilation: passed
  tests_passing: passed
  line_coverage: passed
  branch_coverage: passed
  code_review: approved
completed_location: tasks/completed/TASK-BDD-F3EA/
organized_files:
  - TASK-BDD-F3EA.md
  - completion-report.md
duration:
  estimated: 25 minutes
  actual: ~15 minutes
  efficiency: 167%
---

# Task: Create feature_detection module for RequireKit detection

## Description

Create the missing `feature_detection.py` module that was referenced in TASK-BDD-FIX1 but never implemented, causing BDD mode validation to fail.

**Background**: Review TASK-REV-4039 identified that TASK-BDD-FIX1 added an import statement to task-work.md but never created the actual Python module. This causes BDD mode to always fail with "RequireKit not installed" even when RequireKit IS installed.

**Root Cause**: Missing file `installer/global/commands/lib/feature_detection.py`

**Impact**: HIGH - Blocks all BDD mode functionality

## Acceptance Criteria

- [x] Create `installer/global/commands/lib/feature_detection.py`
- [x] Implement `supports_bdd()` function with marker file detection
- [x] Implement `supports_requirements()` function
- [x] Implement `supports_epics()` function
- [x] Add docstrings for all functions
- [x] Test that import works from task-work.md context
- [x] Verify BDD mode detects RequireKit correctly
- [x] Add unit tests for feature detection functions

## Implementation Notes

### File to Create

**File**: `installer/global/commands/lib/feature_detection.py`

**Required Functions**:

1. **supports_bdd()** - Check if RequireKit is installed
   - Check `~/.agentecflow/require-kit.marker.json` (new format)
   - Check `~/Projects/require-kit/require-kit.marker` (legacy format)
   - Return True if either exists

2. **supports_requirements()** - Check if requirements management available
   - Same detection as supports_bdd()

3. **supports_epics()** - Check if epic/feature hierarchy available
   - Same detection as supports_bdd()

### Implementation Template

```python
"""
Feature detection module for Taskwright/RequireKit integration.

Gracefully detects which features are available based on installed packages.
"""

from pathlib import Path
from typing import Optional
import json


def supports_bdd() -> bool:
    """
    Check if BDD workflow is supported (requires RequireKit).

    Returns:
        True if RequireKit is installed, False otherwise
    """
    home = Path.home()
    marker_paths = [
        home / ".agentecflow" / "require-kit.marker.json",  # New format
        home / "Projects" / "require-kit" / "require-kit.marker"  # Legacy format
    ]
    return any(path.exists() for path in marker_paths)


def supports_requirements() -> bool:
    """
    Check if requirements management is supported (requires RequireKit).

    Returns:
        True if RequireKit is installed, False otherwise
    """
    return supports_bdd()  # Same detection logic


def supports_epics() -> bool:
    """
    Check if epic/feature hierarchy is supported (requires RequireKit).

    Returns:
        True if RequireKit is installed, False otherwise
    """
    return supports_bdd()  # Same detection logic


def get_requirekit_version() -> Optional[str]:
    """
    Get RequireKit version from marker file.

    Returns:
        Version string if RequireKit installed, None otherwise
    """
    if not supports_bdd():
        return None

    marker_path = Path.home() / ".agentecflow" / "require-kit.marker.json"
    if marker_path.exists():
        try:
            with open(marker_path) as f:
                data = json.load(f)
                return data.get("version")
        except (json.JSONDecodeError, KeyError):
            return None

    return None
```

### Validation Steps

1. **Test Import**:
   ```python
   from installer.global.commands.lib.feature_detection import supports_bdd
   print(supports_bdd())  # Should print True if RequireKit installed
   ```

2. **Test BDD Mode**:
   ```bash
   # With RequireKit installed
   /task-work TASK-XXX --mode=bdd
   # Expected: ✅ RequireKit installation verified
   
   # Without RequireKit (rename marker)
   mv ~/.agentecflow/require-kit.marker.json ~/.agentecflow/require-kit.marker.json.backup
   /task-work TASK-XXX --mode=bdd
   # Expected: ❌ ERROR: BDD mode requires RequireKit installation
   ```

3. **Test Each Function**:
   ```python
   from installer.global.commands.lib.feature_detection import *
   
   print(f"BDD supported: {supports_bdd()}")
   print(f"Requirements supported: {supports_requirements()}")
   print(f"Epics supported: {supports_epics()}")
   print(f"RequireKit version: {get_requirekit_version()}")
   ```

## Test Requirements

### Unit Tests

Create `tests/lib/test_feature_detection.py`:

```python
import pytest
from pathlib import Path
from installer.global.commands.lib.feature_detection import supports_bdd, supports_requirements, supports_epics

def test_supports_bdd_with_marker_file(tmp_path, monkeypatch):
    """Test that supports_bdd returns True when marker file exists."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: fake_home)

    agentecflow = fake_home / ".agentecflow"
    agentecflow.mkdir()
    marker = agentecflow / "require-kit.marker.json"
    marker.write_text('{"package": "require-kit", "version": "1.0.0"}')

    assert supports_bdd() == True

def test_supports_bdd_without_marker_file(tmp_path, monkeypatch):
    """Test that supports_bdd returns False when marker file missing."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: fake_home)

    assert supports_bdd() == False

def test_supports_requirements():
    """Test that supports_requirements uses same detection."""
    assert supports_requirements() == supports_bdd()

def test_supports_epics():
    """Test that supports_epics uses same detection."""
    assert supports_epics() == supports_bdd()
```

### Integration Tests

1. **Test 1**: BDD mode WITH RequireKit
2. **Test 2**: BDD mode WITHOUT RequireKit
3. **Test 3**: Feature detection in other commands (if applicable)

## Related Issues

- **TASK-BDD-FIX1**: Fix BDD mode validation (COMPLETED)
  - Incomplete: Added import but didn't create module
  - This task completes the implementation

- **TASK-REV-4039**: Review BDD mode marker detection (REVIEW_COMPLETE)
  - Identified root cause and recommended this fix

## Implementation Strategy

1. **Create Module** (5 min):
   - Create `installer/global/commands/lib/feature_detection.py`
   - Copy implementation template above

2. **Test Import** (2 min):
   - Verify module can be imported
   - Verify functions work correctly

3. **End-to-End Testing** (5 min):
   - Test BDD mode with RequireKit installed
   - Test BDD mode without RequireKit (rename marker)
   - Verify error messages are correct

4. **Unit Tests** (10 min):
   - Create test file
   - Implement unit tests
   - Run tests to verify

5. **Documentation** (3 min):
   - Update TASK-BDD-FIX1 completion report
   - Note that this task completes the implementation

**Total Estimated Time**: ~25 minutes

## Review Report Reference

Full analysis available at:
`.claude/reviews/TASK-REV-4039-review-report.md`

Key findings:
- Missing module is sole cause of BDD mode failures
- Marker file detection logic is correct
- TASK-BDD-FIX1 marked complete prematurely
