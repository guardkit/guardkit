---
paths: apps/backend/**/schemas/**
---

# Pydantic Schemas

## Schema Patterns

Pydantic schemas define request/response validation and OpenAPI documentation.

### Base Schema

```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    """Shared properties across schemas"""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
```

### Create Schema

```python
class UserCreate(UserBase):
    """Properties to receive on creation"""
    password: str = Field(..., min_length=8, max_length=100)
```

### Update Schema

```python
from typing import Optional

class UserUpdate(BaseModel):
    """Properties to receive on update (all optional)"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
```

### Response Schema

```python
class UserPublic(UserBase):
    """Properties to return to client"""
    id: int

    class Config:
        from_attributes = True  # For SQLAlchemy models
```

### Database Schema

```python
class UserInDB(UserBase):
    """Additional properties stored in DB"""
    id: int
    hashed_password: str

    class Config:
        from_attributes = True
```

## Validation

### Field Constraints

```python
from pydantic import Field, validator

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    age: int = Field(..., ge=0, le=150)  # Greater/less than or equal
```

### Custom Validators

```python
from pydantic import validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str

    @validator('password')
    def password_strength(cls, v):
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

    @validator('email')
    def email_domain(cls, v):
        allowed_domains = ['example.com', 'test.com']
        domain = v.split('@')[1]
        if domain not in allowed_domains:
            raise ValueError(f'Email domain must be one of {allowed_domains}')
        return v
```

### Root Validators

```python
from pydantic import root_validator

class DateRange(BaseModel):
    start_date: datetime
    end_date: datetime

    @root_validator
    def check_dates(cls, values):
        start = values.get('start_date')
        end = values.get('end_date')
        if start and end and start > end:
            raise ValueError('start_date must be before end_date')
        return values
```

## Nested Schemas

### With Relationships

```python
# app/schemas/post.py
from pydantic import BaseModel
from typing import Optional
from app.schemas.user import UserPublic

class PostBase(BaseModel):
    title: str
    content: str

class PostCreate(PostBase):
    pass

class PostPublic(PostBase):
    id: int
    user: UserPublic  # Nested user schema

    class Config:
        from_attributes = True
```

### With Lists

```python
from typing import List

class UserWithPosts(UserPublic):
    posts: List[PostPublic] = []

    class Config:
        from_attributes = True
```

## Optional Fields

### With Defaults

```python
from typing import Optional

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True  # Default value
```

### With exclude_unset

```python
# In CRUD operation
update_data = user_in.dict(exclude_unset=True)  # Only changed fields

for field, value in update_data.items():
    setattr(user, field, value)
```

## Config Options

### from_attributes (ORM Mode)

```python
class UserPublic(BaseModel):
    id: int
    email: str
    full_name: str

    class Config:
        from_attributes = True  # Convert SQLAlchemy models
```

**Usage**:
```python
# SQLAlchemy model → Pydantic schema
user_db = db.query(User).first()
user_public = UserPublic.from_orm(user_db)
```

### Alias and Serialization

```python
from pydantic import Field

class UserPublic(BaseModel):
    id: int
    email: str
    full_name: str = Field(..., alias="fullName")  # Camel case in API

    class Config:
        populate_by_name = True  # Accept both snake_case and alias
```

### JSON Schema Customization

```python
class UserPublic(BaseModel):
    id: int
    email: EmailStr = Field(..., example="user@example.com")
    full_name: str = Field(..., example="John Doe")

    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "full_name": "John Doe"
            }
        }
```

## OpenAPI Integration

### Schema Titles

```python
class UserCreate(BaseModel):
    """Create a new user"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password (min 8 characters)")

    class Config:
        title = "User Creation Schema"
```

### Response Models in Routes

```python
from fastapi import APIRouter
from app.schemas.user import UserPublic, UserCreate

router = APIRouter()

@router.post("/", response_model=UserPublic, status_code=201)
def create_user(user_in: UserCreate):
    """
    Create new user.

    - **email**: Unique email address
    - **password**: Minimum 8 characters
    - **full_name**: User's full name
    """
    return created_user
```

## Common Patterns

### Pagination Response

```python
from typing import List, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    per_page: int
    items: List[T]

# Usage
class UsersPaginated(PaginatedResponse[UserPublic]):
    pass
```

### Error Response

```python
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None

@router.get("/", responses={404: {"model": ErrorResponse}})
def get_user():
    pass
```

### Success Response

```python
class MessageResponse(BaseModel):
    message: str

@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(user_id: int):
    return {"message": "User deleted successfully"}
```

## Best Practices

### 1. Schema Suffixes
```python
# ✅ Clear naming
class UserCreate(BaseModel): pass
class UserUpdate(BaseModel): pass
class UserPublic(BaseModel): pass
class UserInDB(BaseModel): pass

# ❌ Ambiguous
class User(BaseModel): pass
class UserInput(BaseModel): pass
```

### 2. Shared Base Schemas
```python
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserPublic(UserBase):
    id: int
```

### 3. from_attributes for ORM
```python
class UserPublic(BaseModel):
    class Config:
        from_attributes = True  # For SQLAlchemy
```

### 4. Field Descriptions
```python
email: EmailStr = Field(..., description="User email address")
```

### 5. Exclude Unset on Update
```python
update_data = user_in.dict(exclude_unset=True)
```

## Validation Examples

### Email Validation

```python
from pydantic import EmailStr

class UserCreate(BaseModel):
    email: EmailStr  # Automatic email validation
```

### URL Validation

```python
from pydantic import HttpUrl

class WebsiteCreate(BaseModel):
    url: HttpUrl  # Validates URL format
```

### Enum Validation

```python
from enum import Enum

class UserRole(str, Enum):
    admin = "admin"
    user = "user"
    guest = "guest"

class UserCreate(BaseModel):
    role: UserRole = UserRole.user  # Only allow enum values
```

### Date/Time Validation

```python
from datetime import datetime

class EventCreate(BaseModel):
    title: str
    start_date: datetime
    end_date: datetime

    @root_validator
    def validate_dates(cls, values):
        if values['start_date'] >= values['end_date']:
            raise ValueError('start_date must be before end_date')
        return values
```

## Type Generation for Frontend

FastAPI generates OpenAPI schema automatically. Frontend can generate TypeScript types:

```bash
# Backend exposes
http://localhost:8000/openapi.json

# Frontend generates types
pnpm generate-types
```

**Result**: Fully type-safe frontend ↔ backend communication.
