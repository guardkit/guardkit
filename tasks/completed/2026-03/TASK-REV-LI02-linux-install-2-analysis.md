---
id: TASK-REV-LI02
title: Analyse second Linux installation of GuardKit on Dell ProMax GB10 (aarch64)
status: backlog
created: 2026-02-22T13:30:00Z
updated: 2026-02-22T13:30:00Z
priority: high
tags: [review, linux, installation, arm64, aarch64, path, installer, dell-promax, regression]
task_type: review
complexity: 4
decision_required: true
hardware: Dell ProMax GB10 (aarch64/ARM64)
install_log: docs/reviews/linux_install/linux_install_2.md
parent_review: TASK-REV-LI01
related_fixes: [TASK-FIX-LI01, TASK-FIX-LI02]
---

# Task: Analyse second Linux installation of GuardKit on Dell ProMax GB10 (aarch64)

## Description

Review the output of the second GuardKit installation on Linux (Dell ProMax GB10, aarch64), run after implementing the fixes from [TASK-REV-LI01](../../completed/TASK-REV-LI01-linux-install-analysis.md), [TASK-FIX-LI01](../../completed/TASK-FIX-LI01-installer-path-and-completions.md), and [TASK-FIX-LI02](../../completed/TASK-FIX-LI02-version-variable-typo.md).

**Installation log**: `docs/reviews/linux_install/linux_install_2.md`
**Target machine**: Dell ProMax GB10, `aarch64` architecture, Ubuntu (bash shell)
**Installer**: `installer/scripts/install.sh`
**Installed to**: `/home/richardwoollcott/.agentecflow`
**Context**: Re-install over an existing installation (backups created for both `.agentecflow` and `.claude`)

## Fixes Verified From LI01

| Fix | Expected | Observed | Status |
|-----|----------|----------|--------|
| TASK-FIX-LI02: Version variable typo | `✓ Version management configured` | Line 181: `✓ Version management configured` | ✅ FIXED |
| TASK-FIX-LI01: Node.js warning clarity | Lists affected templates | Lines 11-13: lists `react-typescript`, `nextjs-fullstack`, `react-fastapi-monorepo` | ✅ FIXED |
| TASK-FIX-LI01: PATH in shell integration | `~/.local/bin` in `.bashrc` block | Shell integration `already configured` — block NOT re-written | ⚠ PARTIAL (see Issue 1) |
| TASK-FIX-LI01: Completion file/names | `guardkit.bash` with correct names | Not directly observable in log | ❓ UNVERIFIED |

## New Features Observed in Install 2

Install 2 added three new steps not present in install 1:

1. **Cache directories** — `ℹ Setting up cache directories... ✓ Cache directories created`
2. **Claude Code integration** — Creates symlinks:
   - `~/.claude/commands → ~/.agentecflow/commands`
   - `~/.claude/agents → ~/.agentecflow/agents`
3. **Python command script symlinks** — `ℹ Setting up Python command script symlinks... ℹ Found 93 Python command script(s)`

## Issues Found

### Issue 1 — REGRESSION: guardkit-py CLI still not on PATH on re-install

**Symptom** (lines 103-110):

```
WARNING: The script guardkit-py is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
...
⚠ guardkit-py CLI not found in PATH
ℹ You may need to restart your shell or add ~/.local/bin to PATH
```

**Root cause**: TASK-FIX-LI01 added `$HOME/.local/bin` to the shell integration block written by `setup_shell_integration()`. However, on this re-install the installer detected that shell integration was **already configured** (line 175: `ℹ Shell integration already configured`) and did NOT re-write the block. The existing `.bashrc` block (written during install 1, before the fix) therefore still lacks `$HOME/.local/bin`.

**Impact**: PATH fix from TASK-FIX-LI01 only benefits fresh installs. Any user upgrading from a pre-fix installation still has the broken PATH. This is a **partial regression** — the fix is correct for new installs but the upgrade path is broken.

**Fix required**: The "already configured" check in `setup_shell_integration()` must detect whether the existing block contains `$HOME/.local/bin` and patch it in-place (or re-write the whole block) if it is absent.

---

### Issue 2 — INCOMPLETE: Python command script symlinks — no success confirmation

**Symptom** (lines 192-194, end of log):

```
ℹ Setting up Python command script symlinks...
ℹ Found 93 Python command script(s)
richardwoollcott@promaxgb10-41b1:~/Projects/appmilla_github/guardkit/installer/scripts$
```

The installer outputs "Found 93 Python command script(s)" and then the shell prompt returns immediately with **no success confirmation** (`✓ Python command script symlinks created` or similar). Every other installer step that succeeds prints a `✓` line.

