---
id: TASK-FIX-8B4F
title: Delete hardcoded-host graphiti_diagnose_v2.py and _v3.py
status: completed
created: 2026-04-11T17:55:00Z
updated: 2026-04-11T18:35:00Z
completed: 2026-04-11T18:35:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-FIX-8B4F/
priority: low
tags: [cleanup, commands-lib, graphiti]
task_type: implementation
parent_review: TASK-REV-C1B4
feature_id: FEAT-E1AF
wave: 1
conductor_workspace: commands-lib-cleanup-wave1-2
implementation_mode: direct
complexity: 1
depends_on: []
---

# Task: Delete `graphiti_diagnose_v2.py` and `graphiti_diagnose_v3.py`

## Background

Surfaced by [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md) Section 4. The directory
`installer/core/commands/lib/` contains three `graphiti_diagnose*.py` files with identical mtimes, confirmed by
the review to be **not semantic versions but three attempts to debug a specific Graphiti/FalkorDB incident**:

| File | Abstraction | Portable? |
|---|---|---|
| `graphiti_diagnose.py` | Uses `guardkit.knowledge.graphiti_client.GraphitiClient` + `load_graphiti_config()` | ✅ Yes |
| `graphiti_diagnose_v2.py` | Direct `redis.Redis("whitestocks", 6379)` — **hardcoded** host | ❌ No — only runs on the original user's machine |
| `graphiti_diagnose_v3.py` | Direct `redis.Redis("whitestocks", 6379)` — same hardcoding, plus a hardcoded `target_graphs` list | ❌ No — same |

Both `_v2` and `_v3` bypass the project's Graphiti abstraction layer to go straight to Redis. On any other machine
(including CI) they will fail at import time with a connection error. They are single-use diagnostic scripts that
were left behind after the underlying issue was understood.

Meanwhile, `install.sh` blindly symlinks all three into `~/.agentecflow/bin/` (as `graphiti-diagnose`,
`graphiti-diagnose-v2`, `graphiti-diagnose-v3`), promoting the hardcoded debug scripts to global shell commands
on every user's PATH.

## Description

Delete the two non-portable variants. Keep the `GraphitiClient`-based version.

### Files to delete

1. `installer/core/commands/lib/graphiti_diagnose_v2.py`
2. `installer/core/commands/lib/graphiti_diagnose_v3.py`

### Files to keep

- `installer/core/commands/lib/graphiti_diagnose.py` — uses the correct abstraction, is portable.

### Optional alternative (only if the user objects to deletion)

If there is any reason to preserve `_v2` / `_v3` as historical exploration notes, move them to
`docs/troubleshooting/graphiti-diagnostics/` with a one-line README explaining that they hardcode `whitestocks:6379`
and are single-use artifacts. Default to delete.

### Verification

- `python3 installer/core/commands/lib/graphiti_diagnose.py --help` (or direct run) still works after deletion.
  Note: it reads config from `.guardkit/graphiti.yaml` — do not break that.
- Nothing imports `graphiti_diagnose_v2` or `_v3` (verified in the review grep).

## Acceptance Criteria

- [ ] `graphiti_diagnose_v2.py` deleted from `installer/core/commands/lib/`.
- [ ] `graphiti_diagnose_v3.py` deleted from `installer/core/commands/lib/`.
- [ ] `graphiti_diagnose.py` untouched and still importable.
- [ ] No remaining live references to `graphiti_diagnose_v2` or `graphiti_diagnose_v3` (grep the tree, excluding
      historical artifacts per review notes).
- [ ] Stale `~/.agentecflow/bin/graphiti-diagnose-v2` and `-v3` symlinks will be auto-pruned by TASK-FIX-CF8D — do
      not manually touch them in this task.

## References

- Parent review: [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md) Section 4
- Depends-on (downstream cleanup): TASK-FIX-CF8D (prunes the stale bin symlinks after this task deletes the sources)
