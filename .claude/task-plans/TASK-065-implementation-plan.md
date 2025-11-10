# Implementation Plan: TASK-065 - Clean Installer - Remove Deprecated Templates

## Metadata
- **Task ID**: TASK-065
- **Complexity**: 4/10 (Medium - straightforward file operations with script updates)
- **Estimated Duration**: 2-3 hours
- **Stack**: default
- **Phase**: 2 (Implementation Planning)

## Overview

Remove 12 deprecated template directories and 10 deprecated stack agent directories from the installer, then update install.sh to reflect correct counts and template lists. This cleanup ensures users only see the 5 core reference templates.

## Architecture Decisions

### AD-1: Incremental Verification Approach
**Decision**: Use step-by-step verification after each deletion category
**Rationale**:
- Prevents accidental deletion of core templates
- Allows rollback at any checkpoint
- Ensures install.sh updates are accurate
**Alternatives Considered**:
- Bulk deletion: Too risky, no intermediate verification
- Manual deletion: Error-prone, inconsistent

### AD-2: Update install.sh After Deletions
**Decision**: Update install.sh counts and lists AFTER verifying all deletions
**Rationale**:
- Ensures counts are accurate based on actual filesystem state
- Prevents sync issues between code and documentation
- Allows testing of installer before committing

### AD-3: Preserve Stack Agent Structure
**Decision**: Keep `installer/global/agents/stacks/` directory with remaining agents
**Rationale**:
- Maintains consistent directory structure
- install.sh expects this structure
- Future templates may add new stack agents

## Implementation Steps

### Step 1: Verify Core Templates (Safety Check)
**Action**: Confirm 5 core templates exist before any deletions
**Files to Verify**:
- `installer/global/templates/default/`
- `installer/global/templates/fastapi-python/`
- `installer/global/templates/nextjs-fullstack/`
- `installer/global/templates/react-fastapi-monorepo/`
- `installer/global/templates/react-typescript/`

**Verification**: Each directory must contain:
- `CLAUDE.md`
- `agents/`
- `templates/`
- `README.md`

**Risk**: If any core template is missing, abort the task

### Step 2: Remove Deprecated Template Directories
**Action**: Delete 12 deprecated template directories
**Directories to Remove**:
1. `installer/global/templates/documentation/`
2. `installer/global/templates/dotnet-aspnetcontroller/`
3. `installer/global/templates/dotnet-fastendpoints/`
4. `installer/global/templates/dotnet-microservice/`
5. `installer/global/templates/dotnet-minimalapi/`
6. `installer/global/templates/fullstack/`
7. `installer/global/templates/maui-appshell/`
8. `installer/global/templates/maui-navigationpage/`
9. `installer/global/templates/maui/`
10. `installer/global/templates/python/`
11. `installer/global/templates/react/`
12. `installer/global/templates/typescript-api/`

**Verification**: After deletion, confirm only 5 directories remain in `installer/global/templates/`

### Step 3: Remove Deprecated Stack Agent Directories
**Action**: Delete 10 deprecated stack agent directories
**Directories to Remove**:
1. `installer/global/agents/stacks/dotnet-aspnetcontroller/`
2. `installer/global/agents/stacks/dotnet-fastendpoints/`
3. `installer/global/agents/stacks/dotnet-microservice/`
4. `installer/global/agents/stacks/dotnet-minimalapi/`
5. `installer/global/agents/stacks/fullstack/`
6. `installer/global/agents/stacks/maui-appshell/`
7. `installer/global/agents/stacks/maui-navigationpage/`
8. `installer/global/agents/stacks/python/`
9. `installer/global/agents/stacks/react/`
10. `installer/global/agents/stacks/typescript-api/`

**Verification**: After deletion, confirm `installer/global/agents/stacks/` has appropriate remaining directories

### Step 4: Count Global Agents
**Action**: Count actual `.md` files in `installer/global/agents/` (excluding stacks subdirectory)
**Purpose**: Get accurate count for install.sh update
**Expected**: ~17 global agent files (non-stack-specific)

