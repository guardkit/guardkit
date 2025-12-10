# Review Report: TASK-REV-144B

## Executive Summary

The installation script (`installer/scripts/install.sh`) is **broken** due to incomplete path updates after renaming `installer/global/` to `installer/core/`. The script contains **26 hardcoded references** to `installer/global/` paths that no longer exist, causing all installation steps that depend on these paths to fail silently or with errors.

**Severity**: Critical (blocking issue for all new installations)

**Root Cause**: Simple find-and-replace oversight during the global→core rename refactoring.

**Fix Complexity**: Low (straightforward text substitution)

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Duration**: ~15 minutes
- **Task Complexity**: 5/10

## Findings

### Finding 1: 26 Hardcoded Path References to Non-Existent Directory

**Evidence**: The following lines in `install.sh` reference `$INSTALLER_DIR/global/` which should be `$INSTALLER_DIR/core/`:

| Line | Current Path | Should Be |
|------|-------------|-----------|
| 67 | `$INSTALLER_DIR/global/templates` | `$INSTALLER_DIR/core/templates` |
| 389-390 | `$INSTALLER_DIR/global/instructions` | `$INSTALLER_DIR/core/instructions` |
| 395-396 | `$INSTALLER_DIR/global/templates` | `$INSTALLER_DIR/core/templates` |
| 409, 413, 422 | `$INSTALLER_DIR/global/lib` | `$INSTALLER_DIR/core/lib` |
| 443, 445 | `$INSTALLER_DIR/global/commands` | `$INSTALLER_DIR/core/commands` |
| 448, 452, 461, 469, 470, 475, 476, 481, 482 | `$INSTALLER_DIR/global/commands/lib` | `$INSTALLER_DIR/core/commands/lib` |
| 495-496 | `$INSTALLER_DIR/global/docs` | `$INSTALLER_DIR/core/docs` |
| 515-516 | `$INSTALLER_DIR/global/agents` | `$INSTALLER_DIR/core/agents` |
| 521 | `$INSTALLER_DIR/global/templates` | `$INSTALLER_DIR/core/templates` |
| 1328-1329 | `$INSTALLER_DIR/global/manifest.json` | `$INSTALLER_DIR/core/manifest.json` |
| 1388-1389 | `$INSTALLER_DIR/global/commands` | `$INSTALLER_DIR/core/commands` |

### Finding 2: Directory Structure Verified

**Evidence**: The rename **has been completed** on the filesystem:

```
installer/
├── core/           # EXISTS - renamed from global/
│   ├── agents/     # 44 items
│   ├── commands/   # 28 items
│   ├── docs/
│   ├── instructions/
│   ├── lib/        # 36 items
│   ├── manifest.json
│   ├── templates/
│   └── utils/
├── scripts/
│   └── install.sh  # BROKEN - still references global/
└── ...
```

There is **no `installer/global/` directory** - the rename is complete except for the install.sh references.

### Finding 3: Cascading Failures

The broken paths cause these specific error messages:

1. **"No agents found to install"** (line 515-516):
   - Cause: `$INSTALLER_DIR/global/agents` doesn't exist
   - Result: Falls through to placeholder agent creation

2. **"No Python command scripts found"** (line 1388-1389):
   - Cause: `COMMANDS_DIR="$INSTALLER_DIR/global/commands"` doesn't exist
   - Result: No Python scripts are symlinked

3. **"No module named 'lib'"** (line 1223-1232):
   - Cause: Python libraries weren't copied from `$INSTALLER_DIR/global/lib` (doesn't exist)
   - Result: Validation fails because lib modules aren't installed

### Finding 4: All Other Path Variables Are Correct

The script correctly uses `$INSTALL_DIR` (target: `~/.agentecflow/`) and `$INSTALLER_DIR` (source: repo's `installer/` directory). Only the hardcoded `global/` subdirectory references are wrong.

## Recommendations

### Option A: Find-and-Replace (Recommended)

**Effort**: 5 minutes
**Risk**: Low
**Approach**: Replace all instances of `/global/` with `/core/` in install.sh

```bash
# Preview changes
sed 's|/global/|/core/|g' installer/scripts/install.sh | diff installer/scripts/install.sh -

# Apply changes
sed -i '' 's|/global/|/core/|g' installer/scripts/install.sh
```

**Pros**:
- Fast, simple, complete fix
- No functional changes, pure path correction

**Cons**:
- None significant

### Option B: Parameterized Path Variable

**Effort**: 15 minutes
**Risk**: Low
**Approach**: Define `CORE_DIR="$INSTALLER_DIR/core"` at the top and use it throughout

```bash
# Add near line 20
CORE_DIR="$INSTALLER_DIR/core"

# Replace all $INSTALLER_DIR/global/ with $CORE_DIR/
```

**Pros**:
- Single point of change if renamed again
- Cleaner code

**Cons**:
- More changes, higher chance of typos
- Marginal benefit for a one-time fix

### Recommended Decision: Option A

Option A is the correct choice because:
1. It's a direct fix for a simple oversight
2. Lower risk of introducing new bugs
3. The rename is unlikely to happen again
4. Takes 5 minutes vs 15 minutes

## Impact Assessment

### If Fixed (Option A)
- Installation will work correctly for new users
- All 26 agent files will be properly installed
- All Python command scripts will be symlinked
- Python import validation will pass
- No changes to functionality, only path corrections

### If Not Fixed
- **All new installations fail**
- Users see confusing error messages
- Users may file bug reports or abandon the project
- Reputation damage to GuardKit

## Files Affected

| File | Action | Lines |
|------|--------|-------|
| `installer/scripts/install.sh` | Modify | 67, 389-390, 395-396, 409, 413, 422, 443, 445, 448, 452, 461, 469, 470, 475, 476, 481, 482, 495-496, 515-516, 521, 1328-1329, 1388-1389 |

## Verification Steps

After applying the fix:

```bash
# 1. Run installation
./installer/scripts/install.sh

# 2. Verify no errors in output

# 3. Check agents installed
ls -la ~/.agentecflow/agents/*.md | wc -l
# Expected: 15+ agents (not just 4 placeholders)

# 4. Check Python symlinks created
ls -la ~/.agentecflow/bin/

# 5. Run doctor
guardkit doctor
```

## Conclusion

This is a **straightforward fix** for a **critical blocking issue**. The root cause is clear, the solution is simple, and the risk is low. Recommend immediate implementation using Option A (find-and-replace).

---

**Review Completed**: 2025-12-10
**Reviewer**: Decision Analysis Agent
**Status**: REVIEW_COMPLETE
