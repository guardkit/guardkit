# TASK-060: Remove Low-Quality Templates

**Created**: 2025-01-08
**Priority**: Medium
**Type**: Cleanup
**Parent**: Template Strategy Overhaul
**Status**: Backlog
**Complexity**: 4/10 (Low-Medium)
**Estimated Effort**: 2-3 days
**Dependencies**: TASK-056 (Audit Complete), TASK-057, TASK-058, TASK-059 (New templates ready)

---

## Problem Statement

Remove templates that scored below 8/10 in the comprehensive audit (TASK-056) to reduce maintenance burden and focus on high-quality reference implementations. Ensure smooth migration path for users who may depend on removed templates.

**Goal**: Remove templates scoring <8/10, archive for posterity, provide migration guidance.

---

## Context

**Related Documents**:
- [Template Strategy Decision](../../docs/research/template-strategy-decision.md)
- [Template Audit Comparative Analysis](../../docs/research/template-audit-comparative-analysis.md) (from TASK-056)
- [Template Removal Plan](../../docs/research/template-removal-plan.md) (from TASK-056)
- TASK-056: Template audit findings

**Current State**:
- 9 built-in templates
- Unknown quality levels (before TASK-056)
- No removal/deprecation process

**Target State**:
- 3 high-quality reference templates (9+/10 score)
- 6 templates removed (or whatever audit shows)
- Clear migration path for users
- Archived templates accessible

---

## Objectives

### Primary Objective
Remove templates scoring <8/10 while providing smooth migration path for users.

### Success Criteria
- [x] Audit findings reviewed (from TASK-056)
- [x] Removal list finalized
- [x] Templates archived in separate branch
- [x] Templates removed from main branch
- [x] Migration guide created
- [x] Deprecation communicated (changelog, README)
- [x] Documentation updated (all references removed)
- [x] Installation script updated

---

## Implementation Scope

### Step 1: Review Audit Findings (from TASK-056)

```bash
# Review comparative analysis
cat docs/research/template-audit-comparative-analysis.md

# Identify templates scoring <8/10
# Expected removal candidates:
# - Templates with scores 0-7.9/10
# - Templates with critical issues
# - Templates without clear use case
```

### Step 2: Create Archive Branch

```bash
# Create archive branch for removed templates
git checkout -b archive/templates-pre-v2.0
git push origin archive/templates-pre-v2.0

# Tag current state
git tag v1.9-final-before-template-overhaul
git push origin v1.9-final-before-template-overhaul
```

### Step 3: Remove Templates from Main

**For each template to remove**:

```bash
# Example: Removing maui-navigationpage template
TEMPLATE_NAME="maui-navigationpage"

# Remove template directory
git rm -r installer/global/templates/$TEMPLATE_NAME/

# Commit removal
git commit -m "chore: Remove $TEMPLATE_NAME template (scored <8/10 in audit)

Removal rationale:
- Audit score: X.X/10
- Quality issues: [list from audit]
- Migration path: See docs/guides/template-migration.md

Archived in branch: archive/templates-pre-v2.0
Reference: TASK-060"
```

### Step 4: Update Installation Script

**File**: `installer/scripts/install.sh`

```bash
# Remove references to deleted templates
# Update template list
# Test installation with remaining templates
```

### Step 5: Create Migration Guide

**File**: `docs/guides/template-migration.md`

```markdown
# Template Migration Guide

## Templates Removed in v2.0

As part of our template quality initiative, the following templates have been removed:

### Removed Templates

| Template | Final Score | Removal Reason | Migration Path |
|----------|------------|----------------|----------------|
| template-a | X.X/10 | Quality issues | Use react-typescript + customize |
| template-b | X.X/10 | Niche use case | Create from your codebase with `/template-create` |
| ... | ... | ... | ... |

### Migration Paths

#### From `template-a` → `react-typescript`

**If you used template-a**:
```bash
# Option 1: Use new react-typescript template
taskwright init react-typescript

