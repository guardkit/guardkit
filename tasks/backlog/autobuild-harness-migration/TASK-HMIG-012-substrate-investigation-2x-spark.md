---
id: TASK-HMIG-012
title: Stage 2 — Substrate quality investigation on 2× DGX Spark + ConnectX-7 (post-hardware-arrival)
status: backlog
task_type: research
created: 2026-06-06T11:00:00Z
updated: 2026-06-18T15:45:00Z
priority: low   # deferred 2026-06-18 — gemma4:26b substrate is sufficient (was: high)
deferred: 2026-06-18   # optional optimization; activates only when 2nd Spark is live AND a stronger Player is wanted
complexity: 6
deadline: 2026-07-15  # post-cutover; targets the wider hardware deployment window (deferred — see banner)
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 4
implementation_mode: manual    # research + empirical validation across candidate models
intensity: standard
effort_hours: 12   # research + deployment + benchmarking across 2-3 candidate models
depends_on:
  - HARDWARE-2ND-DGX-SPARK  # placeholder: 2nd Gigabyte AI TOP Atom + ConnectX-7 cable arriving ~2026-06-08 to 2026-06-13
related_tasks:
  - TASK-HMIG-013  # Stage 1 single-GB10 model swap; this task supersedes IF Stage 1 was insufficient
falsifier: "After landing, FEAT-AOF runs cleanly to APPROVED on at least 2 of 3 tasks under the chosen 2×-Spark substrate within a 90-minute wall-clock budget per task. Coach verdict-emission rate ≥98%. F17 + F6 + F13 all close at substrate level (no longer fire OR fire <2% of turns). The chosen substrate is documented as the new default in MODEL_CONTEXT_WINDOWS."
tags:
  - autobuild
  - substrate-quality
  - hardware
  - post-cutover-optimization
  - dgx-spark
---

# Task: Substrate quality investigation on 2× DGX Spark + ConnectX-7

> **DEFERRED 2026-06-18 (priority → low).** The cutover shipped on the
> single-GB10 **gemma4:26b** Coach (TASK-HMIG-011 completed; TASK-HMIG-013 /
> TASK-OPS-COACHMOE01), and that substrate is **sufficient for ongoing
> operations** — exactly the condition under which this task's own Notes say it
> "can be deferred indefinitely or used purely as an optimization investigation
> when bandwidth permits." This is a *post-cutover optimization* (stronger/faster
> Player via DeepSeek V4 Flash on 2× Spark), NOT pending or blocking work.
>
> **Reactivation conditions (both required):** (1) the 2nd DGX Spark +
> ConnectX-7 is deployed and operational with llama-swap routing TP=2 across both
> Sparks (AC-001); AND (2) there is a concrete need for a faster/stronger Player
> than qwen36-workhorse. Until both hold, this stays parked. Bump priority back to
> high when reactivating.

## Why this task exists

Runs 1-6 of FEAT-AOF empirically demonstrated that the migration mechanics are complete (every F1-F19 finding closed) but the qwen36-workhorse substrate is the load-bearing constraint on cutover confidence:

- F17 substrate F2 at Coach scope (Coach verdict-emission ~67% reliable)
- F6 substrate slowness (Coach turns up to 22+ minutes on multi-turn iteration)
- F13 SPECHANG (test-orchestrator specialist hits 600s cap reliably)

The operator's hardware setup is expanding:
- **Currently**: 1× DGX Spark GB10 (128GB unified memory, fully utilised at ~115GB)
- **Incoming ~2026-06-08 to ~2026-06-13**: 2nd Gigabyte AI TOP Atom + ConnectX-7 cable (256GB total, tensor parallel via NVLink-class interconnect)

**TASK-HMIG-013 ships the cutover** on 2026-06-15 with gemma4:26b on Coach (or nemotron-3-super:120b-a12b fallback) on the existing single GB10. This task (TASK-HMIG-012) is **the follow-on optimization** when the second Spark arrives, targeting candidates that need 2-node deployment for best throughput.

