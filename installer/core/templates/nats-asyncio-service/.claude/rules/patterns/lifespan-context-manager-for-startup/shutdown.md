---
paths: "**/app.py"
---

# Lifespan Context Manager for Startup/Shutdown

## Overview

FastStream uses an `@asynccontextmanager` lifespan function passed to the `FastStream` constructor. Code before `yield` runs at startup (acquire resources, connect to databases), code after `yield` runs at shutdown (release resources, close connections). This ensures clean resource management without scattered init/cleanup code.

## Implementation

### Basic Lifespan in app.py

```python
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from faststream import FastStream
from faststream.nats import NatsBroker

from example_service.config import Settings

settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    stream=sys.stderr,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

broker = NatsBroker(settings.nats_url)

@asynccontextmanager
async def lifespan():
    # Startup: acquire resources, warm caches, check connectivity
    yield
    # Shutdown: release resources, flush buffers, close connections

app = FastStream(broker, lifespan=lifespan)
```

### Entry Point

```python
from __future__ import annotations

import asyncio
from example_service.app import app

if __name__ == "__main__":
    asyncio.run(app.run())
```

## When to Use

- Every FastStream application needs a lifespan function
- When the service connects to external resources (databases, caches, HTTP clients)
- When startup validation is needed (config checks, health probes)
- When graceful shutdown requires resource cleanup (flushing logs, closing pools)

## Best Practices

- Always define the lifespan as an `@asynccontextmanager` — not a plain function
- Place all startup logic before `yield`, all shutdown logic after
- Pass the lifespan to `FastStream(broker, lifespan=lifespan)` — not to the broker
- Configure logging to `sys.stderr` (not stdout) to avoid mixing with NATS message output
- Use `getattr(logging, settings.log_level.upper())` to derive log level from config
- Keep the lifespan in `app.py` alongside broker and app instantiation
