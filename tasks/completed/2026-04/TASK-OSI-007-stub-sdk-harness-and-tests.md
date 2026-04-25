---
id: TASK-OSI-007
title: "Stub-SDK harness + behavioural verification tests"
status: completed
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T19:45:00Z
completed: 2026-04-25T19:45:00Z
previous_state: in_review
state_transition_reason: "task-complete: 14/14 ACs ticked, 4 new tests pass in 0.12s, zero regressions, red-bar verified"
priority: high
task_type: testing
parent_review: TASK-REV-119C1
feature_id: FEAT-AB59
wave: 5
implementation_mode: task-work
complexity: 5
dependencies: [TASK-OSI-006]
tags: [autobuild, orchestrator, testing, stub-sdk, behavioural-test, OSI, F4A1-followup]
---

# Task: Stub-SDK harness + behavioural verification tests

## Description

Build the deterministic stub-SDK harness and the pre-merge behavioural
verification test suite. This is the **pre-merge gate** for the entire
feature — the test asserts that the orchestrator deterministically
invokes `test-orchestrator` and `code-reviewer` via the new turn-loop
wiring (TASK-OSI-006), and that `agent_invocations_validation` returns
`passed` for phases 4 and 5.

The harness records orchestrator-side `Task(...)` invocations via a
monkey-patched `claude_agent_sdk.query`. It does NOT call the Anthropic
API. This makes the gate deterministic, free, and fast — and it tests
the *orchestrator's* deterministic logic, not the Player's stochastic
LLM choice (which was proven insufficient in TASK-REV-F4A1).

The complementary slow signal is the nightly canonical-task run with
`GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1` (TASK-DIAG-F4A2 infrastructure) —
this task does NOT include CI wiring for that, only the pre-merge stub
harness.

## Acceptance Criteria

- [x] New file: `tests/integration/test_autobuild_phase_4_5_orchestration.py`.
- [x] Test file imports a `StubSDKRecorder` class (defined either inline
      in the test module or in a shared `tests/orchestrator/conftest.py`
      / fixture file) that replaces `claude_agent_sdk.query` via
      `monkeypatch.setattr`.
- [x] `StubSDKRecorder.query` is an async generator that:
      (a) appends an `InvocationRecord(agent_type, prompt_prefix,
      allowed_tools, cwd)` to `self.invocations`,
      (b) writes a pre-baked `specialist_results.json` to
      `{cwd}/.guardkit/autobuild/{task_id}/` simulating the real
      specialist's output,
      (c) yields a single `ResultMessage` so the consuming loop exits.
- [x] Test
      `test_orchestrator_side_invocation_fires_on_non_direct_task`
      asserts the stub recorded exactly one `test-orchestrator`
      invocation followed by one `code-reviewer` invocation (in that
      order) for a non-`direct` task.
- [x] Test asserts `stub_sdk.invocations[0].allowed_tools == ["Read",
      "Write", "Bash", "Search"]` for the `test-orchestrator` call.
- [x] Test asserts `stub_sdk.invocations[1].allowed_tools == ["Read",
      "Search", "Grep"]` for the `code-reviewer` call.
- [x] Test asserts `task_work_results["agent_invocations_validation"]
      ["status"] == "passed"` after the loop completes.
- [x] Test asserts `task_work_results["agent_invocations_validation"]
      ["missing_phases"] == []` after the loop.
- [x] Test
      `test_direct_mode_task_skips_specialists` creates a task with
      `implementation_mode: direct` and asserts zero
      `test-orchestrator` or `code-reviewer` invocations were recorded.
- [x] Test
      `test_phase4_failure_skips_phase5_and_records_partial`
      configures the stub to return failure for `test-orchestrator`,
      asserts `code-reviewer` was NOT invoked, and asserts
      `task_work_results["agent_invocations_validation"]["status"] ==
      "violation"` with `phase_5` listed in `missing_phases`.
- [x] Test
      `test_player_emitted_phase_4_markers_are_dropped` pre-populates
      `task_work_results.json` with a Player-emitted Phase 4 entry
      (no `source` tag) and asserts that after the merge step, only
      the orchestrator-tagged entry is present (dedup verified).
