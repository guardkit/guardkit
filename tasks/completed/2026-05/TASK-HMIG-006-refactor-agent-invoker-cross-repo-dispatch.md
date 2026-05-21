---
id: TASK-HMIG-006
title: Refactor agent_invoker._invoke_with_role to dispatch through HarnessAdapter (cross-repo import from guardkitfactory)
status: completed
task_type: implementation
created: 2026-05-19T20:30:00Z
updated: 2026-05-21T00:00:00Z
completed: 2026-05-21T00:00:00Z
completed_location: tasks/completed/2026-05/
previous_state: design_approved
state_transition_reason: "All 10 ACs verified, code review APPROVED_WITH_RECOMMENDATIONS (87/100), Phase 5.5 plan audit APPROVED"
priority: critical
complexity: 7
deadline: 2026-06-15
design:
  status: approved
  approved_at: "2026-05-20T00:00:00Z"
  approved_by: "rich@appmilla.com"
  implementation_plan_version: "v3"
  architectural_review_score: 78
  complexity_score: 7
  design_session_id: "design-TASK-HMIG-006-2026-05-20"
  design_notes: |
    Plan v3 folds Phase 2.5B architectural-reviewer recommendations
    (D-4 ValueError fix, D-6 single-use harness, D-7 documented Wave-2
    divergences, AC-004 non-empty fixture per absence-of-failure rule)
    and Phase 2.8 OQ-1 resolution (use [tool.uv.sources] sibling-repo
    editable pattern from jarvis/specialist-agent fleet convention, not
    PyPI / git+https). Ready for implementation via
    `/task-work TASK-HMIG-006 --implement-only` or autobuild.
  plan_path: docs/state/TASK-HMIG-006/implementation_plan.md
  review_path: docs/state/TASK-HMIG-006/architectural_review.md
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 2
parallel_group: 2A
implementation_mode: task-work
intensity: strict
effort_hours: 10
depends_on:
  - TASK-HMIG-001A   # guardkit-side HarnessAdapter ABC
  - TASK-HMIG-001B   # guardkitfactory-side LangGraphHarness skeleton
  - TASK-HMIG-002R   # guardkitfactory-side backend + permissions config
cross_repo:
  imports_from: guardkitfactory.harness.LangGraphHarness
  notes: This task introduces guardkitfactory as a runtime dependency of guardkit. Add `guardkitfactory>=0.1,<1` to guardkit/pyproject.toml. Operator-side uses `pip install -e ../guardkitfactory`; release CI uses the pinned version.
falsifier: "`pytest guardkit/orchestrator/tests/test_agent_invoker.py` — every existing test passes with `GUARDKIT_HARNESS=sdk` (no behavioural regression on the legacy path); new tests pass with `GUARDKIT_HARNESS=langgraph` against a stub model wired via guardkitfactory. Cross-repo smoke: `pip install guardkitfactory` works from a fresh checkout of guardkit (no editable-install hack required for end users; editable is operator-side only). The frozen path `guardkit/orchestrator/agent_invoker.py` is touched but the change is a non-NEW_GATE behavioural-surface refactor, justified by the parent review."
tags:
  - autobuild
  - harness
  - langgraph-migration
  - cross-repo
  - frozen-path-touch
---

# Task: Refactor agent_invoker._invoke_with_role to dispatch through HarnessAdapter

## Description

Refactor `guardkit/orchestrator/agent_invoker.py` so that the SDK-specific code
between lines 2359 and 2613 (per review §3.2-§3.5) moves behind the
`HarnessAdapter` interface defined in TASK-HMIG-001A.

Two adapters implement the interface:

- **`ClaudeSDKHarness`** — wraps the existing SDK import + ClaudeAgentOptions
  construction + `query()` call + async-message-stream loop. Lives in
  `guardkit/orchestrator/harness/sdk_harness.py`. Default through D-7
  (2026-06-08), retained as opt-in fallback through 2026-06-15.
- **`LangGraphHarness`** — imported from `guardkitfactory` (per Revision 2 /
  D-01). Selected when `GUARDKIT_HARNESS=langgraph`.

The selector is the env var `GUARDKIT_HARNESS=sdk|langgraph`. Default is `sdk`
until D-7, then flips to `langgraph` in the same PR (so cutover is a single
config change).

## Acceptance Criteria

- [ ] AC-001: `agent_invoker._invoke_with_role()` becomes substrate-agnostic.
      Reads `os.environ.get("GUARDKIT_HARNESS", "sdk")` and constructs the
      appropriate adapter. Calls `await harness.invoke(...)` and consumes the
      `AsyncIterator[HarnessEvent]`.
- [ ] AC-002: `guardkit/orchestrator/harness/sdk_harness.py` wraps the existing
      SDK invocation. Imports `from claude_agent_sdk import query,
      ClaudeAgentOptions, AssistantMessage, ResultMessage, CLINotFoundError,
      ProcessError, CLIJSONDecodeError`. Adapts the existing message types to
      `HarnessEvent` taxonomy.
