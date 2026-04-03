# Pytest Asyncio Service Unit Test Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **pytest-asyncio-service-unit-test-specialist** agent.

**Core documentation**: See [pytest-asyncio-service-unit-test-specialist.md](./pytest-asyncio-service-unit-test-specialist.md)

---

## Related Templates

- `templates/testing/tests/test_service.py.template` — Primary template for service unit tests. Shows direct DomainService instantiation, factory fixture usage, and assertions on OutboundMessage fields.

- `templates/testing/tests/conftest.py.template` — Shared fixture module with `make_inbound_message` factory function.

- `templates/services/services/domain.py.template` — The service class being tested, with `process()` method that accepts InboundMessage and returns OutboundMessage.

- `templates/other/schemas/__init__.py.template` — Pydantic schemas used for typed test assertions.

## Code Examples

### Example 1: Service Unit Test

From `templates/testing/tests/test_service.py.template`:

```python
from __future__ import annotations

import pytest
from {{ProjectName}}.services.domain import DomainService


@pytest.mark.asyncio
async def test_service_returns_success(make_inbound_message):
    """Service processes message and returns successful result."""
    service = DomainService()
    msg = make_inbound_message(payload="test-data")
    result = await service.process(msg)
    assert result.success is True
    assert "test-data" in result.result


@pytest.mark.asyncio
async def test_service_links_correlation_id(make_inbound_message):
    """Service sets correlation_id to inbound message_id."""
    service = DomainService()
    msg = make_inbound_message()
    result = await service.process(msg)
    assert result.correlation_id == msg.message_id


@pytest.mark.asyncio
async def test_service_sets_source_id(make_inbound_message):
    """Service identifies itself via source_id."""
    service = DomainService()
    msg = make_inbound_message()
    result = await service.process(msg)
    assert result.source_id == "example-service"
```

### Example 2: Factory Fixture

From `templates/testing/tests/conftest.py.template`:

```python
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
