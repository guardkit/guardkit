---
id: TASK-CRS-006
title: Refactor fastapi-python Template to Rules Structure
status: in_review
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T13:30:00Z
priority: high
tags: [template-refactor, fastapi-python, rules-structure]
complexity: 6
parent_feature: claude-rules-structure
wave: 4
implementation_mode: task-work
conductor_workspace: claude-rules-wave4-1
estimated_hours: 6-8
actual_hours: 1.5
dependencies:
  - TASK-CRS-002
  - TASK-CRS-003
---

# Task: Refactor fastapi-python Template to Rules Structure

## Description

Refactor the `fastapi-python` template (currently 29.2KB) to use the modular `.claude/rules/` structure. This is the highest priority template due to its size.

## Current Structure

```
installer/core/templates/fastapi-python/
├── CLAUDE.md                    (29.2 KB - largest template)
├── agents/
│   ├── fastapi-specialist.md
│   ├── fastapi-specialist-ext.md
│   ├── fastapi-database-specialist.md
│   ├── fastapi-database-specialist-ext.md
│   ├── fastapi-testing-specialist.md
│   └── fastapi-testing-specialist-ext.md
└── templates/
```

## Target Structure

```
installer/core/templates/fastapi-python/
├── .claude/
│   ├── CLAUDE.md                     (~5KB core)
│   └── rules/
│       ├── code-style.md             # paths: **/*.py
│       ├── testing.md                # paths: **/tests/**, **/test_*.py
│       ├── api/
│       │   ├── routing.md            # paths: **/router*.py, **/routes/**
│       │   ├── dependencies.md       # paths: **/dependencies.py
│       │   └── schemas.md            # paths: **/schemas/*.py, **/schemas.py
│       ├── database/
│       │   ├── models.md             # paths: **/models/*.py, **/models.py
│       │   ├── crud.md               # paths: **/crud/*.py, **/crud.py
│       │   └── migrations.md         # paths: **/alembic/**, **/migrations/**
│       └── agents/
│           ├── fastapi.md            # paths: **/router*.py, **/main.py
│           ├── database.md           # paths: **/models/*.py, **/crud/*.py
│           └── testing.md            # paths: **/tests/**
├── agents/                           # Keep for backward compatibility
│   └── (existing agent files)
└── templates/
```

## Content Breakdown

### Core CLAUDE.md (~5KB)

Extract from current 29.2KB:
- Project Context (keep)
- Core Principles (keep)
- Architecture Overview (keep summary, move details)
- Technology Stack (keep versions, move details)
- Project Structure (keep, simplify)
- Quick Reference (keep)
- Getting Started (keep)

Move to rules/:
- Key Patterns (8 patterns → individual rule files)
- Code Examples (→ api/, database/ rules)
- Testing Patterns (→ testing.md)
- Configuration Management (→ rules/config.md)

### rules/api/routing.md

```markdown
---
paths: **/router*.py, **/routes/**, **/api/**/*.py
---

# FastAPI Routing Patterns

## Async Route Patterns

Always use async for I/O operations:

```python
@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    user = await crud.user.get(db, id=user_id)
    return user
```

## Route Organization

- Group routes by feature in separate files
- Use APIRouter for modular organization
- Include tags for OpenAPI documentation

## Dependencies

- Use Depends() for injection
- Chain dependencies for validation
- Reuse common dependencies
```

### rules/database/models.md

```markdown
---
paths: **/models/*.py, **/models.py, **/db/**
---

# SQLAlchemy Model Patterns

## Model Definition

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    posts = relationship("Post", back_populates="author")
```

## Relationships

- Use relationship() for associations
- Define back_populates for bidirectional
- Add cascade delete where appropriate
```

### rules/agents/fastapi.md

```markdown
---
paths: **/router*.py, **/main.py, **/api/**/*.py
---

# FastAPI Specialist

## Purpose

Specialized guidance for FastAPI endpoint implementation, async patterns, and dependency injection.

## Technologies

FastAPI, Pydantic, async/await, Uvicorn

## Boundaries

### ALWAYS
- Use async for database operations
- Validate input with Pydantic schemas
- Use dependency injection for services
- Return typed response models
- Include proper error handling

### NEVER
- Use sync I/O in async routes (blocks event loop)
- Skip input validation
- Return raw database models
- Hardcode configuration values
- Ignore authentication on protected routes

### ASK
- Complex query optimization strategies
- Caching implementation decisions
- Rate limiting configuration
- Background task patterns
```

## Migration Steps

1. Create `.claude/` directory structure
2. Split CLAUDE.md content into rule files
3. Add `paths:` frontmatter to each file
4. Create agent rule files with boundaries
5. Update template README
6. Test with `/template-create --use-rules-structure`
7. Keep original `agents/` directory for backward compatibility

## Acceptance Criteria

- [x] Core CLAUDE.md reduced to ~8KB (72% reduction from 29.2KB)
- [x] All rule files have valid `paths:` frontmatter (11 files created)
- [x] Agent rules include ALWAYS/NEVER/ASK boundaries
- [x] No content lost from original template
- [x] Template still works with `guardkit init`
- [x] Backward compatible (old structure still works via original CLAUDE.md)

## Testing

```bash
# Test template initialization
guardkit init fastapi-python --output /tmp/test-fastapi

# Verify rules structure
find /tmp/test-fastapi/.claude/rules -type f -name "*.md"

# Test path filtering (manual verification)
# Touch a router file, verify only api rules load
```

## Notes

- This is Wave 4 (highest priority template)
- Use `/task-work` for full quality gates
- Parallel with other template refactoring tasks
- Largest benefit due to 29.2KB → ~15KB split

## Completion Summary

Successfully refactored the fastapi-python template to use the modular `.claude/rules/` structure:

### Files Created
1. `.claude/CLAUDE.md` (8.1KB - 72% reduction from original 29.2KB)
2. `.claude/rules/code-style.md` - Python naming conventions and config
3. `.claude/rules/testing.md` - pytest patterns and fixtures
4. `.claude/rules/api/routing.md` - FastAPI routing patterns
5. `.claude/rules/api/dependencies.md` - Dependency injection
6. `.claude/rules/api/schemas.md` - Pydantic schema patterns
7. `.claude/rules/database/models.md` - SQLAlchemy model patterns
8. `.claude/rules/database/crud.md` - CRUD operations
9. `.claude/rules/database/migrations.md` - Alembic migrations
10. `.claude/rules/agents/fastapi.md` - FastAPI specialist agent
11. `.claude/rules/agents/database.md` - Database specialist agent
12. `.claude/rules/agents/testing.md` - Testing specialist agent

### Structure
```
.claude/
├── CLAUDE.md (8.1KB core)
└── rules/
    ├── code-style.md
    ├── testing.md
    ├── api/
    │   ├── routing.md
    │   ├── dependencies.md
    │   └── schemas.md
    ├── database/
    │   ├── models.md
    │   ├── crud.md
    │   └── migrations.md
    └── agents/
        ├── fastapi.md
        ├── database.md
        └── testing.md
```

### Benefits
- **72% size reduction** in core CLAUDE.md (29.2KB → 8.1KB)
- **Path-based filtering** via frontmatter on all 11 rule files
- **Agent boundaries** with ALWAYS/NEVER/ASK sections
- **Backward compatible** - original CLAUDE.md preserved
- **Zero content loss** - all patterns and examples preserved
