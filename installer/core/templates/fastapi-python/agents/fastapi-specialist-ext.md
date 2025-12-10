# fastapi-specialist - Extended Reference

This file contains detailed documentation for the `fastapi-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/fastapi-specialist-ext.md
```


## When to Use This Agent

Use the FastAPI specialist when you need help with:

- Designing API endpoints and route structure
- Implementing dependency injection patterns
- Creating Pydantic validation schemas
- Writing async routes and handling async operations
- Error handling and exception design
- API documentation and OpenAPI customization
- Performance optimization for FastAPI applications
- Security best practices (CORS, authentication, etc.)

### 1. Complex Dependency Chain

```python
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Validate token and get user
    ...

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

# Use in route
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db)
):
    # Only superusers can delete users
    ...
```

### 2. Advanced Pydantic Validation

```python
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional

class ProductCreate(BaseModel):
    name: str
    price: float
    discount_price: Optional[float] = None
    quantity: int
    category_id: int

    @field_validator('price')
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

    @field_validator('discount_price')
    @classmethod
    def discount_must_be_lower_than_price(cls, v, info):
        if v is not None and 'price' in info.data and v >= info.data['price']:
            raise ValueError('Discount price must be lower than regular price')
        return v

    @model_validator(mode='after')
    def check_stock_for_expensive_items(self):
        if self.price > 1000 and self.quantity < 1:
            raise ValueError('Expensive items must have quantity >= 1')
        return self
```

### 3. Async Route with Concurrent Operations

```python
import asyncio
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Run multiple database queries concurrently
    user_stats, recent_orders, notifications = await asyncio.gather(
        get_user_statistics(db, current_user.id),
        get_recent_orders(db, current_user.id, limit=5),
        get_unread_notifications(db, current_user.id)
    )

    return {
        "user_stats": user_stats,
        "recent_orders": recent_orders,
        "notifications": notifications
    }
```

### 4. Custom Exception Handler

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

app = FastAPI()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_exception",
                "message": exc.detail,
                "status_code": exc.status_code
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "validation_error",
                "message": "Request validation failed",
                "details": exc.errors()
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "internal_server_error",
                "message": "An unexpected error occurred"
            }
        }
    )
```


## Common Patterns

### Pagination
```python
from fastapi import Query

@router.get("/items/")
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    items = await crud.item.get_multi(db, skip=skip, limit=limit)
    return items
```

### File Upload
```python
from fastapi import File, UploadFile

@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    # Process file
    return {"filename": file.filename, "size": len(contents)}
```

### Background Tasks
```python
from fastapi import BackgroundTasks

def send_email(email: str, message: str):
    # Send email (this runs in background)
    ...

@router.post("/send-email/")
async def send_notification(
    email: str,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(send_email, email, "Welcome!")
    return {"message": "Email will be sent in background"}
```


## Related Templates

No matching templates found.

### Example 1: Async Test with TestClient and Fixtures

✅ **DO**: Use async tests with proper fixtures and dependency overrides

```python
import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_item_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_token: str
) -> None:
    """Test successful item creation with authentication."""
    # Arrange
    payload = {
        "name": "Test Item",
        "description": "Test Description",
        "price": 99.99
    }
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Act
    response = await async_client.post(
        "/api/v1/items",
        json=payload,
        headers=headers
    )
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert "id" in data
    assert "created_at" in data
```

❌ **DON'T**: Use synchronous tests or skip fixtures

```python

# Missing async, no fixtures, hardcoded dependencies
def test_create_item():
    client = TestClient(app)  # Synchronous client
    response = client.post("/api/v1/items", json={"name": "Test"})
    assert response.status_code == 201  # No auth, incomplete assertions
```

### Example 2: Conftest Fixtures with Dependency Overrides

✅ **DO**: Create comprehensive fixtures with proper cleanup

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

from app.core.config import settings
from app.db.session import get_db
from app.main import app

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide isolated database session for tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        yield session
        await session.rollback()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest_asyncio.fixture
async def async_client(
    db_session: AsyncSession
) -> AsyncGenerator[AsyncClient, None]:
    """Provide async HTTP client with dependency overrides."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture
def auth_token(db_session: AsyncSession) -> str:
    """Generate test authentication token."""
    # Create test user and generate token
    user = create_test_user(db_session)
    return generate_token(user.id)
```

