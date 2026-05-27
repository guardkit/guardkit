---
id: TASK-HMIG-006.4
title: Migrate TaskWorkInterface._execute_via_sdk (pre-loop design phase) through HarnessAdapter
task_type: implementation
status: completed
created: 2026-05-27T15:30:00Z
updated: 2026-05-27T17:00:00Z
completed: 2026-05-27T17:00:00Z
completed_location: tasks/completed/2026-05/
previous_state: in_review
state_transition_reason: "All ACs met; quality gates passed (141 tests green, line cov 81% ≥80%, branch ~97% ≥75%)"
priority: critical
complexity: 6
effort_hours: 6
parent_task: TASK-HMIG-006
parent_review: TASK-REV-HM09
feature_id: FEAT-HMIG
parent_feature: hmig-pre-canary-fixes
wave: 1
conductor_workspace: hmig-pre-canary-fixes-wave1-1
implementation_mode: task-work
intensity: standard
depends_on:
  - TASK-HMIG-006   # Wave-2 — establishes the HarnessAdapter substrate seam
related_tasks:
  - TASK-HMIG-006.1   # Sibling — direct-mode TaskWork dispatch
  - TASK-HMIG-006.2   # Sibling — downstream helpers
  - TASK-HMIG-006.3   # Sibling — Coach independent SDK
  - TASK-HMIG-009A    # Unblocks the partial canary
  - TASK-REV-PL01     # Earlier pre-loop architecture review
tags:
  - autobuild
  - harness
  - langgraph-migration
  - pre-loop
  - pre-canary-blocker
  - cutover-day-blocker
falsifier: "After fix, `guardkit autobuild task TASK-{fixture} --pre-loop` with `GUARDKIT_HARNESS=langgraph` produces ZERO `claude_agent_sdk.subprocess_cli` log lines during the design phase. Verifiable in <5min via grep on stderr.log."
---

# Task: Migrate pre-loop design phase through HarnessAdapter

## Description

