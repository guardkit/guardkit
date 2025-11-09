# FastAPI Python Backend Template

## Project Context

This is a **production-ready FastAPI backend template** based on best practices from the [fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) repository (12k+ stars). The template implements patterns proven in production startup environments, with emphasis on scalability, maintainability, and developer experience.

## Core Principles

1. **Feature-Based Organization**: Structure by domain/feature rather than by file type
2. **Async-First**: Leverage FastAPI's async capabilities for I/O-bound operations
3. **Type Safety**: Comprehensive use of Pydantic for validation and type hints
4. **Dependency Injection**: Reusable dependencies for clean, testable code
5. **Production Ready**: Database migrations, proper error handling, testing infrastructure

## Architecture Overview

### Netflix Dispatch-Inspired Structure

```
{{ProjectName}}/
├── src/
│   ├── {{feature_name}}/         # Feature modules (users, products, orders, etc.)
│   │   ├── router.py             # API endpoints
│   │   ├── schemas.py            # Pydantic models
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── crud.py               # Database operations
│   │   ├── service.py            # Business logic
│   │   ├── dependencies.py       # FastAPI dependencies
│   │   ├── constants.py          # Feature-specific constants
│   │   ├── exceptions.py         # Custom exceptions
│   │   ├── config.py             # Feature-specific config
│   │   └── utils.py              # Helper functions
│   │
│   ├── core/                     # Global configuration
│   │   ├── config.py             # App-wide settings
│   │   ├── security.py           # Authentication/Authorization
│   │   └── logging.py            # Logging configuration
│   │
│   ├── db/                       # Database infrastructure
│   │   ├── base.py               # SQLAlchemy base
│   │   ├── session.py            # Session management
│   │   └── migrations/           # Alembic migrations
│   │
│   ├── main.py                   # FastAPI app initialization
│   ├── config.py                 # Global config
│   ├── database.py               # DB connection setup
│   ├── models.py                 # Shared models
│   ├── exceptions.py             # Global exceptions
│   └── pagination.py             # Pagination helpers
│
├── tests/                        # Test structure mirrors src/
│   ├── {{feature_name}}/
│   │   ├── test_router.py
│   │   ├── test_crud.py
│   │   └── test_service.py
│   └── conftest.py               # Shared fixtures
│
├── alembic/                      # Database migrations
│   ├── versions/
│   └── env.py
│
├── requirements/                 # Split requirements
│   ├── base.txt                  # Production dependencies
│   ├── dev.txt                   # Development dependencies
│   └── prod.txt                  # Production-only dependencies
│
├── .env                          # Environment variables
├── alembic.ini                   # Alembic configuration
├── logging.ini                   # Logging configuration
└── pyproject.toml                # Project metadata and tools

```

### Layer Responsibilities

**API Layer (`router.py`)**:
- HTTP endpoint definitions
- Request/response handling
- Dependency injection
- Route-level validation

**Schema Layer (`schemas.py`)**:
- Pydantic models for validation
- Request/response serialization
- Type definitions
- Data transformation

**Model Layer (`models.py`)**:
- SQLAlchemy ORM models
- Database table definitions
- Relationships and constraints
- Database-level validations

**CRUD Layer (`crud.py`)**:
- Database query operations
- Create, Read, Update, Delete
- Generic base CRUD classes
- Repository pattern implementation

**Service Layer (`service.py`)**:
- Business logic
- Complex operations
- Cross-entity orchestration
- External service integration

**Dependencies Layer (`dependencies.py`)**:
- Reusable dependency functions
- Authentication checks
- Database session management
- Request validation

## Technology Stack

### Core Framework
- **FastAPI** (>=0.104.0): Modern, fast web framework
- **Uvicorn**: ASGI server for production
- **Pydantic** (>=2.0.0): Data validation and settings

### Database
- **SQLAlchemy** (>=2.0.0): ORM for database operations
- **Alembic** (>=1.12.0): Database migration tool
- **asyncpg**: Async PostgreSQL driver (recommended)

### Testing
- **pytest** (>=7.4.0): Testing framework
- **pytest-asyncio** (>=0.21.0): Async test support
- **httpx** (>=0.25.0): Async HTTP client for testing
- **pytest-cov**: Code coverage reporting

### Code Quality
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checker
- **pre-commit**: Git hooks for code quality

## Naming Conventions

### Module and Package Names
```python
# Feature modules use snake_case
src/users/
src/products/
src/order_management/
```

### Class Names
```python
# SQLAlchemy models - PascalCase, singular
class User(Base):
    pass

class Product(Base):
    pass

# Pydantic schemas - PascalCase with type suffix
class UserCreate(BaseModel):
    pass

class UserUpdate(BaseModel):
    pass

class UserInDB(BaseModel):
    pass

class UserPublic(BaseModel):
    pass

# Service classes - PascalCase with Service suffix
class UserService:
    pass

class EmailService:
    pass
```

