---
id: TASK-FIX-STATE02
title: "Phase 2: Fix medium priority state file paths and add shared helper"
status: in_review
task_type: implementation
created: 2025-12-09
updated: 2025-12-09
completed: 2025-12-09
priority: medium
tags: [bug, template-create, checkpoint-resume, state-files, phase-2, refactor]
related_tasks: [TASK-REV-STATE01, TASK-FIX-STATE01]
estimated_complexity: 4
review_source: TASK-REV-STATE01
depends_on: [TASK-FIX-STATE01]
previous_state: in_progress
state_transition_reason: "All quality gates passed - moved to IN_REVIEW"
quality_gates:
  compilation: PASS
  tests_pass: "86/86 (100%)"
  line_coverage: "100%"
  architectural_review: "88/100"
  code_review: "97/100"
---

# TASK-FIX-STATE02: Phase 2 - Medium Priority State File Fixes

## Summary

Fix the remaining medium priority state file path issues and introduce a shared helper to avoid code duplication. This is Phase 2 of the fix identified in TASK-REV-STATE01 comprehensive review.

**Prerequisite**: TASK-FIX-STATE01 (Phase 1) must be completed first.

## Review Reference

- **Review Task**: TASK-REV-STATE01
- **Review Report**: [.claude/reviews/TASK-REV-STATE01-review-report.md](.claude/reviews/TASK-REV-STATE01-review-report.md)
- **Phase 1**: TASK-FIX-STATE01 (critical files - must be done first)

## Scope: Phase 2 - Medium Priority Files + DRY Refactor

### Files to Modify

| File | Line(s) | Current | Change To |
|------|---------|---------|-----------|
| `installer/core/lib/template_config_handler.py` | 42, 52-53 | `Path.cwd()` based | Use shared helper |
| `installer/core/commands/lib/greenfield_qa_session.py` | 1263, 1286, 1300 | Relative paths | Use shared helper |

### New File to Create

| File | Purpose |
|------|---------|
| `installer/core/lib/state_paths.py` | Shared helper for state file paths |

### State Files Affected

| File | Workflow | Priority |
|------|----------|----------|
| `.template-create-config.json` | template-create | Medium |
| `.template-init-session.json` | template-create | Medium |
| `.template-init-partial-session.json` | template-create | Medium |

## Implementation Details

### 1. Create Shared Helper (state_paths.py)

**New file**: `installer/core/lib/state_paths.py`

```python
"""
State Paths Helper

Provides consistent absolute paths for state files used in checkpoint-resume patterns.
All state files are stored in ~/.agentecflow/state/ for CWD independence.

TASK-FIX-STATE02: DRY refactor for state file path management.
"""

from pathlib import Path
from typing import Optional


def get_state_dir() -> Path:
    """
    Get the standard state directory, creating if needed.

    Returns:
        Path to ~/.agentecflow/state/

    Example:
        >>> state_dir = get_state_dir()
        >>> print(state_dir)
        /Users/user/.agentecflow/state
    """
    state_dir = Path.home() / ".agentecflow" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def get_state_file(filename: str) -> Path:
    """
    Get path to a state file in the standard location.

    Args:
        filename: Name of the state file (e.g., ".agent-enhance-state.json")

    Returns:
        Absolute path to the state file

    Example:
        >>> path = get_state_file(".agent-enhance-state.json")
        >>> print(path)
        /Users/user/.agentecflow/state/.agent-enhance-state.json
    """
    return get_state_dir() / filename


def get_phase_request_file(phase: int) -> Path:
    """
    Get path to agent request file for a specific phase.

    Args:
        phase: Phase number (1-8)

    Returns:
        Absolute path to the request file
    """
    return get_state_file(f".agent-request-phase{phase}.json")


def get_phase_response_file(phase: int) -> Path:
    """
    Get path to agent response file for a specific phase.

    Args:
        phase: Phase number (1-8)

    Returns:
        Absolute path to the response file
    """
    return get_state_file(f".agent-response-phase{phase}.json")


# Convenience constants for common state files
AGENT_ENHANCE_STATE = ".agent-enhance-state.json"
TEMPLATE_CREATE_STATE = ".template-create-state.json"
TEMPLATE_CONFIG = ".template-create-config.json"
TEMPLATE_SESSION = ".template-init-session.json"
TEMPLATE_PARTIAL_SESSION = ".template-init-partial-session.json"
```

