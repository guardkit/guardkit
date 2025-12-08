# react-fastapi-monorepo-specialist - Extended Reference

This file contains detailed documentation for the `react-fastapi-monorepo-specialist` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/react-fastapi-monorepo-specialist-ext.md
```


## Guidance Principles

### 1. Workspace Organization
```
apps/              # Applications (deployed independently)
  ├── frontend/    # React app
  └── backend/     # FastAPI app

packages/          # Shared code (not deployed)
  └── shared-types/ # Generated types
```

### 2. Turborepo Pipeline
```json
{
  "pipeline": {
    "generate-types": {
      "outputs": ["src/**"],
      "cache": false  # Always regenerate
    },
    "build": {
      "dependsOn": ["^build", "generate-types"],
      "outputs": ["dist/**"]
    },
    "dev": {
      "dependsOn": ["generate-types"],
      "cache": false,
      "persistent": true
    }
  }
}
```

### 3. Dependency Management
```json
// package.json
{
  "dependencies": {
    "shared-types": "workspace:*"  // Use workspace protocol
  }
}
```

### 4. Type Generation Workflow
```
1. Backend changes (schemas, routes)
2. Start backend: uvicorn app.main:app
3. Generate types: pnpm generate-types
4. Frontend gets updated types automatically
5. TypeScript compiler catches breaking changes
```


## Common Patterns

### Adding a New App
```bash
mkdir -p apps/new-app
cd apps/new-app
pnpm init

# Add to pnpm-workspace.yaml

# Add to turbo.json pipeline
```

### Adding a New Package
```bash
mkdir -p packages/new-package
cd packages/new-package
pnpm init

# Use in apps:

# pnpm add new-package --filter=frontend
```

### Cross-App Communication
```typescript
// ✅ GOOD: Through API
api.get('/users')

// ❌ BAD: Direct imports
import { getUsers } from '../../backend/app/crud/user'
```

### Environment Variables
```bash

# Root .env (shared)
POSTGRES_HOST=localhost

# App-specific .env

# apps/frontend/.env.local
VITE_API_URL=http://localhost:8000

# apps/backend/.env
SECRET_KEY=xyz
```


## Anti-Patterns to Avoid

### 1. Tight Coupling
```typescript
// ❌ BAD: Frontend importing backend code
import { User } from '../../backend/app/models/user'

// ✅ GOOD: Use generated types
import { User } from 'shared-types'
```

### 2. Circular Dependencies
```
apps/frontend → packages/shared-types → apps/backend ❌
apps/frontend → packages/shared-types ← apps/backend ✅
```

### 3. Inconsistent Type Generation
```bash

# ❌ BAD: Manual type definitions
interface User { ... }

# ✅ GOOD: Generated from OpenAPI
pnpm generate-types
```

### 4. Build Order Issues
```json
// ❌ BAD: No dependencies
"build": { "outputs": ["dist/**"] }

// ✅ GOOD: Explicit dependencies
"build": {
  "dependsOn": ["^build", "generate-types"],
  "outputs": ["dist/**"]
}
```

### Type Generation Fails
1. Check backend is running: `curl http://localhost:8000/health`
2. Check OpenAPI spec: `curl http://localhost:8000/openapi.json`
3. Verify network connectivity between services

### Workspace Dependencies Not Resolving
1. Run `pnpm install` from root
2. Check `pnpm-workspace.yaml` includes correct paths
3. Verify `package.json` uses `workspace:*` protocol

### Turborepo Cache Issues
1. Clear cache: `turbo run build --force`
2. Check `.turbo/` directory
3. Verify `turbo.json` outputs are correct

### Docker Compose Issues
1. Check port conflicts: `lsof -i :3000,8000,5432`
2. Rebuild containers: `docker-compose up --build`
3. Check logs: `docker-compose logs -f`

### 1. Keep Apps Independent
Each app should be deployable independently with its own Dockerfile and dependencies.

### 2. Use Shared Packages Sparingly
Only extract code that is truly shared. Don't over-abstract.

### 3. Generate Types Automatically
Never manually write types that can be generated from OpenAPI.

### 4. Optimize Turborepo Cache
Configure outputs correctly to maximize cache hits.

### 5. Document Workspace Structure
Keep README updated with workspace responsibilities and boundaries.


## Related Templates

This specialist works with the following monorepo templates:

### Frontend Templates
- **`templates/apps/frontend/api-hook.ts.template`** - TanStack Query hooks for type-safe API communication. Demonstrates query cache invalidation, mutation patterns, and shared type imports.
- **`templates/apps/frontend/component.tsx.template`** - React components with integrated data fetching. Shows how to consume API hooks and handle loading/error states.