- [ ] AC-003: When `GUARDKIT_HARNESS=langgraph`, the import is
      `from guardkitfactory.harness import LangGraphHarness`. Lazy import (only
      when the env var is set) so that guardkitfactory does not need to be
      installed for `GUARDKIT_HARNESS=sdk` paths.
- [ ] AC-004: Both adapters produce byte-compatible `player_turn_N.json` /
      `coach_turn_N.json` files on disk. Existing downstream consumers
      (CoachValidator, CoachVerifier, synthetic-report path, Graphiti capture)
      are not modified by this task.
- [ ] AC-005: Add `guardkitfactory>=0.1,<1` to `pyproject.toml`
      (or whatever the actual minimum version is after TASK-HMIG-001B lands).
      Use the portfolio-Python-pinning standard (see
      `docs/guides/portfolio-python-pinning.md`).
- [ ] AC-006: `guardkit doctor` (or equivalent diagnostic) reports the active
      harness when invoked, including version of guardkitfactory if importable.
- [ ] AC-007: Resume support: the SDK adapter preserves session_id capture
      (review §3.2 lines 2599-2613); the LangGraph adapter either supports
      resume or explicitly returns `supports_resume = False` and the orchestrator
      handles the absence gracefully (no crash on resume request).
- [ ] AC-008: Existing tests in `tests/orchestrator/test_agent_invoker.py`
      continue to pass with `GUARDKIT_HARNESS=sdk` (no behavioural regression
      on the legacy path).
- [ ] AC-009: New tests in `tests/orchestrator/test_agent_invoker_langgraph.py`
      cover the LangGraph dispatch path using a stub model and a fixture worktree.
- [ ] AC-010: A README note in `guardkit/orchestrator/harness/README.md`
      documents the substrate switch, the cross-repo dependency, and the
      cutover-day flip from `sdk` to `langgraph`.

## Implementation Notes

- This task touches frozen path `guardkit/orchestrator/agent_invoker.py`. The
  TASK-REV-ABST freeze closed 2026-05-17 (two days before this work starts),
  so an override is no longer required. However, the change is a NEW_GATE-adjacent
  refactor; document the rationale in the commit message and reference review
  §10.
- Use `Protocol` or `ABC`? — the parent review §2.4 picks `ABC`. Stick with that.
- Heartbeat logging: preserve the existing SDK-side heartbeat loop at
  `agent_invoker.py:2545+`. The LangGraph adapter should emit comparable
  heartbeat events so progress UI keeps working.
- Timeout enforcement: the SDK adapter wraps the entire stream in
  `asyncio.timeout(self.sdk_timeout_seconds)` at `agent_invoker.py:2519`.
  Mirror this in the LangGraph adapter.

## References

