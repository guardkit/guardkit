---
id: TASK-FIX-LI02
title: Fix version management variable typo in install.sh
status: completed
created: 2026-02-22T14:30:00Z
updated: 2026-02-22T15:00:00Z
completed_at: 2026-02-22T15:05:00Z
priority: high
tags: [installer, bug, version-management, bash]
task_type: bug-fix
complexity: 2
parent_review: TASK-REV-LI01
---

# Task: Fix version management variable typo in install.sh

## Description

`installer/scripts/install.sh` defines the version as `AGENTECFLOW_VERSION="2.0.0"` (line 17) but references it as `$AGENTICFLOW_VERSION` (note: 'I' not 'E') in 6 places throughout the version management and configuration sections. The misspelled variable is never assigned, so it expands to an empty string in bash.

This causes:
1. `ln -sf "" ~/.agentecflow/versions/latest` — fails with `No such file or directory`
2. `set -e` then silently terminates the script before `print_summary()` runs — the user never sees the "Next Steps" guidance
3. `versions/current` contains an empty string instead of `2.0.0`
4. `versions/2.0.0/info.json` is never created (written to `versions//info.json` instead)
5. The global `config.json` gets `"version": ""` instead of `"version": "2.0.0"`

**Root cause source**: `installer/scripts/install.sh` lines 535, 1294, 1420, 1423, 1426, 1428
**Review report**: `.claude/reviews/TASK-REV-LI01-linux-install-review.md`
**Evidence**: `docs/reviews/linux_install/linux_insatall_1.md` line 348

## Acceptance Criteria

- [x] All 6 occurrences of `$AGENTICFLOW_VERSION` replaced with `$AGENTECFLOW_VERSION` in `installer/scripts/install.sh`
- [x] After install: `cat ~/.agentecflow/versions/current` outputs `2.0.0`
- [x] After install: `readlink ~/.agentecflow/versions/latest` outputs `2.0.0`
- [x] After install: `~/.agentecflow/versions/2.0.0/info.json` exists and contains `"version": "2.0.0"`
- [x] After install: `~/.config/agentecflow/config.json` contains `"version": "2.0.0"`
- [x] Installation completes and prints the full post-install summary (confirming `set -e` no longer terminates early)
- [x] No other variables or strings are accidentally modified

## Test Requirements

- [ ] Run `./installer/scripts/install.sh` and confirm it prints the full summary section (was previously cut off by the `ln` failure)
- [ ] Confirm `cat ~/.agentecflow/versions/current` = `2.0.0`
- [ ] Confirm `readlink ~/.agentecflow/versions/latest` = `2.0.0`
- [ ] Confirm `~/.agentecflow/versions/2.0.0/info.json` exists with correct content
- [ ] Grep `installer/scripts/install.sh` for `AGENTICFLOW_VERSION` — must return zero results

## Implementation Notes

This is a pure search-and-replace fix. The 6 affected lines are:

| Line | Current (broken) | Fix |
|------|-------------------|-----|
| 535  | `$AGENTICFLOW_VERSION` | `$AGENTECFLOW_VERSION` |
| 1294 | `$AGENTICFLOW_VERSION` | `$AGENTECFLOW_VERSION` |
| 1420 | `$AGENTICFLOW_VERSION` | `$AGENTECFLOW_VERSION` |
| 1423 | `$AGENTICFLOW_VERSION` | `$AGENTECFLOW_VERSION` |
| 1426 | `$AGENTICFLOW_VERSION` | `$AGENTECFLOW_VERSION` |
| 1428 | `$AGENTICFLOW_VERSION` | `$AGENTECFLOW_VERSION` |

The correctly-defined variable (`AGENTECFLOW_VERSION="2.0.0"`) is at line 17 and must not be changed.

After the rename, optionally add a defensive guard around the `ln` call at line 1423 to surface a clear error if the variable is somehow empty in future:

```bash
if [ -z "$AGENTECFLOW_VERSION" ]; then
    print_error "AGENTECFLOW_VERSION is not set — cannot create versions/latest symlink"
    exit 1
fi
ln -sf "$AGENTECFLOW_VERSION" "$INSTALL_DIR/versions/latest"
```

## Related

- Review report: `.claude/reviews/TASK-REV-LI01-linux-install-review.md`
- Install log: `docs/reviews/linux_install/linux_insatall_1.md`
- Installer: `installer/scripts/install.sh`
- Companion fix: TASK-FIX-LI01 (PATH and completions)
