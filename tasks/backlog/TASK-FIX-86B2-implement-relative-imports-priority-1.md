---
id: TASK-FIX-86B2
title: Implement relative imports for Python path fix (Priority 1 - Launch Blocker)
status: backlog
created: 2025-11-29T19:40:00Z
updated: 2025-11-29T19:40:00Z
priority: critical
tags: [bug, installation, python-imports, launch-blocker, pre-launch]
complexity: 5
parent_review: TASK-REV-DEF4
estimated_effort: 2-3 hours
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Implement Relative Imports for Python Path Fix (Priority 1)

## Context

**CRITICAL LAUNCH BLOCKER**: This task implements the fix for 100% curl installation failure rate identified in comprehensive architectural review TASK-REV-DEF4.

**Review Finding**: Python imports use `from installer.global.lib.X` which causes syntax errors because:
1. `global` is a Python reserved keyword
2. `installer/` directory doesn't exist in installed location
3. Repository path resolution exists but doesn't solve the core problem

**Recommended Solution**: Option 1 - Relative Imports (scored 9/10)

**Impact**: Without this fix, ALL curl installations will fail immediately

---

## Objective

Convert all Python imports from absolute repository paths to relative installed paths.

**Change Pattern**:
```python
# BEFORE (broken):
from installer.global.lib.id_generator import generate_task_id

# AFTER (works):
from lib.id_generator import generate_task_id
```

---

## Implementation Steps

### Step 1: Update task-create.md (Primary Fix)

**File**: `installer/global/commands/task-create.md`

**Action 1**: Remove repository path resolution code
- **Delete lines 207-263** (entire `_find_taskwright_repo()` function)
- This code is no longer needed with relative imports

**Action 2**: Update import statement
- **Find line ~265**:
  ```python
  from installer.global.lib.id_generator import generate_task_id, validate_task_id, check_duplicate
  ```
- **Replace with**:
  ```python
  from lib.id_generator import generate_task_id, validate_task_id, check_duplicate
  ```

---

### Step 2: Find All Other Problematic Imports

**Command**:
```bash
cd ~/Projects/appmilla_github/taskwright
grep -rn "from installer\.global\.lib" installer/global/commands/
```

**Expected Files**:
- `task-create.md` (already fixed in Step 1)
- Potentially other command markdown files
- Any `.py` scripts with embedded imports

**Action**: For each file found, update imports to use `from lib.MODULE_NAME`

---

### Step 3: Update Python Scripts (.py files)

**Files to Check**:
```bash
# Find Python scripts with problematic imports
grep -rn "from installer\.global\.lib" installer/global/commands/*.py
grep -rn "from installer\.global\.lib" installer/global/lib/*.py
```

**Example**: `installer/global/commands/agent-enhance.py`

**BEFORE** (lines ~19-31):
```python
# Custom path resolution
def _find_taskwright_repo():
    marker_path = os.path.expanduser("~/.agentecflow/taskwright.marker.json")
    # ... resolution logic ...
    return repo_path

taskwright_repo = _find_taskwright_repo()
sys.path.insert(0, taskwright_repo)

from installer.global.lib.agent_utils import load_agent_file
```

**AFTER**:
```python
# No path resolution needed!
from lib.agent_utils import load_agent_file
```

**Action**: Remove path resolution code, use relative imports

---

### Step 4: Verify Install Script Copies Lib Files

**File**: `installer/scripts/install.sh`

**Check lines 357-398** should contain:
```bash
# Copy Python libraries
if [ -d "$INSTALLER_DIR/global/lib" ]; then
    mkdir -p "$COMMANDS_DIR/lib"
    cp -r "$INSTALLER_DIR/global/lib"/* "$COMMANDS_DIR/lib/"
fi
```

**Expected**: ✅ This already exists and works correctly

**Action**: Verify it's present, no changes needed

---

### Step 5: Test Curl Installation (Critical)

**Fresh Environment Test**:
```bash
# Clean environment completely
rm -rf ~/.agentecflow
rm -rf ~/Downloads/taskwright  # Or wherever curl downloads

# Install via curl (use your actual curl command)
curl -sSL https://raw.githubusercontent.com/taskwright-dev/taskwright/main/installer/scripts/install.sh | bash

# Test Python command works
/task-create "Test task after curl install fix" priority:high

# Expected: ✅ Task created successfully
# If error: Check which import failed and fix that file
```

**Success Criteria**:
- ✅ No import errors
- ✅ Task file created in tasks/backlog/
- ✅ No syntax errors
- ✅ Command completes normally

---

### Step 6: Test Git Clone Installation (Regression Check)

**Clean Environment Test**:
```bash
# Clean environment
rm -rf ~/.agentecflow

# Install from local git clone (existing method)
cd ~/Projects/appmilla_github/taskwright
./installer/scripts/install.sh

# Test command works
/task-create "Test task after git clone install"

# Expected: ✅ Task created successfully (no regression)
```