### Function Names
```python
# Functions use snake_case
def get_user_by_id(user_id: int):
    pass

def create_product(product_data: ProductCreate):
    pass

# Dependencies use get_ prefix
def get_db():
    pass

def get_current_user():
    pass

def get_settings():
    pass
```

### File Names
```python
# Standard file names per feature
router.py          # API routes
schemas.py         # Pydantic models
models.py          # Database models
crud.py            # Database operations
service.py         # Business logic
dependencies.py    # Dependency functions
constants.py       # Constants
exceptions.py      # Custom exceptions
utils.py           # Utilities
config.py          # Configuration
```

## Key Patterns and Best Practices

### 1. Async Route Patterns

**Always use async for I/O operations:**
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Use async for database I/O operations."""
    user = await crud.user.get(db, id=user_id)
    return user

@router.post("/users/", status_code=201)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Async route for database writes."""
    user = await crud.user.create(db, obj_in=user_data)
    return user
```

**⚠️ AVOID blocking operations in async routes:**
```python
# ❌ BAD - blocks event loop
@router.get("/bad-example")
async def bad_route():
    time.sleep(10)  # Blocks entire application!
    return {"status": "done"}

# ✅ GOOD - use asyncio.sleep
@router.get("/good-example")
async def good_route():
    await asyncio.sleep(10)  # Non-blocking
    return {"status": "done"}

# ✅ ALSO GOOD - sync route (runs in thread pool)
@router.get("/sync-example")
def sync_route():
    time.sleep(10)  # Blocks only this thread
    return {"status": "done"}
```

### 2. Pydantic Schema Pattern

**Create multiple schemas for different use cases:**
```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

# Base schema with shared fields
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern="^[a-zA-Z0-9_]+$")
    full_name: str = Field(min_length=1, max_length=100)

# Schema for creating user (input)
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=100)

# Schema for updating user (partial input)
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=100)

# Schema for database model (internal)
class UserInDB(UserBase):
    id: int
    hashed_password: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # For SQLAlchemy ORM compatibility

# Schema for public API response (output)
class UserPublic(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
```

**Custom Pydantic validators:**
```python
from pydantic import BaseModel, field_validator, model_validator

class ProductCreate(BaseModel):
    name: str
    price: float
    quantity: int

    @field_validator('price')
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

    @model_validator(mode='after')
    def check_quantity_for_expensive_items(self):
        if self.price > 1000 and self.quantity < 1:
            raise ValueError('Expensive items must have quantity >= 1')
        return self
```

### 3. CRUD Pattern with Generics

**Base CRUD class for reusability:**
```python
from typing import Generic, TypeVar, Type, Optional, List
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**
        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """Get a single record by ID."""
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict
    ) -> ModelType:
        """Update an existing record."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> ModelType:
        """Delete a record."""
        obj = await self.get(db, id=id)
        await db.delete(obj)
        await db.commit()
        return obj
```

**Feature-specific CRUD extending base:**
```python
from src.crud.base import CRUDBase
from src.users.models import User
from src.users.schemas import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Custom method: get user by email."""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_active_users(self, db: AsyncSession) -> List[User]:
        """Custom method: get only active users."""
        result = await db.execute(
            select(User).where(User.is_active == True)
        )
        return result.scalars().all()

# Instantiate CRUD
user = CRUDUser(User)
```

### 4. Dependency Injection Patterns

**Database session dependency:**
```python
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for database session.
    Ensures proper session lifecycle and cleanup.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

**Authentication dependency:**
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user.
    Validates JWT token and returns user from database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await crud.user.get(db, id=int(user_id))
    if user is None:
        raise credentials_exception

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user is active.
    Chains with get_current_user dependency.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```

**Data validation dependency:**
```python
from fastapi import Depends, HTTPException, status
from uuid import UUID

