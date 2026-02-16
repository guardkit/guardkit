---
id: TASK-SFT-006
title: "Seam tests S2 \u2014 CLI-to-Python entry point wiring"
task_type: testing
parent_review: TASK-REV-AC1A
feature_id: FEAT-AC1A
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-SFT-001
priority: medium
status: in_review
autobuild_state:
  current_turn: 2
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AC1A
  base_branch: main
  started_at: '2026-02-15T21:22:24.046233'
  last_updated: '2026-02-15T21:30:50.736532'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  \u2022 Test: `guardkit task create`\
      \ with title creates a task file in the correct directory"
    timestamp: '2026-02-15T21:22:24.046233'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-02-15T21:27:11.708199'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Seam Tests S2: CLI (Click) → Python Entry Points

## Objective

Write seam tests verifying that Click CLI commands actually invoke their Python entry points with correct arguments — catching cases where args are lost, async wrapping fails, or commands silently do nothing.

## Seam Definition

**Layer A**: Click CLI commands (`guardkit system-plan`, `guardkit system-overview`, etc.)
**Layer B**: Python entry points (`run_system_plan()`, `get_system_overview()`, etc.)

## Acceptance Criteria

- [ ] `tests/seam/test_cli_to_python.py` created
- [ ] Test: `guardkit system-plan` with `--context` flag passes context file to `run_system_plan()`
- [ ] Test: `guardkit system-overview` invokes `get_system_overview()` and returns output
- [ ] Test: `guardkit graphiti search` passes query string to search function
- [ ] Test: `guardkit task create` with title creates a task file in the correct directory
- [ ] Tests use `click.testing.CliRunner` to invoke commands directly (no subprocess needed)
- [ ] Tests verify the command produced meaningful output (not empty, not just a help message)
- [ ] All tests pass with `pytest tests/seam/test_cli_to_python.py -v`

## Implementation Notes

- Use Click's `CliRunner.invoke()` for direct testing
- Mock Graphiti at the client level, not at the function level
- Check `guardkit/cli/` for command registration and argument parsing
