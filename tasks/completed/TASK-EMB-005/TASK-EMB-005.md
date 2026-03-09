---
id: TASK-EMB-005
title: Add embedding dimension pre-flight check during Graphiti initialization
status: completed
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
completed: 2026-03-09T00:00:00Z
priority: medium
tags: [graphiti, embedding, validation, defensive]
task_type: implementation
complexity: 5
parent_review: TASK-REV-D2B5
feature_id: FEAT-EMB
wave: 3
implementation_mode: task-work
dependencies: [TASK-EMB-001]
previous_state: in_review
completed_location: tasks/completed/TASK-EMB-005/
organized_files: [TASK-EMB-005.md]
---

# Task: Add embedding dimension pre-flight check

## Description

When `GraphitiClient.initialize()` connects to FalkorDB, there's no check that the configured embedding model's output dimensions match the vector dimensions stored in the database. This means dimension mismatches fail silently at search time with cryptic FalkorDB errors.

Add a pre-flight check that:
1. Generates a test embedding using the configured provider
2. Queries FalkorDB for the vector index dimension
3. Compares and logs a clear warning/error if mismatched

## Acceptance Criteria

- [x] After successful FalkorDB connection in `initialize()`, perform dimension check
- [x] If stored vectors exist and dimensions don't match, log a clear ERROR:
  ```
  ERROR: Embedding dimension mismatch! Configured model produces N-dim vectors
  but FalkorDB index expects M-dim vectors. Search will fail.
  Check embedding_provider/embedding_model in .guardkit/graphiti.yaml
  ```
- [x] If no stored vectors exist (fresh DB), skip check gracefully
- [x] Check adds <2s to initialization time
- [x] Check failure does NOT block initialization (warning only, graceful degradation)
- [x] Tests cover: matching dims, mismatched dims, empty DB, embedder timeout

## Implementation Summary

### Files Changed
- `guardkit/knowledge/graphiti_client.py` — added `KNOWN_EMBEDDING_DIMS` constant and three new methods
- `tests/knowledge/test_graphiti_client_embedding_preflight.py` — new test file (16 tests, all passing)

### Approach
Used the lookup-table approach (not live embedding call) to keep the check fast and deterministic:
- `KNOWN_EMBEDDING_DIMS`: 18 common models (OpenAI, nomic, BGE, miniLM, mxbai, snowflake, BAAI)
- `_check_embedding_dimensions()`: FalkorDB-only guard + 1.5s `asyncio.wait_for` timeout
- `_do_embedding_dimension_check()`: lookup → query → compare → log ERROR if mismatch
- `_query_stored_embedding_dim()`: `CALL db.indexes()` via graphiti driver, returns None on any failure

### Quality Gates
- All 16 new tests pass
- 0 regressions in existing knowledge test suite (1884 passed, 12 pre-existing failures unrelated)
- All 6 acceptance criteria satisfied
