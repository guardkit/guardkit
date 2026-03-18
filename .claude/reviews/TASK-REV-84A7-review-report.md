# Review Report: TASK-REV-84A7

## Executive Summary

The `guardkit graphiti add-context` command fails for 5 out of 11 documents when seeding the agentic-dataset-factory project. The root cause is a **fixed `max_tokens=16384` default** in graphiti-core's `OpenAIGenericClient`, which, combined with large input documents, exceeds the Qwen 2.5 model's 32768-token context window. The fix is straightforward: GuardKit already has a `llm_max_tokens` config field — it just needs a sensible default value set in `.guardkit/graphiti.yaml`.

**Root Cause Confidence: HIGH** — validated via source code analysis, run logs, and Docker container logs.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Task**: TASK-REV-84A7
- **Reviewer**: Manual source trace + log analysis

---

## Finding 1: Root Cause — Hardcoded `max_tokens=16384` in graphiti-core

### The Problem

When `guardkit graphiti add-context` processes a document, graphiti-core sends it to the vLLM endpoint for entity extraction. The `OpenAIGenericClient` class in graphiti-core sets `max_tokens=16384` by default:

**File**: `site-packages/graphiti_core/llm_client/openai_generic_client.py` (line 66)
```python
def __init__(self, ..., max_tokens: int = 16384):
```

The vLLM server runs Qwen 2.5 14B with `max_model_len=32768`. When a document's input tokens exceed `32768 - 16384 = 16384` tokens, vLLM rejects the request pre-flight:

```
ValueError: 'max_tokens' is too large: 16384.
This model's maximum context length is 32768 tokens
and your request has N input tokens (16384 > 32768 - N).
```

### Why Retries Don't Help

The graphiti-core retry logic (2 attempts) re-sends the **same parameters**, so retries always fail with the same error. Notably, input token counts increase slightly across retries (e.g., 18954 → 19098 → 19242), likely due to retry-related prompt additions.

### Success vs Failure Pattern

| Document | Input Tokens | Outcome | Headroom (32768 - input) |
|----------|-------------|---------|--------------------------|
| API-tools.md | <16384 | Success | >16384 |
| API-output.md | <16384 | Success | >16384 |
| DM-goal-schema.md | <16384 | Success | >16384 |
| DDR-001/002/003 | <16384 | Success | >16384 |
| DM-rejected-example.md | 16591 | **FAIL** | 16177 |
| DM-coach-rejection.md | 16765 | **FAIL** | 16003 |
| DM-agent-config.md | 17335 | **FAIL** | 15433 |
| DM-training-example.md | 17557 | **FAIL** | 15211 |
| API-entrypoint.md | 18954 | **FAIL** | 13814 |

The threshold is exactly **16384 input tokens** — any document exceeding this causes `input + max_tokens > 32768`.

## Finding 2: GuardKit Already Supports Override

GuardKit's `_build_llm_client()` in [graphiti_client.py:580-601](guardkit/knowledge/graphiti_client.py#L580-L601) already passes `max_tokens` through if configured:

```python
def _build_llm_client(self):
    kwargs = {}
    if self.config.llm_max_tokens is not None:
        kwargs["max_tokens"] = self.config.llm_max_tokens
    return OpenAIGenericClient(config=..., **kwargs)
```

