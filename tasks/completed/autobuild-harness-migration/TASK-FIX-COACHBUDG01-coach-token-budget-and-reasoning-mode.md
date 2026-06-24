---
id: TASK-FIX-COACHBUDG01
title: Robust Coach token budget + parser handles reasoning_content + per-model reasoning_mode config
status: completed
task_type: bug
created: 2026-06-06T12:00:00Z
updated: 2026-06-18T00:00:00Z
previous_state: backlog
state_transition_reason: "Reconciled stale 2026-06-06 snapshot: all ACs already landed across guardkit + guardkitfactory (guardkitfactory was 'not on this box' when filed, present now). Closed as completed 2026-06-18."
priority: high
complexity: 5
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: task-work
intensity: standard
effort_hours: 3
falsifier: "After landing, gemma4-coach successfully emits a fenced JSON verdict with `--reasoning auto` (the load-bearing `--reasoning off` llama.cpp flag becomes optional, not required). The `coach_output_parser.extract_and_write` finds the JSON block whether it lives in `content` OR `reasoning_content`. Coach's max_tokens budget accommodates reasoning + structured output without `finish_reason: \"length\"` cutoffs. Live smoke: replay the run-6 turn-1 Coach prompt against gemma4-coach with reasoning ON — ≥4/5 attempts succeed."
tags:
  - autobuild
  - langgraph-migration
  - coach
  - substrate-robustness
  - hybrid-reasoning-models
---

# Task: Robust Coach token budget + hybrid-reasoning-model handling

