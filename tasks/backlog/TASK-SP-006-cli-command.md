---
id: TASK-SP-006
title: "Create guardkit system-plan CLI command"
status: pending
task_type: feature
parent_review: TASK-REV-DBBC
feature_id: FEAT-SP-001
wave: 3
implementation_mode: task-work
complexity: 6
dependencies:
  - TASK-SP-003
  - TASK-SP-004
  - TASK-SP-005
tags: [system-plan, cli, click]
---

# Task: Create guardkit system-plan CLI Command

## Description

Create the Click CLI command `guardkit system-plan` that orchestrates the interactive architecture planning workflow. This wires together mode detection, question adapter, Graphiti operations, and architecture writer into a user-facing command.

## Acceptance Criteria

- [ ] `guardkit system-plan "description"` launches interactive planning
- [ ] `--mode=setup|refine|review` flag overrides auto-detection
- [ ] `--focus=domains|services|decisions|crosscutting|all` flag narrows scope
- [ ] `--no-questions` flag skips interactive clarification
- [ ] `--defaults` flag uses default answers
- [ ] `--context path/to/file.md` flag includes additional context files
- [ ] `--enable-context/--no-context` flag controls Graphiti integration
- [ ] Mode auto-detected: `setup` when no Graphiti architecture, `refine` otherwise
- [ ] Mode displayed transparently to user with explanation
- [ ] CLI registered in `guardkit/cli/main.py`
- [ ] Async operations wrapped in `asyncio.run()` at CLI boundary
- [ ] Graceful degradation when Graphiti unavailable (falls back to setup, warns user)
- [ ] Exit codes: 0=success, 1=error, 2=cancelled
- [ ] Unit tests for CLI argument parsing and flag combinations
- [ ] Unit tests for mode detection integration

## Files to Create/Modify

- `guardkit/cli/system_plan.py` — Click command implementation
- `guardkit/planning/system_plan.py` — Main orchestration logic (called by CLI)
- `guardkit/planning/mode_detector.py` — `detect_mode()` async function
- `guardkit/cli/main.py` — Register `system_plan` command
- `tests/unit/cli/test_system_plan_cli.py` — CLI tests
- `tests/unit/planning/test_mode_detector.py` — Mode detection tests

## Implementation Notes

- Follow `guardkit/cli/review.py` as the reference pattern for Click command structure
- Use `@handle_cli_errors` decorator from `guardkit/cli/decorators.py`
- Import and register: `from guardkit.cli.system_plan import system_plan` + `cli.add_command(system_plan)`
- `detect_mode()` is async — wrap with `asyncio.run()` at CLI layer
- The orchestration logic in `system_plan.py` coordinates:
  1. Mode detection (async → Graphiti query)
  2. Question flow (sync — adapter determines questions, CLI handles I/O)
  3. Graphiti writes (async — upsert entities)
  4. File writes (sync — architecture writer)
- Mode override: if `--mode` provided, skip `detect_mode()` call entirely

## Seam Test Points

- CLI flag parsing: all option combinations parsed correctly
- Async boundary: `asyncio.run()` wraps all Graphiti operations
- Command registration: `guardkit system-plan --help` works
- Graceful degradation: command works when Graphiti is None/disabled
