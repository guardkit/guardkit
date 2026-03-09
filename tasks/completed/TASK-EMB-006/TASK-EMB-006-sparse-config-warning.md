---
id: TASK-EMB-006
title: Log warning when sparse graphiti.yaml uses FalkorDB with default embedding provider
status: completed
created: 2026-03-09T00:00:00Z
completed: 2026-03-09T00:00:00Z
priority: medium
tags: [graphiti, config, validation, ux]
task_type: implementation
complexity: 3
parent_review: TASK-REV-D2B5
feature_id: FEAT-EMB
wave: 3
implementation_mode: task-work
dependencies: []
completed_location: tasks/completed/TASK-EMB-006/
---

# Task: Log warning for sparse config + FalkorDB combination

## Description

When `load_graphiti_config()` reads a yaml that has `enabled: true` but is missing `embedding_provider` (using the default `openai`), AND the resolved `graph_store` is `falkordb`, emit a warning. This catches the exact scenario that caused the dimension mismatch: sparse per-project config connecting to a shared FalkorDB that was seeded with a different embedding model.

## Acceptance Criteria

- [x] Warning emitted when: `enabled=true` AND `graph_store=falkordb` AND `embedding_provider` was not explicitly set (still at default `openai`)
- [x] Warning message is clear and actionable:
  ```
  WARNING: Graphiti enabled with FalkorDB but embedding_provider not configured
  (defaulting to 'openai'). If this FalkorDB was seeded with a different
  embedding provider, search will fail with dimension mismatch.
  Set embedding_provider in .guardkit/graphiti.yaml
  ```
- [x] Warning NOT emitted when embedding_provider is explicitly set in yaml or env
- [x] Warning NOT emitted when graph_store is neo4j (default scenario, less likely shared)
- [x] Tests cover: sparse yaml + falkordb → warning, complete yaml → no warning, neo4j → no warning

## Key Files

- `guardkit/knowledge/config.py` — `load_graphiti_config()`, around line 458

## Implementation Notes

Track whether `embedding_provider` came from yaml/env or from default. One approach: set a flag `embedding_provider_explicit = False`, flip to `True` if found in yaml data or env vars. After building the settings, check the flag.

## Completion Summary

Implemented `embedding_provider_explicit` flag in `load_graphiti_config()`:
- Flag starts `False`; flipped to `True` when key found in YAML data or `EMBEDDING_PROVIDER` env var applied
- Warning emitted post-env-overrides when `enabled=True`, `graph_store=falkordb`, and flag still `False`
- 5 new tests added to `tests/knowledge/test_config.py::TestSparseConfigFalkorDBWarning`
- All 62 tests in the config test suite pass
