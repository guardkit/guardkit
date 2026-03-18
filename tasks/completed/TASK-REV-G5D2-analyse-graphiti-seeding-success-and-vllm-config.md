---
id: TASK-REV-G5D2
title: Analyse Graphiti seeding success and vLLM Graphiti model configuration
status: completed
task_type: review
review_mode: decision
review_depth: standard
created: 2026-03-18T10:00:00Z
updated: 2026-03-18T16:00:00Z
priority: high
tags: [graphiti, vllm, qwen3, model-selection, dgx-spark, analysis]
complexity: 5
review_results:
  score: 90
  findings_count: 7
  recommendations_count: 4
  decision: keep_qwen2.5_14b_with_xgrammar
  report_path: .claude/reviews/TASK-REV-DGX1-review-report.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse Graphiti seeding success and vLLM Graphiti model configuration

## Description

Following the Graphiti config update (TASK-REV-G4C1) and vLLM model switch, all 4 previously-failing agentic-dataset-factory architecture artefacts have now been successfully seeded. However, the docker log reveals the `vllm-graphiti` container is running **Qwen2.5-14B-Instruct-FP8** rather than the planned **Nemotron 3 Nano 4B FP8**. This review should analyse the results and determine if any further action is needed.

## Source Documents

- `docs/reviews/additonal-templates/add-graphiti-success.md` — successful seeding output for all 4 files
- `docs/reviews/additonal-templates/qwen-docker-success.md` — docker log showing the actual model running in vllm-graphiti container

## Key Observations

### 1. Seeding Success (All 4 Files)

| File | Time (s) | Nodes | Edges | Status |
|------|----------|-------|-------|--------|
| ARCHITECTURE.md | 170s | 13 | 9 | Success |
| container.md | 309s | 15 | 28 | Success |
| domain-model.md | 238s | 15 | 20 | Success |
| ADR-ARCH-002 | 217s | 14 | 12 | Success |

All 14 agentic-dataset-factory architecture artefacts are now seeded.

### 2. Model Mismatch

The `vllm-graphiti` container is running `neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic` (14B, 0.4 GPU util, 32K ctx) instead of the planned `nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8` (4B, 0.05 GPU util, 8K ctx).

This means:
- The `vllm-graphiti.sh` script was likely not used (or was modified before running)
- The 14B model uses ~15GB vs the planned ~4GB
- Processing times (170-309s) are better than Qwen3-Coder (>600s) but slower than expected from a 4B model
- `--served-model-name` was not set, so the model serves as its HuggingFace ID

### 3. Edge Warnings

```
Target index 14 out of bounds for chunk of size 14 in edge HAS_RESPONSIBILITY
```

