# fastapi-testing-specialist - Extended Reference

This file contains detailed documentation for the `fastapi-testing-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/fastapi-testing-specialist-ext.md
```


## Related Templates

### Primary Templates

1. **templates/testing/conftest.py.template**
   - Demonstrates comprehensive pytest fixture architecture for FastAPI
   - Shows async database setup with SQLite in-memory testing
   - Includes dependency override patterns for FastAPI's dependency injection
   - Factory fixtures for test data creation
   - Relevance: PRIMARY - This is the foundation for all FastAPI testing

2. **templates/testing/test_router.py.template**
   - Complete test suite examples for API endpoint testing
   - Async test patterns with pytest.mark.asyncio
   - Status code assertions and response validation
   - Error case testing (validation errors, not found scenarios)
   - Relevance: PRIMARY - Shows best practices for endpoint testing

3. **templates/api/router.py.template**
   - Production router code that tests should validate
   - Demonstrates FastAPI dependency injection patterns
   - Shows proper response_model usage for type safety
   - Relevance: SECONDARY - Understanding router structure improves test design

### Supporting Templates

4. **templates/schemas/schemas.py.template**
   - Pydantic schemas used in request/response validation
   - Field validators that should be tested
   - Relevance: SECONDARY - Tests must validate schema constraints

5. **templates/dependencies/dependencies.py.template**
   - FastAPI dependencies that need mocking/testing
   - Custom validators and resource injection patterns
   - Relevance: SECONDARY - Dependencies often need test overrides

6. **templates/crud/crud_base.py.template**
   - CRUD operations that should be tested at unit level
   - Generic typing patterns for database operations
   - Relevance: TERTIARY - Understanding CRUD helps write better integration tests


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat fastapi-testing-specialist-ext.md
```

Or in Claude Code:
```
Please read fastapi-testing-specialist-ext.md for detailed examples.
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat fastapi-testing-specialist-ext.md
```

Or in Claude Code:
```
Please read fastapi-testing-specialist-ext.md for detailed examples.
```