**Success Criteria**:
- ✅ Works identically to curl installation
- ✅ No regressions for existing git clone users
- ✅ Same behavior in both contexts

---

### Step 7: Test Both Execution Contexts

**Shell Execution Test**:
```bash
taskwright --version
# Should display version without errors
```

**Claude Code Execution Test**:
```bash
# Open Claude Code in a project
# Run: /task-create "Test from Claude Code"
# Expected: Works without import errors
```

**Success Criteria**:
- ✅ Both contexts work identically
- ✅ No import errors in either context
- ✅ Same Python import resolution behavior

---

## Acceptance Criteria

- [ ] All `from installer.global.lib.X` imports changed to `from lib.X`
- [ ] All repository path resolution code removed
- [ ] Fresh curl installation succeeds (clean VM test)
- [ ] Git clone installation still works (no regression)
- [ ] Claude Code slash commands work
- [ ] Shell commands work
- [ ] No Python import errors in any context
- [ ] Task creation completes successfully in all scenarios

---

## Files to Modify

### Confirmed Changes:
1. **installer/global/commands/task-create.md**
   - Remove lines 207-263 (path resolution)
   - Update line 265 (import statement)

### To Check and Potentially Update:
2. **installer/global/commands/*.md** (any with Python imports)
3. **installer/global/commands/*.py** (Python scripts)
4. **installer/global/lib/*.py** (library modules importing other libs)

---

## Testing Checklist

### Pre-Deployment Testing:
- [ ] Find all import statements: `grep -r "from installer\.global\.lib"`
- [ ] Verify all updated to `from lib.X`
- [ ] No remaining repository path resolution code
- [ ] Install script copies lib files correctly

### Post-Deployment Testing:
- [ ] Curl installation on clean macOS VM ✅
- [ ] Curl installation on Ubuntu (if possible) ✅
- [ ] Git clone installation (regression) ✅
- [ ] Conductor worktree (if using Conductor) ✅
- [ ] Claude Code execution ✅
- [ ] Shell execution ✅

---

## Risk Assessment

**Regression Risk**: 🟢 VERY LOW (<1%)

**Why Low Risk**:
- ✅ Install script already copies lib files to correct location
- ✅ Relative imports are standard Python packaging practice
- ✅ No user-facing behavior changes
- ✅ Works identically for all installation methods

**If This Breaks**:
- Symptom: Import errors at runtime
- Root cause: File not copied to lib directory
- Fix: Update install script to copy missing file

---

## Related Issues

- **Parent Review**: TASK-REV-DEF4 (comprehensive architectural review)
- **Related Fix**: TASK-FIX-A7B3 (original Python import fix task)
- **Companion Fix**: TASK-FIX-7EA8 (Priority 2 - installation validation)
- **RequireKit Equivalent**: TASK-FIX-D2C0 (same fix for RequireKit)

---

## Implementation Notes

### Why Relative Imports Work

The install script copies files as follows:
```
installer/global/lib/id_generator.py  →  ~/.agentecflow/commands/lib/id_generator.py
installer/global/commands/task-create.md  →  ~/.agentecflow/commands/task-create.md
```

When Python code in `task-create.md` executes:
- Working directory: `~/.agentecflow/commands/`
- Import: `from lib.id_generator import X`
- Python finds: `~/.agentecflow/commands/lib/id_generator.py` ✅

This works **regardless** of where the repository is (or if it even exists).

### Architecture Benefits

- ✅ **True Standalone Installation**: No repository dependency
- ✅ **Platform Agnostic**: Works on macOS, Linux, Windows WSL
- ✅ **Robust**: User can move/delete repository without breaking commands
- ✅ **Maintainable**: Standard Python packaging pattern
- ✅ **Simple**: No complex sys.path manipulation

---

## Success Metrics

After implementation:
- [ ] Zero import errors in fresh curl installations
- [ ] Zero regression reports from git clone users
- [ ] Commands work in both Claude Code and shell
- [ ] No repository location dependency
- [ ] Ready for public launch ✅

---

## Estimated Effort

- **Step 1-2**: Find and update imports - 1 hour
- **Step 3**: Update Python scripts - 30 minutes
- **Step 4**: Verify install script - 15 minutes
- **Step 5-7**: Testing (curl + git clone + contexts) - 1 hour
- **Documentation**: Update examples - 15 minutes (handled in separate task)

**Total**: 2-3 hours

---

## Next Steps After Completion

1. Mark this task complete
2. Test on fresh VM to validate fix
3. Update TASK-FIX-A7B3 status (original issue)
4. Proceed to TASK-FIX-7EA8 (Priority 2 - validation)
5. Update documentation (Priority 3)
6. Ready for public launch pending RequireKit fix

---

**CRITICAL**: This is a launch blocker. Public launch should NOT proceed until this fix is verified working on clean curl installation.
