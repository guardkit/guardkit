---
id: TASK-FIX-8f75
title: Split large episodes into smaller chunks to avoid timeout scaling
status: completed
task_type: implementation
created: 2026-03-04T00:00:00Z
updated: 2026-03-04T00:00:00Z
completed: 2026-03-04T00:00:00Z
priority: medium
tags: [graphiti, falkordb, timeout, init, performance, architecture]
complexity: 4
parent_review: TASK-REV-BAC1
feature_id: FEAT-init-graphiti-remaining-fixes
completed_location: tasks/completed/TASK-FIX-8f75/
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-04T00:00:00Z
---

# Task: Split large episodes into smaller chunks to avoid timeout scaling

## Description

Implement content-aware episode splitting so that large episodes (project_architecture, complex rules like crud/schemas) are split into smaller sub-episodes before being sent to graphiti-core.

## Root Cause

The graphiti-core `add_episode` pipeline's Phase 4 (edge resolution) is O(extracted_edges × graph_size). Large episodes with rich content extract 20-50 edges, each requiring a DB lookup + vector search + LLM dedup call (~5-8s per edge). Splitting episodes into smaller chunks reduces extracted edges per episode, keeping Phase 4 fast regardless of graph size.

## Approach

1. Define `MAX_EPISODE_CHARS = 2000` threshold for splitting
2. Before calling `client.add_episode()`, check content length
3. If over threshold, split at markdown section boundaries (`## ` headings)
4. Seed each chunk as a separate episode with chunk metadata (chunk_index, total_chunks)
5. Apply to both `project_seeding.py` and `template_sync.py` (rule syncing)

## Files to Modify

- `guardkit/knowledge/project_seeding.py` — `seed_project_overview()` loop
- `guardkit/knowledge/template_sync.py` — `sync_rule_to_graphiti()` content_preview

## Expected Impact

- All episodes complete within 120-180s regardless of graph size
- Eliminates the need for indefinite timeout increases
- More episodes total, but each is faster and more reliable
- Trade-off: slightly more total LLM calls

## Acceptance Criteria

- [x] Episode splitting function implemented with configurable threshold
- [x] Splits at markdown section boundaries (preserves readability)
- [x] Chunk metadata included (chunk_index, total_chunks)
- [x] Applied to project_overview and rule syncing paths
- [x] Existing tests updated and pass
- [x] Integration test: large CLAUDE.md produces multiple sub-episodes
