---
id: TASK-INFRA-008
title: "Testing infrastructure and initial tests"
status: backlog
created: 2024-12-14T11:00:00Z
updated: 2024-12-14T11:00:00Z
priority: high
tags: [infrastructure, testing, pytest, coverage]
complexity: 6
parent_feature: application-infrastructure
wave: 4
implementation_mode: task-work
conductor_workspace: infra-wave4-testing
estimated_effort: 2.5h
dependencies: [TASK-INFRA-007]
---

# Task: Testing infrastructure and initial tests

## Description

Set up comprehensive testing infrastructure with pytest-asyncio, test database isolation, and write initial tests for all implemented components.

## Technical Requirements

### 1. Pytest Configuration (pytest.ini)

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
filterwarnings =
    ignore::DeprecationWarning
```

### 2. Test Fixtures (tests/conftest.py)

```python
import asyncio
from collections.abc import AsyncGenerator
from typing import Generator

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.main import app
from src.database import get_db
from src.core.base import Base
from src.config import settings

# Test database URL (use separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/test_api", "/test_api_test")

engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> dict:
    """Create a test user and return credentials."""
    from src.users import crud as user_crud
    from src.users.schemas import UserCreate

    user_data = UserCreate(
        email="test@example.com",
        password="testpassword123",
        full_name="Test User",
    )
    user = await user_crud.user.create(db_session, obj_in=user_data)
    await db_session.commit()

    return {
        "user": user,
        "email": user_data.email,
        "password": user_data.password,
    }


@pytest.fixture
async def auth_headers(client: AsyncClient, test_user: dict) -> dict:
    """Get authentication headers for test user."""
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        data={"username": test_user["email"], "password": test_user["password"]},
    )
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}
```

### 3. User Router Tests (tests/users/test_router.py)

```python
import pytest
from httpx import AsyncClient

from src.config import settings

API_PREFIX = settings.API_V1_PREFIX


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "newpassword123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: dict):
    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={
            "email": test_user["email"],
            "password": "anotherpassword",
        },
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: dict):
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        data={"username": test_user["email"], "password": test_user["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: dict):
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        data={"username": test_user["email"], "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, auth_headers: dict, test_user: dict):
    response = await client.get(
        f"{API_PREFIX}/auth/me",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get(f"{API_PREFIX}/auth/me")
    assert response.status_code == 401
```

### 4. CRUD Tests (tests/users/test_crud.py)

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.users import crud as user_crud
from src.users.schemas import UserCreate, UserUpdate


@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    user_in = UserCreate(
        email="crud_test@example.com",
        password="testpassword",
        full_name="CRUD Test",
    )
    user = await user_crud.user.create(db_session, obj_in=user_in)
    assert user.email == user_in.email
    assert user.hashed_password != user_in.password


@pytest.mark.asyncio
async def test_get_user_by_email(db_session: AsyncSession, test_user: dict):
    user = await user_crud.user.get_by_email(db_session, email=test_user["email"])
    assert user is not None
    assert user.email == test_user["email"]


@pytest.mark.asyncio
async def test_authenticate_user(db_session: AsyncSession, test_user: dict):
    user = await user_crud.user.authenticate(
        db_session, email=test_user["email"], password=test_user["password"]
    )
    assert user is not None


@pytest.mark.asyncio
async def test_authenticate_wrong_password(db_session: AsyncSession, test_user: dict):
    user = await user_crud.user.authenticate(
        db_session, email=test_user["email"], password="wrongpassword"
    )
    assert user is None
```

## Acceptance Criteria

- [ ] `pytest.ini` configured for async tests
- [ ] `tests/conftest.py` with all fixtures
- [ ] Test database isolation (create/drop per test)
- [ ] `tests/users/test_router.py` - API endpoint tests
- [ ] `tests/users/test_crud.py` - CRUD operation tests
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Coverage ≥80%: `pytest --cov=src --cov-report=term`

## Test Requirements

- Minimum 15 test cases
- Coverage report generated
- No test interdependencies
- Tests can run in parallel

## Quality Gates

```bash
# All tests must pass
pytest tests/ -v

# Coverage must be ≥80%
pytest --cov=src --cov-report=term --cov-fail-under=80

# Type checking
mypy src/ --strict

# Linting
ruff check src/ tests/
```
