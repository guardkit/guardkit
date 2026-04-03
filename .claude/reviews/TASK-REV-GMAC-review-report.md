# Review Report: TASK-REV-GMAC

## Executive Summary

Offloading the Graphiti LLM to the MacBook Pro M2 Max is **feasible and recommended** during GB10 dataset generation runs. After deep investigation into MLX-based options (mlx-omni-server, vllm-mlx, Ollama 0.19 MLX, LM Studio MLX), the best option remains **Ollama (GGUF backend)** or **llama-server** with Qwen2.5-14B Q4_K_M.

**Key insight from MLX deep-dive**: MLX's advertised speed advantage (50-87% faster decode) is **misleading for Graphiti's workload**. Graphiti sends ~8K token prompts and expects short JSON output — a prefill-dominated pattern where GGUF/llama.cpp actually outperforms MLX in real-world wall-clock time (see Finding 1, Option C).

**Recommendation**: Ollama (GGUF) with Q4_K_M quant, ~15-20 tok/s effective, ~8-10GB memory footprint. Fall back to llama-server if json_schema enforcement is needed.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Task**: Investigate running Graphiti LLM on MacBook Pro M2 Max to unblock GB10 dataset runs
- **Complexity**: 4/10

---

## Finding 1: Serving Option Analysis

### Option A: Ollama (RECOMMENDED)

| Criterion | Assessment |
|-----------|------------|
| Setup complexity | Trivial — `brew install ollama && ollama pull qwen2.5:14b-instruct-q4_K_M` |
| Metal support | First-class, auto-detected |
| OpenAI-compatible API | Yes, `/v1/chat/completions` endpoint |
| JSON schema enforcement | **Partial** — supports `format` parameter with JSON schema directly, but does NOT support OpenAI's `response_format: {type: "json_schema", json_schema: {...}}` syntax ([Issue #10001](https://github.com/ollama/ollama/issues/10001)) |
| Graphiti compatibility | Requires testing — Graphiti sends `response_format=json_schema` via OpenAI SDK. Ollama's OpenAI-compat layer may need the schema passed via `format` instead |
| Performance (M2 Max) | ~15-25 tok/s for 14B Q4_K_M |
| Memory | ~8-10GB for Q4_K_M |
| Stability | Production-grade, widely used |

**Key risk**: Graphiti uses OpenAI SDK with `response_format={"type": "json_schema", ...}`. Ollama's OpenAI compatibility layer may silently ignore this format. Need to test whether Ollama's native `format` parameter is used instead when called via OpenAI SDK's chat completions endpoint.

**Mitigation**: If Ollama ignores `json_schema` response_format, two options:
1. Test if Ollama still produces valid JSON (many models do with good prompting)
2. Fall back to llama.cpp which has explicit grammar enforcement

### Option B: llama.cpp (llama-server)

| Criterion | Assessment |
|-----------|------------|
| Setup complexity | Moderate — build from source or Homebrew, manual model download |
| Metal support | First-class (ARM NEON + Metal) |
| OpenAI-compatible API | Yes, built-in server mode |
| JSON schema enforcement | **Full** — `json_schema` parameter with GBNF grammar-based enforcement at token level |
| Graphiti compatibility | Good — supports `/v1/chat/completions` with grammar constraints |
| Performance (M2 Max) | ~15-25 tok/s for 14B Q4_K_M |
| Memory | ~8-10GB for Q4_K_M |
| Stability | Stable but requires manual management (no auto-restart, no model management) |

**Advantage**: Grammar-based JSON enforcement at token level — closest equivalent to vLLM's xgrammar. If Graphiti's `response_format` is passed through, llama-server will enforce it.

**Disadvantage**: More operational overhead (no model versioning, manual process management).

### Option C: MLX-based servers (DEEP DIVE — Revised)

There are now **four** MLX-based serving options. After deep investigation, MLX's theoretical speed advantage is **misleading for Graphiti's workload profile**.

#### C1: mlx-omni-server

