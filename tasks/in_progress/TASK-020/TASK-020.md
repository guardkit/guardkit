---
id: TASK-020
title: Complete Taskwright Rebrand (agentecflow → taskwright)
status: in_review
created: 2025-11-02T00:00:00Z
updated: 2025-11-02T16:30:00Z
priority: high
complexity: 3
estimated_hours: 2
actual_hours: 1.5
tags: [branding, documentation, cli, taskwright]
epic: null
feature: installation
dependencies: [TASK-019]
blocks: [TASK-021]
replaces: [TASK-033]
---

# TASK-020: Complete Taskwright Rebrand

## Objective

Complete the rebrand from "Agentecflow" / "agentecflow init" to "Taskwright" / "taskwright init" across all user-facing documentation, output messages, and CLI commands.

**Note**: This REPLACES archived task TASK-033 (which was incomplete).

## Problem Statement

**Current State** (from user's init output):
```
╔════════════════════════════════════════════════════════╗
║         Agentic Flow Initialization                    ║  ← Wrong branding!
║         Template: dotnet-microservice                  ║
╚════════════════════════════════════════════════════════╝

✅ Agentic Flow successfully initialized!                  ← Wrong branding!

📚 Documentation: https://github.com/appmilla/agentecflow  ← Wrong repo!
```

**Expected State**:
```
╔════════════════════════════════════════════════════════╗
║         Taskwright Initialization                      ║  ← Correct!
║         Template: dotnet-microservice                  ║
╚════════════════════════════════════════════════════════╝

✅ Taskwright successfully initialized!                    ← Correct!

📚 Documentation: https://github.com/appmilla/taskwright   ← Correct!
```

## Scope

### What CHANGES (User-Facing)
- ✅ Product name: "Agentecflow" → "Taskwright"
- ✅ CLI command: `agentecflow init` → `taskwright init`
- ✅ Output messages: All references to "Agentecflow"
- ✅ Documentation: README, CLAUDE.md, guides
- ✅ Repository references

### What STAYS THE SAME (Internal)
- ✅ Configuration folder: `.agentecflow/` (keep this)
- ✅ Global installation: `~/.agentecflow/` (keep this)
- ✅ Internal variable names (unless user-facing)
- ✅ File paths and folder structure

**Rationale**: The configuration folders stay `.agentecflow` for backward compatibility and because "agentecflow" represents the methodology, while "taskwright" is the product name.

## Files to Modify

### 1. CLI Commands (installer/scripts/)

#### install.sh
**Location**: Lines 472-537 (CLI command creation)

**Changes**:
```bash
# Create taskwright-init command (was agentec-init)
cat > "$INSTALL_DIR/bin/taskwright-init" << 'EOF'
#!/bin/bash

# Taskwright Project Initialization
# Primary command for initializing projects

# ... implementation ...
EOF

chmod +x "$INSTALL_DIR/bin/taskwright-init"

# Create main command
cat > "$INSTALL_DIR/bin/taskwright" << 'EOF'
#!/bin/bash

# Taskwright CLI
# Main command-line interface

# ... implementation ...
EOF

chmod +x "$INSTALL_DIR/bin/taskwright"

# Create shorthand aliases
ln -sf "$INSTALL_DIR/bin/taskwright" "$INSTALL_DIR/bin/tw"
ln -sf "$INSTALL_DIR/bin/taskwright-init" "$INSTALL_DIR/bin/twi"
```

#### init-project.sh
**Location**: Lines 36-43 (header), 370-462 (output messages)

**Changes**:
```bash
print_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         Taskwright Initialization                      ║${NC}"  # Changed
    echo -e "${BLUE}║         Template: ${BOLD}$(printf '%-20s' "$TEMPLATE")${NC}${BLUE}         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# In print_next_steps():
echo -e "${GREEN}✅ Taskwright successfully initialized!${NC}"  # Changed
echo ""
echo -e "${BOLD}Next Steps:${NC}"
echo "  1. Use taskwright commands to manage tasks"  # Changed
# ... etc
```

### 2. Documentation

#### Root Files
- **CLAUDE.md** (lines 1-50): Update product description
- **README.md**: Complete rewrite with taskwright branding

#### Guides (docs/guides/)
- `agentecflow-lite-workflow.md` → Rename to `taskwright-workflow.md`
- Update all command examples
- Update all product references

### 3. Shell Integration

#### install.sh - Shell Config
**Location**: Lines 836-856

**Changes**:
```bash
cat >> "$shell_config" << 'EOF'

# Taskwright
export PATH="$HOME/.agentecflow/bin:$PATH"
export AGENTECFLOW_HOME="$HOME/.agentecflow"
# Note: Config folder stays .agentecflow for methodology compatibility

# Taskwright completions (bash)
if [ -f "$HOME/.agentecflow/completions/taskwright.bash" ]; then
    source "$HOME/.agentecflow/completions/taskwright.bash"
fi
EOF
```

### 4. Help Text & Messages

All user-facing help text needs updating:
- Command descriptions
- Usage examples
- Error messages
- Success messages
- Documentation links

## Implementation Plan

### Phase 1: CLI Commands (30 min)
1. Update `install.sh` - Create `taskwright` and `taskwright-init` commands
2. Update `init-project.sh` - Change all output messages
3. Test: Commands work with new names

### Phase 2: Documentation (45 min)
1. Update `CLAUDE.md` - Product description and examples
2. Update `README.md` - Complete rewrite
3. Rename `agentecflow-lite-workflow.md` → `taskwright-workflow.md`
4. Update all guide documents
5. Search and replace remaining references

### Phase 3: Shell Integration (15 min)
1. Update shell config generation
2. Update completion scripts
3. Test shell integration

### Phase 4: Testing (30 min)
1. Clean install test
2. Init test with all templates
3. Documentation accuracy review
4. Link verification

## Search & Replace Strategy

### Find All References
```bash
# Find agentecflow init references
grep -r "agentecflow init" --include="*.md" --include="*.sh" .

# Find Agentecflow product references
grep -r "Agentecflow" --include="*.md" --include="*.sh" .

# Find agentec-init references
grep -r "agentec-init" --include="*.md" --include="*.sh" .
```

### Replace Pattern
```bash
# Command name
agentecflow init → taskwright init
agentec-init → taskwright-init

# Product name
Agentecflow → Taskwright
agentecflow → taskwright (in prose)

# Keep config paths
.agentecflow/ → .agentecflow/ (NO CHANGE)
~/.agentecflow/ → ~/.agentecflow/ (NO CHANGE)
AGENTECFLOW_HOME → AGENTECFLOW_HOME (NO CHANGE - internal)
```

### Exceptions (DO NOT CHANGE)
- `.agentecflow/` folder paths
- `~/.agentecflow/` installation paths
- `AGENTECFLOW_HOME` environment variable
- Historical/archived task references
- Internal variable names (unless user-facing)

## Testing Strategy

### Test 1: CLI Commands
```bash
# After install
taskwright --help
taskwright init --help
taskwright-init --help
tw --help  # shorthand
twi --help  # shorthand

# All should show "Taskwright" branding
```

### Test 2: Installation Flow
```bash
# Clean install
./installer/scripts/install.sh

# Check output for "Taskwright" branding
# Check shell config has taskwright references
```

### Test 3: Init Flow
```bash
# Test init with new command
taskwright init dotnet-microservice

# Verify all output shows "Taskwright"
# Verify .agentecflow/ folder still used (internal)
```

### Test 4: Documentation Consistency
```bash
# No remaining agentecflow init references (except archived)
! grep -r "agentecflow init" --include="*.md" . | grep -v "archive\|archived"

# Taskwright appears in key docs
grep -q "Taskwright" README.md
grep -q "Taskwright" CLAUDE.md
grep -q "taskwright init" docs/guides/*.md
```

### Test 5: Links & References
```bash
# All docs links point to taskwright repo
grep -r "github.com.*taskwright" --include="*.md" .

# No broken links
# ... manual verification ...
```

## Acceptance Criteria

### CLI Commands
- [ ] `taskwright` command exists and works
- [ ] `taskwright init` command exists and works
- [ ] `taskwright-init` command exists and works
- [ ] Shorthands `tw` and `twi` work
- [ ] Help text shows "Taskwright" branding
- [ ] Error messages use "Taskwright"

### Documentation
- [ ] README.md uses "Taskwright" throughout
- [ ] CLAUDE.md uses "Taskwright" for product name
- [ ] Workflow guide renamed and updated
- [ ] All command examples use `taskwright init`
- [ ] No remaining "agentecflow init" in active docs

### Shell Integration
- [ ] Shell config mentions "Taskwright" in comments
- [ ] Commands added to PATH correctly
- [ ] Completions updated (if exist)

### Configuration
- [ ] `.agentecflow/` folder still used (internal)
- [ ] `~/.agentecflow/` installation still used
- [ ] Documentation explains folder naming

### Testing
- [ ] Clean install shows "Taskwright"
- [ ] Init output shows "Taskwright"
- [ ] All templates work with new commands
- [ ] Documentation links verified
- [ ] No broken references

## Migration Notes for Users

**No Action Required**:
- Existing installations continue to work
- Configuration folders stay the same (`.agentecflow/`)
- Only command names change

**Optional Upgrade**:
- Reinstall to get new command names
- Old commands (if present) continue to work via symlinks

## Definition of Done

- [ ] CLI commands renamed and working
- [ ] All user-facing messages updated
- [ ] Documentation rebranded
- [ ] Shell integration updated
- [ ] Tests passing
- [ ] No broken links
- [ ] Migration guide written (if needed)
- [ ] Backward compatibility verified

## Related Tasks

- **TASK-019**: Remove epic/feature/portfolio (must complete first)
- **TASK-021**: Update init output (this unblocks that)
- **TASK-033**: Archived (replaced by this task)

## Notes

- **Medium effort**: ~2 hours total
- **High impact**: User-facing product identity
- **Low risk**: Mostly text changes
- **Backward compatible**: Config folders unchanged

---

**Status**: Ready for implementation
**Priority**: HIGH (product branding)
**Estimated Time**: 2 hours
**Dependencies**: TASK-019 (remove require-kit folders first)