This appeared during ADR-ARCH-002 seeding — a graphiti-core edge resolution issue (cosmetic, didn't prevent seeding).

### 4. Processing Time Baseline

With Qwen2.5-14B-Instruct on the same hardware:
- Generation throughput: 6-10 tok/s
- Episode processing: 170-309s per episode
- Previously with Qwen3-Coder-Next 80B: >600s (timeout)

### 5. Nemotron 3 Nano Failed Completely

Nemotron 3 Nano 4B was trialled and **completely failed** for Graphiti workloads. Two structural issues:

**Issue A: 8192-token context entirely consumed by Graphiti overhead.** Graphiti's entity extraction prompts have ~7800-8100 tokens of baseline overhead (schema definitions, system instructions, existing graph context). With an 8192-token limit, there's virtually no room for the actual document content. The same applies to the 30B-A3B Nemotron variant (identical 8192-token limit).

**Issue B: Graphiti requires `json_schema` guided decoding.** Its `OpenAIGenericClient` sends:

```python
response_format = {
    "type": "json_schema",
    "json_schema": {"name": "...", "schema": {...}}  # full Pydantic schema
}
```

Without `--guided-decoding-backend outlines` in vLLM launch args, the model must follow complex nested schemas purely by instruction-following — which small models with thinking mode fail at.

**Models with thinking mode (Qwen3, Nemotron reasoning mode) are especially problematic** — they spend thousands of tokens in `<think>...</think>` deliberation before producing JSON, and may still get the schema wrong.

### 6. TASK-REV-DGX1 Review Findings: Qwen3-30B-A3B-FP8 Recommended

A comprehensive review (TASK-REV-DGX1, `.claude/reviews/TASK-REV-DGX1-review-report.md`) evaluated all candidates and recommends **Qwen/Qwen3-30B-A3B-FP8**:

| Requirement | Status |
|-------------|--------|
| Context ≥16K | ✅ 32K native |
| Good structured JSON | ✅ General-purpose instruction model (not coder) |
| Fits GB10 memory | ✅ ~32.5 GB FP8; ~33 GB total with nomic-embed |
| GB10 validated | ✅ Community tested, ~60-66 tok/s with MoE latency backend |

**Fallback**: Qwen/Qwen3-14B-FP8 (~16.3 GB) if running all three ports simultaneously proves memory-tight.

**Critical risk**: Qwen3 defaults to `<think>...</think>` thinking mode. Must disable before Graphiti use via `--reasoning-parser` (vLLM server) or `chat_template_kwargs: {enable_thinking: false}`.

**gpt-oss:20b** was also evaluated (Graphiti's own recommended model, native json_schema) but is gated/private on HuggingFace and primarily an Ollama model — less suitable for the vLLM-based infrastructure already in place.

### 7. Model Comparison Matrix (Final)

| Model | Thinking | Context | `json_schema` | GB10 Fit | Outcome |
|-------|----------|---------|---------------|----------|---------|
| Qwen3-Coder-Next 80B | Yes — slow | 256K | Needs guided backend | ~92GB | **Failed** (>600s timeout) |
| Nemotron 3 Nano 4B | Yes — reasoning | **8K** ❌ | Needs guided backend | ~4GB | **Failed** (context too small) |
| Nemotron 3 Nano 30B-A3B | Yes — reasoning | **8K** ❌ | Needs guided backend | ~15GB | **Eliminated** (same context limit) |
| Qwen2.5-14B-Instruct-FP8 | No | 32K | Needs guided backend | ~15GB | **Working** (170-309s, interim) |
| gpt-oss:20b | No | 128K | Native | ~16GB | **Viable** but Ollama-only, gated |
| **Qwen3-30B-A3B-FP8** | **Must disable** | **32K** | **Needs guided backend** | **~33GB** | **Recommended** (TASK-REV-DGX1) |

### 8. Final Decision: Qwen2.5-14B-Instruct + xgrammar (Revised)

TASK-REV-DGX1 recommended Qwen3-30B-A3B-FP8, but further research eliminated it (thinking mode risk) and gpt-oss:20b (ARM64 blocked, MXFP4 broken on Blackwell, json_schema broken in offline mode).

**Final answer: Keep Qwen2.5-14B-Instruct-FP8 with `--guided-decoding-backend xgrammar`.**

`xgrammar` is the key missing piece — it's a constrained decoding backend that enforces JSON schema at generation time, token by token. The model cannot produce invalid JSON even if it tries. This is what OpenAI and Gemini do natively; xgrammar gives the equivalent with any local model.

| Graphiti Requirement | How It's Met |
|---------------------|--------------|
| `response_format: json_schema` | vLLM xgrammar backend enforces schema at token level |
| No thinking mode | Qwen2.5 is pure instruct — zero thinking tokens |
| ≥ 16K context | 128K native |
| Good structured JSON | Qwen2.5 has explicit structured data training |
| GB10 compatible | ARM64 vLLM builds confirmed working |
| Memory | ~16 GB FP8 — comfortable alongside embeddings and AutoBuild |

### Models Eliminated

| Model | Reason Eliminated |
|-------|-------------------|
| Qwen3-Coder-Next 80B | Thinking mode, >600s timeout |
| Nemotron 3 Nano 4B/30B | 8K context consumed by Graphiti overhead |
| gpt-oss:20b | No ARM64 wheel, MXFP4 broken on Blackwell, json_schema broken offline |
| Qwen3-30B-A3B-FP8 | Thinking mode risk (would need disabling + validation) |

## Remaining Implementation Work

1. Update `scripts/vllm-graphiti.sh` — add `qwen2.5-14b` preset with `--guided-decoding-backend xgrammar` as default
2. Update `.guardkit/graphiti.yaml` across repos: `llm_model: neuralmagic/Qwen2.5-14B-Instruct-FP8-dynamic`
3. Run `guardkit graphiti add-context` end-to-end test with xgrammar enabled
4. Verify xgrammar reduces processing time vs current (170-309s without guided decoding)

## Review Scope (Completed via TASK-REV-DGX1)

1. ✅ **Seeding completeness**: All 14 artefacts seeded successfully
2. ✅ **Model selection**: Qwen3-30B-A3B-FP8 selected (TASK-REV-DGX1)
3. ✅ **Nemotron eliminated**: Both 4B and 30B variants — 8K context too small
4. ✅ **gpt-oss evaluated**: Viable but Ollama-only, gated — not selected
5. ✅ **Thinking mode risk**: Identified, mitigation documented
6. ⚠️ **Edge warnings**: Cosmetic (didn't prevent seeding)
7. 🔲 **Script update**: `vllm-graphiti.sh` needs Nemotron presets replaced with Qwen3-30B
8. 🔲 **Config update**: `graphiti.yaml` across repos needs `llm_model` update
9. 🔲 **Thinking mode disable**: Needs implementation and testing

## Acceptance Criteria

- [x] Confirmed all 14 artefacts seeded to Graphiti
- [x] Decision documented: Qwen3-30B-A3B-FP8 (TASK-REV-DGX1)
- [x] Nemotron models eliminated with evidence (8K context)
- [x] gpt-oss:20b evaluated (viable but not selected)
- [x] Edge warning assessed (cosmetic)
- [ ] `vllm-graphiti.sh` script updated with Qwen3-30B preset
- [ ] `.guardkit/graphiti.yaml` configs updated across repos
- [ ] Qwen3 thinking mode disabled and validated
- [ ] End-to-end `add-context` test with new model

## Context

- Parent review: TASK-REV-5B3A (wrong project seeded to Graphiti)
- DGX1 review: TASK-REV-DGX1 (optimal LLM for Graphiti on DGX Spark)
- Config update: TASK-REV-G4C1 (update graphiti configs)
- Port allocation: 8000=Graphiti LLM, 8001=Embed, 8002=AutoBuild
- Current working model: Qwen2.5-14B-Instruct-FP8 (interim, 170-309s/episode)
- Recommended model: Qwen3-30B-A3B-FP8 (~60-66 tok/s, 32K ctx)

## Implementation Notes

Review completed via TASK-REV-DGX1. Decision: switch to Qwen3-30B-A3B-FP8 with thinking mode disabled. Remaining work is implementation (script + config + validation).

## Test Execution Log

[Automatically populated by /task-work]
