# Faststream Nats Broker Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **faststream-nats-broker-specialist** agent.

**Core documentation**: See [faststream-nats-broker-specialist.md](./faststream-nats-broker-specialist.md)

---

## Related Templates

- `templates/infrastructure/example_service/app.py.template` — Primary template for FastStream application setup. Shows NatsBroker instantiation with config settings, logging to stderr, lifespan context manager for startup/shutdown, and handler registration via import side-effects.

- `templates/handlers/handlers/domain.py.template` — Handler implementation using `@broker.subscriber` and `@broker.publisher` decorators. Demonstrates thin-handler pattern where the handler receives a Pydantic message, delegates to DomainService, and returns the result for FastStream to publish.

- `templates/other/example_service/__init__.py.template` — Module imports exposing app, broker, and Settings classes as the public API surface.

- `templates/other/example_service/__main__.py.template` — Entry point that runs `asyncio.run(app.run())` to start the FastStream application.

- `templates/other/example_service/config.py.template` — pydantic-settings BaseSettings configuration with NATS connection parameters used by the broker.

- `templates/other/other/docker-compose.yml.template` — Docker Compose with NATS JetStream service that the broker connects to.

## Code Examples

### Example 1: FastStream Application Setup with Lifespan

From `templates/infrastructure/example_service/app.py.template`:

```python
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from faststream import FastStream
from faststream.nats import NatsBroker

from {{ProjectName}}.config import Settings

settings = Settings()

# Configure logging to stderr only
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    stream=sys.stderr,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

broker = NatsBroker(settings.nats_url)

@asynccontextmanager
async def lifespan():
    # Startup: acquire resources
    yield
    # Shutdown: release resources

app = FastStream(broker, lifespan=lifespan)

# Handler registration via import side-effects
import {{ProjectName}}.handlers  # noqa: F401, E402
```

### Example 2: Handler with @broker.subscriber and @broker.publisher

From `templates/handlers/handlers/domain.py.template`:

```python
from __future__ import annotations

from {{ProjectName}}.app import broker
from {{ProjectName}}.schemas import InboundMessage, OutboundMessage
from {{ProjectName}}.services.domain import DomainService

service = DomainService()

@broker.subscriber("domain.action.request")
@broker.publisher("domain.action.result")
async def handle_domain_action(msg: InboundMessage) -> OutboundMessage:
    """Thin handler: receive, delegate, return."""
    return await service.process(msg)
```

### Example 3: Entry Point

From `templates/other/example_service/__main__.py.template`:

```python
from __future__ import annotations

import asyncio
from {{ProjectName}}.app import app

if __name__ == "__main__":
    asyncio.run(app.run())
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
