---
id: TASK-021
title: Update Init Output to Show Taskwright Workflow Only
status: completed
created: 2025-11-02T00:00:00Z
completed: 2025-11-02T10:30:00Z
priority: high
complexity: 2
estimated_hours: 1.5
actual_hours: 1.0
tags: [init, output, taskwright, workflow, require-kit-split]
epic: null
feature: installation
dependencies: [TASK-020]
blocks: []
---

# TASK-021: Update Init Output to Show Taskwright Workflow Only

## Objective

Update `init-project.sh` output to show ONLY taskwright commands (task workflow) and remove all require-kit commands (requirements, EARS, BDD, epics, features, portfolio).

## Problem Statement

**Current Output** (from user's `taskwright init dotnet-microservice`):
```
═══════════════════════════════════════════════════════
Agentic Flow Workflow
═══════════════════════════════════════════════════════

Stage 1: Requirements & Planning
   /gather-requirements  - Interactive requirements gathering     ← require-kit!
   /formalize-ears       - Convert requirements to EARS notation  ← require-kit!
   /validate-requirements - Check requirements completeness       ← require-kit!
   /epic-create          - Create epic from requirements          ← require-kit!

Stage 2: Feature & Task Definition
   /feature-create       - Create feature from epic               ← require-kit!
   /generate-bdd         - Create BDD scenarios from requirements ← require-kit!
   /task-create          - Create task from feature               ✓ taskwright
   /task-split           - Split complex task                     ✓ taskwright

Stage 3: Engineering & Testing
   /task-work            - Implement task with quality gates      ✓ taskwright
   /execute-tests        - Run test suite                         ✓ taskwright
   /refine               - Refine without full re-work            ✓ taskwright
   /code-review          - Review code quality                    ✓ taskwright

Stage 4: Completion & Deployment
   /task-complete        - Complete and archive task              ✓ taskwright
   /update-state         - Update progress tracking               ← require-kit!
   /update-portfolio     - Update portfolio metrics               ← require-kit!
   /deploy               - Deploy to environment                  ← generic?

═══════════════════════════════════════════════════════
```

**Expected Output** (taskwright only):
```
═══════════════════════════════════════════════════════
Taskwright Workflow
═══════════════════════════════════════════════════════

Simple Task Management:

  /task-create   - Create a new task
  /task-work     - Work on task (Phases 1-5 with quality gates)
  /task-complete - Complete and archive task
  /task-status   - View task status and progress
  /task-refine   - Iterative refinement without full re-work

Design-First Workflow (for complex tasks):

  /task-work TASK-XXX --design-only      - Create plan, stop at checkpoint
  /task-work TASK-XXX --implement-only   - Implement approved plan

UX Design Integration:

  /figma-to-react <file-key> [node-id]   - Figma → React components
  /zeplin-to-maui <project-id> <screen>  - Zeplin → MAUI components

Utilities:

  /debug         - Troubleshoot issues

═══════════════════════════════════════════════════════
For full requirements management (EARS, BDD, epics):
Install require-kit: https://github.com/requirekit/require-kit
═══════════════════════════════════════════════════════
```

## Context

Taskwright is the **lightweight** product:
- ✅ Task workflow (create → work → complete)
- ✅ Quality gates (architectural review, test enforcement)
- ✅ Stack templates
- ✅ UX design integration

Require-kit is the **full requirements** product:
- ❌ Requirements gathering
- ❌ EARS notation
- ❌ BDD generation
- ❌ Epic/feature hierarchy
- ❌ Portfolio management

Users who want BOTH can install both products. But taskwright should only show taskwright commands.

## Files to Modify

### 1. init-project.sh - print_next_steps() Function

**Location**: Lines 370-462

**Current Structure**:
```bash
print_next_steps() {
    # ... header ...

    echo -e "${BOLD}Agentic Flow Workflow${NC}"
    echo "Stage 1: Requirements & Planning"
    echo "   /gather-requirements  - ..."
    echo "   /formalize-ears       - ..."
    # ... many require-kit commands ...

    echo "Stage 2: Feature & Task Definition"
    # ... mix of require-kit and taskwright ...

    echo "Stage 3: Engineering & Testing"
    # ... mostly taskwright ...

    echo "Stage 4: Completion & Deployment"
    # ... mix of both ...
}
```

**Updated Structure**:
```bash
print_next_steps() {
    local detected_type=$(detect_project_type)

    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Taskwright successfully initialized!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}Project Configuration:${NC}"
    echo "  📁 Configuration: .claude/"
    echo "  📚 Documentation: docs/"
    echo "  📋 Tasks: tasks/"
    echo "  🎨 Template: $TEMPLATE"
    echo "  🔍 Detected Type: $detected_type"
    echo ""

    # List installed agents (existing code - keep)
    echo -e "${BOLD}AI Agents:${NC}"
    if [ -d ".claude/agents" ]; then
        for agent in .claude/agents/*.md; do
            if [ -f "$agent" ]; then
                echo "  🤖 $(basename "$agent" .md)"
            fi
        done
    fi
    echo ""

    # Taskwright workflow (SIMPLIFIED)
    echo -e "${BOLD}Taskwright Workflow:${NC}"
    echo ""
    echo "  Simple Task Management:"
    echo "    /task-create      - Create a new task"
    echo "    /task-work        - Work on task (with quality gates)"
    echo "    /task-complete    - Complete and archive task"
    echo "    /task-status      - View task status"
    echo "    /task-refine      - Iterative refinement"
    echo ""
    echo "  Design-First Workflow (complex tasks):"
    echo "    /task-work --design-only      - Plan approval checkpoint"
    echo "    /task-work --implement-only   - Implement approved plan"
    echo ""
    echo "  UX Design Integration:"
    echo "    /figma-to-react   - Figma → React components"
    echo "    /zeplin-to-maui   - Zeplin → MAUI components"
    echo ""
    echo "  Utilities:"
    echo "    /debug            - Troubleshoot issues"
    echo ""

    # Template-specific instructions (existing code - keep but shorten)
    case "$TEMPLATE" in
        dotnet-microservice)
            echo -e "${BOLD}Next Steps for .NET Microservice:${NC}"
            echo "  1. Create your first task: /task-create 'Add health check endpoint'"
            echo "  2. Work on it: /task-work TASK-001"
            echo "  3. Complete: /task-complete TASK-001"
            echo ""
            ;;
        # ... other templates (simplified) ...
    esac

    # Using AI Agents (existing code - keep)
    echo -e "${BOLD}Using AI Agents:${NC}"
    echo "  AI agents are invoked automatically during /task-work"
    echo "  They handle architectural review, testing, and code review"
    echo ""

    # Link to require-kit (NEW)
    echo -e "${BOLD}Need Requirements Management?${NC}"
    echo "  For EARS notation, BDD, epics, and portfolio management:"
    echo "  Install require-kit: ${BLUE}https://github.com/requirekit/require-kit${NC}"
    echo ""

    echo -e "${BLUE}Ready to start development!${NC}"
}
```

## Implementation Steps

### 1. Backup Current Function
```bash
# Make backup before editing
cp installer/scripts/init-project.sh installer/scripts/init-project.sh.backup
```

### 2. Rewrite print_next_steps()

**Remove these sections**:
- Stage 1: Requirements & Planning (all require-kit)
- Stage 2: Feature & Task Definition (mostly require-kit)
- Stage 4: Portfolio/deployment commands (require-kit)

**Keep these sections**:
- Project configuration summary
- AI agents list
- Template-specific next steps (but simplified)

**Add new sections**:
- Simple taskwright workflow commands
- Design-first workflow flags
- UX design integration commands
- Link to require-kit

### 3. Test All Templates

```bash
# Test each template
for template in default react python typescript-api dotnet-microservice maui-appshell maui-navigationpage; do
    echo "Testing: $template"
    cd /tmp/test-$template
    mkdir test && cd test

    # Capture output
    output=$(taskwright init $template 2>&1)

    # Verify taskwright commands shown
    echo "$output" | grep -q "/task-create" && echo "  ✓ /task-create shown"
    echo "$output" | grep -q "/task-work" && echo "  ✓ /task-work shown"
    echo "$output" | grep -q "/task-complete" && echo "  ✓ /task-complete shown"

    # Verify require-kit commands NOT shown
    ! echo "$output" | grep -q "/gather-requirements" && echo "  ✓ /gather-requirements hidden"
    ! echo "$output" | grep -q "/formalize-ears" && echo "  ✓ /formalize-ears hidden"
    ! echo "$output" | grep -q "/epic-create" && echo "  ✓ /epic-create hidden"

    echo ""
done
```

## Expected Output (Example)

```
╔════════════════════════════════════════════════════════╗
║         Taskwright Initialization                      ║
║         Template: dotnet-microservice                  ║
╚════════════════════════════════════════════════════════╝

Using Agentecflow from: /Users/user/.agentecflow
Creating project structure...
  ✓ Project structure created

Copying template files...
  ✓ Using template: dotnet-microservice
  ✓ Copied project context file
  ✓ Copied template-specific agents
  ✓ Copied template files
  ✓ Linked Taskwright commands

Creating project configuration...
  ✓ Created project configuration

Creating initial documentation...
  ✓ Created initial documentation

════════════════════════════════════════════════════════
✅ Taskwright successfully initialized!
════════════════════════════════════════════════════════

Project Configuration:
  📁 Configuration: .claude/
  📚 Documentation: docs/
  📋 Tasks: tasks/
  🎨 Template: dotnet-microservice
  🔍 Detected Type: dotnet-microservice

AI Agents:
  🤖 architectural-reviewer
  🤖 code-reviewer
  🤖 dotnet-api-specialist
  🤖 dotnet-domain-specialist
  🤖 dotnet-testing-specialist
  🤖 task-manager
  🤖 test-orchestrator

Taskwright Workflow:

  Simple Task Management:
    /task-create      - Create a new task
    /task-work        - Work on task (with quality gates)
    /task-complete    - Complete and archive task
    /task-status      - View task status
    /task-refine      - Iterative refinement

  Design-First Workflow (complex tasks):
    /task-work --design-only      - Plan approval checkpoint
    /task-work --implement-only   - Implement approved plan

  UX Design Integration:
    /figma-to-react   - Figma → React components
    /zeplin-to-maui   - Zeplin → MAUI components

  Utilities:
    /debug            - Troubleshoot issues

Next Steps for .NET Microservice:
  1. Create your first task: /task-create 'Add health check endpoint'
  2. Work on it: /task-work TASK-001
  3. Complete: /task-complete TASK-001

Using AI Agents:
  AI agents are invoked automatically during /task-work
  They handle architectural review, testing, and code review

Need Requirements Management?
  For EARS notation, BDD, epics, and portfolio management:
  Install require-kit: https://github.com/requirekit/require-kit

Ready to start development!
```

## Acceptance Criteria

- [ ] Output shows ONLY taskwright commands
- [ ] No require-kit commands shown (gather-requirements, formalize-ears, etc.)
- [ ] No epic/feature/portfolio commands shown
- [ ] Simple task workflow clearly displayed
- [ ] Design-first flags explained
- [ ] UX design integration commands shown
- [ ] Link to require-kit provided for users who need it
- [ ] All 7 templates tested
- [ ] Output is clear and concise (<50 lines)
- [ ] Template-specific instructions simplified

## Testing Strategy

### Test 1: Command Visibility
```bash
output=$(taskwright init default 2>&1)

# Should show these taskwright commands
echo "$output" | grep -q "/task-create" || echo "FAIL: Missing /task-create"
echo "$output" | grep -q "/task-work" || echo "FAIL: Missing /task-work"
echo "$output" | grep -q "/task-complete" || echo "FAIL: Missing /task-complete"
echo "$output" | grep -q "/task-status" || echo "FAIL: Missing /task-status"

# Should NOT show these require-kit commands
! echo "$output" | grep -q "/gather-requirements" || echo "FAIL: Showing /gather-requirements"
! echo "$output" | grep -q "/formalize-ears" || echo "FAIL: Showing /formalize-ears"
! echo "$output" | grep -q "/epic-create" || echo "FAIL: Showing /epic-create"
! echo "$output" | grep -q "/feature-create" || echo "FAIL: Showing /feature-create"
```

### Test 2: Output Length
```bash
# Output should be concise (<60 lines for main workflow section)
output=$(taskwright init default 2>&1)
workflow_lines=$(echo "$output" | grep -A 100 "Taskwright Workflow" | wc -l)
[ $workflow_lines -lt 60 ] || echo "WARN: Output too long ($workflow_lines lines)"
```

### Test 3: All Templates
```bash
# Every template should show same taskwright workflow
for template in default react python typescript-api dotnet-microservice maui-appshell maui-navigationpage; do
    output=$(taskwright init $template 2>&1)
    echo "$output" | grep -q "Taskwright Workflow" || echo "FAIL: $template missing workflow"
done
```

## Definition of Done

- [ ] print_next_steps() rewritten
- [ ] Output shows only taskwright commands
- [ ] No require-kit commands in output
- [ ] Link to require-kit provided
- [ ] Template-specific sections simplified
- [ ] All 7 templates tested
- [ ] Output is concise and clear
- [ ] Backward compatibility maintained (existing projects unaffected)

## Related Tasks

- **TASK-020**: Complete rebrand (must complete first)
- **TASK-019**: Remove folders (complements this)

## Notes

- **Medium effort**: ~1.5 hours
- **High impact**: First impression for users
- **Low risk**: Only affects output text
- **Clear separation**: Taskwright vs require-kit boundaries

---

**Status**: ✅ COMPLETED
**Priority**: HIGH (user experience)
**Estimated Time**: 1.5 hours
**Actual Time**: 1.0 hours
**Dependencies**: TASK-020 (rebrand must complete first)

---

## Implementation Summary

### Changes Made

1. **Simplified print_next_steps() function** (installer/scripts/init-project.sh:375-472)
   - Reorganized output structure with clear sections
   - Added missing commands (/task-refine, /debug)
   - Added UX design integration section
   - Added require-kit link for users who need it

2. **Template-specific instructions simplified**
   - Removed verbose setup commands (dotnet new, npm install, etc.)
   - Replaced with 3-step quick start workflow
   - Added support for all 7 templates (including typescript-api)
   - Consistent format across all templates

3. **Output improvements**
   - Reduced from ~80 lines to ~50 lines
   - Better organization with clear section headers
   - Removed all require-kit commands
   - Added clear separation between taskwright and require-kit

### Verification Results

✅ All taskwright commands shown:
- /task-create, /task-work, /task-complete, /task-status, /task-refine
- /figma-to-react, /zeplin-to-maui
- /debug

✅ No require-kit commands shown:
- /gather-requirements ❌ (hidden)
- /formalize-ears ❌ (hidden)
- /epic-create ❌ (hidden)
- /feature-create ❌ (hidden)
- /update-portfolio ❌ (hidden)

✅ All 7 templates tested:
- default, react, python, typescript-api
- dotnet-microservice
- maui-appshell, maui-navigationpage

### Files Modified

- `installer/scripts/init-project.sh` (50 insertions, 50 deletions)
  - Lines 404-441: Simplified template-specific sections
  - Lines 443-471: Reorganized workflow output

### Acceptance Criteria Status

- ✅ Output shows ONLY taskwright commands
- ✅ No require-kit commands shown
- ✅ No epic/feature/portfolio commands shown
- ✅ Simple task workflow clearly displayed
- ✅ Design-first flags explained
- ✅ UX design integration commands shown
- ✅ Link to require-kit provided
- ✅ All 7 templates tested
- ✅ Output is clear and concise (<50 lines)
- ✅ Template-specific instructions simplified

### Impact

**User Experience:**
- First impression is now clear and focused
- Users understand taskwright's scope immediately
- Clear upgrade path to require-kit if needed

**Documentation:**
- Self-documenting workflow
- No confusion about which product does what
- Clear separation of concerns

**Maintainability:**
- Simpler output logic
- Easier to add new templates
- Consistent format across all templates

---

**Completed**: 2025-11-02
**Branch**: simplify-init-output
**Commit**: 5163609
