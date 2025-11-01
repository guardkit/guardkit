# Full Stack Development with Agentic Flow

This template provides a complete full-stack development environment with React frontend and Python backend, following Agentic Flow methodology.

## Architecture

**Frontend (React)**
- React 18 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Vitest for unit testing
- Playwright for E2E testing

**Backend (Python)**
- FastAPI for API development
- SQLAlchemy for ORM
- Alembic for migrations
- pytest for testing
- Pydantic for data validation

## Project Structure

```
frontend/          # React application
├── src/
├── tests/
└── package.json

backend/           # Python API
├── app/
├── tests/
├── alembic/
└── requirements.txt

shared/           # Shared types and utilities
└── types/
```

## Development Workflow

### Unified Task System
```bash
# 1. Create task (frontend, backend, or full-stack)
/task-create "Add user authentication"

# 2. Work on task with automatic testing
/task-work TASK-XXX [--mode=standard|tdd|bdd]

# 3. Complete task
/task-complete TASK-XXX
```

### Full-Stack Implementation Flow
1. **Define API Contract** - OpenAPI schema first
2. **Backend Implementation** - FastAPI endpoints with tests
3. **Frontend Implementation** - React components with tests
4. **Integration Testing** - Full-stack user scenarios
5. **Quality Gates** - Automatic verification for both stacks

## Testing Strategy

- **Frontend**: Vitest for components, Playwright for user flows
- **Backend**: pytest for API endpoints, integration tests
- **End-to-End**: Full stack user scenarios

## Key Patterns

- **API-First Design**: Define OpenAPI schemas first
- **Type Safety**: Shared TypeScript types between frontend and backend
- **Error Handling**: Consistent error patterns across stacks
- **State Management**: React Query for server state, Zustand for client state

## Quality Gates

- Frontend: 90% test coverage, no TypeScript errors
- Backend: 95% test coverage, no type hints missing
- Integration: All API contracts validated
- E2E: Critical user journeys tested

## Commands

All standard Agentic Flow commands work across both stacks:
- `/task-work` automatically detects and tests both frontend and backend
- `/task-status` shows progress across the full stack
- Quality gates validate both applications before completion