---
id: TASK-INST-04CA
title: Add Python script symlinks to install.sh for global command access
status: backlog
created: 2025-11-22T17:00:00Z
updated: 2025-11-22T17:00:00Z
priority: high
tags: [installation, commands, symlinks, bug-fix, infrastructure]
complexity: 5
estimated_hours: 2-3
prefix: INST
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-INST-04CA: Add Python script symlinks to install.sh for global command access

## Problem Statement

Python-based slash commands (e.g., `/agent-enhance`, `/template-create`) fail when executed from directories other than the taskwright repository because they use **relative paths** to invoke Python scripts.

**Current Behavior**:
```bash
# User in: ~/Projects/DeCUK.Mobile.MyDrive/
# Runs: /agent-enhance maui-mydrive/test-agent
# Error: Can't find ~/Projects/DeCUK.Mobile.MyDrive/installer/global/commands/agent-enhance.py
```

**Root Cause**: Commands execute `python3 installer/global/commands/agent-enhance.py` which resolves relative to **current working directory** instead of the taskwright installation.

**Impact**:
- ❌ Commands only work from taskwright repository directory
- ❌ Breaks Conductor worktree workflows
- ❌ Confusing user experience (commands available but fail)
- ✅ Claude Code's fallback masks the issue (works but inefficiently)

## Solution Overview

Create **global Python script symlinks** in `~/.agentecflow/bin/` that point to repository scripts, allowing commands to use absolute paths that work from any directory.

**Architecture**:
```
~/.agentecflow/
├── bin/              # NEW: Python script symlinks
│   ├── agent-enhance -> {REPO}/installer/global/commands/agent-enhance.py
│   ├── template-create-orchestrator -> {REPO}/.../template_create_orchestrator.py
│   └── ...
├── commands/         # Existing: Command markdown files
├── agents/           # Existing: Agent markdown files
└── templates/        # Existing: User templates

~/.claude/
├── commands -> ~/.agentecflow/commands  # Existing symlink
└── agents -> ~/.agentecflow/agents      # Existing symlink
```

**Benefits**:
- ✅ Commands work from **any directory**
- ✅ Compatible with **Conductor worktrees**
- ✅ Automatic **update propagation** (symlinks track source)
- ✅ Consistent with existing **symlink architecture**
- ✅ No duplication (single source of truth in repository)

## Acceptance Criteria

### AC1: Installation Function

- [ ] **AC1.1**: Add `setup_python_bin_symlinks()` function to install.sh after line 1238
- [ ] **AC1.2**: Function creates `~/.agentecflow/bin/` directory if it doesn't exist
- [ ] **AC1.3**: Function finds all `*.py` files in `installer/global/commands/` (excluding subdirectories)
- [ ] **AC1.4**: Function finds all `*.py` files in `installer/global/commands/lib/` (including nested)
- [ ] **AC1.5**: Function creates symlinks with names converted from underscores to hyphens (e.g., `template_create_orchestrator.py` → `template-create-orchestrator`)
- [ ] **AC1.6**: Function makes symlinks executable (`chmod +x`)
- [ ] **AC1.7**: Function provides clear user feedback (created/updated/skipped/errors)

### AC2: Integration with Install Flow

- [ ] **AC2.1**: Call `setup_python_bin_symlinks()` after `setup_claude_integration()` in main flow
- [ ] **AC2.2**: Installation completes successfully with bin/ symlinks created
- [ ] **AC2.3**: Fresh installations work correctly
- [ ] **AC2.4**: Upgrade installations work correctly (existing + new symlinks)

### AC3: Error Handling

- [ ] **AC3.1**: Gracefully handle missing scripts (warning + skip)
- [ ] **AC3.2**: Detect and report symlink name conflicts (error + skip)
- [ ] **AC3.3**: Handle permission errors (warning + continue)
- [ ] **AC3.4**: Provide summary statistics (created/updated/skipped/errors)
- [ ] **AC3.5**: Exit cleanly even if some symlinks fail

### AC4: Command Definition Updates

- [ ] **AC4.1**: Update `installer/global/commands/agent-enhance.md` with execution section
- [ ] **AC4.2**: Update `installer/global/commands/template-create.md` with execution section
- [ ] **AC4.3**: Update `installer/global/commands/template-validate.md` with execution section
- [ ] **AC4.4**: Commands use absolute symlink paths: `python3 ~/.agentecflow/bin/{name}`

### AC5: Documentation

