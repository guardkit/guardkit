# GB10 / DGX Spark — vLLM Resources & Community References

External resources for hosting models on Dell Pro Max GB10 / DGX Spark hardware.
Use this as a reference when creating or updating vLLM serving scripts.

---

## Docker Images for vLLM on GB10

### spark-vllm-docker (community, recommended)
- **Repo**: https://github.com/eugr/spark-vllm-docker
- **Image**: `ghcr.io/eugr/spark-vllm:latest`
- **What it provides**:
  - Nightly prebuilt vLLM and FlashInfer wheels (avoids 20-40 min compilation)
  - Multi-node cluster support with InfiniBand/RDMA
  - No-Ray mode (`--no-ray`) — slightly faster inference (~1 tok/s), lower memory
  - Custom mods/patches for Qwen models (e.g., `fix-qwen35-tp4-marlin`)
  - `gpu-mem-util-gb` mod — specify GPU memory in GiB instead of fraction
  - fastsafetensors support for faster weight loading
  - Autodiscovery of GB10 nodes
  - Build time: 2-3 min vs 20-40 min from source
- **Recipes available**: qwen3-coder-next-int4-autoround, qwen3.5-122b-fp8, qwen3.5-35b-a3b-fp8, qwen3.5-397b-int4-autoround
- **Key flags**: `--solo` (single node), `--no-ray`, `--setup` (force autodiscovery), `--apply-mod <path>`

### NGC vLLM (NVIDIA official, stable)
- **Image**: `nvcr.io/nvidia/vllm:26.01-py3` (Jan 2026 release)
- **When to use**: Stable fallback if spark image has issues
- **Limitations**: Older vLLM version, no GB10-specific optimizations

### Avarok NVFP4-optimised (community, for MiniMax)
- **Image**: `avarok/dgx-vllm:latest`
- **When to use**: MiniMax M2.5 NVFP4 specifically (~30 tok/s vs ~17 tok/s on NGC)

---

## Benchmarking & Leaderboards

### Spark Arena
- **URL**: https://spark-arena.com/leaderboard
- **What it shows**: Community benchmarks of models running on GB10/DGX Spark hardware
- **Key data point**: Qwen3-Coder-Next showing 60-70 tok/s with optimized configs (vs ~43 tok/s baseline on NGC)
- **Note**: SPA app — data loads dynamically, can't be scraped statically
- **Built by**: eugr, Raphael Amorim, dbsci (same community as spark-vllm-docker)
- **Uses**: llama-benchy for benchmarking, sparkrun for workload management

---

## NVIDIA Developer Forums

### DGX Spark / GB10 Forum
- **URL**: https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719
- **Key threads**:
  - MiniMax M2.5 NVFP4 on single DGX Spark: https://forums.developer.nvidia.com/t/minimax-2-5-reap-nvfp4-on-single-dgx-spark/361248
    - Source of NVFP4 env vars (mjpansa, Feb 2026): CUDA_DEVICE_ORDER, SAFETENSORS_FAST_GPU, VLLM_NVFP4_GEMM_BACKEND, etc.
- **Community contributors**: mjpansa (NVFP4 tuning), eugr (spark-vllm-docker)

---

## GB10 Hardware Notes

- **GPU**: Blackwell-architecture, SM 12.1, ARM64
- **Memory**: 128GB unified (CPU+GPU shared)
- **FP8**: Stable quantization on this hardware
- **NVFP4**: Has ARM64-specific bugs — test thoroughly
- **Driver warning**: Driver 590.x has CUDAGraph capture deadlock on GB10; use 580.x for large models
- **GPU clock tuning**: `sudo nvidia-smi -lgc 200,2150` can prevent sudden shutdowns under heavy load
- **Cache clearing**: `sudo sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'` can fix stuck model loading

---

## GPU Contention Strategies (single GB10)

When running long dataset generation jobs (50-60 hours), the GB10's GPU is fully
occupied. These strategies unblock Graphiti-dependent work (project init, system-arch,
AutoBuild context loading):

### Option 1: Embedding co-hosting (safe, trivial)
The embedding model (nomic-embed, port 8001) uses only 0.03 GPU util (~0.5GB).
It can safely co-host alongside any dataset generation run.

### Option 2: Graphiti LLM on MacBook Pro M2 Max
- **Hardware**: 40-core GPU, 96GB RAM (need to close browsers/IDEs to free memory)
- **Model**: Qwen2.5-14B GGUF via llama.cpp or Ollama
- **How**: Run llama-server or `ollama serve` on MacBook, point `.guardkit/graphiti.yaml`
  LLM endpoint to `http://<macbook-ip>:8000`
- **Expected speed**: ~10-15 tok/s (slower than GB10's ~40 tok/s but unblocks work)
- **Advantage**: GB10 stays 100% on dataset generation

### Option 3: Graphiti LLM on GB10 CPU-only
- Run Qwen2.5-14B GGUF via llama.cpp with `-ngl 0` (no GPU layers)
- Very slow (~3-5 tok/s) but zero GPU contention
- Last resort — MacBook option is better if available

### Option 4: Time-slicing
- Dataset generation overnight/unattended
- Graphiti + interactive work during the day
- No risk but less efficient overall

---

## Related Project Files

- `scripts/vllm-serve.sh` — AutoBuild LLM (port 8002)
- `scripts/vllm-graphiti.sh` — Graphiti LLM (port 8000)
- `scripts/vllm-embed.sh` — Embedding model (port 8001)
- `docs/reference/vllm-perf-tuning.md` — Performance tuning flags reference
- `docs/reviews/vllm-profiling/` — Raw profiling run data
- `.claude/reviews/TASK-REV-CB30-vllm-viability-review-report.md` — Viability analysis
