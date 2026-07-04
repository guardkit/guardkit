---
id: TASK-BDDW-002
title: Multi-stack BDD reachability — route .NET to reqnroll, JS to cucumber-js
task_type: feature
parent_task: TASK-HMIG-BDDWIRE
feature_id: FEAT-E2CB
wave: 2
implementation_mode: task-work
complexity: 4
dependencies: [TASK-BDDW-001]
priority: medium
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
