# TASK-065: Clean Installer - Remove Deprecated Templates

**Created**: 2025-01-10
**Updated**: 2025-01-10T07:45:00Z
**Completed**: 2025-01-10T08:15:00Z
**Priority**: High
**Type**: Bug/Cleanup
**Parent**: Template Strategy Overhaul
**Status**: completed
**Complexity**: 3/10 (Low - re-evaluated from 4/10)
**Estimated Effort**: 1-2 hours
**Actual Effort**: ~45 minutes
**Dependencies**: TASK-060 (Template Removal), TASK-061 (Documentation Update), TASK-062 (React+FastAPI Monorepo)
**Quality Score**: 9.0/10 (EXCELLENT)
**Test Results**: 10/10 tests passed (100%)
**State Transition**: All quality gates passed - ready for review

---

## Problem Statement

The installer script is installing **17 templates** when only **5 core templates** should exist according to the template philosophy established in TASK-060/061. This creates confusion for users and contradicts the "4 high-quality templates" messaging.

**Current State** (from `./install.sh` output):
```
📋 Templates:       17

Available Templates:
  • default
  • documentation
  • dotnet-aspnetcontroller
  • dotnet-fastendpoints
  • dotnet-microservice
  • dotnet-minimalapi
  • fastapi-python
  • fullstack - React + Python
  • maui-appshell
  • maui-navigationpage
  • maui
  • nextjs-fullstack
  • python - Python with FastAPI
  • react-fastapi-monorepo
  • react-typescript
  • react - React with TypeScript
  • typescript-api - NestJS TypeScript backend API
```

**Expected State** (5 templates only):
```
📋 Templates:       5

Available Templates:
  • default - Language-agnostic foundation (8+/10)
  • fastapi-python - FastAPI backend patterns (9+/10)
  • nextjs-fullstack - Next.js full-stack (9+/10)
  • react-fastapi-monorepo - React + FastAPI monorepo (9.2/10)
  • react-typescript - React frontend patterns (9+/10)
```

---

## Context

**Template Philosophy** (from CLAUDE.md):
- **Stack-Specific Reference Templates (9+/10)**: react-typescript, fastapi-python, nextjs-fullstack
- **Language-Agnostic Template (8+/10)**: default
- **Monorepo Template (9.2/10)**: react-fastapi-monorepo (completed in TASK-062)

**Why Only 5 Templates:**
- Templates are **learning resources**, not production code
- High-quality reference implementations demonstrating best practices
- Users should create custom templates from their own codebases via `/template-create`

**Related Tasks:**
- TASK-060: Removed low-quality templates (marked as deprecated)
- TASK-061: Updated documentation for 4-template strategy
- TASK-062: Created react-fastapi-monorepo (5th template)

---

## Objectives

### Primary Objective
Remove deprecated template directories and update installer to only install the 5 core templates.

### Success Criteria
- [x] Only 5 template directories exist in `installer/global/templates/`
- [x] Installer shows "Templates: 5" count
- [x] Installer lists only 5 templates
- [x] Deprecated stack agents removed (11 stacks → 5 stacks)
- [x] Agent count updated (62 agents → correct count for 5 stacks)
- [x] No references to deprecated templates in installer output
- [x] `guardkit doctor` validates 5 templates
- [x] Documentation consistency maintained

---

## Implementation Scope

### Step 1: Identify Deprecated Templates

**Deprecated Templates to Remove** (12 templates):
1. `documentation` - No longer needed (use default)
2. `dotnet-aspnetcontroller` - Low quality
3. `dotnet-fastendpoints` - Low quality
4. `dotnet-microservice` - Low quality
5. `dotnet-minimalapi` - Low quality
6. `fullstack` - Superseded by `react-fastapi-monorepo`
7. `maui-appshell` - Low quality
8. `maui-navigationpage` - Low quality
9. `python` - Superseded by `fastapi-python`
10. `react` - Superseded by `react-typescript`
11. `typescript-api` - Low quality
12. `maui` (if exists as separate directory)

**Core Templates to Keep** (5 templates):
1. `default` - Language-agnostic (8+/10)
2. `fastapi-python` - Python backend (9+/10)
3. `nextjs-fullstack` - Next.js (9+/10)
4. `react-fastapi-monorepo` - Monorepo (9.2/10)
5. `react-typescript` - React frontend (9+/10)

### Step 2: Remove Deprecated Template Directories

Use **Bash tool**:

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit

# Remove deprecated template directories
rm -rf installer/global/templates/documentation
rm -rf installer/global/templates/dotnet-aspnetcontroller
rm -rf installer/global/templates/dotnet-fastendpoints
rm -rf installer/global/templates/dotnet-microservice
rm -rf installer/global/templates/dotnet-minimalapi
rm -rf installer/global/templates/fullstack
rm -rf installer/global/templates/maui-appshell
rm -rf installer/global/templates/maui-navigationpage
rm -rf installer/global/templates/maui
rm -rf installer/global/templates/python
rm -rf installer/global/templates/react
rm -rf installer/global/templates/typescript-api

