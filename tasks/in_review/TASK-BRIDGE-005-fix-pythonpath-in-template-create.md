# TASK-BRIDGE-005: Fix PYTHONPATH in /template-create Command

**Status**: in_review
**Priority**: high
**Estimated Duration**: 30 minutes
**Tags**: #bridge #bugfix #pythonpath #template-create

---

## Description

Fix the `/template-create` command to set PYTHONPATH before invoking the Python orchestrator, enabling the command to work from any directory without "ModuleNotFoundError: No module named 'installer'".

**Part of**: Python↔Claude Agent Invocation Bridge (Critical Feature)
**Blocks**: Template creation from user projects

---

## Context

The bridge implementation (TASK-BRIDGE-001, 002, 003) is complete, but users get this error when running `/template-create` from their project directories:

```
python3 -m installer.global.commands.lib.template_create_orchestrator
ModuleNotFoundError: No module named 'installer'
```

**Root Cause**: The command runs `python3 -m installer.global...` but doesn't set PYTHONPATH to include the taskwright directory, so Python can't find the `installer` module.

**Current Workaround**: Users must manually set PYTHONPATH or run from taskwright directory.

---

## Acceptance Criteria

- [ ] `/template-create` command modified to set PYTHONPATH before running orchestrator
- [ ] PYTHONPATH includes taskwright installation directory
- [ ] Command works from any directory (user project directories)
- [ ] PYTHONPATH discovery handles multiple installation locations:
  - [ ] Standard: `~/Projects/appmilla_github/taskwright`
  - [ ] Alternative: Discover via ~/.agentecflow symlinks
  - [ ] Fallback: Use relative path from command location
