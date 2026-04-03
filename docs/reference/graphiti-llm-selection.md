# Graphiti LLM Selection — Learnings from TASK-REV-DGX1

Findings from selecting and testing LLMs for Graphiti knowledge graph ingestion on
DGX Spark GB10. These learnings apply to any project using Graphiti with local
models via vLLM.

**Task**: TASK-REV-DGX1 | **Date**: 2026-03-18 | **Hardware**: DGX Spark GB10 (128GB unified, SM 12.1, ARM64)

---

## TL;DR

Use `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic` with `--structured-outputs-config.backend xgrammar`.
Avoid Qwen3 (thinking mode wastes tokens). Avoid Nemotron 3 Nano (8K context too small).
Graphiti requires `response_format=json_schema` — xgrammar enforces this at the token level.

---

## 1. Graphiti's Hard Requirements

Graphiti's `OpenAIGenericClient` sends:
```python
response_format = {
    "type": "json_schema",
    "json_schema": {"name": "...", "schema": {...}}  # Pydantic model schema
}
```

This means the LLM + serving layer **must enforce JSON schema compliance**, not just
prompt the model to output JSON. Without enforcement, models return invalid schemas
and ingestion fails — exactly as Graphiti's own README warns:

> "Graphiti works best with LLM services that support Structured Output (such as
> OpenAI and Gemini). Using other services may result in incorrect output schemas
> and ingestion failures."

### What this means for vLLM

vLLM supports `json_schema` response format via guided/constrained decoding backends.
In vLLM v0.13+ (NGC `26.01-py3` image), the flag is:

```
--structured-outputs-config.backend xgrammar
```

The old `--guided-decoding-backend` flag was removed in vLLM v0.12. If using vLLM
v0.6–v0.11, use `--guided-decoding-backend xgrammar` instead.

`auto` mode also selects xgrammar by default, but explicit is better for
correctness-critical workloads like Graphiti.

---

## 2. Context Window Requirement

Graphiti's entity extraction system prompts consume **~7800–8100 input tokens** of
baseline overhead (graph context + extraction schema + few-shot examples). Any
document content is added on top.

**Minimum context**: >10K tokens (practically >=16K for useful document ingestion).

This eliminates all Nemotron 3 Nano variants (4B, 30B-A3B) — they have **8192-token
context windows** which overflow before any document content is included.

---

## 3. Why Qwen3 Models Are Wrong for Graphiti

### The thinking mode problem

All Qwen3 models (8B, 14B, 30B-A3B) have a built-in thinking mode that generates
`<think>...</think>` blocks before each response. This happens by default.

**Observed behaviour** (Qwen3-30B-A3B-FP8, run-3 log):
- First request: ~4 minutes for a 6KB document, generating ~8000 output tokens
- Graphiti extraction response should be ~500 tokens of JSON
- The other ~7500 tokens were thinking — invisible to the client but still generated
- At 5 concurrent requests, KV cache grew from 12% to 30% over 10 minutes
- 900s timeout fired because later episodes with larger docs never completed

### Why `--reasoning-parser qwen3` doesn't fix it

This flag strips `<think>` blocks from the **response** before returning it to the
client. But the model still **generates every thinking token internally** — the GPU
time and KV cache are consumed regardless. The client just doesn't see them.

### Why `llm_max_tokens` doesn't fix it

Setting `llm_max_tokens: 2048` (GuardKit config) caps the total output at 2048
tokens. But if the model is mid-think at token 2048, the JSON response is truncated
and Graphiti gets a broken extraction. It's a band-aid that causes different failures.

### The non-thinking jinja workaround

Qwen publishes `qwen3_nonthinking.jinja` which completely disables thinking at the
server level via `--chat-template ./qwen3_nonthinking.jinja`. This eliminates
thinking tokens entirely. However, it requires downloading the template, mounting it
into the container, and removing `--reasoning-parser qwen3`. It works but adds
complexity — using a non-thinking model is simpler.

---

## 4. Why gpt-oss-20b Doesn't Work on GB10

OpenAI's `gpt-oss` models (used in Graphiti's own MCP server examples) are the
ideal choice architecturally — native structured output, no thinking mode, 128K
context, purpose-built for extraction tasks.

However, `gpt-oss-20b` on GB10 is blocked by three issues:

