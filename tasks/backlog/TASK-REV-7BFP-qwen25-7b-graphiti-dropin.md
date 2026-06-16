---
id: TASK-REV-7BFP
title: Qwen2.5-7B-FP8/Q8 drop-in for qwen-graphiti — shrink the always-on extraction pin ~28GB → ~11GB
status: backlog
task_type: review
review_mode: decision
review_depth: standard
created: 2026-06-12T00:00:00Z
updated: 2026-06-12T00:00:00Z
priority: high
tags: [graphiti, llm-selection, llama-swap, gb10, memory-pressure, dgx-spark]
complexity: 4
decision_required: true
related: [TASK-REV-DGX1, memory-relay-scope]
---

# Task: Qwen2.5-7B drop-in for qwen-graphiti

## Hypothesis

`Qwen2.5-7B-Instruct` (same family as the proven 14B, same structured-data
training lineage, no thinking mode) can serve Graphiti extraction under the
identical llama.cpp/llama-swap configuration, reclaiming ~17GB of always-on
memory with **zero architectural change**. This is the cheap lever; run it
BEFORE TASK-REV-VLLW.

## Prior evidence (do not re-derive)

- TASK-REV-DGX1 selected 14B and documented 32B as the *upward* fallback "if
  the 14B misses entities on complex documents" — 7B was never tested
  downward. Entity recall on complex docs is therefore THE risk, and G4 exists
  to measure exactly that.
- §9.5 Test 1 / §9.8 Stage 3 probes are the validated smoke-test pattern.
- §9.8 showed **dedup output semantics** (invalid `duplicate_facts` idx
  ranges) is the most dangerous failure surface — a dedicated dedup probe is
  included below; do not skip it.
- Qwen2.5 family: no thinking-mode markers (unlike Qwen3.x / Gemma 4), but
  verify with the free-text probe anyway.

## Sequencing constraint (dataset)

Prefer landing memory-relay **P5 (trace proxy)** before flipping production to
7B, so the 14B teacher corpus starts accumulating first. If 7B goes live, keep
the 14B model entry defined (unloaded) — it remains the **teacher** for
offline dataset-generation runs feeding the future distilled extraction model.

## Stages

### S1 — Add experimental model entry (no production change)

```bash
sudo cp /opt/llama-swap/config/config.yaml \
        /opt/llama-swap/config/config.yaml.bak-$(date +%F)-pre-7bfp
# Add "qwen-graphiti-7b" (alias graphiti-llm-test): same args as qwen-graphiti
# (--ctx-size 65536 -np 4 --jinja --temp 0.0 --flash-attn on), model file
# Qwen2.5-7B-Instruct Q8_0 GGUF (~8.1GB).
# LESSON FROM §9.8: the entry MUST belong to a matrix set or the solver
# ignores it — reuse the graphiti_swap set pattern so loading it evicts
# qwen-graphiti (previews the end state).
```

**PASS:** entry hot-reloads; cold load OK; `free -g` shows footprint.
**G1 gate: resident footprint ≤ 12GB (weights ~8GB + 65K-ctx KV).**

### S2 — Smoke probes (direct, no Graphiti)

```bash
# P1 json_schema entity extraction (the §9.5 Test-1 probe): expect valid
#    schema JSON, finish_reason stop, all entities found.
# P2 free-text probe (NO response_format): expect plain text — zero
#    thinking/channel markers.
# P3 dedup-semantics probe (§9.8 guard): present EXISTING FACTS [0..1] and a
#    duplicate; expect idx values ONLY within 0..1.
```

**G2 gate: P1–P3 all pass. Any marker leak or out-of-range idx → FAIL, stop.**

### S3 — Real pipeline, scratch namespace

```bash
cp .guardkit/graphiti.yaml .guardkit/graphiti.yaml.bak-$(date +%F)-7bfp-test
# llm_model: qwen-graphiti → graphiti-llm-test
# Use a SCRATCH group_id (underscores only): experiment_7bfp
guardkit graphiti add-context <fixture-small.md>  --type full_doc   # ~250 words
guardkit graphiti add-context <fixture-large.md>  --type full_doc   # the §9.1 class: a ≥9K-token chunk doc
# Same-day baseline: repeat both against qwen-graphiti into experiment_14b_baseline
```

**G3 gate: episodes added = files submitted, 0 failed, no SDK retry storms,
no exceed_context_size, wall time ≤ 1.5× the same-day 14B baseline.**

### S4 — Extraction quality comparison

Compare `experiment_7bfp` vs `experiment_14b_baseline` graphs: entity count,
edge count, spot-check 10 entities/edges for correctness.

**G4 gate: entity recall ≥ 90% of 14B on the fixture set AND no hallucinated
entities/edges absent from source. This is the decision gate — memory savings
do not justify a quieter, blinder graph.**

### S5 — Decision

| Outcome | Action |
|---|---|
| G1–G4 pass | Promote: rename entry to `qwen-graphiti`, point at 7B file, keep 14B entry defined-but-unloaded as teacher; new findings §9.x entry; 1-week soak with weekly entity-count audit |
| G4 marginal (80–90% recall) | Hold; re-test after memory-relay lands (drain-window scheduling may make the 14B pin acceptable anyway) |
| G2/G3 fail | Revert, document in findings §9.x, fall through to TASK-REV-VLLW |

### S6 — Revert (always executable)

```bash
cp .guardkit/graphiti.yaml.bak-*-7bfp-test .guardkit/graphiti.yaml
# remove qwen-graphiti-7b entry + its matrix set; hot-reload; verify:
curl -sS http://localhost:9000/v1/chat/completions -d '{"model":"qwen-graphiti","max_tokens":4,"messages":[{"role":"user","content":"ping"}]}'
guardkit graphiti clear --group-id experiment_7bfp
guardkit graphiti clear --group-id experiment_14b_baseline
```

## What NOT to do

- Do NOT delete or modify the production `qwen-graphiti` entry during the test.
- Do NOT seed into production group_ids; scratch namespaces only.
- Do NOT run while an AutoBuild build or fine-tune job holds the box.
- Do NOT change embeddings (nomic-embed stays; dimension untouched).
- Do NOT skip the dedup probe (P3) — §9.8's failure was invisible to the
  entity-extraction probe.

## Acceptance criteria

- [ ] G1–G4 results recorded with numbers (footprint, wall times, recall %)
- [ ] Findings doc §9.x entry written (pass or fail)
- [ ] Decision recorded; if promoted, llama-swap config + graphiti.yaml committed and memory steady-state re-measured