| Criterion | Assessment |
|-----------|------------|
| Setup complexity | Moderate — `pip install mlx-omni-server` |
| Metal support | Native MLX framework |
| OpenAI-compatible API | Yes, plus Anthropic SDK compatibility |
| JSON schema enforcement | Via [Outlines](https://github.com/outlines-dev/outlines) library — converts JSON schema to regex, masks logits |
| Graphiti compatibility | Untested — uses Outlines rather than grammar/xgrammar approach |
| Performance (M2 Max) | ~20-30 tok/s decode, but see **prefill caveat** below |
| Model availability | [mlx-community/Qwen2.5-14B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-14B-Instruct-4bit) and [8bit](https://huggingface.co/mlx-community/Qwen2.5-14B-Instruct-8bit) available on HuggingFace |
| Stability | v0.5.2 (Dec 2025) — newer, less battle-tested |

#### C2: vllm-mlx

| Criterion | Assessment |
|-----------|------------|
| Setup complexity | Moderate — `pip install git+https://github.com/waybarrios/vllm-mlx.git` |
| Metal support | Native MLX framework |
| OpenAI-compatible API | Yes, plus Anthropic SDK compatibility, MCP tool calling |
| JSON schema enforcement | **Not explicitly documented** — README does not mention structured output or json_schema |
| Graphiti compatibility | **Uncertain** — no evidence of json_schema support |
| Performance (M2 Max) | Claims 400+ tok/s (smaller models), continuous batching supported |
| Model availability | Examples show Qwen3 models, **not Qwen2.5** |
| Stability | Active development, community-driven |

#### C3: Ollama 0.19 MLX backend (NEW — March 2026)

| Criterion | Assessment |
|-----------|------------|
| Setup complexity | Trivial — same as regular Ollama, MLX auto-enabled |
| Metal support | Native MLX via Ollama |
| Performance | 1,810 tok/s prefill, 112 tok/s decode (on M5 — benchmarked with Qwen3.5-35B) |
| Model availability | **Only Qwen3.5 supported currently** — Qwen2.5 NOT in supported architecture list |
| Requirements | >32GB unified memory |
| Stability | Preview release |

**Verdict on C3**: Not viable yet for Qwen2.5-14B — architecture not supported. Worth revisiting when Ollama expands MLX model support.

#### C4: LM Studio (MLX backend)

| Criterion | Assessment |
|-----------|------------|
| Setup complexity | Trivial — GUI app with model browser |
| JSON schema enforcement | [Full OpenAI-compatible structured output](https://lmstudio.ai/docs/developer/openai-compat/structured-output) |
| Model availability | Qwen2.5-14B in both MLX-4bit and MLX-8bit formats |
| Stability | Production-grade GUI, well-tested |

**Verdict on C4**: Strong contender if GUI/app approach is acceptable. Has the best json_schema support of all MLX options.

---

#### CRITICAL FINDING: MLX decode speed is misleading for Graphiti's workload

Research from [famstack.dev](https://famstack.dev/guides/mlx-vs-gguf-apple-silicon/) reveals that **MLX's reported tok/s only measures decode (generation) speed, not prefill (prompt processing)**. For Graphiti, this distinction is critical:

**Graphiti's workload profile:**
- System prompts: ~7,800-8,100 tokens (long prefill)
- Output: Short JSON entity extraction (short decode)
- Pattern: Long input → short output

**Real-world benchmark data (M1 Max, Qwen3.5-35B-A3B):**

| Context Length | MLX Reported | MLX Effective | GGUF Effective |
|---------------|-------------|--------------|----------------|
| 655 tokens | 59 tok/s | 13 tok/s | 16 tok/s |
| 8,500 tokens | 51 tok/s | **3 tok/s** | ~7 tok/s |

At 8,500 tokens of context (close to Graphiti's ~8K system prompt), **MLX spent 94% of total time on prefill**, making the "57 tok/s decode" number irrelevant. GGUF completed the same task faster.

**Why this happens**: MLX optimizes for Metal GPU throughput during decode, but its prefill implementation is slower than llama.cpp's FlashAttention-based approach. For long-prompt, short-output workloads, prefill dominates wall-clock time.

**Bottom line for Graphiti**: GGUF via Ollama or llama-server will deliver **better real-world performance** than MLX for entity extraction tasks, despite MLX reporting higher tok/s numbers.

**Caveat**: The oMLX project claims 5x faster prefill via tiered KV caching. If mlx-omni-server or vllm-mlx adopt similar optimizations, the calculus could change. But as of April 2026, GGUF remains the pragmatic choice for this workload.

### Option D: vLLM on Mac

**Not viable.** vLLM requires CUDA and does not run on Apple Silicon. Confirmed by the codebase — all vLLM scripts use Docker with `--gpus all` targeting NVIDIA hardware.

---

## Finding 2: Model Quant Selection

| Quant | Size | Memory | Quality | Recommendation |
|-------|------|--------|---------|----------------|
| Q4_K_M | ~8.5GB | ~10GB loaded | Good — minimal quality loss for entity extraction | **Start here** |
| Q5_K_M | ~10.5GB | ~12GB loaded | Better — marginal improvement over Q4 | Upgrade if Q4 misses entities |
| Q8_0 | ~15.5GB | ~18GB loaded | Near-FP16 | Only if memory allows and quality matters |
| FP16 | ~28GB | ~32GB loaded | Reference quality | Too large for comfortable co-hosting |

**Recommendation**: Start with **Q4_K_M**. Graphiti's entity extraction is a structured task (extracting names, relationships from text) — Q4_K_M handles this well. The quality difference between Q4_K_M and FP8 (current GB10 setup) is minimal for extraction tasks. Upgrade to Q5_K_M only if testing reveals missed entities.

---

## Finding 3: Graphiti Configuration — Split Endpoints Already Supported

The existing configuration architecture **already supports split endpoints**. LLM and embedding have separate URL configurations:

### Current config (`.guardkit/graphiti.yaml`):
```yaml
llm_base_url: http://promaxgb10-41b1:8000/v1     # LLM
embedding_base_url: http://promaxgb10-41b1:8001/v1 # Embedding
```

### Current MCP config (`.mcp.json`):
```json
"env": {
  "LLM_API_URL": "http://promaxgb10-41b1:8000/v1",
  "EMBEDDING_API_URL": "http://promaxgb10-41b1:8001/v1"
}
```

### Graphiti MCP server config (`config-guardkit.yaml`):
```yaml
llm:
  providers:
    openai:
      api_url: ${LLM_API_URL:http://promaxgb10-41b1:8000/v1}
embedder:
  providers:
    openai:
      api_url: ${EMBEDDING_API_URL:http://promaxgb10-41b1:8001/v1}
```

**These are already separate.** To point the LLM at MacBook while keeping embeddings on GB10, change only:

1. `.mcp.json` → `LLM_API_URL` to MacBook's Tailscale/LAN IP
2. `.guardkit/graphiti.yaml` → `llm_base_url` to MacBook's IP
3. Optionally: change `llm_model` if using a different model name on Ollama

The embedding model stays on GB10 (port 8001) — no change needed.

---

## Finding 4: Network Considerations

Both machines are on the same Tailscale network (confirmed: GB10 hostname `promaxgb10-41b1` is a Tailscale name). The MacBook should also be accessible via Tailscale.

| Concern | Assessment |
|---------|------------|
| Latency | 1-2ms over Tailscale/LAN — negligible vs 500ms+ per LLM inference |
| Firewall | macOS may block incoming connections — need to allow Ollama's port (default 11434) or configure a custom port |
| Reliability | Tailscale maintains persistent connections — no issue |
| Port | Ollama defaults to 11434, not 8000. Either configure `OLLAMA_HOST=0.0.0.0:8000` or update Graphiti config to use 11434 |

**Action**: Set `OLLAMA_HOST=0.0.0.0:8000` when starting Ollama on MacBook to match the existing port expectation, OR update configs to use port 11434.

---

## Finding 5: Performance Expectations

| Metric | GB10 (current) | MacBook M2 Max (expected) | Impact |
|--------|---------------|--------------------------|--------|
| Throughput | ~40 tok/s (FP8, vLLM) | ~15-25 tok/s (Q4_K_M, Ollama) | 2-3x slower |
| TTFT | 2-3s (with prefix caching) | 5-10s (no prefix caching) | Higher latency on first token |
| Episode processing | ~30-60s per episode | ~60-120s per episode | Acceptable for interactive use |
| Concurrent requests | High (vLLM batching) | Low (Ollama serial) | Fine — Graphiti is sequential |

**Assessment**: The MacBook will be 2-3x slower than GB10 for Graphiti operations, but this is entirely acceptable because:
- Graphiti ingestion is not latency-critical (it's a background knowledge capture operation)
- The bottleneck is entity extraction quality, not speed
- No prefix caching available, but episode processing still completes within timeout
- Graphiti processes episodes sequentially — no need for concurrent request handling

---

## Finding 6: Memory Budget on MacBook

| Component | Memory |
|-----------|--------|
| macOS + system | ~8-10GB |
| VS Code + extensions | ~4-6GB |
| Claude Code | ~2-3GB |
| Browsers (reduced tabs) | ~4-8GB |
| Qwen2.5-14B Q4_K_M via Ollama | ~10GB |
| **Total estimated** | **~28-37GB** |
| **Available (96GB)** | **~59-68GB free** |

**Verdict**: Comfortable. Even with normal IDE + browser load, Q4_K_M fits easily within the 96GB budget. No need to close browsers unless running Q8_0 or larger models.

---

## Finding 7: Ollama json_schema Compatibility Risk

This is the **highest-risk item**. Graphiti's codebase sends requests via the OpenAI Python SDK with `response_format={"type": "json_schema", "json_schema": {...}}`. Ollama's OpenAI compatibility layer has a [known gap](https://github.com/ollama/ollama/issues/10001) where this exact format may be ignored.

**Workarounds (in priority order)**:

1. **Test first**: Ollama may handle the `json_schema` format correctly in newer versions — the issue was filed March 2025 and may have been resolved
2. **Ollama native format**: Ollama supports structured output via its native `format` parameter with a JSON schema. If using the OpenAI SDK, this would require patching how Graphiti constructs its requests (not ideal)
3. **llama-server fallback**: llama.cpp's server has full grammar-based JSON schema enforcement and accepts the standard OpenAI `response_format` — drop-in compatible
4. **LM Studio**: An alternative that wraps llama.cpp/MLX with full OpenAI-compatible structured output support, including `json_schema` response_format

---

## Decision Matrix (Revised after MLX deep-dive)

Weighting reflects Graphiti's actual needs: json_schema enforcement is critical, and "performance" now accounts for the prefill-dominated workload (not raw decode tok/s).

| Criterion (weight) | Ollama (GGUF) | llama-server | mlx-omni-server | LM Studio (MLX) | vllm-mlx |
|---------------------|--------------|-------------|-----------------|-----------------|----------|
| Setup ease (20%) | 10 | 6 | 7 | 9 | 7 |
| json_schema support (30%) | 6* | 9 | 7 | 8 | 3** |
| Real-world perf for Graphiti (20%) | 8 | 8 | 5*** | 6*** | 5*** |
| Stability (15%) | 9 | 8 | 5 | 7 | 4 |
| Maintenance (15%) | 9 | 6 | 6 | 8 | 5 |
| **Weighted Score** | **8.1** | **7.7** | **6.0** | **7.6** | **4.6** |

\* Ollama json_schema score pending testing — could be 9 if recent versions fixed the compatibility gap.
\** vllm-mlx has no documented json_schema/structured output support.
\*** MLX-based options penalized for prefill-dominated workload (Graphiti sends ~8K token prompts, expects short JSON output). See Finding 1, Option C critical finding.

---

## Recommendations

### Primary: Try Ollama first, fall back to llama-server

1. **Install Ollama on MacBook**: `brew install ollama`
2. **Pull model**: `ollama pull qwen2.5:14b-instruct-q4_K_M`
3. **Start with port 8000**: `OLLAMA_HOST=0.0.0.0:8000 ollama serve`
4. **Test json_schema**: Send a test request mimicking Graphiti's `response_format` parameter
5. **If json_schema works**: Update `.mcp.json` and `.guardkit/graphiti.yaml` with MacBook IP
6. **If json_schema fails**: Switch to `llama-server` with `--grammar` support

### Configuration Changes (2 files)

**`.mcp.json`** — change `LLM_API_URL`:
```json
"LLM_API_URL": "http://<macbook-tailscale-ip>:8000/v1"
```

**`.guardkit/graphiti.yaml`** — change `llm_base_url`:
```yaml
llm_base_url: http://<macbook-tailscale-ip>:8000/v1
llm_model: qwen2.5:14b-instruct-q4_K_M  # Ollama model name format
```

### Env var switching (for easy toggle)

Create a simple toggle script:
```bash
# graphiti-macbook.sh — Point Graphiti LLM at MacBook
export LLM_API_URL="http://<macbook-ip>:8000/v1"

# graphiti-gb10.sh — Point Graphiti LLM back at GB10
export LLM_API_URL="http://promaxgb10-41b1:8000/v1"
```

The MCP server config already uses `${LLM_API_URL:...}` env var with fallback, so this works out of the box.

### Testing Protocol

1. Start Ollama on MacBook with the model
2. Run `curl http://<macbook-ip>:8000/v1/models` to verify connectivity
3. Send a structured output test: `curl -X POST http://<macbook-ip>:8000/v1/chat/completions -d '{"model":"qwen2.5:14b-instruct-q4_K_M","messages":[{"role":"user","content":"Extract the person name from: John Smith went to the store"}],"response_format":{"type":"json_schema","json_schema":{"name":"entity","schema":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}}}}'`
4. If step 3 returns valid JSON matching schema → proceed with Graphiti test
5. Run `guardkit graphiti add-context --inline --content "Test episode from MacBook-hosted LLM"` to verify end-to-end

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ollama ignores json_schema format | Medium | High | Fall back to llama-server |
| Model quality too low at Q4 | Low | Medium | Upgrade to Q5_K_M or Q8_0 |
| MacBook memory pressure | Low | Low | 96GB provides ample headroom |
| Network issues | Low | Low | Tailscale is reliable |
| Ollama port conflict | Low | Low | Configure OLLAMA_HOST |

---

## Appendix A: MLX Model Availability for Qwen2.5-14B

Models confirmed available on HuggingFace:

| Model | Format | Size | Source |
|-------|--------|------|--------|
| [mlx-community/Qwen2.5-14B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-14B-Instruct-4bit) | MLX 4-bit | ~8.5GB | mlx-community |
| [mlx-community/Qwen2.5-14B-Instruct-8bit](https://huggingface.co/mlx-community/Qwen2.5-14B-Instruct-8bit) | MLX 8-bit | ~16GB | mlx-community |
| [mlx-community/Qwen2.5-14B-Instruct-1M-6bit](https://huggingface.co/mlx-community/Qwen2.5-14B-Instruct-1M-6bit) | MLX 6-bit (1M ctx) | ~12GB | mlx-community |
| [lmstudio-community/Qwen2.5-14B-Instruct-MLX-4bit](https://huggingface.co/lmstudio-community/Qwen2.5-14B-Instruct-MLX-4bit) | MLX 4-bit | ~8.5GB | LM Studio |

If MLX is ever needed (e.g., oMLX prefill improvements materialize), model availability is not a blocker.

## Appendix B: When to Revisit MLX

MLX would become the better choice if:
1. **oMLX tiered KV caching** (5x prefill speedup) is adopted by mlx-omni-server or vllm-mlx
2. **Ollama 0.19 MLX backend** expands to support Qwen2.5 architecture
3. Graphiti's workload shifts to longer outputs (unlikely for entity extraction)

## Appendix C: Sources

- [Ollama Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama json_schema compatibility issue #10001](https://github.com/ollama/ollama/issues/10001)
- [Ollama MLX Preview (March 2026)](https://ollama.com/blog/mlx)
- [llama.cpp Grammar & Structured Output](https://deepwiki.com/ggml-org/llama.cpp/8.1-grammar-and-structured-output)
- [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [mlx-omni-server](https://github.com/madroidmaq/mlx-omni-server)
- [vllm-mlx](https://github.com/waybarrios/vllm-mlx)
- [LM Studio Structured Output](https://lmstudio.ai/docs/developer/openai-compat/structured-output)
- [MLX vs GGUF real-world performance (famstack.dev)](https://famstack.dev/guides/mlx-vs-gguf-apple-silicon/) — critical prefill vs decode analysis
- [MLX vs llama.cpp comparison (Groundy)](https://groundy.com/articles/mlx-vs-llamacpp-on-apple-silicon-which-runtime-to-use-for-local-llm-inference/)
- [MLX: The Next Inference Engine for Apple Silicon (yage.ai)](https://yage.ai/share/mlx-apple-silicon-en-20260331.html)
- [Qwen2.5-14B-Instruct-4bit MLX (HuggingFace)](https://huggingface.co/mlx-community/Qwen2.5-14B-Instruct-4bit)
- [Qwen2.5-14B-Instruct-8bit MLX (HuggingFace)](https://huggingface.co/mlx-community/Qwen2.5-14B-Instruct-8bit)
