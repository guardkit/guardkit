---
id: TASK-GLI-001
title: GB10 vLLM setup guide — embedding model instance with optimal config
task_type: implementation
status: in_review
created: 2026-02-22T23:45:00Z
updated: 2026-02-27T12:00:00Z
previous_state: in_progress
state_transition_reason: "Guide complete, benchmark results pending GB10 hardware execution"
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

Create a detailed setup guide for deploying a vLLM embedding model instance on the Dell ProMax GB10, optimised for Graphiti seeding workloads. The guide should cover model selection, vLLM configuration via Docker container, and verification.

This is the foundational infrastructure task — all other subtasks depend on the embedding endpoint being available.

**Implementation**: `scripts/vllm-embed.sh` — Docker-based launch script using the NVIDIA NGC vLLM container (`nvcr.io/nvidia/vllm:26.01-py3`).

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
  - `--runner pooling` (for embedding models)
  - `--dtype` (auto vs bfloat16 vs float16)
  - `--gpu-memory-utilization` (leave headroom for LLM instance on port 8000)
  - `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (Blackwell memory config)
  - Any GB10-specific flags (FlashInfer, tensor parallel, etc.)
- [x] Document Docker container lifecycle (stop/rm/run) via `scripts/vllm-embed.sh`
- [x] Document health check / readiness probe (`curl http://localhost:8001/health`, `/v1/models`)
- [ ] Document firewall/Tailscale access for port 8001
- [ ] Test: verify `/v1/embeddings` endpoint returns correct dimension vectors
- [ ] Test: verify embedding quality — seed a small test document via graphiti-core and confirm entity extraction works

## Model Selection Guidance

### Primary: nomic-embed-text-v1.5 (137M params) — RECOMMENDED
- Proven quality parity with OpenAI text-embedding-3-small (MTEB 62.39 vs 62.26)
- Negligible memory footprint (~274MB in fp16)
- Served in vLLM via `--runner pooling --trust-remote-code`
- 8192 token context window
- Works with the 26.01 NVIDIA NGC container

### Alternative: nvidia/llama-nemotron-embed-1b-v2 (1B params) — BLOCKED
- Purpose-built for NVIDIA hardware
- Higher quality (multilingual, 8192 tokens, Matryoshka embeddings)
- ~2GB in fp16, still trivial on 128GB
- Has DGX Spark community track record
- Requires `--runner pooling` and `--pooler-config '{"pooling_type": "MEAN"}'`

> **WARNING**: Nemotron uses a custom bidirectional encoder architecture that falls back to the Transformers backend in vLLM. The 26.01 container ships `transformers==4.57.1`, but encoder model support requires `transformers>=5.0.0.dev0`. **Use nomic until a newer container with transformers 5.x is released.**

### Launch Script

Use `scripts/vllm-embed.sh` to start the embedding server:

```bash
# Option A: nomic-embed-text-v1.5 (default, recommended)
./scripts/vllm-embed.sh

# Option B: nvidia/llama-nemotron-embed-1b-v2 (BLOCKED — see warning above)
./scripts/vllm-embed.sh nemotron

# Option C: Custom model
./scripts/vllm-embed.sh custom org/model-name
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VLLM_EMBED_PORT` | `8001` | Server port |
| `VLLM_EMBED_GPU_UTIL` | `0.15` | GPU memory utilization (0.0-1.0) |
| `VLLM_IMAGE` | `nvcr.io/nvidia/vllm:26.01-py3` | Docker image |
| `HF_TOKEN` | (unset) | Hugging Face token (for gated models) |

### Docker Run Command (reference)

The script runs:

```bash
docker run -d \
  --name vllm-embedding \
  --gpus all \
  -p 8001:8001 \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  ${HF_TOKEN:+-e "HF_TOKEN=$HF_TOKEN"} \
  -e "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True" \
  nvcr.io/nvidia/vllm:26.01-py3 \
  vllm serve nomic-ai/nomic-embed-text-v1.5 \
    --host 0.0.0.0 \
    --port 8001 \
    --dtype auto \
    --gpu-memory-utilization 0.15 \
    --runner pooling \
    --trust-remote-code
```

Key Docker flags:
- `--gpus all` — expose all GPUs to the container
- `--ipc=host` — shared memory for NCCL/PyTorch
- `--ulimit memlock=-1` — unlimited locked memory for GPU buffers
- `-v .cache/huggingface` — persist downloaded models across container restarts
- `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` — GB10/Blackwell memory allocator tuning

### Container Lifecycle

```bash
# Stop and remove existing container
docker stop vllm-embedding && docker rm vllm-embedding

# Restart (just re-run the script)
./scripts/vllm-embed.sh
```

### Health Check and Test Commands

```bash
# Health check
curl http://localhost:8001/health

# List loaded models
curl http://localhost:8001/v1/models

# Test embeddings
curl http://localhost:8001/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "nomic-embed-text-v1.5", "input": "Hello world"}'

# View container logs
docker logs -f vllm-embedding
```

## Output

The guide should be written to: `docs/guides/gb10-vllm-embedding-setup.md`

## Key Files

- `scripts/vllm-embed.sh` — Docker-based embedding server launch script (source of truth)
- `docs/guides/falkordb-nas-infrastructure-setup.md` — existing infrastructure docs
- `docs/reviews/autobuild-api-key-isolation/TASK-REV-55C3-review-report.md` — vLLM AutoBuild setup
- `.guardkit/graphiti.yaml` — Graphiti config (will be updated in TASK-GLI-004)

## Reference

- Parent review: TASK-REV-8B3A
- DGX Spark vLLM setup: https://github.com/eelbaz/dgx-spark-vllm-setup
- DGX Spark Nemotron embed thread: https://forums.developer.nvidia.com/t/getting-nemotron-embed-working-on-dgx-spark/359447
- vLLM embedding docs: https://docs.vllm.ai/en/stable/serving/openai_compatible_server/
