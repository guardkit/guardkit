# DGX Spark / GB10 Research

Research and decisions for running the GuardKit dark factory on the Dell Pro Max GB10 (Blackwell SM121, 128 GB unified memory).

## Contents

### Model serving strategy
- [**dark-factory-economics-and-model-serving.md**](./dark-factory-economics-and-model-serving.md) — primary research doc. Covers the April 2026 cost crisis (£30 Gemini spend in 3 days of Graphiti tinkering), forum research from the NVIDIA DGX Spark community, model footprint / throughput tables, and the llama-swap architectural decision. Updated 2026-04-24/25 with martinB78's benchmark table, dynamic VRAM launcher, LiteLLM routing, Qwen3.6-27B thesis, and dataset factory co-existence analysis (§3.11).
- [**llama-swap-setup.md**](./llama-swap-setup.md) — companion implementation guide. Install, build llama.cpp for SM121, full fleet config.yaml, smoke tests, monitoring, troubleshooting, rollback. Updated 2026-04-24 with dynamic VRAM launcher (§12), LiteLLM Phase 4 config (§13), and int4-AutoRound test candidate.

### Related files elsewhere in the repo
- `.guardkit/llm-provider-switching.md` — per-repo Graphiti provider toggle (GB10 vLLM / MacBook Ollama / Gemini fallback)
- `scripts/vllm-graphiti.sh` — existing Graphiti vLLM launcher with xgrammar JSON enforcement
- `scripts/vllm-serve.sh` — existing AutoBuild vLLM preset manager
- `scripts/vllm-embed.sh` — existing embedder launcher

### Background reading
- `DGX Spark, Nemotron3, and NVFP4: Getting to 65+ tps | by Thomas P. Braun | Avarok.pdf` — NVFP4 optimisation background from the Avarok team

## External references

- [NVIDIA DGX Spark / GB10 forum](https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719) — the primary community resource for real-world benchmarks and setup tips
- [Spark Arena leaderboard](https://spark-arena.com/leaderboard) — community-submitted benchmarks
- [eugr/spark-vllm-docker](https://github.com/eugr/spark-vllm-docker) — the vLLM Docker images the existing scripts depend on
- [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap) — the model-lifecycle manager chosen as the unified front door
- [llama.cpp Anthropic Messages API PR #17570](https://github.com/ggml-org/llama.cpp/pull/17570) — the change that made llama.cpp a drop-in for the Claude Agent SDK
- [martinB78's full-stack repo](https://github.com/mARTin-B78/dgx-spark_lite-llm_llama-swap_vllm_llama-cpp_ollama) — reference implementation for LiteLLM + llama-swap + vLLM + llama.cpp on GB10
- [LiteLLM](https://docs.litellm.ai/) — unified API proxy, routing, and usage logging (Phase 4 target)
- [sparkrun](https://sparkrun.dev) — dbsci's inference orchestration CLI (monitoring for future adoption)
