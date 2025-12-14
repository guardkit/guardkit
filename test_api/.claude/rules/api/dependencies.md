---
paths: **/dependencies.py, **/deps.py
---

# Dependency Injection Patterns

## Database Session Dependency

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

## Authentication Dependency

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

## Data Validation Dependency

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

## Dependency Chaining

Dependencies can be chained together to create complex validation and authorization flows:

```python
async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Requires both active and superuser status."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges"
        )
    return current_user
```

## Best Practices

1. **Use Depends()** for all shared logic (authentication, database sessions, validation)
2. **Chain dependencies** for complex authorization flows
3. **Raise HTTPException** in dependencies for validation errors
4. **Return validated objects** to make route logic cleaner
5. **Reuse dependencies** across multiple endpoints
