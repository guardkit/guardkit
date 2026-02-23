---
id: TASK-GLI-005
title: Test seeding feature-spec v2 document via local vLLM inference
task_type: implementation
status: backlog
created: 2026-02-22T23:45:00Z
updated: 2026-02-22T23:45:00Z
priority: high
tags: [graphiti, vllm, testing, seeding]
complexity: 2
parent_review: TASK-REV-8B3A
feature_id: FEAT-GLI
wave: 3
implementation_mode: direct
dependencies: [TASK-GLI-001, TASK-GLI-003, TASK-GLI-004]
---

# Task: Test Seeding Feature-Spec v2 Document via Local vLLM Inference

## Description

End-to-end verification that the feature-spec v2 document can be successfully seeded into Graphiti using local vLLM inference on the GB10, fully bypassing OpenAI API.

## Context

- The feature-spec v2 document (70KB, 8,841 words, 92 headings) previously failed to seed due to OpenAI rate limiting
- Two consecutive attempts both failed with "Rate limit exceeded" (see `docs/reviews/feature-spec/graphiti_seed_2.md`)
- After TASK-GLI-001 through TASK-GLI-004, Graphiti should be configured to use vLLM on the GB10
- **IMPORTANT**: Existing FalkorDB data contains OpenAI text-embedding-3-small vectors (1024 dim). The new embedding model produces different-dimension vectors. All existing data must be cleared before reseeding to avoid mixed embedding spaces.

## Acceptance Criteria

### Pre-requisite: Clear existing FalkorDB data

The NAS (whitestocks) itself requires no changes — FalkorDB stays running as-is. But the **data inside** must be cleared because the embedding vectors are incompatible (OpenAI = 1024 dim vs nomic-embed-text = 768 dim).

- [ ] Preview existing data: `guardkit graphiti clear --dry-run`
- [ ] Clear all knowledge: `guardkit graphiti clear --confirm`
- [ ] Verify FalkorDB is empty: `guardkit graphiti clear --dry-run` (should show 0 groups)

### Verify vLLM infrastructure

- [ ] Verify `.guardkit/graphiti.yaml` is configured with vLLM provider settings
- [ ] Verify vLLM embedding instance is running on GB10 port 8001 (curl health check)
- [ ] Verify vLLM LLM instance is running on GB10 port 8000 (curl health check)

### Reseed and verify

- [ ] Reseed system knowledge: `guardkit graphiti seed`
- [ ] Run: `guardkit-py graphiti add-context docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md`
- [ ] Verify: episode creation succeeds (no rate limit errors)
- [ ] Verify: no "Episode creation returned None" errors
- [ ] Verify: no unawaited coroutine warnings (`extract_edges_for_chunk`)
- [ ] Verify: search the seeded content to confirm entity extraction quality
  - `guardkit graphiti search "feature-spec command"` returns relevant results
  - `guardkit graphiti search "BDD Gherkin"` returns relevant results
- [ ] Document: capture seed log to `docs/reviews/feature-spec/graphiti_seed_3.md`
- [ ] Document: note any content parsing warnings (expected: "Missing feature overview section")

## Success Metric

The seed command completes without rate limit errors and entities are searchable in Graphiti. This directly resolves the original failure documented in TASK-REV-8B3A.

## Key Files

- `docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md` — document to seed
- `docs/reviews/feature-spec/graphiti_seed_2.md` — previous failed seed log
- `.guardkit/graphiti.yaml` — config (should be updated by TASK-GLI-004)

## Reference

- Parent review: TASK-REV-8B3A
- Previous failure log: `docs/reviews/feature-spec/graphiti_seed_2.md`
