# DGX Spark / GB10 Research

Research, decisions, and deployment docs for the GuardKit inference fleet on the Dell DGX Spark GB10 (Blackwell SM121, 128 GB unified memory).

## Current architecture (deployed 2026-04-29)

<<<<<<< Updated upstream
**All-llama.cpp via llama-swap on :9000.** No vLLM. No Docker for inference. Four models permanently loaded, zero swap overhead.
=======
### Model serving strategy
- [**dark-factory-economics-and-model-serving.md**](./dark-factory-economics-and-model-serving.md) — primary research doc. Covers the April 2026 cost crisis (£30 Gemini spend in 3 days of Graphiti tinkering), forum research from the NVIDIA DGX Spark community, model footprint / throughput tables, and the llama-swap architectural decision. Updated 2026-04-24 with martinB78's authoritative benchmark table, the dynamic VRAM launcher pattern, griffith.mark's three-stage orchestration model, LiteLLM routing layer recommendation, Qwen3.6-27B "one model no swap" thesis, and sparkrun community tooling landscape.
- [**llama-swap-setup.md**](./llama-swap-setup.md) — companion implementation guide. Install, build llama.cpp for SM121, full fleet config.yaml with all five concurrent roles (Jarvis + Forge + architect-agent + Graphiti + embeddings + AutoBuild), smoke tests, monitoring, troubleshooting, rollback. Updated 2026-04-24 with the dynamic VRAM launcher script (adapted from martinB78), LiteLLM Phase 4 config, and Qwen3-Coder-Next int4-AutoRound as a test candidate.
>>>>>>> Stashed changes

| Model | Role | Footprint | Port |
|---|---|---|---|
| Qwen2.5-14B Q8_0 | Graphiti entity extraction + Jarvis intent routing | ~22 GB | :9000 (via llama-swap) |
| nomic-embed-text-v1.5 f16 | Embeddings (768 dims) for Graphiti + ChromaDB | ~0.3 GB | :9000 (via llama-swap) |
| Qwen3.6-35B-A3B Q4_K_XL | Workhorse: AutoBuild Player/Coach, Forge, Dataset Factory | ~21 GB | :9000 (via llama-swap) |
| Gemma 4 26B-A4B Q4_K_M | Fine-tuned GCSE study tutor (Socratic method) | ~17 GB | :9000 (via llama-swap) |
| **Total** | | **~60 GB** | **64 GB headroom** |

Production config: `/opt/llama-swap/config/config.yaml`
Systemd service: `llama-swap.service`
Logs: `/opt/llama-swap/logs/llama-swap.log`

## Document index

### Current (active)

| Document | Purpose |
|---|---|
| [**RUNBOOK-v3-production-deployment.md**](./RUNBOOK-v3-production-deployment.md) | Production deployment runbook. Executed 2026-04-28, six gaps found and fixed via TASK-RUN-D6F4, two operational follow-ups resolved via TASK-OPS-7CB1/9F2A. Post-fix runbook is clean-room re-executable. |
| [**AUTOBUILD-ON-LLAMA-SWAP-findings.md**](./AUTOBUILD-ON-LLAMA-SWAP-findings.md) | AutoBuild + llama-swap findings (2026-05-14, DDD South West demo prep). Anthropic-Messages-API compatibility, the `-np` ctx-split trap, Qwen3.6 protocol-following limit, the `/unload` safety hatch, memory-ceiling freeze postmortem, Qwen3-Coder-30B opt-in setup, Reachy/Jarvis routing topology. |
| [**llama-swap-systemd-supervision.md**](./llama-swap-systemd-supervision.md) | User-space systemd unit with `-watch-config` for auto-reload. Replaces the orphaned nohup process. Pending: sudo cleanup of stale root unit + `loginctl enable-linger`. |
| [**POST-VALIDATION-model-strategy-revision.md**](./POST-VALIDATION-model-strategy-revision.md) | Strategy pivot from dense 27B to MoE 35B-A3B workhorse. Explains the physics (bandwidth wall) and the decision. |
| [**gb10-model-requirements-matrix.md**](./gb10-model-requirements-matrix.md) | Fleet-wide model consolidation analysis: 16 roles → 6 models → 4 deployed. Speed expectations for the dense 27B are superseded by the post-validation revision but the role mapping and cluster analysis remain valid. |
| [**qwen3.6-27b-gb10-community-research.md**](./qwen3.6-27b-gb10-community-research.md) | Forum research on Qwen3.6-27B, MTP, DFlash, PrismaQuant, DDTree. Benchmark data and deployment recipes. |

### Historical (superseded but preserved)

| Document | Status |
|---|---|
| [llama-swap-setup.md](./llama-swap-setup.md) | **Superseded by RUNBOOK-v3.** Describes the old vLLM proxy + Coder-Next/GPT-OSS swap architecture. Kept for reference on llama.cpp build flags, dynamic VRAM launcher, and LiteLLM Phase 4 config. |
| [llama-swap-config.yaml](./llama-swap-config.yaml) | **Superseded.** Old config with vLLM proxy entries. Production config is now at `/opt/llama-swap/config/config.yaml` on the GB10. |
| [dark-factory-economics-and-model-serving.md](./dark-factory-economics-and-model-serving.md) | Original research doc. Historical context on the cost crisis, forum research, and DECISION-DF-001. Conclusions about model choices are superseded. |
| [dark-factory-dataset-factory-conversation-starter.md](./dark-factory-dataset-factory-conversation-starter.md) | Original conversation starter for the dataset factory session. Historical. |

