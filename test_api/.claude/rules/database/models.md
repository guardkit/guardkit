---
paths: **/models/*.py, **/models.py, **/db/**
---

# SQLAlchemy Model Patterns

## Database Model Pattern

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

## Model Definition Best Practices

1. **Use singular names** for model classes (`User`, not `Users`)
2. **__tablename__** should be plural (`users`)
3. **Add indexes** on frequently queried columns
4. **Use nullable=False** for required fields
5. **Add created_at/updated_at** for audit trails
6. **Define relationships** with `back_populates` for bidirectional

## Relationships

```python
# One-to-Many
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    author = relationship("User", back_populates="posts")

# Many-to-Many
from sqlalchemy import Table

post_tags = Table(
    'post_tags',
    Base.metadata,
    Column('post_id', Integer, ForeignKey('posts.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class Post(Base):
    # ...
    tags = relationship("Tag", secondary=post_tags, back_populates="posts")

class Tag(Base):
    __tablename__ = "tags"
    # ...
    posts = relationship("Post", secondary=post_tags, back_populates="tags")
```

## Database Session Management

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

## Creating New Models

### Step-by-step workflow:

```python
# 1. Define model
# src/{{feature_name}}/models.py
from sqlalchemy import Column, Integer, String
from src.db.base import Base

class {{EntityName}}(Base):
    __tablename__ = "{{table_name}}"

    id = Column(Integer, primary_key=True)
    # Add fields...

# 2. Create migration
# alembic revision --autogenerate -m "Add {{feature_name}} table"

# 3. Review and apply migration
# alembic upgrade head
```

## Common Column Types

```python
from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, Date, Time, Float, Numeric,
    JSON, ARRAY, Enum
)

# Text columns
name = Column(String(100))  # VARCHAR with limit
description = Column(Text)  # Unlimited text

# Numbers
price = Column(Numeric(10, 2))  # Decimal with precision
quantity = Column(Integer)
rating = Column(Float)

# Dates and times
created_at = Column(DateTime, default=datetime.utcnow)
birth_date = Column(Date)

# Boolean
is_active = Column(Boolean, default=True)

# JSON
metadata = Column(JSON)

# Arrays (PostgreSQL)
tags = Column(ARRAY(String))
```
