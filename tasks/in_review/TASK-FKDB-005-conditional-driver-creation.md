---
id: TASK-FKDB-005
title: Conditional driver creation in GraphitiClient and Factory
status: in_review
updated: 2026-02-11T18:00:00Z
created: 2026-02-11T17:00:00Z
priority: high
tags: [falkordb, graphiti-client, migration]
parent_review: TASK-REV-38BC
feature_id: FEAT-FKDB-001
implementation_mode: task-work
wave: 2
complexity: 5
depends_on:
  - TASK-FKDB-002
---

# Task: Conditional driver creation in GraphitiClient and Factory

## Description

Update `GraphitiClient.initialize()`, `_check_connection()`, and `GraphitiClientFactory.get_thread_client()` to create either `Neo4jDriver` or `FalkorDriver` based on the `graph_store` config field.

## Acceptance Criteria

- [ ] AC-001: `initialize()` creates `FalkorDriver(host, port, ...)` when `graph_store=falkordb`
- [ ] AC-002: `initialize()` creates `Graphiti(graph_driver=driver)` (not `Graphiti(uri, user, pwd)`) for FalkorDB
- [ ] AC-003: `initialize()` still uses `Graphiti(uri, user, pwd)` when `graph_store=neo4j` (backwards compatible)
- [ ] AC-004: `_check_connection()` works with both driver types
- [ ] AC-005: `GraphitiClientFactory.get_thread_client()` creates correct driver type per config
- [ ] AC-006: Each thread gets its own FalkorDriver instance (NOT shared — thread safety)
- [ ] AC-007: Log message says "Connected to FalkorDB" or "Connected to Neo4j" as appropriate
- [ ] AC-008: Graceful degradation when `falkordb` package not installed (log warning, disable)
- [ ] AC-009: Tests for both driver paths, factory thread-safety, and missing package handling

## Files to Modify

- `guardkit/knowledge/graphiti_client.py` — `initialize()`, `_check_connection()`, factory methods

## Implementation Notes

The key change in `initialize()`:
```python
if self.config.graph_store == "falkordb":
    try:
        from graphiti_core.driver.falkordb_driver import FalkorDriver
        driver = FalkorDriver(
            host=self.config.falkordb_host,
            port=self.config.falkordb_port,
            username=self.config.neo4j_user if self.config.neo4j_user != "neo4j" else None,
            password=self.config.neo4j_password if self.config.neo4j_password != "password123" else None,
        )
        self._graphiti = Graphiti(graph_driver=driver)
    except ImportError:
        logger.warning("falkordb package not installed. Install with: pip install graphiti-core[falkordb]")
        self._connected = False
        return False
else:
    self._graphiti = Graphiti(
        self.config.neo4j_uri,
        self.config.neo4j_user,
        self.config.neo4j_password,
    )
```

**Thread safety**: The factory's `get_thread_client()` already creates per-thread `GraphitiClient` instances. Each thread's `initialize()` will create its own `FalkorDriver` with its own `FalkorDB` client, bound to that thread's event loop. No factory changes needed beyond ensuring config propagation.

**Verified safe**: DD-2 and DD-5 from the review deep-dive confirm the constructor swap is clean and per-thread creation is the correct pattern.
