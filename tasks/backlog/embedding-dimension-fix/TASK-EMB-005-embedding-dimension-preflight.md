---
id: TASK-EMB-005
title: Add embedding dimension pre-flight check during Graphiti initialization
status: backlog
created: 2026-03-09T00:00:00Z
priority: medium
tags: [graphiti, embedding, validation, defensive]
task_type: implementation
complexity: 5
parent_review: TASK-REV-D2B5
feature_id: FEAT-EMB
wave: 3
implementation_mode: task-work
dependencies: [TASK-EMB-001]
---

# Task: Add embedding dimension pre-flight check

## Description

When `GraphitiClient.initialize()` connects to FalkorDB, there's no check that the configured embedding model's output dimensions match the vector dimensions stored in the database. This means dimension mismatches fail silently at search time with cryptic FalkorDB errors.

Add a pre-flight check that:
1. Generates a test embedding using the configured provider
2. Queries FalkorDB for the vector index dimension
3. Compares and logs a clear warning/error if mismatched

## Acceptance Criteria

- [ ] After successful FalkorDB connection in `initialize()`, perform dimension check
- [ ] If stored vectors exist and dimensions don't match, log a clear ERROR:
  ```
  ERROR: Embedding dimension mismatch! Configured model produces N-dim vectors
  but FalkorDB index expects M-dim vectors. Search will fail.
  Check embedding_provider/embedding_model in .guardkit/graphiti.yaml
  ```
- [ ] If no stored vectors exist (fresh DB), skip check gracefully
- [ ] Check adds <2s to initialization time
- [ ] Check failure does NOT block initialization (warning only, graceful degradation)
- [ ] Tests cover: matching dims, mismatched dims, empty DB, embedder timeout

## Key Files

- `guardkit/knowledge/graphiti_client.py` — `initialize()` method, around line 731
- May need FalkorDB query to inspect vector index schema

## Implementation Notes

FalkorDB vector indices have a fixed dimension set at creation time. Query the index metadata to get the expected dimension, then compare with a test embedding. The `embedding_model` dimension should be deterministic for a given model name.

Alternative simpler approach: maintain a known-dimensions lookup table:
```python
KNOWN_EMBEDDING_DIMS = {
    "nomic-embed-text-v1.5": 768,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}
```
And compare at config load time without needing a test embedding call.
