---
id: TASK-TPL-002
title: Fix transaction handling architecture with auto-commit pattern
status: completed
created: 2026-01-27T12:45:00Z
updated: 2026-01-27T13:20:00Z
completed: 2026-01-27T13:20:00Z
completed_phases: [2, 2.5B, 3, 4, 5]
architectural_score: 68
code_review_score: 92
priority: critical
tags: [template, fastapi-python, database, transactions, sqlalchemy]
complexity: 5
parent_review: TASK-REV-A7F3
feature_id: FEAT-TPL-FIX
wave: 1
implementation_mode: task-work
dependencies: []
conductor_workspace: fastapi-fixes-wave1-2
completion_summary: |
  Fixed transaction handling in fastapi-python template:
  - get_db() now auto-commits on success, auto-rollbacks on error
  - CRUDBase methods use flush() instead of commit()
  - Custom queries now persist correctly (original issue resolved)
  - Documentation updated with transaction patterns and guidelines
files_modified:
  - installer/core/templates/fastapi-python/templates/db/session.py.template
  - installer/core/templates/fastapi-python/templates/crud/crud_base.py.template
  - installer/core/templates/fastapi-python/.claude/rules/database/crud.md
  - installer/core/templates/fastapi-python/README.md
---

# Task: Fix transaction handling architecture with auto-commit pattern

## Description

Fix the inconsistent transaction handling in the fastapi-python template. Currently, `get_db()` doesn't commit transactions while CRUDBase methods do, creating data integrity issues for custom queries.

## Problem

Current broken pattern:

```python
# session.py.template - NO COMMIT
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# crud_base.py.template - COMPENSATES WITH COMMIT
async def create(...):
    db.add(db_obj)
    await db.commit()  # Each CRUD method commits
```

**Issues:**
- CRUDBase commits work, but custom queries don't persist
- Developers writing custom queries experience silent data loss
- Violates Single Responsibility Principle (two patterns for same concern)
- Violates Interface Segregation (different semantics for same interface)

## Solution

Implement service-level transaction management:

```python
# session.py.template - Auto-commit on success
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Auto-commit on success
        except Exception:
            await session.rollback()  # Rollback on error
            raise
        finally:
            await session.close()
```

```python
# crud_base.py.template - Remove commits, use flush
async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
    obj_data = obj_in.model_dump()
    db_obj = self.model(**obj_data)
    db.add(db_obj)
    await db.flush()  # Flush to get ID, no commit
    await db.refresh(db_obj)
    return db_obj
```

## Acceptance Criteria

- [x] Update `templates/db/session.py.template` with auto-commit pattern
- [x] Update `templates/crud/crud_base.py.template` to use flush() instead of commit()
- [ ] Add explicit transaction context manager for advanced use cases (deferred per YAGNI review)
- [x] Update `.claude/rules/database/` guidance
- [x] Add transaction pattern documentation to README
- [x] Test that single-request transactions work correctly
- [x] Test that errors properly rollback

## Files to Modify

1. `installer/core/templates/fastapi-python/templates/db/session.py.template`
2. `installer/core/templates/fastapi-python/templates/crud/crud_base.py.template`
3. `installer/core/templates/fastapi-python/.claude/rules/database/crud.md`
4. `installer/core/templates/fastapi-python/README.md`

## Advanced Use Case

For complex multi-operation transactions, add helper:

```python
@asynccontextmanager
async def explicit_transaction(db: AsyncSession):
    """Explicit transaction context for complex operations."""
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
```

## Notes

- This is a breaking change for projects relying on per-CRUD-method commits
- Document migration path for existing projects
- Single transaction per request is the FastAPI convention
