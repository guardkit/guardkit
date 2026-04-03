---
id: TASK-REV-GMAC
title: "Investigate running Graphiti LLM on MacBook Pro M2 Max to unblock GB10 dataset runs"
status: completed
created: 2026-04-03T00:00:00Z
updated: 2026-04-03T00:00:00Z
priority: high
tags: [graphiti, macbook, gpu-contention, vllm, llama-cpp, ollama, infrastructure]
task_type: review
review_mode: decision
review_depth: standard
complexity: 4
review_results:
  mode: decision
  depth: standard
  score: 82
  findings_count: 7
  recommendations_count: 3
  decision: implement
  report_path: .claude/reviews/TASK-REV-GMAC-review-report.md
---

# Task: Investigate running Graphiti LLM on MacBook Pro M2 Max

## Problem

The GB10 is a single-GPU system (128GB unified). When running long dataset generation
jobs (50-60 hours via `vllm-agentic-factory.sh`), the GPU is fully occupied and cannot
co-host the Graphiti LLM (port 8000). This blocks:

- New project initialization (writes context to Graphiti)
- System architecture/design/plan commands (write to Graphiti)
- AutoBuild context loading (reads from Graphiti, even when using Claude Max subscription)

The embedding model (port 8001, ~0.5GB) is trivially small and can co-host — confirmed.

## Proposed Solution

Offload the Graphiti LLM to the MacBook Pro M2 Max over the local network, leaving
the GB10 100% dedicated to dataset generation.

## MacBook Pro Hardware

- **Model**: MacBook Pro Mac14,6 (Model Number Z176000C3B/A)
- **Chip**: Apple M2 Max — 12 cores (8P + 4E)
- **GPU**: 38-core Apple GPU, Metal 3
- **Memory**: 96GB unified
- **Display**: 3456x2234 Retina XDR (built-in)
- **Constraint**: Typically memory-heavy with browsers/IDEs open. May need to close
  browsers and reduce tab count to free 20-30GB for the LLM.

## Investigation Scope

### 1. Model Selection for M2 Max
- Qwen2.5-14B is the current Graphiti LLM on GB10 (~16GB FP8)
- Investigate GGUF quants available (Q4_K_M, Q5_K_M, Q8_0) and size vs quality trade-off
- The model must support Graphiti's `response_format=json_schema` requirement
- Check if xgrammar/grammar-based JSON enforcement works on Apple Silicon

### 2. Serving Option: Ollama vs llama.cpp
- **Ollama**: Easiest setup, good Metal support, but does it support structured output / json_schema?
- **llama.cpp (llama-server)**: More control, supports `--grammar` for JSON, better for fine-grained config
- **vLLM on Mac**: Does vLLM run on Apple Silicon at all? Likely not (CUDA-dependent)
- **mlx-lm**: Apple's own framework — investigate if it supports OpenAI-compatible API + json_schema

### 3. Graphiti Configuration Changes
- `.guardkit/graphiti.yaml` — what needs to change to point the LLM endpoint at MacBook?
- Currently: `http://promaxgb10-41b1:8000` → needs to become `http://<macbook-ip>:8000`
- Can this be an env var override for easy switching?
- Embedding model stays on GB10 (port 8001) — confirm Graphiti can use split endpoints

### 4. Network Considerations
- Both machines on same Tailscale network? Or local LAN?
- Latency impact: local network adds 1-2ms per request — negligible for LLM inference
- Firewall: macOS may block incoming connections on the serving port

### 5. Performance Expectations
- M2 Max with 38 GPU cores: expect ~15-25 tok/s for Qwen2.5-14B Q4_K_M
- Slower than GB10 (~40 tok/s FP8) but fast enough for Graphiti ingestion
- Graphiti's bottleneck is entity extraction quality, not raw speed
- Prefix caching won't be available (llama.cpp/Ollama) — TTFT may be higher

### 6. Memory Budget on MacBook
- Qwen2.5-14B Q4_K_M: ~8-10GB
- Qwen2.5-14B Q5_K_M: ~10-12GB
- Qwen2.5-14B Q8_0: ~16GB
- With typical IDE/browser load: need to verify 96GB is sufficient
- Recommendation: start with Q4_K_M, test quality, upgrade if needed

## Acceptance Criteria

- [ ] Identify best model quant for M2 Max (size vs Graphiti extraction quality)
- [ ] Identify best serving option (Ollama vs llama.cpp vs mlx-lm)
- [ ] Confirm json_schema enforcement works on chosen platform
- [ ] Document `graphiti.yaml` config changes needed for split endpoints
- [ ] Test Graphiti `add_episode` with MacBook-hosted LLM + GB10-hosted embeddings
- [ ] Measure tok/s and TTFT on MacBook
- [ ] Document setup steps for future reference

## References

- `docs/reference/gb10-vllm-resources.md` — GPU contention strategies section
- `docs/reference/vllm-perf-tuning.md` — Current GB10 tuning reference
- `scripts/vllm-graphiti.sh` — Current Graphiti LLM setup (GB10)
- `.guardkit/graphiti.yaml` — Graphiti endpoint configuration
- `.claude/rules/graphiti-knowledge-graph.md` — Graphiti MCP usage guide
