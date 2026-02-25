# MiniMax M2.5 Backup Setup — Dell ProMax GB10

> **Purpose**: Set up MiniMax M2.5 as a resilience layer on the GB10, providing frontier-level
> local inference when the Claude API is unavailable, rate-limited, or when you're approaching
> your Max quota and want to preserve it for interactive Claude Code sessions.
>
> **Non-goal**: This does NOT replace the Qwen3-Coder-Next setup for AutoBuild. Qwen3 remains
> the primary implementation model. MiniMax is the backup for planning/spec work and API outages.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MacBook Pro M2 Max                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Claude Code  │  │  Claude      │  │  guardkit        │  │
│  │ (VS Code)    │  │  Desktop     │  │  autobuild       │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │            │
│         ▼                 ▼                    ▼            │
│    Anthropic API    Anthropic API     ANTHROPIC_BASE_URL    │
│    (cloud)          (cloud)           ═══════════╗          │
└─────────────────────────────────────────────════╬══════════─┘
                                                  ║
                                          ┌───────▼────────┐
                                          │  GB10 :8000    │
                                          │                │
                                          │  PRIMARY:      │
                                          │  Qwen3-Coder   │
                                          │  -Next FP8     │
                                          │  (AutoBuild)   │
                                          │                │
                                          │  BACKUP:       │
                                          │  MiniMax M2.5  │
                                          │  (swap in when │
                                          │  Claude is     │
                                          │  down/limited) │
                                          └────────────────┘
```

**Key principle**: Both models serve on the **same port** (8000) with the **same model alias**
(`claude-sonnet-4-6`), so all downstream tooling works without changes. Only one runs at a time.

## Quick Reference — Swap Commands

```bash
# Normal day: AutoBuild with Qwen3 (already running)
./vllm-serve.sh                    # or ./vllm-serve.sh next

# Claude API goes down → swap to MiniMax for spec/planning work
./vllm-serve.sh minimax            # stops Qwen3, starts MiniMax (~5-8 min)

# Even quicker (if llama.cpp is built): no Docker overhead
./vllm-serve.sh minimax-gguf       # stops everything, starts llama-server (~2 min)

# Claude API is back → swap back to Qwen3 for AutoBuild
./vllm-serve.sh                    # stops MiniMax, starts Qwen3 (~3-5 min)
```

---

## Step 1: Pre-Download Model Weights

Do this once. Downloads are large, so run them ahead of time rather than when you actually
need the backup.

### Option A: NVFP4 REAP for vLLM (recommended)

```bash
# SSH into GB10
ssh promaxgb10-41b1

# Pre-download the NVFP4 model (~70GB)
# This caches in ~/.cache/huggingface so vLLM finds it instantly on launch
pip install huggingface_hub hf_transfer --break-system-packages 2>/dev/null
HF_HUB_ENABLE_HF_TRANSFER=1 huggingface-cli download \
  lukealonso/MiniMax-M2.5-REAP-139B-A10B-NVFP4 \
  --local-dir-use-symlinks auto
```

### Option B: GGUF for llama.cpp (quick backup)

```bash
# Pre-download the GGUF model (~101GB, split into 4 shards)
HF_HUB_ENABLE_HF_TRANSFER=1 huggingface-cli download \
  unsloth/MiniMax-M2.5-GGUF \
  --include "*UD-Q3_K_XL*" \
  --local-dir ~/models/MiniMax-M2.5-GGUF
```

### Option C: Both (belt and braces)

Download both. They share no files, so there's no conflict. Total disk: ~170GB additional.
Your GB10 has plenty of NVMe space for this.

---

## Step 2: Verify llama.cpp is Built (for GGUF path only)

If you want the quick llama.cpp backup path, ensure llama.cpp is compiled with CUDA support:

```bash
ssh promaxgb10-41b1

# Check if llama-server exists
ls -la ~/llama.cpp/build/bin/llama-server

# If not, build it:
git clone https://github.com/ggml-org/llama.cpp.git ~/llama.cpp
cd ~/llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build -j$(nproc)

