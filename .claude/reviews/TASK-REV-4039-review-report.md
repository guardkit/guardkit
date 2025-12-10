# Review Report: TASK-REV-4039

**Title**: Review BDD mode RequireKit marker file detection
**Review Mode**: Decision Analysis
**Review Depth**: Standard
**Reviewer**: Claude (Sonnet 4.5)
**Date**: 2025-11-30
**Duration**: ~15 minutes

---

## Executive Summary

**Root Cause**: The `feature_detection` module referenced in TASK-BDD-FIX1 was never created, causing BDD mode validation to fail with an import error.

**Impact**: HIGH - Completely blocks BDD mode functionality
**Severity**: CRITICAL - TASK-BDD-FIX1 marked as complete but implementation is incomplete

**Recommended Action**: Create `installer/core/commands/lib/feature_detection.py` module with RequireKit detection logic

---

## Review Details

- **Review Type**: Root cause analysis + decision recommendation
- **Scope**: BDD mode validation in task-work command
- **Files Analyzed**:
  - `installer/core/commands/task-work.md` (lines 603-622)
  - `installer/core/commands/lib/` (directory scan)
- **Testing Performed**:
  - Marker file existence verification
  - Path resolution testing
  - Import simulation

---

## Findings

### Finding 1: Missing Module (CRITICAL)

**Evidence**:
```bash
# task-work.md line 606 references:
from installer.core.commands.lib.feature_detection import supports_bdd

# But the file does not exist:
$ ls installer/core/commands/lib/feature_detection.py
ls: installer/core/commands/lib/feature_detection.py: No such file or directory

# grep search confirms no supports_bdd function anywhere:
$ grep -r "def supports_bdd" installer/core/commands/lib/
(no results)
```

**Impact**:
- Python import fails at runtime
- BDD mode validation always reports "RequireKit not installed"
- Even when RequireKit IS correctly installed

**Severity**: CRITICAL

---

### Finding 2: Marker File Detection Works Correctly

**Evidence**:
```python
# Testing the detection logic in isolation:
from pathlib import Path

home = Path.home()
marker_paths = [
    home / ".agentecflow" / "require-kit.marker.json",
    home / "Projects" / "require-kit" / "require-kit.marker"
]

requirekit_installed = any(path.exists() for path in marker_paths)
# Result: True ✅

# File verified to exist:
$ ls -la ~/.agentecflow/require-kit.marker.json
-rw-r--r--  1 richwoollcott  staff  625 Nov 30 07:57 require-kit.marker.json
```

**Conclusion**: The detection logic is correct. The problem is solely the missing module.

---

### Finding 3: TASK-BDD-FIX1 Incomplete Implementation

**What Was Done**:
- ✅ Added mode flag parsing in task-work.md Step 0
- ✅ Added BDD validation with error messages
- ✅ Added import statement for feature_detection module
- ✅ Updated flag display with mode info
- ✅ Removed incorrect comment at line 893
- ✅ Created test verification scenarios

**What Was NOT Done**:
- ❌ Create `feature_detection.py` module
- ❌ Implement `supports_bdd()` function
- ❌ Test the actual runtime execution (only documentation review)

**Impact**: Task marked COMPLETED but functionality doesn't work

---

## Root Cause Analysis

### Timeline of Events

1. **TASK-BDD-FIX1 Created**: Fix BDD mode validation bug
2. **Implementation**: Modified task-work.md to call `supports_bdd()`
3. **Testing**: Code review verified markdown syntax, not runtime execution
4. **Completion**: Task moved to COMPLETED without functional testing
5. **VM Testing**: User discovers BDD mode still fails
6. **This Review**: Identified missing module as root cause

### Why It Wasn't Caught

1. **Test Verification Phase**: Only validated markdown syntax and code structure
2. **No Runtime Testing**: Didn't execute actual `/task-work --mode=bdd` command
3. **Code Review**: Reviewed documentation, not functional behavior
4. **Completion Criteria**: Didn't include "BDD mode works end-to-end"

### Lessons Learned

- Documentation changes require functional verification
- Import statements should be validated against actual files
- End-to-end testing needed for critical workflows
- Completion criteria should include "feature works in production"

---

## Decision Options

### Option 1: Create feature_detection.py Module (RECOMMENDED)

**Implementation**:
```python
# File: installer/core/commands/lib/feature_detection.py

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

**Pros**:
- ✅ Clean separation of concerns
- ✅ Reusable across multiple commands
- ✅ Easier to test in isolation
- ✅ Follows existing lib module pattern
- ✅ Future-proof for additional feature detection
- ✅ Can be extended with version checking, capability detection

**Cons**:
- Requires new file creation
- Slightly more setup

**Estimated Effort**: 15 minutes

---

### Option 2: Inline Detection in task-work.md

**Implementation**:

Replace lines 606-608 in task-work.md:

```markdown
**BEFORE** (current):
```python
from installer.core.commands.lib.feature_detection import supports_bdd

if not supports_bdd():
```

