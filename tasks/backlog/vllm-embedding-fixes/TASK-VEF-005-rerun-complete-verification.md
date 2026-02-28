---
id: TASK-VEF-005
title: Re-run complete verification of vLLM + FalkorDB pipeline
status: completed
created: 2026-02-28T15:00:00Z
updated: 2026-02-28T18:30:00Z
priority: high
tags: [vllm, embedding, falkordb, verification]
parent_review: TASK-REV-36CC
feature_id: FEAT-VEF
implementation_mode: manual
wave: 4
complexity: 2
depends_on:
  - TASK-VEF-004
---

# Task: Re-run complete verification of vLLM + FalkorDB pipeline

## Description

The initial verification (TASK-VEF-003) only captured steps 1-2. Steps 3-4 (FalkorDB connection and full pipeline) were not tested or their output was not captured. After TASK-VEF-004 fixes the served-model-name issue, re-run the complete 4-step verification.

## Verification Steps

Run all steps from TASK-VEF-003 and capture output to `docs/reviews/graphiti-local-embedding/verify_2.md`.

### 1. Verify vLLM Embedding Server (re-verify after fix)

```bash
./scripts/vllm-embed.sh

# Verify both model names work:
curl http://localhost:8001/v1/models | jq '.data[].id'
# Expected: Both "nomic-embed-text-v1.5" AND "nomic-ai/nomic-embed-text-v1.5"

curl http://localhost:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "nomic-embed-text-v1.5", "input": "Hello world"}'
# Expected: 200 OK

curl http://localhost:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "nomic-ai/nomic-embed-text-v1.5", "input": "Hello world"}'
# Expected: 200 OK (previously returned 404)
```

### 2. Verify FalkorDB Connection

```bash
guardkit graphiti status --verbose
# Expected: Connected to FalkorDB at whitestocks:6379

guardkit graphiti search "test query"
# Expected: No connection errors
```

### 3. Verify Full Pipeline

```bash
guardkit graphiti capture --interactive --max-questions 1
# Expected: Successfully captures knowledge
```

### 4. Verify graphiti.yaml embedding_model

```bash
cat .guardkit/graphiti.yaml | grep embedding_model
# Expected: embedding_model should match vLLM served model name
```

## Acceptance Criteria

- [x] Both short and full model names return 200 (TASK-VEF-004 fix verified)
- [x] No `(standard_in)` errors during server startup
- [x] FalkorDB connects via Tailscale to whitestocks:6379
- [x] `guardkit graphiti capture` works end-to-end
- [x] Complete output captured in `verify_2.md`

## Evidence

- Previous verification: `docs/reviews/graphiti-local-embedding/verify_1.md`
- Final verification: `docs/reviews/graphiti-local-embedding/verify_2.md`
- Review report: `.claude/reviews/TASK-REV-36CC-review-report.md`

## Observations

- `graphiti status` and `graphiti search` use OpenAI API embeddings, not local vLLM. The local embedding server is used by `add_episode` during capture. This may be intentional (search requires matching the embedding space of existing vectors) or a configuration gap worth investigating separately.