# Option 2: Create custom template from your existing code
cd your-existing-project-using-template-a
/template-create
taskwright init your-custom-template
```

**Differences to be aware of**:
- [List key differences]
- [Migration steps if needed]

#### From `template-b` → Custom Template

**Recommended approach**:
```bash
# Create template from your production codebase
cd your-production-codebase
/template-create

# Use your custom template
taskwright init your-custom-template
```

### Accessing Archived Templates

If you need the old templates, they are archived:

```bash
# Checkout archive branch
git checkout archive/templates-pre-v2.0

# Or download specific template
git show archive/templates-pre-v2.0:installer/global/templates/template-a/ > template-a-archive.tar
```

### Support

Questions about migration? [Link to issues or discussions]
```

### Step 6: Update Documentation

**Files to update**:

#### CLAUDE.md
```markdown
# Remove all references to deleted templates
# Update template list
# Update examples using removed templates

## Templates

Taskwright includes 3 reference implementation templates:

1. **react-typescript** - Frontend development
2. **fastapi-python** - Backend API development
3. **nextjs-fullstack** - Full-stack applications

**Note**: As of v2.0, we focus on high-quality reference templates.
For custom templates, use `/template-create` from your codebase.
```

#### README.md
```markdown
# Update quick start examples
# Remove references to deleted templates
# Add note about v2.0 template changes
```

#### All documentation files
```bash
# Find all references to removed templates
grep -r "maui-navigationpage" docs/

# Update each file to:
# - Remove deleted template references
# - Replace with new template examples
# - Add migration notes if needed
```

### Step 7: Update Changelog

**File**: `CHANGELOG.md`

```markdown
## [2.0.0] - 2025-XX-XX

### Breaking Changes

**Template Overhaul**:
- Reduced from 9 to 3 high-quality reference implementation templates
- All remaining templates score 9+/10 on comprehensive quality audit

**Removed Templates**:
- `template-a` (scored X.X/10) - Migration: Use `react-typescript` or create custom with `/template-create`
- `template-b` (scored X.X/10) - Migration: Use `fastapi-python` or create custom with `/template-create`
- ... (list all removed)

**Migration Path**:
See [Template Migration Guide](docs/guides/template-migration.md)

**Archived Templates**:
Available in branch `archive/templates-pre-v2.0` or tag `v1.9-final-before-template-overhaul`

**New High-Quality Templates**:
- `react-typescript` (9.3/10) - From Bulletproof React
- `fastapi-python` (9.2/10) - From FastAPI Best Practices
- `nextjs-fullstack` (9.4/10) - Next.js App Router with production patterns

**Rationale**:
Focus on fewer, higher-quality reference implementations. Developers should use `/template-create` from their production codebases for custom templates.

See [Template Strategy Decision](docs/research/template-strategy-decision.md) for full analysis.
```

### Step 8: Communication Plan

**GitHub Release Notes**:
```markdown
# v2.0.0 - Template Quality Overhaul

## 🎉 What's New

High-quality reference implementation templates created from production-proven repositories:
- **react-typescript**: From Bulletproof React (28.5k stars)
- **fastapi-python**: From FastAPI Best Practices (12k+ stars)
- **nextjs-fullstack**: Next.js App Router + production patterns

All templates validated at 9+/10 quality score.

## 💔 Breaking Changes

**Templates Removed**: [List]

**Migration**: See [Template Migration Guide](docs/guides/template-migration.md)

**Why**: Focus on high-quality reference implementations. Use `/template-create` for custom templates from your production code.

## 📦 Accessing Old Templates

Old templates archived in `archive/templates-pre-v2.0` branch.

## 🚀 Upgrade Guide

1. Review [Template Migration Guide](docs/guides/template-migration.md)
2. Update your workflows to use new template names
3. Consider creating custom templates with `/template-create`
```

---

## Acceptance Criteria

### Functional Requirements
- [ ] Audit findings reviewed and removal list finalized
- [ ] Templates archived in separate branch
- [ ] Templates removed from main branch
- [ ] Installation script updated and tested
- [ ] All documentation references removed/updated
- [ ] Migration guide created and comprehensive

