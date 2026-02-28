---
id: TASK-REV-E4B2
title: Update TASK-GLI-001 guide to match vllm-embed.sh implementation
task_type: review
status: completed
created: 2026-02-27T00:00:00Z
updated: 2026-02-27T00:00:00Z
priority: medium
tags: [documentation, vllm, embeddings, gb10, graphiti]
complexity: 3
---

# Task: Update TASK-GLI-001 Guide to Match vllm-embed.sh Implementation

## Description

Review and update `tasks/backlog/graphiti-local-inference/TASK-GLI-001-vllm-embedding-setup-guide.md` so that its documented commands, architecture, and guidance accurately reflect the working implementation in `scripts/vllm-embed.sh`.

The script has diverged from the original task spec in several significant ways. The task guide needs to be updated to serve as an accurate reference.

## Key Discrepancies to Resolve

### 1. Docker-based deployment (script) vs bare-metal vllm serve (task)
- **Task** documents `vllm serve ...` commands run directly on the host
- **Script** uses `docker run` with the NVIDIA vLLM container (`nvcr.io/nvidia/vllm:26.01-py3`)
- Update task to reflect the Docker-based approach with correct flags (`--gpus all`, `--ipc=host`, `--ulimit`, HF cache mount, etc.)

### 2. nomic-embed-text-v1.5 requires `--runner pooling` (not `--task embed`)
- **Task** documents nomic with `--task embed` flag
- **Script** uses `--runner pooling --trust-remote-code` for nomic
- Update the Option A command block accordingly

### 3. Nemotron transformers compatibility warning
- **Script** documents that nemotron requires `transformers>=5.0.0.dev0` but the 26.01 container ships `4.57.1`
- **Task** does not mention this blocker
- Add a clear warning that nemotron is non-functional with current container

### 4. Environment variable configuration
- **Script** supports `VLLM_EMBED_PORT`, `VLLM_EMBED_GPU_UTIL`, `VLLM_IMAGE`, `HF_TOKEN`
- **Task** has none of this
- Document the environment variable override interface

### 5. Custom model preset
- **Script** supports `custom org/model` as a third option
- **Task** only documents nomic and nemotron
- Add the custom model option

### 6. Container lifecycle management
- **Script** handles stopping/removing existing containers before starting
- **Task** only documents systemd (which is not how the script works)
- Update operational guidance to match Docker container approach

### 7. Health check and test commands
- **Script** provides specific curl commands for health, models, and embedding test
- **Task** mentions health checks generically
- Replace with the actual commands from the script

### 8. PYTORCH_CUDA_ALLOC_CONF environment variable
- **Script** sets `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` inside the container
- **Task** does not mention this
- Document this GB10/Blackwell-specific config

### 9. Script reference
- Add `scripts/vllm-embed.sh` to the Key Files section

## Acceptance Criteria

- [ ] vLLM serve commands updated to reflect Docker-based deployment
- [ ] nomic flags corrected to `--runner pooling` instead of `--task embed`
- [ ] Nemotron section includes transformers version incompatibility warning
- [ ] Environment variable configuration documented
- [ ] Custom model preset documented
- [ ] Container lifecycle (stop/rm/run) documented
- [ ] Health check and test curl commands match script output
- [ ] `scripts/vllm-embed.sh` added to Key Files
- [ ] No stale/incorrect information remains in the task

## Files to Review

- `tasks/backlog/graphiti-local-inference/TASK-GLI-001-vllm-embedding-setup-guide.md` (target)
- `scripts/vllm-embed.sh` (source of truth)

## Reference

- Parent task: TASK-GLI-001
