# FEAT-falkordb-timeout-fixes

## Problem

`guardkit init fastapi-python` Step 2.5 (template content sync to Graphiti/FalkorDB) takes ~113 minutes and produces 64 query timeouts, 33 connection closures, and unreadable output filled with 768-dimensional vector dumps.

## Root Causes

1. **Upstream bug getzep/graphiti#1272**: `edge_fulltext_search` uses O(n×m) re-MATCH instead of O(n) node access, turning 2ms queries into 26-118s queries
2. **FalkorDB TIMEOUT=1000ms**: Server kills queries after 1 second — far too low
3. **Full markdown content synced**: Rule episodes include full file content, causing excessive entity extraction and query volume

## Solution

6 targeted fixes in 2 waves:

### Wave 1 — Root Cause Fixes (Critical)

| Task | What | Files |
|------|------|-------|
| [TASK-FIX-1136](TASK-FIX-1136-patch-edge-fulltext-search.md) | Monkey-patch O(n×m) → O(n) | `falkordb_workaround.py` |
| [TASK-FIX-fe67](TASK-FIX-fe67-raise-falkordb-timeout.md) | TIMEOUT 1000 → 30000ms | `docker-compose.falkordb.yml` |
| [TASK-FIX-6e46](TASK-FIX-6e46-remove-full-content-from-rule-sync.md) | Drop `full_content` from rules | `template_sync.py` |

### Wave 2 — Resilience & UX (High/Medium)

| Task | What | Files |
|------|------|-------|
| [TASK-FIX-d457](TASK-FIX-d457-fix-add-episode-return-check.md) | Check add_episode return value | `template_sync.py` |
| [TASK-FIX-72c1](TASK-FIX-72c1-suppress-vector-logging.md) | Suppress vector dump logging | `template_sync.py` |
| [TASK-FIX-143c](TASK-FIX-143c-add-episode-level-timeout.md) | 120s per-episode timeout | `graphiti_client.py` |

## Expected Impact

- Init time: **~120 min → ~8-10 min**
- Query timeouts: **64 → 0**
- Connection closures: **33 → 0**
- Vector dumps in output: **30 → 0**

## Key Finding: Rules Group Not Used at Runtime

The `rules` group in Graphiti is **never queried** by Player/Coach autobuild agents. Confirmed via code trace through `job_context_retriever.py`. Removing `full_content` from rule episodes is safe — actual rule content is served via `.claude/rules/*.md` files copied during Step 1 of init.

## Review Report

Full analysis with C4 diagrams: [.claude/reviews/TASK-REV-1F78-review-report.md](../../../.claude/reviews/TASK-REV-1F78-review-report.md)