### Step 5: Count Stack Agents
**Action**: Count remaining `.md` files in `installer/global/agents/stacks/*/`
**Purpose**: Calculate total agent count for install.sh
**Formula**: Total agents = Global agents + Stack agents

### Step 6: Update install.sh Template Count References
**Action**: Update hardcoded template counts in install.sh
**Locations to Update**:

1. **Line 281** (create_directories function):
   ```bash
   # OLD:
   mkdir -p "$INSTALL_DIR/templates"/{react,python,maui,dotnet-fastendpoints,dotnet-minimalapi,fullstack,typescript-api}

   # NEW:
   mkdir -p "$INSTALL_DIR/templates"/{default,fastapi-python,nextjs-fullstack,react-fastapi-monorepo,react-typescript}
   ```

2. **Line 1091-1092** (print_summary function):
   ```bash
   # Change from: "📋 Templates: $template_count" (currently showing 17)
   # To: Shows actual count (should be 5)
   # Note: This is dynamically calculated, verify it shows 5
   ```

**Verification**: Search for other hardcoded template lists or counts

### Step 7: Update install.sh Template List Output
**Action**: Update template descriptions in print_summary function
**Location**: Lines 1105-1139 (print_summary function)
**Changes**:

```bash
# REMOVE these case statements (deprecated templates):
python)
    echo "  • $name - Python with FastAPI"
    ;;
maui-appshell)
    echo "  • $name - .NET MAUI with AppShell navigation"
    ;;
maui-navigationpage)
    echo "  • $name - .NET MAUI with NavigationPage"
    ;;
dotnet-fastendpoints)
    echo "  • $name - .NET API with FastEndpoints + REPR pattern"
    ;;
dotnet-minimalapi)
    echo "  • $name - .NET Minimal API with vertical slices"
    ;;
fullstack)
    echo "  • $name - React + Python"
    ;;
typescript-api)
    echo "  • $name - NestJS TypeScript backend API"
    ;;
react)
    echo "  • $name - React with TypeScript"
    ;;

# KEEP/ADD these case statements (core templates):
default)
    echo "  • $name - Language-agnostic foundation (Go, Rust, Ruby, etc.)"
    ;;
fastapi-python)
    echo "  • $name - Python backend with FastAPI best practices"
    ;;
nextjs-fullstack)
    echo "  • $name - Next.js full-stack with App Router"
    ;;
react-fastapi-monorepo)
    echo "  • $name - React + FastAPI monorepo architecture"
    ;;
react-typescript)
    echo "  • $name - React frontend with TypeScript"
    ;;
```

### Step 8: Update taskwright-init Help Text
**Action**: Update template list in taskwright-init command
**Location**: Lines 529-537 (print_help function in create_cli_commands)
**Changes**:

```bash
# OLD:
echo "  react                - React with TypeScript"
echo "  python               - Python with FastAPI"
echo "  maui-appshell        - .NET MAUI with AppShell navigation"
echo "  maui-navigationpage  - .NET MAUI with NavigationPage"
echo "  dotnet-fastendpoints - .NET API with FastEndpoints + REPR pattern"
echo "  dotnet-minimalapi    - .NET Minimal API with vertical slices"
echo "  fullstack            - React + Python"
echo "  typescript-api       - NestJS TypeScript backend API"

# NEW:
echo "  default              - Language-agnostic foundation (Go, Rust, Ruby, etc.)"
echo "  fastapi-python       - Python backend with FastAPI best practices"
echo "  nextjs-fullstack     - Next.js full-stack with App Router"
echo "  react-fastapi-monorepo - React + FastAPI monorepo architecture"
echo "  react-typescript     - React frontend with TypeScript"
```

### Step 9: Update Example Commands
**Action**: Update example commands in help text to use core templates
**Locations**:
- Lines 540-542 (taskwright-init examples)
- Lines 601-603 (taskwright examples)

