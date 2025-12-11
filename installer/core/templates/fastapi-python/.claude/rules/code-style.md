---
paths: **/*.py
---

# Python Code Style and Naming Conventions

## Module and Package Names

```python
# Feature modules use snake_case
src/users/
src/products/
src/order_management/
```

## Class Names

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

## Function Names

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

## File Names

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
