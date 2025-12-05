# fastapi-specialist - Extended Documentation

This file contains detailed examples, patterns, and implementation guides for the fastapi-specialist agent.

**Load this file when**: You need comprehensive examples, troubleshooting guidance, or deep implementation details.

**Generated**: 2025-12-05

---


## Code Examples

## Best Practices

1. **Use async def for I/O operations, def for CPU-bound work**
   - Database queries: `async def`
   - External API calls: `async def`
   - Heavy computations: `def` (runs in thread pool)

2. **Design dependency hierarchy carefully**
   - Generic dependencies at bottom (database session)
   - Authentication in middle
   - Permission checks at top

3. **Use multiple Pydantic schemas per entity**
   - `EntityCreate`: Fields required for creation
   - `EntityUpdate`: All fields optional
   - `EntityInDB`: Includes database-generated fields
   - `EntityPublic`: Safe for API responses

4. **Always specify response_model**
   - Ensures proper serialization
   - Provides automatic API documentation
   - Prevents sensitive data leakage

5. **Use status codes from fastapi.status**
   - More readable than magic numbers
   - Provides autocomplete
   - Self-documenting code

6. **Leverage FastAPI's automatic documentation**
   - Add docstrings to endpoints
   - Use Field() descriptions
   - Provide examples in schemas

## Code Examples