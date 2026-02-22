---
id: TASK-REV-8B3A
title: Analyse Graphiti seed rate limit failures and evaluate local embeddings
task_type: review
status: review_complete
created: 2026-02-22T23:00:00Z
updated: 2026-02-22T23:30:00Z
priority: high
tags: [graphiti, openai, rate-limiting, embeddings, falkordb, infrastructure]
complexity: 5
review_results:
  mode: decision
  depth: standard
  score: null
  findings_count: 4
  recommendations_count: 6
  decision: implement_local_inference
  report_path: .claude/reviews/TASK-REV-8B3A-review-report.md
  completed_at: 2026-02-22T23:30:00Z
  implementation_feature: FEAT-GLI
  implementation_path: tasks/backlog/graphiti-local-inference/
  subtask_count: 5
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse Graphiti seed rate limit failures and evaluate local embeddings

## Description

After fixing the RediSearch syntax errors (TASK-REV-661E), the feature-spec document still fails to seed — now due to OpenAI API rate limiting. Two consecutive attempts both failed with `"Rate limit exceeded. Please try again later."` after multiple retry cycles. The seed log is captured in `docs/reviews/feature-spec/graphiti_seed_2.md`.

This review should also evaluate whether to move the embeddings workload to the Dell ProMax GB10 using a local embedding model, eliminating the OpenAI rate limit dependency entirely.

## Context

- TASK-REV-661E fixed the RediSearch backtick/slash sanitization gap — those errors are **resolved** (confirmed: no RediSearch errors in seed_2 log)
- The new failure is entirely OpenAI rate limiting on the `/responses` endpoint
- graphiti-core uses OpenAI embeddings internally for entity extraction and search during `add_episode`
- The feature-spec v2 document is large (~50 sections, rich markdown) which likely generates many embedding requests in a single `add_episode` call
- The Dell ProMax GB10 is available infrastructure with GPU capacity for local model inference

## Observed Failures

### 1. OpenAI Rate Limit (Both Attempts)

```
INFO:openai._base_client:Retrying request to /responses in 0.392428 seconds
INFO:openai._base_client:Retrying request to /responses in 0.949371 seconds
... (5-8 retries per attempt)
WARNING:guardkit.knowledge.graphiti_client:Episode creation request failed: Rate limit exceeded. Please try again later.
```

### 2. Episode Creation Failure (Consequence of #1)

```
Error: Episode creation returned None (possible silent failure)
```

### 3. Unawaited Coroutine (Different from TASK-REV-661E)

```
RuntimeWarning: coroutine 'extract_edges.<locals>.extract_edges_for_chunk' was never awaited
```

Note: This is a *different* coroutine leak than TASK-REV-661E (which was `search`). This is `extract_edges_for_chunk`, suggesting the rate limit interrupts during the edge extraction phase of `add_episode`.

### 4. Content Parsing Warnings (Known — TASK-REV-661E Finding 4)

```
Warning: Missing feature overview section
Warning: No phases found in feature spec
```

These are the same FeatureSpecParser structure warnings from TASK-REV-661E — known and low priority.

## Acceptance Criteria

- [ ] Root cause confirmed for OpenAI rate limit during graphiti seeding
- [ ] Determine which graphiti-core operations trigger the most embedding requests (entity extraction vs search vs edge resolution)
- [ ] Evaluate feasibility of local embeddings on Dell ProMax GB10 (model options, graphiti-core compatibility, performance)
- [ ] Evaluate alternative mitigations (rate limit backoff, chunking strategy, OpenAI tier upgrade, batch API)
- [ ] Recommendation documented: local embeddings vs OpenAI mitigations vs hybrid approach
- [ ] If local embeddings recommended: outline implementation plan (model selection, deployment, graphiti-core integration)

## Key Files to Investigate

- `guardkit/knowledge/graphiti_client.py` — episode creation, OpenAI dependency path
- `graphiti-core` source — `graphiti.py:add_episode()` for embedding call sites
- `graphiti-core` source — `embedder/openai.py` for embedding client configuration
- `graphiti-core` source — `nodes.py` / `edges.py` for entity extraction embedding usage
- `.guardkit/graphiti.yaml` — current Graphiti configuration

## Infrastructure Context

- **Dell ProMax GB10**: Available GPU server, capacity for local model inference
- **Current setup**: graphiti-core → OpenAI API for embeddings (text-embedding-3-small or similar)
- **graphiti-core embedder interface**: May support custom embedder implementations (needs investigation)

## Reference

- Seed log: `docs/reviews/feature-spec/graphiti_seed_2.md`
- Previous review: TASK-REV-661E (RediSearch syntax errors — resolved)
- Feature spec: `docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md`
- Related: FEAT-1253 (/feature-spec command v1)