### Backend Templates
- **`templates/apps/backend/router.py.template`** - FastAPI routers with CRUD endpoints. Implements RESTful patterns with dependency injection and response models.
- **`templates/apps/backend/schema.py.template`** - Pydantic validation schemas. Demonstrates Base/Create/Update/Public pattern for API contracts.
- **`templates/apps/backend/crud.py.template`** - SQLAlchemy database operations. Shows separation of concerns between routing and data access.
- **`templates/apps/backend/model.py.template`** - SQLAlchemy ORM models. Defines database schema with relationships and constraints.

### Infrastructure Templates
- **`templates/docker/docker-compose.service.yml.template`** - Docker service definitions for local development. Enables hot reload with volume mounts.

**Template Relationships**: These templates form a complete monorepo workflow where `schema.py` defines the contract, `router.py` and `crud.py` implement the backend, and `api-hook.ts` + `component.tsx` consume it on the frontend with shared types.

---


## Template Code Examples

### Example 1: Type-Safe Full-Stack Data Flow

✅ **DO**: Use shared types across frontend and backend

```typescript
// Frontend: templates/apps/frontend/api-hook.ts.template
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, Product, ProductCreate } from 'shared-types'

export function useProducts() {
  return useQuery({
    queryKey: ['products'],
    queryFn: async () => {
      const response = await api.get<Product[]>('/products')
      return response.data
    },
  })
}

export function useCreateProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: ProductCreate) => {
      const response = await api.post<Product>('/products', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}
```

```python

# Backend: templates/apps/backend/router.py.template
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

router = APIRouter()

@router.get("/", response_model=List[ProductPublic])
def list_products(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return crud_product.get_products(db, skip=skip, limit=limit)

@router.post("/", response_model=ProductPublic, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db)
):
    return crud_product.create_product(db, product_in=product_in)
```

❌ **DON'T**: Duplicate type definitions or use loose typing

```typescript
// BAD: Types defined separately in frontend
interface Product {
  id: number
  name: string  // Might drift from backend!
}

// BAD: No type safety
const response = await fetch('/products')
const data = await response.json()  // any type
```

---

### Example 2: Pydantic Schema Hierarchy

✅ **DO**: Use Base/Create/Update/Public pattern from `schema.py.template`

```python

# templates/apps/backend/schema.py.template
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(max_length=500)
    price: float = Field(gt=0)

class ProductCreate(ProductBase):
    pass  # Inherits validation from Base

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)

class ProductPublic(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy model compatibility
```

❌ **DON'T**: Use flat schemas or expose internal fields

```python

# BAD: No separation of concerns
class Product(BaseModel):
    id: int  # Exposed in Create endpoint!
    name: str
    hashed_password: str  # Internal field exposed!

# BAD: No validation inheritance
class ProductUpdate(BaseModel):
    name: str  # Required in update (should be optional)
```

---

### Example 3: Docker Compose Hot Reload Setup

✅ **DO**: Use volume mounts for local development from `docker-compose.service.yml.template`

```yaml

# templates/docker/docker-compose.service.yml.template
frontend:
  build:
    context: ./apps/frontend
    dockerfile: Dockerfile.dev
  restart: always
  ports:
    - "5173:5173"
  volumes:
    - ./apps/frontend:/app
    - /app/node_modules  # Prevent overwriting
  environment:
    - VITE_API_URL=http://backend:8000

backend:
  build:
    context: ./apps/backend
    dockerfile: Dockerfile.dev
  restart: always
  ports:
    - "8000:8000"
  volumes:
    - ./apps/backend:/app
  command: uvicorn main:app --host 0.0.0.0 --reload
```

❌ **DON'T**: Copy code into container or skip hot reload

```yaml

# BAD: No volumes = no hot reload
backend:
  build: ./apps/backend
  ports:
    - "8000:8000"
  # Missing volumes and --reload flag
```

---

### Example 4: Query Cache Invalidation Pattern

✅ **DO**: Invalidate caches on mutations using `api-hook.ts.template` pattern

```typescript
// Coordinated cache updates across related queries
export function useDeleteProduct() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/products/${id}`)
    },
    onSuccess: () => {
      // Invalidate list query
      queryClient.invalidateQueries({ queryKey: ['products'] })
      // Invalidate detail queries
      queryClient.invalidateQueries({ queryKey: ['product'] })
    },
  })
}

export function useUpdateProduct() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: ProductUpdate }) => {
      const response = await api.patch<Product>(`/products/${id}`, data)
      return response.data
    },
    onSuccess: (updated, variables) => {
      // Optimistic update to detail query
      queryClient.setQueryData(['product', variables.id], updated)
      // Invalidate list to refetch
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}
```

❌ **DON'T**: Forget to invalidate or invalidate too broadly

```typescript
// BAD: No cache invalidation
export function useCreateProduct() {
  return useMutation({
    mutationFn: async (data: ProductCreate) => {
      return await api.post('/products', data)
    },
    // Missing onSuccess - stale data!
  })
}

