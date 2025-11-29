---
id: TASK-FIX-CCCE
title: Remove duplicate marker file creation (cosmetic fix)
status: completed
created: 2025-11-29T21:15:00Z
updated: 2025-11-29T21:30:00Z
completed: 2025-11-29T21:35:00Z
priority: low
tags: [installation, cleanup, cosmetic, post-launch-ok]
complexity: 1
related_review: TASK-REV-DEF4
estimated_effort: 1 minute
actual_effort: 1 minute
completed_location: tasks/completed/TASK-FIX-CCCE/
test_results:
  status: not_required
  coverage: null
  last_run: null
---

# Task: Remove Duplicate Marker File Creation (Cosmetic Fix)

## Context

**From VM Testing**: Installation creates two marker files instead of one:
- `taskwright.marker.json` ✅ (correct, new format)
- `taskwright.manifest.json` ❌ (legacy, should not exist)

**Impact**: Minor cosmetic issue - doesn't break functionality, just confusing to users

**Priority**: LOW - Can be fixed post-launch

---

## Problem

File: `installer/scripts/install.sh` lines 1539-1542

```bash
# Line 1539: Creates manifest file (LEGACY)
create_package_marker

# Line 1542: Creates marker file (NEW)
create_marker_file
```

Both functions are called, creating two files in `~/.agentecflow/`:
1. `taskwright.manifest.json` (legacy format - shouldn't exist)
2. `taskwright.marker.json` (new format - correct)

---

## Fix

**Recommended: Option 1 - Comment Out Legacy Call**

File: `installer/scripts/install.sh`
Line: 1539

### Change Required

```bash
# BEFORE (line 1539):
create_package_marker

# AFTER:
# create_package_marker  # DEPRECATED - using create_marker_file instead
```

**Why Option 1**:
- Keeps function definition for reference
- Single line change (1 minute)
- Safest approach
- Maintains git history

---

## Alternative: Option 2 (More Thorough)

Delete the entire `create_package_marker()` function:
- Delete lines 1267-1276 (function definition)
- Delete line 1539 (function call)

**Why Not Recommended**:
- More changes = more risk
- Loses historical context
- Unnecessary for cosmetic fix

---

## Acceptance Criteria

- [ ] Only ONE marker file created after installation: `taskwright.marker.json`
- [ ] No `taskwright.manifest.json` file created
- [ ] Installation still completes successfully
- [ ] All commands still work correctly

---

## Implementation Steps

### Step 1: Edit Install Script

```bash
cd ~/Projects/appmilla_github/taskwright

# Open install script
# File: installer/scripts/install.sh
# Line: 1539
```

### Step 2: Comment Out Line 1539

```bash
# Find line 1539 in installer/scripts/install.sh:
create_package_marker

# Change to:
# create_package_marker  # DEPRECATED - using create_marker_file instead
```

### Step 3: Verify Function Still Documented

Check line 1270 has the deprecation message:
```bash
print_info "Skipping legacy marker creation (using JSON marker instead)..."
```

This message now aligns with the actual behavior (function not called).

---

## Testing

### Test 1: Clean Installation

```bash
# Clean environment
rm -rf ~/.agentecflow

# Install via curl
curl -sSL https://raw.githubusercontent.com/taskwright-dev/taskwright/main/installer/scripts/install.sh | bash

# Check marker files
ls ~/.agentecflow/*.json

# Expected output (only ONE file):
# taskwright.marker.json

# Should NOT see:
# taskwright.manifest.json
```

### Test 2: Verify Installation Works

```bash
# After clean install, test commands work:
taskwright --version
# Expected: Shows version

/task-create "Test after marker fix"
# Expected: Task created successfully
```

### Test 3: Verify Marker File Content

```bash
cat ~/.agentecflow/taskwright.marker.json

# Expected: Valid JSON with:
# - package: "taskwright"
# - version
# - install_location
# - install_date
# - install_method
```

---

## Risk Assessment

**Regression Risk**: 🟢 ZERO

**Why Zero Risk**:
- ✅ Only commenting out a call to a legacy function
- ✅ No functional code changed
- ✅ Installation already works fine with both files
- ✅ Removing duplicate doesn't affect anything
- ✅ The function was already marked as "skipped" in logs

**If This Breaks**:
- Symptom: Installation fails (extremely unlikely)
- Fix: Uncomment line 1539 (instant rollback)

---

## Implementation Time

**Total**: 1 minute
- Edit file: 30 seconds
- Commit: 30 seconds

---

## Success Metrics

After implementation:
- [ ] Zero duplicate marker files in fresh installations
- [ ] Installation logs show "Skipping legacy marker creation"
- [ ] Only `taskwright.marker.json` exists in `~/.agentecflow/`
- [ ] All commands work identically

---

## Related Tasks

- **Parent Review**: TASK-REV-DEF4 (comprehensive architectural review)
- **Priority 1 Companion**: TASK-FIX-86B2 (relative imports - launch blocker)
- **Priority 2 Companion**: TASK-FIX-7EA8 (installation validation)

---

## Priority Justification

**Why LOW Priority**:
- ✅ Installation works correctly with both files
- ✅ Commands work correctly
- ✅ Only cosmetic/UX issue
- ✅ Not user-facing (users rarely look in `~/.agentecflow/`)
- ✅ Doesn't affect functionality

**When to Fix**:
- After Priority 1 tasks (TASK-FIX-86B2, TASK-FIX-D2C0)
- After Priority 2 tasks (TASK-FIX-7EA8, TASK-FIX-3196)
- Before or after launch - doesn't matter

**Can be deferred to post-launch** without any impact.

---

## Notes

### Why Two Files Were Created

**Historical Context**:
1. Originally used `taskwright.manifest.json` (legacy format)
2. Later migrated to `taskwright.marker.json` (new JSON format)
3. Added deprecation message (line 1270)
4. But forgot to remove function call (line 1539)

**Result**: Both files created, causing confusion

### Documentation Already Updated

Line 1270 says:
```bash
print_info "Skipping legacy marker creation (using JSON marker instead)..."
```

But line 1539 still calls the function! This fix aligns code with documentation.

---

## Git Commit Message

```
fix: remove duplicate legacy marker file creation

- Comment out create_package_marker call (line 1539)
- Aligns with deprecation message on line 1270
- Only taskwright.marker.json created now
- Cosmetic fix, no functional impact

Refs: TASK-FIX-CCCE, TASK-REV-DEF4
```

---

**STOP HERE** - Task created. Ready for `/task-work TASK-FIX-CCCE` when prioritized.
