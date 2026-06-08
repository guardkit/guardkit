---
id: TASK-OPS-COACH31B
title: Evaluate Gemma 4 31B dense QAT as the AutoBuild Coach substrate (no new hardware)
status: in_progress
task_type: ops
created: 2026-06-08T00:00:00Z
updated: 2026-06-08T20:00:00Z
priority: high
complexity: 4
effort_hours: 4
parent_task: TASK-HMIG-010
related: [TASK-FIX-COACHSCHEMA, TASK-OPS-COACHGRAMMAR, TASK-DATA-COACHHARVEST]
implementation_mode: operator
intensity: standard
blocker: true
---

# Task: Evaluate Gemma 4 31B dense QAT as the Coach substrate

## Why this task exists

**Runs 12–14 proved the current Coach substrate (base Gemma 4 26B-A4B-IT,
3.8B active) cannot do reliable agentic verdict emission.** Three non-hardware
levers were exhausted:
- **Path 1A** (route-level GBNF grammar): no-op — llama.cpp bypasses
  `--grammar-file` when a request carries `tools`, and the deepagents Coach
  always sends tools. ([TASK-OPS-COACHGRAMMAR](autobuild-harness-migration/TASK-OPS-COACHGRAMMAR-enforce-coach-verdict-schema-via-llama-cpp-gbnf.md))
- **Path 1B** (decisive prompt + self-check): failed in run 14 — Coach turn 1
  produced **49,720 chars of reasoning and no verdict** in ~45 min; turn 2 short
  and still no verdict. ([TASK-FIX-COACHSCHEMA](autobuild-harness-migration/TASK-FIX-COACHSCHEMA-tighten-coach-prompt-schema-emission.md))
- **More time** (`--sdk-timeout 3600`): made it **worse** — the bigger budget
  let it ramble 9× longer without converging.

So the wall is the **model's active-reasoning capacity** (3.8B active), not the
scaffolding. The targeted, **no-new-hardware** fix is a model with more *active*
reasoning at ~the same memory: the **Gemma 4 31B dense QAT** (30.7B active vs
3.8B; QAT = quantization-aware-training quality at int4). Cost driver: a capable
**local** Coach is needed because Claude API tokens are prohibitive for
non-client dev work — so swapping in a bigger local model beats both waiting for
a 2nd GB10 (nemotron) and paying per-token for cloud.

## Candidates (verified on HuggingFace, 2026-06-08)

| model | quant file | size | arch | active | note |
|---|---|---:|---|---:|---|
| **`google/gemma-4-31B-it-qat-q4_0-gguf`** | Q4_0 QAT | **17.7 GB** | **DENSE** | **30.7B** | **PRIMARY** — capacity fix; ≈ current Coach memory (17.0 GB) |
| `google/gemma-4-26B-A4B-it-qat-q4_0-gguf` | Q4_0 QAT | 14.4 GB | MoE | 3.8B | secondary — quant-damage control only; same active count as today, so unlikely to fix convergence. Free 2.6 GB though. |
| `unsloth/gemma-4-31B-it-qat-GGUF` | — | — | dense | 30.7B | Unsloth mirror (alt source) |

Both are 256K context. Current Coach for comparison:
`gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf` (17.0 GB, 3.8B active, 3rd-party PTQ).

## What to do

> **Baseline is now clean**: TASK-FIX-COACHSCHEMA's Path 1B prompt block was
> **reverted** (2026-06-08), so the Coach prompt is back to the runs-12/13
> baseline. This run isolates the **substrate** variable.

1. **Download** `google/gemma-4-31B-it-qat-q4_0-gguf` to
   `/opt/llama-swap/models/gemma4-31b-coach/` on `promaxgb10-41b1`. (And
   optionally the 26B-A4B-QAT for a cheap control arm.)
2. **Add a llama-swap route** (mirror the `gemma4-coach` block in
   `/opt/llama-swap/config/config.yaml`, binary
   `/home/richardwoollcott/llama.cpp-new/build/bin/llama-server`):
   - alias `gemma4-31b` (+ `gemma4:31b`), model = the 31B GGUF
   - `--jinja` with the **base Gemma-4 IT chat template** (NOT the
     `gemma4-thinking.jinja` — that forces extra deliberation, the opposite of
     what we want; the architect-agent uses thinking, the Coach must not)
   - `--reasoning auto`, `--temp 0.1`, `--cache-type-k q8_0 --cache-type-v q8_0`
   - `--ctx-size 98304` to start; **if KV at 98K overflows memory** (a dense 31B
     has larger KV than the MoE), drop to 65536. NO `--grammar-file` (Path 1A is
     reverted/no-op).
   - Wire into a matrix.set so it can take the Coach slot. Memory: 31B Q4_0
     (17.7 GB) + q8 KV ≈ ~26 GB resident, ≈ the current Coach footprint — but the
     GB10 has frozen near the ceiling before (findings §9.4); `/unload` + check
     `free -g` before loading.
3. **Tier-1 single-shot A/B** (cheap, on the GB10, the same probes this session
   used for the architect idea): send a substantive Coach prompt to `gemma4-31b`
   vs current `gemma4-coach`, measure:
   - **JSON-verdict discipline** — does it emit a valid fenced `task_id`/`turn`/`decision` verdict?
   - **Tool-calling discipline** — given `tools`, a clean `tool_call`?
   - **Convergence** — reasoning-content length, latency, `finish_reason`
     (does the dense model converge in *fewer* tokens than the 4B-active MoE's
     49,720-char ramble?)
   - **Verdict quality** — correct on a known-answer task, or over-deliberates?
   (Caveat: single-shot ≠ the tool-bound agentic Coach — but the tool/JSON
   discipline signals are valid, and convergence length is the key proxy.)
