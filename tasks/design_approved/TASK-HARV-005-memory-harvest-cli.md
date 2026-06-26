---
autobuild_state:
  base_branch: main
  current_turn: 1
  last_updated: '2026-06-26T12:21:49.957819'
  max_turns: 5
  started_at: '2026-06-26T12:12:40.294131'
  turns:
  - coach_success: true
    decision: approve
    feedback: null
    player_success: true
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    timestamp: '2026-06-26T12:12:40.294131'
    turn: 1
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-HARV
complexity: 4
created: 2026-06-25 00:00:00+00:00
depends_on:
- TASK-HARV-003
- TASK-HARV-004
feature_id: FEAT-HARV
id: TASK-HARV-005
implementation_mode: task-work
parent_feature: memory-harvest-publisher
parent_review: TASK-REV-HARV
status: design_approved
task_type: feature
title: guardkit memory harvest CLI with dry-run
updated: 2026-06-25 00:00:00+00:00
wave: 3
---

# TASK-HARV-005: `guardkit memory harvest` CLI with `--dry-run`

## Objective

Add a new `guardkit memory` Click group with a `harvest` command that wires the walker
(TASK-HARV-003) to the publisher (TASK-HARV-004). `--dry-run` reports what would publish
(counts per type + oversized skips) **without connecting** to NATS.

## Context

guardkit's CLI is Click-based: each subcommand is a module in `guardkit/cli/` and is
registered in `guardkit/cli/main.py` via `cli.add_command(...)` (see the existing
`feature`, `graphiti`, `task` registrations). Mirror that pattern exactly.

## Acceptance Criteria

- [ ] `guardkit/cli/memory.py` defines a `memory` Click group and a `harvest` command,
      registered in `guardkit/cli/main.py` via `cli.add_command(memory)` alongside the
      existing `cli.add_command(...)` calls.
- [ ] `guardkit memory harvest` runs the walker then the publisher and prints a summary
      (published / skipped-oversized / empty-filtered, plus counts-per-type).
- [ ] `guardkit memory harvest --dry-run` runs **only** the walker, prints
      counts-per-type and the oversized-skip report, and **never** connects to NATS and
      **never** reads `GUARDKIT_NATS_PASSWORD` (no `NATSClient` is constructed).
- [ ] Options: `--dry-run`, `--docs-root <path>` (default: repo root `docs/`),
      `--env-file <path>` (optional source for `GUARDKIT_NATS_PASSWORD`).
- [ ] Exit code is `0` on success **including** when oversized docs were skipped (they
      are reported, not fatal); non-zero only on connection/auth failure or an
      unexpected error.
- [ ] Summary output uses the Rich style consistent with the existing
      `guardkit feature` command.
- [ ] CLI tests via `click.testing.CliRunner`: `--dry-run` emits counts and constructs
      **no** `NATSClient` (assert via patch/spy); the wired path invokes walker then
      publisher in order.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation Notes

- Keep the command thin: it orchestrates `harvest_walker` + `harvest_publisher` and
  formats output. No taxonomy, envelope, or NATS logic lives here.
- The `harvest` command runs an async publish path — bridge with `asyncio.run(...)`
  inside the Click callback (the publisher is async; the walker is sync).
- `--dry-run` must short-circuit **before** any password read so it works on a machine
  with no NATS creds at all (e.g. CI, a dev laptop).

## Coach Validation

```bash
pytest tests/ -v -k "memory_cli or harvest_cli"
guardkit memory harvest --dry-run   # smoke: prints counts, no connection
```