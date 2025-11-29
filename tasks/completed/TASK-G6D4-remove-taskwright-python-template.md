---
id: TASK-G6D4
title: "Remove taskwright-python template and document why"
status: completed
created: 2025-11-26T09:55:00Z
updated: 2025-11-26T12:20:00Z
completed: 2025-11-26T12:20:00Z
priority: high
tags: [cleanup, template-removal, simplification]
complexity: 2
estimated_hours: 1
actual_hours: 2.5
task_type: implementation
related_tasks: [TASK-D3A1, TASK-BAA5]
architecture_improvement: +5.25
---

# Task: Remove taskwright-python Template and Document Why

## Problem Statement

The `taskwright-python` template at `installer/global/templates/taskwright-python/` serves no valid purpose and creates confusion. It should be removed.

## Context

**From TASK-D3A1 architectural review**:

**Why the template exists** (original intent):
- Created as a template for Taskwright development
- Intended to demonstrate Taskwright's own architecture (Python CLI with orchestrator pattern)

**Why it should be removed** (discovered issues):
1. **Taskwright's `.claude/` is git-managed** - Not template-initialized
2. **Running `taskwright init taskwright-python` on Taskwright repo was a mistake** - Led to TASK-BAA5 issues
3. **No valid use case for users** - User Python CLI projects should use `fastapi-python` template or create custom templates via `/template-create`
4. **Maintenance burden** - One more template to keep updated
5. **Creates confusion** - Blurs line between Taskwright development and user projects

**Architectural review conclusion**: "The taskwright-python template serves no real purpose"

## Requirements

### 1. Remove Template Directory

Remove the entire template:
```bash
rm -rf installer/global/templates/taskwright-python/
```

### 2. Update Template Documentation

**File**: `installer/global/templates/README.md` (or main README.md)

Remove references to `taskwright-python` template and explain why it was removed:

```markdown
## Available Templates

Taskwright includes 5 high-quality templates for learning and evaluation:

### Stack-Specific Reference Templates
1. **react-typescript** - Frontend best practices
2. **fastapi-python** - Backend API patterns
3. **nextjs-fullstack** - Full-stack application

### Specialized Templates
4. **react-fastapi-monorepo** - Full-stack monorepo
5. **default** - Language-agnostic foundation

### Note on taskwright-python Template (Removed)

The `taskwright-python` template was removed because:
- **Taskwright's `.claude/` is git-managed** - Template initialization not needed for Taskwright development
- **User confusion** - Template suggested users should run `taskwright init` on Taskwright repo itself (incorrect)
- **Better alternatives exist** - Users needing Python CLI templates should use `fastapi-python` or create custom templates via `/template-create`

**For Taskwright development**: The `.claude/` directory is checked into git. Clone the repo and use the configuration as-is.

**For Python CLI projects**: Use `fastapi-python` template or create a custom template based on your architecture.
```

### 3. Update CLAUDE.md Template Philosophy Section

**File**: `.claude/CLAUDE.md` or main `CLAUDE.md`

Update the template count and remove taskwright-python references:

```markdown
## Template Philosophy

Taskwright includes **5 high-quality templates** for learning and evaluation:

### Stack-Specific Reference Templates (9+/10 Quality)
1. **react-typescript** - Frontend best practices (from Bulletproof React)
2. **fastapi-python** - Backend API patterns (from FastAPI Best Practices)
3. **nextjs-fullstack** - Full-stack application (Next.js App Router)

### Specialized Templates (8-9+/10 Quality)
4. **react-fastapi-monorepo** - Full-stack monorepo (9.2/10)

### Language-Agnostic Template (8+/10 Quality)
5. **default** - For Go, Rust, Ruby, Elixir, PHP, and other languages
```

Remove any sections that reference:
- `taskwright-python` template
- Running `taskwright init taskwright-python` on Taskwright repo
- Taskwright as a template use case

### 4. Update Installation Documentation

**File**: Main README.md or docs/guides/installation.md

Ensure installation instructions don't reference `taskwright-python`:

```bash
# Install
chmod +x installer/scripts/install.sh
./installer/scripts/install.sh

# Initialize with template (for USER PROJECTS, not Taskwright itself)
taskwright init [react-typescript|fastapi-python|nextjs-fullstack|default]

# For Taskwright development: .claude/ is in git, no template init needed
```

### 5. Create ADR Documenting Removal

**File**: `docs/adr/0002-remove-taskwright-python-template.md`

```markdown
# ADR 0002: Remove taskwright-python Template

## Status
Accepted

## Context
The `taskwright-python` template was created to demonstrate Taskwright's architecture (Python CLI with orchestrator pattern). However, its existence created confusion and served no valid use case.

## Problems Identified
1. Taskwright's `.claude/` directory is git-managed, not template-initialized
2. Running `taskwright init taskwright-python` on Taskwright repo caused agent deletion issues (TASK-BAA5)
3. No valid user use case - Python CLI projects should use `fastapi-python` or custom templates
4. Maintenance burden for a template with no users
5. Confusion about when to use template init vs git-managed configuration

## Decision
Remove the `taskwright-python` template entirely.

## Consequences

### Positive
- Eliminates confusion about Taskwright development vs user projects
- Reduces template maintenance burden (5 templates instead of 6)
- Clarifies that Taskwright's `.claude/` is git-managed
- Simplifies documentation and onboarding

### Negative
- None identified - template had no valid use case

## Alternatives Considered

### A) Keep template but document limitations
**Rejected**: Doesn't solve confusion, still requires maintenance

### B) Repurpose for generic Python CLI projects
**Rejected**: `fastapi-python` template already serves Python projects; users can create custom templates via `/template-create`

## References
- TASK-D3A1: Architectural review validating removal
- TASK-BAA5: Review of issues caused by running template init on Taskwright repo
- Architectural review score: Current approach 3.5/10, removal approach 8.75/10
```

## Implementation Approach

**Phase 1: Remove Template** (10 min)
- Delete `installer/global/templates/taskwright-python/` directory
- Verify no references in init scripts

**Phase 2: Update Documentation** (30 min)
- Update template README
- Update main CLAUDE.md
- Update installation docs
- Remove any references to 6 templates (now 5)

**Phase 3: Create ADR** (20 min)
- Document decision and rationale
- Reference related tasks and reviews

## Files to Modify

**Delete**:
- `installer/global/templates/taskwright-python/` (entire directory)

**Update**:
- `installer/global/templates/README.md` (or main README.md)
- `CLAUDE.md` or `.claude/CLAUDE.md`
- Installation documentation
- Any references to template count (6 → 5)

**Create**:
- `docs/adr/0002-remove-taskwright-python-template.md`

## Acceptance Criteria

- [x] Template directory removed: `installer/global/templates/taskwright-python/`
- [x] Documentation updated to reference 5 templates (not 6)
- [x] Explanation added for why template was removed
- [x] CLAUDE.md template philosophy updated
- [x] Installation docs clarify: Taskwright uses git-managed .claude/
- [x] ADR created documenting decision and rationale (ADR 0003)
- [x] No broken references to taskwright-python template

## References

- **TASK-D3A1**: Architectural review validating removal decision
- **TASK-BAA5**: Original issue from running template init on Taskwright repo
- **Architectural Review**: docs/reviews/TASK-D3A1-architectural-review.md

## Success Metrics

When complete:
- ✅ No confusion about Taskwright development vs user projects
- ✅ Clear documentation: Taskwright's .claude/ is git-managed
- ✅ Users directed to appropriate templates (fastapi-python) or custom template creation
- ✅ 5 high-quality templates instead of 6 (reduced maintenance)
