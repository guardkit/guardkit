# Nats Docker Integration Test Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **nats-docker-integration-test-specialist** agent.

**Core documentation**: See [nats-docker-integration-test-specialist.md](./nats-docker-integration-test-specialist.md)

---

## Related Templates

- `templates/testing/tests/test_integration.py.template` — Primary template for marker-gated integration tests. Demonstrates the complete `@pytest.mark.integration` + `@pytest.mark.asyncio` dual-marker pattern, `broker.start()` / `broker.stop()` lifecycle wrapping, raw `nats.connect()` subscriber setup, `asyncio.Event` coordination, `asyncio.wait_for()` timeout guard, and full roundtrip assertions on `OutboundMessage` Pydantic fields.

- `templates/other/other/docker-compose.yml.template` — Docker Compose service definition that backs all integration tests. Shows the `nats:latest` image with `-js -m 8222` flags to enable JetStream, port mappings for client (4222) and monitoring (8222), a `wget`-based healthcheck against `/healthz`, and the `depends_on: condition: service_healthy` pattern.

- `templates/other/other/pyproject.toml.template` — Source of truth for marker registration and default exclusion. Contains `addopts = "-m 'not integration'"` and the `markers` table.

- `templates/testing/tests/conftest.py.template` — Shared fixture module with `make_inbound_message` factory fixture.

## Code Examples

### Example 1: Full Roundtrip Integration Test

From `templates/testing/tests/test_integration.py.template`:

```python
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

### Example 2: Docker Compose JetStream Configuration

From `templates/other/other/docker-compose.yml.template`:

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

### Example 3: Marker Registration in pyproject.toml

From `templates/other/other/pyproject.toml.template`:

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

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
