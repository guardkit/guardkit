---
id: TASK-FIX-7A3E
title: Delete dead upfront_complexity_cli, adapter, and its unit test
status: completed
created: 2026-04-11T17:55:00Z
updated: 2026-04-11T18:45:00Z
completed: 2026-04-11T18:45:00Z
previous_state: backlog
completed_location: tasks/completed/TASK-FIX-7A3E/
priority: medium
tags: [cleanup, dead-code, commands-lib]
task_type: implementation
parent_review: TASK-REV-C1B4
feature_id: FEAT-E1AF
wave: 1
conductor_workspace: commands-lib-cleanup-wave1-1
implementation_mode: task-work
complexity: 2
depends_on: []
---

# Task: Delete dead `upfront_complexity_cli.py`, `upfront_complexity_adapter.py`, and its unit test

## Background

Surfaced by [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md) Section 1. This pair of files
is residue from the abandoned TASK-005 design (see `docs/adr/ADR-005-upfront-complexity-refactored-architecture.md`)
that was never wired into any live command path. Same failure mode as [TASK-FIX-E841](../../in_review/TASK-FIX-E841-repair-or-deprecate-template-validate-cli.md)'s
`template_validate_cli.py`: the CLI was designed as a handler backing `/impact-analysis` (or an earlier precursor),
but `/impact-analysis` actually routes through `guardkit.planning.impact_analysis.run_impact_analysis` — a completely
different module in the `guardkit` Python package.

The review verified with direct import-check and `--help` run that the CLI is **structurally healthy** (imports
cleanly, runs end-to-end). It is dead only because nothing calls it. The adapter is a **transitive orphan** — its
only production importer is the dead CLI itself. The single unit test (`tests/unit/test_upfront_adapter.py`)
exercises the adapter in isolation via `importlib.util` and does not prove any live integration.

## Description

Delete the three files below. Verify no live code path is broken by the deletion.

### Files to delete

1. `installer/core/commands/lib/upfront_complexity_cli.py`
2. `installer/core/commands/lib/upfront_complexity_adapter.py`
3. `tests/unit/test_upfront_adapter.py`

### Verification steps

1. Before deleting, grep the entire repo (excluding historical artifacts: `.claude/reviews/`, `docs/reviews/`,
   `docs/archive/`, `docs/implementation-plans/`, `docs/adr/`, `tasks/completed/`, `tasks/archived/`,
   `.claude/state/backup/`) for each of:
   - `upfront_complexity_cli`
   - `upfront_complexity_adapter`
   - `UpfrontComplexityAdapter`
   Confirm no live code importers exist. If any new live importer has appeared since the review (2026-04-11),
   stop and escalate.
2. Delete the three files.
3. Run the full test suite: `pytest tests/ -v`. It must still pass.
4. Run the slash-command integration gate: confirm `/impact-analysis` still works (the review confirmed it uses
   `guardkit.planning.impact_analysis`, not this file).

### What NOT to touch

- Do **not** touch `installer/core/commands/lib/complexity_calculator.py` — that module is a live dependency of
  multiple orchestrators (per the review's grep: `task_breakdown.py`, `review_modes.py`, and the `__init__.py`
  export all reference it). Only the **adapter** on top of the calculator is dead, not the calculator itself.
- Do **not** manually remove the stale `~/.agentecflow/bin/upfront-complexity-cli` symlink. That cleanup is
  TASK-FIX-CF8D's responsibility (it adds a prune pass to `install.sh` that will remove the dangling symlink
  automatically on next install).

## Acceptance Criteria

- [ ] Pre-deletion grep confirms no live code importers for any of the three files (filtered against historical
      artifacts per review notes).
- [ ] Three files deleted: `upfront_complexity_cli.py`, `upfront_complexity_adapter.py`, `tests/unit/test_upfront_adapter.py`.
- [ ] Full pytest suite (`pytest tests/ -v`) passes with no new failures.
- [ ] `python3 -c "from guardkit.planning.impact_analysis import run_impact_analysis"` still imports cleanly
      (sanity check that `/impact-analysis` isn't affected).
- [ ] `complexity_calculator.py` is untouched and still imports cleanly.

## References

- Parent review: [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md) Section 1
- Review report: [.claude/reviews/TASK-REV-C1B4-review-report.md](../../../.claude/reviews/TASK-REV-C1B4-review-report.md)
- Sibling task (same failure mode): [TASK-FIX-E841](../../in_review/TASK-FIX-E841-repair-or-deprecate-template-validate-cli.md)
- Historical design context: `docs/adr/ADR-005-upfront-complexity-refactored-architecture.md`
