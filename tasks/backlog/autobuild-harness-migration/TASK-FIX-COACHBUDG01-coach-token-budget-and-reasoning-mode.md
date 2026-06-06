---
id: TASK-FIX-COACHBUDG01
title: Robust Coach token budget + parser handles reasoning_content + per-model reasoning_mode config
status: backlog
task_type: bug
created: 2026-06-06T12:00:00Z
updated: 2026-06-06T12:00:00Z
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
- [ ] AC-002: Raise Coach `max_tokens` to **16384** at the `LangGraphHarness` `ChatOpenAI(...)` construction site. **BLOCKED ON guardkitfactory** — out of scope for this PR.
- [ ] AC-003: Verify Player + specialist `max_tokens` at the same construction site. **BLOCKED ON guardkitfactory**.

### Layer 2: Parser handles reasoning_content (orchestrator-side)

- [x] **AC-004: COMPLETE 2026-06-06.** [`coach_output_parser.extract_and_write`](../../../guardkit/orchestrator/coach_output_parser.py) extended with "prefer content, fall through to reasoning" precedence. Searches joined `text` first (canonical); on miss, searches joined `reasoning_text` (hybrid fallback); both empty → raises `CoachDecisionNotFoundError` with COACHSF01 substring AND both channel sizes for operator diagnostics. New module helper `_collect_assistant_reasoning`. Module docstring extended with "Hybrid reasoning models — `reasoning_text` fallback" section.
- [x] **AC-005 SDK side: COMPLETE 2026-06-06.** [`AssistantMessageEvent`](../../../guardkit/orchestrator/harness/adapter.py) extended with optional `reasoning_text: str = ""` field (backwards-compat default). [`sdk_harness._extract_assistant_reasoning`](../../../guardkit/orchestrator/harness/sdk_harness.py) joins all `ThinkingBlock.thinking` fields per Anthropic `AssistantMessage` and populates the new event field. Substrate parity for ADR FB-004 now requires the LangGraph side to populate the same field.
- [ ] **AC-005 LangGraph side: BLOCKED ON guardkitfactory.** Populate `AssistantMessageEvent.reasoning_text` from llama.cpp's `message.reasoning_content` (LangChain AIMessage `additional_kwargs['reasoning_content']` or the equivalent v3 LangChain field) inside `langgraph_harness._aiter_events()`. See guardkitfactory follow-on.

### Layer 3: Per-model reasoning_mode config (cross-repo: guardkitfactory)

- [ ] AC-006: Extend `MODEL_CONTEXT_WINDOWS` registry shape. **BLOCKED ON guardkitfactory.**
- [ ] AC-007: Populate the registry for known substrates. **BLOCKED ON guardkitfactory.**

### Validation

- [x] **AC-008 parser tests: COMPLETE 2026-06-06.** `tests/unit/orchestrator/test_coach_output_parser.py::TestHybridReasoningFallback` — 7 tests covering content-only, reasoning-only, both-channels-prefer-content, neither-channel-found, both-channels-empty, frozen-dataclass immutability + default-empty backwards-compat, multi-event reasoning stream concatenation. All pass on first run.
- [x] **AC-008 SDK harness tests: COMPLETE 2026-06-06.** `tests/orchestrator/harness/test_sdk_harness.py::TestThinkingBlockExtraction` — 4 tests covering no-thinking-blocks (backwards-compat), text+thinking-extracted-into-separate-fields, thinking-only (§9.14 failure mode), multi-thinking-block concatenation. All pass.
- [ ] AC-008 registry tests: **BLOCKED ON guardkitfactory.**
- [ ] AC-008 LangGraph reasoning tests: **BLOCKED ON guardkitfactory.**
- [ ] AC-009: Live smoke (gates TASK-HMIG-013 AC-006). **PARTIALLY COMPLETE:** llama-swap already reconfigured with `--reasoning auto` on both `gemma4-coach` and `qwen36-workhorse` as of this revision (preserves the user's empirical state). End-to-end live-data parser smoke (see findings §9.14 "Live-data parser smoke") confirms the Layer-2 contract on this repo's side of the substrate boundary. Full AC-009 (autobuild Player↔Coach loop replay) requires AC-002 + AC-005-LangGraph + AC-006 + AC-007 to land in guardkitfactory first.

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
