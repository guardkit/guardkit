---
paths: "**/handlers/*.py, **/app.py"
---

# Pub/Sub Messaging

## Overview

FastStream implements NATS pub/sub via `@broker.subscriber` and `@broker.publisher` decorators on async handler functions. The subscriber binds a function to a NATS subject; the publisher automatically publishes the return value to another subject. FastStream handles serialization, deserialization, and Pydantic validation automatically.

## Implementation

### Handler with Subscribe and Publish

```python
from __future__ import annotations

from example_service.app import broker
from example_service.schemas import InboundMessage, OutboundMessage
from example_service.services.domain import DomainService

service = DomainService()

@broker.subscriber("domain.action.request")
@broker.publisher("domain.action.result")
async def handle_domain_action(msg: InboundMessage) -> OutboundMessage:
    """Subscribe to request subject, publish result to result subject."""
    return await service.process(msg)
```

### Broker Setup

```python
from faststream import FastStream
from faststream.nats import NatsBroker

broker = NatsBroker("nats://localhost:4222")
app = FastStream(broker, lifespan=lifespan)

# Import handlers to register subscribers on the broker
import example_service.handlers  # noqa: F401, E402
```

### Subject Naming Convention

| Pattern | Example | Purpose |
|---------|---------|---------|
| `{domain}.{action}.request` | `domain.action.request` | Inbound messages |
| `{domain}.{action}.result` | `domain.action.result` | Outbound responses |

## When to Use

- Every message-handling endpoint in the service
- When implementing request/response patterns over NATS
- When multiple handlers process different message types on different subjects
- When building event-driven architectures with decoupled producers and consumers

## Best Practices

- Use dot-separated hierarchical subject names (e.g. `orders.create.request`)
- Pair `@broker.subscriber` with `@broker.publisher` for request/response flows
- Use Pydantic models as handler parameters — FastStream validates automatically
- Register handlers via import side-effects in `app.py` (the `import handlers` pattern)
- Keep one handler function per subject — do not multiplex subjects in a single handler
- Return Pydantic models from handlers — FastStream serializes to JSON for publishing
