---
paths: apps/backend/**/models/**, apps/backend/**/crud/**
---

# Database Layer

## SQLAlchemy Models

### Base Configuration

```python
# app/db/base.py
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
```

### Session Management

```python
# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,  # Verify connections before use
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
```

## Model Patterns

### Basic Model

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

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Model with Relationships

```python
# app/models/post.py
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="posts")
```

```python
# app/models/user.py (updated)
class User(Base):
    __tablename__ = "users"
    # ... other columns ...

    # Relationships
    posts = relationship("Post", back_populates="user")
```

## CRUD Operations

### Read Operations

```python
# app/crud/user.py
from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.user import User

def get_user(db: Session, user_id: int) -> Optional[User]:
    """Get single user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100
) -> List[User]:
    """Get all users with pagination"""
    return db.query(User).offset(skip).limit(limit).all()

def get_active_users(db: Session) -> List[User]:
    """Get all active users"""
    return db.query(User).filter(User.is_active == True).all()
```

### Create Operations

```python
from app.schemas.user import UserCreate
from app.core.security import get_password_hash

def create_user(db: Session, user_in: UserCreate) -> User:
    """Create new user"""
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
```

### Update Operations

```python
from app.schemas.user import UserUpdate

def update_user(
    db: Session,
    user: User,
    user_in: UserUpdate
) -> User:
    """Update existing user"""
    update_data = user_in.dict(exclude_unset=True)

    # Handle password separately
    if "password" in update_data:
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password

    # Update fields
    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    return db_user
```

### Delete Operations

```python
def delete_user(db: Session, user: User) -> None:
    """Delete user"""
    db.delete(user)
    db.commit()

def soft_delete_user(db: Session, user: User) -> User:
    """Soft delete user (mark as inactive)"""
    user.is_active = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

## Query Patterns

### Filtering

```python
# Simple filter
users = db.query(User).filter(User.is_active == True).all()

# Multiple filters
users = db.query(User).filter(
    User.is_active == True,
    User.email.like("%@example.com")
).all()

# OR conditions
from sqlalchemy import or_

users = db.query(User).filter(
    or_(
        User.email == "test@example.com",
        User.full_name == "Test User"
    )
).all()
```

### Ordering

```python
# Ascending
users = db.query(User).order_by(User.created_at).all()

# Descending
users = db.query(User).order_by(User.created_at.desc()).all()

# Multiple fields
users = db.query(User).order_by(
    User.is_active.desc(),
    User.created_at
).all()
```

### Pagination

```python
def get_users_paginated(
    db: Session,
    page: int = 1,
    per_page: int = 20
) -> List[User]:
    """Get users with pagination"""
    skip = (page - 1) * per_page
    return db.query(User).offset(skip).limit(per_page).all()
```

### Counting

```python
# Count all
total = db.query(User).count()

# Count with filter
active_count = db.query(User).filter(User.is_active == True).count()
```

### Joins

```python
# Inner join
results = db.query(User, Post).join(Post).all()

# Left outer join
results = db.query(User).outerjoin(Post).all()

# With filter on joined table
users_with_posts = (
    db.query(User)
    .join(Post)
    .filter(Post.title.like("%Python%"))
    .all()
)
```

## Transactions

### Commit Pattern

```python
def create_user_with_post(
    db: Session,
    user_in: UserCreate,
    post_in: PostCreate
) -> User:
    """Create user and post in single transaction"""
    try:
        # Create user
        user = User(**user_in.dict())
        db.add(user)
        db.flush()  # Get user.id without committing

        # Create post with user.id
        post = Post(**post_in.dict(), user_id=user.id)
        db.add(post)

        # Commit both
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise
```

### Rollback Pattern

```python
def update_user_safe(
    db: Session,
    user: User,
    user_in: UserUpdate
) -> User:
    """Update with rollback on error"""
    try:
        for field, value in user_in.dict(exclude_unset=True).items():
            setattr(user, field, value)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
```

## Database Migrations (Alembic)

### Create Migration

```bash
cd apps/backend

# Auto-generate migration
alembic revision --autogenerate -m "Add users table"

# Manual migration
alembic revision -m "Add custom index"
```

### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific version
alembic upgrade abc123

# Downgrade
alembic downgrade -1
```

### Migration Script

```python
# alembic/versions/abc123_add_users_table.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

def downgrade():
    op.drop_index('ix_users_email')
    op.drop_table('users')
```

## Best Practices

### 1. Use Type Hints
```python
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()
```

### 2. Indexes on Foreign Keys
```python
class Post(Base):
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
```

### 3. Timestamps
```python
created_at = Column(DateTime(timezone=True), server_default=func.now())
updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 4. Soft Deletes
```python
is_active = Column(Boolean, default=True)
deleted_at = Column(DateTime(timezone=True), nullable=True)
```

### 5. Pagination
```python
def get_items(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Item).offset(skip).limit(limit).all()
```

## Troubleshooting

### Issue: Connection pool exhausted
**Solution**: Increase pool size
```python
engine = create_engine(
    SQLALCHEMY_DATABASE_URI,
    pool_size=20,
    max_overflow=40
)
```

### Issue: Stale data after update
**Solution**: Use `db.refresh(obj)`
```python
db.commit()
db.refresh(user)
return user
```

### Issue: Migration conflicts
**Solution**: Resolve manually or regenerate
```bash
alembic history
alembic downgrade base
alembic revision --autogenerate -m "Fresh migration"
```
