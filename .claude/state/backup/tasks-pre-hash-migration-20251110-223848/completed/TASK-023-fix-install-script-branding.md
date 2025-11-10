---
id: TASK-023
title: Fix Remaining Branding Issues in install.sh
status: completed
created: 2025-11-02T17:00:00Z
completed: 2025-11-02T17:30:00Z
priority: high
complexity: 1
estimated_hours: 0.25
actual_hours: 0.25
tags: [branding, installer, taskwright, quick-fix]
epic: null
feature: installation
dependencies: [TASK-020]
blocks: []
---

# TASK-023: Fix Remaining Branding Issues in install.sh

## Objective

Fix all remaining "agentecflow" and "agentec-init" references in `install.sh` that were missed in TASK-020 rebrand.

## Problem Statement

**From User's Install Output:**
```
╔════════════════════════════════════════════════════════╗
║         Agentecflow Installation System                ║  ← Should be "Taskwright"
║         Version: 2.0.0                                 ║
╚════════════════════════════════════════════════════════╝

ℹ Installing Agentecflow to /Users/...                    ← Should be "Taskwright"
...
✓ All agentecflow commands now available in Claude Code!   ← Should be "taskwright"
...
✅ Agentecflow installation complete!                       ← Should be "Taskwright"
...
Available Commands:
  • agentec-init [template]  - Initialize a project        ← Should be "taskwright-init"
  • agentecflow init         - Alternative initialization  ← Should be "taskwright init"
  • af                       - Short for agentecflow       ← Should be "tw (taskwright)"
  • ai                       - Short for agentec-init      ← Should be "twi (taskwright-init)"
...
Next Steps:
  3. Run: agentec-init dotnet-microservice                ← Should be "taskwright-init"
```

**Root Cause:**
TASK-020 updated `init-project.sh` but missed the main `install.sh` script completely.

## Files to Modify

### install.sh - All User-Facing Messages

**Location**: `installer/scripts/install.sh`

#### Change 1: Header (Lines 37-42)
```bash
# CURRENT
print_header() {
    echo ""
    print_message "$BLUE" "╔════════════════════════════════════════════════════════╗"
    print_message "$BLUE" "║         Agentecflow Installation System                ║"
    print_message "$BLUE" "║         Version: $AGENTECFLOW_VERSION                  ║"
    print_message "$BLUE" "╚════════════════════════════════════════════════════════╝"
    echo ""
}

# FIXED
print_header() {
    echo ""
    print_message "$BLUE" "╔════════════════════════════════════════════════════════╗"
    print_message "$BLUE" "║         Taskwright Installation System                 ║"
    print_message "$BLUE" "║         Version: $AGENTECFLOW_VERSION                  ║"
    print_message "$BLUE" "╚════════════════════════════════════════════════════════╝"
    echo ""
}
```

#### Change 2: Installing Message (Line ~1251)
```bash
# CURRENT
print_info "Installing Agentecflow to $INSTALL_DIR"

# FIXED
print_info "Installing Taskwright to $INSTALL_DIR"
```

#### Change 3: Claude Code Integration Message (Line ~1191)
```bash
# CURRENT
print_success "All agentecflow commands now available in Claude Code!"

# FIXED
print_success "All taskwright commands now available in Claude Code!"
```

#### Change 4: Completion Header (Lines ~1043-1045)
```bash
# CURRENT
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Agentecflow installation complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"

# FIXED
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Taskwright installation complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
```

#### Change 5: Available Commands (Lines ~1063-1068)
```bash
# CURRENT
echo -e "${BOLD}Available Commands:${NC}"
echo "  • agentec-init [template]  - Initialize a project"
echo "  • agentecflow init         - Alternative initialization"
echo "  • agentecflow doctor       - Check system health"
echo "  • af                       - Short for agentecflow"
echo "  • ai                       - Short for agentec-init"

# FIXED
echo -e "${BOLD}Available Commands:${NC}"
echo "  • taskwright-init [template]  - Initialize a project"
echo "  • taskwright init             - Alternative initialization"
echo "  • taskwright doctor           - Check system health"
echo "  • tw                          - Short for taskwright"
echo "  • twi                         - Short for taskwright-init"
```

#### Change 6: Next Steps (Line ~1115)
```bash
# CURRENT
echo "  3. Run: agentec-init dotnet-microservice"

# FIXED
echo "  3. Run: taskwright-init dotnet-microservice"
```

#### Change 7: Comments (Multiple locations)
```bash
# Find all comment references
grep -n "Agentecflow" installer/scripts/install.sh

# Update comments like:
# Line 3: # Agentecflow - Global Installation Script
# TO: # Taskwright - Global Installation Script

# Line 39: ║         Agentecflow Installation System                ║
# Already covered above
```

## Quick Fix Script

