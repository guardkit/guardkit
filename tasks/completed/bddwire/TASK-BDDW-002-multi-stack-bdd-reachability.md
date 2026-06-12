---
id: TASK-BDDW-002
title: "Multi-stack BDD reachability \u2014 route .NET to reqnroll, JS to cucumber-js"
task_type: feature
parent_task: TASK-HMIG-BDDWIRE
feature_id: FEAT-E2CB
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-BDDW-001
priority: medium
status: completed
updated: '2026-06-12T12:42:10'
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-E2CB
  base_branch: main
  started_at: '2026-06-12T12:58:27.691932'
  last_updated: '2026-06-12T13:34:27.261518'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- The Player claimed to have implemented ''reqnroll_plugin.py'' and
      ''cucumber_js_plugin.py'', but these files do not exist on disk. This is a critical
      honesty violation.: Ensure all implementation files are actually created and
      staged in the workspace before submitting the report.

      - The orchestrator aborted evidence collection (partial_honesty_abort) before
      running tests. The Player''s claim of 11 passing tests cannot be verified.:
      Fix the implementation and ensure the test suite is actually executed and recorded
      by the orchestrator.'
    timestamp: '2026-06-12T12:58:27.691932'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-06-12T13:13:02.968478'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Multi-stack BDD reachability

## Description

Wave 1 (TASK-BDDW-001) wired `guardkitfactory.bdd.discover(stack_profile)` into the
Coach evidence path for Python (pytest-bdd). This task makes the **.NET (reqnroll)**
and **JS (cucumber-js)** plugins — which exist and are tested in guardkitfactory but
are currently **dead code, unreachable from any run** — actually reachable, by
ensuring stack detection routes a .NET project to `ReqnrollPlugin` and a JS project
to `CucumberJSPlugin` through the same discovery seam.

## Acceptance Criteria

- [ ] **AC-2 (multi-stack reachability)**: a .NET project routes to `ReqnrollPlugin`
  and a JS project to `CucumberJSPlugin` through `guardkitfactory.bdd.discover` in
  the Coach evidence path — the currently-dead paths become reachable. Tests assert
  plugin selection per stack profile (Python → pytest-bdd, .NET → reqnroll,
  JS → cucumber-js).
- [ ] **AC-2b (unsupported stack → absent-signal)**: a stack with no registered BDD
  plugin (`discover` returns `None`) maps to ABSENT SIGNAL in `bundle.bdd`, never a
  silent pass — consistent with AC-3 of Wave 1.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation Notes

- **Seam:** the stack-detection → `discover(stack_profile)` dispatch landed in
  Wave 1. This task verifies/extends the `StackProfile` construction so the detected
  stack (`detect_stack_template`, `coach_validator.py:64`, returns a template string)
  maps to the correct `StackProfile.language` the factory `discover` keys on.
- **Plugins** already exist and are contract-gated in guardkitfactory
  (`reqnroll_plugin.py`, `cucumber_js_plugin.py`) — this task writes NO new plugin,
  only the routing + per-stack selection tests.
- Depends on Wave 1's discovery seam being in place.

## Coach Validation

- `pytest tests/ -k "bdd and (reqnroll or cucumber or stack_profile)" -v`
- Tests assert correct plugin class selected per stack profile.
- Lint/format checks pass with zero errors.
