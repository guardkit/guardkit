# AGENTS.md — Service Boundary Document

## ALWAYS

- Define a Pydantic schema for every NATS subject (both inbound and outbound)
- Keep handlers thin — validate, delegate to service, return result
- Put all business logic in `services/`, never in `handlers/`
- Use `TestNatsBroker` for handler unit tests — no real NATS server needed
- Use factory functions in `conftest.py` for test data (not fixture-heavy patterns)
- Log to stderr only — stdout must never be used for log output
- Use `from __future__ import annotations` on all modules
- Use `pydantic-settings` for all configuration — never hardcode connection strings
- Follow the subject hierarchy convention: `domain.action.qualifier.{id}`
- Include `correlation_id` in response messages to link to originating requests
- Use `ConfigDict(extra="ignore")` on all message schemas for forward compatibility

## NEVER

- Put business logic in handlers — handlers are thin dispatchers only
- Pass raw bytes through NATS — always use typed Pydantic models
- Skip `ack()` on JetStream messages — unacknowledged messages redelivery
- Hardcode NATS URLs or subject strings — use config and constants
- Use `print()` for logging — use `logging` to stderr
- Import from `handlers/` in `services/` — dependency flows one way: handler → service
- Block the asyncio event loop with synchronous I/O

## ASK (decide per-project)

- Push vs pull subscribe for JetStream consumers
- Stream retention policy (WorkQueue vs Limits vs Interest)
- Whether to use NATS KV store for service state
- Durable consumer names and replay policy
- Message deduplication window
- Dead letter queue strategy for failed messages