- [ ] **AC5.1**: Update CLAUDE.md "Installation & Setup" section with bin/ directory info
- [ ] **AC5.2**: Add troubleshooting section for symlink issues
- [ ] **AC5.3**: Document symlink structure and naming conventions
- [ ] **AC5.4**: Include verification commands for post-installation

### AC6: Testing & Verification

- [ ] **AC6.1**: Fresh installation creates bin/ directory and symlinks
- [ ] **AC6.2**: Commands work from different directories (e.g., /tmp, user projects)
- [ ] **AC6.3**: Commands work in Conductor worktrees
- [ ] **AC6.4**: Symlinks are executable and point to correct targets
- [ ] **AC6.5**: Script updates propagate through symlinks
- [ ] **AC6.6**: Upgrade path preserves existing installations

## Technical Design

### 1. Bash Function for install.sh

Add to `installer/scripts/install.sh` after line 1238:

```bash
# Create symlinks for Python command scripts in ~/.agentecflow/bin/
# This allows commands to work from any directory
setup_python_bin_symlinks() {
    print_info "Setting up Python command script symlinks..."

    local BIN_DIR="$INSTALL_DIR/bin"
    local COMMANDS_DIR="$INSTALLER_DIR/global/commands"
    local COMMANDS_LIB_DIR="$INSTALLER_DIR/global/commands/lib"

    # Create bin directory if it doesn't exist
    if [ ! -d "$BIN_DIR" ]; then
        mkdir -p "$BIN_DIR"
        print_success "Created bin directory: $BIN_DIR"
    fi

    # Track statistics
    local symlinks_created=0
    local symlinks_updated=0
    local symlinks_skipped=0
    local errors=0

    # Find all Python command scripts
    local python_scripts=()

    # Find scripts in commands/ directory (exclude lib/)
    if [ -d "$COMMANDS_DIR" ]; then
        while IFS= read -r script; do
            python_scripts+=("$script")
        done < <(find "$COMMANDS_DIR" -maxdepth 1 -type f -name "*.py" 2>/dev/null)
    fi

    # Find scripts in commands/lib/ directory
    if [ -d "$COMMANDS_LIB_DIR" ]; then
        while IFS= read -r script; do
            python_scripts+=("$script")
        done < <(find "$COMMANDS_LIB_DIR" -type f -name "*.py" 2>/dev/null)
    fi

    # Check if we found any scripts
    if [ ${#python_scripts[@]} -eq 0 ]; then
        print_warning "No Python command scripts found"
        return 0
    fi

    print_info "Found ${#python_scripts[@]} Python command script(s)"

    # Create symlink for each Python script
    for script_path in "${python_scripts[@]}"; do
        local script_file=$(basename "$script_path")
        local symlink_name="${script_file%.py}"

        # Convert underscores to hyphens
        symlink_name="${symlink_name//_/-}"

        local symlink_path="$BIN_DIR/$symlink_name"

        # Check if script is readable
        if [ ! -r "$script_path" ]; then
            print_warning "Cannot read script: $script_path (skipping)"
            ((errors++))
            continue
        fi

        # Check for conflicts
        if [ -L "$symlink_path" ]; then
            local existing_target=$(readlink "$symlink_path")
            if [ "$existing_target" != "$script_path" ]; then
                print_warning "Symlink conflict: $symlink_name"
                print_warning "  Existing: $existing_target"
                print_warning "  New: $script_path"
                print_error "Cannot create symlink due to conflict"
                ((errors++))
                continue
            fi
        fi

        # Create or update symlink
        if [ -L "$symlink_path" ]; then
            local current_target=$(readlink "$symlink_path")
            if [ "$current_target" = "$script_path" ]; then
                ((symlinks_skipped++))
            else
                ln -sf "$script_path" "$symlink_path"
                chmod +x "$symlink_path" 2>/dev/null || true
                ((symlinks_updated++))
                print_info "  Updated: $symlink_name"
            fi
        elif [ -e "$symlink_path" ]; then
            print_error "Cannot create symlink: $symlink_path exists as regular file"
            ((errors++))
        else
            ln -s "$script_path" "$symlink_path"
            chmod +x "$symlink_path" 2>/dev/null || true
            ((symlinks_created++))
            print_info "  Created: $symlink_name → $(basename $script_path)"
        fi
    done

    # Summary
    echo ""
    if [ $errors -eq 0 ]; then
        print_success "Python command symlinks configured successfully"
        print_info "  Created: $symlinks_created"
        print_info "  Updated: $symlinks_updated"
        print_info "  Skipped: $symlinks_skipped"
        print_info "  Location: $BIN_DIR"
        print_info "Commands can now be executed from any directory"
    else
        print_warning "Python command symlinks configured with errors"
        print_info "  Created: $symlinks_created"
        print_info "  Updated: $symlinks_updated"
        print_info "  Skipped: $symlinks_skipped"
        print_error "  Errors: $errors"
        print_warning "Some commands may not work correctly"
    fi
}
```

