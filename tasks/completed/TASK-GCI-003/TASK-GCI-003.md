---
id: TASK-GCI-003
title: Align embedding dimensions between MCP and Python client
status: completed
created: 2026-03-18T00:00:00Z
updated: 2026-03-18T12:30:00Z
completed: 2026-03-18T12:30:00Z
priority: medium
tags: [graphiti, embeddings, configuration]
parent_review: TASK-REV-C166
feature_id: FEAT-GCI
implementation_mode: task-work
wave: 2
complexity: 3
depends_on:
  - TASK-GCI-001
previous_state: in_review
---

# Task: Align embedding dimensions between MCP and Python client

## Description

The MCP server config specifies `EMBEDDING_DIM: "1024"` and `dimensions: 1024`, but the Python client doesn't explicitly set dimensions and relies on the model default. The nomic-embed-text-v1.5 model supports multiple dimensions (768 default, up to 1024 with Matryoshka). If these differ, vector search across both access methods will produce incorrect results.

## Requirements

1. **Add `embedding_dimensions` to `.guardkit/graphiti.yaml` schema**
   - New optional field in `GraphitiConfig`
   - Default: `None` (use model default)
   - When set, pass to both Python client and MCP server config generation

2. **Ensure `--copy-graphiti` copies this field**
   - Already copies other embedding settings; add `embedding_dimensions`

3. **Validate dimension consistency during `guardkit init --with-mcp`**
   - If `.guardkit/graphiti.yaml` has `embedding_dimensions` set, ensure MCP server config matches
   - Warn if MCP server config uses different dimensions

4. **Determine actual dimension in use**
   - Check FalkorDB vector index to see what dimension was used when indices were created
   - Document the correct value for the current infrastructure

## Acceptance Criteria

- [x] `embedding_dimensions` field added to `GraphitiConfig` dataclass
- [x] `--copy-graphiti` includes `embedding_dimensions`
- [x] MCP server config generation uses matching dimensions
- [x] Dimension mismatch produces a clear warning during init
- [x] Documented which dimension value is correct for current infrastructure

## Implementation Notes

- The Python client's dimension pre-flight check is in `graphiti_client.py` lines 603-701
- The MCP server config is at `graphiti/mcp_server/config/config-guardkit.yaml`
- nomic-embed-text-v1.5 supports: 64, 128, 256, 512, 768 (default), 1024 dimensions

## Completion Summary

### Changes Made

- **`guardkit/knowledge/config.py`**: Added `embedding_dimensions: Optional[int] = None` to `GraphitiSettings` with validation, YAML loading, and `EMBEDDING_DIMENSIONS` env var support.
- **`guardkit/knowledge/graphiti_client.py`**: Added `embedding_dimensions: Optional[int] = None` to `GraphitiConfig`. `_do_embedding_dimension_check` now uses this explicit value when set, overriding `KNOWN_EMBEDDING_DIMS`.
- **`guardkit/cli/init.py`**: `generate_mcp_server_config` and `generate_mcp_json_entry` use `settings.embedding_dimensions` (fallback 1024). Added dimension mismatch warning during `--with-mcp` init. `GraphitiConfig` construction passes `embedding_dimensions`.
- **`guardkit/cli/graphiti.py`**: Both `GraphitiConfig` constructor calls now pass `embedding_dimensions`.
- **`.guardkit/graphiti.yaml`**: Added `embedding_dimensions: 1024` — documents that this FalkorDB was seeded with 1024-dim Matryoshka vectors.
- **`tests/cli/test_init_mcp.py`**: Updated `_make_settings` helper; added 5 new tests covering explicit dimension vs. default behaviour.

### Infrastructure Documentation

The current FalkorDB (whitestocks:6379) was seeded with **1024-dim vectors** using nomic-embed-text-v1.5 with Matryoshka enabled. The correct value for all clients is `embedding_dimensions: 1024`.

### Tests

All 38 tests in `test_init_mcp.py` pass. All 62 tests in `test_config.py` pass. All 16 tests in `test_graphiti_client_embedding_preflight.py` pass.