// BAD: Invalidate everything
onSuccess: () => {
  queryClient.invalidateQueries()  // Nuclear option - poor performance
}
```

---


## Template Anti-Patterns

### Type Safety Violations

❌ **NEVER**: Duplicate type definitions across frontend and backend
```typescript
// BAD: Frontend types separate from backend
// apps/frontend/types.ts
interface Product {
  id: number
  name: string  // Will drift from backend!
}
```
**Why it fails**: Schema changes in backend won't reflect in frontend, causing runtime errors.

**Fix**: Always import from `shared-types` package generated from OpenAPI spec.

❌ **NEVER**: Use `any` type in API communication
```typescript
// BAD: No type safety
const data: any = await api.get('/products')
```
**Why it fails**: Loses all type checking, defeats purpose of TypeScript and monorepo shared types.

**Fix**: Use generated types from `shared-types`: `const data = await api.get<Product[]>('/products')`

### Dependency Management

❌ **NEVER**: Use relative imports across workspace packages
```typescript
// BAD: Brittle relative path
import { Product } from '../../../packages/shared-types/index.ts'
```
**Why it fails**: Breaks when directory structure changes, bypasses pnpm workspace resolution.

**Fix**: Use package name: `import { Product } from 'shared-types'`

❌ **NEVER**: Install dependencies directly in workspace root
```bash

# BAD: Wrong package.json location
npm install axios  # Installs in root, not available to apps
```
**Why it fails**: Apps can't access root dependencies in pnpm workspaces.

**Fix**: Use workspace-specific install: `pnpm add axios --filter frontend`

### API Patterns

❌ **NEVER**: Skip cache invalidation in mutations
```typescript
// BAD: Stale data after creation
export function useCreateProduct() {
  return useMutation({
    mutationFn: async (data: ProductCreate) => {
      return await api.post('/products', data)
    },
    // Missing onSuccess invalidation!
  })
}
```
**Why it fails**: UI shows outdated data until manual refresh.

**Fix**: Always invalidate in `onSuccess`: `queryClient.invalidateQueries({ queryKey: ['products'] })`

❌ **NEVER**: Expose internal fields in Public schemas
```python

# BAD: Leaking sensitive data
class UserPublic(BaseModel):
    id: int
    email: str
    hashed_password: str  # EXPOSED!

    class Config:
        from_attributes = True
```
**Why it fails**: Security vulnerability - sensitive fields returned to client.

**Fix**: Only include safe fields in `*Public` schemas, use separate internal models.

### Docker and Development

❌ **NEVER**: Use production builds in Docker Compose dev environment
```yaml

# BAD: Slow rebuild cycle
frontend:
  build:
    context: ./apps/frontend
  command: pnpm build && pnpm preview
  # Missing volumes = no hot reload
```
**Why it fails**: Every code change requires full rebuild (minutes vs seconds).

**Fix**: Use dev server with volume mounts (see `docker-compose.service.yml.template`).

❌ **NEVER**: Hardcode API URLs in frontend code
```typescript
// BAD: Environment-specific URL
const API_URL = 'http://localhost:8000'
const response = await fetch(`${API_URL}/products`)
```
**Why it fails**: Breaks when deployed, can't use Docker service names.

**Fix**: Use environment variable: `VITE_API_URL=http://backend:8000` in Docker Compose.

### Turborepo Pipeline Mistakes

❌ **NEVER**: Forget dependency order in pipelines
```json
// BAD: Frontend builds before shared-types
{
  "pipeline": {
    "build": {
      "outputs": ["dist/**"]
      // Missing dependsOn!
    }
  }
}
```
**Why it fails**: Frontend builds with stale types, causing import errors.

**Fix**: Declare dependencies: `"dependsOn": ["^build"]` to build shared packages first.

❌ **NEVER**: Run serial tasks that could be parallel
```bash

# BAD: Sequential execution
pnpm --filter frontend test
pnpm --filter backend test
```
**Why it fails**: Wastes time - tests are independent and could run concurrently.

**Fix**: Use Turborepo: `pnpm turbo run test --parallel`

### Schema Design

❌ **NEVER**: Make all Update schema fields required
```python

# BAD: Forces full object replacement
class ProductUpdate(BaseModel):
    name: str  # Required - can't do partial update!
    description: str
    price: float
```
**Why it fails**: Client must send all fields even for single property change.

**Fix**: Use `Optional` for all Update fields: `name: Optional[str] = None`

❌ **NEVER**: Skip validation constraints
```python

# BAD: No validation
class ProductCreate(BaseModel):
    name: str  # Could be empty string!
    price: float  # Could be negative!
```
**Why it fails**: Invalid data reaches database, causing errors or data corruption.

**Fix**: Add Pydantic constraints: `name: str = Field(min_length=1)`, `price: float = Field(gt=0)`


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat react-fastapi-monorepo-specialist-ext.md
```

Or in Claude Code:
```
Please read react-fastapi-monorepo-specialist-ext.md for detailed examples.
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat react-fastapi-monorepo-specialist-ext.md
```

Or in Claude Code:
```
Please read react-fastapi-monorepo-specialist-ext.md for detailed examples.
```
