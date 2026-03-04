---
id: TASK-IGR-YQ01
title: Quote glob patterns in rule frontmatter across all templates
status: completed
created: 2026-03-03T00:00:00Z
updated: 2026-03-03T12:00:00Z
completed: 2026-03-03T12:00:00Z
priority: medium
complexity: 2
tags: [graphiti, init, yaml, templates, frontmatter]
task_type: implementation
parent_review: TASK-REV-AE10
feature_id: FEAT-IGR
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: Quote glob patterns in rule frontmatter across all templates

## Description

YAML `safe_load()` interprets unquoted `*` at the start of a value as an alias indicator, causing frontmatter parsing to fail for rule files with glob patterns like `paths: **/*.py`. This results in empty metadata being synced to Graphiti during `guardkit init` Step 2.5 (template sync), losing path-pattern discoverability.

## Root Cause

In `guardkit/knowledge/template_sync.py:79`, `yaml.safe_load(frontmatter_text)` fails when the `paths:` value starts with `*`. YAML spec treats `*` as an alias character.

Only values starting with `*` fail — values like `tasks/**/*` or `apps/backend/**/*.py` parse correctly because `*` isn't the first character of the value token.

## Fix

Wrap all unquoted glob values in the `paths:` frontmatter field with double quotes across all template rule files.

### Before
```yaml
---
paths: **/*.py
---
```

### After
```yaml
---
paths: "**/*.py"
---
```

### For multi-value patterns
```yaml
# Before
---
paths: **/tests/**, **/test_*.py, **/*_test.py, **/conftest.py
---

# After
---
paths: "**/tests/**, **/test_*.py, **/*_test.py, **/conftest.py"
---
```

## Affected Files (25 that currently fail YAML parsing)

### fastapi-python (12 files)
- `.claude/rules/code-style.md`
- `.claude/rules/testing.md`
- `.claude/rules/api/dependencies.md`
- `.claude/rules/api/routing.md`
- `.claude/rules/api/schemas.md`
- `.claude/rules/database/crud.md`
- `.claude/rules/database/migrations.md`
- `.claude/rules/database/models.md`
- `.claude/rules/guidance/database.md`
- `.claude/rules/guidance/fastapi.md`
- `.claude/rules/guidance/testing.md`
- `.claude/rules/patterns/pydantic-constraints.md`

### nextjs-fullstack (11 files)
- `.claude/rules/code-style.md`
- `.claude/rules/testing.md`
- `.claude/rules/api/routes.md`
- `.claude/rules/auth/nextauth.md`
- `.claude/rules/database/prisma.md`
- `.claude/rules/guidance/react-state.md`
- `.claude/rules/guidance/server-actions.md`
- `.claude/rules/guidance/server-components.md`
- `.claude/rules/server/actions.md`
- `.claude/rules/server/components.md`
- `.claude/rules/server/streaming.md`

### react-fastapi-monorepo (2 files — only those starting with `*`)
- `.claude/rules/guidance/docker.md`
- `.claude/rules/monorepo/docker.md`

## Additional Files to Quote for Consistency (13 files)

These don't fail YAML parsing today (value doesn't start with `*`), but should be quoted for consistency and to prevent breakage if patterns are reordered:

### default (2 files)
- `.claude/rules/quality-gates.md`
- `.claude/rules/workflow.md`

### fastmcp-python (3 files)
- `.claude/rules/mcp-patterns.md`
- `.claude/rules/security.md`
- `.claude/rules/testing.md`

### react-fastapi-monorepo (8 files)
- `.claude/rules/backend/database.md`
- `.claude/rules/backend/fastapi.md`
- `.claude/rules/backend/schemas.md`
- `.claude/rules/frontend/query.md`
- `.claude/rules/frontend/react.md`
- `.claude/rules/frontend/types.md`
- `.claude/rules/guidance/monorepo.md`
- `.claude/rules/guidance/type-safety.md`
- `.claude/rules/monorepo/turborepo.md`

## Files Already Correct (no changes needed)
- `default/code-style.md` — uses `"**/*.py"` (quoted)
- `mcp-typescript/*` — uses `["src/**/*.ts"]` (JSON array)
- `react-typescript/*` — uses `["**/*.test.*"]` (JSON array)
- `fastmcp-python/config.md`, `fastmcp-python/docker.md` — already quoted

## Regression Risk

**LOW**: The `default` template already uses quoted paths (`"**/*.py"`) and works with Claude Code rule activation. Quoting does not change the parsed string value — `yaml.safe_load('paths: "**/*.py"')` returns `{'paths': '**/*.py'}` (same value, no quotes in the parsed result).

## Acceptance Criteria

- [x] All 25 currently-failing rule files have quoted `paths:` values
- [x] Additional 13 files quoted for consistency
- [x] Existing test `test_extract_agent_metadata_malformed_frontmatter` still passes
- [x] New test: `test_extract_agent_metadata_with_glob_paths` verifies glob frontmatter parses correctly
- [x] `python3 -c "import yaml; yaml.safe_load('paths: \"**/*.py\"')"` succeeds for all patterns

## Effort Estimate

~1 hour
