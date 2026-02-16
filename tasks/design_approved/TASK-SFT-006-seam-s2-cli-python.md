---
complexity: 4
dependencies:
- TASK-SFT-001
feature_id: FEAT-AC1A
id: TASK-SFT-006
implementation_mode: task-work
parent_review: TASK-REV-AC1A
priority: medium
status: design_approved
task_type: testing
title: Seam tests S2 — CLI-to-Python entry point wiring
wave: 2
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