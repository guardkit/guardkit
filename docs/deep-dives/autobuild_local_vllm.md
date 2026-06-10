# AutoBuild on a local vLLM / llama-swap substrate

> **Scope.** How AutoBuild's Player–Coach loop is backed by local models on
> the Dell ProMax GB10 (DGX Spark) instead of the Anthropic API, which model
> plays which role, and the known substrate caveats. Created by
> TASK-HMIG-009A (2026-05-27, AC-007).

## Canonical AutoBuild Player model

**The canonical AutoBuild Player model is `qwen-coder-next` (Qwen3-Coder-Next
FP8).** This is the single source of truth for local-substrate AutoBuild runs
and for the LangGraph-migration canary (TASK-HMIG-009 / 009A / 009B).

Source of truth — [`docs/research/dgx-spark/gb10-model-requirements-matrix.md`](../research/dgx-spark/gb10-model-requirements-matrix.md),
"Cluster B: The Coder" (role **R3 — AutoBuild Player**):

| Candidate | Footprint | tok/s | Notes |
|-----------|-----------|-------|-------|
| **Qwen3-Coder-Next FP8** | ~60 GB | 32.9 | **Current. Proven with AutoBuild** |
| Qwen3-Coder-Next int4-AutoRound | ~35 GB | 66.7 | 2× faster, pending A/B test |
| Qwen3.6-27B FP8 (dense) | ~27 GB | TBD | Wildcard |

Corroborated by the system-architecture intent doc
[`docs/research/dev-pipeline-system/ships-computer-system-arch-intent.md`](../research/dev-pipeline-system/ships-computer-system-arch-intent.md):
the *Dell ProMax Build Agent* runs "vLLM + Qwen3-Coder-Next (local)" and "handles
all non-FinProxy AutoBuild work at zero per-token cost".

### Models that are NOT the AutoBuild Player

These are deliberately called out because they have been mistaken for the
Player model and have polluted earlier canary methodology:

- **`qwen3-coder-30b`** — **not** an AutoBuild Player model. It does not appear
  in the requirements matrix's Cluster B. An undocumented, non-operator-approved
  swap to this model some time after 2026-04-29 is the suspected cause of the
  canary "F2 — local Qwen fails marker contract" finding
  ([`canary-analysis.md` §3.F2](../state/TASK-REV-HMIG/canary-analysis.md)). If
  a future need arises to offer it as an additional Player option, file a
  separate task and run its own marker-contract audit — do not assume it
  inherits qwen-coder-next's proven status.
- **`qwen36-workhorse`** — the **Reasoner** cluster (Cluster C), used for the
  AutoBuild **Coach** / Jarvis / orchestrator roles, **not** the Player. Per
  the live runbook config it is a llama.cpp `cmd:`-managed entry on the GB10.

## How AutoBuild reaches the local substrate

Both harnesses route through the GB10's llama-swap **front door at
`http://promaxgb10-41b1:9000`**, which routes by the `model` field of each
request to whichever llama.cpp backend currently holds that model:

| Harness | Env var | Endpoint | Model string |
|---------|---------|----------|--------------|
| `sdk` | `ANTHROPIC_BASE_URL` | `http://promaxgb10-41b1:9000` | `qwen-coder-next` |
| `langgraph` | `OPENAI_BASE_URL` | `http://promaxgb10-41b1:9000/v1` | `openai:qwen-coder-next` |

llama-swap exposes both OpenAI (`/v1/chat/completions`, `/v1/embeddings`) and
Anthropic (`/v1/messages`, `/v1/messages/count_tokens`) surfaces on the same
port; the Anthropic surface is what lets the claude-agent-sdk Player target a
local model by string.

## Live deployment status (verified 2026-05-27, TASK-HMIG-009A AC-001A)

> ⚠️ **As of 2026-05-27, `qwen-coder-next` is NOT deployed on the live GB10
> llama-swap.** This is a config-drift blocker, not a model-choice change.

`GET http://promaxgb10-41b1:9000/v1/models` returns `architect-agent`,
`gemma4-tutor`, `nomic-embed`, `qwen-graphiti`, `qwen3-coder-30b`,
`qwen36-workhorse` — **`qwen-coder-next` is absent.** A direct completion to
`qwen-coder-next` returns `could not find suitable inference handler`; port
8002 refuses connection; `qwen3-coder-30b` answers normally.

Root cause is a documentation/deployment divergence:

- [`docs/research/dgx-spark/llama-swap-config.yaml`](../research/dgx-spark/llama-swap-config.yaml)
  **does** define `qwen-coder-next` (lines 72–90, a llama.cpp `cmd:` entry
  pointing at `/opt/llama-swap/models/qwen3-coder-next/Qwen3-Coder-Next-FP8.gguf`)
  — but that file is **marked HISTORICAL** at line 4 (pre-llamacpp-migration,
  2026-04-29) and names
  [`RUNBOOK-v3-production-deployment.md`](../research/dgx-spark/RUNBOOK-v3-production-deployment.md)
  §5.2 as the live source-of-truth.
- The runbook's live config block defines `qwen36-workhorse`, `gemma4-tutor`,
  `qwen-graphiti`, `nomic-embed` — but **not** `qwen-coder-next` and not
  `qwen3-coder-30b` (which the live server nonetheless serves, so the live
  config has drifted from the runbook too).

