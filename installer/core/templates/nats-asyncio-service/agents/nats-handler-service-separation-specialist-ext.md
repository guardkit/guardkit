# Nats Handler Service Separation Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **nats-handler-service-separation-specialist** agent.

**Core documentation**: See [nats-handler-service-separation-specialist.md](./nats-handler-service-separation-specialist.md)

---

## Related Templates

- `templates/handlers/handlers/domain.py.template` — Thin handler implementation: receives Pydantic message via `@broker.subscriber`, delegates to `DomainService.process()`, returns result for `@broker.publisher`.

- `templates/services/services/domain.py.template` — Pure service class with `process()` method. Contains all business logic with zero NATS/broker imports. Independently testable.

- `templates/testing/tests/test_service.py.template` — Service unit tests that instantiate DomainService directly without any broker or NATS infrastructure.

- `templates/testing/tests/test_handler.py.template` — Handler tests using TestNatsBroker that verify the handler-to-service delegation chain.

- `templates/other/schemas/__init__.py.template` — Pydantic schemas that define the contract between handler and service layers.

## Code Examples

### Example 1: Thin Handler (Dispatch Only)

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

### Example 2: Pure Service (No NATS Imports)

From `templates/services/services/domain.py.template`:

```python
from __future__ import annotations

from {{ProjectName}}.schemas import InboundMessage, OutboundMessage


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

### Example 3: Service Unit Test (No Broker)

From `templates/testing/tests/test_service.py.template`:

```python
from __future__ import annotations

import pytest
from {{ProjectName}}.services.domain import DomainService


@pytest.mark.asyncio
async def test_service_returns_success(make_inbound_message):
    service = DomainService()
    msg = make_inbound_message(payload="test-data")
    result = await service.process(msg)
    assert result.success is True
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
