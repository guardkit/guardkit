# TASK-OPS-COACH31B — Gemma 4 31B dense QAT as the AutoBuild Coach substrate

> **Status (2026-06-08):** AC-1 done (model downloaded + route live); AC-2
> **baseline arm** done (reproduces F24); AC-2 **31B arm** pending a keepalive
> pause; AC-3 (run-15) deferred until AC-2 results (operator decision).
>
> **Host:** all infra work runs on `promaxgb10-41b1` (the GB10). This dir is the
> tracked twin of the experiment artifacts, mirroring the run-14-artifacts
> pattern.

## What this evaluates

Runs 12–14 proved the current Coach substrate — `gemma4-coach` = base Gemma 4
**26B-A4B-IT** (an MoE with only ~**3.8B active** params) — cannot organise
agentic reasoning to a fenced-JSON verdict. Three non-hardware levers were
exhausted (grammar = no-op for tool-bound agents; decisive prompt = worse; more
time = worse). The no-new-hardware fix under test: **`google/gemma-4-31B-it-qat-
q4_0-gguf`**, a **dense 30.7B** model (30.7B active vs 3.8B) at QAT int4 quality,
17.65 GB ≈ the current Coach's 17.0 GB footprint.

## AC-1 — model + route (DONE)

- **Model:** `google/gemma-4-31B-it-qat-q4_0-gguf` → weights file
  `gemma-4-31B_q4_0-it.gguf`, **17.65 GB** (17,650,999,456 B — exact HF match),
  GGUF v3, `architecture: gemma4`, dense **30.7B** params, **256K** context,
  Apache-2.0, **not gated**. Embedded **base Gemma-4 IT chat template** (tool
  calling supported; thinking channel off by default). Downloaded to
  `/opt/llama-swap/models/gemma4-31b-coach/` (mmproj vision file intentionally
  NOT downloaded — text Coach only).
- **Route:** `gemma4-31b` block added to `/opt/llama-swap/config/config.yaml`
  (backup: `config.yaml.bak-2026-06-08-pre-coach31b`). Posture mirrors
  `gemma4-coach` so the substrate is the only variable: base IT embedded
  template via `--jinja` (NO `--chat-template-file`), `--reasoning auto`,
  `--temp 0.1 --top-p 0.9`, `--cache-type-k/v q8_0`, `--ctx-size 98304`,
  **NO `--grammar-file`**. Aliases: `gemma4:31b`, `gemma-4-31b-it-qat`, `coach31`.
- **Matrix:** `g31: gemma4-31b` var + `coach31: "qg & ne & qw & g31 & dl"` set
  (mirrors `all` but swaps Coach gc→g31). NOT in `preload`/`all`/keepalive, so
  the route is dormant until `gemma4:31b` is requested — non-disruptive.
- llama-swap (`-watch-config`) hot-reloaded the route; `gemma4-31b` is present
  in `/v1/models`. **Serve-test (cold load) pending** the keepalive pause.

### Operational lesson (logged)
Editing `config.yaml` triggers a `-watch-config` **matrix reload** that tears
down + rebuilds all models, returning HTTP 502 / `"matrix is shutting down"`
500s to any in-flight request. **Never edit the config while a probe/run is
mid-flight.** (Cost us the first baseline run; re-ran clean.)

### Keepalive hazard (logged)
`llama-swap-keepalive.timer` (system timer, 5-min cadence) probes a hardcoded
allowlist that includes `gemma4-coach`. When g31 is loaded via `coach31` (which
evicts gc), the keepalive revives gc **on top of** g31 → two ~17 GB Coaches +
family → OOM/freeze. **Pause it for any g31 session** (`sudo systemctl stop
llama-swap-keepalive.timer`) and restart after. Stopping needs sudo (no
passwordless sudo for this operator on the box).

## AC-2 — single-shot A/B