The config field exists in [config.py:102](guardkit/knowledge/config.py#L102):
```python
llm_max_tokens: Optional[int] = None  # Cap output tokens
```

But `.guardkit/graphiti.yaml` does **not set `llm_max_tokens`**, so it defaults to `None`, which means graphiti-core's 16384 default takes effect.

## Finding 3: Docker Log Analysis

The Docker logs confirm:

1. **vLLM configuration**: `max_model_len=32768`, `gpu_memory_utilization=0.4`, model `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic`
2. **Error location**: vLLM's `serving_engine.py:1028` `_validate_input()` raises `ValueError` before any GPU processing — this is a pre-flight check
3. **No GPU/memory issues**: KV cache usage peaks at ~4.5%, well within capacity. The errors are purely parameter validation failures
4. **Successful requests processed fine**: Before the errors, requests with <16384 input tokens completed normally with ~9.8 tokens/s generation throughput

## Finding 4: Additional Hardcoded Value in graphiti-core

`graphiti_core/utils/maintenance/edge_operations.py` (line 104) also hardcodes `extract_edges_max_tokens = 16384`. This could cause identical failures during edge extraction operations on large documents, even if the main client's max_tokens is reduced.

---

## Mitigation Options

### Option A: Set `llm_max_tokens` in Config (Recommended)

**Change**: Add `llm_max_tokens: 4096` to `.guardkit/graphiti.yaml`

```yaml
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic
llm_max_tokens: 4096  # Safe for 32K context: leaves 28K for input
```

| Pros | Cons |
|------|------|
| Zero code changes needed | Static value — doesn't adapt to input size |
| Immediate fix (config only) | 4096 may be insufficient for very complex extractions |
| Already supported by GuardKit | Doesn't fix edge_operations.py hardcoded value |
| Trivially reversible | |

**Max safe input**: 32768 - 4096 = **28672 tokens** (covers all failing documents).

### Option B: Dynamic `max_tokens` Calculation in GuardKit

**Change**: Modify `_build_llm_client()` or add a wrapper that calculates `max_tokens` per request based on input token count.

```python
# Conceptual: dynamic calculation
max_tokens = min(16384, context_window - input_tokens - buffer)
```

| Pros | Cons |
|------|------|
| Adapts to any document size | Requires code change in GuardKit |
| Maximises output quality | Needs access to token count before LLM call |
| Handles edge cases automatically | graphiti-core doesn't expose per-request max_tokens override |
| Future-proof | Would need to monkey-patch or fork OpenAIGenericClient |

**Complexity**: High — graphiti-core's `OpenAIGenericClient` sets `max_tokens` at init time, not per-request. Would require either a PR to graphiti-core or a monkey-patch.

### Option C: Document Chunking

**Change**: Use GuardKit's existing `llm_chunk_threshold` config to split large documents before sending to Graphiti.

```yaml
llm_chunk_threshold: 12000  # Bytes; splits docs above this into chunks
```

| Pros | Cons |
|------|------|
| Already partially implemented in GuardKit | Chunks may lose cross-section context |
| Reduces token count per request | Increases number of LLM calls |
| Works regardless of max_tokens setting | May produce fragmented knowledge graph entities |

### Option D: Increase Model Context Window

**Change**: Switch to a model with larger context (e.g., Qwen 2.5 with 128K context) or increase `max_model_len` in vLLM config.

| Pros | Cons |
|------|------|
| Removes the constraint entirely | Larger models need more GPU memory |
| No code or config changes to GuardKit | Qwen 2.5 14B native context is 32K (128K requires RoPE scaling) |
| Better for future large documents | May reduce quality at extended context lengths |
| | Requires container restart and testing |

---

## Recommendation

**Implement Option A immediately** (config change, 30 seconds), then consider **Option B as a follow-up** (upstream PR or GuardKit enhancement).

### Rationale

1. Option A fixes 100% of currently failing documents with zero risk
2. `4096` output tokens is generous for entity extraction (graphiti-core's prompts typically need <2K output tokens)
3. The `llm_max_tokens` config path is already tested and production-ready
4. Option B is the ideal long-term solution but requires either a graphiti-core PR or significant monkey-patching

### Immediate Action

Add one line to `.guardkit/graphiti.yaml`:

```yaml
llm_max_tokens: 4096
```

Then re-run the 5 failing commands.

---

## Appendix: Token Budget Analysis

| Component | Tokens |
|-----------|--------|
| Model context window | 32768 |
| Largest failing input (API-entrypoint.md) | 18954 |
| Required max_tokens for success | ≤13814 |
| Recommended max_tokens | 4096 |
| Safety margin at 4096 | 28672 - 18954 = **9718 tokens** |

With `max_tokens: 4096`, even the largest document (18954 input tokens) has 9718 tokens of headroom — a 50% safety margin.
