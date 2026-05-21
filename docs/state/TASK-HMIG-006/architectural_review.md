# Architectural Review — TASK-HMIG-006 (Phase 2.5B)

**Reviewer**: architectural-reviewer (subagent)
**Date**: 2026-05-20
**Plan version reviewed**: v1
**Intensity**: strict (≥70/100 threshold)

## Scores

| Dimension | Score |
|---|---|
| SOLID | 38/50 |
| DRY | 21/25 |
| YAGNI | 19/25 |
| **Overall** | **78/100** |

**Verdict**: APPROVE_WITH_RECOMMENDATIONS — proceed to Phase 2.8 human checkpoint.

## Top strengths

1. D-1 deferral is correctly reasoned — migrating `_track_tool_use` / `_extract_partial_from_messages` now would break AC-008 and rightly waits for cutover-day.
2. Phased implementation (3a → 3b → 3c → 3d → 3e) limits blast radius per sub-phase.
3. OQ-3 (`selector.py` vs `__init__.py`) correctly preserves `adapter.py` as a pure abstract surface.
4. Three follow-up tasks (006.1, 006.2, 006.3) named and tied to specific unresolved concerns — scope hygiene done right.
5. Lazy-import diagnostic for LangGraph mirrors existing SDK ImportError pattern (consistent operator experience).

## Concerns (severity-ordered)

| Severity | Concern | Recommendation |
|---|---|---|
| MEDIUM | `ValueError` translation ambiguity after refactor — orchestrator's `except ValueError` becomes structurally ambiguous (harness vs orchestrator-layer `ValueError` indistinguishable) | In `ClaudeSDKHarness.invoke()`, catch and re-raise `ValueError` from the translation loop as `AgentInvocationError(error_class="ValueError")` before it escapes the harness |
| MEDIUM | AC-004 parity test risks false-green on tool-call sub-schema (per `.claude/rules/absence-of-failure-is-not-success.md` — schema-subset check with empty fixture is the same "count_attempted=0" pattern) | Add one tool-call-exercising fixture on the LangGraph stub path, OR explicitly document `tool_calls: []` as a Wave-2 divergence in `harness/README.md` |
| LOW | `_install_sdk_cleanup_handler` placement (init vs invoke) has different semantics under instance reuse — not resolved in plan v1 | Clarify before Phase 3b: harness instances are single-use per turn or shared across turns? Recommendation: single-use, place in `invoke()` |
| LOW | `_emit_llm_call_event` will emit null token counts on LangGraph path; downstream consumers silently receive null | Document as known degradation in `harness/README.md` |
| LOW | `from lib.factory_guards import ...` in `langgraph_harness.py` (already merged as HMIG-001B) uses bare `lib` namespace — triggers `.claude/rules/namespace-hygiene.md` shadow-hazard pattern | Note for Phase 5 code review and cutover-day flip; not a blocker for this task |

## Detailed scrutiny of plan decisions

### D-1 (`event.raw` channel)

Pragmatic leaky abstraction, not a clean separation. The ABC's `AssistantMessageEvent.raw: object | None` field is the acknowledged escape hatch (see `adapter.py` module docstring honesty). Acceptable for Wave 2 *if* TASK-HMIG-006.2 is filed before this task closes.

**One concrete gap**: plan does not state what `_emit_llm_call_event` receives on the LangGraph path. Token extraction will return null counts. Downstream dashboards/Graphiti capture silently receive null. Document in README.

### D-3 (orchestrator-side concerns stay)

Seam correctly drawn. `asyncio.timeout` as defence-in-depth outside the harness is the right call. `_cancel_monitor` correctly stays in orchestrator (feature-level signal, not per-invocation). Single concern: `_install_sdk_cleanup_handler` placement → see LOW concern above.

### D-4 (exceptions translate inside harness) — **weakest seam**

Currently `_invoke_with_role` catches 5 exception types. Plan moves `CLINotFoundError`/`ProcessError`/`CLIJSONDecodeError` translation into `ClaudeSDKHarness` but leaves `ValueError` and generic `Exception` in `agent_invoker.py`. Post-refactor, the orchestrator's `except ValueError` becomes structurally ambiguous (origin could be harness translation loop, `select_harness()`, event dispatch, or `_emit_llm_call_event`). Recommended fix is to make the harness the single point of all SDK-exception normalisation.

### Cross-repo dependency direction

Bidirectional smell (guardkit → guardkitfactory at install, guardkitfactory → guardkit at import). Mitigated by lazy import + autobuild optional dep group. Residual debt: implicit coupling via `_translate_kwargs_for_langgraph()` helper that needs documentation in README. Not a must-fix today.

### OQ-1 (guardkitfactory PyPI availability)

Correctly escalated to Phase 2.8 checkpoint. Do not block plan on it.

### AC-004 byte-compat parity test (most important concern)

Plan proposes schema-subset parity (variant b). Risk matches the documented `absence-of-failure-is-not-success` pattern: a schema-subset check that only asserts key presence and top-level types passes when value is `[]` vs populated list — does not catch value-structural divergence.

> "Pair every `count_failed == 0` rule with `count_attempted > 0`."

Analog here: pair every schema-equality assertion with a fixture that exercises the non-empty case. Add at least one tool-call-exercising fixture, OR mark `tool_calls: []` as an explicit Wave-2 divergence in README (converts potential false-green into a documented known divergence).

## Pre-Phase-2.8 actions completed

- [x] Plan updated with D-4 ValueError fix
- [x] Plan updated with AC-004 tool-call fixture commitment
- [x] Plan updated with `_install_sdk_cleanup_handler` placement decision (`invoke()`, single-use harness)
- [x] Plan updated with LangGraph-path degradation documentation requirement (null tokens, empty tool_calls)
- [x] Note re: `lib.factory_guards` namespace-hygiene flag added to Phase 5 risks