**AFTER** (inline):
```python
# Check for RequireKit installation
home = Path.home()
marker_paths = [
    home / ".agentecflow" / "require-kit.marker.json",
    home / "Projects" / "require-kit" / "require-kit.marker"
]
requirekit_installed = any(path.exists() for path in marker_paths)

if not requirekit_installed:
```

**Pros**:
- ✅ No new files needed
- ✅ Self-contained in task-work.md
- ✅ Easier to understand (all logic in one place)

**Cons**:
- ❌ Code duplication if other commands need same check
- ❌ Harder to test in isolation
- ❌ Doesn't follow existing lib module pattern
- ❌ Less maintainable long-term

**Estimated Effort**: 5 minutes

---

## Recommendation

**CHOOSE OPTION 1: Create feature_detection.py module**

### Rationale

1. **Best Practice**: Follows existing Taskwright architecture (lib modules for reusable logic)
2. **Maintainability**: Single source of truth for feature detection
3. **Testability**: Can unit test feature_detection independently
4. **Extensibility**: Easy to add `supports_requirements()`, `supports_epics()`, etc.
5. **Future-Proof**: Already referenced in task-work.md, just needs to be created

### Implementation Plan

1. **Create Module** (5 min):
   ```bash
   touch installer/core/commands/lib/feature_detection.py
   # Add code from Option 1 above
   ```

2. **Validate Import** (2 min):
   ```python
   # Test that import works:
   from installer.core.commands.lib.feature_detection import supports_bdd
   print(supports_bdd())  # Should print True if RequireKit installed
   ```

3. **Test BDD Mode** (5 min):
   ```bash
   # Create test task
   /task-create "Test BDD validation" bdd_scenarios:[BDD-TEST-001]

   # Test BDD mode
   /task-work TASK-XXX --mode=bdd
   # Should now detect RequireKit correctly
   ```

4. **Update Documentation** (3 min):
   - Update TASK-BDD-FIX1 completion report
   - Add note about feature_detection.py creation
   - Document the bug and fix

**Total Effort**: ~15 minutes

---

## Test Plan

### Unit Tests (feature_detection.py)

```python
# File: tests/lib/test_feature_detection.py

import pytest
from pathlib import Path
from installer.core.commands.lib.feature_detection import supports_bdd

def test_supports_bdd_with_marker_file(tmp_path, monkeypatch):
    """Test that supports_bdd returns True when marker file exists."""
    # Mock home directory
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: fake_home)

    # Create marker file
    agentecflow = fake_home / ".agentecflow"
    agentecflow.mkdir()
    marker = agentecflow / "require-kit.marker.json"
    marker.write_text('{"package": "require-kit", "version": "1.0.0"}')

    # Test
    assert supports_bdd() == True

def test_supports_bdd_without_marker_file(tmp_path, monkeypatch):
    """Test that supports_bdd returns False when marker file missing."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: fake_home)

    assert supports_bdd() == False
```

### Integration Tests (task-work command)

```bash
# Test 1: BDD mode WITH RequireKit
$ /task-work TASK-XXX --mode=bdd
Expected: ✅ RequireKit installation verified

# Test 2: BDD mode WITHOUT RequireKit (remove marker)
$ mv ~/.agentecflow/require-kit.marker.json ~/.agentecflow/require-kit.marker.json.backup
$ /task-work TASK-XXX --mode=bdd
Expected: ❌ ERROR: BDD mode requires RequireKit installation

# Test 3: Restore marker and retest
$ mv ~/.agentecflow/require-kit.marker.json.backup ~/.agentecflow/require-kit.marker.json
$ /task-work TASK-XXX --mode=bdd
Expected: ✅ RequireKit installation verified
```

---

## Related Tasks

- **TASK-BDD-FIX1**: Fix BDD mode validation (COMPLETED)
  - **Action**: Needs follow-up fix to create feature_detection.py
  - **Status**: Mark as incomplete or create TASK-BDD-FIX2

---

## Appendices

### Appendix A: VM Test Output

```bash
richwoollcott@macos .agentecflow % ls -la
-rw-r--r--@  1 richwoollcott  staff   603 30 Nov 10:48 require-kit.marker.json

richwoollcott@macos ~ % /task-work TASK-308E --mode=bdd
🔍 Validating BDD mode requirements...

❌ ERROR: BDD mode requires RequireKit installation

  Repository: https://github.com/requirekit/require-kit
  Installation:
    cd ~/Projects/require-kit
    ./installer/scripts/install.sh

  Alternative modes:
    /task-work TASK-308E --mode=tdd
    /task-work TASK-308E --mode=standard
```

### Appendix B: Files Checked

```bash
$ ls installer/core/commands/lib/*.py | wc -l
76

$ grep -r "feature_detection" installer/core/commands/lib/
(no results - module doesn't exist)

$ grep -r "def supports_bdd" installer/core/commands/
(no results - function doesn't exist)
```

---

## Conclusion

The BDD mode validation failure is caused by a missing Python module (`feature_detection.py`) that was referenced in TASK-BDD-FIX1 but never created. The detection logic itself is correct and works when tested in isolation.

**Immediate Action**: Create `feature_detection.py` module with `supports_bdd()` function

**Long-term**: Improve test verification to include functional/runtime testing, not just documentation review
