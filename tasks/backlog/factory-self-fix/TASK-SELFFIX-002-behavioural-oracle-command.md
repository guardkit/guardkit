---
id: TASK-SELFFIX-002
title: behavioural_oracle.command for any stack
task_type: feature
parent_review: TASK-REV-SELFFIX
feature_id: FEAT-8AD1
wave: 1
implementation_mode: task-work
complexity: 5
dependencies: []
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-8AD1
  base_branch: main
  started_at: '2026-07-25T14:40:21.231201'
  last_updated: '2026-07-25T15:21:06.754668'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-07-25T14:40:21.231201'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---
# behavioural_oracle.command for any stack

Implement the guard docstring's promised, currently-unimplemented path: a
`behavioural_oracle.command` declared in the feature/task YAML runs as the runtime oracle
when no `tests/acceptance/*_roundtrip.py` artefact exists. This is the non-Python cure —
the command can be `go test ./...`, `npm run smoke`, anything. Producer seam:
`guardkit/orchestrator/quality_gates/coach_validator.py` (`_produce_behavioural_oracle`).
Reader (`_apply_behavioural_oracle_guard`) is UNCHANGED — the result shape must match
exactly. Binding spec: docs/factory-self-fix-scope-and-buildplan.md §2 Fix B + §3.

## Acceptance Criteria
- [ ] With no Python oracle artefact and a YAML-declared command that exits 0, the bundle's behavioural_oracle reports {status: "ran", passed: true, exit_code: 0, duration, timed_out: false, output_tail, provenance naming the command and its YAML origin}
- [ ] A command exiting non-zero reports {status: "ran", passed: false} with the failure output captured in output_tail
- [ ] A command exceeding GUARDKIT_ORACLE_TIMEOUT reports timed_out: true (which the existing guard treats as ran-and-failed) and the subprocess is reliably killed
- [ ] Precedence: when a *_roundtrip.py artefact exists, the file path runs and the command does NOT (existing file-glob tests stay green)
- [ ] A YAML-declared command is operator policy: the result is never downgraded to not_independent
- [ ] Hermetic tests cover all four shapes above using fake commands (true/false/sleep) — no docker, no network
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes
- Command executes via the system shell with cwd = the worktree root; environment inherits the gather's existing env posture.
- Read the declaration from the same feature/task YAML surface the orchestrator already loads — do not invent a new config file.
