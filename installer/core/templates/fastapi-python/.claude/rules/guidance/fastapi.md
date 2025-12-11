---
paths: **/router*.py, **/main.py, **/api/**/*.py
---

# FastAPI Specialist Agent

## Purpose

Specialized guidance for FastAPI endpoint implementation, async patterns, and dependency injection.

## Technologies

FastAPI, Pydantic, async/await, Uvicorn

## Boundaries

### ALWAYS
- ✅ Use async for database operations (prevents blocking event loop)
- ✅ Validate input with Pydantic schemas (type safety and validation)
- ✅ Use dependency injection for services (clean, testable code)
- ✅ Return typed response models (API contract enforcement)
- ✅ Include proper error handling (HTTPException with status codes)

### NEVER
- ❌ Never use sync I/O in async routes (blocks event loop, degrades performance)
- ❌ Never skip input validation (security and data integrity risk)
- ❌ Never return raw database models (exposes internal structure)
- ❌ Never hardcode configuration values (breaks environment separation)
- ❌ Never ignore authentication on protected routes (security vulnerability)

### ASK
- ⚠️ Complex query optimization strategies (multiple approaches, performance trade-offs)
- ⚠️ Caching implementation decisions (in-memory vs Redis vs CDN)
- ⚠️ Rate limiting configuration (threshold values depend on use case)
- ⚠️ Background task patterns (immediate vs queue vs scheduled)

## When This Agent Is Used

This agent provides guidance when working with:
- API endpoint files (`router.py`, `main.py`)
- Route definitions and request handling
- FastAPI dependency injection
- Async/await patterns
- Request/response validation

## Capabilities

1. **Async route implementation** with proper I/O handling
2. **Dependency injection patterns** for authentication and validation
3. **Error handling** with custom exceptions
4. **API versioning** and router organization
5. **Request/response validation** with Pydantic

## Integration with Other Rules

- **Schemas**: Uses Pydantic schemas from `api/schemas.md`
- **Dependencies**: Implements patterns from `api/dependencies.md`
- **Database**: Integrates with CRUD operations from `database/crud.md`
- **Testing**: Tested with patterns from `testing.md`

## See Also

- `.claude/rules/api/routing.md` - Detailed routing patterns
- `.claude/rules/api/dependencies.md` - Dependency injection
- `.claude/rules/api/schemas.md` - Pydantic schema patterns
