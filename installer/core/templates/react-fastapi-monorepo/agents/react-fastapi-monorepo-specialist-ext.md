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
    "generate-types": { "outputs": ["src/**"], "cache": false },
    "build": { "dependsOn": ["^build", "generate-types"], "outputs": ["dist/**"] },
    "dev": { "dependsOn": ["generate-types"], "cache": false, "persistent": true }
  }
}
```

### 3. Dependency Management
```json
{ "dependencies": { "shared-types": "workspace:*" } }
```

### 4. Type Generation Workflow
1. Backend changes (schemas, routes)
2. Start backend: `uvicorn app.main:app`
3. Generate types: `pnpm generate-types`
4. Frontend gets updated types automatically
5. TypeScript compiler catches breaking changes


## Common Patterns

### Adding a New App/Package
```bash
mkdir -p apps/new-app && cd apps/new-app && pnpm init
# Add to pnpm-workspace.yaml and turbo.json pipeline
```

### Cross-App Communication
```typescript
// GOOD: Through API
api.get('/users')

// BAD: Direct imports
import { getUsers } from '../../backend/app/crud/user'
```

### Environment Variables
```bash
# Root .env (shared)
POSTGRES_HOST=localhost
# apps/frontend/.env.local
VITE_API_URL=http://localhost:8000
# apps/backend/.env
SECRET_KEY=xyz
```


## Code Examples

### Full-Stack Data Flow

**Frontend** (api-hook.ts.template):
```typescript
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

**Backend** (router.py.template):
```python
router = APIRouter()

@router.get("/", response_model=List[ProductPublic])
def list_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_product.get_products(db, skip=skip, limit=limit)

@router.post("/", response_model=ProductPublic, status_code=status.HTTP_201_CREATED)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    return crud_product.create_product(db, product_in=product_in)
```

### Pydantic Schema Hierarchy (schema.py.template)

```python
class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(max_length=500)
    price: float = Field(gt=0)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, gt=0)

class ProductPublic(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
```

### Query Cache Invalidation

```typescript
export function useDeleteProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => { await api.delete(`/products/${id}`) },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['product'] })
    },
  })
}
```


## Related Templates

### Frontend
- **templates/apps/frontend/api-hook.ts.template** - TanStack Query hooks with cache invalidation
- **templates/apps/frontend/component.tsx.template** - Components with data fetching

### Backend
- **templates/apps/backend/router.py.template** - FastAPI CRUD endpoints with DI
- **templates/apps/backend/schema.py.template** - Pydantic Base/Create/Update/Public pattern
- **templates/apps/backend/crud.py.template** - SQLAlchemy operations
- **templates/apps/backend/model.py.template** - ORM models with relationships

### Infrastructure
- **templates/docker/docker-compose.service.yml.template** - Docker service definitions


## Anti-Patterns to Avoid

### 1. Tight Coupling
```typescript
// BAD: Frontend importing backend code
import { User } from '../../backend/app/models/user'
// GOOD: Use generated types
import { User } from 'shared-types'
```

### 2. Circular Dependencies
```
apps/frontend → packages/shared-types → apps/backend  (BAD)
apps/frontend → packages/shared-types ← apps/backend  (GOOD)
```

### 3. Missing Cache Invalidation
```typescript
// BAD: stale data after mutation
useMutation({ mutationFn: async (data) => api.post('/products', data) })
// GOOD: invalidate on success
onSuccess: () => queryClient.invalidateQueries({ queryKey: ['products'] })
```

### 4. Build Order Issues
```json
// BAD: no dependencies
"build": { "outputs": ["dist/**"] }
// GOOD: explicit dependency chain
"build": { "dependsOn": ["^build", "generate-types"], "outputs": ["dist/**"] }
```

### 5. Exposing Internal Fields in Public Schemas
```python
# BAD: hashed_password in response
class UserPublic(BaseModel):
    hashed_password: str  # Security vulnerability!
# GOOD: only safe fields in *Public schemas
```


## Troubleshooting

- **Type generation fails**: Check backend running (`curl http://localhost:8000/health`), verify OpenAPI spec
- **Workspace deps not resolving**: `pnpm install` from root, check `pnpm-workspace.yaml`
- **Turborepo cache issues**: `turbo run build --force`, check `.turbo/` directory
- **Docker Compose issues**: Check ports (`lsof -i :3000,8000,5432`), rebuild with `--build`
