---
paths: "**/tests/conftest.py, **/tests/*.py"
---

# Factory Function Pattern for Test Data

## Overview

Test data is constructed via factory functions exposed as pytest fixtures. A private `_make_*` function builds Pydantic models with sensible defaults, and a `@pytest.fixture` exposes it. Tests call the fixture with keyword overrides for only the fields they care about, keeping test code concise and intention-revealing.

## Implementation

### Factory Function in conftest.py

```python
from __future__ import annotations

import pytest
from example_service.schemas import InboundMessage


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

### Usage in Service Tests

```python
@pytest.mark.asyncio
async def test_service_returns_success(make_inbound_message):
    service = DomainService()
    msg = make_inbound_message(payload="test-data")
    result = await service.process(msg)
    assert result.success is True
    assert "test-data" in result.result
```

### Usage in Handler Tests

```python
@pytest.mark.asyncio
async def test_handler_processes_message(make_inbound_message):
    async with TestNatsBroker(broker) as tb:
        msg = make_inbound_message(payload="test-data")
        await tb.publish(msg, "domain.action.request")
```

## When to Use

- Every test that creates Pydantic message instances
- When multiple tests need similar test data with small variations
- When adding new message schemas — create a matching factory fixture
- When test readability matters — `make_inbound_message(payload="x")` is clearer than constructing the full object

## Best Practices

- Name the private function `_make_{schema_name}` and the fixture `make_{schema_name}`
- Provide defaults for all required fields so tests only override what they care about
- Use `**overrides` pattern: merge defaults with caller-provided values
- Place all factory fixtures in `conftest.py` so they are available to all test modules
- Return the factory function from the fixture (not a constructed instance) — this lets each test customise the data
- Create one factory per message schema — don't reuse factories across unrelated schemas
