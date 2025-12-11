---
paths: **/tests/**, **/test_*.py, **/*_test.py, **/conftest.py
---

# Testing Patterns

## Async Test Client

```python
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.fixture
async def client():
    """Async HTTP client for testing API endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    """Test user creation endpoint."""
    response = await client.post(
        "/api/v1/users/",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword123",
            "full_name": "Test User"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "password" not in data  # Ensure password not in response
```

## Database Fixtures

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.db.base import Base
from src.main import app
from src.db.session import get_db

# Test database URL (use in-memory SQLite or separate test DB)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create test database and tables."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with TestSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest.fixture
def override_get_db(test_db: AsyncSession):
    """Override get_db dependency with test database."""
    async def _override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()
```

## Factory Fixtures

```python
import pytest
from src.users.models import User
from src.users.schemas import UserCreate

@pytest.fixture
async def create_user(test_db: AsyncSession):
    """Factory fixture to create test users."""
    async def _create_user(**kwargs):
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123",
            "full_name": "Test User",
            **kwargs
        }
        user = User(**user_data)
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        return user

    return _create_user

@pytest.mark.asyncio
async def test_get_user(client: AsyncClient, create_user, override_get_db):
    """Test retrieving a user."""
    user = await create_user(email="specific@example.com")

    response = await client.get(f"/api/v1/users/{user.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user.id
    assert data["email"] == "specific@example.com"
```

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
