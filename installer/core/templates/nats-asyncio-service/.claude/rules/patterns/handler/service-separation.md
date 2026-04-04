---
paths: "**/handlers/*.py, **/services/*.py"
---

# Handler/Service Separation

## Overview

The thin-handler / pure-service layering pattern. Handlers own only NATS dispatch (subscribe, delegate, publish), while services own all business logic with zero NATS or broker imports. This separation makes business logic independently testable without any messaging infrastructure.

## Implementation

### Thin Handler (Dispatch Only)

```python
from __future__ import annotations

from example_service.app import broker
from example_service.schemas import InboundMessage, OutboundMessage
from example_service.services.domain import DomainService

service = DomainService()

@broker.subscriber("domain.action.request")
@broker.publisher("domain.action.result")
async def handle_domain_action(msg: InboundMessage) -> OutboundMessage:
    """Thin handler: receive, delegate, return."""
    return await service.process(msg)
```

### Pure Service (No NATS Imports)

```python
from __future__ import annotations

from example_service.schemas import InboundMessage, OutboundMessage


class DomainService:
    """Pure business logic — no NATS, no broker, independently testable."""

    async def process(self, msg: InboundMessage) -> OutboundMessage:
        result = f"Processed: {msg.payload}"
        return OutboundMessage(
            correlation_id=msg.message_id,
            source_id="example-service",
            success=True,
            result=result,
        )
```

### Service Unit Test (No Broker)

```python
@pytest.mark.asyncio
async def test_service_returns_success(make_inbound_message):
    service = DomainService()
    msg = make_inbound_message(payload="test-data")
    result = await service.process(msg)
    assert result.success is True
```

## When to Use

- Every NATS handler/service pair in the project
- When business logic must be testable without a running NATS broker
- When handlers need to remain thin dispatchers with no conditional logic
- When multiple handlers share the same service (e.g. different subjects, same logic)

## Best Practices

- Handlers import from `app` (broker) and `services` — never the reverse
- Services import only from `schemas` — never from `app`, `broker`, or `handlers`
- Keep handler functions to 1-3 lines: receive, delegate, return
- Place all conditional logic, validation, and transformation in the service layer
- Test services directly with `DomainService()` — no broker setup needed
