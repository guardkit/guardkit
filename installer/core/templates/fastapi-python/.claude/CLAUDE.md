# FastAPI Python Backend Template

## Project Context

This is a **production-ready FastAPI backend template** based on best practices from the [fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) repository (12k+ stars). The template implements patterns proven in production startup environments, with emphasis on scalability, maintainability, and developer experience.

## Core Principles

1. **Feature-Based Organization**: Structure by domain/feature rather than by file type
2. **Async-First**: Leverage FastAPI's async capabilities for I/O-bound operations
3. **Type Safety**: Comprehensive use of Pydantic for validation and type hints
4. **Dependency Injection**: Reusable dependencies for clean, testable code
5. **Production Ready**: Database migrations, proper error handling, testing infrastructure

## Technology Stack

### Core Framework
- **FastAPI** (>=0.104.0): Modern, fast web framework
- **Uvicorn**: ASGI server for production
- **Pydantic** (>=2.0.0): Data validation and settings

### Database
- **SQLAlchemy** (>=2.0.0): ORM for database operations
- **Alembic** (>=1.12.0): Database migration tool
- **asyncpg**: Async PostgreSQL driver (recommended)

### Testing
- **pytest** (>=7.4.0): Testing framework
- **pytest-asyncio** (>=0.21.0): Async test support
- **httpx** (>=0.25.0): Async HTTP client for testing
- **pytest-cov**: Code coverage reporting

### Code Quality
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checker
- **pre-commit**: Git hooks for code quality

## Project Structure

```
{{ProjectName}}/
├── src/
│   ├── {{feature_name}}/         # Feature modules (users, products, orders, etc.)
│   │   ├── router.py             # API endpoints
│   │   ├── schemas.py            # Pydantic models
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── crud.py               # Database operations
│   │   ├── service.py            # Business logic
│   │   ├── dependencies.py       # FastAPI dependencies
│   │   ├── constants.py          # Feature-specific constants
│   │   ├── exceptions.py         # Custom exceptions
│   │   ├── config.py             # Feature-specific config
│   │   └── utils.py              # Helper functions
│   │
│   ├── core/                     # Global configuration
│   │   ├── config.py             # App-wide settings
│   │   ├── security.py           # Authentication/Authorization
│   │   └── logging.py            # Logging configuration
│   │
│   ├── db/                       # Database infrastructure
│   │   ├── base.py               # SQLAlchemy base
│   │   ├── session.py            # Session management
│   │   └── migrations/           # Alembic migrations
│   │
│   ├── main.py                   # FastAPI app initialization
│   ├── config.py                 # Global config
│   ├── database.py               # DB connection setup
│   ├── models.py                 # Shared models
│   ├── exceptions.py             # Global exceptions
│   └── pagination.py             # Pagination helpers
│
├── tests/                        # Test structure mirrors src/
│   ├── {{feature_name}}/
│   │   ├── test_router.py
│   │   ├── test_crud.py
│   │   └── test_service.py
│   └── conftest.py               # Shared fixtures
│
├── alembic/                      # Database migrations
│   ├── versions/
│   └── env.py
│
├── requirements/                 # Split requirements
│   ├── base.txt                  # Production dependencies
│   ├── dev.txt                   # Development dependencies
│   └── prod.txt                  # Production-only dependencies
│
├── .env                          # Environment variables
├── alembic.ini                   # Alembic configuration
├── logging.ini                   # Logging configuration
└── pyproject.toml                # Project metadata and tools
```

## Layer Responsibilities

**API Layer (`router.py`)**: HTTP endpoint definitions, request/response handling, dependency injection, route-level validation

**Schema Layer (`schemas.py`)**: Pydantic models for validation, request/response serialization, type definitions, data transformation

**Model Layer (`models.py`)**: SQLAlchemy ORM models, database table definitions, relationships and constraints, database-level validations

**CRUD Layer (`crud.py`)**: Database query operations, Create/Read/Update/Delete, generic base CRUD classes, repository pattern implementation

**Service Layer (`service.py`)**: Business logic, complex operations, cross-entity orchestration, external service integration

**Dependencies Layer (`dependencies.py`)**: Reusable dependency functions, authentication checks, database session management, request validation

## Quality Standards

### Code Coverage
- **Minimum Line Coverage**: 80%
- **Minimum Branch Coverage**: 75%
- **Test Categories**: Unit tests, integration tests, API tests

### Type Checking
- **Tool**: mypy
- **Mode**: Strict
- **Coverage**: 100% of code annotated

### Linting
- **Tool**: ruff
- **Rules**: Default + FastAPI best practices
- **Formatting**: ruff format

### Testing Requirements
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term --cov-report=html

# Run specific test file
pytest tests/users/test_router.py -v

# Run async tests
pytest -m asyncio
```

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

## Specialized Agents Available

This template works with the following specialized AI agents:

- **fastapi-specialist**: FastAPI patterns, routing, dependencies (see `.claude/rules/guidance/fastapi.md`)
- **fastapi-database-specialist**: SQLAlchemy, Alembic, database design (see `.claude/rules/guidance/database.md`)
- **fastapi-testing-specialist**: pytest, async testing, fixtures (see `.claude/rules/guidance/testing.md`)

Use these agents during development for specialized guidance.

## Detailed Patterns and Examples

For detailed code examples, patterns, and best practices, see the `.claude/rules/` directory:

- **API Patterns**: `.claude/rules/api/` - Routing, schemas, dependencies
- **Database Patterns**: `.claude/rules/database/` - Models, CRUD, migrations
- **Testing Patterns**: `.claude/rules/testing.md` - Fixtures, async tests, coverage
- **Code Style**: `.claude/rules/code-style.md` - Naming conventions, organization

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic V2](https://docs.pydantic.dev/latest/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Original Best Practices Guide](https://github.com/zhanymkanov/fastapi-best-practices)

## Agent Response Format

When generating `.agent-response.json` files (checkpoint-resume pattern), use the format specification:

**Reference**: [Agent Response Format Specification](../../docs/reference/agent-response-format.md) (TASK-FIX-267C)

**Key Requirements**:
- Field name: `response` (NOT `result`)
- Data type: JSON-encoded string (NOT object)
- All 9 required fields must be present

See the specification for complete schema and examples.
