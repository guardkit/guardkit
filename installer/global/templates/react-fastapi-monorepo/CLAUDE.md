# React + FastAPI Monorepo Template

## Project Context

This is a **production-ready full-stack monorepo template** combining React frontend and FastAPI backend with type safety through OpenAPI code generation. It uses Turborepo for monorepo orchestration, pnpm workspaces for dependency management, and Docker Compose for local development.

## Core Principles

1. **Type Safety Across Stack**: OpenAPI → TypeScript generation ensures frontend and backend types stay in sync
2. **Monorepo Efficiency**: Turborepo caches and parallelizes builds, tests, and type generation
3. **Feature-Based Frontend**: React code organized by domain features, not technical layers
4. **Layered Backend**: FastAPI follows Netflix Dispatch-inspired layered architecture
5. **Developer Experience**: Docker Compose for one-command local development

## Architecture Overview

### Monorepo Structure

```
react-fastapi-monorepo/
├── apps/
│   ├── frontend/          # React + TypeScript + Vite
│   │   ├── src/
│   │   │   ├── features/  # Feature-based modules
│   │   │   ├── components/ # Shared components
│   │   │   └── hooks/     # Shared hooks
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   └── Dockerfile
│   │
│   └── backend/           # FastAPI + SQLAlchemy
│       ├── app/
│       │   ├── api/       # API routes
│       │   ├── core/      # Configuration
│       │   ├── crud/      # Database operations
│       │   ├── db/        # Database setup
│       │   ├── models/    # SQLAlchemy models
│       │   └── schemas/   # Pydantic schemas
│       ├── tests/
│       ├── pyproject.toml
│       └── Dockerfile
│
├── packages/
│   └── shared-types/      # Generated TypeScript types
│       ├── src/
│       │   ├── index.ts   # API client and manual types
│       │   └── generated/ # Auto-generated from OpenAPI
│       └── scripts/
│           └── generate-types.js
│
├── docker-compose.yml     # Local development orchestration
├── turbo.json            # Turborepo pipeline configuration
└── package.json          # Root workspace scripts
```

### Technology Stack

**Frontend (apps/frontend)**:
- **React 18.3**: UI library with concurrent features
- **TypeScript 5.4+**: Static typing
- **Vite 5.2**: Fast build tool and dev server
- **TanStack Query 5.32**: Server state management
- **Vitest**: Unit testing

**Backend (apps/backend)**:
- **FastAPI 0.115**: Modern async Python web framework
- **SQLAlchemy 2.0**: Database ORM
- **Pydantic 2.0**: Data validation and OpenAPI generation
- **pytest**: Testing framework
- **PostgreSQL**: Database

**Shared Packages**:
- **shared-types**: Type-safe API client generated from OpenAPI spec

**Infrastructure**:
- **Turborepo**: Monorepo task orchestration
- **pnpm**: Fast, disk-efficient package manager
- **Docker Compose**: Multi-container local development
- **@hey-api/openapi-ts**: OpenAPI → TypeScript type generation

## Key Patterns

### 1. Type-Safe API Client Pattern

**Backend generates OpenAPI spec**:
```python
# apps/backend/app/main.py
from fastapi import FastAPI

app = FastAPI(
    title="My API",
    openapi_url="/openapi.json"  # OpenAPI spec endpoint
)
```

**Frontend generates TypeScript types**:
```bash
# From monorepo root
pnpm generate-types

# This runs:
# 1. Fetches http://localhost:8000/openapi.json
# 2. Generates TypeScript types via @hey-api/openapi-ts
# 3. Outputs to packages/shared-types/src/generated/
```

**Frontend uses generated types**:
```typescript
// apps/frontend/src/features/users/hooks/use-users.ts
import { useQuery } from '@tanstack/react-query'
import { api, User } from 'shared-types'

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

**Benefits**:
- Compile-time type checking
- Auto-complete in IDE
- Refactoring safety
- Self-documenting API

### 2. Turborepo Task Orchestration

**Pipeline configuration** (turbo.json):
```json
{
  "pipeline": {
    "generate-types": {
      "outputs": ["src/**"],
      "cache": false
    },
    "build": {
      "dependsOn": ["^build", "generate-types"],
      "outputs": ["dist/**", ".next/**", "build/**"]
    },
    "dev": {
      "dependsOn": ["generate-types"],
      "cache": false,
      "persistent": true
    }
  }
}
```

**Key features**:
- **Dependency Resolution**: `build` depends on `generate-types`
- **Caching**: Turborepo caches build outputs
- **Parallelization**: Runs independent tasks in parallel
- **Filtering**: Run tasks for specific apps (`--filter=frontend`)

**Common commands**:
```bash
# Run all dev servers (frontend + backend)
pnpm dev

