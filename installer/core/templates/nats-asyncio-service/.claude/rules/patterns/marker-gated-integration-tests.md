---
paths: "**/tests/test_integration*.py, **/pyproject.toml, **/docker-compose*.yml"
---

# Marker-Gated Integration Tests

## Overview

Integration tests that require a real NATS server are gated behind `@pytest.mark.integration`. By default, pytest excludes these tests via `addopts = "-m 'not integration'"` in `pyproject.toml`. Developers run them explicitly with `pytest -m integration` when Docker Compose NATS is available. This prevents CI failures from missing infrastructure while still supporting full end-to-end testing.

## Implementation

### Integration Test with Real NATS

```python
import asyncio

import nats
import nats.aio.msg
import pytest

from example_service.app import broker
from example_service.schemas import InboundMessage, OutboundMessage


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_roundtrip_with_real_nats() -> None:
    """End-to-end test: publish message, handler processes, result published."""
    await broker.start()
    try:
        nc = await nats.connect("nats://localhost:4222")
        try:
            received: list[OutboundMessage] = []
            event = asyncio.Event()

            async def on_result(msg: nats.aio.msg.Msg) -> None:
                received.append(OutboundMessage.model_validate_json(msg.data))
                event.set()

            sub = await nc.subscribe("domain.action.result", cb=on_result)
            await asyncio.sleep(0.2)

            inbound = InboundMessage(
                source_id="integration-test",
                payload="roundtrip-check",
            )
            await broker.publish(inbound, "domain.action.request")
            await asyncio.wait_for(event.wait(), timeout=5.0)

            assert len(received) == 1
            result = received[0]
            assert result.success is True
            assert result.correlation_id == inbound.message_id

            await sub.unsubscribe()
        finally:
            await nc.close()
    finally:
        await broker.stop()
```

### Marker Registration in pyproject.toml

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-m 'not integration'"
markers = [
    "integration: requires real NATS server (run with '-m integration')",
    "seam: cross-module contract tests",
    "integration_contract: tests that verify integration contracts",
]
```

### Docker Compose NATS with JetStream

```yaml
services:
  nats:
    image: nats:latest
    ports:
      - "4222:4222"
      - "8222:8222"
    command: ["-js", "-m", "8222"]
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8222/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3
```

## When to Use

- Testing full message roundtrips through real NATS infrastructure
- Verifying broker start/stop lifecycle with actual connections
- Testing JetStream features (persistence, replay) not available in TestNatsBroker
- CI/CD pipelines with Docker Compose NATS available

## Best Practices

- Always dual-mark with `@pytest.mark.integration` and `@pytest.mark.asyncio`
- Default-exclude via `addopts = "-m 'not integration'"` so plain `pytest` skips them
- Run explicitly with `pytest -m integration` when NATS is available
- Use `broker.start()` / `broker.stop()` in `try/finally` for clean lifecycle management
- Use `asyncio.Event` + `asyncio.wait_for(timeout=5.0)` to avoid hanging tests
- Use raw `nats.connect()` client for subscribing to result subjects — independent of FastStream
- Always clean up: `sub.unsubscribe()`, `nc.close()`, `broker.stop()`
