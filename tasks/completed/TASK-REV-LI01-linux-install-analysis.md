---
id: TASK-REV-LI01
title: Analyse first Linux installation of GuardKit on Dell ProMax GB10 (aarch64)
status: completed
created: 2026-02-22T12:24:30Z
updated: 2026-02-22T14:00:00Z
priority: high
tags: [review, linux, installation, arm64, aarch64, path, installer, dell-promax]
task_type: review
complexity: 4
decision_required: true
hardware: Dell ProMax GB10 (aarch64/ARM64)
install_log: docs/reviews/linux_install/linux_insatall_1.md
---

# Task: Analyse first Linux installation of GuardKit on Dell ProMax GB10 (aarch64)

## Description

Review the output of the first-ever GuardKit installation on Linux (Dell ProMax GB10, ARM64/aarch64 architecture). The install completed but produced several warnings and one clear bug. This review should triage each issue, determine root causes, and produce concrete fixes for the installer and/or documentation.

**Installation log**: `docs/reviews/linux_install/linux_insatall_1.md`
**Target machine**: Dell ProMax GB10, `aarch64` architecture, Ubuntu (bash shell)
**Installer**: `installer/scripts/install.sh`
**Installed to**: `/home/richardwoollcott/.agentecflow`

## Installation Summary

Overall the install succeeded:
- Python 3.12 found, all Python dependencies installed
- `guardkit-py` package built and installed (editable mode)
- Claude Agent SDK available, AutoBuild ready
- 62 agents installed (30 global + 32 stack-specific)
- Shell integration added to `~/.bashrc`

## Issues Found

### Issue 1 — CRITICAL: guardkit-py CLI not on PATH (functional blocker)

**Symptom**: Multiple `WARNING: The script X is installed in '/home/richardwoollcott/.local/bin' which is not on PATH` messages, culminating in:

```
⚠ guardkit-py CLI not found in PATH
ℹ You may need to restart your shell or add ~/.local/bin to PATH
```

**Affected scripts**: `dotenv`, `tqdm`, `f2py`, `numpy-config`, `httpx`, `openai`, `uvicorn`, `jsonschema`, `mcp`, `guardkit-py`

**Root cause hypothesis**: pip is installing to `~/.local/bin` (user install, because system site-packages is not writeable), but `~/.local/bin` is not in the current `$PATH` at installer execution time. The installer adds shell integration to `~/.bashrc` but does not ensure `~/.local/bin` is included in that integration, and does not verify PATH after sourcing.

**Impact**: After install, the user cannot run `guardkit` from a new terminal until `~/.local/bin` is in their PATH. The `source ~/.bashrc` suggestion (line 342 of install log) should fix it post-install, but the installer should both add `~/.local/bin` to PATH in the shell integration block AND verify the CLI is reachable before completing.

---

### Issue 2 — BUG: Version management symlink creation fails

**Symptom** (last meaningful line of output, line 348):

```
ln: failed to create symbolic link '/home/richardwoollcott/.agentecflow/versions/latest' -> '': No such file or directory
```

**Root cause hypothesis**: The target of the symlink is an empty string — the version variable is not being set before the `ln` call. This could mean:
- A version variable is unset/empty in the installer script
- The `versions/` directory does not exist at the time of `ln`
- The install path for the versioned build artefact was not resolved correctly

**Impact**: Version management is broken; the `latest` symlink is missing. This may prevent future upgrade/rollback logic from working. The installer exits silently after this failure — it should either surface a clear error or handle the empty variable gracefully.

---

### Issue 3 — Node.js not found

**Symptom**:

```
⚠ Node.js not found. Some features may be limited.
```

**Impact**: Minor on this machine (user has not requested Node.js features). The warning is correct but could be clearer about which specific features are affected. Consider listing the exact commands/templates that require Node.js so users can make an informed decision.

---

### Issue 4 — Installer installs to `.agentecflow` but package says `guardkit`

**Observation**: The install target is `/home/richardwoollcott/.agentecflow` (line 8), but the PyPI package is `guardkit-py` and the CLI entry points are named `guardkit`, `guardkit-init`, `gk`, `gki`. This may confuse users who look for `~/.guardkit` or `~/.agentecflow`.

**Impact**: Documentation/UX clarity issue; not a functional blocker.

---

### Issue 5 — Backup created for existing `.claude` directory (informational)

**Symptom**:

```
⚠ Found existing installations: .claude
ℹ Creating backup of .claude at /home/richardwoollcott/.claude.backup.20260222_122430
✓ Backup created: /home/richardwoollcott/.claude.backup.20260222_122430
```

**Impact**: None — this is correct behaviour. The installer correctly backs up before overwriting. Worth noting in documentation so users are aware their previous `.claude` config is preserved at `.claude.backup.*`.

---

## Review Scope

### Installer Files to Analyse

1. `installer/scripts/install.sh` — main installer (primary focus)
2. Any version management logic within the installer (symlink creation, version variable)
3. Shell integration block added to `~/.bashrc`

### Key Questions to Answer

1. **PATH fix**: Does the shell integration block added to `~/.bashrc` include `export PATH="$HOME/.local/bin:$PATH"`? If not, that is the fix.
2. **Symlink bug**: What is the version variable in `install.sh` that is passed to `ln`? Where is it set, and why is it empty?
3. **Post-install verification**: Does the installer re-check CLI availability after sourcing the new PATH? Should it?
4. **Node.js messaging**: Can we list the specific features requiring Node.js in the warning message?
5. **Directory naming**: Is `.agentecflow` the intended permanent name, or is a rename to `.guardkit` planned?

## Acceptance Criteria

- [x] Root cause of CLI-not-on-PATH identified and fix proposed
- [x] Root cause of symlink failure (`ln: failed to create symbolic link ... -> ''`) identified and fix proposed
- [x] Node.js missing feature list documented
- [x] All issues triaged as: `bug-fix-required`, `documentation-only`, `by-design`, or `deferred`
- [x] At least one concrete fix task created per `bug-fix-required` issue
- [x] Review report written to `.claude/reviews/TASK-REV-LI01-linux-install-review.md`

## Test Requirements

- [ ] Installer fix for PATH should be verified by running install in a clean shell where `~/.local/bin` is not in PATH
- [ ] Symlink fix should be verified by confirming `/home/.../.agentecflow/versions/latest` resolves correctly post-install
- [ ] No regression on macOS installer (if shared code is changed)

## Implementation Notes

This is a **review task** — no code changes are made here. Findings will produce one or more follow-up `TASK-FIX-*` tasks for the installer.

## Related

- Install log: `docs/reviews/linux_install/linux_insatall_1.md`
- Installer: `installer/scripts/install.sh`
- Shell integration: `~/.bashrc` (post-install, on target machine)