- [ ] Existing PYTHONPATH preserved (append, don't replace)
- [ ] No regression: Command still works when run from taskwright directory
- [ ] Error handling if taskwright directory can't be found

---

## Implementation Plan

### File to Modify

1. `~/.agentecflow/commands/template-create.md` (or `installer/global/commands/template-create.md`)

### Implementation Steps

#### Step 1: Add PYTHONPATH Setup (15 min)

Modify the command execution section (around line 950) to add PYTHONPATH before running orchestrator:

```python
# BEFORE (Current - BROKEN):
cmd_parts = [
    "python3", "-m",
    "installer.global.commands.lib.template_create_orchestrator"
]

# ... add arguments ...

cmd = " ".join(cmd_parts)
result = bash(cmd, timeout=ORCHESTRATOR_TIMEOUT_MS)
```

```python
# AFTER (Fixed):
import os
from pathlib import Path

# Step 1: Discover taskwright installation directory
def find_taskwright_path():
    """
    Find taskwright installation directory.

    Tries multiple strategies:
    1. Check if ~/.agentecflow is a symlink (points to taskwright)
    2. Check standard location: ~/Projects/appmilla_github/taskwright
    3. Check relative to command file location

    Returns:
        Path to taskwright directory or None if not found
    """
    # Strategy 1: Follow ~/.agentecflow symlink
    agentecflow = Path.home() / ".agentecflow"
    if agentecflow.is_symlink():
        target = agentecflow.resolve()
        # Symlink points to taskwright/.agentecflow, go up one level
        if target.name == ".agentecflow":
            taskwright_path = target.parent
            if (taskwright_path / "installer").exists():
                return taskwright_path

    # Strategy 2: Standard installation location
    standard_path = Path.home() / "Projects" / "appmilla_github" / "taskwright"
    if (standard_path / "installer").exists():
        return standard_path

    # Strategy 3: Relative to this command file
    # (if running from taskwright directory)
    if Path("installer").exists():
        return Path.cwd()

    return None

# Step 2: Set PYTHONPATH
taskwright_path = find_taskwright_path()

if taskwright_path is None:
    print("❌ ERROR: Cannot find taskwright installation directory")
    print("   Searched:")
    print("   - ~/.agentecflow symlink target")
    print("   - ~/Projects/appmilla_github/taskwright")
    print("   - Current directory")
    print()
    print("   Please ensure taskwright is installed correctly.")
    exit(1)

# Set PYTHONPATH to include taskwright directory
original_pythonpath = os.environ.get("PYTHONPATH", "")
if original_pythonpath:
    os.environ["PYTHONPATH"] = f"{taskwright_path}:{original_pythonpath}"
else:
    os.environ["PYTHONPATH"] = str(taskwright_path)

print(f"🔍 Taskwright path: {taskwright_path}")
print(f"🐍 PYTHONPATH: {os.environ['PYTHONPATH']}")
print()

# Step 3: Build and run command (unchanged)
cmd_parts = [
    "python3", "-m",
    "installer.global.commands.lib.template_create_orchestrator"
]

# ... add arguments ...

cmd = " ".join(cmd_parts)
result = bash(cmd, timeout=ORCHESTRATOR_TIMEOUT_MS)
```

#### Step 2: Test from Different Directories (10 min)

Test that command works from:
1. User project directory (primary use case)
2. Taskwright directory (regression test)
3. Home directory (edge case)
4. Random directory (edge case)

#### Step 3: Add Error Handling (5 min)

Add clear error messages if:
- Taskwright directory can't be found
- Python module still not found after PYTHONPATH set
- Permission issues accessing taskwright directory

---

## Technical Details

### PYTHONPATH Format

```bash
# On Unix/macOS (colon-separated)
export PYTHONPATH="/path/to/taskwright:/existing/paths"

# In Python
os.environ["PYTHONPATH"] = f"{taskwright_path}:{original_pythonpath}"
```

### Discovery Strategies

**Priority 1: Symlink Resolution**
- Most reliable for installations following docs
- `~/.agentecflow` symlinks to `taskwright/.agentecflow`
- Resolve symlink and go up one directory

**Priority 2: Standard Location**
- `~/Projects/appmilla_github/taskwright`
- Most users install here

**Priority 3: Current Directory**
- If running from taskwright directory
- Fallback for development

### Error Messages

```
❌ ERROR: Cannot find taskwright installation directory

Searched:
- ~/.agentecflow symlink target
- ~/Projects/appmilla_github/taskwright
- Current directory: /Users/you/Projects/other-project

Troubleshooting:
1. Verify taskwright is installed: ls ~/Projects/appmilla_github/taskwright
2. Check symlink: ls -la ~/.agentecflow
3. Run install.sh if needed: ~/Projects/appmilla_github/taskwright/installer/scripts/install.sh

Manual workaround:
export PYTHONPATH="~/Projects/appmilla_github/taskwright:$PYTHONPATH"
/template-create --path .
```

---

## Testing

### Test Case 1: Run from User Project
```bash
cd ~/Projects/my-dotnet-project
/template-create --validate --path .

# Expected: Works without error
# Actual (before fix): ModuleNotFoundError
```

### Test Case 2: Run from Taskwright
```bash
cd ~/Projects/appmilla_github/taskwright
/template-create --validate --path ~/Projects/my-dotnet-project

# Expected: Works (regression test)
```

### Test Case 3: Run from Home Directory
```bash
cd ~
/template-create --validate --path ~/Projects/my-dotnet-project

# Expected: Works
```

### Test Case 4: Taskwright Not Found
```bash
# Rename taskwright directory temporarily
mv ~/Projects/appmilla_github/taskwright ~/Projects/appmilla_github/taskwright-backup

cd ~/Projects/my-dotnet-project
/template-create --validate --path .

# Expected: Clear error message with troubleshooting steps
# Restore after test:
mv ~/Projects/appmilla_github/taskwright-backup ~/Projects/appmilla_github/taskwright
```

---

## Dependencies

- **TASK-BRIDGE-001**: Agent Bridge Infrastructure (COMPLETED)
- **TASK-BRIDGE-002**: Orchestrator Integration (COMPLETED)
- **TASK-BRIDGE-003**: Command Integration (COMPLETED)

---

## Definition of Done

- [ ] PYTHONPATH setup code added to template-create.md
- [ ] Command works from any directory (tested from 3+ locations)
- [ ] Error handling for missing taskwright directory
- [ ] Clear error messages with troubleshooting steps
- [ ] No regression: existing workflows still work
- [ ] Documentation updated (if needed)
- [ ] User tested: Works with DeCUK.Mobile.MyDrive project

---

## Related Tasks

- TASK-BRIDGE-001: Agent Bridge Infrastructure
- TASK-BRIDGE-002: Orchestrator Integration
- TASK-BRIDGE-003: Command Integration
- TASK-BRIDGE-004: End-to-End Testing

---

## References

- [Bridge Implementation Summary](../../docs/proposals/BRIDGE-IMPLEMENTATION-SUMMARY.md)
- [Technical Specification](../../docs/proposals/python-claude-bridge-technical-spec.md)
- User Bug Report: "ModuleNotFoundError: No module named 'installer'"

---

## User Impact

**Before Fix**:
```bash
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate
# ❌ ModuleNotFoundError: No module named 'installer'
# Workaround: cd ~/Projects/appmilla_github/taskwright
```

**After Fix**:
```bash
cd ~/Projects/DeCUK.Mobile.MyDrive
/template-create --validate
# ✅ Works from any directory
# 🔍 Taskwright path: /Users/.../taskwright
# 🐍 PYTHONPATH set correctly
# Phase 1: Q&A Session...
```

---

## Estimated Time Breakdown

- PYTHONPATH discovery logic: 10 minutes
- Integration with command: 5 minutes
- Error handling: 5 minutes
- Testing from multiple directories: 10 minutes
- **Total**: ~30 minutes