# Verify
./build/bin/llama-server --version
```

---

## Step 3: Test MiniMax M2.5

### Test A: vLLM NVFP4 path

```bash
# On GB10 (this will stop the current Qwen3 container)
./vllm-serve.sh minimax

# Wait 5-8 minutes, then from your Mac:
curl http://promaxgb10-41b1:8000/health
curl http://promaxgb10-41b1:8000/v1/models

# Test completion
curl http://promaxgb10-41b1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-6",
    "max_tokens": 200,
    "messages": [{"role": "user", "content": "Write a brief feature spec for a user authentication module. Include requirements, acceptance criteria, and edge cases."}]
  }'
```

The spec-writing prompt is deliberate — MiniMax M2.5 was trained with a "spec-writing tendency"
and should produce structured, architect-level output. If the response quality looks strong,
your backup is validated.

### Test B: llama.cpp GGUF path

```bash
# On GB10
./vllm-serve.sh minimax-gguf

# Wait 2-3 minutes (or longer on first download), then from Mac:
curl http://promaxgb10-41b1:8000/health

# Test completion (llama.cpp uses OpenAI format)
curl http://promaxgb10-41b1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-6",
    "max_tokens": 200,
    "messages": [{"role": "user", "content": "Write a brief feature spec for a user authentication module."}]
  }'
