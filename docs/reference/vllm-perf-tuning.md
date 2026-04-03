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

**Pending validation**: Needs a profiling run (Run 7) on the GB10 to confirm actual tok/s improvement.

---

## Related Files

- `scripts/vllm-serve.sh` — AutoBuild LLM (port 8002, optimized)
- `scripts/vllm-graphiti.sh` — Graphiti LLM (port 8000, candidates for same optimizations)
- `scripts/vllm-embed.sh` — Embedding model (port 8001)
- `docs/reference/gb10-vllm-resources.md` — External resources and community links
- `docs/reviews/vllm-profiling/` — Raw profiling run data (Runs 1-6)
- `.claude/reviews/TASK-REV-CB30-vllm-viability-review-report.md` — Full viability analysis
