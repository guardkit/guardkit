---
id: TASK-FIX-7EA8
title: Add post-installation validation and simplify installation model (Priority 2)
status: in_review
created: 2025-11-29T19:40:00Z
updated: 2025-11-29T20:45:00Z
priority: high
tags: [installation, validation, quality-gates, pre-launch]
complexity: 3
parent_review: TASK-REV-DEF4
depends_on: TASK-FIX-86B2
estimated_effort: 1 hour
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add Post-Installation Validation (Priority 2)

## Context

**From TASK-REV-DEF4 Review**: Priority 2 recommendation to add fail-fast validation during installation.

**Current Issue**: Installation completes successfully even if Python imports are broken. Users discover issues at runtime when running first command.

**Recommended Fix**: Add post-installation validation to catch issues during install, not at runtime.

---

## Objectives

1. **Add Python Import Validation**: Test that imports work immediately after installation
2. **Simplify Installation Model**: Remove symlink fragility (optional but recommended)
3. **Update Marker File**: Remove confusing `repo_path` field

---

## Implementation Steps

### Step 1: Add Post-Installation Validation

**File**: `installer/scripts/install.sh`

**Location**: End of script (after all installation steps, before final success message)

**Add This Code** (after line ~1500):
```bash
echo ""
echo "=========================================="
echo "Validating installation..."
echo "=========================================="

# Test Python imports work
python3 << 'EOF'
import sys
import os

# Change to installed commands directory
os.chdir(os.path.expanduser("~/.agentecflow/commands"))

# Test critical imports
try:
    from lib.id_generator import generate_task_id, validate_task_id
    print("✅ Python imports validated successfully")
except ImportError as e:
    print(f"❌ ERROR: Python import validation failed")
    print(f"   {e}")
    print("")
    print("   This is a bug in the installation script.")
    print("   Please report this issue with the error message above.")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Installation validation failed"
    echo "   Installation incomplete - please report this issue"
    exit 1
fi

echo "✅ Installation validated successfully"
echo ""
```

**Why This Helps**:
- ✅ Catches import errors during installation, not at runtime
- ✅ Provides clear error messages if something wrong
- ✅ Prevents "successful" installations that are actually broken
- ✅ Fail-fast principle: catch issues early

---

### Step 2: Simplify Installation Model (Optional)

**File**: `installer/scripts/install.sh`

**Current Issue**: Mixed installation model (copy + symlink) creates confusion

**Option A: Keep Current Approach** (if time-constrained)
- Skip this step
- Symlinks still work, just fragile

**Option B: Remove Python Script Symlinks** (recommended)

**Find lines ~1256-1383** (symlink creation for Python scripts):
```bash
echo "Creating command symlinks..."
for script in "$REPO_DIR"/installer/global/commands/*.py; do
    script_name=$(basename "$script" .py)
    ln -s "$script" "$BIN_DIR/$script_name"
done
```

**Replace with copy approach**:
```bash
echo "Installing command scripts..."
for script in "$REPO_DIR"/installer/global/commands/*.py; do
    script_name=$(basename "$script" .py)
    cp "$script" "$BIN_DIR/$script_name"
    chmod +x "$BIN_DIR/$script_name"
done
```

**Benefits**:
- ✅ No symlink fragility
- ✅ Commands work even if repository moved/deleted
- ✅ True standalone installation
- ✅ Consistent with file copying approach

**Trade-off**: Development workflow changes (need to re-install after script changes)

---

### Step 3: Update Marker File Schema

**File**: `installer/scripts/install.sh`

**Find marker file creation** (lines ~1403-1425):

**BEFORE**:
```json
{
  "package": "taskwright",
  "version": "$VERSION",
  "repo_path": "$REPO_DIR",
  "install_location": "~/.agentecflow",
  "install_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
```

**AFTER**:
```json
{
  "package": "taskwright",
  "version": "$VERSION",
  "install_location": "~/.agentecflow",
  "install_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "install_method": "$INSTALL_METHOD",
  "python_lib_path": "~/.agentecflow/commands/lib"
}
```