### 2. Update template_config_handler.py

**Location**: `installer/core/lib/template_config_handler.py` lines 42, 52-53

**Current**:
```python
CONFIG_FILENAME = ".template-create-config.json"
# ...
self.config_dir = config_path or Path.cwd()
self.config_file = self.config_dir / self.CONFIG_FILENAME
```

**Change to**:
```python
from lib.state_paths import get_state_file, TEMPLATE_CONFIG

CONFIG_FILENAME = TEMPLATE_CONFIG
# ...
if config_path is None:
    self.config_file = get_state_file(CONFIG_FILENAME)
else:
    self.config_file = config_path / self.CONFIG_FILENAME
```

### 3. Update greenfield_qa_session.py

**Location**: `installer/core/commands/lib/greenfield_qa_session.py` lines 1263, 1286, 1300

**Current**:
```python
session_file = Path(".template-init-session.json")
session_file = Path(".template-init-partial-session.json")
```

**Change to**:
```python
from lib.state_paths import get_state_file, TEMPLATE_SESSION, TEMPLATE_PARTIAL_SESSION

# In save_session (line 1263):
if session_file is None:
    session_file = get_state_file(TEMPLATE_SESSION)

# In load_session (line 1286):
if session_file is None:
    session_file = get_state_file(TEMPLATE_SESSION)

# In _save_partial_session (line 1300):
session_file = get_state_file(TEMPLATE_PARTIAL_SESSION)
```

### 4. Refactor Phase 1 Files (Optional DRY improvement)

If desired, refactor Phase 1 files to use the shared helper:

**orchestrator.py**:
```python
from lib.state_paths import get_state_file, AGENT_ENHANCE_STATE
self.state_file = get_state_file(AGENT_ENHANCE_STATE)
```

**state_manager.py**:
```python
from lib.state_paths import get_state_file, TEMPLATE_CREATE_STATE
if state_file is None:
    state_file = get_state_file(TEMPLATE_CREATE_STATE)
```

**invoker.py**:
```python
from lib.state_paths import get_phase_request_file, get_phase_response_file
if request_file is None:
    self.request_file = get_phase_request_file(phase)
if response_file is None:
    self.response_file = get_phase_response_file(phase)
```

## Acceptance Criteria

### AC1: Shared Helper Created
- [ ] `state_paths.py` created with all helper functions
- [ ] Constants defined for common state files
- [ ] Functions documented with examples

### AC2: Medium Priority Files Fixed
- [ ] `template_config_handler.py` uses shared helper
- [ ] `greenfield_qa_session.py` uses shared helper
- [ ] All session files written to `~/.agentecflow/state/`

### AC3: DRY Refactor (Optional)
- [ ] Phase 1 files refactored to use shared helper (if desired)
- [ ] No code duplication for state path logic

### AC4: Tests
- [ ] Unit tests for `state_paths.py` helper functions
- [ ] Existing tests still pass

## Testing

### Unit Tests for state_paths.py
- [ ] `get_state_dir()` creates directory if missing
- [ ] `get_state_file()` returns correct absolute path
- [ ] `get_phase_request_file()` and `get_phase_response_file()` work correctly

### Integration Tests
- [ ] Template config saves/loads from correct location
- [ ] QA session saves/loads from correct location
- [ ] Partial session saves to correct location

## Definition of Done

- [ ] `state_paths.py` created and working
- [ ] Medium priority files updated
- [ ] Optional DRY refactor for Phase 1 files (if approved)
- [ ] All tests pass
- [ ] No regression in existing functionality

## Related Tasks

- **TASK-REV-STATE01**: Review task that identified this issue (COMPLETED)
- **TASK-FIX-STATE01**: Phase 1 critical fixes (PREREQUISITE)
