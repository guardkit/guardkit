---
id: TASK-FIX-BDDVAL
title: Fix BDD mode RequireKit detection to check for .marker.json extension
status: backlog
created: 2025-11-30T07:45:00Z
updated: 2025-11-30T07:45:00Z
priority: high
tags: [bdd, integration, requirekit, detection, bug]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Fix BDD mode RequireKit detection to check for .marker.json extension

## Description
The BDD mode validation in taskwright checks for `~/.agentecflow/require-kit.marker` but RequireKit's installer creates `~/.agentecflow/require-kit.marker.json` (with .json extension). This causes BDD mode to incorrectly report that RequireKit is not installed even when it is.

## Evidence

**Current BDD Validation Check:**
```bash
ls ~/.agentecflow/require-kit.marker  # ❌ Wrong filename
```

**RequireKit Installer Creates:**
```bash
~/.agentecflow/require-kit.marker.json  # ✅ Correct filename
```

**Source:**
- RequireKit installer: [installer/scripts/install.sh:237](https://github.com/requirekit/require-kit/blob/main/installer/scripts/install.sh#L237)
  ```bash
  cat > "$INSTALL_DIR/$PACKAGE_NAME.marker.json" <<EOF
  ```

**Error Output:**
```
❌ ERROR: BDD mode requires RequireKit installation

BDD MODE PREREQUISITES NOT MET:

1. RequireKit Installation: ❌ NOT INSTALLED
   - Marker file not found: ~/.agentecflow/require-kit.marker
```

## Root Cause Analysis

The BDD mode validation logic needs to be updated to check for the correct filename with the `.json` extension. The validation is likely in one of these locations:

1. A slash command that validates BDD prerequisites
2. The task-work command when `--mode=bdd` is specified
3. A shared validation function for mode prerequisites

The check should support both formats for backwards compatibility:
- Legacy: `require-kit.marker` (if any old installations exist)
- Current: `require-kit.marker.json` (current installer standard)

## Acceptance Criteria
- [ ] BDD mode validation checks for `require-kit.marker.json` (primary)
- [ ] Backwards compatibility: also accept legacy `require-kit.marker` if present
- [ ] Validation correctly detects RequireKit when marker.json exists
- [ ] Error message updated to show correct filename being checked
- [ ] Consistent with taskwright's own marker format (taskwright.marker.json)

## Test Requirements
- [ ] Unit test: validation passes when require-kit.marker.json exists
- [ ] Unit test: validation passes when legacy require-kit.marker exists
- [ ] Unit test: validation fails when neither file exists
- [ ] Integration test: BDD mode proceeds when RequireKit properly detected
- [ ] Error message test: shows correct filename in error output

## Investigation Steps
1. Find BDD mode validation code:
   ```bash
   cd /Users/richwoollcott/Projects/taskwright
   grep -r "require-kit.marker" --include="*.md" --include="*.py" --include="*.sh"
   grep -r "BDD mode requires RequireKit" --include="*.md"
   ```

2. Locate the validation function (likely in):
   - `.claude/commands/task-work.md`
   - `.claude/agents/task-manager.md`
   - Any BDD-specific validation scripts

3. Check for similar detection logic for taskwright's own marker

## Implementation Notes

**Fix Approach:**
1. Update detection check to look for `.marker.json` extension
2. Add fallback check for legacy `.marker` format
3. Update error messages to reflect correct filename
4. Ensure consistency with taskwright.marker.json detection

**Example Fix:**
```bash
# Old (incorrect):
ls ~/.agentecflow/require-kit.marker

# New (correct):
if [ -f ~/.agentecflow/require-kit.marker.json ] || [ -f ~/.agentecflow/require-kit.marker ]; then
    echo "RequireKit installed"
else
    echo "RequireKit not installed"
fi
```

**Validation Patterns:**
Look for these patterns in the codebase:
- Direct file checks: `ls ~/.agentecflow/require-kit.marker`
- Python checks: `Path("~/.agentecflow/require-kit.marker").exists()`
- Bash conditionals: `[ -f ~/.agentecflow/require-kit.marker ]`

## Related Issues
- Blocks BDD workflow even when RequireKit is properly installed
- Inconsistent with installer's actual behavior
- User confusion: installation succeeds but detection fails

## Cross-Repository Dependencies
- Related to: require-kit TASK-FIX-MARKER (marker file creation bug)
- Both tasks needed for full BDD mode integration to work

## References
- RequireKit installer: https://github.com/requirekit/require-kit/blob/main/installer/scripts/install.sh#L237
- RequireKit feature detection: https://github.com/requirekit/require-kit/blob/main/installer/global/lib/feature_detection.py#L84-L88

## Test Execution Log
[Automatically populated by /task-work]
