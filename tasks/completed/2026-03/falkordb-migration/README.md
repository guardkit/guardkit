# FEAT-FKDB-001: FalkorDB Migration

## Problem Statement

GuardKit's knowledge graph integration currently uses Neo4j as the graph database backend via graphiti-core. FalkorDB offers a lighter-weight, Redis-based alternative that graphiti-core already supports natively via its `FalkorDriver`. This migration replaces the Neo4j backend with FalkorDB while preserving all existing functionality.

## Solution Approach

**Incremental migration** — add FalkorDB support alongside Neo4j via a `graph_store` config field, then switch the default. The architecture already has 95% driver-agnostic code (verified in TASK-REV-38BC deep review).

**Critical path**: Refactor 3 raw Cypher queries in `graphiti_client.py` from Neo4j session API (`result.data()`, `result.single()`) to driver-agnostic `execute_query()` + tuple unpacking.

## Key Findings (from TASK-REV-38BC)

- Zero direct Neo4j imports in application code
- 95% of code needs zero changes (all uses graphiti-core API)
- 3 raw Cypher queries need refactoring (CRITICAL — `FalkorDriverSession.run()` returns `None`)
- `execute_query()` returns compatible tuples from both drivers (verified)
- Per-thread FalkorDriver required (existing factory pattern handles this)
- No FalkorDB tests in graphiti-core — validation required first
- `falkordb` Python package not installed — needs adding

## Subtask Summary

| Task | Title | Wave | Mode | Priority |
|------|-------|------|------|----------|
| TASK-FKDB-001 | Validate FalkorDB + graphiti-core end-to-end | 0 | direct | P0 |
| TASK-FKDB-002 | Add graph_store config + FalkorDB connection params | 1 | task-work | P1 |
| TASK-FKDB-003 | Add falkordb optional dependency | 1 | direct | P1 |
| TASK-FKDB-004 | FalkorDB Docker Compose | 1 | direct | P1 |
| TASK-FKDB-005 | Conditional driver creation (GraphitiClient + Factory) | 2 | task-work | P0 |
| TASK-FKDB-006 | Refactor 3 raw Cypher queries to execute_query() | 2 | task-work | P0 |
| TASK-FKDB-007 | Update tests for FalkorDB compatibility | 3 | task-work | P1 |
| TASK-FKDB-008 | Cleanup, docs update, and ADR-003 | 3 | direct | P2 |

## Review Provenance

- **Parent review**: TASK-REV-38BC
- **Review report**: `.claude/reviews/TASK-REV-38BC-review-report.md`
- **Review depth**: Deep architectural (with revision pass)
