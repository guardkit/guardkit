---
paths: **/schemas.py, **/schema.py, **/models/schemas.py
---

# Pydantic Schema Patterns

## Multiple Schemas for Different Use Cases

Create separate schemas for different operations:

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

## Custom Pydantic Validators

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

## Schema Naming Convention

Follow these patterns for schema names:

- **Base**: `{Entity}Base` - Shared fields
- **Create**: `{Entity}Create` - Input for creation
- **Update**: `{Entity}Update` - Input for updates (optional fields)
- **InDB**: `{Entity}InDB` - Full database representation
- **Public**: `{Entity}Public` - Public API response
- **List**: `{Entity}List` - For paginated responses

## Defining New Schemas

### Step-by-step workflow:

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

## Best Practices

1. **Separate input/output schemas** - Never expose database models directly
2. **Use Field() for validation** - Add constraints directly in schema
3. **Use EmailStr, HttpUrl** - Leverage Pydantic's built-in types
4. **from_attributes = True** - Required for SQLAlchemy ORM compatibility
5. **Optional fields for updates** - Use `Optional[T] = None` for PATCH endpoints
