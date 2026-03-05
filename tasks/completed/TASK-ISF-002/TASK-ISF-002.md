---
id: TASK-ISF-002
title: Revert rule main_content to content_preview in sync_rule_to_graphiti
status: completed
completed: 2026-03-04T00:00:00Z
priority: critical
complexity: 1
parent_review: TASK-REV-C043
feature_id: FEAT-ISF
wave: 1
implementation_mode: task-work
tags: [revert, graphiti, init, performance]
---

# TASK-ISF-002: Revert Rule Content to content_preview

## Problem

`sync_rule_to_graphiti()` was changed from sending `content_preview: body[:500]` to `main_content: chunk.content` (full ~2000 char chunks). This causes graphiti-core to extract far more entities and edges per episode, pushing rule episodes past the 180s timeout. Rules that completed in 60-130s with `content_preview` now timeout at 180s with `main_content`.

## Solution

Revert the rule body field from `main_content: chunk.content` back to `content_preview: chunk.content[:500]`.

The `content_preview` (500 chars) is sufficient for Graphiti's semantic search use case. Full rule text stays in the static `.claude/rules/` files and is loaded on-demand.

## Files Changed

- `guardkit/knowledge/template_sync.py:565` — Changed `"main_content": chunk.content` to `"content_preview": chunk.content[:500] if chunk.content else ""`
- `tests/knowledge/test_template_sync.py` — Updated 2 tests to assert `content_preview` key instead of `main_content`

## Acceptance Criteria

- [x] Rule body uses `content_preview` key (not `main_content`)
- [x] Content limited to 500 chars
- [x] Episode splitting infrastructure (`chunk.content`, `chunk_index`, `total_chunks`) remains intact
- [x] Existing tests pass (63 passed, 2 skipped)

## Testing

```bash
pytest tests/knowledge/test_template_sync.py -v
# 63 passed, 2 skipped
```