```

### Test C: AutoBuild with MiniMax

```bash
# From your Mac, with MiniMax serving on GB10:
ANTHROPIC_BASE_URL=http://promaxgb10-41b1:8000 \
ANTHROPIC_API_KEY=vllm-local-key \
guardkit autobuild task TASK-GLI-004 --verbose
```

If tool calling fails, check the troubleshooting section below.

### Don't forget: swap back to Qwen3 after testing

```bash
ssh promaxgb10-41b1
./vllm-serve.sh
```

---

## Step 4: Update the autobuild-vllm Wrapper (Optional)

If you're using the `autobuild-vllm` wrapper from the original guide, it already works
with MiniMax — same port, same endpoint. No changes needed.

For convenience, you might add a status check that shows which model is currently serving:

```bash
# Add to ~/.local/bin/autobuild-vllm, after the health check:
CURRENT_MODEL=$(curl -sf "${VLLM_URL}/v1/models" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('data', []):
    owned = m.get('owned_by', 'unknown')
    print(f\"{m['id']} (backend: {owned})\")
" 2>/dev/null || echo "unknown")
echo "AutoBuild → ${VLLM_URL} → ${CURRENT_MODEL}"
```

---

## Performance Expectations

| Preset | Model | Tok/s (gen) | Tok/s (prefill) | Context | Best For |
|--------|-------|-------------|-----------------|---------|----------|
| `next` (default) | Qwen3-Coder-Next FP8 | 30-43 | ~2,384 | 256K | AutoBuild implementation |
| `minimax` | MiniMax M2.5 NVFP4 | 17-30* | ~3,342 | 131K | Spec writing, planning, backup |
| `minimax-gguf` | MiniMax M2.5 GGUF Q3 | ~20 | ~26** | 16-32K | Quick emergency backup |
| `minimax-awq` | MiniMax M2.5 AWQ 4-bit | ~15 | ~1,089 | 65K | Stable fallback |

\* 17 tok/s with standard vLLM, ~30 tok/s expected with Avarok NVFP4-optimised image
\*\* llama.cpp prefill is per-request, not batched — lower throughput but adequate for single-user

### Benchmark Quality Comparison

| Benchmark | Qwen3-Coder-Next | MiniMax M2.5 | Notes |
|-----------|-------------------|--------------|-------|
| SWE-Bench Verified | 70%+ | 80.2% | MiniMax leads |
| SWE-Bench Pro | 44.3% | — | Qwen3 reported |
| Multi-SWE-Bench | — | 51.3% | MiniMax multi-repo strength |
| Active params | 3B | 10B | Qwen3 is 3x more efficient |

**Takeaway**: MiniMax is more capable per-request but slower. Perfect for planning/spec work
where quality matters more than iteration speed. Qwen3 is better for AutoBuild's rapid
Player-Coach turns where throughput compounds.

---

## Troubleshooting

### Tool calling failures with MiniMax

MiniMax uses a different tool calling format than Qwen3. The `minimax_m2` parser handles this
in vLLM. If you see malformed tool calls:

1. Check vLLM logs: `docker logs -f vllm-server`
2. Try the `minimax_m2_append_think` reasoning parser (already set in the preset)
3. The community noted that `minimax_m2` vs `minimax_m2_append_think` parser choice
   affects output — test both if you hit issues

### CUDA OOM on MiniMax NVFP4

The preset uses `--gpu-memory-utilization 0.85`. If OOM occurs:
```bash
VLLM_GPU_UTIL=0.80 ./vllm-serve.sh minimax
```
Community reports that 0.80 is stable for day-long coding sessions, while 0.85-0.90 can
cause OOM after extended use as the KV cache grows.

### Model name mismatch / 404 errors

All presets alias as `claude-sonnet-4-6`. Verify with:
```bash
curl http://promaxgb10-41b1:8000/v1/models | python3 -m json.tool
```
The `id` field should show `claude-sonnet-4-6` regardless of which model is actually serving.

### Slow first request

Normal — the prefix cache is cold. Subsequent requests with similar prompts will be
significantly faster (60-70% cache hit rate reported for Qwen3; expect similar for MiniMax).

### llama.cpp GGUF: AutoBuild format issues

llama.cpp serves OpenAI-compatible `/v1/chat/completions` but NOT the Anthropic Messages API
(`/v1/messages`). If AutoBuild specifically requires the Anthropic message format, the GGUF
path won't work — use the vLLM `minimax` preset instead, which translates the API format.

For standalone spec-writing (not through AutoBuild), the llama.cpp path works fine with any
OpenAI-compatible client.

---

## Community Resources

These are the key threads and tools from the DGX Spark developer community:

- **Spark Arena Leaderboard**: https://spark-arena.com/leaderboard
  Live benchmarks for models on GB10 hardware

- **spark-vllm-docker** (eugr): https://github.com/eugr/spark-vllm-docker
  Community-standard vLLM Docker images for the Spark

- **Avarok NVFP4 Docker** (tbraun96): https://github.com/Avarok-Cybersecurity/dgx-vllm
  20% faster NVFP4 via Marlin backend (stabilising, check before relying on it)

- **MiniMax M2.5 NVFP4 REAP thread**: https://forums.developer.nvidia.com/t/minimax-2-5-reap-nvfp4-on-single-dgx-spark/361248
  First single-Spark benchmarks and launch config

- **MiniMax M2.5 GGUF speedrun**: https://forums.developer.nvidia.com/t/minimax-2-5-on-dgx-spark-thanks-to-unsloth-https-unsloth-ai-docs-models-minimax-2-5/360663
  Step-by-step llama.cpp setup with benchmarks

- **NVFP4 unlock announcement**: https://forums.developer.nvidia.com/t/we-unlocked-nvfp4-on-the-dgx-spark-20-faster-than-awq/361163
  Avarok's breakthrough with Marlin MoE backend

- **FP4 scaling analysis**: https://forums.developer.nvidia.com/t/fp4-on-dgx-spark-why-it-doesnt-scale-like-youd-expect/360142
  109 replies — deep technical discussion on why NVFP4 performance was initially disappointing

---

## What This Doesn't Change

Your existing setup is **completely unaffected**:

- **Claude Code sessions** (VS Code, `claude` CLI) → still use Anthropic cloud API
- **Claude Desktop** → still uses Anthropic cloud API
- **AutoBuild default** (`./vllm-serve.sh` or `./vllm-serve.sh next`) → still Qwen3-Coder-Next
- **autobuild-vllm wrapper** → works with any model serving on port 8000

The MiniMax presets are **additive** — new options in the same script, activated only when
you explicitly choose them.
