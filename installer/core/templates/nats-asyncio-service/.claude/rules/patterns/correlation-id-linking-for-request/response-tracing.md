---
paths: "**/schemas/*.py, **/schemas.py, **/services/*.py"
---

# Correlation ID Linking for Request/Response Tracing

## Overview

Every outbound message carries a `correlation_id` set to the inbound message's `message_id`. This creates a traceable link between request and response, enabling distributed tracing across NATS subjects without external tracing infrastructure.

## Implementation

### Schema Definitions

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
    correlation_id: str   # Links to inbound message_id
    success: bool
    result: str
```

### Correlation Linking in Service

```python
class DomainService:
    async def process(self, msg: InboundMessage) -> OutboundMessage:
        return OutboundMessage(
            correlation_id=msg.message_id,  # Links response to request
            source_id="example-service",
            success=True,
            result=f"Processed: {msg.payload}",
        )
```

### Test Verification

```python
@pytest.mark.asyncio
async def test_service_links_correlation_id(make_inbound_message):
    service = DomainService()
    msg = make_inbound_message()
    result = await service.process(msg)
    assert result.correlation_id == msg.message_id
```

## When to Use

- Every request/response message pair in the service
- When downstream consumers need to match responses to their original requests
- When debugging message flow across multiple NATS subjects
- When building audit trails or log correlation

## Best Practices

- Always set `correlation_id = msg.message_id` in the service, not the handler
- Use `uuid4` for `message_id` generation via `Field(default_factory=...)` — never manual strings
- Use `ConfigDict(extra="ignore")` on all message schemas for forward compatibility
- Auto-generate `timestamp` with UTC timezone — never accept client-provided timestamps
- Test correlation linking explicitly — it is a critical contract between services