async def valid_user_id(
    user_id: int,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to validate user ID exists.
    Returns user object if found, raises 404 if not.
    """
    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return user

# Usage in router
@router.get("/users/{user_id}")
async def get_user(user: User = Depends(valid_user_id)):
    """
    User validation happens in dependency.
    If we reach here, user definitely exists.
    """
    return user

@router.put("/users/{user_id}")
async def update_user(
    update_data: UserUpdate,
    user: User = Depends(valid_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Reuse same validation across multiple endpoints.
    Dependency ensures user exists before update logic runs.
    """
    updated_user = await crud.user.update(db, db_obj=user, obj_in=update_data)
    return updated_user
```

### 5. Database Session Management

**Async session configuration:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()
```

**Database model pattern:**
```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    posts = relationship("Post", back_populates="author")
```

### 6. Error Handling

**Custom exception classes:**
```python
from fastapi import HTTPException, status

class UserNotFound(HTTPException):
    def __init__(self, user_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )

class EmailAlreadyExists(HTTPException):
    def __init__(self, email: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {email} already exists"
        )

class InsufficientPermissions(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to perform this action"
        )
```

**Global exception handler:**
```python
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from src.core.logging import logger

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    Logs error and returns generic 500 response.
    """
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

### 7. Testing Patterns

**Async test client:**
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

**Database fixtures:**
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

**Factory fixtures:**
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

## Configuration Management

**Base settings with Pydantic:**
```python
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "{{ProjectName}}"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Database
    DATABASE_URL: PostgresDsn

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # External Services
    REDIS_URL: Optional[str] = None
    SENTRY_DSN: Optional[str] = None

    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

## API Versioning

**Router organization:**
```python
from fastapi import APIRouter
from src.users.router import router as users_router
from src.products.router import router as products_router

api_router = APIRouter()

api_router.include_router(
    users_router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    products_router,
    prefix="/products",
    tags=["products"]
)
```

**Main app setup:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.router import api_router
from src.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
```

## Quality Standards

### Code Coverage
- **Minimum Line Coverage**: 80%
- **Minimum Branch Coverage**: 75%
- **Test Categories**: Unit tests, integration tests, API tests

### Type Checking
- **Tool**: mypy
- **Mode**: Strict
- **Coverage**: 100% of code annotated

### Linting
- **Tool**: ruff
- **Rules**: Default + FastAPI best practices
- **Formatting**: ruff format

### Testing Requirements
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term --cov-report=html

# Run specific test file
pytest tests/users/test_router.py -v

# Run async tests
pytest -m asyncio
```

## Development Workflow

### 1. Create New Feature
```bash
# Create feature directory
mkdir -p src/{{feature_name}}
touch src/{{feature_name}}/{router,schemas,models,crud,service,dependencies}.py
```

### 2. Define Database Model
```python
# src/{{feature_name}}/models.py
from sqlalchemy import Column, Integer, String
from src.db.base import Base

class {{EntityName}}(Base):
    __tablename__ = "{{table_name}}"

    id = Column(Integer, primary_key=True)
    # Add fields...
```

### 3. Create Migration
```bash
# Auto-generate migration
alembic revision --autogenerate -m "Add {{feature_name}} table"

# Review and apply migration
alembic upgrade head
```

### 4. Define Pydantic Schemas
```python
# src/{{feature_name}}/schemas.py
from pydantic import BaseModel

class {{EntityName}}Create(BaseModel):
    # Input fields...
    pass

class {{EntityName}}Public(BaseModel):
    # Output fields...
    class Config:
        from_attributes = True
```

### 5. Implement CRUD Operations
```python
# src/{{feature_name}}/crud.py
from src.crud.base import CRUDBase
from .models import {{EntityName}}
from .schemas import {{EntityName}}Create, {{EntityName}}Update

class CRUD{{EntityName}}(CRUDBase[{{EntityName}}, {{EntityName}}Create, {{EntityName}}Update]):
    # Add custom methods if needed
    pass

{{entity_name}} = CRUD{{EntityName}}({{EntityName}})
```

### 6. Create API Endpoints
```python
# src/{{feature_name}}/router.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from . import crud, schemas

router = APIRouter()

@router.get("/", response_model=list[schemas.{{EntityName}}Public])
async def list_{{entity_name_plural}}(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    return await crud.{{entity_name}}.get_multi(db, skip=skip, limit=limit)
```

### 7. Write Tests
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

## Specialized Agents Available

This template works with the following specialized AI agents:

- **fastapi-specialist**: FastAPI patterns, routing, dependencies
- **fastapi-database-specialist**: SQLAlchemy, Alembic, database design
- **fastapi-testing-specialist**: pytest, async testing, fixtures

Use these agents during development for specialized guidance.

## Common Patterns Quick Reference

| Pattern | File | Example |
|---------|------|---------|
| API Endpoint | `router.py` | `@router.get("/users/{id}")` |
| Request Schema | `schemas.py` | `UserCreate(BaseModel)` |
| Response Schema | `schemas.py` | `UserPublic(BaseModel)` |
| DB Model | `models.py` | `class User(Base)` |
| CRUD Operation | `crud.py` | `user.get(db, id=1)` |
| Business Logic | `service.py` | `UserService.register()` |
| Dependency | `dependencies.py` | `get_current_user()` |
| Custom Exception | `exceptions.py` | `UserNotFound(HTTPException)` |
| Test | `tests/*/test_*.py` | `test_create_user()` |

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic V2](https://docs.pydantic.dev/latest/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Original Best Practices Guide](https://github.com/zhanymkanov/fastapi-best-practices)