| Issue | Detail |
|-------|--------|
| No ARM64 wheel | OpenAI's custom vLLM fork (`vllm==0.10.1+gptoss`) ships x86_64 only |
| MXFP4 broken on Blackwell | SM 12.1 Marlin kernel produces wrong output tokens (vLLM issue #37030) |
| BF16 workaround is 42GB | Bypasses MXFP4 but large footprint |

Building the gptoss fork from source for ARM64 is theoretically possible but not
worth the effort when Qwen2.5-14B works well.

---

## 5. The Winning Model: Qwen2.5-14B-Instruct-FP8

| Attribute | Value |
|-----------|-------|
| HuggingFace ID | `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic` |
| Architecture | Dense, 14.8B parameters |
| Context window | 128K tokens native |
| FP8 memory | ~16 GB weights |
| Thinking mode | None — pure instruct |
| JSON quality | Excellent — Qwen2.5 has explicit structured data training |
| GB10 compatibility | Standard NGC vLLM image, no special flags |

**Why not `Qwen/Qwen2.5-14B-Instruct-FP8`?** That repo ID doesn't exist on
HuggingFace — the official Qwen org only publishes BF16. FP8 checkpoints are
published by `neuralmagic/` and `RedHatAI/` as community quantisations.

### Fallback: Qwen2.5-32B

`neuralmagic/Qwen2.5-32B-Instruct-FP8-dynamic` (~34 GB) if the 14B misses
entities on complex documents. Same flags, just more memory.

---

## 6. vLLM Configuration for Graphiti on GB10

### Working config (vLLM 0.13.0, NGC 26.01-py3)

```bash
vllm serve neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic \
  --host 0.0.0.0 --port 8000 \
  --gpu-memory-utilization 0.40 \
  --max-model-len 32768 \
  --dtype auto \
  --kv-cache-dtype fp8 \
  --enable-prefix-caching \
  --structured-outputs-config.backend xgrammar
```

### Flag rationale

| Flag | Why |
|------|-----|
| `--structured-outputs-config.backend xgrammar` | Enforces json_schema at token level — Graphiti requires this |
| `--enable-prefix-caching` | Graphiti sends identical system prompts repeatedly; caching cuts TTFT from ~28s to 2-3s |
| `--kv-cache-dtype fp8` | Reduces KV cache memory footprint |
| `--max-model-len 32768` | 32K is sufficient; larger values waste KV cache memory |
| `--gpu-memory-utilization 0.40` | ~51GB allocation — leaves headroom for embed + AutoBuild models |

### Flags NOT needed for Qwen2.5

| Flag | Why not |
|------|---------|
| `--reasoning-parser` | No thinking mode to strip |
| `--trust-remote-code` | Qwen2.5 architecture is natively supported |
| `--tensor-parallel-size` | 14B fits on a single GPU easily |
| `VLLM_FLASHINFER_MOE_BACKEND` | Not an MoE model |
| `--load-format fastsafetensors` | Not needed for standard HF checkpoint |

---

## 7. vLLM Version Gotchas

| Issue | Detail | Fix |
|-------|--------|-----|
| `--guided-decoding-backend` rejected | Flag removed in vLLM v0.12 | Use `--structured-outputs-config.backend` (v0.13+) |
| `Qwen/Qwen2.5-14B-Instruct-FP8` 401 error | Repo doesn't exist under `Qwen/` org | Use `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic` |
| `trust_remote_code` ignored warning | vLLM prints "has no effect here and is ignored" | Safe to remove for Qwen2.5 |

---

## 8. NVFP4 on GB10 — Don't Use It (Yet)

NVFP4 quantisation on GB10 ARM64 is currently unreliable:
- vLLM bug #35519: Qwen3.5 NVFP4 crashes on ARM64
- In benchmarks, NVFP4 is slower than AWQ on SM 12.1 (35.58 vs 42.11 tok/s)
- Requires patched Docker images (avarok/dgx-vllm-nvfp4-kernel:v23)
- Active vLLM PRs (#35568, #35693, #35947) and CUTLASS (#3038) for fixes

Stick with FP8 for production workloads.

---

## 9. Models Evaluated and Eliminated

| Model | Context | Why eliminated |
|-------|---------|---------------|
| Nemotron 3 Nano 4B FP8 | 8K | Context overflow — prompts alone exceed 8192 tokens |
| Nemotron 3 Nano 30B-A3B FP8 | 8K | Same 8192-token limit as 4B variant |
| Nemotron 3 Super 120B NVFP4 | 262K | ~69 GB model + ~16 tok/s — too large, too slow |
| Qwen3-30B-A3B-FP8 | 32K | Thinking mode: 900s+ timeouts from internal `<think>` generation |
| Qwen3-14B-FP8 | 32K | Same thinking mode problem as Qwen3-30B |
| Qwen3-Coder-Next | 32K | >600s per episode — poor structured JSON for non-code tasks |
| gpt-oss-20b | 128K | No ARM64 wheel; MXFP4 broken on Blackwell SM 12.1 |
| gpt-oss-120b | 128K | ~99 GB RAM; Marlin race condition at TP=1 on SM 12.1 |
| Mistral-Small-4-119B NVFP4 | 40K | ~99 GB RAM; MLA backend fails on SM 12.1; ~27 tok/s |
| Mistral-Nemo-12B | 128K | No GB10 benchmarks; unvalidated on ARM64 |
| Llama 3.1 8B | 128K | Inferior JSON quality vs Qwen2.5; no GB10 community data |

---

## 10. GB10 Port Allocation

| Port | Service | Model | Memory |
|------|---------|-------|--------|
| 8000 | Graphiti LLM | `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic` | ~51 GB (0.40 util) |
| 8001 | Embeddings | `nomic-embed-text-v1.5` | ~0.5 GB |
| 8002 | AutoBuild LLM | `Qwen3-Coder-Next` | ~32–45 GB |
| 8003 | Nemotron 3 Nano | `nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8` | ~4 GB |

Total with ports 8000+8001+8002: ~84–97 GB of 128 GB unified memory.

---

## 11. Key Resources

| Resource | URL |
|----------|-----|
| NVIDIA GB10 forum | https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/721 |
| Qwen3.5-35B-A3B thread | https://forums.developer.nvidia.com/t/362200 |
| NVFP4 PSA thread | https://forums.developer.nvidia.com/t/353069 |
| spark-vllm-docker | https://github.com/eugr/spark-vllm-docker |
| Graphiti structured output warning | https://github.com/getzep/graphiti |
| Graphiti MCP server (gpt-oss example) | https://github.com/getzep/graphiti/blob/main/mcp_server/README.md |
| vLLM structured outputs docs | https://docs.vllm.ai/en/latest/ |
| Review report | `.claude/reviews/TASK-REV-DGX1-review-report.md` |
| Serving script | `scripts/vllm-graphiti.sh` |
| Config | `.guardkit/graphiti.yaml` |