### 2. Integration Point

Add function call after `setup_claude_integration()` in main installation flow (around line 1400-1500):

```bash
# After setup_claude_integration()
setup_claude_integration
setup_python_bin_symlinks  # NEW: Add this line
```

### 3. Command Definition Updates

#### agent-enhance.md

Add to end of `installer/global/commands/agent-enhance.md`:

```markdown
---

## Command Execution

```bash
# Execute via symlinked Python script
python3 ~/.agentecflow/bin/agent-enhance "$@"
```

**Note**: The command uses an absolute path to a symlinked Python script in `~/.agentecflow/bin/`. This allows the command to work from any directory, including Conductor worktrees. The symlink points to the actual script in the repository, so updates propagate automatically.
```

#### template-create.md

Add to end of `installer/global/commands/template-create.md`:

```markdown
---

## Command Execution

```bash
# Execute via symlinked Python script
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

**Note**: This command uses the orchestrator pattern with the entry point in `lib/template_create_orchestrator.py`. The symlink is created as `template-create-orchestrator` (underscores converted to hyphens for consistency).
```

#### template-validate.md

Add to end of `installer/global/commands/template-validate.md`:

```markdown
---

## Command Execution

```bash
# Execute via symlinked Python script
python3 ~/.agentecflow/bin/template-validate-orchestrator "$@"
```

**Note**: This command uses the orchestrator pattern similar to template-create. The symlink name uses hyphens for consistency with command naming conventions.
```

### 4. Documentation Updates

#### CLAUDE.md - Installation Section

Add to "Installation & Setup" section:

```markdown
**Python Command Scripts**: All Python-based command scripts are symlinked to `~/.agentecflow/bin/` for global accessibility. This allows commands to work from any directory, including Conductor worktrees. The symlinks point to the actual repository scripts, so updates propagate automatically.

**Directory Structure**:
```
~/.agentecflow/
├── bin/              # Python script symlinks
├── commands/         # Slash command definitions
├── agents/           # Agent markdown files
└── templates/        # User templates
```
```

#### CLAUDE.md - Troubleshooting Section

Add new troubleshooting section:

```markdown
## Troubleshooting

### Command Not Found

If a slash command fails with "file not found":

1. **Check symlink exists**:
   ```bash
   ls -l ~/.agentecflow/bin/agent-enhance
   ```

2. **Verify target is valid**:
   ```bash
   readlink ~/.agentecflow/bin/agent-enhance
   ```

3. **Re-run installation**:
   ```bash
   cd ~/Projects/appmilla_github/taskwright
   ./installer/scripts/install.sh
   ```

### Permission Denied

If you get permission errors:

```bash
# Make scripts executable
chmod +x ~/.agentecflow/bin/*

# Or re-run installation
./installer/scripts/install.sh
```
```

## Test Plan

### Test 1: Fresh Installation

```bash
# Remove existing installation
rm -rf ~/.agentecflow ~/.claude

# Run installer
cd ~/Projects/appmilla_github/taskwright
./installer/scripts/install.sh

# Verify bin directory created
test -d ~/.agentecflow/bin && echo "✓ Bin directory created"

# Verify symlinks exist
test -L ~/.agentecflow/bin/agent-enhance && echo "✓ agent-enhance symlink exists"
test -L ~/.agentecflow/bin/template-create-orchestrator && echo "✓ template-create-orchestrator symlink exists"

# Test from different directory
cd /tmp
/agent-enhance --help 2>&1 | grep -q "Agent Enhance" && echo "✓ Command works from /tmp"
```

**Expected**: All checks pass, commands work from any directory

### Test 2: Upgrade Installation

```bash
# Simulate existing installation
mkdir -p ~/.agentecflow/commands
mkdir -p ~/.claude
ln -s ~/.agentecflow/commands ~/.claude/commands

# Run installer
cd ~/Projects/appmilla_github/taskwright
./installer/scripts/install.sh

# Verify bin directory added
test -d ~/.agentecflow/bin && echo "✓ Bin directory added"

# Verify existing symlinks preserved
test -L ~/.claude/commands && echo "✓ Existing symlinks preserved"
```

**Expected**: New bin/ directory added without breaking existing setup

### Test 3: Conductor Worktree

```bash
# Create worktree
cd ~/Projects/appmilla_github/taskwright
git worktree add ../taskwright-test test-branch

