# Task-Create ID Generator Import Bug

**Discovered**: 2025-11-29 during VM testing
**Severity**: HIGH - `/task-create` command completely broken on fresh installations
**Status**: FIXED

---

## Bug Description

When running `/task-create` on a fresh installation, the command fails with:

```
✗ Failed to import id_generator: No module named 'id_generator'
```

This breaks task creation entirely, making the system unusable.

---

## Root Cause

The `/task-create` command is specification-based ([task-create.md](../../../installer/global/commands/task-create.md)) and executes Python code inline via Claude Code. The spec includes:

```python
from installer.global.lib.id_generator import generate_task_id, validate_task_id, check_duplicate
```

**Problem**: This import assumes Python can find the `installer/` package, but:

1. When running from a user project (e.g., `~/Projects/test-api-service`), the taskwright repo is NOT in Python's sys.path
2. The `id_generator.py` module exists at `~/Projects/appmilla_github/taskwright/installer/global/lib/id_generator.py`
3. Python doesn't know where to find it

**Unlike Python command scripts** (e.g., `agent-enhance.py`) which use `__file__` to resolve the repo path, **inline spec execution** doesn't have `__file__` available.

---

## Fix Applied

### Fix 1: Add Repository Root Resolution to task-create.md

**File**: [task-create.md](../../../installer/global/commands/task-create.md:207-263)

**Added path resolution before import**:

```python
# === BEGIN: Repository Root Resolution ===
import sys
from pathlib import Path

def _find_taskwright_repo():
    """
    Find taskwright repository root by looking for marker file.
    Search order:
    1. ~/.agentecflow/taskwright.marker.json (contains repo path)
    2. Common locations (~/Projects/appmilla_github/taskwright, ~/Projects/taskwright)
    """
    # Check marker file first (most reliable)
    marker_json = Path.home() / ".agentecflow" / "taskwright.marker.json"
    if marker_json.exists():
        import json
        try:
            with open(marker_json) as f:
                data = json.load(f)
                repo_path = Path(data.get("repo_path", ""))
                if repo_path.exists():
                    return repo_path
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    # Fallback: Check common locations
    common_paths = [
        Path.home() / "Projects" / "appmilla_github" / "taskwright",
        Path.home() / "Projects" / "taskwright",
        Path.cwd(),  # Current directory (if running from repo)
    ]

    for path in common_paths:
        # Verify it's the taskwright repo
        if (path / "installer" / "global" / "lib" / "id_generator.py").exists():
            return path

    return None

taskwright_repo = _find_taskwright_repo()
if not taskwright_repo:
    print("ERROR: Cannot locate taskwright repository")
    print("  Searched:")
    print("    - ~/.agentecflow/taskwright.marker.json")
    print("    - ~/Projects/appmilla_github/taskwright")
    print("    - ~/Projects/taskwright")
    print("  Installation may be incomplete. Try reinstalling:")
    print("    cd ~/Projects/appmilla_github/taskwright")
    print("    ./installer/scripts/install.sh")
    sys.exit(1)

# Add to sys.path
if str(taskwright_repo) not in sys.path:
    sys.path.insert(0, str(taskwright_repo))
# === END: Repository Root Resolution ===

from installer.global.lib.id_generator import generate_task_id, validate_task_id, check_duplicate
```

**How it works**:
1. Checks `~/.agentecflow/taskwright.marker.json` for `repo_path` field (most reliable)
2. Falls back to common installation paths
3. Verifies path contains `installer/global/lib/id_generator.py`
4. Adds repo root to `sys.path`
5. Imports normally

### Fix 2: Add repo_path to Marker File

**File**: [install.sh](../../../installer/scripts/install.sh:1373-1407)

**Added `repo_path` field to marker file**:

```bash
# Determine repository root (parent of installer/)
local repo_root
if [ -d "$INSTALLER_DIR" ]; then
    repo_root="$(cd "$INSTALLER_DIR/.." && pwd)"
else
    repo_root="$PWD"  # Fallback to current directory
fi

# Create marker file with repo_path
cat > "$marker_file" << EOF
{
  "package": "taskwright",
  "version": "$AGENTECFLOW_VERSION",
  "installed": "$install_date",
  "install_location": "$INSTALL_DIR",
  "repo_path": "$repo_root",
  ...
}
EOF
```

**Why this is needed**:
- Marker file already exists for feature detection ([feature_detection.py](../../../installer/global/lib/feature_detection.py))
- Adding `repo_path` provides a **reliable, installation-agnostic** way to find the repo
- Works whether installed via git clone or curl script

---

## Verification

### Test 1: Fresh Installation on VM