**Changes**:
```bash
# OLD examples:
taskwright-init react              # Initialize with React template
taskwright-init dotnet-minimalapi  # Initialize with .NET Minimal API

# NEW examples:
taskwright-init react-typescript   # Initialize with React TypeScript template
taskwright-init fastapi-python     # Initialize with FastAPI template
```

### Step 10: Verify install.sh Agent Count Display
**Action**: Verify agent count display matches actual count
**Location**: Lines 392-408 (install_global_agents function)
**Verification**:
- Ensure dynamic counting works correctly
- Test that output shows: "Installed X total agents (Y global + Z stack-specific)"
- Verify X = Y + Z and matches actual file count

### Step 11: Search for Deprecated Template References
**Action**: Search install.sh for any remaining deprecated template names
**Search Terms**:
- "maui"
- "dotnet-fastendpoints"
- "dotnet-minimalapi"
- "typescript-api"
- "fullstack"
- "python" (but not "fastapi-python")
- "react" (but not "react-typescript" or "react-fastapi-monorepo")

**Verification**: No matches found (except in comments/history)

### Step 12: Test Installer (Dry Run)
**Action**: Review install.sh changes without executing
**Checks**:
1. Template creation in create_directories() lists only 5 core templates
2. Template help text shows only 5 core templates
3. Example commands use core template names
4. No references to deprecated templates in functional code

## File Changes Summary

### Files to Delete (22 total)
**Templates (12)**:
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

**Stack Agents (10)**:
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

### Files to Modify (1)
**installer/scripts/install.sh**:
- Line 281: Update mkdir template list (5 core templates)
- Lines 529-537: Update taskwright-init help text (5 core templates)
- Lines 540-542: Update taskwright-init examples
- Lines 601-603: Update taskwright examples
- Lines 1105-1139: Update print_summary template descriptions (5 core templates)

## Testing Strategy

### Verification Points
1. **Post-deletion verification**: Confirm only 5 templates remain
2. **Agent count verification**: Confirm agent counts are accurate
3. **install.sh syntax check**: `bash -n installer/scripts/install.sh`
4. **Directory structure**: Verify `installer/global/templates/` and `installer/global/agents/stacks/` have expected structure
5. **No broken references**: grep for deprecated template names

### Success Criteria
- ✅ Only 5 templates exist in `installer/global/templates/`
- ✅ Only appropriate stack agents remain in `installer/global/agents/stacks/`
- ✅ install.sh shows correct template count (5)
- ✅ install.sh shows correct template list (5 core templates)
- ✅ install.sh help text matches available templates
- ✅ No references to deprecated templates in functional code
- ✅ install.sh passes syntax check

## Risk Assessment

### Risks
1. **Accidental deletion of core templates**: CRITICAL
   - Mitigation: Verify core templates BEFORE any deletions (Step 1)

2. **Breaking install.sh**: HIGH
   - Mitigation: Syntax check before committing, test in isolated environment

3. **Inconsistent documentation**: MEDIUM
   - Mitigation: This task only handles installer; documentation updates are separate

4. **User confusion if cached installers**: LOW
   - Mitigation: Version check in install.sh, users will get new version

### Rollback Plan
If issues discovered:
1. Revert `installer/scripts/install.sh` to previous version
2. Restore deleted directories from git history: `git checkout HEAD~1 -- installer/global/templates/[name]`
3. Re-run verification steps

## Dependencies
- None (standalone cleanup task)

## Follow-up Tasks
- Update documentation references to deprecated templates (separate task)
- Update CLAUDE.md if it references specific template counts (verify only)
- Update any getting-started guides (separate task)

## Notes
- This task is part of the template consolidation strategy (Template Philosophy)
- Focus is on the 5 core templates: default, fastapi-python, nextjs-fullstack, react-fastapi-monorepo, react-typescript
- The `default` template was recently added (TASK-060A) and should NOT be removed
- Stack agents that remain (if any) should be for the 5 core templates only
