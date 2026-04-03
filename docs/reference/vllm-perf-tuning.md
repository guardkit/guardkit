# vLLM Performance Tuning — GB10 Reference

Proven vLLM flags, environment variables, and memory budgets for optimizing
inference throughput on Dell Pro Max GB10 / DGX Spark.

---

## vLLM Serve Flags

### High Impact

| Flag | Effect | Notes |
|------|--------|-------|
| `--load-format fastsafetensors` | 2-3x faster model loading | Don't use when model needs >0.85 of available RAM |
| `--num-scheduler-steps 8` | Multi-step scheduling, reduces per-token overhead | Default is 1; 8 is good for single-user |
| `--enable-chunked-prefill` | Overlaps prefill and decode phases | Critical for long context (>32K) workloads |
| `--attention-backend flashinfer` | Fast attention implementation | Already default in newer vLLM |
| `--enable-prefix-caching` | Reuses KV cache for repeated prefixes | Huge win for Graphiti (TTFT 28s -> 2-3s) and AutoBuild (repeated system prompts) |

### Medium Impact

| Flag | Effect | Notes |
|------|--------|-------|
| `--max-num-seqs 4` | Limits concurrent sequences | Reduces memory overhead for single-user workloads like AutoBuild |
| `--gpu-memory-utilization 0.90` | More KV cache space | Safe when GPU is dedicated; watch total memory with co-hosted models |
| `--kv-cache-dtype fp8` | Halves KV cache memory | Allows longer contexts; slight quality trade-off |

### MoE-Specific

| Flag | Effect | Notes |
|------|--------|-------|
| `--enable-expert-parallel` | MoE expert parallelism | For data-parallel multi-node configs |
| `VLLM_FLASHINFER_MOE_BACKEND=latency` | Latency-optimized MoE on SM 12.1 | ~60% speedup on GB10; required for single-request workloads |

### Structured Output (Graphiti)

| Flag | Effect | Notes |
|------|--------|-------|
| `--structured-outputs-config.backend xgrammar` | Token-level JSON schema enforcement | Required for Graphiti; replaces old `--guided-decoding-backend` in v0.13+ |

---

## Docker Environment Variables

| Env Var | Effect | Notes |
|---------|--------|-------|
| `VLLM_USE_V1=1` | vLLM v1 engine | Significantly faster for single-request workloads (newer images only) |
| `CUDA_DEVICE_ORDER=PCI_BUS_ID` | Consistent GPU ordering | Prevents device ID confusion |
| `SAFETENSORS_FAST_GPU=1` | Direct GPU loading of safetensors | Faster weight loading |
| `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` | Blackwell memory tuning | Reduces fragmentation |
| `OMP_NUM_THREADS=8` | CPU thread management | Prevents CPU oversubscription |
| `NCCL_IB_DISABLE=1` | Disable InfiniBand | Required for single-node setups |
| `VLLM_NVFP4_GEMM_BACKEND=cutlass` | NVFP4 GEMM backend | Required for NVFP4 models on GB10 |
| `VLLM_USE_FLASHINFER_MOE_FP4=0` | Disable FlashInfer MOE FP4 | Required for NVFP4 models on GB10 |

---

## Memory Budget (128GB unified, all 3 services)

| Service | Port | GPU Util | Approx Memory |
|---------|------|----------|---------------|
| Graphiti LLM (Qwen2.5-14B FP8) | 8000 | 0.40 | ~51GB |
| Embeddings (nomic-embed) | 8001 | 0.03 | ~0.5GB |
| AutoBuild LLM (Qwen3-Coder-Next FP8) | 8002 | 0.90 | ~45GB |
| **Total** | | | **~97GB** |

Headroom: ~31GB for OS, CPU tasks, Graphiti/FalkorDB. Safe but tight — if OOM, reduce AutoBuild GPU util to 0.85.

---

## Measured Performance (from profiling runs)

| Metric | Baseline (NGC, old flags) | Target (spark-vllm + tuning) |
|--------|--------------------------|------------------------------|
| Throughput | ~43 tok/s | ~60-70 tok/s |
| Per-turn latency | ~20s | ~13-15s |
| vs Anthropic API factor | 3-4x | ~2-2.5x |
| Model load time | 3-5 min | ~2-3 min (fastsafetensors) |

---

## Changes Applied to vllm-serve.sh (Apr 2026)

1. Default image: NGC -> `ghcr.io/eugr/spark-vllm:latest`
2. GPU util: 0.80 -> 0.90
3. New flags: `--enable-chunked-prefill`, `--load-format fastsafetensors`, `--num-scheduler-steps 8`, `--max-num-seqs 4`
4. New env vars: `VLLM_USE_V1=1`, `CUDA_DEVICE_ORDER=PCI_BUS_ID`, `SAFETENSORS_FAST_GPU=1`
5. Fallback: `VLLM_USE_NGC=1 ./scripts/vllm-serve.sh` restores old NGC image
6. Original backed up as `scripts/vllm-serve.original.sh`

## Changes Applied to vllm-agentic-factory.sh (Apr 2026)

Migrated from direct `docker run` with broken ghcr.io image to locally-built
spark-vllm-docker `vllm-node-tf5` image.