# Verify only 5 templates remain
ls -1 installer/global/templates/
# Should show:
# default
# fastapi-python
# nextjs-fullstack
# react-fastapi-monorepo
# react-typescript
# guardkit.marker.json
```

### Step 3: Remove Deprecated Stack Agents

Use **Bash tool**:

```bash
# Remove deprecated stack agent directories
rm -rf installer/global/agents/stacks/dotnet-aspnetcontroller
rm -rf installer/global/agents/stacks/dotnet-fastendpoints
rm -rf installer/global/agents/stacks/dotnet-microservice
rm -rf installer/global/agents/stacks/dotnet-minimalapi
rm -rf installer/global/agents/stacks/fullstack
rm -rf installer/global/agents/stacks/maui-appshell
rm -rf installer/global/agents/stacks/maui-navigationpage
rm -rf installer/global/agents/stacks/python
rm -rf installer/global/agents/stacks/react
rm -rf installer/global/agents/stacks/typescript-api

# Verify only 5 stack agent directories remain
ls -1 installer/global/agents/stacks/
# Should show:
# default
# fastapi-python
# nextjs-fullstack
# react-fastapi-monorepo
# react-typescript
```

### Step 4: Update Installer Script - Template Count

Use **Edit tool** to update `installer/scripts/install.sh`:

**Search for template counting logic** and ensure it validates 5 templates:

```bash
# Find template counting section
grep -n "templates" installer/scripts/install.sh | grep -i count
```

**Update the installation summary section** (around line 700-800) to show correct count:

```bash
# Old:
  📋 Templates:       17

# New:
  📋 Templates:       5
```

### Step 5: Update Installer Script - Agent Count

**Expected Agent Counts**:
- Global agents: 14 (unchanged)
- Stack-specific agents per template:
  - default: ~4 agents
  - fastapi-python: ~4 agents
  - nextjs-fullstack: ~4 agents
  - react-fastapi-monorepo: ~3 agents
  - react-typescript: ~4 agents
- **Total stack agents**: ~19 agents
- **Total agents**: 14 global + 19 stack = ~33 agents

Use **Edit tool** to update agent count validation in `installer/scripts/install.sh`.

### Step 6: Update Template List Output

Use **Edit tool** to update the "Available Templates" section in `install.sh`:

**Find the template list generation** (around line 800-900):

```bash
grep -n "Available Templates" installer/scripts/install.sh
```

**Update to show only 5 templates with descriptions**:

```bash
Available Templates:
  • default - Language-agnostic foundation (Go, Rust, Ruby, PHP, etc.)
  • fastapi-python - FastAPI backend with layered architecture (9+/10)
  • nextjs-fullstack - Next.js App Router full-stack (9+/10)
  • react-fastapi-monorepo - React + FastAPI monorepo with type safety (9.2/10)
  • react-typescript - React frontend with feature-based architecture (9+/10)
```

### Step 7: Update `guardkit doctor` Command

Use **Read tool** and **Edit tool** to update the doctor command if it validates template count:

```bash
# Find doctor command
find installer/global/commands -name "*doctor*"
```

Update validation to expect 5 templates.

### Step 8: Verify Installer Output

Use **Bash tool** to test the installer:

```bash
# Run installer
cd installer/scripts
./install.sh

# Expected output:
# ✓ Installed project templates
# ...
# ✓ Installed 33 total agents (14 global + 19 stack-specific)
# ...
# 📋 Templates:       5
# ...
# Available Templates:
#   • default
#   • fastapi-python
#   • nextjs-fullstack
#   • react-fastapi-monorepo
#   • react-typescript
```

### Step 9: Update Any Remaining Documentation References

Use **Grep tool** to find references to deprecated templates:

```bash
# Search for deprecated template names
grep -r "dotnet-fastendpoints\|fullstack\|maui-appshell\|python\|react\|typescript-api" installer/ docs/ README.md CLAUDE.md
```

Use **Edit tool** to update any found references.

### Step 10: Commit Changes

Use **Bash tool**:

```bash
git add installer/
git status

# Verify deletions:
# - 12 template directories removed
# - 10 stack agent directories removed
# - installer/scripts/install.sh modified
```

---

## Acceptance Criteria

### Functional Requirements
- [ ] Only 5 template directories in `installer/global/templates/`
- [ ] Only 5 stack agent directories in `installer/global/agents/stacks/`
- [ ] Installer shows "Templates: 5"
- [ ] Installer lists only 5 templates with descriptions
- [ ] Agent count correct (~33 agents: 14 global + 19 stack)
- [ ] No deprecated template names in installer output
- [ ] `guardkit doctor` validates 5 templates
- [ ] `guardkit-init` lists only 5 templates

### Quality Requirements
- [ ] All 5 templates install correctly
- [ ] All 5 templates' agents load correctly
- [ ] No broken symlinks or references
- [ ] Installer output is clear and accurate
- [ ] Documentation is consistent

---

## Testing Requirements

### Template Installation Tests
```bash
# Test each core template
cd /tmp/test-guardkit

guardkit-init default
# Expected: Initializes successfully

guardkit-init fastapi-python
# Expected: Initializes successfully

guardkit-init nextjs-fullstack
# Expected: Initializes successfully

