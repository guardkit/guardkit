# TASK-060 Implementation Plan: Remove Low-Quality Templates

**Task**: Remove Low-Quality Templates
**Complexity**: 4/10 (Low-Medium)
**Estimated Effort**: 2-3 days
**Created**: 2025-11-09

---

## Overview

Remove 2 low-quality templates (dotnet-aspnetcontroller and default) based on TASK-056 audit findings, while preserving them in an archive branch and providing clear migration paths for users.

---

## Audit Findings Summary

Based on TASK-056 comprehensive audit:

**Templates to REMOVE** (2):
- **dotnet-aspnetcontroller** (6.5/10, Grade C)
  - Traditional ASP.NET MVC pattern
  - Redundant with dotnet-fastendpoints and dotnet-minimalapi
  - Below 8/10 quality threshold
  - Migration: Use dotnet-fastendpoints instead

- **default** (6.0/10, Grade C)
  - Generic, minimal guidance
  - Limited reference value
  - Users better served by technology-specific templates
  - Migration: Choose technology-specific template (react, python, etc.)

**Templates to KEEP** (3):
- maui-appshell (8.8/10)
- maui-navigationpage (8.5/10)
- fullstack (8.0/10)

**Templates to IMPROVE** (5):
- react (7.5/10) - needs template files, manifest validation
- python (7.5/10) - needs template files, manifest validation
- typescript-api (7.2/10) - needs template files, agents
- dotnet-fastendpoints (7.0/10) - needs documentation
- dotnet-minimalapi (6.8/10) - needs comprehensive overhaul

---

## Implementation Steps

### Step 1: Create Archive Branch
**Effort**: 30 minutes
**Files**: N/A

```bash
# Create archive branch from current state
git checkout -b archive/templates-pre-v2.0

# Push archive branch
git push -u origin archive/templates-pre-v2.0

# Tag current state
git tag v1.9-final-before-template-overhaul
git push origin v1.9-final-before-template-overhaul

# Return to working branch
git checkout claude/task-work-011CUwxnz53DWdVQt5LWazU9
```

### Step 2: Remove Templates from Main
**Effort**: 1 hour
**Files**:
- installer/global/templates/dotnet-aspnetcontroller/ (REMOVE)
- installer/global/templates/default/ (REMOVE)

```bash
# Remove template directories
git rm -r installer/global/templates/dotnet-aspnetcontroller/
git rm -r installer/global/templates/default/

# Commit removal
git commit -m "chore: Remove dotnet-aspnetcontroller and default templates

Removal rationale:
- dotnet-aspnetcontroller (6.5/10): Traditional MVC pattern, redundant with dotnet-fastendpoints
- default (6.0/10): Generic template, minimal guidance

Templates archived in: archive/templates-pre-v2.0
Tagged as: v1.9-final-before-template-overhaul
Migration guide: docs/guides/template-migration.md

Reference: TASK-060, TASK-056 (audit findings)"
```

### Step 3: Update Installation Script
**Effort**: 1 hour
**Files**:
- installer/scripts/install.sh (MODIFY)

**Changes**:
- Remove references to `dotnet-aspnetcontroller` and `default` templates
- Update template count (from 10 to 8)
- Verify template list is accurate
- Test installation with remaining templates

### Step 4: Create Migration Guide
**Effort**: 2 hours
**Files**:
- docs/guides/template-migration.md (CREATE)

**Content**:
- Overview of template removal in v2.0
- Removed templates table (name, score, reason, migration path)
- Detailed migration paths for each removed template
- Instructions for accessing archived templates
- Support/contact information

### Step 5: Update Documentation
**Effort**: 3 hours
**Files**:
- CLAUDE.md (MODIFY) - Update template list, remove references
- .claude/CLAUDE.md (MODIFY) - Update template list, remove references
- README.md (MODIFY) - Update quick start, remove references
- docs/**/*.md (MODIFY) - Remove all references to deleted templates

**Changes**:
- Replace all references to `dotnet-aspnetcontroller` and `default` templates
- Update template count throughout documentation
- Add note about v2.0 template changes
- Add links to migration guide

### Step 6: Update Changelog
**Effort**: 1 hour
**Files**:
- CHANGELOG.md (MODIFY)

**Content**:
- Add v2.0.0 section
- Document breaking changes (template removal)
- List removed templates with scores and migration paths
- Reference migration guide
- Explain rationale (focus on quality over quantity)

### Step 7: Verify No Broken References
**Effort**: 1 hour
**Files**: N/A

```bash
# Search for references to removed templates
grep -r "dotnet-aspnetcontroller" docs/ README.md CLAUDE.md .claude/
grep -r "default template" docs/ README.md CLAUDE.md .claude/

# Verify installation script
./installer/scripts/install.sh --help

# Verify template list
ls installer/global/templates/
```

### Step 8: Test Installation
**Effort**: 1 hour
**Files**: N/A

```bash
# Test installation in clean environment
# Verify only 8 templates installed
# Verify no errors or broken references
```

