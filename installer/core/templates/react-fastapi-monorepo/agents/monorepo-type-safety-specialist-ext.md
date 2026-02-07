# monorepo-type-safety-specialist - Extended Reference

This file contains detailed documentation for the `monorepo-type-safety-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/monorepo-type-safety-specialist-ext.md
```


## Guidance Principles

### 1. OpenAPI Spec Quality

**Backend (FastAPI)**:
```python
from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    """Schema for creating a user"""
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {"email": "user@example.com", "full_name": "John Doe"}
        }
```

**Generated TypeScript**:
```typescript
export interface UserCreate {
  /** User email address */
  email: string
  full_name: string
}
```

### 2. Type Generation Script

```javascript
// packages/shared-types/scripts/generate-types.js
import { exec } from 'child_process'

const OPENAPI_URL = process.env.VITE_API_URL || 'http://localhost:8000'
const command = `npx @hey-api/openapi-ts \
  -i ${OPENAPI_URL}/openapi.json \
  -o ./src/generated \
  -c axios`

exec(command, (error) => {
  if (error) {
    console.error('Type generation failed. Ensure backend is running at', OPENAPI_URL)
    process.exit(1)
  }
  console.log('Types generated successfully')
})
```

### 3. Type-Safe API Client

```typescript
// packages/shared-types/src/index.ts
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

export * from './generated'
```

**Usage**:
```typescript
import { useQuery } from '@tanstack/react-query'
import { api, User } from 'shared-types'

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await api.get<User[]>('/users')
      return response.data  // Type: User[]
    },
  })
}
```


## Common Patterns

### CRUD Type Pattern

**Backend**: See "Type-Safe Schema Hierarchy" section below for the complete pattern with Field constraints and validation.

**Frontend Hook**:
```typescript
import { Item, ItemCreate } from 'shared-types'

export function useCreateItem() {
  return useMutation({
    mutationFn: async (data: ItemCreate) => {
      const response = await api.post<Item>('/items', data)
      return response.data
    }
  })
}
```

### Error Handling Pattern

**Backend**: Define `ErrorResponse(BaseModel)` with `detail: str` field, use `HTTPException`.

**Frontend**:
```typescript
import { AxiosError } from 'axios'
import { ErrorResponse } from 'shared-types'

const axiosError = err as AxiosError<ErrorResponse>
if (axiosError.response?.status === 404) {
  throw new Error(axiosError.response.data.detail)
}
```

### Pagination Pattern

**Backend**: `PaginatedResponse(BaseModel, Generic[T])` with `data`, `total`, `page`, `page_size`.
**Frontend**: `api.get<PaginatedResponse<Item>>('/items', { params: { page, page_size: 10 } })`


## Related Templates

### Backend Type Definition
- **templates/apps/backend/schema.py.template** - Pydantic schema hierarchy (Base/Create/Update/Public)
- **templates/apps/backend/router.py.template** - FastAPI routes with `response_model` for codegen
- **templates/apps/backend/model.py.template** - SQLAlchemy models mapping to Pydantic/TypeScript

### Frontend Type Usage
- **templates/apps/frontend/api-hook.ts.template** - TanStack Query hooks with typed `shared-types`
- **templates/apps/frontend/component.tsx.template** - Components consuming typed hooks

### Type Bridge
- **templates/apps/backend/crud.py.template** - CRUD with `model_dump()` for Pydantic v2


## Code Examples

### Type-Safe Schema Hierarchy

```python
class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    price: float = Field(..., gt=0)

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    price: float | None = Field(None, gt=0)

class ItemPublic(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
```

### Type-Safe Frontend Hook

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ItemPublic, ItemCreate, ItemUpdate } from '../types/shared-types';

export const useItems = () => {
  return useQuery({
    queryKey: ['items'],
    queryFn: async () => {
      const { data } = await api.get<ItemPublic[]>('/items');
      return data;
    },
  });
};

export const useCreateItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (newItem: ItemCreate) => {
      const { data } = await api.post<ItemPublic>('/items', newItem);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
    },
  });
};
```


## Anti-Patterns to Avoid

### 1. Manual Type Duplication
```typescript
// BAD: manually defined types drift from backend
interface User { id: number; email: string }

// GOOD: use generated types
import { User } from 'shared-types'
```

### 2. Type Assertions Instead of Generics
```typescript
// BAD
const data = response.data as User

// GOOD
const response = await api.get<User>('/users/1')
```

### 3. Missing response_model
```python
# BAD: TypeScript generator gets 'unknown'
@router.get("/tasks")
async def list_tasks(): ...

# GOOD: explicit response type (see "Type-Safe Schema Hierarchy" for schema patterns)
@router.get("/tasks", response_model=list[TaskPublic])
async def list_tasks(): ...
```

### 4. Using `any` with API Responses
```typescript
// BAD: defeats type safety
const { data } = await api.get<any>('/tasks');

// GOOD: typed
const { data } = await api.get<TaskPublic[]>('/tasks');
```

### 5. Relative Imports Across Workspaces
```typescript
// BAD: brittle path
import { Product } from '../../../packages/shared-types/index.ts'

// GOOD: package import
import { Product } from 'shared-types'
```


## Troubleshooting

- **Types stale**: `pnpm generate-types` then `turbo run build --force --filter=frontend`
- **Type generation fails**: Check backend running, OpenAPI spec valid, network connectivity
- **Type mismatch**: Regenerate types, check backend schema, clear node_modules
- **Import resolution**: Use package imports (`shared-types`), not relative paths