Harness: [`probe_harness.py`](probe_harness.py) — sends 4 representative Coach
prompts (mirroring `agent_invoker._build_coach_prompt`, same verdict schema) to
an OpenAI-compatible `/v1/chat/completions` endpoint at temp 0.1 / top_p 0.9 and
records finish_reason, verdict (last fenced ```json block), reasoning/content
char counts, tool_calls, latency, tok/s. Probes:

- **A** clean-approve (no tools) — known answer: `approve`
- **B** clear-feedback (no tools) — known answer: `feedback`
- **C** tool-calling discipline (read_file + run_tests tools) — expect a tool_call
- **D** convergence-stress (large report + specialist violation, modelled on the
  run-14 `TASK-FIX-IA03` shape that triggered the 49,720-char ramble) — `feedback`

Full transcripts in [`probes/`](probes/).

> **Methodology caveat (important):** the FIRST baseline run was corrupted by a
> `-watch-config` matrix reload (I edited the config mid-run) — its probe-D
> rambled to 25,007c, but that was a degraded-server artifact, not clean gc
> behaviour. The numbers below are the **clean re-run** (no concurrent config
> edit). The raw `finish_reason` field is the authoritative convergence signal.

### CLEAN single-shot A/B (6 probes × 2 arms)

| probe | gemma4-coach (MoE, 3.8B active) | gemma4-31b (dense, 30.7B active) |
|---|---|---|
| **A** clean-approve (verify-instr., no tools) | **`length` — ramble 27,006c, 0 verdict, 358s** | `stop` — gather→`read_file` intent, 1,155c, 42s |
| **B** clear-feedback (verify-instr., no tools) | `stop` — `feedback` ✓, 3,979c, 35s | `stop` — gather→`bash ls` intent, 1,318c, 46s |
| **C** tool-calling (tools provided) | `tool_calls` `run_tests` ✓, 4s | `tool_calls` `read_file` ✓, 20s |
| **D** convergence-stress (in-band evidence) | `stop` — `feedback` ✓, 6,986c, 70s | `stop` — `feedback` ✓, 2,903c, 202s |
| **E** toolless-approve ("no tools, decide now") | `stop` — `approve` ✓, 6,383c, 49s | `stop` — `approve` ✓, 2,127c, 103s |
| **F** toolless-feedback ("no tools, decide now") | `stop` — `feedback` ✓, 8,971c, 69s | `stop` — `feedback` ✓, 1,792c, 94s |

**Convergence (the F24 metric — does it spiral to the token ceiling?)**
- gc: **1/6 ceiling ramble** — probe A (clean-approve): `finish=length`, 27,006c
  reasoning, 0c content, no verdict. Degenerate loop verbatim in the transcript:
  *"Wait, I see the prompt says ... ? No. ... I'll just use ... Wait, I see the
  prompt says ... ? No."* Notably it's the **approve** path that breaks (confidence
  needed; consistent with the run-6 "approve needs more confidence" finding).
- g31: **0/6 ceiling rambles.** Every probe finished `stop`/`tool_calls`.

**Verdict discipline (valid fenced verdict where a verdict is the expected output: D, E, F)**
- gc: **3/3 valid + correct** (also B). g31: **3/3 valid + correct.**
- On D (the planted-trap probe) **both** arms caught the planted AC-010/011
  contradiction + the specialist violation; g31 additionally flagged the 29 fake
  "module" files. Verdict *quality* is high on both when they converge.

**Agentic gather-first instinct (A/B — instructed to "run the tests yourself", no tools)**
- g31 converged to a **tool-gather intent** (emit `read_file`/`bash` then stop,
  waiting for results) — the correct Coach behaviour in the real tool-bound loop.
- gc on A spiralled instead of deciding to gather; on B it answered directly.

**Reasoning economy (converged cases):** g31 uses **2–4× fewer** reasoning chars
than gc to reach the same verdict (D: 2,903 vs 6,986; E: 2,127 vs 6,383;
F: 1,792 vs 8,971). The dense model is more decisive per token.

### The decisive nuance (adversarially verified — see `probes/adversarial-adjudication.json`)

The **toolless** probes E/F (explicit "no tools — emit verdict NOW") made **BOTH**
models converge to correct verdicts. So **single-shot is a weak discriminator for
the substrate question**: the MoE's pathology is not raw fenced-JSON emission —
it can emit a verdict when relieved of the agentic gather decision. The
catastrophic 49,720-char failure (run-14) happened in the **tool-bound agentic
loop** (gather via tools → interpret results → synthesise across turns), which a
single-shot probe cannot reproduce. The clean single-shot run only reproduces a
*partial* F24 (gc rambles on the clean-approve case A).

> An adversarial scoring pass (Explore agents) initially mislabelled g31's A/B as
> "ramble_to_ceiling F24 spirals." That is **false** — their own recorded
> `finish_reason` was `stop` with ~1,200c reasoning (a gather-intent, not a
> ceiling spiral). The raw `finish_reason` cross-check (only `baseline-gc/A` is
> `length`) is authoritative. Logged here as a caution: trust the metric, not the
> agent's pattern-match.

### Verdict on AC-2 (literal bar) — PASS, with a weak-discriminator caveat
AC-2's literal bar: *"the 31B should emit a valid fenced verdict and converge in
far fewer reasoning tokens than the MoE's 49,720-char ramble."* → **Met**: g31
emits valid correct verdicts (D/E/F), converges in 1,792–2,903c (vs 49,720), and
**never** hit the ceiling. BUT the single-shot A/B did **not** decisively prove a
*substrate wall* — the MoE also converges toolless. The substrate question is
settled only by AC-3 (run-15).

## AC-4 — speed (DONE)
- **Per-token:** dense 31B ≈ **9–10 tok/s**; MoE ≈ **40–46 tok/s** → the dense
  model is **~4.5× slower per token** (expected: 30.7B active vs 3.8B).
- **Net time-to-verdict:** because g31 converges in 2–4× fewer tokens, the gap
  narrows but does **not** invert. When the MoE *converges*, it wins wall-clock
  (D: 70s vs 202s; E: 49s vs 103s; F: 69s vs 94s). g31 wins wall-clock **only**
  where the MoE rambles (A: 42s with a tool-intent vs 358s with no verdict).
- **Implication for run-15:** a 4.5×-slower Coach in a multi-turn tool-bound loop
  may make each *converged* Coach turn slow. Watch net time-to-verdict per turn.
  If it converges but is impractically slow, the documented fallbacks are the
  **12B dense QAT** (~7 GB, 12B active, faster) or distillation
  ([TASK-DATA-COACHHARVEST](../../../tasks/backlog/TASK-DATA-COACHHARVEST-harvest-claude-era-coach-training-data.md)).

## AC-3 — run-15 falsifier (DEFERRED → recommend GO)
Operator decision 2026-06-08: defer until AC-2 numbers are in. **Recommendation
after AC-2: GO** — run-15 is the *only* test that exercises the tool-bound
agentic loop where run-14 actually failed; single-shot could not settle the
substrate question. Bar: ≥1 Coach turn converges (valid fenced verdict within the
SDK timeout) across ≥4 turns, ≥80% valid (vs run-14's 0/2). Recipe:
[`run-15-recipe.md`](run-15-recipe.md).

## Rollback
Delete the `gemma4-31b` model block + `g31` var + `coach31` set from
`config.yaml` (restore `config.yaml.bak-2026-06-08-pre-coach31b`); `rm -rf
/opt/llama-swap/models/gemma4-31b-coach/`. The route is dormant by default so
leaving it in place is harmless.
