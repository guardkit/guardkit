---
paths: packages/shared-types/**, **/generated/**
---

# Type-Safe API Client

## Type Generation Workflow

Full-stack type safety through OpenAPI → TypeScript generation:

```
Backend (FastAPI)           Frontend (React)
      ↓                           ↑
[Generate OpenAPI]          [Generate Types]
      ↓                           ↑
/openapi.json       ───>    @hey-api/openapi-ts
      ↓                           ↑
Pydantic schemas            TypeScript types
```

## Workflow Steps

### 1. Backend Generates OpenAPI Spec
```python
# apps/backend/app/main.py
from fastapi import FastAPI

app = FastAPI(
    title="My API",
    version="1.0.0",
    openapi_url="/openapi.json"
)
```

**Accessible at**: `http://localhost:8000/openapi.json`

### 2. Generate TypeScript Types
```bash
# Ensure backend is running
cd apps/backend
uvicorn app.main:app

# In another terminal, generate types
pnpm generate-types
```

**This runs**:
1. Fetches `http://localhost:8000/openapi.json`
2. Generates TypeScript via `@hey-api/openapi-ts`
3. Outputs to `packages/shared-types/src/generated/`

### 3. Frontend Imports Generated Types
```typescript
import { api, User, UserCreate, UserUpdate } from 'shared-types'

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await api.get<User[]>('/users')
      return response.data  // Fully typed!
    },
  })
}
```

## Package Structure

```
packages/shared-types/
├── src/
│   ├── index.ts           # Re-exports + API client
│   └── generated/         # Auto-generated from OpenAPI
│       ├── types.ts       # Type definitions
│       └── schemas.ts     # Validation schemas
├── scripts/
│   └── generate-types.js  # Type generation script
└── package.json
```

## API Client Configuration

### Base Configuration
```typescript
// packages/shared-types/src/index.ts
import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add interceptors
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Re-export generated types
export * from './generated/types'
```

## Type Generation Configuration

### Generation Script
```javascript
// packages/shared-types/scripts/generate-types.js
import { exec } from 'child_process'

const config = {
  input: 'http://localhost:8000/openapi.json',
  output: './src/generated',
  client: 'axios',
}

exec(`npx @hey-api/openapi-ts ${JSON.stringify(config)}`, (error) => {
  if (error) {
    console.error('Type generation failed:', error)
    process.exit(1)
  }
  console.log('✓ Types generated successfully')
})
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

## Usage Examples

### Query with Generated Types
```typescript
import { api, User } from 'shared-types'

const { data } = await api.get<User[]>('/users')
// data is User[] - fully typed!
```

### Mutation with Generated Types
```typescript
import { api, UserCreate, User } from 'shared-types'

const newUser: UserCreate = {
  email: 'test@example.com',
  full_name: 'Test User',
  password: 'secret123'
}

const { data } = await api.post<User>('/users', newUser)
// data is User - fully typed!
```

### Type Guards
```typescript
import { User } from 'shared-types'

function isUser(data: unknown): data is User {
  return (
    typeof data === 'object' &&
    data !== null &&
    'id' in data &&
    'email' in data &&
    'full_name' in data
  )
}
```

## Regeneration Triggers

### When to Regenerate Types
- ✅ After adding/modifying Pydantic schemas
- ✅ After changing API endpoints
- ✅ After modifying response models
- ✅ Before deploying frontend changes

### How to Regenerate
```bash
# Quick regeneration
pnpm generate-types

# With backend restart
docker-compose restart backend
pnpm generate-types

# Force fresh generation
rm -rf packages/shared-types/src/generated
pnpm generate-types
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Generate types
  run: |
    docker-compose up -d backend
    sleep 10  # Wait for backend
    pnpm generate-types

- name: Build frontend
  run: pnpm --filter frontend build
```

## Best Practices

### 1. Always Generate Before Dev/Build
```json
{
  "dev": {
    "dependsOn": ["generate-types"]
  }
}
```

### 2. Use Generated Types
✅ `import { User } from 'shared-types'`
❌ Manual type definitions

### 3. Keep Types in Sync
```bash
# After backend changes
pnpm generate-types
```

### 4. Version Control
- ✅ Commit generated types (recommended)
- ❌ Or add to .gitignore and regenerate in CI

### 5. Type-Safe API Calls
```typescript
const response = await api.get<User[]>('/users')
const users: User[] = response.data  // Type-safe!
```

## Troubleshooting

### Issue: Type generation fails
**Check**: Backend running at `http://localhost:8000`
**Check**: OpenAPI spec accessible at `/openapi.json`
**Solution**: Start backend, then regenerate

### Issue: Types are stale
**Solution**: Regenerate after backend changes
```bash
pnpm generate-types
```

### Issue: Frontend can't find types
**Check**: `shared-types` in dependencies
**Solution**: `pnpm install` from root

### Issue: Type mismatches
**Cause**: Backend/frontend out of sync
**Solution**: Regenerate types
```bash
pnpm generate-types
```

## OpenAPI Spec Best Practices

### Backend: Use Response Models
```python
from pydantic import BaseModel
from typing import List

class UserPublic(BaseModel):
    id: int
    email: str
    full_name: str

@router.get("/", response_model=List[UserPublic])
def list_users():
    return users
```

### Backend: Document Endpoints
```python
@router.post(
    "/",
    response_model=UserPublic,
    summary="Create user",
    description="Create a new user with email and password"
)
def create_user(user_in: UserCreate):
    return user
```
