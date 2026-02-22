---
id: TASK-FIX-LI09
title: Suppress pip PATH warning during install with --no-warn-script-location
status: completed
created: 2026-02-22T15:30:00Z
updated: 2026-02-22T15:30:00Z
completed: 2026-02-22T15:30:00Z
priority: normal
tags: [installer, linux, pip, python, warning, polish]
task_type: bug-fix
complexity: 1
parent_review: TASK-REV-LI04
completed_location: tasks/completed/TASK-FIX-LI09/
---

# Task: Suppress pip PATH warning during install with --no-warn-script-location

## Description

During installation, pip emits a `WARNING:` line that is now the only remaining noise item in the install output:

```
WARNING: The script guardkit-py is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
```

This warning is emitted by pip itself (not the installer) when a script entry point is installed into a directory not in `$PATH` at install time. The installer already handles PATH configuration (deferred to shell restart via TASK-FIX-LI06), so this warning is misleading to users.

The fix is to pass `--no-warn-script-location` to both pip install invocations in `install_python_package()`.

**File**: `installer/scripts/install.sh`
**Function**: `install_python_package()` (lines 402–480)
**Evidence**: Install 4 log, lines 103–104
**Review**: `tasks/backlog/TASK-REV-LI04-linux-install-4-analysis.md` Issue 2

## Root Cause

`install_python_package()` has two pip install calls:

```bash
# Line 428 — primary (--break-system-packages)
python3 -m pip install -e "$repo_root[autobuild]" --break-system-packages 2>&1

# Line 436 — fallback (--user)
python3 -m pip install -e "$repo_root[autobuild]" --user 2>&1
```

Neither carries `--no-warn-script-location`. pip emits the warning when `~/.local/bin` is not in `$PATH` at the time of install. On this machine (aarch64 Ubuntu), PATH is patched post-install (via shell restart), so the warning fires during install.

## Fix Applied

Added `--no-warn-script-location` to both pip install calls in `installer/scripts/install.sh`.

**Line 428:**
```bash
python3 -m pip install -e "$repo_root[autobuild]" --break-system-packages --no-warn-script-location 2>&1
```

**Line 436:**
```bash
python3 -m pip install -e "$repo_root[autobuild]" --user --no-warn-script-location 2>&1
```

## Acceptance Criteria

- [x] Both pip install calls in `install_python_package()` include `--no-warn-script-location`
- [ ] Install output contains no `WARNING:` lines (no pip PATH warning)
- [ ] Install still succeeds and `guardkit-py` script is installed to `~/.local/bin`
- [ ] No regression on any previously fixed items

## Test Requirements

- [ ] After fix: `grep "WARNING:" <(./install.sh 2>&1)` returns no matches
- [ ] After fix: `guardkit` command available after `source ~/.bashrc`
- [ ] No regression on macOS (flag is supported by pip on all platforms)

## Related

- Review: `tasks/backlog/TASK-REV-LI04-linux-install-4-analysis.md`
- Review report: `.claude/reviews/TASK-REV-LI04-linux-install-review.md`
- Companion fix (agent count): `tasks/backlog/TASK-FIX-LI08-print-summary-agent-count-stack-agents.md`
- Predecessor (installer PATH messaging): TASK-FIX-LI06
- Installer: `installer/scripts/install.sh` — `install_python_package()` (~lines 428, 436)
