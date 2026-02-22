---
id: TASK-FIX-LI05
title: Verify and harden Claude Code integration symlinks in setup_claude_integration
status: completed
created: 2026-02-22T13:45:00Z
updated: 2026-02-22T14:05:00Z
completed: 2026-02-22T14:05:00Z
completed_location: tasks/completed/2026-02/TASK-FIX-LI05/
priority: normal
tags: [installer, linux, claude-code, symlinks, verification, hardening]
task_type: bug-fix
complexity: 2
parent_review: TASK-REV-LI02
---

# Task: Verify and harden Claude Code integration symlinks in setup_claude_integration

## Description

Install 2 added a new `setup_claude_integration()` step that creates symlinks:

```
~/.claude/commands → ~/.agentecflow/commands
~/.claude/agents   → ~/.agentecflow/agents
```

The installer reported success (lines 184-190 of the install 2 log), but the symlinks have not been functionally verified on the target machine. Additionally, a code review of `setup_claude_integration()` reveals two hardening gaps that could cause silent failures on future installs.

**File**: `installer/scripts/install.sh`
**Function**: `setup_claude_integration()` (~lines 1601-1647)
**Evidence**: `docs/reviews/linux_install/linux_install_2.md` lines 184-190
**Review**: `tasks/backlog/TASK-REV-LI02-linux-install-2-analysis.md` Issue 4

## Issues to Address

### Issue A — Symlinks not verified on target machine (functional verification)

The installer's own verification block (lines 1636-1646) uses `[ -L ... ]` to confirm both symlinks exist as symlinks, but does **not** verify that they resolve to valid targets (i.e. the targets actually exist). A dangling symlink would pass `[ -L ]` but fail at runtime.

**Verification commands to run on the Dell ProMax GB10**:

```bash
# Confirm both exist as symlinks
ls -la ~/.claude/commands ~/.claude/agents

# Confirm targets are the expected directories
readlink ~/.claude/commands   # expected: /home/richardwoollcott/.agentecflow/commands
readlink ~/.claude/agents     # expected: /home/richardwoollcott/.agentecflow/agents

# Confirm targets actually exist and contain files
ls ~/.agentecflow/commands | head -5
ls ~/.agentecflow/agents | head -5

# Confirm Claude Code can see the commands (check from the Claude Code perspective)
ls ~/.claude/commands | head -5
ls ~/.claude/agents | head -5
```

If any of these fail, a follow-up code fix is required.

### Issue B — Verification uses `[ -L ]` but not `[ -L ] && readlink -e ]` (dangling symlink risk)

The verification in `setup_claude_integration()` is:

```bash
if [ -L "$HOME/.claude/commands" ] && [ -L "$HOME/.claude/agents" ]; then
    print_success "Claude Code integration configured successfully"
    ...
else
    print_error "Failed to create symlinks for Claude Code integration"
    ...
fi
```

`[ -L path ]` returns true even for a **dangling symlink** (symlink exists but target does not). The verification should also confirm the targets exist using `-e` (follows the symlink and checks the target):

```bash
if [ -L "$HOME/.claude/commands" ] && [ -e "$HOME/.claude/commands" ] && \
   [ -L "$HOME/.claude/agents" ]   && [ -e "$HOME/.claude/agents" ]; then
```

### Issue C — `set -e` risk on `ln -sf` failure

The two `ln -sf` calls that create the symlinks are **not** guarded:

```bash
ln -sf "$INSTALL_DIR/commands" "$HOME/.claude/commands"
ln -sf "$INSTALL_DIR/agents" "$HOME/.claude/agents"
```

If either `ln` call fails (e.g. permissions issue, `~/.claude` not writeable), `set -e` will exit the script immediately with no error message printed. The function would appear to silently fail. These should be guarded with explicit error handling:

```bash
if ! ln -sf "$INSTALL_DIR/commands" "$HOME/.claude/commands"; then
    print_error "Failed to create ~/.claude/commands symlink"
    return 1
fi
if ! ln -sf "$INSTALL_DIR/agents" "$HOME/.claude/agents"; then
    print_error "Failed to create ~/.claude/agents symlink"
    return 1
fi
```

## Acceptance Criteria

- [ ] Run all verification commands in Issue A on the Dell ProMax GB10 and confirm all resolve correctly; document results in this task
- [ ] Verification block in `setup_claude_integration()` updated to use `[ -L path ] && [ -e path ]` instead of `[ -L path ]` alone (Issue B)
- [ ] `ln -sf` calls wrapped in explicit error guards so failures produce a clear `print_error` message rather than a silent `set -e` exit (Issue C)
- [ ] On a re-install where symlinks already exist and are correct, the function removes and recreates them cleanly (current behaviour via `rm` then `ln -sf` — confirm this path works)
- [ ] On install where `~/.claude/commands` is an unexpected regular directory (not a symlink), the backup logic fires and the symlink is created correctly

## Test Requirements

- [ ] Manual verification on Dell ProMax GB10 (see Issue A commands above)
- [ ] Simulate dangling symlink: `ln -sf /nonexistent ~/.claude/commands-test` and confirm updated `[ -L ] && [ -e ]` detects it as failed
- [ ] Simulate `ln` failure by making `~/.claude` read-only and confirming explicit error message is shown rather than silent exit
- [ ] Confirm no regression: clean install and re-install both succeed with symlinks resolving

## Implementation Notes

This task combines a runtime verification (Issue A, must be done on the target machine) with two defensive code improvements (Issues B and C). The code changes are small and low-risk. Issue A should be verified first — if the symlinks are already broken on the target machine, that finding may add additional acceptance criteria.

## Related

- Review: `tasks/backlog/TASK-REV-LI02-linux-install-2-analysis.md` (Issue 4)
- Installer: `installer/scripts/install.sh` — `setup_claude_integration()` (~lines 1601-1647)
- Evidence: `docs/reviews/linux_install/linux_install_2.md` lines 184-190
- Companion fixes: `tasks/backlog/TASK-FIX-LI03-path-patch-on-reinstall.md`, `tasks/backlog/TASK-FIX-LI04-counter-increment-set-e-crash.md`
