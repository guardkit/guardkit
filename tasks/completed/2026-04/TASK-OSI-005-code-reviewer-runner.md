---
id: TASK-OSI-005
title: "code-reviewer orchestrator-side runner"
status: completed
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T00:00:00Z
completed: 2026-04-25T00:00:00Z
previous_state: in_review
state_transition_reason: "All ACs satisfied; 4 new + 9 regression unit tests pass; 75 broader orchestrator/autobuild tests pass; ruff clean"
priority: high
task_type: feature
parent_review: TASK-REV-119C1
feature_id: FEAT-AB59
wave: 3
implementation_mode: task-work
complexity: 5
dependencies: [TASK-OSI-004]
tags: [autobuild, orchestrator, specialist, code-reviewer, OSI, F4A1-followup]
consumer_context:
  - task: TASK-OSI-004
    consumes: SPECIALIST_RESULTS_JSON
    framework: "specialist_invocations.invoke_code_reviewer"
    driver: "structured prompt context + Read access to specialist_results.json"
    format_note: "phase_4 block must be passed via SpecialistInvocationResult and rendered into prompt as 'Phase 4 summary' section"
---

# Task: code-reviewer orchestrator-side runner

## Description

Implement `invoke_code_reviewer` in
`guardkit/orchestrator/specialist_invocations.py`. This is the
orchestrator-side runner for the Phase 5 specialist. It is invoked only
after `invoke_test_orchestrator` succeeds (Phase 4 status = passed); the
orchestrator's turn-loop wiring (TASK-OSI-006) is responsible for that
guard.

The runner takes `phase4_result` as a required argument and includes a
structured Phase 4 summary in the prompt context, so `code-reviewer` can
review the implementation with full knowledge of test outcomes.

## Acceptance Criteria

- [x] `specialist_invocations.py` exports
      `invoke_code_reviewer(worktree_path: Path, task_id: str,
      phase4_result: SpecialistInvocationResult, sdk_timeout: int,
      agent_invoker: AgentInvoker, cancellation_event: asyncio.Event)
      -> SpecialistInvocationResult` with real implementation (not a
      stub).
- [x] `phase4_result` is included in the prompt as a structured
      "Phase 4 summary" section: `tests_run`, `tests_failed`,
      `coverage_pct`, `quality_gates_passed`, `output_summary`.
- [x] Function calls `run_specialist` with `allowed_tools=["Read",
      "Search", "Grep"]` (subset of `code-reviewer.md` frontmatter
      line 13 — `Write` is dropped because the orchestrator-side
      review must NOT modify source files; review output goes to
      `specialist_results.json` directly via the runner, not via the
      agent's `Write` tool).
- [x] On success, appends a `phase_5` block to
      `.guardkit/autobuild/{task_id}/specialist_results.json`
      preserving the existing `phase_4` block: `status="passed"`,
      `duration_seconds`, `error=None`, and Phase 5-specific fields:
      `issues` (list), `quality_score` (float), `recommendations`
      (list), `output_summary`.
- [x] On failure, appends a `phase_5` block with `status="failed"` and
      `error` populated. Phase 4 block is preserved (no rollback). Does
      NOT raise into caller.
- [x] Function ASSERTS at entry that `phase4_result.status == "passed"`
      — if invoked with a failed Phase 4 result, the function raises
      `ValueError` (caller bug — TASK-OSI-006 turn-loop wiring is
      responsible for the guard). This is a defensive check, not the
      primary skip gate.
- [x] Unit tests (with stub SDK) cover: (a) success path appends
      `phase_5` block while preserving `phase_4`, (b) failure path
      records failure without raising, (c) `ValueError` raised when
      called with `phase4_result.status="failed"`, (d) prompt contains
      a "Phase 4 summary" string when introspected.
- [x] All modified files pass project-configured lint/format checks
      with zero errors.

## Implementation Notes

- The "Phase 4 summary" in the prompt is the single most important
  piece of context for `code-reviewer` — without it the review is
  blind to test outcomes. Verify via the unit test that introspects
  the rendered prompt.
- `Write` is intentionally dropped from the agent's allowed_tools: the
  orchestrator-side `code-reviewer` should NOT modify source files. Its
  output goes via the structured result block written by the runner
  itself.
- Reference: `installer/core/agents/code-reviewer.md` lines 40-90 for
  the review checklist.
- Output schema MUST match the §4.1 contract in the review report.

## Notes

- Wave 2 (depends on TASK-OSI-004).
- Consumer of SPECIALIST_RESULTS_JSON (Phase 4 block produced by
  TASK-OSI-004).
- Anti-stub rule applies: `invoke_code_reviewer` body must contain
  real prompt-build (with Phase 4 summary) + SDK call + result-write
  logic.
