---
paths: apps/backend/**/*.py
---

# FastAPI Backend Architecture

## Layered Architecture

FastAPI backend follows Netflix Dispatch-inspired layered architecture:

```
apps/backend/app/
├── api/
│   └── routes/           # API endpoints
│       ├── users.py
│       └── auth.py
├── core/                 # Configuration
│   ├── config.py
│   └── security.py
├── crud/                 # Database operations
│   └── user.py
├── db/                   # Database setup
│   ├── base.py
│   └── session.py
├── models/               # SQLAlchemy models
│   └── user.py
├── schemas/              # Pydantic schemas
│   └── user.py
└── main.py              # Application entry point
```

## Layer Responsibilities

### 1. API Layer (api/routes/)
**Purpose**: HTTP endpoints, request/response handling

```python
# app/api/routes/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.schemas.user import UserPublic, UserCreate, UserUpdate
from app.crud import user as crud_user
from app.api.deps import get_db

router = APIRouter()

@router.get("/", response_model=List[UserPublic])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all users"""
    users = crud_user.get_users(db, skip=skip, limit=limit)
    return users

@router.post("/", response_model=UserPublic, status_code=201)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """Create new user"""
    # Check if user exists
    existing = crud_user.get_user_by_email(db, email=user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = crud_user.create_user(db, user_in=user_in)
    return user

@router.get("/{user_id}", response_model=UserPublic)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get user by ID"""
    user = crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db)
):
    """Update user"""
    user = crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user = crud_user.update_user(db, user=user, user_in=user_in)
    return user

@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Delete user"""
    user = crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    crud_user.delete_user(db, user=user)
```

### 2. Schema Layer (schemas/)
**Purpose**: Request/response validation, OpenAPI generation

```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=8)

class UserPublic(UserBase):
    id: int

    class Config:
        from_attributes = True  # For SQLAlchemy models

class UserInDB(UserBase):
    id: int
    hashed_password: str

    class Config:
        from_attributes = True
```

### 3. Model Layer (models/)
**Purpose**: Database schema, SQLAlchemy ORM

```python
# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 4. CRUD Layer (crud/)
**Purpose**: Database operations, business logic

```python
# app/crud/user.py
from sqlalchemy.orm import Session
from typing import Optional, List

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash

def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user_in: UserCreate) -> User:
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user: User, user_in: UserUpdate) -> User:
    update_data = user_in.dict(exclude_unset=True)

    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password

    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()
```

## Naming Conventions

### Files
- All files: `snake_case.py`
- Example: `user.py`, `database_config.py`

### Code
- **Classes**: `PascalCase`
- **Functions**: `snake_case`
- **Constants**: `SCREAMING_SNAKE_CASE`
- **Database tables**: `snake_case`, plural
- **Models**: `PascalCase`, singular
- **Schemas**: `PascalCase` with suffix

### Schema Naming
```python
class UserCreate(BaseModel):    # Create operation
class UserUpdate(BaseModel):    # Update operation
class UserPublic(BaseModel):    # Public response
class UserInDB(BaseModel):      # Database representation
```

## Router Configuration

```python
# app/api/api.py
from fastapi import APIRouter
from app.api.routes import users, auth

api_router = APIRouter()

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)
```

## Application Entry Point

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

## Dependency Injection

```python
# app/api/deps.py
from typing import Generator
from app.db.session import SessionLocal

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Error Handling

### HTTP Exceptions
```python
from fastapi import HTTPException

@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    return user
```

### Global Exception Handler
```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )
```

## Testing (Trophy Model)

**Backend follows Kent C. Dodds' Trophy testing model:**
- **50% Feature/Integration**: Test through TestClient (HTTP boundary)
- **30% Unit**: Complex business logic (calculations, validators)
- **10% E2E**: Critical API workflows
- **10% Static**: Pydantic schemas, mypy

**Key Principle:** Test through HTTP API with TestClient. DO NOT mock internal services. Mock external APIs at protocol level (WireMock, responses library). Focus on testing behavior, not implementation details.

```python
# tests/test_users.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_user():
    response = client.post(
        "/users/",
        json={
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

def test_get_user():
    response = client.get("/users/1")
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
```

**Testing Checklist:**
- [ ] Feature test for every API endpoint (TestClient)
- [ ] Unit tests for complex business logic only
- [ ] Contract tests for third-party integrations (Stripe, SendGrid)
- [ ] E2E tests for critical workflows only

**When Seam Tests ARE Needed:**
- Third-party API integrations (external services)
- Microservice boundaries (when calling other services)

## Best Practices

### 1. Layer Separation
✅ API → CRUD → Model
❌ API → Model (skip CRUD)

### 2. Schema Suffixes
✅ `UserCreate`, `UserUpdate`, `UserPublic`
❌ `User`, `UserInput`, `UserOutput`

### 3. Response Models
```python
@router.get("/", response_model=List[UserPublic])
def list_users():
    # FastAPI automatically validates response
    return users
```

### 4. Dependency Injection
```python
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pass
```

### 5. Error Handling
```python
# ✅ Specific error codes
raise HTTPException(status_code=404, detail="User not found")

# ❌ Generic errors
raise HTTPException(status_code=500, detail="Error")
```
