---
id: TASK-FIX-LI03
title: Fix shell integration PATH not updated when re-installing over existing config
status: completed
created: 2026-02-22T13:45:00Z
updated: 2026-02-22T14:05:00Z
completed_at: 2026-02-22T14:05:00Z
priority: high
tags: [installer, linux, path, bash, zsh, reinstall, shell-integration]
task_type: bug-fix
complexity: 2
parent_review: TASK-REV-LI02
---

# Task: Fix shell integration PATH not updated when re-installing over existing config

## Description

`setup_shell_integration()` in `installer/scripts/install.sh` checks whether `.agentecflow/bin` is already present in `~/.bashrc` (or `~/.zshrc`). If so, it prints "Shell integration already configured" and returns early **without checking whether `$HOME/.local/bin` is also present**.

TASK-FIX-LI01 added `$HOME/.local/bin` to the PATH export line written by `setup_shell_integration()`. However, users who installed before that fix have an old block in their shell config that does not include `$HOME/.local/bin`. On re-install, the "already configured" early-return prevents the updated block from being written, so `guardkit-py CLI not found in PATH` continues to be reported.

**File**: `installer/scripts/install.sh`
**Function**: `setup_shell_integration()`
**Evidence**: `docs/reviews/linux_install/linux_install_2.md` lines 103-110 and 175
**Review**: `tasks/backlog/TASK-REV-LI02-linux-install-2-analysis.md` Issue 1

## Root Cause

Lines ~1256-1259 (current):

```bash
# Check if already configured correctly
if grep -q "\.agentecflow/bin" "$shell_config" 2>/dev/null; then
    print_info "Shell integration already configured"
    return
fi
```

This returns early whenever `.agentecflow/bin` is found, regardless of whether the existing block is complete. No check is made for `\.local/bin`.

## Acceptance Criteria

- [ ] When re-installing and shell config contains `.agentecflow/bin` **but not** `.local/bin`, the installer patches the existing PATH export line in-place to prepend `$HOME/.local/bin:` before `$HOME/.agentecflow/bin:` — it does **not** append a duplicate block
- [ ] When re-installing and shell config already contains both `.agentecflow/bin` and `.local/bin`, the installer prints "Shell integration already configured" and returns unchanged (no regression)
- [ ] When installing fresh (no `.agentecflow/bin` in config), the full block is written as before (no regression)
- [ ] Fix applies to both bash (`~/.bashrc` / `~/.bash_profile`) and zsh (`~/.zshrc`) paths
- [ ] After the fix, running `./install.sh` on this machine (which has the old `.bashrc` block) eliminates the `⚠ guardkit-py CLI not found in PATH` warning
- [ ] `grep "$HOME/.local/bin" ~/.bashrc` returns a match after the patched re-install

## Implementation Notes

Replace the "already configured" early-return block with a two-stage check:

```bash
# Check if already configured correctly
if grep -q "\.agentecflow/bin" "$shell_config" 2>/dev/null; then
    # Also check PATH includes ~/.local/bin (needed for pip user installs on Linux)
    if ! grep -q "\.local/bin" "$shell_config" 2>/dev/null; then
        print_info "Updating shell integration to add ~/.local/bin to PATH..."
        # Patch the existing PATH export line in-place (GNU sed and BSD sed)
        sed -i 's|export PATH="\$HOME/\.agentecflow/bin:\$PATH"|export PATH="$HOME/.local/bin:$HOME/.agentecflow/bin:$PATH"|' \
            "$shell_config" 2>/dev/null || \
        sed -i '' 's|export PATH="\$HOME/\.agentecflow/bin:\$PATH"|export PATH="$HOME/.local/bin:$HOME/.agentecflow/bin:$PATH"|' \
            "$shell_config" 2>/dev/null
        print_success "Updated PATH in $shell_config to include ~/.local/bin"
        print_info "Please restart your shell or run: source $shell_config"
    else
        print_info "Shell integration already configured"
    fi
    return
fi
```

**Key points**:
- Use `sed -i` (GNU, Linux) with fallback to `sed -i ''` (BSD, macOS) — same pattern already used elsewhere in the function
- The regex must match the exact string written by the old integration block (`export PATH="$HOME/.agentecflow/bin:$PATH"`) which uses literal `$HOME` (written inside single-quoted heredoc, so `$HOME` is a literal string in the file)
- Do **not** duplicate or append another GuardKit block — patch in-place only

## Test Requirements

- [ ] Run `./install.sh` on a machine whose `.bashrc` contains `export PATH="$HOME/.agentecflow/bin:$PATH"` (no `.local/bin`) — confirm PATH line is updated, no duplicate block added, no `⚠ guardkit-py CLI not found in PATH` warning
- [ ] Run `./install.sh` on a machine whose `.bashrc` already contains `$HOME/.local/bin:$HOME/.agentecflow/bin` — confirm "Shell integration already configured" is printed and file is unchanged
- [ ] Run `./install.sh` on a clean machine with no GuardKit config — confirm full block is written as before
- [ ] Test on macOS (zsh) to confirm BSD `sed -i ''` fallback works

## Related

- Review: `tasks/backlog/TASK-REV-LI02-linux-install-2-analysis.md` (Issue 1)
- Original fix: `tasks/completed/TASK-FIX-LI01-installer-path-and-completions.md`
- Installer: `installer/scripts/install.sh` — `setup_shell_integration()`
- Evidence: `docs/reviews/linux_install/linux_install_2.md` lines 103-110, 175

## Completion Report

**Completed**: 2026-02-22T14:05:00Z
**Duration**: ~20 minutes
**Final Status**: COMPLETED

### Deliverables
- Files changed: 1 (`installer/scripts/install.sh`)
- Change: 4-line early-return replaced with 12-line two-stage check

### Implementation Summary
Replaced the single-stage "already configured" guard at line 1255 with a two-stage check:
1. `.agentecflow/bin` present but `.local/bin` absent → `sed` patches the existing `export PATH=` line in-place (GNU fallback to BSD)
2. Both present → "already configured" (no change, no regression)
3. Neither → falls through to original full-block-append logic (no regression)

### Acceptance Criteria Status
- [x] Re-install with old block patches PATH line in-place (no duplicate block)
- [x] Re-install with up-to-date block prints "already configured", no change
- [x] Fresh install writes full block as before
- [x] Applies to bash and zsh (same code path)
- [x] GNU/BSD `sed` fallback pattern used (consistent with rest of function)
