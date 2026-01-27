---
paths: **/crud/*.py, **/crud.py, **/repository/*.py
---

# CRUD Pattern with Generics

## Base CRUD Class

**Reusable CRUD class for all models:**

```python
from typing import Generic, TypeVar, Type, Optional, List
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**
        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """Get a single record by ID."""
        result = await db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        result = await db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record. Changes flushed but not committed."""
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict
    ) -> ModelType:
        """Update an existing record. Changes flushed but not committed."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> ModelType:
        """Delete a record. Changes flushed but not committed."""
        obj = await self.get(db, id=id)
        await db.delete(obj)
        await db.flush()
        return obj
```

## Feature-Specific CRUD

**Extend base class with custom methods:**

```python
from src.crud.base import CRUDBase
from src.users.models import User
from src.users.schemas import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Custom method: get user by email."""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_active_users(self, db: AsyncSession) -> List[User]:
        """Custom method: get only active users."""
        result = await db.execute(
            select(User).where(User.is_active == True)
        )
        return result.scalars().all()

# Instantiate CRUD
user = CRUDUser(User)
```

## Creating New CRUD

### Step-by-step workflow:

```python
# src/{{feature_name}}/crud.py
from src.crud.base import CRUDBase
from .models import {{EntityName}}
from .schemas import {{EntityName}}Create, {{EntityName}}Update

class CRUD{{EntityName}}(CRUDBase[{{EntityName}}, {{EntityName}}Create, {{EntityName}}Update]):
    # Add custom methods if needed
    pass

{{entity_name}} = CRUD{{EntityName}}({{EntityName}})
```

## Transaction Management

### Auto-Commit Pattern

The `get_db()` dependency automatically commits on success:

```python
@router.post("/users/")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # CRUD method uses flush(), not commit()
    user = await crud.user.create(db, obj_in=user_data)
    # Auto-committed when endpoint succeeds
    return user
```

### Multiple Operations in One Transaction

All operations in a single endpoint are committed atomically:

```python
@router.post("/complex/")
async def complex_operation(
    data: ComplexCreate,
    db: AsyncSession = Depends(get_db)
):
    user = await crud.user.create(db, obj_in=data.user)
    profile = await crud.profile.create(db, obj_in=data.profile)
    # BOTH committed atomically on success
    # BOTH rolled back if either operation fails
    return {"user": user, "profile": profile}
```

### Anti-Patterns

❌ **NEVER manually commit in CRUD methods:**
```python
# BAD - breaks transaction atomicity
async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
    db.add(db_obj)
    await db.commit()  # ❌ Prevents multiple operations in one transaction
    return db_obj
```

✅ **ALWAYS use flush() in CRUD methods:**
```python
# GOOD - allows atomic multi-operation transactions
async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
    db.add(db_obj)
    await db.flush()  # ✅ Assigns ID without committing
    await db.refresh(db_obj)
    return db_obj
```

## Best Practices

1. **Use generic base class** for common operations
2. **Add custom methods** to feature-specific CRUD classes
3. **Return Optional[T]** for get operations (may not exist)
4. **Use async/await** for all database operations
5. **Instantiate CRUD objects** at module level for reuse
6. **Use flush(), not commit()** in CRUD methods (auto-commit via get_db)