guardkit-init react-fastapi-monorepo
# Expected: Initializes successfully

guardkit-init react-typescript
# Expected: Initializes successfully

# Test deprecated template (should fail)
guardkit-init fullstack
# Expected: Error - template not found
```

### Agent Loading Tests
```bash
# Verify agents load for each template
cd /tmp/test-default-template
guardkit-init default

# Check .claude/agents/ directory
ls -la .claude/agents/
# Expected: 14 global agents + 4 default stack agents
```

### Doctor Command Test
```bash
guardkit doctor
# Expected: Reports 5 templates, no errors
```

---

## Files to Modify

### Templates (DELETE)
- `installer/global/templates/documentation/`
- `installer/global/templates/dotnet-aspnetcontroller/`
- `installer/global/templates/dotnet-fastendpoints/`
- `installer/global/templates/dotnet-microservice/`
- `installer/global/templates/dotnet-minimalapi/`
- `installer/global/templates/fullstack/`
- `installer/global/templates/maui-appshell/`
- `installer/global/templates/maui-navigationpage/`
- `installer/global/templates/maui/`
- `installer/global/templates/python/`
- `installer/global/templates/react/`
- `installer/global/templates/typescript-api/`

### Stack Agents (DELETE)
- `installer/global/agents/stacks/dotnet-aspnetcontroller/`
- `installer/global/agents/stacks/dotnet-fastendpoints/`
- `installer/global/agents/stacks/dotnet-microservice/`
- `installer/global/agents/stacks/dotnet-minimalapi/`
- `installer/global/agents/stacks/fullstack/`
- `installer/global/agents/stacks/maui-appshell/`
- `installer/global/agents/stacks/maui-navigationpage/`
- `installer/global/agents/stacks/python/`
- `installer/global/agents/stacks/react/`
- `installer/global/agents/stacks/typescript-api/`

### Installer Script (MODIFY)
- `installer/scripts/install.sh`
  - Update template count (line ~700)
  - Update agent count (line ~600)
  - Update template list output (line ~850)

### Documentation (VERIFY/UPDATE)
- `README.md` - Verify "4 templates" messaging (should be 5 now with react-fastapi-monorepo)
- `CLAUDE.md` - Update template count if needed
- `docs/guides/template-philosophy.md` - Update to mention 5 templates

---

## Expected Installer Output (After Fix)

```
╔════════════════════════════════════════════════════════╗
║         GuardKit Installation System                 ║
║         Version: 2.0.0                  ║
╚════════════════════════════════════════════════════════╝

...

✓ Installed project templates
...
✓ Installed 33 total agents (14 global + 19 stack-specific)
  Global agents:
    - architectural-reviewer
    - build-validator
    - code-reviewer
    - complexity-evaluator
    - database-specialist
    - debugging-specialist
    - devops-specialist
    - figma-react-orchestrator
    - pattern-advisor
    - security-specialist
    - task-manager
    - test-orchestrator
    - test-verifier
    - zeplin-maui-orchestrator

...

Installation Summary:
  📁 Home Directory: /Users/richardwoollcott/.agentecflow
  🔧 Configuration: /Users/richardwoollcott/.config/agentecflow
  📦 Version: 2.0.0

Installed Components:
  🤖 AI Agents:       33
  📋 Templates:       5
  ⚡ Commands:       14

Available Templates:
  • default - Language-agnostic foundation (Go, Rust, Ruby, PHP, etc.)
  • fastapi-python - FastAPI backend with layered architecture (9+/10)
  • nextjs-fullstack - Next.js App Router full-stack (9+/10)
  • react-fastapi-monorepo - React + FastAPI monorepo with type safety (9.2/10)
  • react-typescript - React frontend with feature-based architecture (9+/10)

...

✅ GuardKit installation complete!
```

---

## Risk Mitigation

### Risk 1: Breaking Existing User Installations
**Mitigation**: Installer backs up existing `.agentecflow` directory before installing. Users with old templates can still access them in backup.

### Risk 2: Agent Count Mismatch
**Mitigation**: Count agents programmatically in installer script, don't hardcode numbers.

### Risk 3: Missed References to Deprecated Templates
**Mitigation**: Comprehensive grep search + manual verification of documentation.

---

## Success Metrics

**Quantitative**:
- Template count: 5 (down from 17)
- Stack agent directories: 5 (down from 15)
- Total agent count: ~33 (down from 62)
- Installer output accuracy: 100%

**Qualitative**:
- Clear, consistent messaging about "5 high-quality templates"
- No confusion about which templates to use
- Faster installer execution (fewer files to copy)
- Cleaner directory structure

---

## Related Tasks

- **TASK-060**: Remove Low-Quality Templates (marked deprecated)
- **TASK-061**: Update Documentation for 4-Template Strategy
- **TASK-062**: Create React + FastAPI Monorepo Template (5th template)
- **TASK-063**: Update Documentation for 5-Template Strategy

---

**Document Status**: Ready for Implementation
**Created**: 2025-01-10
**Parent Epic**: Template Strategy Overhaul
**Depends On**: TASK-062 (React+FastAPI Monorepo completed)