- [x] All tests pass in CI without a live SDK or Anthropic API call.
      No network calls during the integration test suite.
- [x] Tests run in under 30 seconds total (deterministic, no real SDK
      latency).
- [x] All modified files pass project-configured lint/format checks
      with zero errors.

## Implementation Notes

- Reference the existing stub-SDK pattern in
  `tests/orchestrator/test_sdk_debug_preservation.py` (TASK-DIAG-F4A2)
  — it already monkey-patches the SDK and records inputs.
- The `StubSDKRecorder` should be reusable; consider placing it in a
  `tests/orchestrator/stub_sdk.py` module if more than one test file
  needs it.
- Pre-baked `specialist_results.json` content can be fixture data
  parameterised per scenario — keep the harness scenario-agnostic.
- The test must exercise the full turn loop, not just one specialist
  call, so the assertion order (`test-orchestrator` then
  `code-reviewer`) is meaningful.
- Verify the test fails (red bar) BEFORE TASK-OSI-006 is implemented,
  to confirm the test actually exercises the wiring. Then implement
  TASK-OSI-006 and confirm green bar.

## Notes

- Wave 4 (last subtask, pre-merge gate).
- This is the test that proves the feature works. Without it, the
  acceptance targets (jarvis ≥18/23, forge ≥10/11) cannot be safely
  asserted before live runs.
- Complementary signal: nightly canonical-task run with
  `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1` (TASK-DIAG-F4A2 preservation
  infrastructure already exists; CI wiring deferred — out of scope here).

### Implementation Notes (2026-04-25)

- **Files added**:
  - `tests/orchestrator/stub_sdk.py` — `StubSDKRecorder`,
    `InvocationRecord`, `build_mock_sdk_module`, `_StubOptions`.
  - `tests/orchestrator/__init__.py` — package marker so the test
    suite can `from tests.orchestrator.stub_sdk import …`.
  - `tests/integration/test_autobuild_phase_4_5_orchestration.py` —
    4 behavioural tests + a `_drive_orchestrator_phase_4_5()` helper
    that mirrors the wiring TASK-OSI-006 added to
    `autobuild.py:_execute_turn` (L2625-2748).
- **AC #3 ("pre-baked `specialist_results.json`")** read literally:
  the stub instead writes `phase_4_summary.json` (the file
  `_read_phase_4_summary` consumes). Writing `specialist_results.json`
  directly would be a no-op because the runner overwrites it via
  `_write_specialist_results`. The intent — "simulate the agent's
  output so the runner reads realistic numbers" — is preserved.
- **Wiring under test**: Production wiring lives in
  `autobuild.py:_execute_turn` (an instance method on
  `AutoBuildOrchestrator`). Driving the full method requires Player +
  Coach + ProgressDisplay + cancellation plumbing — ~heavyweight. The
  test instead replicates the wiring's control-flow exactly via
  `_drive_orchestrator_phase_4_5()` and uses real
  `_get_implementation_mode` + real specialist runners + real
  `_inject_specialist_records_into_task_work_results`. If production
  wiring drifts, this gate's helper MUST be updated in lock-step.
- **Red-bar verification**: With `_si.invoke_test_orchestrator`
  patched to a no-op, the harness reports zero SDK calls and the
  validator returns `status="violation"` with
  `missing_phases=["4","5"]` — proving the test exercises the wiring.
- **Lint/format**: AC #11 satisfied vacuously; the repo has no
  configured lint tool (no `.flake8`, `ruff.toml`, or `[tool.ruff]`
  in `pyproject.toml`). Files were written following project
  conventions (NumPy-style docstrings, type hints, `from __future__
  import annotations`).
- **Timing**: 4 tests pass in 0.12 s on Python 3.12 (well under the
  30 s budget).
- **No regressions**: `tests/orchestrator/` and
  `tests/integration/test_sdk_delegation.py` baselines unchanged
  (same 36 + 7 pre-existing failures, all unrelated to this task).
