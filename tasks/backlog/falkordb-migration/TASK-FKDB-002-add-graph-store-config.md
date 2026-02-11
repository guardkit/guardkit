---
id: TASK-FKDB-002
title: Add graph_store config field and FalkorDB connection params
status: backlog
created: 2026-02-11T17:00:00Z
priority: high
tags: [falkordb, config, migration]
parent_review: TASK-REV-38BC
feature_id: FEAT-FKDB-001
implementation_mode: task-work
wave: 1
complexity: 4
depends_on:
  - TASK-FKDB-001
---

# Task: Add graph_store config field and FalkorDB connection params

## Description

Add a `graph_store` configuration field to `GraphitiSettings` and `GraphitiConfig` that controls which graph database backend to use. Add FalkorDB-specific connection parameters alongside existing Neo4j ones. Keep existing `neo4j_*` field names as backwards-compatible aliases.

## Acceptance Criteria

- [ ] AC-001: `GraphitiSettings` has `graph_store: str = "neo4j"` field (valid: `"neo4j"`, `"falkordb"`)
- [ ] AC-002: `GraphitiSettings` has `falkordb_host: str = "localhost"` and `falkordb_port: int = 6379` fields
- [ ] AC-003: `GRAPH_STORE` env var overrides `graph_store` config field
- [ ] AC-004: `FALKORDB_HOST` and `FALKORDB_PORT` env vars override FalkorDB connection params
- [ ] AC-005: `GraphitiConfig` has matching fields propagated from settings
- [ ] AC-006: Existing `neo4j_*` fields, `NEO4J_*` env vars, and YAML config continue to work unchanged
- [ ] AC-007: `load_graphiti_config()` loads and validates all new fields
- [ ] AC-008: Tests for new config fields, env var overrides, and validation

## Files to Modify

- `guardkit/knowledge/config.py` — Add fields to `GraphitiSettings`, env var overrides to `load_graphiti_config()`
- `guardkit/knowledge/graphiti_client.py` — Add fields to `GraphitiConfig`

## Implementation Notes

- `graph_store` validation: must be one of `"neo4j"`, `"falkordb"` (raise `ValueError` otherwise)
- Keep `neo4j_uri`, `neo4j_user`, `neo4j_password` as-is — they're backend-agnostic config field names
- FalkorDB uses host/port (not URI) for connection — different from Neo4j's bolt:// URI pattern
- The `_try_lazy_init()` function must propagate `graph_store` to config
