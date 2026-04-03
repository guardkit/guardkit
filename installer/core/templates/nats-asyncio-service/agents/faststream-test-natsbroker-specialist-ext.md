# Faststream Test Natsbroker Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **faststream-test-natsbroker-specialist** agent.

**Core documentation**: See [faststream-test-natsbroker-specialist.md](./faststream-test-natsbroker-specialist.md)

---

## Related Templates

- `templates/testing/tests/test_handler.py.template` — Primary template for TestNatsBroker unit tests. Shows async context manager pattern, `tb.publish()` for injecting messages, and `handler.mock` assertions.

- `templates/testing/tests/conftest.py.template` — Shared fixture module with `make_inbound_message` factory function for constructing test data.

- `templates/handlers/handlers/domain.py.template` — The handler being tested, showing `@broker.subscriber` and `@broker.publisher` decorators.

- `templates/other/schemas/__init__.py.template` — Pydantic message schemas used as handler input/output types in tests.

- `templates/infrastructure/example_service/app.py.template` — The module-level broker singleton that TestNatsBroker wraps.

## Code Examples

### Example 1: TestNatsBroker Handler Test

From `templates/testing/tests/test_handler.py.template`:

```python
from __future__ import annotations

import pytest
from faststream.nats import TestNatsBroker

from {{ProjectName}}.app import broker
from {{ProjectName}}.schemas import InboundMessage


@pytest.mark.asyncio
async def test_handler_processes_message(make_inbound_message):
    """Handler receives inbound message and produces outbound result."""
    async with TestNatsBroker(broker) as tb:
        msg = make_inbound_message(payload="test-data")
        await tb.publish(msg, "domain.action.request")
```

### Example 2: Factory Function Fixture

From `templates/testing/tests/conftest.py.template`:

```python
from __future__ import annotations

import pytest
from {{ProjectName}}.schemas import InboundMessage


def _make_inbound_message(**overrides) -> InboundMessage:
    defaults = {
        "source_id": "test-source",
        "payload": "test-payload",
    }
    defaults.update(overrides)
    return InboundMessage(**defaults)


@pytest.fixture
def make_inbound_message():
    return _make_inbound_message
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
