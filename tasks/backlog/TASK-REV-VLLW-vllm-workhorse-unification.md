---
id: TASK-REV-VLLW
title: vLLM-served Qwen3.6 workhorse unification — one model for agents AND Graphiti extraction
status: backlog
task_type: review
review_mode: decision
review_depth: deep
created: 2026-06-12T00:00:00Z
updated: 2026-06-12T00:00:00Z
priority: medium
tags: [graphiti, vllm, llama-swap, qwen36-workhorse, gb10, structured-outputs, dgx-spark]
complexity: 6
decision_required: true
related: [TASK-REV-7BFP, TASK-REV-DGX1, memory-relay-scope]
---

# Task: vLLM workhorse unification experiment

## Hypothesis

Serving `qwen36-workhorse` via **vLLM under llama-swap** (the validated §9.2
coder-next pattern) removes all three llama.cpp blockers that killed the
2026-05-30 consolidation attempts, allowing one resident model to serve both
agent traffic and Graphiti extraction:

1. **§9.5 slot starvation** — vLLM continuous batching has no `-np` slot
   model; Graphiti's 3–5-call fan-out becomes ordinary concurrent sequences.
2. **§9.6/§9.7 `-np 2` launch bug** — llama.cpp-specific; does not apply.
3. **§9.1 per-slot context partitioning** — each vLLM sequence can use up to
   `max-model-len`; the 9.4K-token chunk class is structurally fine.

Model quality is already proven: §9.5 Test 1 (Qwen3.6 + `--reasoning off` +
grammar) returned clean schema-compliant extraction in 2.77s. vLLM's xgrammar
backend is the TASK-REV-DGX1-documented enforcement mechanism.

## Honest cost model (verify, don't assume)

| Item | llama.cpp today | vLLM unified (estimate) |
|---|---|---|
| Workhorse weights | ~21GB GGUF Q4-class | ~35GB FP8 safetensors |
| qwen-graphiti | ~28GB resident | **retired** |
| KV | per-slot, elastic | pre-allocated via `--gpu-memory-utilization` |
| Combined resident | ~55GB | target ≤55GB (tune util) |
| Cold load | seconds | minutes (§9.2 observed ~7 min for coder-next) |

Net memory win may be 0–10GB, **not** 28GB — the wins are fragility removal,
one fewer model, and full-context extraction. If TASK-REV-7BFP already passed,
weigh whether this experiment is still worth the operational change.

## Pre-flight checks (abort early if any fail)

- [ ] FP8 checkpoint for Qwen3.6-35B-A3B exists on HF and/or is cached locally.
- [ ] vLLM 0.13 (NGC 26.01-py3) registers the architecture (same hybrid
      family as Qwen3-Next, which loaded in §9.2 — confirm the exact class).
- [ ] ≥ ~60GB free before first load (`/unload` first; stop keepalive timer).
- [ ] Tool-call parser flag for Qwen3.6 instruct identified (coder-next used
      `--tool-call-parser qwen3_coder`; verify the correct parser for 3.6).
- [ ] Non-thinking serving mode confirmed (chat-template kwarg or server flag
      — extraction calls MUST NOT generate reasoning tokens).

## Stages

### S1 — Wrapper + llama-swap entry (modelled on §9.2)

```bash
sudo cp /opt/llama-swap/config/config.yaml \
        /opt/llama-swap/config/config.yaml.bak-$(date +%F)-pre-vllw
# /opt/llama-swap/scripts/vllm-workhorse.sh ${PORT}: docker run --rm of NGC
# vLLM serving Qwen3.6-35B-A3B-FP8 with:
#   --structured-outputs-config.backend xgrammar
#   --enable-prefix-caching            (Graphiti's repeated 7.8K scaffolding)
#   --gpu-memory-utilization <tuned>   (start 0.45; G1 bounds it)
#   --max-model-len 131072
#   tool parser per pre-flight; non-thinking template per pre-flight
# LESSONS: no --load-format fastsafetensors (§9.2); entry needs cmdStop +
# matrix set; stop llama-swap-keepalive.timer for the session.
sudo systemctl stop llama-swap-keepalive.timer
```

**G1 gate: loads via llama-swap within healthCheckTimeout (600s); resident
footprint ≤ 55GB at chosen util; ≥ 35 tok/s generation.**

### S2 — Smoke probes

```bash
# P1 json_schema extraction probe (§9.5 Test-1)        → valid schema, no leak
# P2 dedup-semantics probe (§9.8 guard, idx range 0..1) → in-range only
# P3 /v1/messages tool-use probe (the AutoBuild path, §9.2 step 3)
# P4 free-text probe → no reasoning tokens in content
```

**G2 gate: P1–P4 pass.**

### S3 — Graphiti pipeline at full concurrency

```bash
cp .guardkit/graphiti.yaml .guardkit/graphiti.yaml.bak-$(date +%F)-vllw-test
# llm_model → the vLLM workhorse alias; chunk_extraction_concurrency: 8
# (restored — the point is that vLLM absorbs the fan-out)
# Scratch group_id: experiment_vllw. Same fixture pair as TASK-REV-7BFP,
# including the ≥9K-token chunk doc. Same-day 14B baseline for wall-time.
```

**G3 gate: episodes added = files, 0 failed, 0 synthetic-429/SDK-retry storms,
0 exceed_context_size, wall ≤ 2× qwen-graphiti baseline.**

### S4 — Agent regression

```bash
# jarvis intent-classification smoke; one 3-turn AutoBuild task via
# ANTHROPIC_BASE_URL against the vLLM workhorse; one forge interaction.
```

**G4 gate: no tool-call format failures; latency acceptable for interactive
jarvis use (subjective but record p50/p95).**

### S5 — Decision

| Outcome | Action |
|---|---|
| G1–G4 pass | Decision point: retire `qwen-graphiti` (D10 of memory-relay scope gets a different residency target; drain concurrency may rise). New findings §9.x; 1-week soak |
| G1 fails on footprint | Record; fall back to TASK-REV-7BFP outcome; keep wrapper as future option for second-Spark world |
| G3 fails | The §9.5 diagnosis was wrong/incomplete — escalate to a review task before any further consolidation attempts |

### S6 — Revert

```bash
cp .guardkit/graphiti.yaml.bak-*-vllw-test .guardkit/graphiti.yaml
# remove vLLM workhorse entry + matrix set; restore config backup; hot-reload
docker stop vllm-workhorse 2>/dev/null || true
sudo systemctl start llama-swap-keepalive.timer
curl -sS http://localhost:9000/v1/chat/completions -d '{"model":"qwen-graphiti","max_tokens":4,"messages":[{"role":"user","content":"ping"}]}'
guardkit graphiti clear --group-id experiment_vllw
```

## What NOT to do

- Do NOT run concurrently with TASK-REV-7BFP or any fine-tune job.
- Do NOT leave the keepalive timer stopped after the session (§9.2 lesson).
- Do NOT pass `--load-format fastsafetensors` (§9.2: ModuleNotFoundError).
- Do NOT test against production group_ids.
- Do NOT conflate this with the memory-relay build: if memory-relay P3 has
  landed, episodes buffer safely during any failure here — preferred ordering
  is relay P1–P3 first.

## Acceptance criteria

- [ ] Pre-flight checklist completed with evidence before S1
- [ ] G1–G4 recorded with numbers (footprint, tok/s, wall times, p50/p95)
- [ ] Findings doc §9.x entry written (pass or fail)
- [ ] If passed: explicit decision on retiring qwen-graphiti, with memory-relay scope D10 updated to the new residency target