1. **Image**: `ghcr.io/eugr/spark-vllm:latest` (broken, private) -> locally-built
   `vllm-node-tf5` via `./build-and-copy.sh --tf5` in `~/Projects/spark-vllm-docker`
2. **Networking**: `-p 8002:8000` port mapping -> `--network host` with `--port 8002`
3. **Run script**: `run-on-gb10.sh` updated to support both `--resume` and fresh starts
   (previously hardcoded `--resume`)
4. **Flags**: Aligned with spark-arena leaderboard #1 recipe (see investigation below)

Prerequisites (one-time):
```bash
git clone https://github.com/eugr/spark-vllm-docker.git ~/Projects/spark-vllm-docker
cd ~/Projects/spark-vllm-docker && ./build-and-copy.sh --tf5
```

---

## Spark-Arena Leaderboard Investigation (Apr 2026)

### Context

The spark-arena leaderboard (https://spark-arena.com/leaderboard) shows
Qwen3.5-35B-A3B-FP8 achieving **50.75 tok/s** on a single DGX Spark. Our
dataset generation pipeline was achieving **38 tok/s**. Investigation to
close the gap.

### What we tried

| Change | Result |
|--------|--------|
| `launch-cluster.sh --solo` (Ray wrapper) | **32 tok/s** — slower due to Ray overhead |
| Direct `docker run vllm-node` (no Ray) | **35 tok/s** — better but below baseline |
| Added `--kv-cache-dtype fp8`, `--attention-backend flashinfer` | **35 tok/s** — no change |
| Added `VLLM_MARLIN_USE_ATOMIC_ADD=1` | **35 tok/s** — no change |
| Removed `VLLM_USE_V1=1`, `--enable-chunked-prefill` | Marginal improvement |
| Full spark-arena #1 recipe flags | **38 tok/s** — matched previous baseline |
| Previous `cu130-nightly` image with original flags | **40 tok/s** — the best observed |

### Flags from spark-arena #1 recipe (final config)

```
--trust-remote-code
--enable-auto-tool-choice --tool-call-parser qwen3_coder
--reasoning-parser qwen3
--enable-prefix-caching
--kv-cache-dtype fp8
--attention-backend flashinfer
--max-num-batched-tokens 32768
--max-num-seqs 10
--max-cudagraph-capture-size 10
--mamba-ssm-cache-dtype float16
--load-format fastsafetensors
VLLM_MARLIN_USE_ATOMIC_ADD=1
mods/fix-qwen3.5-autoround (Transformers rope validation patch)
```

### Root cause: leaderboard measures batched throughput

The 50 tok/s leaderboard figure uses `llama-benchy`, which sends **multiple
concurrent requests**. The throughput is measured across the batch.

Our pipeline sends **1 request at a time** (sequential Player → Coach loop).
vLLM logs consistently show `Running: 1 reqs, Waiting: 0 reqs`. With only
1 concurrent request, CUDA graph optimisations and batching provide no
benefit. The 38-40 tok/s we observe is close to the **single-request hardware
limit** for this model on GB10.

### Key learnings

1. **Leaderboard != real-world single-request throughput**. Spark-arena
   benchmarks use concurrent batched requests. Single-request decode
   throughput on Qwen3.5-35B-A3B-FP8 tops out around **38-41 tok/s** on GB10.

2. **`launch-cluster.sh --solo` adds Ray overhead** (~5 tok/s penalty).
   For single-node setups, direct `docker run` is faster. The `--no-ray`
   flag has no effect in solo mode.

3. **`VLLM_USE_V1=1` may cause regressions** in vLLM 0.18.x for this model.
   The leaderboard recipes omit it. Removing it recovered ~3 tok/s.

4. **`--enable-chunked-prefill` hurts single-request workloads**. None of
   the top recipes use it. Removing it helped slightly.

5. **`vllm-node-tf5` vs `cu130-nightly`**: The locally-built spark-vllm
   image (vLLM 0.18.2) performed ~2 tok/s slower than `cu130-nightly`
   (vLLM ~0.17.x, pulled 26 Mar 2026) on our workload. Newer is not
   always faster for specific model/workload combinations.

6. **The real throughput bottleneck is architectural**: Player and Coach
   run sequentially. Overlapping Player generation with Coach evaluation
   (concurrent requests) would better utilise the GPU and could approach
   the 50 tok/s batched throughput.

### Run time estimates (2,500 targets at 38 tok/s)

| Metric | Value |
|--------|-------|
| Avg tokens per target (prompt + completion) | ~10,500 |
| Time per target at 38 tok/s decode | ~35-45s |
| Estimated total for 2,500 targets | ~25-30 hours |
| Previous run (Run 1, 40 tok/s) | 23 hours |

---

## Related Files

- `scripts/vllm-agentic-factory.sh` — Dataset Factory LLM (port 8002, uses spark-vllm-docker)
- `scripts/vllm-serve.sh` — AutoBuild LLM (port 8002, optimized)
- `scripts/vllm-graphiti.sh` — Graphiti LLM (port 8000, candidates for same optimizations)
- `scripts/vllm-embed.sh` — Embedding model (port 8001)
- `docs/reference/gb10-vllm-resources.md` — External resources and community links
- `docs/reviews/vllm-profiling/` — Raw profiling run data (Runs 1-6)
- `.claude/reviews/TASK-REV-CB30-vllm-viability-review-report.md` — Full viability analysis