```bash
# Install taskwright
cd ~/Projects/appmilla_github/taskwright
./installer/scripts/install.sh

# Verify marker file has repo_path
cat ~/.agentecflow/taskwright.marker.json | grep repo_path
# Should output: "repo_path": "/Users/[username]/Projects/appmilla_github/taskwright"

# Try task creation from user project
cd ~/Projects/test-api-service
/task-create "Test task creation"

# Expected:
# ✅ Task created: TASK-A3F2
# File: tasks/backlog/TASK-A3F2-test-task-creation.md
```

**Success criteria**: Task created without import errors.

### Test 2: Curl Installation

**IMPORTANT**: Curl installation now **clones the repository permanently** to fix this issue.

```bash
# Remove existing installation
rm -rf ~/.agentecflow
rm -rf ~/Projects/taskwright  # or ~/taskwright

# Install via curl
curl -sSL https://install.taskwright.dev | bash

# Expected behavior:
# - If git is available: Clones repo to ~/Projects/taskwright (or ~/taskwright)
# - If git not available: Downloads tarball to ~/Projects/taskwright (or ~/taskwright)
# - Creates marker file with repo_path pointing to permanent location

# Verify marker file
cat ~/.agentecflow/taskwright.marker.json | grep repo_path
# Should output: "repo_path": "/Users/[username]/Projects/taskwright"

# Verify repository exists
ls ~/Projects/taskwright/installer/global/lib/id_generator.py
# Should exist

# Try task creation
cd ~/Projects/my-project
/task-create "Test task"

# Expected: Task created successfully
```

**Success criteria**:
- Repository cloned/downloaded to permanent location
- repo_path points to that location
- Task creation works from any directory

### Test 3: Non-Standard Installation Path

```bash
# Clone to custom location
cd ~/custom-location
git clone https://github.com/taskwright/taskwright.git

# Install
cd taskwright
./installer/scripts/install.sh

# Verify marker file
cat ~/.agentecflow/taskwright.marker.json | grep repo_path
# Should output: "repo_path": "/Users/[username]/custom-location/taskwright"

# Try task creation
cd ~/Projects/another-project
/task-create "Test task"

# Expected: Task created successfully
```

**Success criteria**: Works regardless of installation path.

---

## Impact

### Before Fix
- ❌ `/task-create` completely broken on fresh installations
- ❌ Users unable to create tasks
- ❌ System unusable without manual workarounds

### After Fix
- ✅ `/task-create` works from any directory
- ✅ Automatic repository path detection
- ✅ Graceful fallback to common locations
- ✅ Clear error message if repo not found

---

## Related Files

- **Spec**: [task-create.md](../../../installer/global/commands/task-create.md)
- **Module**: [id_generator.py](../../../installer/global/lib/id_generator.py)
- **Installation**: [install.sh](../../../installer/scripts/install.sh)
- **Feature Detection**: [feature_detection.py](../../../installer/global/lib/feature_detection.py)

---

## Follow-Up

### Other Commands to Check

**Question**: Do other inline spec commands have the same issue?

**Commands to audit**:
- `/task-work` - Uses task-manager agent (spec-based, may have similar imports)
- `/task-status` - Likely pure spec, check for module imports
- `/task-complete` - Check for module imports
- `/task-refine` - Check for module imports

**Action**: Search for `from installer.global.` in all `.md` command specs and add repository resolution pattern if found.

### Alternative Solution: Convert to Python Script

**Consideration**: Should `task-create` be a Python script (`.py`) instead of a spec (`.md`)?

**Pros**:
- Uses standard `__file__` resolution pattern (like `agent-enhance.py`)
- No special path resolution needed
- Easier to test and debug
- Consistent with other complex commands

**Cons**:
- Less transparent (spec is more readable for humans)
- Requires maintenance of separate Python file
- Loses inline documentation benefits

**Recommendation**: Keep as spec for now (transparency is valuable), but if we add more complex Python logic, consider converting to `.py` script.

---

## Status

- [x] Bug identified (VM testing)
- [x] Root cause analyzed (import path resolution)
- [x] Fix 1 applied (task-create.md repository resolution)
- [x] Fix 2 applied (install.sh marker file repo_path)
- [ ] Verified on VM (pending reinstallation)
- [ ] Regression testing (other commands)
- [ ] Documentation updated

---

**Next Steps**: User should reinstall on VM to pick up the fix:

```bash
# On VM
cd ~/Projects/appmilla_github/taskwright
git pull
./installer/scripts/install.sh

# Verify marker file
cat ~/.agentecflow/taskwright.marker.json | grep repo_path

# Test task creation
cd ~/Projects/test-api-service
/task-create "Test BDD error handling"
```