> **CLOSED 2026-06-18 — completed (all layers landed across both repos).**
> This file was a 2026-06-06 snapshot taken when guardkitfactory was *"not on
> this box"*, so every cross-repo AC was conservatively parked as `BLOCKED ON
> guardkitfactory`. guardkitfactory is present locally now and all of that work
> has since shipped. Evidence verified on disk 2026-06-18:
>
> - **Layer 1 (max_tokens):** `guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py`
>   `_SYNTHESIS_MAX_TOKENS_DEFAULT = 16384` (AC-002, exact target value) +
>   per-role budget threading at `:520` (AC-003). Commit `e8350bd`.
> - **Layer 2 (parser + reasoning_text parity):** guardkit side committed
>   (`d5f1bec6`); guardkitfactory `extract_last_ai_reasoning` in
>   `_aiter_events` (`:616`) surfaces `reasoning_content` on
>   `AssistantMessageEvent.reasoning_text` (AC-005 LangGraph). Commits
>   `e8350bd`, `44634ea` (OpenAI Responses-API reasoning extraction).
> - **Layer 3 (registry):** `guardkitfactory/src/guardkitfactory/harness/model_config.py`
>   `MODEL_CONTEXT_WINDOWS: dict[str, dict[str, Any]]` with per-model
>   `reasoning_mode` + `get_reasoning_mode()` accessor (AC-006/007). Commit `e8350bd`.
> - **Validation:** guardkit-side 11 tests pass (`TestHybridReasoningFallback`
>   7 + `TestThinkingBlockExtraction` 4); guardkitfactory-side
>   `tests/harness/test_model_config.py` 9 pass. AC-009 LangGraph live smoke
>   done via gemma4-coach probe (commit `5340c32`); gating task **HMIG-013 is
>   COMPLETED**. The `--reasoning off` belt-and-braces workaround can now be
>   relaxed to `auto` (it already is on gemma4-coach + qwen36-workhorse).
>
> The `.claude/rules/` seeding follow-on in **Notes** below is deliberately
> **deferred** (the 2×-Spark substrate confirmation bar — HMIG-012 — is still
> open). No code change was required by this closure; it is bookkeeping only.

## Why this task exists

The 2026-06-06 §9.13 finding in `docs/research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md` captured a load-bearing pattern:

> *"Base Gemma 4 IT is a hybrid reasoning model and its embedded chat template defaults to `--reasoning auto`, which detects the template's thinking-mode markers and routes pre-content tokens into `reasoning_content`. With Coach's narrow `max_tokens` budget the thinking phase never finishes, content never emits, and the orchestrator sees an empty Coach turn. That is exactly the F17 failure mode the swap was meant to close — qwen36-workhorse emits prose before JSON; without `--reasoning off`, gemma4-coach would emit reasoning before JSON. **Same disease, different drug.**"*

The current workaround is `--reasoning off` at the llama-swap server level. It works for gemma4-coach but is brittle:

- **Loses reasoning benefit**: For Coach candidates whose reliability comes FROM reasoning (Nemotron-3-Super-120B's 6-hop agentic depth, DeepSeek V4 Flash's Terminal-Bench score), disabling thinking degrades verdict quality.
- **Per-substrate infra config**: Every future Coach-model swap (TASK-HMIG-012's 2× Spark candidates: DeepSeek V4 Flash, Qwen3.5-122B-A10B, etc.) requires manually discovering whether `--reasoning off` is needed.
- **Doesn't generalise**: The orchestrator side will keep producing empty Coach turns whenever a hybrid-reasoning model is deployed without this flag — and the COACHSF01 safety net will fire to mask it, hiding a substrate-quality data point that should drive registry updates.

The robust fix is orchestrator-side: bump the Coach generation budget so reasoning + content both fit, extend the COACHOUT01 parser to find the fenced JSON block in EITHER field, and encode per-model reasoning-mode metadata in `MODEL_CONTEXT_WINDOWS` so future swaps are config-driven.

## What "budget" actually means here

Three different things people call "context" or "KV cache":

| Term | What it means | Status |
|---|---|---|
| **Context window** (`--ctx-size`) | KV-cache storage for input + output. Determines max prompt + response length. | `65536` on gemma4-coach. Plenty. **Not the constraint.** |
| **`max_tokens`** (per generation) | How many tokens the model is ALLOWED to OUTPUT before being cut off. | Currently capped somewhere too tight for reasoning + structured output. **This is the constraint.** |
| **Per-role budget** (orchestrator) | Should Coach get a different budget from Player or specialists? | Currently uniform; should be per-role. |

`finish_reason: "length"` in the §9.13 pre-fix smoke is the smoking gun — it's `max_tokens`, not context window.

## Acceptance Criteria

### Layer 1: Coach max_tokens budget (orchestrator-side)

- [x] **AC-001: COMPLETE 2026-06-06.** `max_tokens` is implicit on the guardkit side: `claude-agent-sdk`'s `ClaudeAgentOptions` does NOT expose a `max_tokens` field (see [`sdk_harness.py`](../../../guardkit/orchestrator/harness/sdk_harness.py) §"Build ClaudeAgentOptions" block — the constructor kwargs do not include it). Anthropic API uses model defaults. The actionable setting site for AC-002 is the `LangChain ChatOpenAI(...)` constructor in `guardkitfactory.harness.langgraph_harness` (separate repo, not on this box). Full investigation summary in findings doc §9.14 "Layer 1 finding".
- [x] **AC-002: COMPLETE (guardkitfactory commit `e8350bd`).** `_SYNTHESIS_MAX_TOKENS_DEFAULT = 16384` at the `LangGraphHarness` synthesis construction site — the exact target value, env-overridable via `GUARDKIT_COACH_SYNTHESIS_MAX_TOKENS`.
- [x] **AC-003: COMPLETE (guardkitfactory commit `e8350bd`).** Per-role `max_tokens` budgets threaded via `role` at the construction site (`langgraph_harness.py:520`).

### Layer 2: Parser handles reasoning_content (orchestrator-side)

- [x] **AC-004: COMPLETE 2026-06-06.** [`coach_output_parser.extract_and_write`](../../../guardkit/orchestrator/coach_output_parser.py) extended with "prefer content, fall through to reasoning" precedence. Searches joined `text` first (canonical); on miss, searches joined `reasoning_text` (hybrid fallback); both empty → raises `CoachDecisionNotFoundError` with COACHSF01 substring AND both channel sizes for operator diagnostics. New module helper `_collect_assistant_reasoning`. Module docstring extended with "Hybrid reasoning models — `reasoning_text` fallback" section.
- [x] **AC-005 SDK side: COMPLETE 2026-06-06.** [`AssistantMessageEvent`](../../../guardkit/orchestrator/harness/adapter.py) extended with optional `reasoning_text: str = ""` field (backwards-compat default). [`sdk_harness._extract_assistant_reasoning`](../../../guardkit/orchestrator/harness/sdk_harness.py) joins all `ThinkingBlock.thinking` fields per Anthropic `AssistantMessage` and populates the new event field. Substrate parity for ADR FB-004 now requires the LangGraph side to populate the same field.
- [x] **AC-005 LangGraph side: COMPLETE (guardkitfactory commits `e8350bd`, `44634ea`).** `langgraph_harness._aiter_events()` populates `AssistantMessageEvent.reasoning_text` via `extract_last_ai_reasoning(result)` (`:616`); follow-on `44634ea` extends extraction to the OpenAI Responses-API `reasoning_content[]` shape. Substrate parity (ADR FB-004) restored.

### Layer 3: Per-model reasoning_mode config (cross-repo: guardkitfactory)

- [x] **AC-006: COMPLETE (guardkitfactory commit `e8350bd`).** `MODEL_CONTEXT_WINDOWS` reshaped to `dict[str, dict[str, Any]]` (`{"ctx_size", "reasoning_mode", "max_tokens_*"}`) with backwards-compatible accessors `get_reasoning_mode()` / legacy int lookups normalised at access time.
- [x] **AC-007: COMPLETE (guardkitfactory commit `e8350bd`).** Registry populated: `qwen36-workhorse` → `reasoning_mode: "off"` (§3.2), `gemma4:26b` → `reasoning_mode: "auto"`; unknown models default to `"auto"`.

### Validation

- [x] **AC-008 parser tests: COMPLETE 2026-06-06.** `tests/unit/orchestrator/test_coach_output_parser.py::TestHybridReasoningFallback` — 7 tests covering content-only, reasoning-only, both-channels-prefer-content, neither-channel-found, both-channels-empty, frozen-dataclass immutability + default-empty backwards-compat, multi-event reasoning stream concatenation. All pass on first run.
- [x] **AC-008 SDK harness tests: COMPLETE 2026-06-06.** `tests/orchestrator/harness/test_sdk_harness.py::TestThinkingBlockExtraction` — 4 tests covering no-thinking-blocks (backwards-compat), text+thinking-extracted-into-separate-fields, thinking-only (§9.14 failure mode), multi-thinking-block concatenation. All pass.
- [x] **AC-008 registry tests: COMPLETE (guardkitfactory).** `tests/harness/test_model_config.py` — 9 tests (reasoning_mode policy per model, legacy-entry normalisation default `auto`, `get_reasoning_mode` accessor). Verified passing 2026-06-18.
- [x] **AC-008 LangGraph reasoning tests: COMPLETE (guardkitfactory).** `tests/harness/test_langgraph_harness.py` — `extract_last_ai_reasoning` + `reasoning_text` surfacing / empty-default cases.
- [x] **AC-009: COMPLETE.** llama-swap runs `--reasoning auto` on both `gemma4-coach` and `qwen36-workhorse`. guardkitfactory commit `5340c32` closed the LangGraph live smoke via a gemma4-coach probe handling the `reasoning_content[]` shape. Gating task **TASK-HMIG-013 is COMPLETED**; the migration exercised this path live through run-15+, and follow-on tasks (COACHTURNBUDGET, COACHREASON01) build directly on this `max_tokens` infrastructure.

## Implementation Notes

- **Investigation first**: AC-001 may find that `max_tokens` is implicit (no explicit setting; inherits from `claude-agent-sdk` or LangChain defaults). If so, the fix is to EXPLICITLY set it via the harness construction path. Document where in the task notes.
- **`reasoning_content` field provenance**: This is OpenAI-compat-extended (`message.reasoning_content` per llama.cpp's `--reasoning auto` output). Check whether `claude-agent-sdk` and `langgraph_harness.py` preserve it through their event-stream parsers. If `AssistantMessageEvent.text` only carries `content`, extend to `AssistantMessageEvent.text + AssistantMessageEvent.reasoning_text`.
- **Backwards-compatible registry**: Existing callers expect `MODEL_CONTEXT_WINDOWS[name]` → int. The shape change must preserve this — either accessor wrappers (`get_ctx_size(name)`, `get_max_tokens(name, role)`, `get_reasoning_mode(name)`) or duck-typing at lookup time. Don't break callers.
- **Substrate parity**: ADR FB-004 already requires both harnesses to emit `AssistantMessageEvent` with `text` populated. Extending to also populate `reasoning_text` (or equivalent) preserves the parity invariant.
- **Cross-repo coordination**: guardkitfactory changes (Layer 3 + Layer 2 parity) ship first, then guardkit (Layer 1 + Layer 2 parser).

## Out of scope

- Investigating reasoning-mode behaviour for nemotron-3-super:120b-a12b, DeepSeek V4 Flash, or other future candidates — that's TASK-HMIG-012's job once the substrate is deployed. This task just adds the *config slot* for them.
- Per-model `temperature`, `top_p`, etc. — also TASK-HMIG-012 territory. Stay focused on max_tokens + reasoning_mode.
- The §9.13 finding's `--reasoning off` workaround stays in place on llama-swap until AC-009 proves the parser fix is sufficient. Belt-and-braces during the transition.

## References

- §9.13 finding doc (the operational evidence and root cause): `docs/research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md`
- COACHOUT01 (Shape A parser the Layer-2 fix extends): `tasks/completed/2026-06/TASK-FIX-COACHOUT01-coach-verdict-emission-contract.md`
- COACHSF01 (safety net the parser substring-couples to): `tasks/completed/2026-06/TASK-FIX-COACHSF01-coach-soft-fail-on-decision-not-found.md`
- TASK-HMIG-013 AC-006 (gates this task's live-smoke validation): `tasks/backlog/autobuild-harness-migration/TASK-HMIG-013-swap-coach-to-gemma4-26b-single-gb10.md`
- TASK-HMIG-012 (post-cutover registry population): `tasks/backlog/autobuild-harness-migration/TASK-HMIG-012-substrate-investigation-2x-spark.md`
- ADR FB-004 (substrate parity invariant for the parser): `.claude/rules/feature-build-invariants.md`
- MODEL_CONTEXT_WINDOWS precedent: TASK-HMIG-002R-MODEL-PROFILE (guardkitfactory commit)

## Notes

The meta-rule worth seeding into `.claude/rules/` post-cutover:

> *"Hybrid reasoning models route generation to `reasoning_content` by default. Orchestrator parsers must check both `content` and `reasoning_content` fields. Coach `max_tokens` budget must accommodate reasoning preamble + structured output — typically 16384 is sufficient. Per-model reasoning_mode metadata in the substrate registry lets future model swaps stay config-driven."*

File as the `.claude/rules/` seeding follow-on once the empirical pattern is confirmed across 2-3 substrates (gemma4-coach + nemotron-3-super + DeepSeek V4 Flash at minimum). For now, capture the lesson in this task's notes — the rule emerges from the empirical evidence as TASK-HMIG-012 populates the registry.