## Research already done (2026-06-06)

The mid-2026 candidate landscape on DGX Spark, ranked by relevance to our use case:

### Models DROPPED from candidate list

- **Nemotron-3-Ultra-550B-A55B** — Technically fits 2× Spark at 2-bit GGUF (~137GB) but runs at ~5 tok/s per the GB10 forum's "it works" thread. At that throughput, a 1000-token Coach verdict takes 200s; a 3000-token verdict takes 10 min. Substitutes one F6 substrate-slowness problem for another. **Not viable for Coach.**
- **Pay-per-token cloud APIs** (Sonnet, GPT, etc.) — Excluded by operator constraint: zero API budget.

### Primary candidates for 2× Spark deployment

| Model | Params | Quant | Single-Spark? | 2× Spark notes | Use case |
|---|---|---|---|---|---|
| **DeepSeek V4 Flash** | 284B / 13B active MoE | FP8 (~80GB) | ✓ yes | TP=2 across 2× Spark → faster inference, 200K context. 186-reply forum thread on deployment. SWE-bench Verified 79.0%, LiveCodeBench 91.6%, Terminal-Bench 2.0 56.9%. SOTA open-source agentic coding. | **Player** (primary) — multi-step coding work |
| **Qwen3.5-122B-A10B** | 122B / 10B active MoE | NVFP4 / FP8 | borderline single | 2× Spark with TP=2 gives headroom for KV cache + longer context | **Player alternative** if DeepSeek V4 Flash has issues |
| **nemotron-3-super:120b-a12b** | 120B / 12B active MoE | NVFP4 | ✓ yes (16.4 tok/s) | 2× Spark with TP=2 → 2× speedup. 17/17 agentic + 6-hop depth. "Strongest agentic profile across the suite" per Exxact benchmark. | **Coach** (highest reliability) if gemma4:26b proves insufficient in Stage 1 |
| **gemma4:26b** | 26B MoE | various | ✓ yes (52.7 tok/s) | Already chosen for Stage 1 (TASK-HMIG-013). 2× Spark doesn't help materially. | **Coach** (already in Stage 1) |

### Secondary candidates worth tracking

- **DeepSeek V4 Pro** — even better than Flash (SWE-bench 80.6%, LiveCodeBench 93.5%, Terminal-Bench 67.9%) but larger memory footprint. Investigate if Flash isn't enough.
- **Mistral-Small-4-119B-2603-NVFP4** — emerging in the forum but no production-deployment numbers yet.
- **Larger Qwen3.6 variants** — if the family adds bigger sizes.

## Acceptance Criteria

