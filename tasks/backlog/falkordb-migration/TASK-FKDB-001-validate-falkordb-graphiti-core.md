---
id: TASK-FKDB-001
title: Validate FalkorDB + graphiti-core end-to-end
status: backlog
created: 2026-02-11T17:00:00Z
priority: high
tags: [falkordb, validation, graphiti, migration]
parent_review: TASK-REV-38BC
feature_id: FEAT-FKDB-001
implementation_mode: direct
wave: 0
complexity: 4
---

# Task: Validate FalkorDB + graphiti-core end-to-end

## Description

Before any code changes, validate that graphiti-core's FalkorDriver actually works with a real FalkorDB instance. graphiti-core ships the driver code but has **no tests for it** (DD-6 finding from TASK-REV-38BC). GuardKit would be an early adopter — we need confidence before proceeding.

## Acceptance Criteria

- [ ] AC-001: `pip install graphiti-core[falkordb]` succeeds and `falkordb` package is importable
- [ ] AC-002: FalkorDB Docker container starts and responds to health checks
- [ ] AC-003: `Graphiti(graph_driver=FalkorDriver(...))` + `build_indices_and_constraints()` succeeds
- [ ] AC-004: `add_episode()` creates an episode in FalkorDB (verified by subsequent search)
- [ ] AC-005: `search()` returns the episode created in AC-004 with correct content
- [ ] AC-006: Fulltext search with `group_ids` parameter returns filtered results
- [ ] AC-007: Datetime fields survive the add_episode → search round-trip
- [ ] AC-008: `driver.execute_query()` returns `(records, header, None)` tuple as documented

## Implementation Notes

Create a standalone validation script (not production code) that:
1. Starts FalkorDB via Docker Compose
2. Installs `graphiti-core[falkordb]` in a test venv
3. Runs the 8 acceptance criteria checks
4. Reports pass/fail for each

**If any check fails**, stop the migration and file upstream issues on graphiti-core before proceeding.

### FalkorDB Docker quick start:
```bash
docker run -d --name falkordb-test -p 6379:6379 falkordb/falkordb:latest
```

### Minimal validation code:
```python
from graphiti_core import Graphiti
from graphiti_core.driver.falkordb_driver import FalkorDriver

driver = FalkorDriver(host='localhost', port=6379)
g = Graphiti(graph_driver=driver)
await g.build_indices_and_constraints()
# ... add_episode, search, verify
await g.close()
```

## Gate

This task is a **gate** for all subsequent FEAT-FKDB-001 tasks. If validation fails, the migration is blocked pending upstream fixes.
