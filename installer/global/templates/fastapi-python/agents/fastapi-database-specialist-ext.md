# fastapi-database-specialist - Extended Documentation

This file contains detailed examples, patterns, and implementation guides for the fastapi-database-specialist agent.

**Load this file when**: You need comprehensive examples, troubleshooting guidance, or deep implementation details.

**Generated**: 2025-12-05

---


## Code Examples

## Best Practices

1. **Always use async sessions for FastAPI**
   - Use `AsyncSession` from `sqlalchemy.ext.asyncio`
   - Configure async engine with `create_async_engine`
   - Use `async_sessionmaker` for session factory

2. **Prevent N+1 queries**
   - Use `selectinload()` for one-to-many relationships
   - Use `joinedload()` for many-to-one relationships
   - Use `.unique()` after `joinedload()` to deduplicate results

3. **Design indexes strategically**
   - Add indexes to foreign keys
   - Index columns used in WHERE clauses frequently
   - Add composite indexes for multi-column queries
   - Don't over-index (impacts write performance)

4. **Use proper cascade options**
   - `cascade="all, delete-orphan"` for owned relationships
   - `ondelete="CASCADE"` on foreign keys for database-level cascades
   - Consider soft deletes for audit trails

5. **Handle migrations carefully**
   - Test migrations on staging before production
   - Use `op.batch_alter_table()` for SQLite compatibility
   - Include data migrations when needed
   - Always provide downgrade paths

6. **Use database constraints**
   - Define constraints in models AND migrations
   - Use unique constraints for business logic
   - Use check constraints for data validation
   - Leverage database-level defaults