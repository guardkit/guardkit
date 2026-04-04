---
paths: "**/config.py, **/.env*, **/docker-compose*.yml"
---

# Environment Variable Configuration via Pydantic Settings

## Overview

All service configuration is managed through a `pydantic-settings` `BaseSettings` class with a `SERVICE_` env prefix. Settings are loaded from environment variables and `.env` files, providing type-safe configuration with defaults that work locally and are overridden in Docker/production environments.

## Implementation

### Settings Class

```python
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "SERVICE_", "env_file": ".env"}

    nats_url: str = "nats://localhost:4222"
    nats_connect_timeout: int = 5
    nats_max_reconnect_attempts: int = 10
    log_level: str = "INFO"
    service_name: str = "example-service"
```

### Environment Variable File

```bash
# .env.example
SERVICE_NATS_URL=nats://localhost:4222
SERVICE_NATS_CONNECT_TIMEOUT=5
SERVICE_NATS_MAX_RECONNECT_ATTEMPTS=10
SERVICE_LOG_LEVEL=INFO
SERVICE_SERVICE_NAME=example-service
```

### Docker Compose Override

```yaml
services:
  service:
    build: .
    depends_on:
      nats:
        condition: service_healthy
    environment:
      - SERVICE_NATS_URL=nats://nats:4222
```

### Usage in app.py

```python
from example_service.config import Settings

settings = Settings()
broker = NatsBroker(settings.nats_url)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    stream=sys.stderr,
)
```

## When to Use

- Every service needs a Settings class for configuration
- When connecting to NATS (URL, timeouts, reconnect policy)
- When configuring logging levels per environment
- When deploying via Docker Compose with environment variable overrides

## Best Practices

- Always use the `SERVICE_` env prefix to namespace variables and avoid collisions
- Provide sensible defaults for every setting (local development should work without a `.env` file)
- Use `model_config = {"env_prefix": "SERVICE_", "env_file": ".env"}` — not class-level `Config`
- Instantiate `Settings()` once in `app.py` and import it — do not create multiple instances
- Ship a `.env.example` file documenting all available settings
- In Docker Compose, override only the settings that differ (e.g. `nats://nats:4222` instead of `localhost`)
