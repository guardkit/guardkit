# Pydantic Nats Schema Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **pydantic-nats-schema-specialist** agent.

**Core documentation**: See [pydantic-nats-schema-specialist.md](./pydantic-nats-schema-specialist.md)

---

## Related Templates

- `templates/other/schemas/__init__.py.template` — Primary schema template. Defines InboundMessage and OutboundMessage with ConfigDict(extra="ignore"), UUID message_id, UTC timestamp, version, source_id, and correlation_id fields.

- `templates/handlers/handlers/domain.py.template` — Handler that receives InboundMessage and returns OutboundMessage, showing schema usage at the handler boundary.

- `templates/services/services/domain.py.template` — Service that accepts InboundMessage and constructs OutboundMessage, showing correlation_id linking.

- `templates/testing/tests/conftest.py.template` — Factory fixture for constructing InboundMessage test instances with default values.

## Code Examples

### Example 1: Pydantic Message Schemas

From `templates/other/schemas/__init__.py.template`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


class InboundMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0"
    source_id: str
    payload: str


class OutboundMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0"
    source_id: str
    correlation_id: str
    success: bool
    result: str
```

### Example 2: Correlation ID Linking in Service

From `templates/services/services/domain.py.template`:

```python
async def process(self, msg: InboundMessage) -> OutboundMessage:
    return OutboundMessage(
        correlation_id=msg.message_id,  # Links response to request
        source_id="example-service",
        success=True,
        result=f"Processed: {msg.payload}",
    )
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
