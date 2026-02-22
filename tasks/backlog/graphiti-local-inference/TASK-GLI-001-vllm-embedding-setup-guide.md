---
id: TASK-GLI-001
title: GB10 vLLM setup guide — embedding model instance with optimal config
task_type: implementation
status: backlog
created: 2026-02-22T23:45:00Z
updated: 2026-02-22T23:45:00Z
priority: high
tags: [vllm, embeddings, gb10, infrastructure, graphiti]
complexity: 4
parent_review: TASK-REV-8B3A
feature_id: FEAT-GLI
wave: 1
implementation_mode: task-work
dependencies: []
---

# Task: GB10 vLLM Setup Guide — Embedding Model Instance with Optimal Config

## Description

Create a detailed setup guide for deploying a vLLM embedding model instance on the Dell ProMax GB10, optimised for Graphiti seeding workloads. The guide should cover model selection, vLLM configuration, systemd service setup, and verification.

This is the foundational infrastructure task — all other subtasks depend on the embedding endpoint being available.

## Context

- Dell ProMax GB10 hostname: `promaxgb10-41b1` (Tailscale IP: 100.84.90.91)
- GB10 specs: NVIDIA Blackwell GPU, 128GB unified memory, DGX OS (Ubuntu 24.04 ARM64)
- vLLM is the designated inference runtime (TASK-REV-55C3 for AutoBuild)
- AutoBuild LLM planned on port 8000; embedding model on port 8001
- graphiti-core fires ~215 embedding API calls per `add_episode()` at `SEMAPHORE_LIMIT=20` concurrency
- Continuous batching is the key advantage for this workload

## Acceptance Criteria

- [ ] Document recommends primary embedding model with rationale (nomic-embed-text-v1.5 or nvidia/llama-nemotron-embed-1b-v2)
- [ ] Benchmark both candidate models on GB10 — report throughput (req/s) and latency (p50/p99) at concurrency 20
- [ ] Document optimal vLLM serve flags for GB10 Blackwell architecture (sm_121)
  - `--task embed`
  - `--dtype` (auto vs bfloat16 vs float16)
  - `--max-model-len` (match graphiti-core's max input)
  - `--gpu-memory-utilization` (leave headroom for LLM instance on port 8000)
  - Any GB10-specific flags (FlashInfer, tensor parallel, etc.)
- [ ] Document systemd service unit for auto-start on boot
- [ ] Document health check / readiness probe (curl to /v1/models)
- [ ] Document firewall/Tailscale access for port 8001
- [ ] Test: verify `/v1/embeddings` endpoint returns correct dimension vectors
- [ ] Test: verify embedding quality — seed a small test document via graphiti-core and confirm entity extraction works

## Model Selection Guidance

### Primary: nomic-embed-text-v1.5 (137M params)
- Proven quality parity with OpenAI text-embedding-3-small (MTEB 62.39 vs 62.26)
- Negligible memory footprint (~274MB in fp16)
- Supported in vLLM via `--task embed`
- 8192 token context window

### Alternative: nvidia/llama-nemotron-embed-1b-v2 (1B params)
- Purpose-built for NVIDIA hardware
- Higher quality (multilingual, 8192 tokens, Matryoshka embeddings)
- ~2GB in fp16, still trivial on 128GB
- Has DGX Spark community track record
- Requires `--runner pooling` and `--pooler-config '{"pooling_type": "MEAN"}'`

### vLLM Serve Commands (starting point)

```bash
# Option A: nomic-embed-text-v1.5
vllm serve nomic-ai/nomic-embed-text-v1.5 \
  --host 0.0.0.0 \
  --port 8001 \
  --task embed \
  --dtype auto \
  --gpu-memory-utilization 0.15

# Option B: nvidia/llama-nemotron-embed-1b-v2
vllm serve nvidia/llama-nemotron-embed-1b-v2 \
  --host 0.0.0.0 \
  --port 8001 \
  --runner pooling \
  --pooler-config '{"pooling_type": "MEAN"}' \
  --dtype auto \
  --gpu-memory-utilization 0.15 \
  --trust-remote-code
```

## Output

The guide should be written to: `docs/guides/gb10-vllm-embedding-setup.md`

## Key Files

- `docs/guides/falkordb-nas-infrastructure-setup.md` — existing infrastructure docs
- `docs/reviews/autobuild-api-key-isolation/TASK-REV-55C3-review-report.md` — vLLM AutoBuild setup
- `.guardkit/graphiti.yaml` — Graphiti config (will be updated in TASK-GLI-004)

## Reference

- Parent review: TASK-REV-8B3A
- DGX Spark vLLM setup: https://github.com/eelbaz/dgx-spark-vllm-setup
- DGX Spark Nemotron embed thread: https://forums.developer.nvidia.com/t/getting-nemotron-embed-working-on-dgx-spark/359447
- vLLM embedding docs: https://docs.vllm.ai/en/stable/serving/openai_compatible_server/
