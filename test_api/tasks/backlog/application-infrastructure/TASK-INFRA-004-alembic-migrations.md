---
id: TASK-INFRA-004
title: "Alembic migrations setup"
status: backlog
created: 2024-12-14T11:00:00Z
updated: 2024-12-14T11:00:00Z
priority: high
tags: [infrastructure, database, alembic, migrations]
complexity: 5
parent_feature: application-infrastructure
wave: 2
implementation_mode: task-work
conductor_workspace: infra-wave2-migrations
estimated_effort: 1.5h
dependencies: [TASK-INFRA-002, TASK-INFRA-003]
---

# Task: Alembic migrations setup

## Description

Configure Alembic for database migrations with async support for SQLAlchemy 2.0 and PostgreSQL.

## Technical Requirements

### 1. Initialize Alembic

```bash
alembic init alembic
```

### 2. Configure alembic.ini

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[post_write_hooks]
hooks = ruff
ruff.type = exec
ruff.executable = ruff
ruff.options = check --fix REVISION_SCRIPT_FILENAME
```

### 3. Async-Aware env.py (alembic/env.py)

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from src.config import settings
from src.core.base import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 4. Migration Script Template (alembic/script.py.mako)

Update to include proper imports and async patterns.

## Acceptance Criteria

- [ ] `alembic/` directory created with async env.py
- [ ] `alembic.ini` configured for PostgreSQL async
- [ ] Migrations run successfully in async mode
- [ ] Can create new migration: `alembic revision --autogenerate -m "message"`
- [ ] Can apply migrations: `alembic upgrade head`
- [ ] Can rollback migrations: `alembic downgrade -1`

## Test Requirements

- Test migration creation
- Test upgrade/downgrade cycle
- Test autogenerate detects model changes

## Dependencies

- TASK-INFRA-002 (database connection)
- TASK-INFRA-003 (configuration)
- TASK-INFRA-005 (Base model for metadata)