- [ ] AC-001: Confirm 2nd DGX Spark + ConnectX-7 deployed and operational. Verify llama-swap can route to both Sparks transparently (single endpoint, TP=2 routing for large models).
- [ ] AC-002: Deploy **DeepSeek V4 Flash (FP8, TP=2)** across 2× Spark. Verify it appears in llama-swap model list. Run an empirical structured-output smoke (replay 5 Coach prompts from previous runs): emission rate ≥95%.
- [ ] AC-003: Live FEAT-AOF run with `--model deepseek-v4-flash --coach-model gemma4:26b` (Player on DeepSeek, Coach on the Stage-1 winner). Measure:
  - Coach verdict-emission rate across 6+ turns
  - Wave 1 IA03 wall-clock to APPROVED (target: <30 min, vs run 4's 12 min for the rare 1-turn success)
  - F6 multi-turn drift presence/absence
  - F13 SPECHANG firing rate
- [ ] AC-004: If AC-003 passes: file as the new default substrate. Update `MODEL_CONTEXT_WINDOWS` defaults in guardkitfactory `model_config.py`. Document the cutover-policy change as TASK-HMIG-014 (or fold into the operator's normal task-work cadence).
- [ ] AC-005: If AC-003 partial-passes (Player improves but Coach issues remain): try **nemotron-3-super:120b-a12b** for Coach. This candidate is highly-rated for agentic reliability (17/17 + 6-hop) and fits single Spark at NVFP4 — 2× Spark deployment would just speed it up via TP=2.
- [ ] AC-006: Document final substrate-policy recommendations in `docs/guides/autobuild-substrate-policy.md` (new file): which model for which role, KV-cache headroom, expected throughput, known failure modes per substrate, recommended timeouts (`--task-timeout`, SPECHANG cap, etc.).
- [ ] AC-007: Capture Graphiti knowledge entries for each tested substrate (model, role, success rate, throughput, observed failure modes) for future autobuild context loading.

## Implementation Notes

- This is a research + empirical-validation task. Plan for 2-3 model deployments × 1 FEAT-AOF run each = ~3-5 runs total. Each run is 30-90 minutes wall-clock + analysis time.
- The 2× Spark deployment requires recipes from the GB10 forum (`"DeepSeek-V4-Flash (official FP8) running across 2x DGX Spark — TP=2, MTP, 200K ctx, recipe + numbers"` — 186 replies is the canonical recipe thread).
- ConnectX-7 cable bandwidth is the load-bearing factor for tensor-parallel speedup. Verify the cable + driver setup with a simple TP=2 inference smoke before committing to FEAT-AOF runs.
- Power and thermal: 2× DGX Spark draws ~480W sustained. Verify the operator's circuit + cooling before sustained-load testing.
- This task does NOT block the 2026-06-15 cutover — TASK-HMIG-013 (Stage 1) handles that. This task is the **post-cutover optimization** that converts autobuild from "works with documented substrate variance" to "works reliably as production default."

## What this task is NOT

- **Not architectural work**: every architectural finding F1-F19 is closed. This is purely substrate quality.
- **Not a model fine-tuning project**: we're testing already-published models, not training new ones. Out of scope for the cutover window.
- **Not a hardware troubleshooting task**: assume the 2× Spark + ConnectX-7 deployment is operator-managed via DGX Spark documentation. If hardware-side problems arise, file separately.

## References

- TASK-HMIG-013 (Stage 1, prerequisite): [TASK-HMIG-013](TASK-HMIG-013-swap-coach-to-gemma4-26b-single-gb10.md)
- DeepSeek V4 Flash deployment recipe (canonical forum thread): "DeepSeek-V4-Flash (official FP8) running across 2x DGX Spark — TP=2, MTP, 200K ctx, recipe + numbers" on [NVIDIA DGX Spark GB10 forum](https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719)
- Spark Arena leaderboard: [spark-arena.com](https://spark-arena.com/)
- Exxact DGX Spark agentic benchmark: [Benchmarking Local AI Agents on NVIDIA DGX Spark](https://www.exxactcorp.com/blog/benchmarks/benchmarking-local-ai-agents-on-nvidia-dgx-spark)
- DeepSeek V4 Flash benchmarks: [BuildFast with AI review](https://www.buildfastwithai.com/blogs/deepseek-v4-flash-review-2026)
- Nemotron-3-Ultra memory analysis (and why we DROPPED it from candidates): [Unsloth Nemotron-3-Ultra docs](https://unsloth.ai/docs/models/nemotron-3-ultra)
- MODEL_CONTEXT_WINDOWS precedent: TASK-HMIG-002R-MODEL-PROFILE (guardkitfactory)
- Cutover task: [TASK-HMIG-011](TASK-HMIG-011-cutover-ceremony-flip-default-harness.md)

## Notes

This task targets the wider window post-cutover. Hardware delivery timing is uncertain (invoice-pending); the task's effective start is "when the 2nd Spark + ConnectX-7 is operational and llama-swap routes to both Sparks." Until that condition is met this task stays in backlog. Operator polls hardware status; task picks up automatically once status flips.

If TASK-HMIG-013's gemma4:26b swap turns out to be sufficient for ongoing operations (autobuild reliable, BDD layering works on top), this task can be deferred indefinitely or used purely as an optimization investigation when bandwidth permits.
