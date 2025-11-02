---
id: TASK-019
title: Remove Epic/Feature/Portfolio Folders from Taskwright Init
status: backlog
created: 2025-11-02T00:00:00Z
priority: high
complexity: 2
estimated_hours: 1
tags: [init, cleanup, taskwright, require-kit-split]
epic: null
feature: installation
dependencies: []
blocks: [TASK-020]
---

# TASK-019: Remove Epic/Feature/Portfolio Folders from Taskwright Init

## Objective

Remove epic, feature, and portfolio folder creation from `init-project.sh` to align with taskwright's lightweight task-only focus. These are require-kit features and should not be in taskwright.

## Problem Statement

**Current Behavior** (from user's `taskwright init dotnet-microservice` output):
```
📁 Project structure created:
   tasks/         - Task management (backlog → in_progress → completed)
   epics/         - Epic management (active, archived)       ← require-kit!
   features/      - Feature management (active, archived)    ← require-kit!
   portfolio/     - Portfolio metrics and reports            ← require-kit!
   docs/          - Documentation (adr, state)
   tests/         - Test organization (unit, integration, e2e)
   src/           - Source code
```

**Expected Behavior** (taskwright is lightweight):
```
📁 Project structure created:
   .claude/       - Taskwright configuration
   docs/          - Documentation (ADRs, guides)
   tasks/         - Task management (backlog → in_progress → completed)
```

**Rationale**:
- **Taskwright**: Lightweight task workflow system (create → work → complete)
- **Require-kit**: Full requirements management (EARS, BDD, epics, features, portfolio)
- These are two separate products now!

## Context

From the product split:
- **Taskwright** = Tasks + Quality Gates + Templates
- **Require-kit** = Requirements + EARS + BDD + Epics + Features + Portfolio

Taskwright users should NOT see epic/feature/portfolio folders - those are only for users who install BOTH taskwright + require-kit together.

## Acceptance Criteria

- [ ] Remove epic folder creation from init-project.sh
- [ ] Remove feature folder creation from init-project.sh
- [ ] Remove portfolio folder creation from init-project.sh
- [ ] Keep tasks folder creation (core to taskwright)
- [ ] Keep docs folder creation (ADRs, guides)
- [ ] Keep .claude folder creation (configuration)
- [ ] Update folder structure output message
- [ ] Test: init should only create minimal folders
- [ ] Backward compatible (existing projects unaffected)

## Files to Modify

### 1. init-project.sh - Project Structure Creation

**Location**: `installer/scripts/init-project.sh:148-175`

**Current Code**:
```bash
create_project_structure() {
    print_info "Creating project structure..."

    # Always create .claude at root
    mkdir -p .claude/{agents,commands,hooks,templates,stacks}

    # Always create docs at root
    mkdir -p docs/{adr,state}

    # Create task management structure
    mkdir -p tasks/{backlog,in_progress,in_review,blocked,completed}

    # Create epic management structure (require-kit feature!)
    mkdir -p epics/{active,archived}

    # Create feature management structure (require-kit feature!)
    mkdir -p features/{active,archived}

    # Create portfolio structure (require-kit feature!)
    mkdir -p portfolio/{metrics,reports}

    # Handle test directory based on project type
    # ... test directory handling ...
}
```

**Updated Code**:
```bash
create_project_structure() {
    print_info "Creating project structure..."

    # Always create .claude at root
    mkdir -p .claude/{agents,commands,hooks,templates,stacks}

    # Always create docs at root
    mkdir -p docs/{adr,state}

    # Create task management structure (core taskwright feature)
    mkdir -p tasks/{backlog,in_progress,in_review,blocked,completed}

    # REMOVED: epic/feature/portfolio (these are require-kit features)
    # If user installs require-kit, it will create these folders

    # Handle test directory based on project type
    # ... test directory handling continues unchanged ...

    print_success "Project structure created"
}
```

### 2. init-project.sh - Output Message Update

**Location**: `installer/scripts/init-project.sh:370-462` (print_next_steps function)

**Current Output**:
```
📁 Project structure created:
   tasks/         - Task management (backlog → in_progress → completed)
   epics/         - Epic management (active, archived)
   features/      - Feature management (active, archived)
   portfolio/     - Portfolio metrics and reports
   docs/          - Documentation (adr, state)
```

**Updated Output**:
```
📁 Project structure created:
   .claude/       - Taskwright configuration
   docs/          - Documentation and ADRs
   tasks/         - Task workflow (backlog → in_progress → in_review → blocked → completed)
```

## Implementation

### Step 1: Remove Folder Creation

```bash
# Edit init-project.sh
# Line ~158-165: Remove these lines
# mkdir -p epics/{active,archived}
# mkdir -p features/{active,archived}
# mkdir -p portfolio/{metrics,reports}
```

### Step 2: Update Output Message

```bash
# Edit init-project.sh
# Line ~380-390: Simplify folder list in output
# Remove references to epics, features, portfolio
```

### Step 3: Test Folder Creation

```bash
# Test init creates minimal folders
cd /tmp/test-taskwright
mkdir test-project && cd test-project
~/.agentecflow/scripts/init-project.sh default

# Verify folder structure
tree -L 1
# Expected:
# .
# ├── .claude/
# ├── docs/
# └── tasks/

# Should NOT see:
# ├── epics/      ← Should not exist
# ├── features/   ← Should not exist
# └── portfolio/  ← Should not exist
```

## Testing Strategy

### Test 1: Minimal Folder Creation
```bash
# Initialize new project
cd /tmp/taskwright-test
mkdir test && cd test
taskwright init default

# Check folders
folders=$(ls -d */ 2>/dev/null | tr '\n' ' ')

# Verify expected folders exist
[[ "$folders" == *".claude/"* ]] && echo "✓ .claude/ created"
[[ "$folders" == *"docs/"* ]] && echo "✓ docs/ created"
[[ "$folders" == *"tasks/"* ]] && echo "✓ tasks/ created"

# Verify require-kit folders do NOT exist
[[ "$folders" != *"epics/"* ]] && echo "✓ epics/ not created"
[[ "$folders" != *"features/"* ]] && echo "✓ features/ not created"
[[ "$folders" != *"portfolio/"* ]] && echo "✓ portfolio/ not created"
```

### Test 2: Output Message Accuracy
```bash
# Run init and capture output
output=$(taskwright init default 2>&1)

# Verify output mentions only taskwright folders
echo "$output" | grep -q "tasks/" && echo "✓ Mentions tasks/"
echo "$output" | grep -q "docs/" && echo "✓ Mentions docs/"

# Verify output does NOT mention require-kit folders
! echo "$output" | grep -q "epics/" && echo "✓ Does not mention epics/"
! echo "$output" | grep -q "features/" && echo "✓ Does not mention features/"
! echo "$output" | grep -q "portfolio/" && echo "✓ Does not mention portfolio/"
```

### Test 3: All Templates
```bash
# Test each template
for template in default react python typescript-api dotnet-microservice maui-appshell maui-navigationpage; do
    echo "Testing template: $template"
    cd /tmp/test-$template
    mkdir test && cd test
    taskwright init $template

    # Verify no require-kit folders
    [ ! -d epics ] && [ ! -d features ] && [ ! -d portfolio ] && echo "  ✓ $template: No require-kit folders"
done
```

## Definition of Done

- [ ] Epic folder creation removed from init-project.sh
- [ ] Feature folder creation removed from init-project.sh
- [ ] Portfolio folder creation removed from init-project.sh
- [ ] Output message updated (no epic/feature/portfolio references)
- [ ] Tasks, docs, .claude folders still created correctly
- [ ] All templates tested (no require-kit folders created)
- [ ] Documentation updated if needed
- [ ] Backward compatibility verified (existing projects unaffected)

## Related Tasks

- **TASK-018**: Audit agents (must complete first)
- **TASK-020**: Complete rebrand (this unblocks that)
- **TASK-033**: Original rebrand task (archived, replaced by TASK-020)

## Notes

- **Quick Fix**: ~30 minutes
- **Low Risk**: Only removes folder creation (no breaking changes)
- **Clean Separation**: Aligns with taskwright vs require-kit split
- **User Impact**: Users will see cleaner, simpler project structure

---

**Status**: Ready for implementation
**Priority**: HIGH (product clarity)
**Estimated Time**: 1 hour
**Dependencies**: None (can start immediately)
