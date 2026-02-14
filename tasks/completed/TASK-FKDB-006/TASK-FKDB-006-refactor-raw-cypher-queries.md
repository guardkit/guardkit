---
id: TASK-FKDB-006
title: Refactor 3 raw Cypher queries to driver-agnostic execute_query()
status: completed
completed: 2026-02-11T18:00:00Z
created: 2026-02-11T17:00:00Z
priority: high
tags: [falkordb, critical-path, graphiti-client, migration]
parent_review: TASK-REV-38BC
feature_id: FEAT-FKDB-001
implementation_mode: task-work
wave: 2
complexity: 5
depends_on:
  - TASK-FKDB-005
---

# Task: Refactor 3 raw Cypher queries to driver-agnostic execute_query()

## Description

**CRITICAL PATH ITEM.** Refactor the 3 raw Cypher queries in `graphiti_client.py` from `driver.session().run()` + Neo4j-specific result methods (`.data()`, `.single()`) to `driver.execute_query()` + tuple unpacking. This is the only code that will **crash at runtime** under FalkorDB (DD-4: `FalkorDriverSession.run()` returns `None`).

## Acceptance Criteria

- [ ] AC-001: `_list_groups()` uses `driver.execute_query()` instead of `driver.session().run()`
- [ ] AC-002: `_clear_group()` uses `driver.execute_query()` instead of `driver.session().run()`
- [ ] AC-003: `get_clear_preview()` uses `driver.execute_query()` instead of `driver.session().run()`
- [ ] AC-004: All 3 methods handle `None` return from `execute_query()` (DD-8: FalkorDB edge case)
- [ ] AC-005: All 3 methods use `records, _, _ = result` unpacking (works for both Neo4j EagerResult and FalkorDB tuple)
- [ ] AC-006: Existing tests updated to reflect new query pattern
- [ ] AC-007: New tests verify both Neo4j-style and FalkorDB-style return types
- [ ] AC-008: No regressions in existing clear/list functionality

## Files to Modify

- `guardkit/knowledge/graphiti_client.py` — Lines 1072-1096 (`_list_groups`), 1097-1129 (`_clear_group`), 1275-1372 (`get_clear_preview`)
- `tests/knowledge/test_graphiti_client_clear.py` — Update mocks
- `tests/cli/test_graphiti_list.py` — Update mocks

## Implementation Notes

### Exact refactors (from TASK-REV-38BC deep-dive):

**`_list_groups()` (line 1087):**
```python
# BEFORE:
async with driver.session() as session:
    result = await session.run(
        "MATCH (e:Episode) RETURN DISTINCT e.group_id AS group_id"
    )
    records = await result.data()
    return [r["group_id"] for r in records if r.get("group_id")]

# AFTER:
result = await driver.execute_query(
    "MATCH (e:Episode) RETURN DISTINCT e.group_id AS group_id"
)
if result is None:
    return []
records, _, _ = result
return [r["group_id"] for r in records if r.get("group_id")]
```

**`_clear_group()` (line 1114):**
```python
# BEFORE:
async with driver.session() as session:
    result = await session.run(query, group_id=group_id)
    record = await result.single()
    return record["count"] if record else 0

# AFTER:
result = await driver.execute_query(query, group_id=group_id)
if result is None:
    return 0
records, _, _ = result
return records[0]["count"] if records else 0
```

**`get_clear_preview()` (line 1342):**
```python
# BEFORE:
async with driver.session() as session:
    result = await session.run(query, groups=target_groups)
    record = await result.single()
    estimated = record["count"] if record else 0

# AFTER:
result = await driver.execute_query(query, groups=target_groups)
if result is None:
    estimated = 0
else:
    records, _, _ = result
    estimated = records[0]["count"] if records else 0
```

### Why this is safe (verified in DD-1):

- Neo4j `EagerResult` is a named tuple — `result[0]` returns records
- FalkorDB returns `(records, header, None)` — `result[0]` returns records
- graphiti-core itself uses `records, _, _ = result` at 20+ call sites
- Both drivers return records as `List[Dict]` for these simple queries
