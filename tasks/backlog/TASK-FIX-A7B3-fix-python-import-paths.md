---
id: TASK-FIX-A7B3
title: Fix Python import paths for curl installation compatibility
status: backlog
created: 2025-11-29T18:20:00Z
updated: 2025-11-29T18:20:00Z
priority: high
tags: [bug, installation, python, imports]
complexity: 6
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Fix Python import paths for curl installation compatibility

## Problem Description

When taskwright is installed via curl (not from a local git clone), Python imports fail because:

1. **Wrong import paths in documentation**: Commands reference `from installer.global.lib.X` but files are copied to `~/.agentecflow/commands/lib/`
2. **Missing Python path setup**: The `repo_path` field in the marker file exists but isn't used to add the repository to Python's sys.path
3. **Installation doesn't match runtime paths**: Files are installed to one location but imports expect them in another

### Example Error
```python
# This fails when installed via curl:
from installer.global.lib.id_generator import generate_task_id

# ModuleNotFoundError: No module named 'installer'
```

## Root Cause Analysis

The install script copies Python files:
- **From**: `$INSTALLER_DIR/global/commands/lib/*.py`
- **To**: `~/.agentecflow/commands/lib/*.py`

But command documentation shows imports as:
- `from installer.global.lib.id_generator import ...`

This works when running from a git clone but fails when installed via curl because:
- The `installer/` directory doesn't exist in `~/.agentecflow/`
- Python doesn't know to look in the repository path
- The `repo_path` in the marker file is not used to configure Python paths

## Acceptance Criteria

- [ ] All Python imports in command files use paths that work with curl installation
- [ ] Either use relative imports (`from lib.X`) or configure Python path from marker file
- [ ] Installation script validates that all referenced Python modules are copied
- [ ] Test installation via curl successfully runs commands that use Python imports
- [ ] Documentation examples show correct import paths

## Proposed Solutions

### Option 1: Use Relative Imports (Recommended)
Change all imports to use the installed location:
```python
# BEFORE (broken with curl):
from installer.global.lib.id_generator import generate_task_id

# AFTER (works everywhere):
from lib.id_generator import generate_task_id
```

**Pros**: Simple, works immediately, no path manipulation needed
**Cons**: Requires updating all command documentation

### Option 2: Add Python Path Setup
Create a Python path bootstrap that reads from the marker file:
```python
import sys
import json
import os

# Read repo_path from marker
marker_path = os.path.expanduser("~/.agentecflow/taskwright.marker.json")
with open(marker_path) as f:
    marker = json.load(f)
    repo_path = marker.get("repo_path")
    if repo_path and os.path.exists(repo_path):
        sys.path.insert(0, repo_path)

# Now imports work:
from installer.global.lib.id_generator import generate_task_id
```

**Pros**: Keeps existing import paths
**Cons**: Adds complexity, requires bootstrap code in every command

### Option 3: Symlink Solution
Create symlink during installation:
```bash
ln -sf "$repo_root" "$INSTALL_DIR/installer"
```

**Pros**: Transparent, no code changes
**Cons**: Breaks when repo_path moves, symlinks may not work on all platforms

## Implementation Plan

1. **Audit all command files** for Python import statements
2. **Check if referenced modules exist** in both repo and installed locations
3. **Choose solution** (Option 1 recommended for simplicity)
4. **Update all imports** to use chosen pattern
5. **Update install script** to validate all imports are satisfied
6. **Test curl installation** to verify fix

## Files Affected

### Command Files (need import updates)
- `/commands/task-create.md` - References `installer.global.lib.id_generator`
- Any other commands using Python imports

### Install Script
- `installer/scripts/install.sh` - May need to copy additional Python files or create path setup

### Marker File (already updated)
- `taskwright.marker.json` - Contains `repo_path` field

## Test Plan

1. **Fresh curl install test**:
   ```bash
   # Clean environment
   rm -rf ~/.agentecflow

   # Install via curl
   curl -sSL https://raw.githubusercontent.com/taskwright-dev/taskwright/main/installer/scripts/install.sh | bash

   # Test Python imports
   /task-create "Test task"
   ```

2. **Verify all commands work** that use Python imports
3. **Check both local clone and curl install** produce same behavior

## Notes

- This is a **critical bug** affecting curl installations
- Adding `repo_path` to marker was a good first step but doesn't solve the import issue
- Solution must work without requiring users to set environment variables
- Consider adding this check to the `taskwright doctor` command

## Related Issues

- Duplicate marker file bug (FIXED)
- requirekit integration check (FIXED)
