---
id: TASK-REV-661E
title: Analyse Graphiti seed failures for feature-spec document
task_type: review
status: review_complete
created: 2026-02-22T18:00:00Z
updated: 2026-02-22T22:00:00Z
priority: high
tags: [graphiti, falkordb, seeding, debugging]
complexity: 0
review_results:
  mode: decision
  depth: standard
  findings_count: 4
  recommendations_count: 6
  report_path: docs/reviews/feature-spec/TASK-REV-661E-review-report.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse Graphiti seed failures for feature-spec document

## Description

Analyse the failures encountered when seeding the feature-spec v2 document (`docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md`) to Graphiti. The seed log is captured in `docs/reviews/feature-spec/graphiti_seed_1.md`.

## Context

During the FEAT-1253 (/feature-spec command) implementation, the 3 ADR documents seeded successfully but the main feature spec document failed with multiple errors.

## Observed Failures

### 1. RediSearch Fulltext Query Syntax Errors
Three separate `FalkorDB query` errors with pattern:
```
RediSearch: Syntax error at offset N near KEYWORD
```

The failing query is a fulltext search on the `Entity` index:
```cypher
CALL db.idx.fulltext.queryNodes('Entity', $query) YIELD node AS n, score
WHERE n.group_id IN $group_ids
```

The problematic query values contain special characters that RediSearch cannot parse:
- `(Slash | command | \` | claude/commands/feature | spec | md\`)`  -- backticks and forward slashes
- `(CLI | flags | \` | from\` | \` | output\` | ...)` -- escaped backticks throughout
- `(Cross | cutting | tags | \` | smoke\` | \` | regression\`)` -- backticks

### 2. Episode Creation Failure
```
Episode creation returned None (possible silent failure)
```

### 3. Coroutine Warning
```
RuntimeWarning: coroutine 'search' was never awaited
```

### 4. Content Parsing Warnings
```
Warning: Missing feature overview section
Warning: No phases found in feature spec
```

## Acceptance Criteria

- [x] Root cause identified for RediSearch syntax errors (backtick/special char escaping in fulltext queries)
  - **Upstream**: `FalkorDriver.sanitize()` in graphiti-core v0.26.3 omits backticks, forward slashes, pipes, backslashes from its character stripping list
  - **GuardKit gap**: `build_fulltext_query_fixed()` delegates text sanitization to the original without adding its own layer
- [x] Root cause identified for episode creation returning None
  - **Not a separate bug**: Direct consequence of RediSearch errors — exception propagates from `add_episode()` through `_create_episode()` which catches and returns None
- [x] Root cause identified for unawaited coroutine warning
  - **Upstream**: Exception during `add_episode()` leaks coroutines created by `semaphore_gather` in the `search` method's decorator wrapper
- [x] Root cause identified for missing section parsing (feature overview, phases)
  - **GuardKit**: `FeatureSpecParser` expects `## Feature Overview` and `### Phase N: Name (Xh)` headers; the v2 doc uses `## 1. Problem Statement` and `### Task N:` headers instead
- [x] Determine if these are upstream graphiti-core issues vs GuardKit workaround gaps
  - 3 upstream (sanitize gap, coroutine leak), 1 GuardKit (parser), 1 workaround gap
- [x] Recommendations documented for fixes (with task references if implementation needed)
  - See review report: `docs/reviews/feature-spec/TASK-REV-661E-review-report.md`

## Key Files to Investigate

- `guardkit/knowledge/graphiti_client.py` -- episode creation and error handling
- `guardkit/knowledge/falkordb_workaround.py` -- FalkorDB patches (already patches `build_fulltext_query`)
- `guardkit/knowledge/add_context.py` -- document parsing and episode chunking
- `graphiti-core` source -- `driver/falkordb_driver.py` for query construction

## Reference

- Seed log: `docs/reviews/feature-spec/graphiti_seed_1.md`
- Feature spec: `docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md`
- Related: FEAT-1253 (/feature-spec command v1)
