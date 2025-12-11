# FastAPI Python Backend Template

A production-ready FastAPI template based on best practices from the [fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) repository (12k+ stars). This template implements patterns proven in production startup environments, with emphasis on scalability, maintainability, and developer experience.

## Overview

This template provides a complete foundation for building async Python web APIs with:

- **Netflix Dispatch-inspired architecture**: Feature-based organization for scalability
- **Async-first design**: Leverages FastAPI's async capabilities
- **Type safety**: Comprehensive Pydantic validation
- **Dependency injection**: Clean, testable code patterns
- **Database migrations**: Alembic for schema management
- **Production-ready**: Error handling, logging, testing infrastructure

## Quick Start

```bash
# Initialize new project from this template
guardkit init fastapi-python

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/dev.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Create database and run migrations
alembic upgrade head

# Run development server
uvicorn src.main:app --reload

# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

## Features

### Core Framework
- **FastAPI** (>=0.104.0) - Modern, fast web framework
- **SQLAlchemy** (>=2.0.0) - Async ORM for database operations
- **Pydantic** (>=2.0.0) - Data validation and settings
- **Alembic** (>=1.12.0) - Database migration tool

### Development Tools
- **pytest** + **pytest-asyncio** - Async testing
- **httpx** - Async HTTP client for testing
- **ruff** - Fast Python linter and formatter
- **mypy** - Static type checker

### Architecture Patterns
- Generic CRUD base classes
- Dependency injection for cross-cutting concerns
- Repository pattern with async database operations
- Multiple Pydantic schemas per entity (Create, Update, InDB, Public)
- Feature-based module organization

## Project Structure

```
{{ProjectName}}/
├── src/
│   ├── {{feature_name}}/         # Feature modules
│   │   ├── router.py             # API endpoints
│   │   ├── schemas.py            # Pydantic models
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── crud.py               # Database operations
│   │   ├── service.py            # Business logic
│   │   ├── dependencies.py       # FastAPI dependencies
│   │   └── __init__.py
│   │
│   ├── core/                     # Global configuration
│   │   ├── config.py             # App settings
│   │   ├── security.py           # Auth/security
│   │   └── logging.py            # Logging config
│   │
│   ├── db/                       # Database infrastructure
│   │   ├── base.py               # SQLAlchemy base
│   │   ├── session.py            # Session management
│   │   └── migrations/           # Alembic migrations
│   │
│   └── main.py                   # FastAPI app
│
├── tests/                        # Test structure mirrors src/
│   ├── {{feature_name}}/
│   │   ├── test_router.py
│   │   ├── test_crud.py
│   │   └── test_service.py
│   └── conftest.py               # Shared fixtures
│
├── requirements/
│   ├── base.txt                  # Production dependencies
│   ├── dev.txt                   # Development dependencies
│   └── prod.txt                  # Production-only dependencies
│
├── alembic/                      # Database migrations
├── .env.example                  # Environment variables template
├── alembic.ini                   # Alembic configuration
├── pyproject.toml                # Project metadata
└── README.md
```

## Development Workflow

### 1. Create New Feature

```bash
# Create feature directory structure
mkdir -p src/products
touch src/products/{__init__.py,router.py,schemas.py,models.py,crud.py,service.py,dependencies.py}
```

### 2. Define Database Model

```python
# src/products/models.py
from sqlalchemy import Column, Integer, String, Float
from src.db.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
```

### 3. Create Migration

```bash
# Auto-generate migration
alembic revision --autogenerate -m "Add products table"

# Review and apply
alembic upgrade head
```

### 4. Define Schemas

```python
# src/products/schemas.py
from pydantic import BaseModel

class ProductCreate(BaseModel):
    name: str
    price: float

class ProductPublic(ProductCreate):
    id: int

    class Config:
        from_attributes = True
```

### 5. Implement CRUD

```python
# src/products/crud.py
from src.crud.base import CRUDBase
from .models import Product
from .schemas import ProductCreate, ProductUpdate

class CRUDProduct(CRUDBase[Product, ProductCreate, ProductUpdate]):
    pass