- Review §3 — live execution-flow trace, especially §3.2-§3.5 (SDK boundary)
- Review §4.2 — five highest-friction touch-points (#1 invocation loops, #4 message-type dispatch, #5 SDK exception types)
- Review §10 — reconciliation with TASK-REV-ABST narrow mandate + gate freeze
- Pairs with: `guardkitfactory/.../TASK-HMIG-001B-implement-langgraph-harness-skeleton.md`,
  `TASK-HMIG-002R-configure-localshellbackend-and-permissions.md`

## Notes

The "byte-compatible coach_turn_N.json" contract (AC-004) is the single
hardest thing in this task — the SDK and LangGraph produce different shapes
of intermediate state, and both must collapse to the same on-disk artifact.
If a mismatch surfaces, surface it as a feedback issue, do not silently
diverge — schema drift here breaks every downstream consumer.

## Implementation Summary

Implemented over 2026-05-20 → 2026-05-21 via interactive `/task-work
TASK-HMIG-006 --implement-only` in seven phases (3a → 3b → 3c → 3d → 3e
→ 4+4.5 → 5+5.5).

### Approach

Established the `HarnessAdapter` substrate seam at
`guardkit/orchestrator/harness/`, then migrated the **first** of three
SDK call sites (`AgentInvoker._invoke_with_role` at
`agent_invoker.py:2359-2740`) through `select_harness()`. The two
remaining SDK call sites (direct-mode TaskWork at `:5269+`,
`coach_validator.py:1869+`) are deferred to TASK-HMIG-006.1/.3 per
plan §1; helper-function migration to true byte-compat parity is
deferred to TASK-HMIG-006.2 (D-7 cutover-day blocker) per Design
Decision D-1.

### Result

All 10 ACs verified. Final test pass: **1052 passed** across
orchestrator + doctor surfaces. AC-008 surface (133 tests) green with
no test-file modifications. Coverage: `sdk_harness.py` 87% line
(≥85% strict), `selector.py` 100%.

Code review: APPROVED_WITH_RECOMMENDATIONS, **87/100** (SOLID 88 / DRY
85 / YAGNI 90 / Security 84). Zero must-fix; three should-fix items
(S-1 lazy-import contract warning, S-2 translator-level
`resume_session_id` debug trace, S-3 `AsyncGenerator` return-type
precision) applied during Phase 5.5.

Plan audit: APPROVED. LOC overage (+2072 over plan estimate of +685)
is entirely in test surface required by plan §6 + strict-intensity
coverage requirements. No unjustified scope creep.

### Lessons

- **`type(block).__name__` cannot be spoofed by `__class__` property
  override** — the byte-compat parity test required real classes
  named `TextBlock` / `ToolUseBlock` in the fixture, not dataclasses
  with overridden `__class__`. One fix-loop attempt cost (Phase 4.5
  attempt 1).
- **`ResultMessageEvent.raw` asymmetry was a real gap in the ABC**
  (TASK-HMIG-001A). Phase 3a flagged it; Phase 3b confirmed needed
  for `_emit_llm_call_event` / `_extract_partial_from_messages` to
  consume raw SDK message objects on the SDK path. Additive
  defaulted-`None` field — backwards-compatible with the 5
  adapter-interface tests, but worth a one-line traceability comment
  on the ABC field (code review C-5, deferred).
- **`_translate_kwargs_for_langgraph` silently dropping
  `resume_session_id`** has two surfaces that need user signal:
  orchestrator-side (AC-007 warning at `agent_invoker.py:2512-2518`,
  shipped Phase 3c) AND translator-side (debug trace, shipped Phase
  5.5 S-2 for direct callers of `select_harness()` who bypass the
  orchestrator).
- **The `[tool.uv.sources]` sibling-repo editable pattern** (D-5,
  OQ-1 resolution) works seamlessly with the existing editable
  guardkitfactory install. `pip`-only users (no `uv`) will get a
  cryptic install failure — flagged for the portfolio-Python-pinning
  guide (code review C-3, deferred).

### Architectural decisions captured in this task

1. **D-1 — event.raw channel.** `ClaudeSDKHarness` populates
   `HarnessEvent.raw` with the original SDK message; downstream
   helpers (`_track_tool_use`, `_extract_partial_from_messages`,
   `_emit_llm_call_event`) continue to consume `event.raw` with
   their existing duck-typing. Trade-off documented in
   `harness/README.md` divergences table.
2. **D-3 — Thin substrate seam.** The harness boundary handles only
   substrate-specific work (lazy SDK import, message-stream
   translation, generator hygiene, D-4 exception normalisation,
   `_install_sdk_cleanup_handler` per D-6). All orchestrator-side
   concerns (heartbeat, cancel monitor, latency measurement,
   `sdk_debug`, `_emit_llm_call_event`, `_track_tool_use`,
   `check_assistant_message_error`, partial-extract on cancel,
   session_id rescan) stay in `agent_invoker.py`.
4. **D-4 — Exception normalisation owned by the harness.**
   `CLINotFoundError`, `ProcessError`, `CLIJSONDecodeError`, and
   harness-internal `ValueError` translate to `AgentInvocationError`
   inside `ClaudeSDKHarness.invoke()`. Orchestrator's catch cascade
   is now substrate-agnostic.
5. **D-5 — Sibling-repo editable resolution.** Use
   `[tool.uv.sources]` (fleet convention from jarvis /
   specialist-agent for `nats-core`), not PyPI / git+https.
6. **D-7 — Documented Wave-2 divergences.** Five named divergences
   between SDK and LangGraph paths are asserted as positive evidence
   in `test_byte_compat_parity.py`, with explicit follow-up task IDs
   per `.claude/rules/absence-of-failure-is-not-success.md`. The
   assertions invert when TASK-HMIG-006.2 lands.

### Related ADRs / reviews

- Parent review: TASK-REV-HMIG (review §10 frozen-path-touch
  justification)
- Plan: [`docs/state/TASK-HMIG-006/implementation_plan.md`](../../docs/state/TASK-HMIG-006/implementation_plan.md)
- Architectural review: [`docs/state/TASK-HMIG-006/architectural_review.md`](../../docs/state/TASK-HMIG-006/architectural_review.md)
- Code review: [`docs/state/TASK-HMIG-006/code_review.md`](../../docs/state/TASK-HMIG-006/code_review.md)
- Plan audit: [`docs/state/TASK-HMIG-006/plan_audit.md`](../../docs/state/TASK-HMIG-006/plan_audit.md)

### Follow-ups filed (OQ-4)

- [`TASK-HMIG-006.1`](../../backlog/autobuild-harness-migration/TASK-HMIG-006.1-migrate-direct-mode-sdk-dispatch.md) — direct-mode TaskWork dispatch
- [`TASK-HMIG-006.2`](../../backlog/autobuild-harness-migration/TASK-HMIG-006.2-migrate-helpers-to-harness-event-dispatch.md) — helper migration (D-7 cutover-day blocker)
- [`TASK-HMIG-006.3`](../../backlog/autobuild-harness-migration/TASK-HMIG-006.3-migrate-coach-independent-sdk-invocation.md) — Coach SDK migration
