# Feature Input: FastAPI Python Base Project

## Feature Name

`fastapi-base-project`

## One-liner

A production-structured FastAPI application with health endpoint, structured JSON logging, request correlation IDs, Pydantic settings management, and a complete test harness — all runnable without any external services.

---

## Background & Motivation

This project serves as the foundation for AutoBuild benchmark testing on a local vLLM inference stack (GB10 / Qwen3-Coder). The primary requirement is that the entire test suite passes with no external dependencies — no database, no Redis, no external APIs. Everything must work with `pytest` out of the box.

The project should reflect real production patterns (proper project layout, environment config, middleware, typed request/response models) so that benchmark tasks built on top of it exercise realistic coding work rather than toy problems.

---

## Goals

- `pytest` runs green with zero external services
- Production-grade project layout that a new feature can be dropped into cleanly
- Typed throughout (Pydantic v2, no `Any` leakage in public interfaces)
- Structured JSON logging with correlation IDs visible in test output
- Settings management via environment variables with sensible defaults
- Coverage target: ≥ 90% on all project code

---

## What Is NOT in Scope

- Database integration (no SQLAlchemy, no Alembic, no PostgreSQL)
- Authentication / JWT (separate feature)
- Redis or any external caching
- Docker / deployment configuration
- API versioning beyond a simple `/v1/` prefix on routes

---

## Project Layout

```
fastapi-base/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app factory
│   ├── settings.py              # Pydantic BaseSettings
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── correlation.py       # Correlation ID injection
│   ├── routers/
│   │   ├── __init__.py
│   │   └── health.py            # Health endpoint
│   └── schemas/
│       ├── __init__.py
│       └── health.py            # HealthResponse model
├── tests/
│   ├── conftest.py              # TestClient fixture, settings override
│   ├── test_health.py
│   ├── test_correlation.py
│   └── test_settings.py
├── pyproject.toml
└── .env.example
```

---

## Components

### Settings (`app/settings.py`)

Pydantic `BaseSettings` with:
- `APP_NAME: str` — default `"fastapi-base"`
- `APP_VERSION: str` — default `"0.1.0"`
- `ENVIRONMENT: Literal["development", "staging", "production"]` — default `"development"`
- `LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"]` — default `"INFO"`
- `LOG_FORMAT: Literal["json", "text"]` — default `"json"`
- `API_PREFIX: str` — default `"/v1"`

All fields overridable via environment variables. Tests override via `Settings(...)` constructor, never via env patching.

### Logging (`app/main.py` or `app/logging.py`)

Structured JSON logging configured at app startup from `Settings.LOG_LEVEL` and `Settings.LOG_FORMAT`. Each log line includes:
- `timestamp` (ISO 8601)
- `level`
- `message`
- `correlation_id` (if request context is active)
- `logger` (module name)

In `LOG_FORMAT=text` mode, output is human-readable for local development. In `json` mode, each line is a valid JSON object for log aggregation.

### Correlation ID Middleware (`app/middleware/correlation.py`)

Starlette middleware that:
- Reads `X-Correlation-ID` from incoming request header
- Generates a UUID v4 if header is absent
- Injects the ID into a `contextvars.ContextVar` for use by the logging layer
- Adds `X-Correlation-ID` to every response header

Correlation ID is accessible to route handlers and logged automatically on every request/response.

### Health Router (`app/routers/health.py`)

`GET /v1/health` — returns 200 with:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development"
}
```

`GET /v1/health/live` — liveness probe, always returns `{"status": "ok"}` with 200.

`GET /v1/health/ready` — readiness probe. In this base project, always returns `{"status": "ok"}` with 200. Future features (e.g. DB integration) extend this to include dependency checks.

### App Factory (`app/main.py`)

`create_app(settings: Settings | None = None) -> FastAPI` factory function used by both the production entry point and tests. Registers middleware and routers. Configures logging on startup.

---

## Acceptance Criteria (high-level, for Gherkin generation)

- Given `GET /v1/health` is called, the response is 200 with `status: "ok"`, `version`, and `environment`
- Given `GET /v1/health/live` is called, the response is always 200 regardless of any application state
- Given `GET /v1/health/ready` is called, the response is 200 in this base configuration
- Given a request arrives without `X-Correlation-ID` header, the response includes a generated UUID in `X-Correlation-ID`
- Given a request arrives with `X-Correlation-ID: abc-123`, the response includes `X-Correlation-ID: abc-123`
- Given `LOG_FORMAT=json` is configured, log output for a request is valid JSON with `correlation_id` field
- Given `ENVIRONMENT=production`, the `environment` field in the health response reflects this
- Given `pytest` is run with no environment variables set, all tests pass using default settings
- Given an unknown route is requested, the response is 404 with a JSON error body (not HTML)

---

## Tech Stack

- Python 3.12+
- FastAPI 0.115+
- Pydantic v2 / pydantic-settings
- Uvicorn (runtime only, not required for tests)
- pytest + httpx (via `httpx` for `AsyncClient` or `TestClient`)
- pytest-cov for coverage

---

## Notes for Spec Generation

- Stack is Python
- No async database or external service calls anywhere in this base — `TestClient` (sync) is sufficient, no need for `pytest-anyio` or async fixtures in this feature
- The app factory pattern is the key design decision — it makes settings injection clean for tests without monkeypatching
- `pyproject.toml` should include dev dependencies for the test suite and a `[tool.pytest.ini_options]` section
- `.env.example` lists all settings with their defaults and brief comments
