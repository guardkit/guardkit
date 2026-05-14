---
id: TASK-DEMO-D5DD
title: Add --short flag to guardkit version subcommand
status: backlog
task_type: feature
created: 2026-05-14T13:15:00Z
updated: 2026-05-14T14:20:00Z
priority: medium
tags: [demo, dddsw, cli]
implementation_mode: task-work
complexity: 2
depends_on: []
autobuild:
  enabled: true
  max_turns: 3
  base_branch: main
  mode: standard
---

# TASK-DEMO-D5DD — Add --short flag to guardkit version subcommand

## Description

Add a `--short` flag to the existing `guardkit version` Click subcommand at
[`guardkit/cli/main.py:140-145`](../../../guardkit/cli/main.py#L140-L145).
When `--short` is passed, the command prints only the semver string
(`0.1.0` followed by a newline) to stdout, with no banner or other
content. Default behaviour (no flag) is unchanged.

The version constant is at
[`guardkit/__init__.py:3`](../../../guardkit/__init__.py#L3)
(`__version__ = "0.1.0"`).

## Acceptance Criteria

- [ ] Running `guardkit version --short` prints exactly `0.1.0\n` to stdout and exits with code 0. No other output (no banner, no "GuardKit CLI version" prefix).
- [ ] Running `guardkit version` (no flag) continues to print the existing human-readable output (`GuardKit CLI version 0.1.0` via `console.print`) and exits 0. The default behaviour string is unchanged byte-for-byte.
- [ ] `guardkit version --help` includes a help line documenting the `--short` flag.
- [ ] A new unit test file (e.g. `tests/cli/test_version_command.py`) uses Click's `CliRunner` to exercise both modes, asserting exact stdout content and exit code 0 in each.
- [ ] All existing tests continue to pass (`pytest tests/ -x`).

## Implementation Notes

- Add `--short` as a `click.option(..., is_flag=True, default=False)` decorator on the existing `version()` function.
- For the short path use `click.echo(__version__)` — `click.echo` adds the trailing newline automatically. Do **not** use `console.print` for the short path (Rich may inject ANSI styling).
- The unit test should use `from click.testing import CliRunner` and import the `cli` group from `guardkit.cli.main`.
- Keep the diff minimal — under 20 lines of production code, under 30 lines of test.

## Out of Scope

- Wiring `--short` through any bash wrapper or installer shim outside `guardkit/cli/`.
- Renaming or refactoring the existing `version` command.
- Updating CHANGELOG, README, or any other documentation file.
- Adding `--short` to any other CLI subcommand.

## References

- [`guardkit/__init__.py:3`](../../../guardkit/__init__.py#L3) — version constant
- [`guardkit/cli/main.py:140-145`](../../../guardkit/cli/main.py#L140-L145) — existing version command
- DDD South West 2026 demo — smoke test for autobuild on local Qwen3.6 backend via llama-swap
