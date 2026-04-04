---
paths: "**/app.py, **/handlers/*.py, **/config.py"
---

# Module-Level Singleton for Service Instances

## Overview

Service instances (broker, settings, app) are created at module level so that all handlers share the same instance via import. This avoids dependency injection frameworks and leverages Python's module-level caching — a module is only executed once, so `from app import broker` always returns the same object.

## Implementation

### Broker Singleton in app.py

```python
from __future__ import annotations

from faststream import FastStream
from faststream.nats import NatsBroker

from example_service.config import Settings

settings = Settings()
broker = NatsBroker(settings.nats_url)
app = FastStream(broker, lifespan=lifespan)
```

### Handler Imports the Singleton

```python
from example_service.app import broker
from example_service.services.domain import DomainService

service = DomainService()

@broker.subscriber("domain.action.request")
@broker.publisher("domain.action.result")
async def handle_domain_action(msg: InboundMessage) -> OutboundMessage:
    return await service.process(msg)
```

### Handler Registration via Import Side-Effects

```python
# At the bottom of app.py — importing the handlers module
# registers all @broker.subscriber decorators on the singleton broker
import example_service.handlers  # noqa: F401, E402
```

## When to Use

- Creating the NatsBroker instance that all handlers share
- Creating the Settings instance that configures the entire application
- Creating DomainService instances at handler module level
- Any object that must be shared across modules without a DI container

## Best Practices

- Create exactly one `NatsBroker` and one `FastStream` app per process
- Place singletons in `app.py` — the canonical import source for broker and app
- Place configuration in `config.py` — instantiate `Settings()` once in `app.py`
- Use `import side-effects` (importing a handler module) to register subscribers on the broker
- Never instantiate a second broker — TestNatsBroker wraps the existing singleton for tests
