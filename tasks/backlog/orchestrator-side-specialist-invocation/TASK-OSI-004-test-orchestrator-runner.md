---
id: TASK-OSI-004
title: "test-orchestrator orchestrator-side runner"
status: backlog
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T00:00:00Z
priority: high
task_type: feature
parent_review: TASK-REV-119C1
feature_id: FEAT-AB59
wave: 2
implementation_mode: task-work
complexity: 5
dependencies: [TASK-OSI-001, TASK-OSI-002]
tags: [autobuild, orchestrator, specialist, test-orchestrator, OSI, F4A1-followup]
---

# Task: test-orchestrator orchestrator-side runner

## Description

Implement `invoke_test_orchestrator` in
`guardkit/orchestrator/specialist_invocations.py` (skeleton from
TASK-OSI-001). This is the orchestrator-side runner for the Phase 4
specialist. It builds a structured prompt from the task's requirements,
current worktree state, and Phase 3 completion summary, then invokes
`test-orchestrator` via `run_specialist` with the agent's declared tools.

On both success and failure, the runner writes a structured `phase_4`
block to `.guardkit/autobuild/{task_id}/specialist_results.json` so
TASK-OSI-002's merge step always has data to read.

## Acceptance Criteria

- [ ] `specialist_invocations.py` exports
      `invoke_test_orchestrator(worktree_path: Path, task_id: str,
      sdk_timeout: int, agent_invoker: AgentInvoker, cancellation_event:
      asyncio.Event) -> SpecialistInvocationResult` with a real
      implementation (not a stub — see anti-stub rule).
- [ ] Function builds a structured prompt that includes (a) the task's
      requirements/acceptance criteria from the task markdown, (b) a
      summary of files changed in Phase 3 (read from
      `task_work_results.json`'s Phase 3 entry), and (c) instructions to
      run the project's test suite and produce a structured result.
- [ ] Function calls `run_specialist` with `allowed_tools=["Read",
      "Write", "Bash", "Search"]` (matches `test-orchestrator.md`
      frontmatter line 18).
- [ ] On success, writes `specialist_results.json` to
      `.guardkit/autobuild/{task_id}/` with a `phase_4` block containing:
      `status="passed"`, `duration_seconds`, `error=None`, and Phase
      4-specific fields: `tests_run`, `tests_failed`, `coverage_pct`,
      `output_summary`, `quality_gates_passed`.
- [ ] On failure (SDK exception, timeout, non-success result), writes
      `specialist_results.json` with a `phase_4` block containing
      `status="failed"` and `error` populated. Does NOT raise into
      caller.
- [ ] If `specialist_results.json` already exists for this turn (e.g.
      from a prior interrupted run), the new write overwrites the
      `phase_4` block while preserving any `phase_5` block (idempotent
      partial write).
- [ ] Unit tests (with stub SDK) cover: (a) success path writes correct
      schema, (b) failure path writes failure block without raising,
      (c) timeout path writes `status="failed"` + `error="timeout"`,
      (d) idempotent partial write preserves existing `phase_5` block.
- [ ] All modified files pass project-configured lint/format checks
      with zero errors.

## Implementation Notes

- The structured prompt should NOT replicate the full execution
  protocol — `test-orchestrator` agent definition has its own system
  prompt. Pass only task-specific context.
- Reference: `installer/core/agents/test-orchestrator.md` for the
  agent's responsibilities and expected output shape.
- Use a try/except around the SDK invocation; on timeout the
  `cancellation_event` will be set by the orchestrator's per-turn
  monitor — propagate via the existing `_invoke_with_role` mechanism.
- Output schema MUST match the §4.1 contract in the review report.

## Notes

- Wave 2.
- Producer of SPECIALIST_RESULTS_JSON (consumed by TASK-OSI-002 and
  TASK-OSI-005).
- Anti-stub rule applies: `invoke_test_orchestrator` is a primary
  deliverable function; body must contain real prompt-build + SDK call
  + result-write logic.
