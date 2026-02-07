---
paths: **/tests/**, **/test_*.py, **/*_test.py, **/conftest.py
---

# Testing Patterns

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
