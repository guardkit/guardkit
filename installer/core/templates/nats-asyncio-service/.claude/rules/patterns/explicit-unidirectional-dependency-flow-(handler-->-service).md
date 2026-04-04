---
paths: "**/handlers/*.py, **/services/*.py, **/app.py"
---

# Explicit Unidirectional Dependency Flow (Handler -> Service)

## Overview

Dependencies flow in one direction: `app.py` -> `handlers/` -> `services/` -> `schemas/`. Handlers import from `app` (broker) and `services`, but services never import from handlers or app. This prevents circular imports and ensures business logic remains decoupled from messaging infrastructure.

## Implementation

### Dependency Graph

```
app.py (broker, settings, app)
  └── handlers/domain.py (imports broker from app, DomainService from services)
        └── services/domain.py (imports only from schemas)
              └── schemas/__init__.py (standalone Pydantic models)
```

### Handler (imports from app + services)

```python
from example_service.app import broker          # ← imports from app
from example_service.schemas import InboundMessage, OutboundMessage
from example_service.services.domain import DomainService  # ← imports from services

service = DomainService()

@broker.subscriber("domain.action.request")
@broker.publisher("domain.action.result")
async def handle_domain_action(msg: InboundMessage) -> OutboundMessage:
    return await service.process(msg)
```

### Service (imports only from schemas)

```python
from example_service.schemas import InboundMessage, OutboundMessage

class DomainService:
    """No imports from app, broker, or handlers."""

    async def process(self, msg: InboundMessage) -> OutboundMessage:
        return OutboundMessage(
            correlation_id=msg.message_id,
            source_id="example-service",
            success=True,
            result=f"Processed: {msg.payload}",
        )
```

### Schemas (no internal imports)

```python
from pydantic import BaseModel, ConfigDict, Field

class InboundMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source_id: str
    payload: str
```

## When to Use

- Every module boundary in the service — this is the architectural invariant
- When adding new handlers, services, or schema modules
- When refactoring to prevent circular import errors
- When reviewing pull requests for dependency direction violations

## Best Practices

- Services must never `from app import broker` — that is a handler responsibility
- Schemas must never import from services, handlers, or app
- If a service needs configuration, pass it via constructor arguments, not by importing `settings`
- Use `import handlers` at the bottom of `app.py` (after broker is defined) to avoid circular imports
- Test services by direct instantiation — if a service test needs a broker, the dependency direction is wrong
