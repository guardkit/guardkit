---
id: TASK-BOOT-43DE
title: Coach test fallback to subprocess with sys.executable
status: backlog
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
priority: high
tags: [autobuild, coach-validator, defence-in-depth]
task_type: feature
complexity: 3
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

# Task: Coach test fallback to subprocess with sys.executable

## Description

Change `run_independent_tests()` in CoachValidator to use `subprocess.run()` with `sys.executable` as the Python interpreter for independent test verification, rather than spawning an SDK CLI session.

This is **defence-in-depth**, not the primary fix. The bootstrap phase (TASK-BOOT-E3C0) is the root cause fix. This task eliminates any residual PATH resolution ambiguity where the SDK CLI's Bash tool might resolve `python3` to a different interpreter than the orchestrator's Python.

See: `.claude/reviews/TASK-REV-4D57-review-report.md` (Revision 3) — R3.

## Why This Matters Even With Bootstrap

The SDK passes `os.environ` correctly. But the Bash tool inside the CLI spawns a shell that resolves `python3` via PATH. If PATH ordering differs between the orchestrator's Python and what the shell resolves (e.g., macOS `/usr/bin/python3` vs framework Python), tests could hit the wrong interpreter. Using `sys.executable` explicitly pins the Python binary.

## Acceptance Criteria

- [ ] `run_independent_tests()` in `coach_validator.py` uses `subprocess.run()` with `sys.executable -m pytest` for Python test execution
- [ ] Non-Python test commands (e.g., `npm test`, `dotnet test`) continue to use the existing execution path
- [ ] Test command construction uses `sys.executable` to eliminate PATH ambiguity
- [ ] Subprocess inherits `os.environ` from the orchestrator process
- [ ] Unit tests for subprocess test execution path
- [ ] Existing Coach validation tests continue to pass

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `run_independent_tests()` and `_run_tests_via_sdk()` methods
- `tests/unit/test_coach_subprocess_tests.py` — NEW: unit tests