# Build everything
pnpm build

# Build specific app
turbo run build --filter=frontend

# Run tests across monorepo
pnpm test
```

### 3. Docker Compose Development Environment

**Services**:
```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    ports: ["5432:5432"]

  backend:
    build: ./apps/backend
    ports: ["8000:8000"]
    depends_on: [db]
    volumes:
      - ./apps/backend:/app  # Hot reload

  frontend:
    build: ./apps/frontend
    ports: ["3000:3000"]
    depends_on: [backend]
    volumes:
      - ./apps/frontend:/app  # Hot reload
```

**Usage**:
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down
```

**Benefits**:
- One-command setup
- Consistent environment
- No local PostgreSQL needed
- Hot reload for both apps

### 4. Frontend Feature-Based Architecture

**Feature structure**:
```
features/users/
├── api/
│   ├── get-users.ts       # API call + query options
│   └── create-user.ts     # Mutation
├── components/
│   ├── users-list.tsx     # Feature component
│   └── user-card.tsx      # Sub-component
└── hooks/
    └── use-users.ts       # Custom hook wrapping useQuery
```

**API layer example**:
```typescript
// features/users/api/get-users.ts
import { queryOptions, useQuery } from '@tanstack/react-query'
import { api, User } from 'shared-types'

export const getUsersQueryOptions = ({ page }: { page?: number } = {}) => {
  return queryOptions({
    queryKey: page ? ['users', { page }] : ['users'],
    queryFn: async () => {
      const response = await api.get<User[]>('/users', {
        params: { page }
      })
      return response.data
    },
  })
}

export const useUsers = ({ page, queryConfig }: Options) => {
  return useQuery({
    ...getUsersQueryOptions({ page }),
    ...queryConfig,
  })
}
```

### 5. Backend Layered Architecture

**Layer responsibilities**:

**API Layer** (api/routes/):
```python
# app/api/routes/users.py
from fastapi import APIRouter, Depends
from app.schemas.user import UserPublic, UserCreate
from app.crud import user as crud_user

router = APIRouter()

@router.get("/", response_model=List[UserPublic])
def list_users(db: Session = Depends(get_db)):
    return crud_user.get_users(db)
```

**Schema Layer** (schemas/):
```python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str

class UserPublic(BaseModel):
    id: int
    email: str
    full_name: str
```

**Model Layer** (models/):
```python
# app/models/user.py
from sqlalchemy import Column, Integer, String
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
```

**CRUD Layer** (crud/):
```python
# app/crud/user.py
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user_in: UserCreate):
    db_user = User(**user_in.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
```

## Naming Conventions

### Frontend (TypeScript)

**Files**:
- Components: `kebab-case.tsx` (export: `PascalCase`)
- Hooks: `use-hook-name.ts` or `useHookName.ts`
- API files: `{action}-{entity}.ts`
- Features: singular, lowercase, kebab-case

**Code**:
- Components: `PascalCase`
- Hooks: `camelCase` with `use` prefix
- Functions: `camelCase`
- Constants: `SCREAMING_SNAKE_CASE` or `camelCase`
- Types/Interfaces: `PascalCase`

**Examples**:
```typescript
// features/discussions/components/discussions-list.tsx
export const DiscussionsList = () => { ... }

// features/discussions/hooks/use-discussions.ts
export const useDiscussions = () => { ... }

// features/discussions/api/get-discussions.ts
export const getDiscussions = () => { ... }
```

### Backend (Python)

**Files**:
- All files: `snake_case.py`
- Example: `user.py`, `database_config.py`

