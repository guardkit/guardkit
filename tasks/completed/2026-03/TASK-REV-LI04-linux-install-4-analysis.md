---
id: TASK-REV-LI04
title: Analyse fourth Linux installation of GuardKit on Dell ProMax GB10 (aarch64)
status: review_complete
created: 2026-02-22T14:45:00Z
updated: 2026-02-22T15:30:00Z
priority: normal
tags: [review, linux, installation, arm64, aarch64, installer, dell-promax, polish]
task_type: review
complexity: 2
decision_required: false
hardware: Dell ProMax GB10 (aarch64/ARM64)
install_log: docs/reviews/linux_install/linux_install_4.md
parent_review: TASK-REV-LI03
related_fixes: [TASK-FIX-LI06, TASK-FIX-LI07]
review_results:
  mode: code-quality
  depth: standard
  findings_count: 2
  recommendations_count: 2
  decision: implement
  report_path: .claude/reviews/TASK-REV-LI04-linux-install-review.md
  completed_at: 2026-02-22T15:30:00Z
  follow_up_tasks: [TASK-FIX-LI08, TASK-FIX-LI09]
---

# Task: Analyse fourth Linux installation of GuardKit on Dell ProMax GB10 (aarch64)

## Description

Review the output of the fourth GuardKit installation on Linux (Dell ProMax GB10, aarch64), run after implementing [TASK-FIX-LI06](../../completed/2026-02/TASK-FIX-LI06/TASK-FIX-LI06.md) and [TASK-FIX-LI07](../../completed/2026-02/TASK-FIX-LI07/TASK-FIX-LI07.md).

**Installation log**: `docs/reviews/linux_install/linux_install_4.md`
**Target machine**: Dell ProMax GB10, `aarch64` architecture, Ubuntu (bash shell)
**Installer**: `installer/scripts/install.sh`
**Context**: Re-install over existing installation (backups created for `.agentecflow` and `.claude`)

The install is functionally clean. One item from TASK-FIX-LI07 did not land (agent count). One cosmetic pip warning remains. Everything else is resolved.

---

## Fixes Verified From LI03

| Fix | Expected | Observed | Status |
|-----|----------|----------|--------|
| TASK-FIX-LI06: No mid-install `⚠` PATH warning | Warning removed from step 5; deferred `ℹ` near end | Line 284: `ℹ guardkit-py installed to ~/.local/bin — restart your shell or run: source ~/.bashrc` (appears just before summary banner) | ✅ FIXED |
| TASK-FIX-LI07 Issue B: Template descriptions | `fastmcp-python` and `mcp-typescript` show descriptions | Lines 310-311: both templates have descriptions | ✅ FIXED |
| TASK-FIX-LI07 Issue A: Agent count via `find` | Summary shows `62` agents | Line 296: `🤖 AI Agents: 30 (including clarification-questioner)` | ❌ NOT FIXED |
| TASK-FIX-LI03: PATH check shows "already configured" | `.bashrc` already has `~/.local/bin` so no re-patch needed | Line 173: `ℹ Shell integration already configured` | ✅ CORRECT |

---

## Issues Found

### Issue 1 — OUTSTANDING: Agent count still shows 30 despite TASK-FIX-LI07 being marked complete

**Symptom** (line 296):

```
🤖 AI Agents: 30 (including clarification-questioner)
```

The install step (line 136) still correctly reports:

```
✓ Installed 62 total agents (30 global + 32 stack-specific)
```

**Root cause**: TASK-FIX-LI07 Issue A specified replacing the shallow `ls -1 "$INSTALL_DIR/agents/"*.md | wc -l` glob in `print_summary()` with `find "$INSTALL_DIR/agents/" -name "*.md" | wc -l`. The task was marked `completed: 2026-02-22T15:05:00Z`, but install 4 (run at `20260222_143237`, i.e. 14:32) was run before the fix was committed, or the fix was not actually applied to `install.sh`.

**Verification needed**: Check whether `install.sh` currently contains `ls -1 "$INSTALL_DIR/agents/"*.md` or `find "$INSTALL_DIR/agents/"` for the agent count. If the `ls` glob is still present, the fix was not applied and needs to be re-done.

**Impact**: Post-install summary undercounts agents by 32 (shows 30 of 62). Misleading but not functional.

---

### Issue 2 — COSMETIC: pip-level PATH warning still shown during install

**Symptom** (lines 103-104):

```
WARNING: The script guardkit-py is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
```

**Root cause**: This warning is emitted by pip itself, not the installer. pip warns whenever it installs a script entry point into a directory that is not in `$PATH` at the time of installation. The installer cannot suppress pip's own stderr output without passing `--no-warn-script-location` to the `pip install` invocation.

**Impact**: The warning appears mid-install and is now the only `WARNING:` level message remaining. Since TASK-FIX-LI06 removed the installer's own `⚠` message, this is the last noise item. It creates minor confusion for users who know the PATH situation is being managed by the installer.

**Fix**: Add `--no-warn-script-location` to the `pip install` call in `install_python_package()`. This suppresses the pip-level warning without affecting install behaviour.

---

## Review Scope

### Installer Files to Analyse

1. `installer/scripts/install.sh` — `print_summary()` (Issue 1: confirm `ls` vs `find` for agent count), `install_python_package()` (Issue 2: add `--no-warn-script-location`)

### Key Questions to Answer

1. **Issue 1**: Does `install.sh` currently use `ls -1 "$INSTALL_DIR/agents/"*.md` or `find "$INSTALL_DIR/agents/" -name "*.md"` for the agent count in `print_summary()`? If `ls` is still present, the fix was not committed.
2. **Issue 2**: What is the exact `pip install` invocation line in `install_python_package()`? Confirm `--no-warn-script-location` is not already present.

## Acceptance Criteria

- [ ] `install.sh` inspected — confirm whether `ls` or `find` is used for agent count
- [ ] If `ls` is still present: re-apply the `find` fix from TASK-FIX-LI07 Issue A
- [ ] Post-install summary shows `AI Agents: 62` (or correct total matching `Installed 62 total agents`)
- [ ] `--no-warn-script-location` added to `pip install` invocation — no pip `WARNING:` lines in install output
- [ ] All issues triaged as `bug-fix-required`, `by-design`, or `completed`
- [ ] Follow-up `TASK-FIX-LI08+` tasks created for each `bug-fix-required` finding
- [ ] Review report written to `.claude/reviews/TASK-REV-LI04-linux-install-review.md`

## Test Requirements

- [ ] After fixes: post-install summary shows correct agent count (62)
- [ ] After fixes: no `WARNING:` lines in install output
- [ ] No regression on any previously fixed items

## Implementation Notes

This is a **short review** — only two items, both small. Complexity is 2 (down from 3 for LI03). Likely produces two small fix tasks (`TASK-FIX-LI08` and `TASK-FIX-LI09`, or a single combined task if they are trivially small).

After addressing these two items, the Linux installer can be considered **stable on aarch64 Ubuntu** for the primary use case (re-install from source repo with Python user install).

## Related

- Install log (this review): `docs/reviews/linux_install/linux_install_4.md`
- Install log (install 3): `docs/reviews/linux_install/linux_install_3.md`
- Previous review: `tasks/backlog/TASK-REV-LI03-linux-install-3-analysis.md`
- Fixes from LI03: `tasks/completed/2026-02/TASK-FIX-LI06/TASK-FIX-LI06.md`, `tasks/completed/2026-02/TASK-FIX-LI07/TASK-FIX-LI07.md`
- Installer: `installer/scripts/install.sh`
