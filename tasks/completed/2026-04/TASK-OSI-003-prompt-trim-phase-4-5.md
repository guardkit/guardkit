---
id: TASK-OSI-003
title: "Prompt trim: remove Phase 4/5 instructions from Player protocol"
status: completed
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T14:00:00Z
completed: 2026-04-25T14:00:00Z
previous_state: in_review
completed_location: tasks/completed/2026-04/
priority: high
task_type: refactor
parent_review: TASK-REV-119C1
feature_id: FEAT-AB59
wave: 1
implementation_mode: direct
complexity: 3
dependencies: []
tags: [autobuild, orchestrator, prompt-trim, OSI, F4A1-followup]
---

# Task: Prompt trim — remove Phase 4/5 instructions from Player protocol

## Description

Trim the AutoBuild execution protocol prompt files so the Player no longer
receives Phase 4 and Phase 5 instructions. The orchestrator now owns Phases
4 and 5 (TASK-OSI-006); the Player is told this in a single replacement
paragraph.

This removes the Player's structural incentive to claim Phase 4/5 phase
markers in `task_work_results.json` and reduces residual double-count risk
that TASK-OSI-002's source-tag dedup is the backstop for.

## Acceptance Criteria

- [x] `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` no
      longer instructs the Player to invoke `test-orchestrator` or
      `code-reviewer` via the `Task` tool for Phases 4 and 5.
- [x] `guardkit/orchestrator/prompts/autobuild_execution_protocol_medium.md`
      receives the same trim if it exists.
- [x] `guardkit/orchestrator/prompts/autobuild_execution_protocol_slim.md`
      receives the same trim if it exists.
- [x] A single replacement paragraph informs the Player: "Phases 4
      (test execution) and 5 (code review) are executed by the
      AutoBuildOrchestrator after your Phase 3 completes. You do not
      need to invoke `test-orchestrator` or `code-reviewer` directly.
      Focus your turn on Phases 1, 2, 3, and (optionally) Phase 4.5
      (test-fix loop) for your own feedback."
- [x] Phase 3 specialist guidance (e.g., "consider using
      `python-api-specialist`") remains as a soft recommendation —
      this is out of scope for the trim.
- [x] Phase 4.5 fix-loop guidance is preserved: the Player still runs
      tests inline for its own feedback during implementation; the
      orchestrator runs `test-orchestrator` afterwards as the gate
      input.
- [x] All modified files pass project-configured lint/format checks
      with zero errors.

## Implementation Notes

- This is a refactor task — no new logic, only prompt-content changes.
  Refuted prompt-class fix attempts (TASK-FIX-7A08, commits `7f8f14ba`,
  `86688fc6`, `a8789317`) targeted Phase 4/5 enforcement; this task
  targets Phase 4/5 *removal*. The prompt-class fix-class is being
  retired, not retried.
- Read all three protocol files first to identify Phase 4/Phase 5
  sections precisely. Do NOT delete Phase 4.5 (the fix-loop) — it is
  semantically distinct.
- Verify the trim does not break existing tests in
  `tests/orchestrator/` that snapshot protocol content (if any).

## Notes

- Wave 1, parallel-safe with TASK-OSI-001 and TASK-OSI-002.
- Mitigation owner for the "Player phase-marker double-count" risk.
- Refuted-fix-class boundary: this is a refactor, not a re-instruction.