**Remediation (GB10-shell action):** add the `qwen-coder-next` builders-group
entry to `/opt/llama-swap/config/config.yaml` (per the historical
`llama-swap-config.yaml:72-90` block), ensure the GGUF is present at
`/opt/llama-swap/models/qwen3-coder-next/Qwen3-Coder-Next-FP8.gguf`, reload
llama-swap, and re-run the AC-001A curl smoke until `/v1/models` lists
`qwen-coder-next` and a completion returns 200 with non-empty content. Update
the runbook in the same change so the documented and live configs reconverge.

## Known substrate caveats

- **Tool-call / marker contract under the pre-loop SDK path (F2).** Earlier
  pilots burned 10–17 SDK turns in the pre-loop design phase without emitting
  any `tool_use` blocks or writing files — but those pilots ran
  `qwen3-coder-30b` / `qwen36-workhorse`, **not** the canonical
  `qwen-coder-next`. Whether F2 reproduces on `qwen-coder-next` is the open
  question gated behind AC-001A/B and must be re-checked once the model is
  actually deployed. The llama.cpp config uses `--jinja --reasoning off`; if
  tool-use parsing misbehaves, inspect the tool-call-parser plumbing for the
  active alias.
- **Throughput (F8).** Local-Qwen runs are ~5–10× slower than the Anthropic
  Sonnet baseline the original canary thresholds were calibrated against. Budget
  wall-clock accordingly (a single pilot rep took ~2h 16min).
- **Base honesty rate (F6).** Player honesty-failure rate (fabricated
  `files_modified` lists) is materially higher on local Qwen than on Sonnet.
  The Coach honesty guards (F5) catch this, but each false claim costs a turn —
  so first-pass-success rates reflect substrate quality, not only harness
  wiring.

## B-full Coach latency budgeting (TASK-PERF-COACHTURNBUDGET)

When the investigating B-full Coach is enabled (`GUARDKIT_COACH_GATHER=1`,
TASK-ARCH-COACHBFULL), a Coach turn runs a tool-using **gather** (Phase A) then a
toolless **synthesis** (Phase B). On a dense hybrid-reasoning model
(`gemma4:31b` under `--reasoning auto`) the synthesis latency is dominated by
`reasoning_content` generation grinding toward the `max_tokens` ceiling — run-23
TP05 took **41m43s** (a 16384-token grind) and the 80-min task budget was
exhausted **before** the Player could apply the fix the Coach correctly caught
(`TIMEOUT_BUDGET_EXHAUSTED`). A reviewer that catches bugs but starves the fix
cycle is only half a loop.

Three levers bound this. Two are operator/substrate-side, one is in code:

- **g31 residency (Lever 1, ops).** Keep `gemma4:31b` resident across Player
  turns so it is not cold-loaded (~50 GB) every Coach turn. This is a llama-swap
  keepalive policy on the GB10 — tracked under **TASK-OPS-COACH31B**, not a code
  change.
- **Reasoning curtailment (Lever 2).** The actual latency driver is the thinking
  phase, not the verdict. Two knobs, both leaving the verdict substance
  (`criteria_verification` + `issues`) intact — do **not** just lower
  `max_tokens`, which truncates the bug report:
  - **Server-side:** the llama-swap `--reasoning` budget flag for the `coach31`
    set (operator policy; the `reasoning_mode` field in
    `guardkitfactory…model_config.MODEL_CONTEXT_WINDOWS` documents intent only).
  - **Per-request (code, default-off):** set
    `GUARDKIT_COACH_SYNTHESIS_REASONING_BUDGET` to an int to inject
    `reasoning_budget` into the toolless-synthesis request body (llama.cpp
    semantics: `0` disables thinking, `-1` unlimited, `N` caps). Unset → field
    omitted → behaviour unchanged. The synthesis generation budget itself stays
    independent of the gather's via `GUARDKIT_COACH_SYNTHESIS_MAX_TOKENS`
    (default 16384). GB10/`gemma4:31b` live support for the wire-field is
    confirmed at the catch→fix falsifier run (AC-4).
- **Task budget for ≥2 turns (Lever 3, config).** A catch→fix cycle is **two**
  Coach turns. The per-task budget is `--task-timeout` (default 2400s, floored at
  3000s by `GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR`, then × the local
  `GUARDKIT_TIMEOUT_MULTIPLIER`, default 4.0). For B-full runs set
  `--task-timeout` high enough that **one** B-full turn is ≤ ~50% of the budget,
  so a second turn fits. Until per-turn latency is cut (Levers 1–2), raising the
  budget is the explicit interim stopgap; the real fix is latency, not budget.

## References

- Model source of truth: [`gb10-model-requirements-matrix.md`](../research/dgx-spark/gb10-model-requirements-matrix.md)
- System-arch intent: [`ships-computer-system-arch-intent.md`](../research/dev-pipeline-system/ships-computer-system-arch-intent.md)
- Live llama-swap config source-of-truth: [`RUNBOOK-v3-production-deployment.md`](../research/dgx-spark/RUNBOOK-v3-production-deployment.md) §5.2
- Historical (drifted) config: [`llama-swap-config.yaml`](../research/dgx-spark/llama-swap-config.yaml)
- Canary set + scope variants: [`.guardkit/autobuild/TASK-REV-HMIG-canary-set.json`](../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json)
- Canary analysis (F1–F8 findings): [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../state/TASK-REV-HMIG/canary-analysis.md)
- Canary runner: [`scripts/canary_validation_runner.py`](../../scripts/canary_validation_runner.py)
