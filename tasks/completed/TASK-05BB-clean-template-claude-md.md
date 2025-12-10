---
id: TASK-05BB
legacy_id: TASK-008
title: "Clean Stack Template CLAUDE.md Files"
created: 2025-10-27
status: completed
priority: medium
complexity: 4
parent_task: none
subtasks: []
estimated_hours: 2
completed: 2025-11-01
---

# TASK-05BB: Clean Stack Template CLAUDE.md Files

## Description

Remove requirements management references from CLAUDE.md files in all stack templates while keeping stack-specific patterns, quality gates, and testing documentation.

## Templates to Update

```
installer/core/templates/default/CLAUDE.md
installer/core/templates/react/CLAUDE.md
installer/core/templates/python/CLAUDE.md
installer/core/templates/typescript-api/CLAUDE.md
installer/core/templates/maui-appshell/CLAUDE.md
installer/core/templates/maui-navigationpage/CLAUDE.md
installer/core/templates/dotnet-microservice/CLAUDE.md
installer/core/templates/fullstack/CLAUDE.md
```

## Changes for Each Template

### Remove Sections
- Requirements Management
- EARS Notation
- BDD/Gherkin Scenarios
- Epic/Feature Hierarchy
- External PM Tool Integration
- Stage 1: Specification (if mentioned)
- Stage 2: Tasks Definition (epic/feature parts)

### Keep Sections
- Task Workflow
- Quality Gates (Phase 2.5, 4.5, 2.6, 2.7, 5.5)
- Testing Patterns (stack-specific)
- Stack-Specific Patterns
- Architecture Principles
- Domain Layer patterns (for .NET templates)
- State management (for React)

### Update Task Creation Examples

**Change FROM**:
```bash
/task-create "Feature" epic:EPIC-001 feature:FEAT-001 requirements:[REQ-001]
```

**TO**:
```bash
/task-create "Feature name"
/task-create "Add authentication" priority:high
```

### Update Workflow Examples

**Change FROM**:
```bash
# Stage 1: Specification
/gather-requirements → /formalize-ears

# Stage 2: Tasks Definition
/epic-create → /feature-create → /task-create

# Stage 3: Engineering
/task-work
```

**TO**:
```bash
# Create task
/task-create "Feature name"

# Work on it (with quality gates)
/task-work TASK-XXX

# Complete
/task-complete TASK-XXX
```

## Implementation Steps

### 1. Create Backup

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/taskwright/.conductor/kuwait

# Backup all CLAUDE.md files
for template in default react python typescript-api maui-appshell \
                maui-navigationpage dotnet-microservice fullstack; do
  cp installer/core/templates/$template/CLAUDE.md \
     installer/core/templates/$template/CLAUDE.md.backup
done
```

### 2. Edit Each Template

For each template:
1. Open CLAUDE.md
2. Remove sections listed above
3. Update task creation examples
4. Update workflow examples
5. Verify quality gate documentation remains

### 3. Verify Changes

```bash
# Check for forbidden references in each template
for template in installer/core/templates/*/CLAUDE.md; do
  echo "Checking $template..."
  grep -i "epic.*create\|feature.*create\|gather.*requirements\|formalize.*ears\|generate.*bdd" "$template" \
    | grep -v "# Historical" && echo "⚠ Found references in $template"
done

# Should return empty or only historical context
```

### 4. Test Template Initialization

```bash
# For each template, verify it still initializes
cd /tmp
for template in default react python typescript-api; do
  mkdir test-$template
  cd test-$template
  # Simulate: agentecflow init $template
  # Verify CLAUDE.md is copied and correct
  cd ..
done
```

## Per-Template Checklist

### default/
- [ ] CLAUDE.md updated
- [ ] Requirements sections removed
- [ ] Quality gate documentation retained
- [ ] Generic workflow examples updated

### react/
- [ ] CLAUDE.md updated
- [ ] React patterns retained (state management, component design)
- [ ] Testing patterns retained (Vitest, Playwright)
- [ ] Requirements references removed

### python/
- [ ] CLAUDE.md updated
- [ ] Python patterns retained (FastAPI, pytest, async/await)
- [ ] Testing patterns retained
- [ ] Requirements references removed

### typescript-api/
- [ ] CLAUDE.md updated
- [ ] NestJS patterns retained
- [ ] Result patterns retained
- [ ] Domain modeling retained
- [ ] Requirements references removed

### maui-appshell/, maui-navigationpage/
- [ ] CLAUDE.md updated for both
- [ ] Domain layer patterns retained
- [ ] MVVM patterns retained
- [ ] ErrorOr patterns retained
- [ ] Requirements references removed

### dotnet-microservice/
- [ ] CLAUDE.md updated
- [ ] FastEndpoints patterns retained
- [ ] Either monad patterns retained
- [ ] Requirements references removed

### fullstack/
- [ ] CLAUDE.md updated
- [ ] Integration patterns retained
- [ ] Frontend/backend coordination retained
- [ ] Requirements references removed

## Validation Checklist

### All Templates
- [ ] 8 CLAUDE.md files updated
- [ ] No EARS notation references
- [ ] No BDD scenario references
- [ ] No epic/feature hierarchy references
- [ ] Quality gates documentation retained
- [ ] Stack-specific patterns retained
- [ ] Testing documentation retained

### Grep Verification
```bash
# Should return empty (except historical context)
grep -r "EARS\|epic.*hierarchy\|feature.*hierarchy" \
  installer/core/templates/*/CLAUDE.md | grep -v "Historical"
