# Feature: FastAPI Template Fixes

## Problem Statement

The fastapi-python template has significant integration issues discovered during real-world testing:

1. **Authentication broken** - passlib incompatible with bcrypt 5.x
2. **Data doesn't persist** - Transaction handling inconsistent
3. **Projects fail to start** - Missing dependencies
4. **Migrations fail** - Incomplete alembic.ini
5. **Developer confusion** - Poor venv documentation
6. **Schema validation errors** - Over-constrained Pydantic models

These issues cause new projects to fail immediately and require 2-4 hours of debugging.

## Solution

Fix the template with 6 targeted improvements:

| Issue | Fix | Priority |
|-------|-----|----------|
| bcrypt/passlib | Replace with direct bcrypt | Critical |
| Transaction handling | Auto-commit in get_db() | Critical |
| Missing dependencies | Complete pyproject.toml | High |
| Alembic logging | Complete alembic.ini | Medium |
| Venv documentation | Enhanced README | Medium |
| Schema constraints | Pattern guide | Low |

## Impact

| Metric | Before | After |
|--------|--------|-------|
| Project setup time | 2-4 hours | 5-10 minutes |
| Runtime failures | 100% | <1% |
| Data integrity issues | 30-40% | <1% |

## Subtasks

| ID | Title | Priority | Wave | Mode |
|----|-------|----------|------|------|
| [TASK-TPL-001](./TASK-TPL-001-replace-passlib-with-bcrypt.md) | Replace passlib with direct bcrypt | Critical | 1 | task-work |
| [TASK-TPL-002](./TASK-TPL-002-fix-transaction-handling.md) | Fix transaction handling architecture | Critical | 1 | task-work |
| [TASK-TPL-003](./TASK-TPL-003-create-pyproject-toml-template.md) | Create complete pyproject.toml template | High | 1 | task-work |
| [TASK-TPL-004](./TASK-TPL-004-add-alembic-ini-template.md) | Add complete alembic.ini template | Medium | 2 | direct |
| [TASK-TPL-005](./TASK-TPL-005-enhance-readme-venv-emphasis.md) | Enhance README with venv emphasis | Medium | 2 | direct |
| [TASK-TPL-006](./TASK-TPL-006-add-pydantic-constraints-guide.md) | Add pydantic-constraints.md pattern guide | Low | 2 | direct |

## Execution Strategy

### Wave 1: Critical (Parallel)
- 3 tasks can run in parallel using Conductor
- Addresses blocking issues
- Workspaces: `fastapi-fixes-wave1-{1,2,3}`

### Wave 2: Quality-of-Life (Parallel)
- 3 tasks can run in parallel
- Addresses developer experience
- Workspaces: `fastapi-fixes-wave2-{1,2,3}`

## Getting Started

```bash
# Option 1: Sequential execution
/task-work TASK-TPL-001
/task-work TASK-TPL-002
/task-work TASK-TPL-003
# ... continue with Wave 2

# Option 2: Parallel with Conductor
conductor spawn fastapi-fixes-wave1-1 "/task-work TASK-TPL-001"
conductor spawn fastapi-fixes-wave1-2 "/task-work TASK-TPL-002"
conductor spawn fastapi-fixes-wave1-3 "/task-work TASK-TPL-003"
```

## Source

- **Parent Review:** [TASK-REV-A7F3](./../TASK-REV-A7F3-fastapi-template-integration-issues.md)
- **Review Report:** [.claude/reviews/TASK-REV-A7F3-fastapi-template-review.md](../../../.claude/reviews/TASK-REV-A7F3-fastapi-template-review.md)
- **Integration Issues:** From `guardkit_testing/simple-feature_success/integration_issues.md`

## Related Files

- `installer/core/templates/fastapi-python/` - Template directory
- `installer/core/templates/fastapi-python/manifest.json` - Template metadata
- `installer/core/templates/fastapi-python/templates/` - Code templates
