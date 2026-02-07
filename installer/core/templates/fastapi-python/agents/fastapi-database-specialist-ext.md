# fastapi-database-specialist - Extended Reference

This file contains detailed documentation for the `fastapi-database-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/fastapi-database-specialist-ext.md
```


## When to Use This Agent

Use the FastAPI database specialist when you need help with:

- Designing SQLAlchemy models and relationships
- Creating and managing Alembic migrations
- Optimizing database queries
- Implementing async database operations
- Transaction management and concurrency
- Database testing strategies

### 1. SQLAlchemy Model with Relationships

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from src.db.base import Base

# Association table for many-to-many
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'))
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # One-to-many relationship
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    # Many-to-many relationship
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    # One-to-one relationship
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
```

### 2. Efficient Async Query with Eager Loading

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user_with_posts(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get user with all posts in single query (no N+1)."""
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.posts))
    )
    return result.scalar_one_or_none()

async def get_posts_with_author_and_comments(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[Post]:
    """Optimized: joinedload for many-to-one, selectinload for one-to-many."""
    result = await db.execute(
        select(Post)
        .options(
            joinedload(Post.author),
            selectinload(Post.comments)
        )
        .offset(skip).limit(limit)
        .order_by(Post.created_at.desc())
    )
    return result.scalars().unique().all()
```

### 3. Alembic Migration with Data Migration

```python
"""Add user roles

Revision ID: abc123
Revises: def456
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session

revision = 'abc123'
down_revision = 'def456'

def upgrade():
    op.create_table('roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table('user_roles',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    # Data migration: create default roles
    bind = op.get_bind()
    session = Session(bind=bind)
    session.execute(
        sa.text("INSERT INTO roles (name, description) VALUES "
                "('admin', 'Administrator with full access'), "
                "('user', 'Regular user'), "
                "('moderator', 'Content moderator')")
    )
    session.commit()

def downgrade():
    op.drop_table('user_roles')
    op.drop_table('roles')
```

### 4. Optimistic Locking with Version Column

```python
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    quantity = Column(Integer, default=0)
    version = Column(Integer, default=1, nullable=False)

async def update_product_quantity(
    db: AsyncSession, product_id: int, new_quantity: int, current_version: int
) -> Product:
    """Update with optimistic locking to prevent concurrent update conflicts."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.version != current_version:
        raise HTTPException(status_code=409, detail="Product was updated by another user.")
    product.quantity = new_quantity
    product.version += 1
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product
```


## Common Patterns

### Database Naming Conventions
```python
from sqlalchemy import MetaData

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)
```

### Soft Delete Pattern
```python
class SoftDeleteMixin:
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

async def soft_delete_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.is_deleted = True
        user.deleted_at = datetime.utcnow()
        await db.commit()
```

### Audit Trail Pattern
```python
class AuditMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
```


## Related Templates

- **templates/models/models.py.template** - SQLAlchemy ORM models with relationships and timestamps
- **templates/db/session.py.template** - Async session management with connection pooling
- **templates/crud/crud_base.py.template** - Generic CRUD base class with type safety
- **templates/crud/crud.py.template** - Feature-specific CRUD extensions
- **templates/core/config.py.template** - Database connection configuration
- **templates/dependencies/dependencies.py.template** - Session injection and validation
- **templates/schemas/schemas.py.template** - Pydantic schemas for ORM validation


## Best Practices

### Async Operations
```python
# DO: async/await for all database operations
async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# DON'T: synchronous operations block the event loop
def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()
```

### Connection Pooling
```python
# DO: configure pool for production
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True, pool_size=10, max_overflow=20
)

# DON'T: default settings can exhaust connections under load
engine = create_async_engine(DATABASE_URL)
```

### Session Management
```python
# DO: use FastAPI dependencies for automatic cleanup
@router.get("/items/")
async def get_items(db: AsyncSession = Depends(get_db)):
    return await crud.item.get_multi(db)

# DON'T: manually manage sessions (error-prone)
@router.get("/items/")
async def get_items():
    session = AsyncSessionLocal()
    try:
        items = await crud.item.get_multi(session)
        return items
    finally:
        await session.close()
```

### Partial Updates
```python
# DO: exclude_unset=True for PATCH operations
update_data = obj_in.model_dump(exclude_unset=True)

# DON'T: overwrites fields with None even if not provided
update_data = obj_in.model_dump()
```


## Anti-Patterns to Avoid

### 1. N+1 Query Problem
```python
# WRONG - fires N queries for N users
users = await crud.user.get_multi(db)
for user in users:
    user.posts = await crud.post.get_by_user_id(db, user.id)

# CORRECT - single query with eager loading
result = await db.execute(select(User).options(selectinload(User.posts)))
users = result.scalars().all()
```

### 2. Unmanaged Session Lifecycle
```python
# WRONG - session may leak on exception
@router.get("/items/")
async def get_items():
    session = AsyncSessionLocal()
    items = await crud.item.get_multi(session)
    await session.close()
    return items

# CORRECT - automatic cleanup via dependency injection
@router.get("/items/")
async def get_items(db: AsyncSession = Depends(get_db)):
    return await crud.item.get_multi(db)
```

### 3. Exposing ORM Models Directly
```python
# WRONG - exposes internal fields, lazy loading issues
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# CORRECT - use Pydantic schemas
@router.get("/users/{user_id}", response_model=UserInDB)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await crud.user.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### 4. Hardcoded Connection Strings
```python
# WRONG - credentials in source code
engine = create_async_engine("postgresql+asyncpg://admin:password123@localhost/mydb")

# CORRECT - environment variables via Pydantic settings
engine = create_async_engine(str(settings.DATABASE_URL), echo=settings.DEBUG)
```

### 5. Ignoring Transaction Boundaries
```python
# WRONG - no transaction, partial updates possible
await crud.user.update(db, user_id=1, data={"balance": 100})
await crud.transaction.create(db, user_id=1, amount=100)  # May fail

# CORRECT - atomic operations
async with db.begin():
    await crud.user.update(db, user_id=1, data={"balance": 100})
    await crud.transaction.create(db, user_id=1, amount=100)
```