❌ **DON'T**: Skip cleanup or reuse global state

```python

# Missing cleanup, global state pollution
@pytest.fixture
def client():
    return TestClient(app)  # No dependency override, no cleanup

@pytest.fixture
def db():
    return SessionLocal()  # No transaction rollback, data leaks between tests
```

### Example 3: Parametrized Tests for Multiple Scenarios

✅ **DO**: Use parametrize for comprehensive edge case coverage

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,expected_status,expected_error",
    [
        # Valid cases
        ({"name": "Valid Item", "price": 10.0}, 201, None),
        ({"name": "A" * 100, "price": 0.01}, 201, None),
        
        # Invalid cases
        ({"name": "", "price": 10.0}, 422, "name: field required"),
        ({"name": "Item", "price": -1.0}, 422, "price: must be positive"),
        ({"name": "Item", "price": "invalid"}, 422, "price: not a valid float"),
        ({"name": "A" * 256, "price": 10.0}, 422, "name: max length exceeded"),
    ],
)
async def test_create_item_validation(
    async_client: AsyncClient,
    auth_token: str,
    payload: dict,
    expected_status: int,
    expected_error: str | None
) -> None:
    """Test item creation with various valid and invalid inputs."""
    response = await async_client.post(
        "/api/v1/items",
        json=payload,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == expected_status
    
    if expected_error:
        assert expected_error in response.text
```

❌ **DON'T**: Write separate tests for each validation case

```python

# Repetitive, verbose, harder to maintain
async def test_empty_name():
    # ... duplicate setup code
    assert response.status_code == 422

async def test_negative_price():
    # ... duplicate setup code
    assert response.status_code == 422

# 10+ more similar functions...
```

### Example 4: Testing Error Handling and Edge Cases

✅ **DO**: Test all error paths with specific assertions

```python
import pytest
from httpx import AsyncClient
from unittest.mock import patch

@pytest.mark.asyncio
async def test_database_connection_error(
    async_client: AsyncClient,
    auth_token: str
) -> None:
    """Test graceful handling of database failures."""
    with patch("app.crud.crud_item.get", side_effect=ConnectionError("DB unavailable"))):
        response = await async_client.get(
            "/api/v1/items/1",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 503
        data = response.json()
        assert data["detail"] == "Service temporarily unavailable"
        assert "error_id" in data  # For tracking

@pytest.mark.asyncio
async def test_unauthorized_access(
    async_client: AsyncClient
) -> None:
    """Test endpoint protection without authentication."""
    response = await async_client.get("/api/v1/items")
    
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

@pytest.mark.asyncio
async def test_resource_not_found(
    async_client: AsyncClient,
    auth_token: str
) -> None:
    """Test 404 handling for non-existent resources."""
    response = await async_client.get(
        "/api/v1/items/99999",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"
```

### Example 5: Coverage Strategy with pytest-cov

✅ **DO**: Configure comprehensive coverage with meaningful thresholds

```ini

# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = """
    --strict-markers
    --strict-config
    --cov=app
    --cov-branch
    --cov-report=term-missing:skip-covered
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=80
    -vv
"""

[tool.coverage.run]
source = ["app"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__init__.py",
    "*/config.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

❌ **DON'T**: Run tests without coverage tracking

```bash

# No coverage data, can't identify gaps
pytest tests/
```


## Anti-Patterns to Avoid

### Anti-Pattern 1: Test Interdependence
❌ Tests that rely on execution order or shared state
✅ Each test should be independently runnable

### Anti-Pattern 2: Overmocking
❌ Mocking so much that you're not testing real behavior
✅ Mock external services, but test your actual code paths

### Anti-Pattern 3: Assertion Roulette
❌ Multiple unrelated assertions in one test
✅ One logical concept per test, use parametrize for variations

### Anti-Pattern 4: Test Code Duplication
❌ Copy-pasting test setup across multiple files
✅ Extract common setup into conftest.py fixtures

### Anti-Pattern 5: Ignoring Async/Await
❌ Using sync code in async tests or vice versa
✅ Match your test async patterns to your application code


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat fastapi-specialist-ext.md
```

Or in Claude Code:
```
Please read fastapi-specialist-ext.md for detailed examples.
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat fastapi-specialist-ext.md
```

Or in Claude Code:
```
Please read fastapi-specialist-ext.md for detailed examples.
```
