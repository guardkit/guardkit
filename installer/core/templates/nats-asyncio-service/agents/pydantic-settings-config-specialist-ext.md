# Pydantic Settings Config Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **pydantic-settings-config-specialist** agent.

**Core documentation**: See [pydantic-settings-config-specialist.md](./pydantic-settings-config-specialist.md)

---

## Related Templates

- `templates/other/example_service/config.py.template` — Primary configuration template. Shows BaseSettings with `SERVICE_` env prefix, `.env` file loading, NATS URL, connection timeout, reconnect settings, log level, and service name.

- `templates/other/other/.env.example.template` — Example environment file showing all SERVICE_-prefixed variables and their defaults.

- `templates/infrastructure/example_service/app.py.template` — Application setup that instantiates Settings and passes `settings.nats_url` to NatsBroker.

- `templates/other/other/docker-compose.yml.template` — Docker Compose showing `SERVICE_NATS_URL=nats://nats:4222` environment variable mapping.

## Code Examples

### Example 1: BaseSettings Configuration

From `templates/other/example_service/config.py.template`:

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

### Example 2: Environment Variable File

From `templates/other/other/.env.example.template`:

```bash
SERVICE_NATS_URL=nats://localhost:4222
SERVICE_NATS_CONNECT_TIMEOUT=5
SERVICE_NATS_MAX_RECONNECT_ATTEMPTS=10
SERVICE_LOG_LEVEL=INFO
SERVICE_SERVICE_NAME=example-service
```

### Example 3: Docker Compose Environment Mapping

From `templates/other/other/docker-compose.yml.template`:

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

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
