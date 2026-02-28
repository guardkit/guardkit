# Review Report: TASK-REV-E4B2

## Executive Summary

TASK-GLI-001 (vLLM embedding setup guide) has **9 discrepancies** with the implemented `scripts/vllm-embed.sh`. Two are critical (wrong deployment model, wrong nomic flags), one is high severity (nemotron compatibility blocker undocumented), and six are medium/low. All are straightforward documentation updates with no architectural decisions required.

## Review Details
- **Mode**: Documentation alignment review
- **Depth**: Standard
- **Source of truth**: `scripts/vllm-embed.sh`
- **Target**: `tasks/backlog/graphiti-local-inference/TASK-GLI-001-vllm-embedding-setup-guide.md`

## Findings

### CRITICAL

| # | Finding | Task Says | Script Says |
|---|---------|-----------|-------------|
| 1 | Deployment model | Bare-metal `vllm serve` | Docker container via `nvcr.io/nvidia/vllm:26.01-py3` |
| 2 | nomic flags | `--task embed` | `--runner pooling --trust-remote-code` |

### HIGH

| # | Finding | Detail |
|---|---------|--------|
| 3 | Nemotron blocker | Requires `transformers>=5.0.0.dev0`; container 26.01 ships `4.57.1`. Non-functional. |

### MEDIUM

| # | Finding | Detail |
|---|---------|--------|
| 4 | Environment variables | `VLLM_EMBED_PORT`, `VLLM_EMBED_GPU_UTIL`, `VLLM_IMAGE`, `HF_TOKEN` — not documented |
| 6 | systemd vs Docker | Task mentions systemd; script uses Docker container lifecycle |

### LOW

| # | Finding | Detail |
|---|---------|--------|
| 5 | Custom model preset | `./vllm-embed.sh custom org/model` — not documented |
| 7 | Health check commands | Generic in task; script has specific curl commands |
| 8 | PYTORCH_CUDA_ALLOC_CONF | `expandable_segments:True` not documented |
| 9 | Missing key file reference | `scripts/vllm-embed.sh` not in Key Files section |

## Recommendations

All 9 findings should be resolved by updating TASK-GLI-001 in-place:

1. Replace bare-metal `vllm serve` commands with Docker `docker run` commands matching the script
2. Fix nomic flags from `--task embed` to `--runner pooling --trust-remote-code`
3. Add warning to nemotron section about transformers version incompatibility
4. Add environment variable configuration section
5. Add custom model preset documentation
6. Replace systemd references with Docker container lifecycle guidance
7. Add specific curl commands for health/models/embeddings test
8. Document `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`
9. Add `scripts/vllm-embed.sh` to Key Files

## Decision

**Recommendation**: Direct implementation — all changes are documentation corrections with no ambiguity.
