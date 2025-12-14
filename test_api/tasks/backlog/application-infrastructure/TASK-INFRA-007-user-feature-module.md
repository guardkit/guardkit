---
id: TASK-INFRA-007
title: "User feature module"
status: backlog
created: 2024-12-14T11:00:00Z
updated: 2024-12-14T11:00:00Z
priority: high
tags: [infrastructure, users, feature-module, auth]
complexity: 6
parent_feature: application-infrastructure
wave: 3
implementation_mode: task-work
conductor_workspace: infra-wave3-auth
estimated_effort: 3h
dependencies: [TASK-INFRA-006]
---

# Task: User feature module

## Description

Create the complete User feature module following the feature-based architecture pattern with model, schemas, CRUD, service, and router.

## Technical Requirements

### 1. User Model (src/users/models.py)

```python
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from src.core.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
```

### 2. User Schemas (src/users/schemas.py)

```python
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = None


class UserPublic(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class UserInDB(UserPublic):
    hashed_password: str
```

### 3. User CRUD (src/users/crud.py)

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.crud import CRUDBase
from src.core.security import get_password_hash, verify_password
from src.users.models import User
from src.users.schemas import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def authenticate(
        self, db: AsyncSession, *, email: str, password: str
    ) -> User | None:
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


user = CRUDUser(User)
```

### 4. Auth Router (src/users/router.py)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.config import settings
from src.core.security import create_access_token, create_refresh_token, decode_token
from src.core.schemas import Token, TokenRefresh
from src.core.dependencies import get_current_active_user
from src.users.models import User
from src.users.schemas import UserCreate, UserPublic
from src.users import crud as user_crud

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await user_crud.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    return await user_crud.user.create(db, obj_in=user_in)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    user = await user_crud.user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return Token(
        access_token=create_access_token(subject=user.id),
        refresh_token=create_refresh_token(subject=user.id),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
) -> Token:
    payload = decode_token(token_data.refresh_token)
    if payload is None or payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    user = await user_crud.user.get(db, id=int(payload.sub))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return Token(
        access_token=create_access_token(subject=user.id),
        refresh_token=create_refresh_token(subject=user.id),
    )


@router.get("/me", response_model=UserPublic)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
) -> User:
    return current_user
```

### 5. Register Router in main.py

```python
from src.users.router import router as auth_router

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
```

## Acceptance Criteria

- [ ] `src/users/models.py` with User model
- [ ] `src/users/schemas.py` with all user schemas
- [ ] `src/users/crud.py` with CRUDUser class
- [ ] `src/users/router.py` with auth endpoints
- [ ] Endpoints: POST /register, POST /login, POST /refresh, GET /me
- [ ] Email uniqueness enforced
- [ ] Password never returned in responses

## Test Requirements

- Test user registration (success + duplicate email)
- Test login (success + wrong password + wrong email)
- Test token refresh (success + invalid token)
- Test /me endpoint (authenticated + unauthenticated)