TASK-HMIG-006 migrated `agent_invoker._invoke_with_role` through `HarnessAdapter`, and three follow-ups (006.1/.2/.3) cover three other SDK call sites in `agent_invoker.py` and `coach_validator.py`. **A fourth SDK call site at `guardkit/orchestrator/quality_gates/task_work_interface.py:_execute_via_sdk` was missed** — surfaced by the TASK-HMIG-009 canary pilot ([TASK-REV-HM09 review report §1](../../../.claude/reviews/TASK-REV-HM09-review-report.md#1-ac-001--f1-dispatch-chain-diagnosis)).

This task closes that fourth boundary. The pre-loop design phase (Phases 1.5–2.8) currently imports `claude_agent_sdk.query` directly at [`task_work_interface.py:438-450`](../../../guardkit/orchestrator/quality_gates/task_work_interface.py#L438-L450) regardless of `GUARDKIT_HARNESS`, causing every `autobuild task --pre-loop` invocation to silently bypass the harness adapter.

## Why this matters

Without this fix, the LangGraph cutover delivers only partial migration: `GUARDKIT_HARNESS=langgraph` switches the Player-Coach loop (TASK-HMIG-006 covered) but the design phase always uses claude-agent-sdk. This contests HMIG-006's "agent_invoker through HarnessAdapter" completion claim and means **claude-agent-sdk cannot be removed as a hard dependency post-cutover** — defeating the migration's primary value.

## Acceptance Criteria

- [x] **AC-001** — `task_work_interface.py:_execute_via_sdk` no longer imports `claude_agent_sdk` directly. Instead it routes through `select_harness()` (just like `agent_invoker._invoke_with_role`). *Verified: zero `import claude_agent_sdk` statements remain (only docstring/comment references); `select_harness` imported + used at `_execute_via_sdk`.*
- [x] **AC-002** — `_translate_kwargs_for_langgraph` at [`harness/selector.py`](../../../guardkit/orchestrator/harness/selector.py) extended to translate the four additional SDK-only kwargs used by the pre-loop:
  - `setting_sources=["project"]` — chose **option (a)**: no-op on the LangGraph path (DeepAgents loads its default context). Dropped with a debug-level trace mirroring `resume_session_id`; documented in the translator docstring. The SDK harness gained a `setting_sources` constructor param (default `["project"]`) so the kwarg flows through `select_harness()` without `TypeError`.
  - `max_turns=25` — already dropped by the translator (returns `{"model": ...}`); documented.
  - `allowed_tools=[...]` — already dropped; documented (DeepAgents built-in tool surface used).
  - `permission_mode="acceptEdits"` — already dropped; documented (deferred to TASK-HMIG-002R).
- [x] **AC-003** — Tests at `tests/unit/test_task_work_interface.py` (actual path; the AC's `tests/orchestrator/quality_gates/` path does not exist) pass on the SDK path. The SDK-message-iteration tests were re-pointed to mock at the harness seam (the architecturally correct boundary), since the SDK iteration now lives in `ClaudeSDKHarness`. The end-to-end `TestSDKOptionsForInlineProtocol` SDK-path assertions (setting_sources=["project"], max_turns=25, no Skill/Task) still pass unchanged.
- [x] **AC-004** — `TestHarnessDispatch.test_routes_through_select_harness` asserts `select_harness()` is invoked; `TestSubstrateParity.test_identical_events_yield_identical_result` asserts the raw `DesignPhaseResult` dict is identical between an SDK-shape stream (raw populated) and a LangGraph-shape stream (raw `None`).
- [x] **AC-005** — Falsifier implemented as a cheap, CI-able test (`TestFalsifierNoSdkOnLangGraph.test_langgraph_design_phase_never_calls_sdk`): with `GUARDKIT_HARNESS=langgraph` the **real** `select_harness` dispatch runs (only `LangGraphHarness.invoke` is stubbed), and `claude_agent_sdk.query` is asserted to have **zero** calls. The full `guardkit autobuild task --pre-loop` smoke needs a live LLM — see manual smoke step in Completion Notes.
- [x] **AC-006** — `guardkit/orchestrator/harness/README.md` "Wave-2 LangGraph divergences" table gained a pre-loop design-phase row marked **"Fixed in TASK-HMIG-006.4 (this task)"** with explanatory prose.

## Implementation Notes

The Phase 3b refactor pattern is already established by TASK-HMIG-006 — replicate the dispatch shape at the new site. Main complication is `setting_sources` translation: DeepAgents has no direct analogue. Options:

- **(a)** No-op the translation; document that the LangGraph path always loads the default DeepAgents context.
- **(b)** Add a context-injection hook to `LangGraphHarness.invoke()` that mirrors the project-sources loading. Larger scope.

Recommend (a) for this task; defer (b) to a separate task if needed.

## References

- Parent review: [TASK-REV-HM09 review report §3, §5](../../../.claude/reviews/TASK-REV-HM09-review-report.md#3-ac-003--f1-remediation-recommendation)
- Canary evidence: [`docs/state/TASK-REV-HMIG/canary-analysis.md` §3.F1](../../../docs/state/TASK-REV-HMIG/canary-analysis.md#f1-pre-loop-design-phase-bypasses-the-harness-adapter)
- Established pattern: TASK-HMIG-006 commit `eaf6a1d5f` (`agent_invoker.py:_invoke_with_role`)
- Sibling tasks: TASK-HMIG-006.1, .2, .3

## Completion Notes (2026-05-27)

### Files changed (this task only)
- `guardkit/orchestrator/quality_gates/task_work_interface.py` — `_execute_via_sdk` rewritten to route through `select_harness()` + `harness.invoke()`; `asyncio.timeout`/`async_heartbeat` wrappers kept orchestrator-side (D-3); SDK-missing `AgentInvocationError`(cause=`ImportError`) re-raised as `ImportError` to preserve the subprocess fallback; all other harness failures → `DesignPhaseError`. Module + class docstrings updated.
- `guardkit/orchestrator/harness/sdk_harness.py` — added optional `setting_sources` constructor param (default `["project"]`, backward-compatible); `invoke()` uses it instead of the hardcoded literal.
- `guardkit/orchestrator/harness/selector.py` — `_translate_kwargs_for_langgraph` now documents + debug-logs the `setting_sources` drop (option (a) no-op).
- `guardkit/orchestrator/harness/README.md` — pre-loop divergence row added, marked fixed.
- Tests: `tests/unit/test_task_work_interface.py` (new `TestHarnessDispatch`, `TestHarnessExceptionHandling`, `TestSubstrateParity`, `TestFalsifierNoSdkOnLangGraph`, `TestParseSDKOutputRobustness`), `tests/orchestrator/harness/test_selector.py` (+setting_sources translation/dispatch), `tests/orchestrator/harness/test_sdk_harness.py` (+setting_sources default/forwarding), `tests/unit/test_sdk_environment_parity.py` (grep assertion updated to `event.raw`).

### Design decisions
- **setting_sources translation = option (a)** (no-op; LangGraph loads default DeepAgents context). Option (b) context-injection deferred per the task's Implementation Notes recommendation.
- **ToolResultBlock-in-AssistantMessage extraction dropped intentionally.** Real SDK streams never nest tool-result content inside `AssistantMessage`s (tool results arrive as separate messages the pre-migration loop never handled), so collecting `event.text` is full parity for production. Reaching into `event.raw` for tool blocks would work against the harness design (tool-event explosion is reserved for TASK-HMIG-006.2). The one artificial test asserting that path was re-pointed to the harness seam.

### Quality gates
- `tests/unit/test_task_work_interface.py`: 99 passed. Module line coverage 73% → **81%** (≥80%); branch ~97% (≥75%). Remaining uncovered lines are pre-existing untested methods (`_execute_via_subprocess`, `execute_security_review`, `_parse_design_result`, parts of `_parse_sdk_output`) — out of scope, untouched.
- Harness suites (`tests/orchestrator/harness/`): all pass. AC-008 player/coach regression surface (`test_agent_invoker_sdk_errors`, `test_coach_sdk_stream_resilience`, `test_specialist_observability`, `test_llm_call_events`, `test_agent_invoker_langgraph`): 46 passed — shared `ClaudeSDKHarness` change is backward-compatible.

### AC-005 manual smoke step (full-run form)
The cheap falsifier (`test_langgraph_design_phase_never_calls_sdk`) is in CI. The full-run falsifier from the frontmatter requires a live LLM and is a manual step:
```bash
GUARDKIT_HARNESS=langgraph guardkit autobuild task TASK-<small-fixture> --pre-loop 2>stderr.log
# Expect ZERO matches:
grep -c "claude_agent_sdk.subprocess_cli" stderr.log   # → 0 in the design phase
```

### Out-of-scope observations (NOT changed)
- `guardkit/cli/autobuild.py` is modified in the working tree by sibling task **TASK-FIX-WTBC** (base-branch detection). Left untouched — it must not be folded into this task's commit.
- Pre-existing test failures unrelated to this task (confirmed by stashing source changes and re-running): `test_agent_invoker_task_work_implement_checks_error` (grep test for `agent_invoker.py`, stale since TASK-HMIG-006), the 5 `TestSlimProtocolRouting` cases, `test_max_turns_uses_constant`, `test_invoke_with_role_always_uses_project_setting_sources`, 2 `test_autobuild_preloop` integration tests, `test_task_work_sdk_max_turns_is_50`, and 14 in `test_digest_content`/`test_design_context_integration`. These predate this change and are out of scope.