### Validation records

| Document | What it proved |
|---|---|
| [**RESULTS-v3-production-deployment.md**](./RESULTS-v3-production-deployment.md) | Production deployment results: 65 GB VRAM, 41.32 tok/s workhorse, all four models coexisting. Six gaps found and documented. |
| [**VALIDATION-D6F4-gap-fix-results.md**](./VALIDATION-D6F4-gap-fix-results.md) | All six D6F4 gaps verified PASS against live deployment. Surfaced two operational follow-ups (overnight crashes + 429 throttling). |
| [**VALIDATION-OPS-7CB1-9F2A-results.md**](./VALIDATION-OPS-7CB1-9F2A-results.md) | Keep-alive timer revives crashed children in 30s (TASK-OPS-7CB1). Concurrency tuning eliminated 429 throttling: 0 rate limits vs 8 yesterday (TASK-OPS-9F2A). Both fixes installed and active on host. |
| [RESULTS-v2-all-llamacpp-validation.md](./RESULTS-v2-all-llamacpp-validation.md) | All-llama.cpp architecture works: Graphiti JSON extraction via llama.cpp (no xgrammar needed), embeddings at 768 dims, MoE workhorse at 45 tok/s, three-model co-existence at 46 GB. **The key evidence that eliminated vLLM.** |
| [RESULTS-qwen3.6-27b-validation.md](./RESULTS-qwen3.6-27b-validation.md) | Dense Qwen3.6-27B quality is excellent (tool calling, JSON, reasoning all pass) but hits 8.35 tok/s bandwidth wall on GB10. **The key evidence that pivoted to MoE.** |
| [RUNBOOK-v2-all-llamacpp-architecture.md](./RUNBOOK-v2-all-llamacpp-architecture.md) | The validation runbook for RESULTS-v2. |
| [RUNBOOK-qwen3.6-27b-validation.md](./RUNBOOK-qwen3.6-27b-validation.md) | The validation runbook for RESULTS-v1. |

### Background reading

| Document | Notes |
|---|---|
| `DGX Spark, Nemotron3, and NVFP4 - Thomas P. Braun.pdf` | NVFP4 optimisation background |

## Key decisions made during this research

1. **DECISION-DF-001:** No cloud API on dark factory critical path (triggered by £30 Gemini spend in 3 days)
2. **Dense 27B → MoE 35B-A3B:** Memory-bandwidth physics means dense models hit ~8-10 tok/s ceiling on GB10; MoE with 3B active params achieves 45+ tok/s
3. **vLLM → all-llama.cpp:** vLLM pre-allocates ~50 GB for a 14 GB model; llama.cpp takes only what it needs, reclaiming ~36 GB
4. **Four always-loaded models:** At ~60 GB total, no swapping is needed — everything stays hot with 64 GB headroom

## External references

<<<<<<< Updated upstream
- [NVIDIA DGX Spark / GB10 forum](https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719)
- [Spark Arena leaderboard](https://spark-arena.com/leaderboard)
- [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap)
- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)
- [AEON-7 DFlash deployment](https://github.com/AEON-7/Qwen3.6-NVFP4-DFlash) — reference for future DFlash integration
- [martinB78's full-stack repo](https://github.com/mARTin-B78/dgx-spark_lite-llm_llama-swap_vllm_llama-cpp_ollama)

## Rollback

If the all-llama.cpp architecture needs to be reverted:
```bash
sudo systemctl stop llama-swap
cp ~/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-config.yaml.pre-llamacpp.bak \
   ~/Projects/appmilla_github/guardkit/scripts/graphiti-mcp-config.yaml
cp ~/Projects/appmilla_github/guardkit/scripts/archive-vllm/*.sh \
   ~/Projects/appmilla_github/guardkit/scripts/
./scripts/vllm-graphiti.sh && ./scripts/vllm-embed.sh
```
=======
- [NVIDIA DGX Spark / GB10 forum](https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719) — the primary community resource for real-world benchmarks and setup tips
- [Spark Arena leaderboard](https://spark-arena.com/leaderboard) — community-submitted benchmarks
- [eugr/spark-vllm-docker](https://github.com/eugr/spark-vllm-docker) — the vLLM Docker images the existing scripts depend on
- [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap) — the model-lifecycle manager chosen as the unified front door
- [llama.cpp Anthropic Messages API PR #17570](https://github.com/ggml-org/llama.cpp/pull/17570) — the change that made llama.cpp a drop-in for the Claude Agent SDK
- [martinB78's full-stack repo](https://github.com/mARTin-B78/dgx-spark_lite-llm_llama-swap_vllm_llama-cpp_ollama) — reference implementation for LiteLLM + llama-swap + vLLM + llama.cpp on GB10 (reviewed 2026-04-24)
- [LiteLLM](https://docs.litellm.ai/) — unified API proxy, routing, and usage logging (Phase 4 target)
- [sparkrun](https://sparkrun.dev) — dbsci's inference orchestration CLI (monitoring for future adoption)
>>>>>>> Stashed changes
