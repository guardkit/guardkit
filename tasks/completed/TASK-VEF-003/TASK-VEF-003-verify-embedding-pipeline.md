---
id: TASK-VEF-003
title: End-to-end verification of vLLM embedding + FalkorDB pipeline
status: completed
created: 2026-02-28T12:00:00Z
updated: 2026-03-01T00:00:00Z
completed: 2026-03-01T00:00:00Z
priority: high
tags: [vllm, embedding, falkordb, verification]
parent_review: TASK-CC3E
feature_id: FEAT-VEF
implementation_mode: manual
wave: 2
complexity: 2
depends_on:
  - TASK-VEF-001
  - TASK-VEF-002
completed_location: tasks/completed/TASK-VEF-003/
---

# Task: End-to-end verification of vLLM embedding + FalkorDB pipeline

## Description

Verify that all fixes from TASK-VEF-001 and TASK-VEF-002 work together on the Dell Pro Max GB10. This is a manual verification task to be run on the actual hardware.

## Parent Review

TASK-CC3E — Diagnose vLLM embedding GPU memory error and fix
Report: `.claude/reviews/TASK-CC3E-review-report.md`

## Verification Steps

### 1. Verify vLLM Embedding Server Starts

```bash
# Ensure LLM server on port 8000 is running first
./scripts/vllm-embed.sh

# Expected: Pre-flight check shows available memory
# Expected: Container starts successfully
# Expected: GPU util shows 0.03 (not 0.15)
```

### 2. Verify Model Name Resolution

```bash
# Check registered model names
curl http://localhost:8001/v1/models | jq '.data[].id'
# Expected: "nomic-ai/nomic-embed-text-v1.5" (with short name alias)

# Test with short name (from script output)
curl http://localhost:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "nomic-embed-text-v1.5", "input": "Hello world"}'
# Expected: 200 OK with embedding vector

# Test with full name
curl http://localhost:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "nomic-ai/nomic-embed-text-v1.5", "input": "Hello world"}'
# Expected: 200 OK with embedding vector
```

### 3. Verify FalkorDB Connection

```bash
# Check FalkorDB reachability via Tailscale
guardkit graphiti status --verbose
# Expected: Connected to FalkorDB at whitestocks:6379

# Test Graphiti with embedding
guardkit graphiti search "test query"
# Expected: No connection errors
```

### 4. Verify Full Pipeline

```bash
# Run a capture session that exercises embeddings + FalkorDB
guardkit graphiti capture --interactive --max-questions 1
# Expected: Successfully captures knowledge (embeddings generated via vLLM, stored in FalkorDB)
```

## Acceptance Criteria

- [x] vLLM embedding server starts alongside LLM server (no GPU memory error)
- [x] Embedding API responds to both short and full model names
- [x] FalkorDB connects via Tailscale to Synology NAS
- [x] Graphiti capture works end-to-end (embedding + storage)
- [x] Pre-flight GPU check displays correct memory information

## Infrastructure Required

- Dell Pro Max GB10 / DGX Spark with LLM server running on port 8000
- Synology NAS accessible via Tailscale at `whitestocks`
- FalkorDB running on NAS (port 6379)
