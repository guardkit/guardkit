---
id: TASK-REV-D2B5
title: Investigate Graphiti embedding dimension mismatch (768 vs 1024)
status: review_complete
review_results:
  mode: root-cause-analysis
  depth: standard
  findings_count: 4
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-D2B5-review-report.md
  completed_at: 2026-03-09T00:00:00Z
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
priority: high
tags: [graphiti, embedding, vllm, dimension-mismatch, gb10]
task_type: review
complexity: 5
---

# Task: Investigate Graphiti embedding dimension mismatch (768 vs 1024)

## Description

Graphiti is reporting a vector dimension mismatch error during embedding lookups. The error is:

```
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Vector dimension mismatch, expected 768 but got 1024
WARNING:guardkit.knowledge.graphiti_client:Search request failed: Vector dimension mismatch, expected 768 but got 1024
```

### Root Cause Hypothesis

Embeddings are being **written** using the Dell Pro Max GB10 local vLLM instance (768-dimensional vectors via `http://promaxgb10-41b1:8001/v1/embeddings`), but **lookups/searches** are falling back to the OpenAI API (`https://api.openai.com/v1/embeddings`) which produces 1024-dimensional vectors (text-embedding-3-small default).

The system was migrated from OpenAI to local vLLM to avoid rate limits, but the embedding provider configuration for search/lookup operations may not have been updated consistently across all codepaths.

### Evidence

1. **Seeding succeeds** - `clear_graphiti_and_seed.md` shows successful embedding writes via `http://promaxgb10-41b1:8001/v1/embeddings`
2. **AutoBuild lookup fails** - `anthropic_feat-2AAA.md_run_1.md` shows lookups going to `https://api.openai.com/v1/embeddings` followed by dimension mismatch errors (expected 768, got 1024)
3. **Previous feature succeeded** - `anthropic_feat-001.md` completed successfully (likely before the vLLM migration, or with consistent embedding provider)

### Key Files to Investigate

- `guardkit/knowledge/config.py` - Embedding provider configuration (defaults to `openai`)
- `guardkit/knowledge/graphiti_client.py` - Client initialisation and embedding provider routing
- `guardkit/knowledge/template_sync.py` - Template sync embedding usage
- Environment variables: `EMBEDDING_PROVIDER`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`
- AutoBuild environment setup - how env vars are passed to player/coach subprocesses

## Acceptance Criteria

- [ ] Confirm root cause: identify exactly where lookup embeddings diverge from write embeddings
- [ ] Identify all codepaths that create embedding requests (write vs search)
- [ ] Determine if the issue is environment config (missing env vars in autobuild context) or code logic
- [ ] Propose fix: ensure consistent embedding provider for both write and search operations
- [ ] Verify the Dell GB10 vLLM model's embedding dimension (expected: 768)
- [ ] Check if OpenAI text-embedding-3-small can be configured to output 768 dimensions (as a fallback option)

## Context References

- Seeding log (successful writes): `docs/reviews/graphiti-local-embedding/clear_graphiti_and_seed.md`
- Failed autobuild run: `~/Projects/appmilla_github/youtube-transcript-mcp/docs/reviews/autobuild/anthropic_feat-2AAA.md_run_1.md`
- Successful prior run: `~/Projects/appmilla_github/youtube-transcript-mcp/docs/reviews/autobuild/anthropic_feat-001.md`

## Implementation Notes

The fix likely involves one or more of:
1. Ensuring `EMBEDDING_PROVIDER=vllm` and `EMBEDDING_BASE_URL=http://promaxgb10-41b1:8001/v1` are propagated to all autobuild subprocesses
2. Checking that `graphiti_client.py` uses the configured embedding provider for search, not just for writes
3. Verifying the autobuild CLI bootstraps the correct embedding environment

## Test Execution Log
[Automatically populated by /task-work]
