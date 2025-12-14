---
paths: **/router*.py, **/routes/**, **/api/**/*.py, **/main.py
---

# FastAPI Routing Patterns

## Async Route Patterns

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

## Avoid Blocking Operations

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

## Route Organization

- Group routes by feature in separate files
- Use APIRouter for modular organization
- Include tags for OpenAPI documentation
- Use proper HTTP status codes

## Error Handling

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

## Creating New Endpoints

### Step-by-step workflow:

```python
# 1. Create feature directory
mkdir -p src/{{feature_name}}
touch src/{{feature_name}}/{router,schemas,models,crud,service,dependencies}.py

# 2. Define router
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
