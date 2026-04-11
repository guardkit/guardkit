---
id: TASK-REF-9C5A
title: Relocate demo scripts and verify-shell out of commands/lib/
status: completed
created: 2026-04-11T17:55:00Z
updated: 2026-04-11T18:35:00Z
completed: 2026-04-11T18:35:00Z
previous_state: in_review
priority: low
tags: [cleanup, refactor, commands-lib, directory-hygiene]
task_type: implementation
parent_review: TASK-REV-C1B4
feature_id: FEAT-E1AF
wave: 1
conductor_workspace: commands-lib-cleanup-wave1-3
implementation_mode: direct
complexity: 2
depends_on: []
---

# Task: Relocate demo scripts and `verify_*.sh` out of `commands/lib/`

## Background

Surfaced by [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md) Section 2. The directory
`installer/core/commands/lib/` is meant to hold "command-support libraries" imported by slash commands and
orchestrators. It is NOT meant to hold manual developer demos. Five files violate this intent:

- `demo_agent_tracker_integration.py`
- `demo_phase_gate_integration.py`
- `demo_plan_markdown.py`
- `demo_template_qa.py`
- `verify_micro_implementation.sh`

Because of `install.sh`'s blind-walk behavior (TASK-REV-C1B4 Section 2 root cause), all four Python demos are
currently promoted to global shell commands in `~/.agentecflow/bin/` (`demo-agent-tracker-integration`,
`demo-phase-gate-integration`, `demo-plan-markdown`, `demo-template-qa`). Users do not know these are not
intended to be called.

## Description

Move the five files to a location that makes their purpose explicit and does not cause `install.sh` to symlink
them into `bin/`.

### Target location

Use **`examples/`** — it already exists at the repo root per the review's grep (`examples/plan_review_usage.py`),
so no new directory needed. Alternatively `scripts/dev/` if the user prefers a dev-scripts convention. Default:
`examples/`.

### Files to move

| From | To |
|---|---|
| `installer/core/commands/lib/demo_agent_tracker_integration.py` | `examples/demo_agent_tracker_integration.py` |
| `installer/core/commands/lib/demo_phase_gate_integration.py` | `examples/demo_phase_gate_integration.py` |
| `installer/core/commands/lib/demo_plan_markdown.py` | `examples/demo_plan_markdown.py` |
| `installer/core/commands/lib/demo_template_qa.py` | `examples/demo_template_qa.py` |
| `installer/core/commands/lib/verify_micro_implementation.sh` | `examples/verify_micro_implementation.sh` |

### Verification

- Each demo still runs standalone after relocation. If a demo has relative imports like
  `from .something import ...`, convert to absolute imports (`from installer.core.commands.lib.something import ...`)
  or adjust `sys.path` as needed. The review did not deep-read these files, so verify one at a time.
- Grep for any CI/hook/script that invokes the old path. If found, update.
- Stale `~/.agentecflow/bin/demo-*` symlinks will be auto-pruned by TASK-FIX-CF8D — do not manually touch them
  in this task.

### Not in scope

- Do not rewrite or improve the demos. Move them as-is.
- Do not touch `install.sh` — TASK-FIX-CF8D and TASK-ISH-D09E handle the installer changes.

## Acceptance Criteria

- [x] 5 files relocated from `installer/core/commands/lib/` to `examples/`.
- [x] Each relocated demo is still runnable (`python3 examples/demo_X.py` succeeds or fails with a user-understandable
      message, not with `ImportError`).
- [x] No CI, hook, or slash command references the old path under `commands/lib/` (grep confirms).
- [x] `installer/core/commands/lib/` no longer contains any `demo_*.py` or `verify_*.sh` files.

## Implementation Notes

- Used `git mv` to preserve history for all 5 files.
- Patched imports in 4 demo `.py` files: each now adds
  `Path(__file__).parent.parent / "installer" / "core" / "commands" / "lib"` to `sys.path` before importing
  sibling modules. Matches the convention already used by `examples/agent_scanner_usage.py` and
  `examples/plan_review_usage.py`.
- Patched `examples/verify_micro_implementation.sh` to compute `REPO_ROOT` and `LIB_DIR` absolutely
  rather than using the brittle `cd ../../..` it had when it lived in `commands/lib/`. Verified end-to-end:
  14/14 checks pass.
- Updated one live doc reference: `installer/core/commands/lib/AGENT_TRACKER_INTEGRATION.md` line 340
  now points to `examples/demo_agent_tracker_integration.py`.
- Other references to the old path live only in archived task files / session notes
  (`tasks/archived/`, `tasks/completed/`, `docs/archive/`, `.claude/state/backup/`) — left alone as
  frozen history per `task_workflow` conventions.

## References

- Parent review: [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md) Section 2
- Pairs with: TASK-FIX-CF8D (bin/ prune), TASK-ISH-D09E (manifest replaces blind walk)
