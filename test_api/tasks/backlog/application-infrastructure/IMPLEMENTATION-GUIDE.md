# Implementation Guide: Application Infrastructure

## Execution Strategy

**Mode**: Parallel execution with Conductor workspaces
**Testing**: Standard (80% coverage, quality gates)
**Total Waves**: 4
**Total Effort**: ~15.5 hours

---

## Wave 1: Core Infrastructure (Parallel)

**Tasks**: 3 | **Can run in parallel**: Yes | **Dependencies**: None

### Conductor Setup

```bash
# Create 3 parallel workspaces
conductor workspace create infra-wave1-setup
conductor workspace create infra-wave1-database
conductor workspace create infra-wave1-config
```

### Tasks

| Workspace | Task ID | Title | Mode | Effort |
|-----------|---------|-------|------|--------|
| infra-wave1-setup | TASK-INFRA-001 | Project setup with dependencies | direct | 30 min |
| infra-wave1-database | TASK-INFRA-002 | Database connection and session | task-work | 2 hr |
| infra-wave1-config | TASK-INFRA-003 | Configuration and environment | task-work | 1 hr |

### Execution

```bash
# In workspace: infra-wave1-setup
# Direct implementation (no /task-work needed)
# Create: pyproject.toml, requirements/, src/__init__.py

# In workspace: infra-wave1-database
/task-work TASK-INFRA-002

# In workspace: infra-wave1-config
/task-work TASK-INFRA-003
```

### Wave 1 Completion Criteria

- [ ] `pyproject.toml` created with all dependencies
- [ ] `requirements/base.txt`, `requirements/dev.txt` created
- [ ] `src/database.py` with async engine and session factory
- [ ] `src/config.py` with Pydantic BaseSettings
- [ ] `.env.example` with all required variables

---

## Wave 2: Database Layer (Parallel)

**Tasks**: 2 | **Can run in parallel**: Yes | **Dependencies**: Wave 1 complete

### Conductor Setup

```bash
conductor workspace create infra-wave2-migrations
conductor workspace create infra-wave2-crud
```

### Tasks

| Workspace | Task ID | Title | Mode | Effort |
|-----------|---------|-------|------|--------|
| infra-wave2-migrations | TASK-INFRA-004 | Alembic migrations setup | task-work | 1.5 hr |
| infra-wave2-crud | TASK-INFRA-005 | Base model and CRUD patterns | task-work | 2 hr |

### Execution

```bash
# In workspace: infra-wave2-migrations
/task-work TASK-INFRA-004

# In workspace: infra-wave2-crud
/task-work TASK-INFRA-005
```

### Wave 2 Completion Criteria

- [ ] `alembic/` directory with async-aware `env.py`
- [ ] `alembic.ini` configured for PostgreSQL
- [ ] `src/core/base.py` with declarative base
- [ ] `src/core/crud.py` with generic CRUD class
- [ ] Initial migration created

---

## Wave 3: Authentication (Sequential)

**Tasks**: 2 | **Can run in parallel**: No (TASK-007 depends on TASK-006) | **Dependencies**: Wave 2 complete

### Conductor Setup

```bash
# Single workspace for sequential execution
conductor workspace create infra-wave3-auth
```

### Tasks

| Workspace | Task ID | Title | Mode | Effort |
|-----------|---------|-------|------|--------|
| infra-wave3-auth | TASK-INFRA-006 | JWT authentication | task-work | 3 hr |
| infra-wave3-auth | TASK-INFRA-007 | User feature module | task-work | 3 hr |

### Execution

```bash
# In workspace: infra-wave3-auth
/task-work TASK-INFRA-006
# Wait for completion, then:
/task-work TASK-INFRA-007
```

### Wave 3 Completion Criteria

- [ ] `src/core/security.py` with JWT functions
- [ ] `src/core/dependencies.py` with `get_current_user`
- [ ] `src/users/` feature module complete:
  - `models.py` - User SQLAlchemy model
  - `schemas.py` - UserCreate, UserPublic, etc.
  - `crud.py` - User CRUD operations
  - `router.py` - Auth endpoints (register, login, me)
  - `service.py` - User business logic
- [ ] Password hashing with bcrypt
- [ ] Token refresh endpoint

---

## Wave 4: Testing & Quality (Single Task)

**Tasks**: 1 | **Dependencies**: Wave 3 complete

### Conductor Setup

```bash
conductor workspace create infra-wave4-testing
```

### Tasks

| Workspace | Task ID | Title | Mode | Effort |
|-----------|---------|-------|------|--------|
| infra-wave4-testing | TASK-INFRA-008 | Testing infrastructure | task-work | 2.5 hr |

### Execution

```bash
# In workspace: infra-wave4-testing
/task-work TASK-INFRA-008
```

### Wave 4 Completion Criteria

- [ ] `tests/conftest.py` with async fixtures
- [ ] Test database configuration (isolation)
- [ ] `tests/users/test_router.py` - API tests
- [ ] `tests/users/test_crud.py` - CRUD tests
- [ ] `pytest.ini` configuration
- [ ] Coverage ≥80% line, ≥75% branch
- [ ] All tests passing

---

## Final Verification

After all waves complete:

```bash
# Run full test suite
pytest tests/ -v --cov=src --cov-report=term

# Type checking
mypy src/ --strict

# Linting
ruff check src/ tests/

# Start application
uvicorn src.main:app --reload
```

### Expected Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/login` | User login (returns JWT) |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/users/me` | Current user profile |
| GET | `/docs` | OpenAPI documentation |

---

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection string
python -c "from src.config import settings; print(settings.DATABASE_URL)"
```

### Migration Issues

```bash
# Check current revision
alembic current

# Show migration history
alembic history

# Reset (development only)
alembic downgrade base
alembic upgrade head
```

### Test Failures

```bash
# Run single test with verbose output
pytest tests/users/test_router.py::test_create_user -v -s

# Check test database isolation
pytest tests/ --tb=short
```