---

## File Change Summary

**Files to CREATE** (1):
- docs/guides/template-migration.md

**Files to MODIFY** (4):
- installer/scripts/install.sh
- CLAUDE.md
- .claude/CLAUDE.md
- CHANGELOG.md

**Directories to REMOVE** (2):
- installer/global/templates/dotnet-aspnetcontroller/
- installer/global/templates/default/

**Total Changes**: 7 files/directories

---

## Testing Plan

### Verification Tests

1. **Archive Verification**
   ```bash
   # Verify archive branch exists
   git branch -r | grep archive/templates-pre-v2.0

   # Verify tag exists
   git tag | grep v1.9-final-before-template-overhaul

   # Verify templates exist in archive
   git checkout archive/templates-pre-v2.0
   ls installer/global/templates/ | wc -l  # Should be 10
   git checkout claude/task-work-011CUwxnz53DWdVQt5LWazU9
   ```

2. **Removal Verification**
   ```bash
   # Verify templates removed
   ls installer/global/templates/ | wc -l  # Should be 8
   ! test -d installer/global/templates/dotnet-aspnetcontroller
   ! test -d installer/global/templates/default
   ```

3. **Documentation Verification**
   ```bash
   # Verify migration guide exists
   test -f docs/guides/template-migration.md

   # Verify no broken references
   ! grep -r "dotnet-aspnetcontroller" docs/ README.md CLAUDE.md .claude/ 2>/dev/null || echo "Found references"
   ! grep -r "default template" docs/ README.md CLAUDE.md .claude/ 2>/dev/null || echo "Found references"
   ```

4. **Installation Verification**
   ```bash
   # Test installation script (dry-run if possible)
   ./installer/scripts/install.sh
   # Verify 8 templates listed
   # Verify no errors
   ```

---

## Risk Mitigation

### Risk 1: Users Depend on Removed Templates
**Likelihood**: Low (templates scored low, likely minimal usage)
**Impact**: Medium (users need to migrate)
**Mitigation**:
- Create comprehensive migration guide
- Archive templates in accessible branch
- Provide clear migration paths
- Document alternative templates

### Risk 2: Broken Documentation References
**Likelihood**: Medium (templates referenced in multiple docs)
**Impact**: High (broken links, confusion)
**Mitigation**:
- Systematic grep search for all references
- Update all documentation before commit
- Verify with automated search
- Test quickstart examples

### Risk 3: Installation Script Breaks
**Likelihood**: Low (straightforward changes)
**Impact**: High (blocks new users)
**Mitigation**:
- Thorough testing after updates
- Verify in clean environment
- Keep rollback plan (git revert)

---

## Success Criteria

**Functional Requirements**:
- [ ] Archive branch created and pushed
- [ ] Templates removed from main branch
- [ ] Installation script updated and functional
- [ ] Migration guide created and comprehensive
- [ ] All documentation references updated
- [ ] Changelog updated

**Quality Requirements**:
- [ ] No broken references in documentation
- [ ] Installation script works with remaining templates
- [ ] Migration paths are clear and actionable
- [ ] Archived templates accessible in archive branch

**Documentation Requirements**:
- [ ] Migration guide complete with all removed templates
- [ ] Changelog updated with v2.0 breaking changes
- [ ] README updated with correct template count
- [ ] CLAUDE.md updated with current template list

---

## Rollback Plan

If issues discovered:
```bash
# Revert commit
git revert HEAD

# Or restore from archive
git checkout archive/templates-pre-v2.0 -- installer/global/templates/dotnet-aspnetcontroller
git checkout archive/templates-pre-v2.0 -- installer/global/templates/default
git commit -m "Rollback: Restore removed templates"
```

---

## Timeline

**Total Estimated Effort**: 10 hours (1.5 days)
- Step 1 (Archive): 0.5 hours
- Step 2 (Remove): 1 hour
- Step 3 (Install Script): 1 hour
- Step 4 (Migration Guide): 2 hours
- Step 5 (Documentation): 3 hours
- Step 6 (Changelog): 1 hour
- Step 7 (Verification): 1 hour
- Step 8 (Testing): 1 hour

**Conservative Estimate**: 2 days (within 2-3 day estimate)

---

## Dependencies

**Completed**:
- ✅ TASK-056: Audit complete with findings

**Required**:
- None (all dependencies met)

**Optional**:
- TASK-057, TASK-058, TASK-059: New reference templates (mentioned but not required for removal)

---

## Notes

- This is a cleanup task focused on quality over quantity
- Removes 20% of templates (2 of 10)
- Keeps the 3 highest-quality templates (8+/10)
- Leaves 5 medium-quality templates for future improvement
- Net result: 8 templates remaining (3 high-quality, 5 to improve)
- Archive ensures no data loss and provides rollback capability

---

**Plan Status**: Ready for Review
**Created**: 2025-11-09
**Next Phase**: Architectural Review (Phase 2.5)