# Test command from worktree
cd ../taskwright-test
/agent-enhance --help 2>&1 | grep -q "Agent Enhance" && echo "✓ Works in worktree"
```

**Expected**: Commands work in git worktrees

### Test 4: Script Update Propagation

```bash
# Modify source script
cd ~/Projects/appmilla_github/taskwright
echo "# Test comment" >> installer/global/commands/agent-enhance.py

# Check symlink reflects change
grep -q "Test comment" ~/.agentecflow/bin/agent-enhance && echo "✓ Updates propagate"

# Cleanup
git checkout installer/global/commands/agent-enhance.py
```

**Expected**: Changes to source visible through symlink

### Test 5: Error Handling

```bash
# Create conflict
mkdir -p ~/.agentecflow/bin
touch ~/.agentecflow/bin/agent-enhance  # Regular file

# Run installation
./installer/scripts/install.sh 2>&1 | grep -q "Cannot create symlink" && echo "✓ Conflict detected"

# Cleanup
rm ~/.agentecflow/bin/agent-enhance
```

**Expected**: Installation detects conflict and reports error

## Implementation Checklist

### Phase 1: Add Function to install.sh
- [ ] Add `setup_python_bin_symlinks()` function after line 1238
- [ ] Test function independently with sample scripts
- [ ] Verify error handling for all edge cases

### Phase 2: Integrate with Install Flow
- [ ] Add function call after `setup_claude_integration()`
- [ ] Test fresh installation
- [ ] Test upgrade installation

### Phase 3: Update Command Definitions
- [ ] Update agent-enhance.md with execution section
- [ ] Update template-create.md with execution section
- [ ] Update template-validate.md with execution section
- [ ] Verify commands work from different directories

### Phase 4: Update Documentation
- [ ] Update CLAUDE.md Installation section
- [ ] Add Troubleshooting section to CLAUDE.md
- [ ] Document symlink structure and naming

### Phase 5: Testing
- [ ] Run Test 1 (Fresh Installation)
- [ ] Run Test 2 (Upgrade Installation)
- [ ] Run Test 3 (Conductor Worktree)
- [ ] Run Test 4 (Update Propagation)
- [ ] Run Test 5 (Error Handling)

### Phase 6: Verification
- [ ] All acceptance criteria met
- [ ] All tests pass
- [ ] Documentation complete
- [ ] No regressions in existing functionality

## Files Modified

1. `installer/scripts/install.sh` - Add function and integration
2. `installer/global/commands/agent-enhance.md` - Add execution section
3. `installer/global/commands/template-create.md` - Add execution section
4. `installer/global/commands/template-validate.md` - Add execution section
5. `CLAUDE.md` - Update installation and troubleshooting sections

## Success Metrics

### Functional
- ✅ Commands work from any directory
- ✅ Compatible with Conductor worktrees
- ✅ Symlinks created for all Python scripts
- ✅ Fresh and upgrade installations succeed
- ✅ Script updates propagate automatically

### Quality
- ✅ Clear error messages for all failure scenarios
- ✅ Graceful handling of conflicts and permission issues
- ✅ Comprehensive documentation and troubleshooting
- ✅ All tests pass consistently

### User Experience
- ✅ No manual configuration required
- ✅ Works immediately after installation
- ✅ Clear feedback during installation
- ✅ Easy to verify and troubleshoot

## Related Issues

- **Original Error**: `/agent-enhance` failed from DeCUK.Mobile.MyDrive directory
- **Root Cause**: Relative path resolution in command definitions
- **Fallback**: Claude Code successfully works around issue using Task tool
- **Permanent Fix**: This task implements symlink-based global access

## Notes

### Naming Convention

Symlink names convert underscores to hyphens for consistency:
- `template_create_orchestrator.py` → `template-create-orchestrator`
- `template_validate_orchestrator.py` → `template-validate-orchestrator`
- `agent_enhance.py` → `agent-enhance`

### Backward Compatibility

This change is **fully backward compatible**:
- Existing installations work after upgrade
- Old and new patterns can coexist
- No breaking changes to existing workflows
- Migration happens automatically on re-install

### Performance

Symlinks have **zero performance overhead**:
- No file duplication
- Direct filesystem links
- Immediate update propagation
- Same as executing scripts directly

---

**Priority**: High
**Complexity**: 5/10 (Medium)
**Estimated Effort**: 2-3 hours
**Impact**: Resolves critical usability issue
**Status**: Ready for Implementation
