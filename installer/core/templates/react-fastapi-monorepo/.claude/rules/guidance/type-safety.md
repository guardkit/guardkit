---
paths: packages/shared-types/**, **/openapi*, **/generated/**
---

# Type Safety Specialist Agent

## Purpose

OpenAPI → TypeScript type generation for full-stack type safety.

## Technologies

- **@hey-api/openapi-ts**: OpenAPI to TypeScript generator
- **FastAPI**: OpenAPI spec generation
- **Pydantic**: Backend schema validation
- **TypeScript**: Frontend type checking

## Boundaries

### ALWAYS
- ✅ Regenerate types after backend schema changes (maintain frontend-backend sync)
- ✅ Use generated types in frontend API calls (ensure type safety)
- ✅ Keep shared-types package up to date (prevent type mismatches)
- ✅ Verify OpenAPI spec is valid before generating (prevent corrupted types)
- ✅ Run type generation in Turborepo pipeline (automate workflow)

### NEVER
- ❌ Never manually define types that exist in generated/ (creates divergence)
- ❌ Never skip type generation in CI/CD pipeline (breaks deployment)
- ❌ Never import backend types directly (breaks separation of concerns)
- ❌ Never ignore type errors from generated code (indicates schema issues)
- ❌ Never modify generated files directly (changes will be overwritten)

### ASK
- ⚠️ Type generation configuration changes: Ask about custom mappings or overrides
- ⚠️ Custom type extensions strategy: Ask how to augment generated types
- ⚠️ Breaking API change handling: Ask about migration strategy for frontend
- ⚠️ Monorepo type sharing strategy: Ask about cross-workspace type dependencies

## Key Patterns

### Type Generation Workflow

```
Backend (FastAPI)      →   OpenAPI Spec   →   TypeScript Types   →   Frontend
[Pydantic schemas]     →   /openapi.json  →   @hey-api/openapi-ts →   [Type-safe API calls]
```

### Usage in Frontend

```typescript
import { api, User, UserCreate } from 'shared-types'

// Fully typed API call
const { data } = await api.get<User[]>('/users')
// data is User[] - compile-time type checking!
```

### Turborepo Integration

```json
{
  "pipeline": {
    "generate-types": {
      "outputs": ["src/**"],
      "cache": false
    },
    "dev": {
      "dependsOn": ["generate-types"]
    },
    "build": {
      "dependsOn": ["^build", "generate-types"]
    }
  }
}
```

## Common Tasks

### Regenerate Types After Backend Changes

```bash
# Ensure backend is running
cd apps/backend
uvicorn app.main:app --reload

# Generate types (another terminal)
pnpm generate-types
```

### Add New Backend Endpoint

1. **Backend**: Create Pydantic schema
```python
class ProductPublic(BaseModel):
    id: int
    name: str
    price: float
```

2. **Backend**: Add API route with response_model
```python
@router.get("/", response_model=List[ProductPublic])
def list_products():
    return products
```

3. **Regenerate types**
```bash
pnpm generate-types
```

4. **Frontend**: Use generated types
```typescript
import { api, Product } from 'shared-types'

const { data } = await api.get<Product[]>('/products')
```

### Troubleshoot Type Mismatches

**Issue**: Frontend type errors after backend changes

**Solution**:
```bash
# 1. Check backend is running
curl http://localhost:8000/openapi.json

# 2. Regenerate types
pnpm generate-types

# 3. Restart frontend dev server
pnpm --filter frontend dev
```

## Integration with GuardKit

When working on type-related tasks:
1. Always regenerate types after Pydantic schema changes
2. Verify frontend compiles after type generation
3. Run frontend tests to catch type-related issues
4. Use `/task-work` for full quality gates including type checking
