---
id: TASK-CRS-013
title: Update Template README Files for Rules Structure
status: backlog
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T12:15:00Z
priority: low
tags: [documentation, template-readme, rules-structure]
complexity: 3
parent_feature: claude-rules-structure
wave: 5
implementation_mode: direct
conductor_workspace: claude-rules-wave5-3
estimated_hours: 2-3
dependencies:
  - TASK-CRS-006
  - TASK-CRS-007
  - TASK-CRS-008
  - TASK-CRS-009
  - TASK-CRS-010
---

# Task: Update Template README Files for Rules Structure

## Description

Update the README.md files for all 5 built-in templates to document the new rules structure and explain the directory organization.

## Files to Modify

1. `installer/core/templates/react-typescript/README.md`
2. `installer/core/templates/fastapi-python/README.md`
3. `installer/core/templates/nextjs-fullstack/README.md`
4. `installer/core/templates/react-fastapi-monorepo/README.md`
5. `installer/core/templates/default/README.md`

## Changes Required (Per Template)

### Add Rules Structure Section

```markdown
## Rules Structure

This template uses Claude Code's modular rules structure for optimized context loading.

### Directory Layout

```
.claude/
├── CLAUDE.md                    # Core documentation (~5KB)
└── rules/
    ├── code-style.md            # Code style guidelines
    ├── testing.md               # Testing conventions
    ├── patterns/                # Pattern-specific rules
    │   └── {pattern}.md
    └── agents/                  # Agent guidance
        └── {agent}.md
```

### Path-Specific Rules

Rules files use `paths:` frontmatter for conditional loading:

| Rule File | Loads When Editing |
|-----------|-------------------|
| `rules/code-style.md` | Any `.{ext}` file |
| `rules/testing.md` | Test files |
| `rules/agents/{name}.md` | Relevant files |

### Benefits

- Rules only load when editing relevant files
- Reduced context window usage (60-70% reduction)
- Organized by concern (patterns, agents, etc.)
```

### Template-Specific Content

**react-typescript**:
```markdown
| Rule File | Loads When Editing |
|-----------|-------------------|
| `rules/patterns/feature-based.md` | `src/features/**` |
| `rules/patterns/query-patterns.md` | `**/*query*`, `**/*api*` |
| `rules/agents/react-query.md` | Query/API files |
| `rules/agents/form-validation.md` | Form/validation files |
```

**fastapi-python**:
```markdown
| Rule File | Loads When Editing |
|-----------|-------------------|
| `rules/api/routing.md` | `**/router*.py` |
| `rules/database/models.md` | `**/models/*.py` |
| `rules/agents/fastapi.md` | API route files |
| `rules/agents/database.md` | Model/CRUD files |
```

**nextjs-fullstack**:
```markdown
| Rule File | Loads When Editing |
|-----------|-------------------|
| `rules/server/components.md` | `**/app/**/*.tsx` |
| `rules/server/actions.md` | `**/actions/*.ts` |
| `rules/database/prisma.md` | `**/prisma/**` |
| `rules/agents/server-components.md` | App Router files |
```

**react-fastapi-monorepo**:
```markdown
| Rule File | Loads When Editing |
|-----------|-------------------|
| `rules/monorepo/turborepo.md` | `turbo.json`, `package.json` |
| `rules/frontend/react.md` | `apps/frontend/**` |
| `rules/backend/fastapi.md` | `apps/backend/**` |
| `rules/agents/type-safety.md` | `packages/shared-types/**` |
```

**default**:
```markdown
| Rule File | Loads When Editing |
|-----------|-------------------|
| `rules/code-style.md` | All files (no filter) |
| `rules/workflow.md` | All files (no filter) |
| `rules/quality-gates.md` | All files (no filter) |
```

## Acceptance Criteria

- [ ] All 5 template READMEs updated
- [ ] Directory structure documented
- [ ] Path-specific rules table included
- [ ] Benefits explained
- [ ] Template-specific paths accurate

## Notes

- This is Wave 5 (documentation)
- Direct implementation
- Depends on template refactoring completion
- Run after Wave 4 tasks complete
