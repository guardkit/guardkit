---
id: TASK-BOOT-6D85
title: Wire _docker_available into task dict for conditional approval
status: backlog
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
priority: high
tags: [autobuild, coach-validator, docker, conditional-approval]
task_type: feature
complexity: 2
parent_review: TASK-REV-4D57
feature_id: FEAT-BOOT
wave: 2
implementation_mode: task-work
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Wire _docker_available into task dict for conditional approval

## Description

The task dict constructed in `_invoke_coach_safely()` does not include `_docker_available`. The CoachValidator's conditional approval logic reads `task.get("_docker_available", True)`, which defaults to `True`, making `not docker_available` always `False`. Conditional approval can never fire.

This task adds `_docker_available` to the task dict by calling `validator._is_docker_available()` before validation.

See: `.claude/reviews/TASK-REV-4D57-review-report.md` (Revision 3) — Finding 3 and R5.

## Acceptance Criteria

- [ ] `_invoke_coach_safely()` in `autobuild.py` includes `_docker_available: validator._is_docker_available()` in the task dict
- [ ] `_is_docker_available()` is called once per Coach invocation (not per-turn)
- [ ] When Docker is NOT available and all other conditions are met, conditional approval CAN fire
- [ ] Unit test: mock Docker unavailable → verify `_docker_available=False` in task dict
- [ ] Unit test: mock Docker available → verify `_docker_available=True` in task dict
- [ ] Existing tests continue to pass

## Key Files

- `guardkit/orchestrator/autobuild.py` — `_invoke_coach_safely()` task dict construction
- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_is_docker_available()` method, conditional approval logic
- `tests/unit/test_docker_available_wiring.py` — NEW: unit tests
