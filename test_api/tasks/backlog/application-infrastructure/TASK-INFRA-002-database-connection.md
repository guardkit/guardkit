---
id: TASK-INFRA-002
title: "Database connection and session management"
status: backlog
created: 2024-12-14T11:00:00Z
updated: 2024-12-14T11:00:00Z
priority: high
tags: [infrastructure, database, sqlalchemy, async]
complexity: 5
parent_feature: application-infrastructure
wave: 1
implementation_mode: task-work
conductor_workspace: infra-wave1-database
estimated_effort: 2h
---

# Task: Database connection and session management

## Description

Implement async database connection using SQLAlchemy 2.0 with asyncpg driver for PostgreSQL. Create session management with proper dependency injection for FastAPI.

## Technical Requirements

### 1. Async Engine Setup (src/database.py)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Create async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

### 2. Database Session Dependency

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### 3. Connection Pool Configuration

- Pool size: 5 (configurable)
- Max overflow: 10 (configurable)
- Pool timeout: 30 seconds
- Pool recycle: 1800 seconds (30 min)

### 4. Health Check Endpoint

Add database connectivity check to health endpoint.

## Acceptance Criteria

- [ ] `src/database.py` created with async engine
- [ ] Session dependency `get_db()` implemented
- [ ] Connection pooling configured
- [ ] Database URL loaded from environment
- [ ] Health check verifies database connectivity
- [ ] Tests verify session lifecycle (commit/rollback)

## Test Requirements

- Unit test for session dependency
- Integration test for database connectivity
- Test transaction rollback on error

## Dependencies

- TASK-INFRA-001 (project setup)
- TASK-INFRA-003 (config for DATABASE_URL)