```bash
#!/bin/bash
# Quick fix for install.sh branding

cd ~/Projects/appmilla_github/taskwright

# Backup
cp installer/scripts/install.sh installer/scripts/install.sh.backup

# Find and replace - user-facing text only
sed -i '' 's/Agentecflow Installation System/Taskwright Installation System/g' installer/scripts/install.sh
sed -i '' 's/Installing Agentecflow to/Installing Taskwright to/g' installer/scripts/install.sh
sed -i '' 's/All agentecflow commands/All taskwright commands/g' installer/scripts/install.sh
sed -i '' 's/Agentecflow installation complete/Taskwright installation complete/g' installer/scripts/install.sh
sed -i '' 's/agentec-init \[template\]/taskwright-init [template]/g' installer/scripts/install.sh
sed -i '' 's/agentecflow init/taskwright init/g' installer/scripts/install.sh
sed -i '' 's/agentecflow doctor/taskwright doctor/g' installer/scripts/install.sh
sed -i '' 's/Short for agentecflow/Short for taskwright/g' installer/scripts/install.sh
sed -i '' 's/Short for agentec-init/Short for taskwright-init/g' installer/scripts/install.sh
sed -i '' 's/Run: agentec-init/Run: taskwright-init/g' installer/scripts/install.sh

# Update shorthand aliases in output
sed -i '' 's/  • af  /  • tw  /g' installer/scripts/install.sh
sed -i '' 's/  • ai  /  • twi /g' installer/scripts/install.sh

# Verify changes
echo "Changes made:"
git diff installer/scripts/install.sh | grep "^[-+]" | head -20

# Test install (dry run if possible)
echo ""
echo "Test the installer manually to verify all output"
```

## What NOT to Change

**Keep these INTERNAL references as-is:**
- `$INSTALL_DIR` = `$HOME/.agentecflow` (config folder name)
- `AGENTECFLOW_VERSION` (variable name)
- `AGENTECFLOW_HOME` (environment variable)
- Directory paths: `.agentecflow/`, `~/.agentecflow/`
- Comments referring to internal structure

**Why?**
- Backward compatibility
- Config folder represents the methodology name
- Only user-facing text should change

## Expected Output After Fix

```
╔════════════════════════════════════════════════════════╗
║         Taskwright Installation System                 ║
║         Version: 2.0.0                                 ║
╚════════════════════════════════════════════════════════╝

ℹ Installing Taskwright to /Users/richwoollcott/.agentecflow
...
✓ All taskwright commands now available in Claude Code!
...
✅ Taskwright installation complete!
...
Available Commands:
  • taskwright-init [template]  - Initialize a project
  • taskwright init             - Alternative initialization
  • taskwright doctor           - Check system health
  • tw                          - Short for taskwright
  • twi                         - Short for taskwright-init
...
Next Steps:
  3. Run: taskwright-init dotnet-microservice
```

## Testing Strategy

### Test 1: Visual Inspection
```bash
# Run installer and capture output
./installer/scripts/install.sh 2>&1 | tee install-output.txt

# Check for old branding
grep -i "agentecflow" install-output.txt | grep -v ".agentecflow"  # Should be empty
grep -i "agentec-init" install-output.txt  # Should be empty

# Check for new branding
grep -i "taskwright" install-output.txt  # Should have multiple matches
grep -i "taskwright-init" install-output.txt  # Should have multiple matches
```

### Test 2: Full Install
```bash
# Clean test environment
rm -rf ~/.agentecflow ~/.claude

# Run installer
cd ~/Projects/appmilla_github/taskwright
./installer/scripts/install.sh

# Verify commands created
which taskwright
which taskwright-init
which tw
which twi

# Verify old commands NOT created
! which agentec-init || echo "ERROR: Old command still exists"
! which agentecflow || echo "ERROR: Old command still exists"
```

### Test 3: Help Text
```bash
# Check command help shows new branding
taskwright --help | grep -i "taskwright"
taskwright-init --help | grep -i "taskwright"

# Should NOT show old branding
! taskwright --help | grep -i "agentecflow"
! taskwright-init --help | grep -i "agentec-init"
```

## Acceptance Criteria

- [ ] Header shows "Taskwright Installation System"
- [ ] Installing message says "Installing Taskwright to..."
- [ ] Completion message says "✅ Taskwright installation complete!"
- [ ] Available commands list shows "taskwright-init", "taskwright init", etc.
- [ ] Shorthand aliases shown as "tw" and "twi"
- [ ] Next steps reference "taskwright-init"
- [ ] No user-facing "agentecflow" or "agentec-init" references remain
- [ ] Internal paths (`.agentecflow/`) unchanged
- [ ] Full install test passes
- [ ] Visual output inspection passes

## Definition of Done

- [ ] All user-facing text updated to "taskwright"
- [ ] Command examples use "taskwright-init"
- [ ] Shorthand aliases updated (tw, twi)
- [ ] Internal config paths unchanged (`.agentecflow/`)
- [ ] Install test shows correct branding
- [ ] No "agentecflow init" or "agentec-init" in user output
- [ ] Git commit with clear message

## Notes

- **Priority**: High (user-facing branding issue)
- **Complexity**: 1/10 (simple find/replace)
- **Time**: 15 minutes
- **Risk**: Very low (text-only changes)
- **Testing**: Visual inspection sufficient

---

**Status**: Ready for implementation
**Priority**: HIGH (completes TASK-020 rebrand)
**Estimated Time**: 15 minutes
**Dependencies**: TASK-020 (partially complete)
