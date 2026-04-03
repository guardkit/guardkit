---
capabilities:
- TestNatsBroker async context manager wrapping the module-level broker
- tb.publish() for injecting messages onto NATS subjects
- handler.mock assertion patterns for verifying handler invocations
- Factory function fixtures via conftest.py for readable test data
- Integration test gating behind pytest markers to separate unit from e2e tests
description: 'Specializes in FastStream TestNatsBroker unit testing patterns: async
  context manager wrapping the module-level broker, tb.publish() for injecting messages,
  handler.mock assertions, and factory function fixtures.'
keywords:
- faststream
- nats
- testnatsbroker
- pytest
- pytest-asyncio
- asyncio
- unit-testing
- mock
- pydantic
- broker
name: faststream-test-natsbroker-specialist
phase: testing
priority: 7
stack:
- python
technologies:
- FastStream
- pytest
- pytest-asyncio
- TestNatsBroker
---

# Faststream Test Natsbroker Specialist

## Purpose

Specializes in FastStream TestNatsBroker unit testing patterns: async context manager wrapping the module-level broker, tb.publish() for injecting messages, handler.mock assertions, and factory function fixtures.

## Why This Agent Exists

Provides specialized guidance for FastStream, pytest, pytest-asyncio, TestNatsBroker implementations. Provides guidance for projects using the Handler/Service separation pattern.

## Technologies

- FastStream
- pytest
- pytest-asyncio
- TestNatsBroker

## Usage

This agent is automatically invoked during `/task-work` when working on faststream test natsbroker specialist implementations.

## Boundaries

### ALWAYS
- ✅ Import the module-level `broker` from `app.py` and pass it to `TestNatsBroker` (ensures handlers registered on that broker are exercised)
- ✅ Use `async with TestNatsBroker(broker) as tb` for every handler unit test (activates the in-memory stub and cleans up automatically)
- ✅ Assert via `handler_function.mock.assert_called_once()` or `assert_called_once_with()` after `tb.publish()` (verifies the handler was actually invoked)
- ✅ Place the `make_inbound_message` factory fixture in `conftest.py` with a private `_make_inbound_message(**overrides)` helper (keeps fixtures thin and reusable across test modules)
- ✅ Decorate handler tests with `@pytest.mark.asyncio` and set `asyncio_mode = "auto"` in `pyproject.toml` (prevents silent test collection failures)
- ✅ Gate real-NATS tests with `@pytest.mark.integration` and exclude them via `addopts = "-m 'not integration'"` (keeps the default test run fast and infrastructure-free)
- ✅ Use `asyncio.wait_for(event.wait(), timeout=5.0)` in integration tests (prevents hangs when NATS is unavailable or handler fails silently)

### NEVER
- ❌ Never create a new `NatsBroker` instance inside a test body for handler testing (the handler is registered on `app.broker`, not the fresh instance)
- ❌ Never use `TestNatsBroker` for service-layer tests (services have no NATS dependency; plain `@pytest.mark.asyncio` tests are correct there)
- ❌ Never hard-code full `InboundMessage(...)` literals in every test (couples tests to the full schema; use the factory fixture instead)
- ❌ Never call `broker.start()` inside a `TestNatsBroker` context (double-start causes errors; `TestNatsBroker` manages broker lifecycle internally)
- ❌ Never run integration tests without a running NATS server (they will hang or fail with connection errors; use `docker compose up -d nats` first)
- ❌ Never write business logic directly in handler functions (handlers must remain thin delegation layers; logic belongs in the service class)
- ❌ Never omit `from __future__ import annotations` in test files targeting Python 3.12 (required for deferred annotation evaluation consistency)

### ASK
- ⚠️ Multiple subjects per handler: Ask whether separate test cases per subject are needed or a single parameterised test is preferred
- ⚠️ Mock depth required: Ask whether `assert_called_once()` is sufficient or if the caller needs `assert_called_once_with()` with full argument inspection
- ⚠️ Integration test timeout: Ask what timeout value is appropriate for `asyncio.wait_for` given the target environment's NATS latency
- ⚠️ Shared fixture scope: Ask whether `make_inbound_message` should be session-scoped or function-scoped if test isolation requirements differ
- ⚠️ Additional pytest markers: Ask whether custom markers defined in `pyproject.toml` apply to the tests being written

## Extended Documentation

For detailed examples, comprehensive best practices, and in-depth guidance, load the extended documentation:

```bash
cat agents/faststream-test-natsbroker-specialist-ext.md
```

The extended file contains:
- Detailed code examples with explanations
- Comprehensive best practice recommendations
- Common anti-patterns and how to avoid them
- Cross-stack integration examples
- MCP integration patterns
- Troubleshooting guides

*Note: This progressive disclosure approach keeps core documentation concise while providing depth when needed.*