**Changes**:
- ❌ **Remove**: `repo_path` (confusing, suggests repository required)
- ✅ **Add**: `install_method` (curl vs git-clone, useful for diagnostics)
- ✅ **Add**: `python_lib_path` (documents where Python libs are)

**Why This Helps**:
- ✅ Clearer schema (no false repository dependency)
- ✅ Better diagnostics (know installation method)
- ✅ Documentation for Python lib location

**Note**: Set `INSTALL_METHOD` variable earlier in script:
```bash
# Near top of script, after determining curl vs clone
if [ "$IS_CURL_INSTALL" = true ]; then
    INSTALL_METHOD="curl"
else
    INSTALL_METHOD="git-clone"
fi
```

---

## Acceptance Criteria

### Must Have:
- [ ] Post-installation validation added to install script
- [ ] Validation tests Python imports work
- [ ] Clear error messages if validation fails
- [ ] Installation exits with error code if validation fails

### Should Have (if time permits):
- [ ] Python script symlinks replaced with copies
- [ ] Marker file schema updated (remove repo_path, add install_method)
- [ ] Installation method detection added

### Testing:
- [ ] Fresh curl installation passes validation
- [ ] Broken installation fails validation with clear message
- [ ] Error message helpful for debugging
- [ ] No false positives (valid install doesn't fail validation)

---

## Testing Plan

### Test 1: Validation Catches Broken Imports

**Setup**: Intentionally break imports to test validation
```bash
# After installation, corrupt a lib file
echo "broken" > ~/.agentecflow/commands/lib/id_generator.py

# Run validation manually
cd ~/.agentecflow/commands
python3 -c "from lib.id_generator import generate_task_id"

# Expected: Import error caught
```

### Test 2: Validation Passes for Good Install

```bash
# Fresh install
rm -rf ~/.agentecflow
curl -sSL .../install.sh | bash

# Expected: Validation passes, installation succeeds
# Output should show: "✅ Installation validated successfully"
```

### Test 3: Symlink Removal (if implemented)

```bash
# Install, then delete repository
curl -sSL .../install.sh | bash
rm -rf ~/Downloads/taskwright  # or wherever curl downloaded

# Test commands still work
/task-create "Test after repo deletion"

# Expected: ✅ Works (no symlink dependency)
```

---

## Risk Assessment

**Regression Risk**: 🟢 VERY LOW

**Why Low Risk**:
- Validation is additive (doesn't change existing logic)
- Runs after installation (doesn't interfere with process)
- Early exit prevents broken installations from appearing successful

**If Validation Too Strict**:
- Symptom: False positives (good install fails validation)
- Fix: Adjust validation criteria
- Mitigation: Test on multiple clean VMs first

---

## Implementation Effort

- **Step 1**: Add validation - 30 minutes
- **Step 2**: Remove symlinks (optional) - 20 minutes
- **Step 3**: Update marker file - 10 minutes
- **Testing**: Validate on clean VM - 30 minutes

**Total**: 1-1.5 hours

---

## Success Metrics

After implementation:
- [ ] Installation validation catches broken imports
- [ ] Clear error messages guide users to report issues
- [ ] Zero successful installations that are actually broken
- [ ] Fail-fast principle enforced

---

## Related Tasks

- **Depends On**: TASK-FIX-86B2 (implement relative imports first)
- **Parent Review**: TASK-REV-DEF4 (architectural review)
- **Companion**: TASK-FIX-3196 (RequireKit validation)

---

## Notes

**Priority 2 vs Priority 1**:
- Priority 1 (TASK-FIX-86B2) fixes the **broken imports**
- Priority 2 (this task) adds **validation** to prevent future breaks

**Can be deferred if time-constrained**, but recommended before launch for quality assurance.

**Order of Operations**:
1. First: Fix imports (TASK-FIX-86B2)
2. Second: Add validation (this task)
3. Third: Test on clean VM
4. Fourth: Update docs
5. Ready for launch ✅