product = CRUDProduct(Product)
```

### 6. Create API Endpoints

```python
# src/products/router.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from . import crud, schemas

router = APIRouter()

@router.get("/", response_model=list[schemas.ProductPublic])
async def list_products(db: AsyncSession = Depends(get_db)):
    return await crud.product.get_multi(db)

@router.post("/", response_model=schemas.ProductPublic)
async def create_product(
    product: schemas.ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    return await crud.product.create(db, obj_in=product)
```

### 7. Write Tests

```python
# tests/products/test_router.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_product(client: AsyncClient):
    response = await client.post(
        "/api/v1/products/",
        json={"name": "Test Product", "price": 99.99}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Product"
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term --cov-report=html

# Run specific test file
pytest tests/users/test_router.py -v

# Run tests matching pattern
pytest -k "test_create" -v
```

### Writing Tests

The template includes:
- Async test fixtures
- Database test setup with SQLite in-memory
- HTTP client fixture with `httpx.AsyncClient`
- Factory fixtures for creating test data
- Authentication helpers

See `tests/conftest.py` for available fixtures.

## Configuration

All configuration is handled through environment variables or `.env` file:

```ini
# .env
PROJECT_NAME=MyAPI
DEBUG=True
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure production database
- [ ] Set up proper logging
- [ ] Configure CORS for production domains
- [ ] Run migrations: `alembic upgrade head`
- [ ] Set up health check monitoring
- [ ] Configure error tracking (e.g., Sentry)
- [ ] Use HTTPS/TLS
- [ ] Set up rate limiting

### Running in Production

```bash
# Using Uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

# Using Gunicorn with Uvicorn workers
gunicorn src.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements/prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## API Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current migration
alembic current
```

## Code Quality

```bash
# Format code
ruff format src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/

# Run all quality checks
ruff format src/ tests/ && ruff check src/ tests/ && mypy src/ && pytest
```

## Specialized AI Agents

This template includes three specialized agents for AI-assisted development:

- **fastapi-specialist**: FastAPI patterns, routing, dependencies
- **fastapi-database-specialist**: SQLAlchemy, Alembic, database design
- **fastapi-testing-specialist**: pytest, async testing, fixtures

Invoke these during development for specialized guidance.

## Rules Structure

This template uses Claude Code's modular rules structure for optimized context loading.

### Directory Layout

```
.claude/
├── CLAUDE.md                    # Core documentation (~5KB)
└── rules/
    ├── code-style.md            # Code style guidelines
    ├── testing.md               # Testing conventions
    ├── patterns/                # Pattern-specific rules
    │   └── {pattern}.md
    └── agents/                  # Agent guidance
        └── {agent}.md
```

### Path-Specific Rules

Rules files use `paths:` frontmatter for conditional loading:

| Rule File | Loads When Editing |
|-----------|-------------------|
| `rules/code-style.md` | Any `.py` file |
| `rules/testing.md` | Test files |
| `rules/api/routing.md` | `**/router*.py` |
| `rules/database/models.md` | `**/models/*.py` |
| `rules/guidance/fastapi.md` | API route files |
| `rules/guidance/database.md` | Model/CRUD files |

### Benefits

- Rules only load when editing relevant files
- Reduced context window usage (60-70% reduction)
- Organized by concern (patterns, agents, etc.)

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic V2](https://docs.pydantic.dev/latest/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Original Best Practices Guide](https://github.com/zhanymkanov/fastapi-best-practices)

## Template Information

- **Source**: [fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) (12k+ stars)
- **Version**: 1.0.0
- **Quality Score**: 9+/10
- **Complexity**: 7/10 (Medium-High)
- **Best For**: Backend APIs, microservices, async web applications
- **Production Ready**: Yes

## Contributing

This is a reference template maintained as part of GuardKit. To create your own customized version:

```bash
# Use this template as reference
guardkit init fastapi-python

# Or create your own template from your codebase
/template-create
```

## License

This template structure is provided as-is for learning and reference. Individual components follow their respective licenses (FastAPI, SQLAlchemy, etc.).
