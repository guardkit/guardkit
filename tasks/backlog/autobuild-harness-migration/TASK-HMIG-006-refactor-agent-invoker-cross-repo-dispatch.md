---
id: TASK-HMIG-006
title: Refactor agent_invoker._invoke_with_role to dispatch through HarnessAdapter (cross-repo import from guardkitfactory)
status: backlog
task_type: implementation
created: 2026-05-19T20:30:00Z
updated: 2026-05-19T20:30:00Z
priority: critical
complexity: 7
deadline: 2026-06-15
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
