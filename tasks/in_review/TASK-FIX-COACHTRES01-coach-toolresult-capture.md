---
id: TASK-FIX-COACHTRES01
title: Capture real tool output in the Coach SDK independent-test path (emit ToolResultEvent on both substrates)
task_type: feature
parent_review: TASK-REV-COSE
feature_id: FEAT-HARV
status: in_review
created: 2026-06-26T00:00:00+00:00
updated: 2026-06-26T00:00:00+00:00
priority: high
tags:
  - autobuild
  - coach-validator
  - harness
  - sdk
  - langgraph
  - cross-repo
  - capture-fix
complexity: 4
implementation_mode: task-work
dependencies: []
---

# Task: Capture real tool output in the Coach SDK independent-test path

## Description

This is the **implementation of TASK-REV-COSE option (a)** — the *capture
fix*, chosen over option (b) (default `coach_test_execution=subprocess`)
because it keeps the SDK independent-test path a **real oracle** rather than
retiring it.

The Coach's SDK independent-test path (`_run_tests_via_sdk`,
`coach_validator.py`) asks a Coach agent to run pytest via Bash, then reads
the captured `output_text` for pass/fail markers. **Pre-fix, neither harness
surfaced the Bash tool's output**:

- **SDK harness** (`sdk_harness.py`) handled `AssistantMessage` /
  `ResultMessage` / `ToolUseEvent` but **dropped** the `UserMessage` carrying
  the `ToolResultBlock` (the tool's stdout) — see the former "other messages"
  drop branch and the `ToolResultEvent` note at the consumer.
- **LangGraph harness** (`guardkitfactory/.../langgraph_harness.py`) emitted
  `ToolUseEvent` from `AIMessage.tool_calls` but never walked the
  `ToolMessage` history for tool *results*.

So `bash_output` stayed `None` and the only captured text was the Coach
agent's **narration** (`collected_text`, e.g.
`"I'll run the test command and show you the full output."`). The pass/fail
heuristic then found no marker — the FEAT-HARV narration-capture defect, where
TASK-HARV-003 stalled while the deterministic subprocess pytest passed
**8601/8601** every turn. Because the capture depends on the Coach LLM's
response shape, it was **flaky run-to-run** (wave-1 002/004 passed in one run,
went absent in the next).

The adapter already defines `ToolResultEvent` (in the `HarnessEvent` union),
and the consumer in `_run_tests_via_sdk` already has a (formerly dead)
`ToolResultEvent` branch that prefers `bash_output` over `collected_text`. The
fix is therefore **purely additive at the harness layer**: emit the event both
substrates were dropping. No consumer change needed.

## Acceptance Criteria

- [x] SDK harness emits one `ToolResultEvent` per `ToolResultBlock` in a
      `UserMessage` (`tool_use_id` / `content` / `is_error`), duck-typed by
      class name (no new SDK import), placed before the terminal
      `ResultMessageEvent` so the consumer (which breaks on
      `ResultMessageEvent`) captures it.
- [x] LangGraph harness emits one `ToolResultEvent` per `ToolMessage` in the
      `ainvoke` result history (`_iter_tool_result_events`, mirroring
      `_iter_tool_use_events`), `status == "error"` → `is_error=True`.
- [x] Consumer (`_run_tests_via_sdk`) unchanged — the real `bash_output` now
      flows into the existing pass/fail determination, replacing narration.
- [x] No new absent-routing: a genuine failure still blocks
      (`tests_passed=False`, `signal_absent=False`); a collection error still
      classifies `collection_error` → conditional-approve; a true pass →
      `tests_passed=True`. The change only makes the SDK path *deterministic*
      instead of narration-flaky.
- [x] Unit tests both substrates: SDK (`test_sdk_harness.py::TestToolResult
      Translation`, 4 tests), LangGraph
      (`test_langgraph_harness.py::TestToolResultParity`, 3 tests).
- [x] Cross-repo seam test guarding the contract against a guardkitfactory
      version skew (`test_xrepo_contract_seam.py::TestToolResultEmission
      Contract`, 2 tests).
- [x] No regression to the harness suites (SDK 36, LangGraph 41) or the
      coach-validator / runtime-parity / smoke suites.

## What landed

| Layer | File | Change |
|---|---|---|
| SDK harness | `guardkit/orchestrator/harness/sdk_harness.py` | import `ToolResultEvent`; new `UserMessage`/`ToolResultBlock` → `ToolResultEvent` branch |
| LangGraph harness | `guardkitfactory/src/guardkitfactory/harness/langgraph_harness.py` | import `ToolResultEvent`; `_iter_tool_result_events`; emit in `invoke` after tool-use events |
| SDK tests | `tests/orchestrator/harness/test_sdk_harness.py` | `TestToolResultTranslation` (4) |
| LangGraph tests | `guardkitfactory/tests/harness/test_langgraph_harness.py` | `TestToolResultParity` (3) |
| Seam test | `tests/orchestrator/harness/test_xrepo_contract_seam.py` | `TestToolResultEmissionContract` (2) |

## Relationship to COSE / DF44

- **TASK-REV-COSE** owns the *capture* diagnosis. This task is its
  implementation (option a). COSE can be closed referencing this.
- **TASK-FIX-DF44** owns *classification + approval*. Its original core
  (`collection_error` classification + conditional approval) is **already on
  main** (landed by TASK-FIX-1D70, `coach_validator.py:6838` + `:2230`). Its
  remaining work is the **absent-vs-classified asymmetry** (Guard #6 treating
  an absent signal as *stricter* than a classified failure) — a robustness
  item now **dormant for the default flow** because the capture fix makes the
  SDK path produce real markers, so a no-marker absent capture is rare. Left
  as a follow-up, not a harvest blocker.

## Out of scope / follow-ups

- The absent-vs-classified asymmetry (DF44 remainder).
- The 5 pre-existing stale tests in `test_coach_sdk_stream_resilience.py`
  (they assert raw `pytest.raises(RuntimeError/ProcessError/CLINotFoundError)`
  but the harness boundary now normalises those to `AgentInvocationError` —
  TASK-HMIG-006.3 staleness; pristine-main baseline is 7 failed, this fix
  reduces it to 5). Pre-existing, unrelated to tool results.

## Rule / design references

- `.claude/rules/per-task-green-is-not-feature-green.md`,
  `.claude/rules/absence-of-failure-is-not-success.md` (the low-fidelity
  independent-test oracle family this capture fix sharpens).
- Handoff: `docs/handoff/autobuild-coach-test-gathering-handoff-2026-06-26.md`.
