---
id: TASK-FIX-8374
title: Fix graphiti-check Python environment resolution with wrapper script
status: completed
created: 2026-03-27T00:00:00Z
updated: 2026-03-27T14:15:00Z
completed: 2026-03-27T14:15:00Z
completed_location: tasks/completed/TASK-FIX-8374/
priority: medium
tags: [graphiti, installer, python-env, system-arch, infrastructure]
parent_review: TASK-REV-CFE0
feature_id: FEAT-CFE0
implementation_mode: task-work
wave: 1
complexity: 3
---

# Task: Fix graphiti-check Python Environment Resolution

## Description

The `graphiti-check` CLI tool (symlinked from `~/.agentecflow/bin/graphiti-check` to `installer/core/commands/lib/graphiti_check.py`) uses `#!/usr/bin/env python3` which resolves to the system Python. The system Python does NOT have `graphiti-core` installed, causing `/system-arch` and other commands that call `get_graphiti()` to report "Graphiti unavailable" even when all infrastructure is healthy.

This was identified as the root cause of the `system-arch-graphiti-failed` incident documented in `docs/reviews/agentic-dataset-factory/system-arch-graphiti-failed.md`.

## Root Cause

- `graphiti_check.py` shebang: `#!/usr/bin/env python3` resolves to system Python
- System Python lacks `graphiti-core`, `redis`, and other dependencies
- GuardKit venv (`guardkit/.venv/`) has all dependencies installed correctly
- Secondary issue: symlink target (`graphiti_check.py`) lacks execute permission

## Recommended Fix (Option B from failure report)

Have the GuardKit installer generate a **wrapper shell script** instead of symlinking directly to the `.py` file:

```bash
#!/usr/bin/env bash
exec /path/to/guardkit/.venv/bin/python /path/to/graphiti_check.py "$@"
```

## Acceptance Criteria

- [x] Installer generates a wrapper script at `~/.agentecflow/bin/graphiti-check` instead of a symlink
- [x] Wrapper explicitly invokes the GuardKit venv Python
- [x] `graphiti_check.py` has execute permission set (`chmod +x`)
- [x] Running `graphiti-check` from any directory correctly reports Graphiti availability when infrastructure is up
- [x] Existing functionality unchanged for Claude Code sessions (MCP path unaffected)
- [x] Installer handles upgrade scenario (replaces existing symlink with wrapper)

## Key Files

- `installer/core/commands/lib/graphiti_check.py` (the tool script)
- `installer/scripts/install.sh` (creates the symlink, needs to create wrapper instead)
- `docs/reviews/agentic-dataset-factory/system-arch-graphiti-failed.md` (full diagnosis)

## Notes

This does NOT affect autobuild — autobuild uses GuardKit's venv directly and loads Graphiti successfully. This only affects CLI tool scripts invoked via shell symlinks.
