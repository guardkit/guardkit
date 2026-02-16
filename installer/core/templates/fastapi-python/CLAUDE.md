# FastAPI Python Backend Template

## Project Context

This is a **production-ready FastAPI backend template** based on best practices from the [fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) repository (12k+ stars). The template implements patterns proven in production startup environments, with emphasis on scalability, maintainability, and developer experience.

## Core Principles

1. **Feature-Based Organization**: Structure by domain/feature rather than by file type
2. **Async-First**: Leverage FastAPI's async capabilities for I/O-bound operations
3. **Type Safety**: Comprehensive use of Pydantic for validation and type hints
4. **Dependency Injection**: Reusable dependencies for clean, testable code
5. **Production Ready**: Database migrations, proper error handling, testing infrastructure

## Architecture Overview

```
{{ProjectName}}/
├── src/
│   ├── {{feature_name}}/      # Feature modules
│   │   ├── router.py          # API endpoints
│   │   ├── schemas.py         # Pydantic models
│   │   ├── models.py          # SQLAlchemy ORM
│   │   ├── crud.py            # DB operations
│   │   ├── service.py         # Business logic
│   │   ├── dependencies.py    # DI functions
│   │   ├── constants.py       # Constants
│   │   ├── exceptions.py      # Custom exceptions
│   │   ├── config.py          # Feature config
│   │   └── utils.py           # Helpers
│   ├── core/                  # Global config, security, logging
│   ├── db/                    # SQLAlchemy base, sessions, migrations
│   └── main.py                # App initialization
├── tests/                     # Mirrors src/ structure
│   ├── {{feature_name}}/
│   └── conftest.py            # Shared fixtures
├── alembic/                   # DB migrations
├── requirements/              # base.txt, dev.txt, prod.txt
├── .env                       # Environment variables
├── alembic.ini
└── pyproject.toml
```

## Technology Stack

| Category | Tool | Version | Purpose |
|----------|------|---------|---------|
| **Framework** | FastAPI | >=0.104.0 | Web framework |
| **Server** | Uvicorn | latest | ASGI server |
| **Validation** | Pydantic | >=2.0.0 | Data validation |
| **ORM** | SQLAlchemy | >=2.0.0 | Database operations |
| **Migrations** | Alembic | >=1.12.0 | Schema migrations |
| **DB Driver** | asyncpg | latest | Async PostgreSQL |
| **Testing** | pytest | >=7.4.0 | Test framework |
| **Async Tests** | pytest-asyncio | >=0.21.0 | Async test support |
| **HTTP Client** | httpx | >=0.25.0 | Async HTTP testing |
| **Coverage** | pytest-cov | latest | Code coverage |
| **Linting** | ruff | latest | Linter + formatter |
| **Types** | mypy | latest | Static type checker |

## Layer Responsibilities

| Layer | File | Responsibility |
|-------|------|---------------|
| **API** | `router.py` | HTTP endpoints, request/response handling, DI, route validation |
| **Schema** | `schemas.py` | Pydantic models, validation, serialization, type definitions |
| **Model** | `models.py` | SQLAlchemy ORM, table definitions, relationships, constraints |
| **CRUD** | `crud.py` | DB queries, generic base CRUD, repository pattern |
| **Service** | `service.py` | Business logic, complex operations, external integrations |
| **Dependencies** | `dependencies.py` | Reusable DI functions, auth checks, session management |

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Feature modules | `snake_case` | `src/order_management/` |
| ORM models | PascalCase, singular | `class User(Base)` |
| Pydantic schemas | PascalCase + type suffix | `UserCreate`, `UserPublic`, `UserInDB` |
| Service classes | PascalCase + Service | `UserService`, `EmailService` |
| Functions | `snake_case` | `get_user_by_id()`, `create_product()` |
| Dependencies | `get_` prefix | `get_db()`, `get_current_user()` |
| Standard files | Fixed names per feature | `router.py`, `schemas.py`, `models.py`, `crud.py` |

See `.claude/rules/code-style.md` for full naming conventions with examples.

## Key Patterns

### Async Routes
Always use `async def` for I/O-bound routes, sync `def` for CPU-bound (runs in threadpool). Never use `time.sleep()` in async routes.
See `.claude/rules/api/routing.md` for patterns and anti-patterns.

### Pydantic Schemas
Create separate schemas per operation: `Base` (shared fields), `Create` (input), `Update` (optional fields), `InDB` (internal), `Public` (response). Use `from_attributes = True` for ORM compatibility.
See `.claude/rules/api/schemas.md` for full examples.

### Generic CRUD
Use `CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]` for reusable operations. Extend with custom methods per feature. Use `flush()` not `commit()` in CRUD methods.
See `.claude/rules/database/crud.md` for base class and extensions.

### Dependency Injection
Chain dependencies for complex auth flows: `get_db()` → `get_current_user()` → `get_current_active_user()`. Use `Depends()` for validation (`valid_user_id()`).
See `.claude/rules/api/dependencies.md` for full patterns.

### Database Sessions
Async engine with `asyncpg`, `async_sessionmaker`, `expire_on_commit=False`. Auto-commit via `get_db()` dependency.
See `.claude/rules/database/models.md` for session config and model patterns.

### Error Handling
Custom exception classes extending `HTTPException`. Global exception handler for unhandled errors with structured logging.
See `.claude/rules/api/routing.md` for exception patterns.

### Testing
Async test client with `httpx.AsyncClient`, in-memory SQLite fixtures, factory fixtures for test data, dependency override pattern.
See `.claude/rules/testing.md` for fixtures and test patterns.

