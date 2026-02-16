---
paths: **/tests/**, **/test_*.py, **/*_test.py, **/conftest.py
---

# Testing Patterns

## Trophy Testing Model

This template follows **Kent C. Dodds' Trophy testing model** for client-facing applications:

```
        🏆  E2E (~10%)
      ___________
    /             \
   | Feature/       |
   | Integration    |    ← Primary investment (~50%)
   | Tests          |
    \_____________/
     Unit Tests (~30%)
      ___________
     Static/Types (~10%)
```

**Testing Distribution:**
- **50% Feature/Integration Tests**: Test API endpoints with TestClient (HTTP boundary)
- **30% Unit Tests**: Complex business logic (calculations, validations, parsers)
- **10% E2E Tests**: Critical API workflows only (auth flow, payment processing)
- **10% Static Analysis**: Pydantic validation, mypy type checking

**Key Principle:** Test user-facing behavior through the HTTP API. Mock external services at protocol level (database in test mode, third-party APIs with real HTTP mocks). DO NOT mock internal functions/services. Focus on testing behavior, not implementation details.

## Async Test Client

**Pattern**: Async HTTP client fixture with FastAPI TestClient using httpx.AsyncClient
**See**: [../agents/fastapi-testing-specialist.md](../agents/fastapi-testing-specialist.md) for complete fixture examples and test patterns

## Database Fixtures

**Pattern**: Async test database setup with SQLite in-memory engine, automatic table creation/cleanup, and FastAPI dependency override
**See**: [../agents/fastapi-testing-specialist.md](../agents/fastapi-testing-specialist.md) for complete test_db and override_get_db fixture examples

## Factory Fixtures

**Pattern**: Reusable factory fixtures with **kwargs for test data customization, automatic database commit and refresh
**See**: [../agents/fastapi-testing-specialist.md](../agents/fastapi-testing-specialist.md) for factory fixture patterns with user_factory and post_factory examples

## Development Workflow

### Create New Feature Tests

```bash
# Create test directory structure
mkdir -p tests/{{feature_name}}
touch tests/{{feature_name}}/{test_router,test_crud,test_service}.py
```

### Example Test Structure

```python
# tests/{{feature_name}}/test_router.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_{{entity_name}}(client: AsyncClient):
    response = await client.post(
        "/api/v1/{{entity_name_plural}}/",
        json={...}
    )
    assert response.status_code == 201
```

## Testing Checklist

For every API feature/user story, ensure:
- [ ] **Feature/Integration Test**: At least one test using TestClient (HTTP boundary)
- [ ] **Unit Tests**: Only for complex business logic (calculations, validators, parsers)
- [ ] **Contract Tests**: For third-party API integrations (use WireMock or responses library)
- [ ] **E2E Test**: Only for critical workflows (auth, payment, data pipelines)
- [ ] **Static Analysis**: Pydantic schemas validate request/response data

**What to Test:**
- API endpoints through TestClient (50% of tests)
- Complex business logic in service layer (30% of tests)
- Third-party integrations with HTTP mocks (contract tests)
- Critical workflows end-to-end (10% of tests)

**What NOT to Test:**
- FastAPI routing logic (framework-tested)
- Pydantic validation (library-tested)
- Simple CRUD operations without business logic
- Database ORM behavior (SQLAlchemy-tested)

**When Seam Tests ARE Needed:**
- Third-party API integrations (Stripe, SendGrid, external services) - test at protocol/seam boundary
- Microservice boundaries (when calling other internal services)
- Message queue consumers/producers (Kafka, RabbitMQ)
