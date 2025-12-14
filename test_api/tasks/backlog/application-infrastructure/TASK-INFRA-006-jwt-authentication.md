---
id: TASK-INFRA-006
title: "JWT authentication implementation"
status: backlog
created: 2024-12-14T11:00:00Z
updated: 2024-12-14T11:00:00Z
priority: high
tags: [infrastructure, security, jwt, authentication]
complexity: 6
parent_feature: application-infrastructure
wave: 3
implementation_mode: task-work
conductor_workspace: infra-wave3-auth
estimated_effort: 3h
dependencies: [TASK-INFRA-004, TASK-INFRA-005]
---

# Task: JWT authentication implementation

## Description

Implement JWT-based authentication with access tokens, refresh tokens, and password hashing using bcrypt.

## Technical Requirements

### 1. Security Module (src/core/security.py)

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    type: str  # "access" or "refresh"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> TokenPayload | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return TokenPayload(**payload)
    except JWTError:
        return None
```

### 2. Authentication Dependencies (src/core/dependencies.py)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.core.security import decode_token
from src.users.models import User
from src.users import crud as user_crud

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None or payload.type != "access":
        raise credentials_exception

    user = await user_crud.user.get(db, id=int(payload.sub))
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```

### 3. Token Schemas (src/core/schemas.py)

```python
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str
```

## Acceptance Criteria

- [ ] `src/core/security.py` with JWT functions
- [ ] `src/core/dependencies.py` with auth dependencies
- [ ] `src/core/schemas.py` with token schemas
- [ ] Password hashing with bcrypt (cost factor 12)
- [ ] Access token expiry: 30 minutes (configurable)
- [ ] Refresh token expiry: 7 days (configurable)
- [ ] Token decode returns None on invalid token (no exceptions)

## Test Requirements

- Test password hashing/verification
- Test token creation and decoding
- Test expired token handling
- Test invalid token handling
- Test get_current_user dependency
