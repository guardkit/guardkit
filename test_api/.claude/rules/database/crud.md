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
        """Create a new record."""
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict
    ) -> ModelType:
        """Update an existing record."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: int) -> ModelType:
        """Delete a record."""
        obj = await self.get(db, id=id)
        await db.delete(obj)
        await db.commit()
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

## Best Practices

1. **Use generic base class** for common operations
2. **Add custom methods** to feature-specific CRUD classes
3. **Return Optional[T]** for get operations (may not exist)
4. **Use async/await** for all database operations
5. **Instantiate CRUD objects** at module level for reuse