**Code**:
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE`
- Database tables: `snake_case`, plural
- Models: `PascalCase`, singular
- Schemas: `PascalCase` with suffix (`UserCreate`, `UserUpdate`, `UserPublic`)

**Examples**:
```python
# models/user.py
class User(Base):  # PascalCase, singular
    __tablename__ = "users"  # snake_case, plural

# schemas/user.py
class UserCreate(BaseModel):  # PascalCase with suffix
    pass

# crud/user.py
def get_user_by_email(db: Session, email: str):  # snake_case
    pass
```

### Shared

**Packages**: `kebab-case` (e.g., `shared-types`)
**Docker services**: lowercase, `kebab-case` (e.g., `backend`, `postgres-db`)

## Development Workflow

### 1. Starting Development

```bash
# Option 1: Docker Compose (Recommended)
pnpm docker:up
# Opens: Frontend (3000), Backend (8000), PostgreSQL (5432)

# Option 2: Manual
docker-compose up db          # Terminal 1: Database
cd apps/backend && uvicorn app.main:app --reload  # Terminal 2
cd apps/frontend && pnpm dev  # Terminal 3
pnpm generate-types          # Terminal 4: After backend is up
```

### 2. Creating a New Feature

**Frontend Feature**:
```bash
mkdir -p apps/frontend/src/features/products/{api,components,hooks}

# api/get-products.ts - API calls + query options
# components/products-list.tsx - UI component
# hooks/use-products.ts - Custom hooks
```

**Backend Feature**:
```bash
mkdir -p apps/backend/app/{api/routes,schemas,models,crud}

# api/routes/products.py - API endpoints
# schemas/product.py - Pydantic schemas
# models/product.py - SQLAlchemy model
# crud/product.py - CRUD operations
```

**Regenerate Types**:
```bash
# After backend changes
pnpm generate-types
```

### 3. Adding a Docker Service

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

### 4. Testing

**Frontend tests**:
```bash
cd apps/frontend
pnpm test              # Run Vitest
pnpm test:coverage     # With coverage
```

**Backend tests**:
```bash
cd apps/backend
pytest                 # Run all tests
pytest tests/test_users.py  # Specific file
pytest --cov=app      # With coverage
```

### 5. Building for Production

```bash
# Build all apps
pnpm build

# Build Docker images
docker build -t frontend:prod ./apps/frontend
docker build -t backend:prod ./apps/backend
```

## Common Tasks

### Add a New API Endpoint

1. **Backend**: Create route in `api/routes/{entity}.py`
```python
@router.post("/", response_model=ProductPublic)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    return crud_product.create(db, product_in=product_in)
```

2. **Backend**: Add Pydantic schema in `schemas/{entity}.py`
```python
class ProductCreate(BaseModel):
    name: str
    price: float
```

3. **Backend**: Add SQLAlchemy model in `models/{entity}.py`
```python
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
```

4. **Backend**: Add CRUD operations in `crud/{entity}.py`
```python
def create_product(db: Session, product_in: ProductCreate):
    db_product = Product(**product_in.dict())
    db.add(db_product)
    db.commit()
    return db_product
```

5. **Generate types**:
```bash
pnpm generate-types
```

6. **Frontend**: Use generated types
```typescript
import { api, Product, ProductCreate } from 'shared-types'

const { data } = useQuery({
  queryKey: ['products'],
  queryFn: async () => {
    const response = await api.get<Product[]>('/products')
    return response.data
  }
})
```

### Add Database Migration

```bash
cd apps/backend

# Create migration
alembic revision --autogenerate -m "Add products table"

# Review generated migration in alembic/versions/

# Apply migration
alembic upgrade head
```

### Add Environment Variable

1. Add to `.env`:
```bash
NEW_SETTING=value
```

2. Add to backend config (`app/core/config.py`):
```python
class Settings(BaseSettings):
    NEW_SETTING: str
```

3. Add to `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      - NEW_SETTING=${NEW_SETTING}
```

## Type Generation Workflow

### Automatic Type Generation

Type generation is integrated into Turborepo pipeline:

```bash
# During development
pnpm dev
# → Runs generate-types before starting dev servers

# During build
pnpm build
# → Runs generate-types before building apps
```

### Manual Type Generation

```bash
# Ensure backend is running
cd apps/backend
uvicorn app.main:app

# Generate types (in another terminal)
pnpm generate-types

