---
id: TASK-CMD1-004
title: Condense workflow sections to 3-line summaries
status: completed
created: 2026-01-13T11:35:00Z
priority: medium
tags: [documentation, progressive-disclosure]
complexity: 2
parent: TASK-REV-CMD1
implementation_mode: direct
parallel_group: wave-2
conductor_workspace: claude-md-reduction-wave2-1
---

# Task: Condense workflow sections to 3-line summaries

## Problem Statement

Several sections in root CLAUDE.md duplicate content already available in `docs/` guides. These should be condensed to brief summaries with pointers.

## Acceptance Criteria

- [x] Condense "Incremental Enhancement Workflow" section (3,308 chars → ~200 chars)
- [x] Condense "Template Validation" section (2,600 chars → ~200 chars)
- [x] Condense "Template Philosophy" section (2,730 chars → ~200 chars)
- [x] Condense "Progressive Disclosure" section (2,390 chars → ~200 chars)
- [x] Ensure all pointers reference existing docs

## Implementation Notes

### Section Replacements

**Incremental Enhancement Workflow** (current: 3,308 chars):
```markdown
## Incremental Enhancement Workflow

Enhance agents incrementally via task-based or direct enhancement.
Use `--create-agent-tasks` flag to generate enhancement tasks automatically.
See: [Incremental Enhancement Workflow](docs/workflows/incremental-enhancement-workflow.md)
```

**Template Validation** (current: 2,600 chars):
```markdown
## Template Validation

3-level validation: Automatic (always), Extended (`--validate`), Comprehensive (`/template-validate`).
Reports saved to template directory.
See: [Template Validation Guide](docs/guides/template-validation-guide.md)
```

**Template Philosophy** (current: 2,730 chars):
```markdown
## Template Philosophy

5 high-quality templates for learning: react-typescript, fastapi-python, nextjs-fullstack, react-fastapi-monorepo, default.
Create production templates from your code with `/template-create`.
See: [Template Philosophy Guide](docs/guides/template-philosophy.md)
```

**Progressive Disclosure** (current: 2,390 chars):
```markdown
## Progressive Disclosure

Core files always load; extended files load on-demand (55-60% token reduction).
Default: rules structure (`--no-rules-structure` to opt out).
See: [Rules Structure Guide](docs/guides/rules-structure-guide.md)
```

## Estimated Savings

~5,500 characters total

## Existing Docs (Verified)

- `docs/workflows/incremental-enhancement-workflow.md` (21,225 chars)
- `docs/guides/template-validation-guide.md` (exists)
- `docs/guides/template-philosophy.md` (exists)
- `docs/guides/rules-structure-guide.md` (exists)