```

## Acceptance Criteria

- [ ] All 8 template CLAUDE.md files updated
- [ ] Requirements management sections removed
- [ ] Quality gate sections retained
- [ ] Stack-specific patterns retained
- [ ] Task creation examples simplified
- [ ] Workflow examples updated
- [ ] Grep verification passes
- [ ] Template initialization still works

## Related Tasks

- TASK-1FDF: Remove requirements management commands
- TASK-1063: Modify task-create.md
- TASK-6444: Modify task-work.md

## Estimated Time

2 hours (15 minutes per template)

## Notes

- Templates may vary in structure - adapt approach as needed
- Some templates may not have all sections - that's OK
- Keep any template-specific innovations
- Focus on removing epic/feature/requirements, not rewriting everything

## Completion Summary

### Changes Made

**Templates Updated:**
- ✅ default/CLAUDE.md - Removed requirements management sections, simplified workflow
- ✅ react/CLAUDE.md - Added task workflow section, enhanced with state management patterns
- ✅ python/CLAUDE.md - No changes needed (already clean)
- ✅ typescript-api/CLAUDE.md - Replaced requirements workflow with unified task workflow
- ✅ maui-appshell/CLAUDE.md - No changes needed (already clean)
- ✅ maui-navigationpage/CLAUDE.md - No changes needed (already clean)
- ✅ dotnet-microservice/CLAUDE.md - No changes needed (already clean)
- ✅ fullstack/CLAUDE.md - Replaced epic/feature workflow with unified task system

### Sections Removed
- Requirements Management references
- EARS Notation guidance
- BDD/Gherkin workflow instructions
- Epic/Feature hierarchy documentation
- `/gather-requirements`, `/formalize-ears`, `/generate-bdd` commands
- `epic:EPIC-XXX`, `feature:FEAT-XXX`, `requirements:[REQ-XXX]` parameter patterns

### Sections Retained
- Task Workflow (`/task-create`, `/task-work`, `/task-complete`)
- Quality Gates (Phase 2.5, 4.5, 2.7, 5.5)
- Testing Patterns (stack-specific)
- Stack-Specific Patterns and Best Practices
- Architecture Principles
- Development Standards

### Verification
- ✅ All 8 templates verified clean (no forbidden references)
- ✅ Backups created (.backup files)
- ✅ Task creation examples simplified
- ✅ Workflow examples updated to unified system

### Files Changed
- installer/core/templates/default/CLAUDE.md
- installer/core/templates/react/CLAUDE.md
- installer/core/templates/typescript-api/CLAUDE.md
- installer/core/templates/fullstack/CLAUDE.md

### Files Unchanged (Already Clean)
- installer/core/templates/python/CLAUDE.md
- installer/core/templates/maui-appshell/CLAUDE.md
- installer/core/templates/maui-navigationpage/CLAUDE.md
- installer/core/templates/dotnet-microservice/CLAUDE.md
