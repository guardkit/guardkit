---
id: TASK-POF-001
title: Add --autobuild-mode composite flag to task-work
status: backlog
task_type: implementation
created: 2026-02-15T14:00:00Z
updated: 2026-02-15T14:00:00Z
priority: high
complexity: 2
tags: [autobuild, preamble, performance, quick-win]
parent_review: TASK-REV-A781
feature_id: preamble-overhead-fix
implementation_mode: direct
wave: 1
parallel_group: wave-1
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add --autobuild-mode Composite Flag

## Description

Add a `--autobuild-mode` flag to the task-work command that bundles optimizations for autonomous execution:
- `--no-questions` (skip Phase 1.6 clarification - no human present)
- `--skip-arch-review` (skip Phase 2.5B for complexity ≤5)
- `--auto-approve-checkpoint` (skip Phase 2.8 blocking wait)
- `--docs=minimal` (minimize documentation overhead)

## Acceptance Criteria

- [ ] `--autobuild-mode` flag accepted by task-work command parsing (Step 0)
- [ ] Flag expands to the four sub-flags listed above
- [ ] Pre-loop `_build_design_prompt()` in `task_work_interface.py` uses `--autobuild-mode` instead of individual flags
- [ ] Pre-loop `_build_design_prompt()` already passes `--auto-approve-checkpoint` - verify `--no-questions` and `--docs=minimal` are also consistently applied
- [ ] Existing flag behavior unchanged when `--autobuild-mode` not specified

## Files to Modify

1. `installer/core/commands/task-work.md` - Add flag documentation and Step 0 parsing
2. `.claude/commands/task-work.md` - Add flag to project-level command spec
3. `guardkit/orchestrator/quality_gates/task_work_interface.py` - Use `--autobuild-mode` in `_build_design_prompt()`

## Implementation Notes

- This is a prompt-level change - the `--autobuild-mode` flag is parsed by Claude when it processes the task-work skill, not by Python code
- The pre-loop code in `task_work_interface.py` already passes some of these flags individually - consolidate into `--autobuild-mode`
- Keep the individual flags working for manual use
