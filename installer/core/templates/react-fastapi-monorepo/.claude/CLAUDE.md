# React + FastAPI Monorepo Template

## Project Context

Production-ready full-stack monorepo with React frontend, FastAPI backend, and type safety through OpenAPI generation. Uses Turborepo for orchestration, pnpm workspaces, and Docker Compose.

## Core Principles

1. **Type Safety**: OpenAPI → TypeScript keeps frontend/backend types in sync
2. **Monorepo Efficiency**: Turborepo caches and parallelizes builds
3. **Feature-Based Frontend**: React organized by domain features
4. **Layered Backend**: FastAPI follows Netflix Dispatch architecture
5. **Developer Experience**: Docker Compose for one-command setup

## Technology Stack

**Frontend**: React 18.3, TypeScript 5.4+, Vite 5.2, TanStack Query 5.32, Vitest
**Backend**: FastAPI 0.115, SQLAlchemy 2.0, Pydantic 2.0, pytest, PostgreSQL
**Shared**: shared-types (generated from OpenAPI)
**Infrastructure**: Turborepo, pnpm, Docker Compose, @hey-api/openapi-ts

## Quick Start

```bash
# Start all services
pnpm docker:up

# Services available:
# - Frontend: http://localhost:3000
# - Backend: http://localhost:8000
# - Database: localhost:5432

# Generate types after backend changes
pnpm generate-types

# Run tests
pnpm test

# Build for production
pnpm build
```

## Project Structure

```
monorepo/
├── apps/
│   ├── frontend/          # React + TypeScript + Vite
│   │   └── src/features/  # Feature-based modules
│   └── backend/           # FastAPI + SQLAlchemy
│       └── app/
│           ├── api/       # Routes
│           ├── crud/      # Database operations
│           ├── models/    # SQLAlchemy models
│           └── schemas/   # Pydantic schemas
├── packages/
│   └── shared-types/      # Generated TypeScript types
├── docker-compose.yml
├── turbo.json
└── .claude/
    └── rules/             # Pattern documentation
        ├── monorepo/
        ├── frontend/
        ├── backend/
        └── agents/
```

## Type-Safe API Workflow

### 1. Backend Defines Schema
```python
# apps/backend/app/schemas/user.py
class UserPublic(BaseModel):
    id: int
    email: str
    full_name: str
```

### 2. Generate Types
```bash
pnpm generate-types  # Fetches /openapi.json, generates TypeScript
```

### 3. Frontend Uses Types
```typescript
import { api, User } from 'shared-types'

const { data } = await api.get<User[]>('/users')
// data is User[] - fully typed!
```

## Common Workflows

### Add New Feature

**Backend**:
```bash
mkdir -p apps/backend/app/{api/routes,schemas,models,crud}
# Create user.py in each directory
pnpm generate-types
```

**Frontend**:
```bash
mkdir -p apps/frontend/src/features/users/{api,components,hooks}
# api/get-users.ts - API calls
# components/users-list.tsx - UI
# hooks/use-users.ts - Custom hooks
```

### Run Specific Workspace
```bash
pnpm --filter frontend dev
pnpm --filter backend test
turbo run build --filter=frontend
```

### Reset Environment
```bash
docker-compose down -v
docker-compose up -d --build
```

## Naming Conventions

**Frontend**:
- Components: `kebab-case.tsx` (export `PascalCase`)
- Hooks: `use-hook-name.ts`
- Features: singular, lowercase

**Backend**:
- Files: `snake_case.py`
- Models: `PascalCase`, singular
- Tables: `snake_case`, plural
- Schemas: `PascalCase` with suffix (`UserCreate`, `UserPublic`)

## Rules Documentation

Detailed patterns and best practices are in `.claude/rules/`:

**Monorepo**: Turborepo, Docker, workspaces
**Frontend**: React architecture, TanStack Query, type generation
**Backend**: FastAPI layers, database operations, Pydantic schemas
**Agents**: Specialized guidance for monorepo, type-safety, Docker

Load rules as needed:
```bash
cat .claude/rules/frontend/types.md
cat .claude/rules/backend/fastapi.md
```

## Specialized Agents

Template includes AI agents for:
1. **monorepo**: Turborepo orchestration, pnpm workspaces, Docker Compose
2. **type-safety**: OpenAPI → TypeScript generation and type-safe API patterns
3. **docker**: Multi-service orchestration and container management

See `.claude/rules/guidance/*.md` for agent specifications.

## Environment Variables

**Frontend** (.env):
```bash
VITE_API_URL=http://localhost:8000
```

**Backend** (.env):
```bash
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changethis
SECRET_KEY=changethis123456789
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

## Testing Strategy: Trophy Model

This monorepo uses **Kent C. Dodds' Trophy testing model** for both frontend and backend apps:

```
    🏆  E2E (~10%)
  ___________
/             \
| Feature/    |
| Integration |  ← Primary focus (~50%)
| Tests       |
\____________/
Unit Tests (~30%)
__________
Static (~10%)
```

### Testing Distribution

**Frontend (React)**:
- **50% Feature/Integration Tests**: Test user scenarios across components with MSW
- **30% Unit Tests**: Complex calculations, validators, utilities only
- **10% E2E Tests**: Critical user journeys (login, core workflows)
- **10% Static Analysis**: TypeScript strict mode, ESLint

**Backend (FastAPI)**:
- **50% Feature/Integration Tests**: Test endpoints with TestClient across all layers
- **30% Unit Tests**: Complex business logic only (calculations, parsers)
- **10% E2E Tests**: Critical API workflows (auth, core processes)
- **10% Static Analysis**: mypy strict mode, ruff linting

### Testing Principles

**✅ Test behavior, not implementation**
- Frontend: Test user interactions, not component internals
- Backend: Test API contracts, not internal function calls
- Both: Focus on business outcomes

**✅ What to mock:**
- External APIs (at HTTP level via MSW/httpx.MockTransport)
- Third-party services (payment gateways, email services)
- Slow operations (file uploads, image processing)

**❌ What NOT to mock:**
- Frontend: Internal functions, React Query, Zustand state
- Backend: Service/CRUD layers, Pydantic validation, database (use test DB)
- Both: Framework routing, rendering, or request handling

**✅ When seam tests ARE needed:**
- Third-party integrations (Stripe, SendGrid, external APIs)
- Microservice boundaries in distributed systems
- Shared library packages in monorepo (test integration points)

### Testing Requirements Checklist

**Frontend**:
- [ ] Feature/integration tests for every user story
- [ ] Unit tests for complex business logic only
- [ ] E2E tests for critical user journeys
- [ ] TypeScript strict mode enabled

**Backend**:
- [ ] Feature/integration tests for every API endpoint
- [ ] Unit tests for complex algorithms only
- [ ] Contract tests for third-party integrations
- [ ] mypy strict mode enabled

**Shared Packages**:
- [ ] Integration tests at package boundaries
- [ ] Type generation validated with tests

**See**: [ADR-SP-009](../../../docs/architecture/decisions/ADR-SP-009-honeycomb-testing-model.md) for architectural justification.

## Troubleshooting

**Types not updating**: `pnpm generate-types` after backend changes
**Port conflicts**: Check `lsof -i :3000,8000,5432` and change ports
**Database issues**: `docker-compose down -v && docker-compose up db -d`
**Stale cache**: `turbo run build --force`

## Resources

- [Turborepo Docs](https://turbo.build/repo/docs)
- [FastAPI Template](https://github.com/tiangolo/full-stack-fastapi-template)
- [TanStack Query](https://tanstack.com/query/latest)
- [@hey-api/openapi-ts](https://github.com/hey-api/openapi-ts)
