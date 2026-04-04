---
paths: "**/tests/test_handler*.py, **/tests/test_*.py"
---

# In-Memory Broker Testing via TestNatsBroker

## Overview

FastStream's `TestNatsBroker` wraps the module-level broker singleton in an in-memory transport, enabling handler tests to run without a real NATS server. Messages are published via `tb.publish()`, handlers execute synchronously within the context manager, and handler invocations can be verified via `handler.mock` assertions.

## Implementation

### Handler Test with TestNatsBroker

```python
from __future__ import annotations

import pytest
from faststream.nats import TestNatsBroker

from example_service.app import broker
from example_service.schemas import InboundMessage


@pytest.mark.asyncio
async def test_handler_processes_message(make_inbound_message):
    """Handler receives inbound message and produces outbound result."""
    async with TestNatsBroker(broker) as tb:
        msg = make_inbound_message(payload="test-data")
        await tb.publish(msg, "domain.action.request")
```

### Verifying Handler Was Called

```python
from example_service.handlers.domain import handle_domain_action

@pytest.mark.asyncio
async def test_handler_was_invoked(make_inbound_message):
    async with TestNatsBroker(broker) as tb:
        msg = make_inbound_message()
        await tb.publish(msg, "domain.action.request")
        handle_domain_action.mock.assert_called_once()
```

### How It Works

```
TestNatsBroker(broker)
    ├── Wraps the module-level broker singleton
    ├── Replaces NATS transport with in-memory queue
    ├── tb.publish() injects messages into handlers
    ├── Handlers execute within the async context manager
    └── handler.mock tracks invocations for assertions
```

## When to Use

- Every handler unit test — TestNatsBroker is the standard handler testing tool
- When testing handler-to-service delegation without NATS infrastructure
- When verifying message routing (correct subject triggers correct handler)
- When checking handler invocation counts via `.mock` assertions

## Best Practices

- Always use `async with TestNatsBroker(broker) as tb:` — the context manager handles setup and teardown
- Import the module-level `broker` from `app.py` — TestNatsBroker wraps the existing singleton
- Use `tb.publish(msg, "subject")` to inject messages — do not call handlers directly
- Use `handler.mock.assert_called_once()` to verify handlers were triggered
- Combine with factory fixtures for test data: `make_inbound_message(payload="test-data")`
- For integration tests against real NATS, use `@pytest.mark.integration` instead (see marker-gated-integration-tests pattern)
