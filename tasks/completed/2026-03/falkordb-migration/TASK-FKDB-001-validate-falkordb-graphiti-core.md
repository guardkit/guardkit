---
id: TASK-FKDB-001
title: Validate FalkorDB + graphiti-core end-to-end
status: completed
created: 2026-02-11T17:00:00Z
updated: 2026-02-11T20:47:00Z
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

- [x] AC-001: `pip install graphiti-core[falkordb]` succeeds and `falkordb` package is importable
- [x] AC-002: FalkorDB Docker container starts and responds to health checks
- [x] AC-003: `Graphiti(graph_driver=FalkorDriver(...))` + `build_indices_and_constraints()` succeeds
- [x] AC-004: `add_episode()` creates an episode in FalkorDB (verified by subsequent search)
- [x] AC-005: `search()` returns the episode created in AC-004 with correct content
- [x] AC-006: Fulltext search with `group_ids` parameter returns filtered results — **PASS (workaround applied, TASK-FKDB-32D9)**
- [x] AC-007: Datetime fields survive the add_episode → search round-trip
- [x] AC-008: `driver.execute_query()` returns `(records, header, None)` tuple as documented

## Validation Results (2026-02-11)

**8/8 passed — FalkorDB migration UNBLOCKED**

### All Passing (8)

| AC | Result | Details |
|----|--------|---------|
| AC-001 | PASS | `falkordb==1.4.0` + `redis==7.1.1` installed via `pip install graphiti-core[falkordb]` |
| AC-002 | PASS | `falkordb/falkordb:latest` container healthy, Redis PING/PONG confirmed |
| AC-003 | PASS | `Graphiti(graph_driver=FalkorDriver(host, port, database))` + `build_indices_and_constraints()` completed |
| AC-004 | PASS | `add_episode()` completed in 7.6-8.7s (LLM entity extraction), episode UUID returned |
| AC-005 | PASS | `search()` returned 2 results immediately after single `add_episode()` |
| AC-006 | PASS | Single group_id search works correctly with monkey-patch workaround (TASK-FKDB-32D9). Group A: 2, Group B: 1 |
| AC-007 | PASS | `reference_time` (2026-02-11T12:00:00Z) preserved in `episode.valid_at`, `created_at` also correct |
| AC-008 | PASS | `execute_query()` returns `(List[Dict], List[str], None)` tuple — matches documented format |

### UPSTREAM BUG: `@handle_multiple_group_ids` Decorator — Single Group ID Not Cloned

**Root cause CONFIRMED (re-validation 2026-02-11T20:12Z, graphiti-core v0.26.3):**

The `@handle_multiple_group_ids` decorator in `graphiti_core/decorators.py` only clones the FalkorDB driver when `len(group_ids) > 1`. For single group_id searches, it falls through to normal execution using `self.driver` — which was mutated by the prior `add_episode()` to point at the **wrong database**.

**Mechanism:**
1. `add_episode("ep1", group_id="A")` → `self.driver = self.driver.clone(database="A")` → driver on DB "A"
2. `search(query, group_ids=["A"])` → **3 results** (driver correctly on DB "A")
3. `add_episode("ep2", group_id="B")` → `self.driver = self.driver.clone(database="B")` → driver on DB "B"
4. `search(query, group_ids=["A"])` → decorator sees `len(["A"]) == 1` → **falls through** → searches DB "B" → **0 results**
5. `search(query, group_ids=["A", "B"])` → decorator sees `len > 1` → **clones per group** → **3 results** (correct!)

**Evidence from diagnostic run:**
```
Single group_id - Group A: 0, Group B: 1   ← BROKEN (searches wrong DB)
Multi  group_id - Both groups: 3            ← WORKS  (decorator clones correctly)
Current driver._database: fkdb_validation_b_20260211_201210  ← mutated to B
```

**Fix required in graphiti-core:** Change `len(group_ids) > 1` to `len(group_ids) >= 1` in `decorators.py` line ~54 so single group_id searches also get a cloned driver.

**GuardKit workaround (if fix not accepted upstream):** Always pass a dummy second group_id to trigger the decorator, or manually reset `g.driver` after each `add_episode()`.

**Impact:** FalkorDB is unusable for GuardKit without this fix (knowledge graph uses single group_id searches). Migration BLOCKED until upstream fix or workaround adopted.

**Action required:** File issue on [graphiti-core](https://github.com/getzep/graphiti) with the diagnostic output and proposed one-line fix.

### Additional Finding: MATCH Queries Return Empty

FalkorDB's `execute_query("MATCH (n) RETURN ...")` returns 0 records even when nodes are confirmed to exist (via successful `search()` and `add_episode()` return values). This suggests FalkorDB's graph query layer and fulltext search layer have different visibility semantics. This is relevant for TASK-FKDB-006 (raw Cypher query refactoring).

### Additional Finding: Constructor Auto-Index Build

`FalkorDriver.__init__()` schedules `build_indices_and_constraints()` via `loop.create_task()`. Creating multiple `FalkorDriver` instances concurrently (or in quick succession) overwhelms FalkorDB with simultaneous index creation requests, causing `ConnectionError: Connection closed by server` and `RedisError: Buffer is closed` errors. GuardKit's `GraphitiClientFactory` creates per-thread drivers — this pattern needs careful sequencing during initialization.

## Gate Status

**UNBLOCKED** — All 8 acceptance criteria pass. Monkey-patch workaround (TASK-FKDB-32D9) fixes the upstream `@handle_multiple_group_ids` decorator bug. TASK-FKDB-002 through TASK-FKDB-008 can proceed.

**Workaround:** `guardkit/knowledge/falkordb_workaround.py` patches the decorator at import time. Auto-detects upstream fix and becomes a no-op when PR #1170 merges.

## Files Created

- `docker/docker-compose.falkordb-test.yml` — FalkorDB test container
- `scripts/graphiti-validation/validate_falkordb.py` — Validation script (8 AC checks)

## Implementation Notes

Create a standalone validation script (not production code) that:
1. Starts FalkorDB via Docker Compose
2. Installs `graphiti-core[falkordb]` in a test venv
3. Runs the 8 acceptance criteria checks
4. Reports pass/fail for each

**If any check fails**, stop the migration and file upstream issues on graphiti-core before proceeding.

### FalkorDB Docker quick start:
```bash
docker compose -f docker/docker-compose.falkordb-test.yml up -d
```

### Run validation:
```bash
python scripts/graphiti-validation/validate_falkordb.py
```