4. **Tier-2 run 15** (the real test): from the Mac, langgraph harness, the
   31B as `--coach-model`, clean baseline prompt:
   ```bash
   GUARDKIT_HARNESS=langgraph \
     OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
     OPENAI_API_KEY=llama-swap-local-key \
     guardkit autobuild feature FEAT-AOF \
       --fresh --model qwen36-workhorse --coach-model gemma4:31b \
       --task-timeout 4800 --sdk-timeout 3600 \
       2>&1 | tee .guardkit/autobuild/TASK-REV-HMIG-feature-run/run-15-stdout.log
   ```

## Acceptance criteria

- [x] **AC-1** ✅ (2026-06-08): `gemma-4-31B_q4_0-it.gguf` (17.65 GB, dense 30.7B,
  GGUF v3) downloaded to `/opt/llama-swap/models/gemma4-31b-coach/`; `gemma4-31b`
  route added (base IT embedded template via `--jinja`, `--reasoning auto`,
  `--temp 0.1`, q8 KV, ctx 98304, **no grammar**) + `g31` var + `coach31` set.
  Cold-loaded **ready** via the `coach31` set (evicting gc), **~28 GB free, no OOM**.
- [x] **AC-2 (single-shot A/B)** ✅ (2026-06-08): 6 probes × 2 arms measured (see
  [findings](../../docs/state/TASK-OPS-COACH31B/README.md)). The 31B emits valid
  correct fenced verdicts (D/E/F), converges in **1,792–2,903c reasoning** (vs the
  49,720-char ramble), **never** hits the token ceiling (0/6 vs gc's 1/6 on the
  clean-approve case), uses **2–4× fewer** reasoning tokens than gc when both
  converge, and shows the correct **gather-first** tool instinct (A/B). **PASS on
  the literal bar.** Caveat: single-shot is a **weak substrate discriminator** —
  the toolless probes (E/F) made **both** arms converge, so single-shot does not
  prove a substrate wall; the run-14 catastrophe was tool-bound. → AC-3 decisive.
- [ ] **AC-3 (falsifier — run 15)**: DEFERRED (operator decision) until AC-2
  results in; **now recommend GO** — it is the only test of the tool-bound
  agentic loop where run-14 failed. Bar: ≥1 Coach turn converges (valid fenced
  verdict within SDK timeout) across ≥4 turns, ≥80% valid (vs run-14's 0/2).
  Recipe: [`run-15-recipe.md`](../../docs/state/TASK-OPS-COACH31B/run-15-recipe.md).
- [x] **AC-4** ✅ (2026-06-08): dense 31B ≈ **9–10 tok/s** vs MoE ≈ **40–46 tok/s**
  (~4.5× slower/token). Net time-to-verdict: gc faster when it converges (D 70s vs
  202s); 31B faster only where gc rambles (A 42s vs 358s/no-verdict). A 4.5×-slower
  Coach in a multi-turn loop may be slow per converged turn — if so, fall to the
  **12B dense QAT** (~7 GB) or distillation (TASK-DATA-COACHHARVEST).

## Results summary (2026-06-08, on `promaxgb10-41b1`)

Full evidence + harness + transcripts:
[`docs/state/TASK-OPS-COACH31B/`](../../docs/state/TASK-OPS-COACH31B/). The route
is **dormant by default** (not in `preload`/`all`/keepalive) — it only loads when
`gemma4:31b` is requested via the `coach31` set, so it does not disturb the fleet.
Config backup: `config.yaml.bak-2026-06-08-pre-coach31b`. The single-shot A/B is
encouraging but not decisive; the substrate verdict awaits run-15.

## Implementation notes / escalation

- **If the 31B converges** → local Coach problem is solved on current hardware;
  make it the Coach default; close TASK-HMIG-010's Coach gate.
- **If the 31B converges but is too slow** → consider the smaller dense
  **12B QAT** (12B active, ~7 GB — still 3× the MoE's active, faster than 31B),
  or distill (TASK-DATA-COACHHARVEST) to teach tighter convergence.
- **If the 31B *also* fails to converge** → the agentic-Coach task may exceed any
  ~30B-class local model; fall to distillation onto the 31B base, or Path 2
  (nemotron-3-super, hardware-gated).
- **Re-add prompt guidance only after a clean baseline**: if the 31B converges
  but is verbose, re-introduce **decisiveness-only** (drop the run-14 self-check
  clause that's the suspected cause of the 49,720-char loop).
- **Optional sub-experiment**: `--reasoning off` for the Coach (faster, more
  decisive) — the run-14 ramble suggests less reasoning, not more, helps
  convergence. The parser reads both channels (COACHBUDG01) so it's safe.

## Related

- Substrate evidence: runs 12–14 ([run-14 log](../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-14.md), [run-14 artifacts](../../docs/state/TASK-REV-HMIG/run-14-artifacts/README.md))
- QAT blog: https://blog.google/innovation-and-ai/technology/developers-tools/quantization-aware-training-gemma-4/
- Distillation data: [TASK-DATA-COACHHARVEST](TASK-DATA-COACHHARVEST-harvest-claude-era-coach-training-data.md)
- Current Coach route: `gemma4-coach` in `/opt/llama-swap/config/config.yaml` (the block to mirror)