### Quality Requirements
- [ ] No broken references in documentation
- [ ] Installation script works with remaining templates
- [ ] Migration paths are clear and actionable
- [ ] Users can access archived templates if needed

### Documentation Requirements
- [ ] Migration guide complete
- [ ] Changelog updated
- [ ] README updated
- [ ] CLAUDE.md updated
- [ ] All guides updated

---

## Testing Requirements

### Verification Tests
```bash
# 1. Verify templates removed
ls installer/global/templates/
# Expected: Only react-typescript, fastapi-python, nextjs-fullstack

# 2. Verify archive exists
git checkout archive/templates-pre-v2.0
ls installer/global/templates/
# Expected: All 9 original templates

# 3. Verify installation script works
git checkout main
./installer/scripts/install.sh
# Expected: Successful installation of 3 templates

# 4. Verify templates installed
ls ~/.agentecflow/templates/
# Expected: react-typescript, fastapi-python, nextjs-fullstack

# 5. Verify no broken documentation links
grep -r "maui-navigationpage" docs/
# Expected: No results (or only in migration guide)

# 6. Verify migration guide exists
cat docs/guides/template-migration.md
# Expected: Complete migration guide
```

---

## Expected Removals (Hypothetical - Based on Audit)

**Likely removal candidates** (will be confirmed by TASK-056 audit):

1. **maui-appshell** - Niche (mobile-only), lower usage
2. **maui-navigationpage** - Duplicate MAUI approach
3. **dotnet-fastendpoints** - Specific .NET pattern
4. **dotnet-aspnetcontroller** - Legacy .NET pattern
5. **dotnet-minimalapi** - Covered by nextjs-fullstack API patterns
6. **typescript-api** - Covered by nextjs-fullstack API routes

**Potential keepers** (if they score 8+):
- **default** - Generic fallback (might keep if high quality)
- **react** - If high quality, might replace with react-typescript
- **python** - If high quality, might replace with fastapi-python

**Note**: Final removal list depends on TASK-056 audit findings.

---

## Risk Mitigation

### Risk 1: Users Depend on Removed Templates
**Mitigation**:
- 6-month deprecation notice before removal
- Comprehensive migration guide
- Archived branch accessible
- Support in migration process

### Risk 2: Broken Documentation References
**Mitigation**:
- Systematic grep search for all references
- Update all documentation before release
- Test all quickstart examples

### Risk 3: Installation Script Breaks
**Mitigation**:
- Thorough testing after updates
- Verify in fresh environment
- Keep rollback plan

---

## Deprecation Timeline

**Recommended approach** (if users exist):

```
Month 1 (Now):
- Announce deprecation in README
- Add deprecation warnings to removed templates
- Release v1.9 with warnings

Month 2-6:
- Deprecation period
- Support users in migration
- Answer questions

Month 7:
- Remove templates (v2.0)
- Archive in separate branch
- Release with migration guide
```

**Fast approach** (if few/no users):
- Announce + remove in same release (v2.0)
- Provide clear migration path
- Archive for posterity

---

## Success Metrics

**Quantitative**:
- Templates reduced from 9 to 3 (67% reduction)
- All remaining templates score 9+/10
- Zero broken documentation references
- Installation script functional: 100%

**Qualitative**:
- Migration guide is clear and helpful
- Users understand rationale
- Archive is accessible
- No major user complaints

---

## Related Tasks

- **TASK-056**: Prerequisite - Audit findings inform removal decisions
- **TASK-057**: New react-typescript template (replacement)
- **TASK-058**: New fastapi-python template (replacement)
- **TASK-059**: New nextjs-fullstack template (replacement)
- **TASK-061**: Update documentation (parallel/sequential)
- **TASK-021**: Template location strategy (related consideration)

---

**Document Status**: Ready for Implementation (after TASK-056, TASK-057, TASK-058, TASK-059)
**Created**: 2025-01-08
**Parent Epic**: Template Strategy Overhaul