# Types are generated at:
# packages/shared-types/src/generated/
```

### Type Generation Troubleshooting

**Issue**: Type generation fails
- **Check**: Backend is running at `http://localhost:8000`
- **Check**: OpenAPI spec accessible at `/openapi.json`
- **Solution**: Start backend, then regenerate types

**Issue**: Types are stale
- **Solution**: `pnpm generate-types` after backend changes

**Issue**: Frontend can't find types
- **Check**: `shared-types` package is in `node_modules`
- **Solution**: `pnpm install` from root

## Testing Strategy

### Frontend Testing (Vitest)

```typescript
// apps/frontend/src/features/users/__tests__/users-list.test.tsx
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { UsersList } from '../components/users-list'

test('renders users list', async () => {
  const queryClient = new QueryClient()

  render(
    <QueryClientProvider client={queryClient}>
      <UsersList />
    </QueryClientProvider>
  )

  expect(screen.getByText(/users/i)).toBeInTheDocument()
})
```

### Backend Testing (pytest)

```python
# apps/backend/tests/test_users.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_user():
    response = client.post(
        "/users/",
        json={
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
```

### Integration Testing

```typescript
// Test type-safe API calls
import { api } from 'shared-types'

test('fetches users with correct types', async () => {
  const response = await api.get('/users')
  const users = response.data

  // TypeScript ensures users is User[]
  expect(users[0]).toHaveProperty('id')
  expect(users[0]).toHaveProperty('email')
})
```

## Troubleshooting

### Frontend not connecting to backend

**Check**:
1. Backend is running: `curl http://localhost:8000/health`
2. CORS is configured: Check `BACKEND_CORS_ORIGINS` in `.env`
3. API URL is correct: Check `VITE_API_URL` in `.env`

**Solution**:
```bash
# .env
VITE_API_URL=http://localhost:8000
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

### Type generation fails

**Check**:
1. Backend is running: `curl http://localhost:8000/openapi.json`
2. OpenAPI spec is valid JSON

**Solution**:
```bash
# Start backend
cd apps/backend
uvicorn app.main:app --reload

# Regenerate types
pnpm generate-types
```

### Docker Compose issues

**Check**:
1. Ports are available: `lsof -i :3000,8000,5432`
2. Docker is running: `docker ps`

**Solution**:
```bash
# Stop conflicting services
docker-compose down

# Restart
docker-compose up -d --build
```

### Database connection errors

**Check**:
1. PostgreSQL is running: `docker-compose ps db`
2. Credentials are correct in `.env`

**Solution**:
```bash
# Reset database
docker-compose down -v
docker-compose up db -d

# Wait for health check
docker-compose logs db
```

## Specialized Agents

This template includes specialized AI agents for monorepo patterns:

### 1. **react-fastapi-monorepo-specialist**
- Monorepo architecture decisions
- Turborepo pipeline configuration
- Workspace dependency management
- Docker Compose orchestration

### 2. **monorepo-type-safety-specialist**
- OpenAPI → TypeScript type generation
- Type-safe API client patterns
- Shared type management
- Frontend-backend type synchronization

### 3. **docker-orchestration-specialist**
- Docker Compose multi-service setups
- Development vs production configurations
- Volume and network management
- Service health checks

**Usage**: These agents are automatically available when using the template. Reference them in tasks for specialized guidance.

## Environment Variables Reference

### Frontend (.env)
```bash
VITE_API_URL=http://localhost:8000  # Backend API URL
```

### Backend (.env)
```bash
# Database
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changethis

# API
SECRET_KEY=changethis123456789
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Admin
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=changethis
```

## Additional Resources

- [Turborepo Documentation](https://turbo.build/repo/docs)
- [pnpm Workspaces](https://pnpm.io/workspaces)
- [FastAPI Official Template](https://github.com/tiangolo/full-stack-fastapi-template)
- [TanStack Query Docs](https://tanstack.com/query/latest)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [@hey-api/openapi-ts](https://github.com/hey-api/openapi-ts)

## Notes

- This template combines patterns from `react-typescript` and `fastapi-python` templates
- Type generation requires backend to be running
- Docker Compose is recommended for local development
- Turborepo caches build outputs for faster rebuilds
- The monorepo supports independent deployment of frontend and backend
