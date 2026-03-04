---
id: TASK-REV-1F78
title: Review init project output timeout errors
status: review_complete
task_type: review
created: 2026-03-03T00:00:00Z
updated: 2026-03-04T00:00:00Z
priority: high
tags: [graphiti, falkordb, timeout, init, template-sync, performance]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review init project output timeout errors

## Description

Analyse the `guardkit init fastapi-python` output captured in `docs/reviews/reduce-static-markdown/init_project_3.md` to understand the extensive FalkorDB query timeout errors occurring during Step 2.5 (template content sync to Graphiti).

## Source File

`docs/reviews/reduce-static-markdown/init_project_3.md` (2116 lines, ~325KB)

## Key Observations for Review

### 1. Timeout Errors in Template Sync (Step 2.5) — 64 timeouts
- 64 `ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out` errors
- All timeouts occur on `CALL db.idx.fulltext.queryRelationships('RELATES_TO', ...)` queries
- Timeouts happen during rule syncing (code-style, testing, crud, models, pydantic-constraints, routing, schemas, dependencies, etc.)
- Retry mechanism fires (attempts 1/3, 2/3, 3/3) but subsequent retries also timeout
- 5 episodes failed entirely: `WARNING:guarditi_client:Episode creation failed: Query timed out` (lines 354, 516, 931, 1079, 1299)

### 2. Connection Closed by Server — 33 occurrences (NEW)
- 33 `ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.` errors
- Appears later in the run (around lines 2052-2099), suggesting FalkorDB server becomes overwhelmed
- Occurs during the final rules being synced (dependencies, schemas, routing, fastapi, database)
- Indicates server-side resource exhaustion, not just query complexity

### 3. Vector Search Queries Dumped to Output — 30 occurrences (NEW)
- 30 `search_vector` entries containing full embedding vectors (768-dimensional float arrays) dumped to console
- Each vector dump is hundreds of characters, bloating the output to 325KB
- Vectors are being logged as part of failed query parameters — should never be in user-visible output

### 4. Query Pattern Issues
- Fulltext queries use very long pipe-separated keyword lists (e.g., `(Python | Code | Style | Naming | Conventions | rule | specifies | Pydantic | schemas | use | PascalCase | type | suffix)`)
- Queries pass `edge_uuids` filters that are sometimes empty arrays `[]`
- All queries target `group_ids: ['rules']`
- Despite timeouts, some episodes still report as "Completed" with very long durations (96-153 seconds)
- 16 rules synced successfully out of an unknown total (some may have silently failed)

### 5. Performance Concerns
- Step 2 (project knowledge seeding): 401s total for 8 episodes (avg ~50s each)
- Step 2.5 (template sync): Individual episodes taking 96-153 seconds
- Total init time is extremely high for what should be a quick setup operation
- Init did eventually complete ("GuardKit initialized successfully!") despite the errors

### 6. Warnings During Seeding (Step 2)
- `LLM returned invalid duplicate_facts idx values` warnings throughout
- `Target index -1 out of bounds for chunk of size 15` warnings in edge operations
- These may indicate data integrity issues in the graph

### 7. Unawaited Coroutine Warnings (NEW)
- 5 `RuntimeWarning: coroutine '...' was never awaited` at end of run:
  - `search`, `edge_search`, `node_search`, `episode_search`, `community_search`
- Suggests async cleanup issue — Graphiti search coroutines created but never executed
- May indicate that some search/dedup operations were skipped entirely

## Error Summary

| Error Type | Count | Severity |
|------------|-------|----------|
| Query timed out | 64 | High |
| Connection closed by server | 33 | Critical |
| search_vector dumps in output | 30 | Medium (UX) |
| Episode creation failed | 5 | High |
| Unawaited coroutines | 5 | Medium |
| Invalid duplicate_facts idx | ~30+ | Low (upstream) |
| Index out of bounds | ~15 | Low (upstream) |

## Review Questions

1. **Root cause**: Are timeouts caused by FalkorDB query complexity, index issues, data volume, or server resource limits?
2. **Server exhaustion**: Why does FalkorDB close connections mid-run? Is it an OOM or thread exhaustion issue?
3. **Query optimisation**: Can the fulltext relationship queries be simplified or batched differently?
4. **Retry strategy**: Is the current 3-attempt retry with 2s/4s backoff appropriate, or should it fail fast?
5. **Content reduction**: Would reducing the static markdown content being synced (the "reduce-static-markdown" initiative) eliminate these timeouts?
6. **Edge case handling**: Are the `edge_uuids: []` empty array queries necessary, or should they be skipped?
7. **Vector logging**: Why are 768-dim embedding vectors being logged to stderr? Can this be suppressed?
8. **Async cleanup**: What causes the unawaited coroutine warnings and are search operations being silently dropped?
9. **Data integrity**: Are the 5 failed episodes causing incomplete knowledge graphs that affect downstream usage?
10. **Init UX impact**: What is the acceptable total time for `guardkit init`? Current time is poor UX despite eventual success.

## Acceptance Criteria

- [ ] Root cause of FalkorDB query timeouts identified
- [ ] Root cause of "Connection closed by server" errors identified
- [ ] Relationship between markdown content volume and timeout frequency documented
- [ ] Impact of 5 failed episodes on knowledge graph completeness assessed
- [ ] Unawaited coroutine warnings root cause identified
- [ ] Recommendations for timeout mitigation provided
- [ ] Priority ordering of fixes established
- [ ] Connection to reduce-static-markdown initiative clarified

## Implementation Notes

This is a review/analysis task. Use `/task-review TASK-REV-1F78` to execute the review.
