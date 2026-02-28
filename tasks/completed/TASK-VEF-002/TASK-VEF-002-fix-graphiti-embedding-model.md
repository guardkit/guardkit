---
id: TASK-VEF-002
title: Fix graphiti.yaml embedding model name to match vLLM served model
status: completed
created: 2026-02-28T12:00:00Z
updated: 2026-02-28T13:05:00Z
completed: 2026-02-28T13:05:00Z
priority: medium
tags: [graphiti, embedding, config]
parent_review: TASK-CC3E
feature_id: FEAT-VEF
implementation_mode: direct
wave: 1
complexity: 1
previous_state: in_review
state_transition_reason: "All acceptance criteria verified, config change confirmed consistent with TASK-VEF-001"
completed_location: tasks/completed/TASK-VEF-002/
---

# Task: Fix graphiti.yaml embedding model name to match vLLM served model

## Description

The `.guardkit/graphiti.yaml` config specifies `embedding_model: text-embedding-3-small` (an OpenAI model name), but the embedding provider is `vllm` serving `nomic-ai/nomic-embed-text-v1.5`. If graphiti-core passes this model name in API calls, requests will fail.

## Parent Review

TASK-CC3E — Diagnose vLLM embedding GPU memory error and fix
Report: `.claude/reviews/TASK-CC3E-review-report.md`

## Changes Applied

Updated `.guardkit/graphiti.yaml` line 50:

```yaml
# Before
embedding_model: text-embedding-3-small

# After (matches --served-model-name from TASK-VEF-001)
embedding_model: nomic-embed-text-v1.5
```

Verified consistency: TASK-VEF-001 sets `--served-model-name $(basename "$MODEL")` which resolves to `nomic-embed-text-v1.5` for the nomic preset.

## Acceptance Criteria

- [x] `embedding_model` in `.guardkit/graphiti.yaml` matches the vLLM served model name
- [x] Model name is consistent with the `--served-model-name` set in TASK-VEF-001

## Files Modified

- `.guardkit/graphiti.yaml`