**Root cause hypotheses**:
1. The symlink creation loop runs silently (no output on success) and the script exits normally — the `✓` confirmation message is simply missing from the code
2. The symlink creation fails silently (the loop encounters an error but the script doesn't surface it)
3. The post-install summary was meant to print after this step but is missing from the log (compare: install 1 also had no post-install summary due to early `set -e` exit from the `ln` bug — that bug is now fixed, so summary should now appear)

**Impact**: Unknown. If the symlinks were created, the 93 Python command scripts may not be reachable via the expected paths. If they failed silently, no error was reported.

**Fix required**:
- Add a `✓ Python command script symlinks created (N links)` success message after the loop
- Add error handling if any symlink creation fails
- Investigate why no post-install summary is printed (related to Issue 3)

---

### Issue 3 — MISSING: Post-install summary / "Next Steps" not printed

**Symptom**: The install log ends at line 194 with the shell prompt. There is no post-install summary section (the "Next Steps" or completion banner that `print_summary()` should emit after all steps complete).

**Root cause hypothesis**: In install 1, the `set -e` early exit caused by the `ln` bug (TASK-FIX-LI02) prevented `print_summary()` from running. TASK-FIX-LI02 fixed the `ln` bug, so install 2 should reach `print_summary()`. However, if the Python symlink step (Issue 2) itself causes a non-zero exit, `set -e` could again terminate the script before `print_summary()` runs.

**Impact**: Users receive no post-install guidance (next steps, verification commands, documentation links). This is a usability gap regardless of root cause.

**Fix required**: Determine if `print_summary()` is called after the Python symlinks step, and whether Issue 2 is causing an early exit.

---

### Issue 4 — UNVERIFIED: Claude Code integration symlinks created correctly

**Symptom** (lines 184-190):

```
ℹ Setting up Claude Code integration...
✓ Created ~/.claude directory
✓ Claude Code integration configured successfully
ℹ   Commands: ~/.claude/commands → ~/.agentecflow/commands
ℹ   Agents: ~/.claude/agents → ~/.agentecflow/agents

✓ All guardkit commands now available in Claude Code!
```

This step succeeded and is a new feature (not present in install 1). However, it has not been functionally verified:

1. Do `~/.claude/commands` and `~/.claude/agents` actually resolve as symlinks to `~/.agentecflow/commands` and `~/.agentecflow/agents`?
2. Does Claude Code pick up the commands and agents through these symlinks on this machine?
3. If `.claude` is overwritten on a future install, do the symlinks survive or get replaced with directories?

**Impact**: If the symlinks are correct, Claude Code integration works out of the box — significant UX improvement. If not verified, it may give false confidence.

---

### Issue 5 — INFORMATIONAL: Shell integration correctly detects existing config

**Observation** (line 175):

```
ℹ Shell integration already configured
```

The installer correctly detected that `.bashrc` already had the GuardKit shell integration block and did not duplicate it. This is correct behaviour for re-installs. However, it is the direct cause of Issue 1 above — the "already configured" path needs to also handle migrating the PATH entry.

---

## Review Scope

### Installer Files to Analyse

1. `installer/scripts/install.sh` — `setup_shell_integration()` (Issue 1), Python symlinks step (Issue 2), `print_summary()` call (Issue 3), Claude Code integration (Issue 4)

### Key Questions to Answer

1. **Issue 1 — PATH upgrade**: Does `setup_shell_integration()` check whether `~/.local/bin` is already in the existing block before skipping? If not, what is the minimal change to patch the PATH in-place on re-installs?
2. **Issue 2 — Symlinks**: What does the Python symlink creation loop look like in `install.sh`? Does it output a success confirmation? Does it use `set -e`?
3. **Issue 3 — Summary**: Is `print_summary()` called unconditionally at the end of `main()`? Or is it inside a conditional branch that may have been skipped?
4. **Issue 4 — Claude Code**: Run `ls -la ~/.claude/commands ~/.claude/agents` on the target machine to verify symlinks resolve correctly.

## Acceptance Criteria

- [ ] Root cause of PATH not being updated on re-install identified (Issue 1)
- [ ] Fix proposed for `setup_shell_integration()` to update PATH in existing `.bashrc` blocks
- [ ] Python symlinks step code inspected — whether `✓` confirmation is missing or step is failing silently (Issue 2)
- [ ] Post-install summary absence explained — whether it is an Issue 2 cascade or an unrelated bug (Issue 3)
- [ ] Claude Code integration symlinks verified on target machine (Issue 4)
- [ ] All issues triaged as: `bug-fix-required`, `documentation-only`, `by-design`, or `deferred`
- [ ] Follow-up `TASK-FIX-LI03+` tasks created for each `bug-fix-required` finding
- [ ] Review report written to `.claude/reviews/TASK-REV-LI02-linux-install-review.md`

## Test Requirements

- [ ] After fix for Issue 1: run install on a machine with existing `.bashrc` block that lacks `~/.local/bin`; confirm `guardkit` is on PATH in a new terminal without manual intervention
- [ ] After fix for Issue 2: confirm `✓` confirmation is printed and symlinks resolve with `ls -la ~/.agentecflow/bin/`
- [ ] After fix for Issue 3: confirm post-install summary prints at end of install
- [ ] No regression on fresh installs (all fixes must be additive, not break first-time behaviour)
- [ ] No regression on macOS (zsh path must be tested if `setup_shell_integration()` changes)

## Implementation Notes

This is a **review task** — no code changes are made here. Findings produce one or more follow-up `TASK-FIX-LI03+` tasks.

The three new installer steps added since install 1 (cache dirs, Claude Code integration, Python symlinks) were likely added as part of the same work that implemented TASK-FIX-LI01/LI02. Their introduction and any interaction with Issues 2/3 should be scoped in the review.

## Related

- Install log (this review): `docs/reviews/linux_install/linux_install_2.md`
- Install log (previous): `docs/reviews/linux_install/linux_insatall_1.md`
- Previous review: `tasks/completed/TASK-REV-LI01-linux-install-analysis.md`
- Fixes from LI01: `tasks/completed/TASK-FIX-LI01-installer-path-and-completions.md`, `tasks/completed/TASK-FIX-LI02-version-variable-typo.md`
- Installer: `installer/scripts/install.sh`
