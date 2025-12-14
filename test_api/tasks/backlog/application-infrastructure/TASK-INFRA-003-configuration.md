---
id: TASK-INFRA-003
title: "Configuration and environment management"
status: backlog
created: 2024-12-14T11:00:00Z
updated: 2024-12-14T11:00:00Z
priority: high
tags: [infrastructure, config, environment, pydantic]
complexity: 3
parent_feature: application-infrastructure
wave: 1
implementation_mode: task-work
conductor_workspace: infra-wave1-config
estimated_effort: 1h
---

# Task: Configuration and environment management

## Description

Implement centralized configuration management using Pydantic Settings with environment variable support and validation.

## Technical Requirements

### 1. Settings Class (src/config.py)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "FastAPI Application"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()
```

### 2. Environment File Template (.env.example)

```env
# Application
APP_NAME=FastAPI Application
DEBUG=true
API_V1_PREFIX=/api/v1

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
POSTGRES_DB=test_api

# JWT
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 3. FastAPI App Configuration (src/main.py)

```python
from fastapi import FastAPI
from src.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)
```

## Acceptance Criteria

- [ ] `src/config.py` with Settings class created
- [ ] `.env.example` template created
- [ ] All settings validated at startup
- [ ] DATABASE_URL property generates correct async URL
- [ ] `src/main.py` basic app created with settings
- [ ] Health endpoint returns app info

## Test Requirements

- Test settings load from environment
- Test settings validation (required fields)
- Test DATABASE_URL property construction
