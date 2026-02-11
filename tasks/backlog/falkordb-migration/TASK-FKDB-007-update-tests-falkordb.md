---
id: TASK-FKDB-007
title: Update tests for FalkorDB compatibility
status: backlog
created: 2026-02-11T17:00:00Z
priority: medium
tags: [falkordb, testing, migration]
parent_review: TASK-REV-38BC
feature_id: FEAT-FKDB-001
implementation_mode: task-work
wave: 3
complexity: 5
depends_on:
  - TASK-FKDB-005
  - TASK-FKDB-006
---

# Task: Update tests for FalkorDB compatibility

## Description

Update test fixtures, assertions, and integration tests to work with FalkorDB. Most unit tests use mocks and need no changes. Focus on tests that reference Neo4j-specific defaults or use real connections.

## Acceptance Criteria

- [ ] AC-001: `tests/conftest.py` fixtures updated with FalkorDB-aware defaults
- [ ] AC-002: Config tests verify new `graph_store`, `falkordb_host`, `falkordb_port` fields
- [ ] AC-003: Integration tests that use real connections parameterized for both backends
- [ ] AC-004: E2E tests work with FalkorDB Docker container
- [ ] AC-005: Full test suite passes with `graph_store=neo4j` (no regressions)
- [ ] AC-006: Key test paths verified with `graph_store=falkordb` (mocked or real)
- [ ] AC-007: Re-seed and verify knowledge graph with FalkorDB backend

## Files to Modify

- `tests/conftest.py` — Fixture defaults
- `tests/knowledge/test_config.py` — New field validation
- `tests/knowledge/test_graphiti_client.py` — Default URI assertions
- `tests/knowledge/test_graphiti_client_factory.py` — Constructor patterns
- `tests/knowledge/test_graphiti_client_clear.py` — Updated query mocks (from TASK-FKDB-006)
- Integration and E2E test files as needed

## Implementation Notes

**68 test files** reference Neo4j/Graphiti. Breakdown by impact:
- ~45 use mocks → NO changes needed
- ~12 need config assertion updates (default values)
- ~8 need connection config updates
- ~3 E2E tests need real FalkorDB

Priority: Ensure zero regressions with Neo4j config first, then validate FalkorDB paths.
