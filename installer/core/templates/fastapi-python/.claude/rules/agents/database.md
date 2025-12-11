---
paths: **/models/*.py, **/crud/*.py, **/db/**
---

# Database Specialist Agent

## Purpose

Specialized guidance for SQLAlchemy ORM models, CRUD operations, and database design.

## Technologies

SQLAlchemy 2.0, Alembic, asyncpg, PostgreSQL

## Boundaries

### ALWAYS
- ✅ Use async session for all database operations (non-blocking I/O)
- ✅ Define indexes on frequently queried columns (query performance)
- ✅ Use relationship() with back_populates (bidirectional integrity)
- ✅ Add created_at/updated_at timestamps (audit trail)
- ✅ Use generic CRUD base class (code reuse and consistency)

### NEVER
- ❌ Never expose IQueryable outside repository (breaks encapsulation)
- ❌ Never use raw SQL without parameterization (SQL injection risk)
- ❌ Never ignore database errors silently (data integrity)
- ❌ Never commit transactions within CRUD methods (violates single responsibility)
- ❌ Never use sync database calls in async routes (blocks event loop)

### ASK
- ⚠️ Complex joins across >3 tables (raw SQL vs ORM trade-offs)
- ⚠️ Caching strategy needed (in-memory vs distributed cache)
- ⚠️ Soft delete vs hard delete (data retention policy decision)
- ⚠️ Index strategy for large tables (composite indexes, partial indexes)

## When This Agent Is Used

This agent provides guidance when working with:
- Database model files (`models.py`)
- CRUD operation files (`crud.py`)
- Database session management (`db/session.py`)
- Migration files (`alembic/versions/`)

## Capabilities

1. **SQLAlchemy model design** with relationships and constraints
2. **Generic CRUD patterns** with type safety
3. **Async database operations** using SQLAlchemy 2.0
4. **Database migration** creation and management with Alembic
5. **Query optimization** and indexing strategies

## Integration with Other Rules

- **Models**: Uses patterns from `database/models.md`
- **CRUD**: Implements patterns from `database/crud.md`
- **Migrations**: Follows patterns from `database/migrations.md`
- **Schemas**: Maps to Pydantic schemas from `api/schemas.md`

## See Also

- `.claude/rules/database/models.md` - Model definition patterns
- `.claude/rules/database/crud.md` - CRUD operation patterns
- `.claude/rules/database/migrations.md` - Migration best practices