### Configuration
Pydantic `BaseSettings` for typed config with `.env` support, field validators, CORS origins parsing.
See `.claude/rules/code-style.md` for Settings pattern.

## Common Tasks Index

| Task | Steps | Reference |
|------|-------|-----------|
| **New feature** | Create dir → model → migration → schemas → CRUD → router → tests | `.claude/rules/` (all) |
| **New endpoint** | Add to `router.py` with schemas + dependencies | `.claude/rules/api/routing.md` |
| **New schema** | Base → Create → Update → InDB → Public in `schemas.py` | `.claude/rules/api/schemas.md` |
| **New model** | Define in `models.py` → `alembic revision --autogenerate` | `.claude/rules/database/models.md` |
| **New CRUD** | Extend `CRUDBase` in `crud.py` | `.claude/rules/database/crud.md` |
| **New dependency** | Add to `dependencies.py`, use with `Depends()` | `.claude/rules/api/dependencies.md` |
| **New tests** | Mirror src/ structure, use fixtures from `conftest.py` | `.claude/rules/testing.md` |
| **Run migration** | `alembic revision --autogenerate -m "desc"` → `alembic upgrade head` | `.claude/rules/database/migrations.md` |

## Quality Standards

| Gate | Threshold | Tool |
|------|-----------|------|
| Line Coverage | >= 80% | pytest-cov |
| Branch Coverage | >= 75% | pytest-cov |
| Type Checking | 100% annotated, strict mode | mypy |
| Linting | Zero violations | ruff |
| Formatting | ruff format | ruff |

```bash
pytest                                               # Run all tests
pytest --cov=src --cov-report=term --cov-report=html # With coverage
pytest tests/users/test_router.py -v                 # Specific file
pytest -m asyncio                                    # Async tests only
```

## Specialized Agents

- **fastapi-specialist**: FastAPI patterns, routing, dependencies (see `.claude/rules/guidance/fastapi.md`)
- **fastapi-database-specialist**: SQLAlchemy, Alembic, database design (see `.claude/rules/guidance/database.md`)
- **fastapi-testing-specialist**: pytest, async testing, fixtures (see `.claude/rules/guidance/testing.md`)

## Quick Reference

| Pattern | File | Example |
|---------|------|---------|
| API Endpoint | `router.py` | `@router.get("/users/{id}")` |
| Request Schema | `schemas.py` | `UserCreate(BaseModel)` |
| Response Schema | `schemas.py` | `UserPublic(BaseModel)` |
| DB Model | `models.py` | `class User(Base)` |
| CRUD Operation | `crud.py` | `user.get(db, id=1)` |
| Business Logic | `service.py` | `UserService.register()` |
| Dependency | `dependencies.py` | `get_current_user()` |
| Custom Exception | `exceptions.py` | `UserNotFound(HTTPException)` |
| Test | `tests/*/test_*.py` | `test_create_user()` |

## Detailed Patterns and Examples

For detailed code examples, patterns, and best practices, see the `.claude/rules/` directory:

- **API Patterns**: `.claude/rules/api/` - Routing, schemas, dependencies
- **Database Patterns**: `.claude/rules/database/` - Models, CRUD, migrations
- **Testing Patterns**: `.claude/rules/testing.md` - Fixtures, async tests, coverage
- **Code Style**: `.claude/rules/code-style.md` - Naming conventions, configuration, API versioning

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic V2](https://docs.pydantic.dev/latest/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Original Best Practices Guide](https://github.com/zhanymkanov/fastapi-best-practices)

## Testing Strategy: Trophy Model

This template follows **Kent C. Dodds' Trophy testing model** for client applications:

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

- **50% Feature/Integration Tests**: Test API endpoints with TestClient across layers
- **30% Unit Tests**: Complex business logic only (calculations, validators, parsers)
- **10% E2E Tests**: Critical API workflows (auth flow, core business processes)
- **10% Static Analysis**: mypy strict mode, ruff linting

### Testing Principles

**✅ Test behavior, not implementation**
- Use FastAPI TestClient for endpoint tests
- Test request → response flow through all layers
- Verify business outcomes, not internal function calls

**✅ What to mock:**
- External APIs (at HTTP level via httpx.MockTransport or responses)
- Third-party services (payment gateways, email services)
- Slow operations (file uploads, heavy computations)

**❌ What NOT to mock:**
- Internal service/CRUD layer calls
- Database operations (use test database)
- Pydantic validation
- FastAPI dependency injection

**✅ When seam tests ARE needed:**
- Third-party integrations (Stripe, SendGrid, AWS)
- Microservice boundaries in distributed systems
- Platform tool development (NOT client APIs)

### Testing Requirements Checklist

- [ ] Feature/integration tests for every user story (endpoint → DB → response)
- [ ] Unit tests for complex business logic only (calculations, validators, parsers)
- [ ] Contract tests for third-party API integrations
- [ ] E2E tests for critical API workflows only (auth, core processes)
- [ ] mypy strict mode enabled
- [ ] ruff linting with recommended rules

**See**: [ADR-SP-009](../../docs/architecture/decisions/ADR-SP-009-honeycomb-testing-model.md) for architectural justification.

## Agent Response Format

When generating `.agent-response.json` files (checkpoint-resume pattern), use the format specification:

**Reference**: [Agent Response Format Specification](../../docs/reference/agent-response-format.md) (TASK-FIX-267C)

**Key Requirements**:
- Field name: `response` (NOT `result`)
- Data type: JSON-encoded string (NOT object)
- All 9 required fields must be present

See the specification for complete schema and examples.
