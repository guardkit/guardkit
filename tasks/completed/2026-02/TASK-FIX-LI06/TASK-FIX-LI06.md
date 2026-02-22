---
id: TASK-FIX-LI06
title: Fix false-alarm guardkit-py CLI not found warning shown before PATH is updated
status: completed
created: 2026-02-22T14:20:00Z
updated: 2026-02-22T14:20:00Z
completed: 2026-02-22T14:30:00Z
priority: high
tags: [installer, linux, path, ux, cli-check, sequencing]
task_type: bug-fix
complexity: 2
parent_review: TASK-REV-LI03
---

# Task: Fix false-alarm guardkit-py CLI not found warning shown before PATH is updated

## Description

`install_python_package()` checks whether the `guardkit-py` CLI is reachable in the current PATH and emits `⚠ guardkit-py CLI not found in PATH` when it is not. This check runs at **step 5** of `main()`. However, `setup_shell_integration()` — which patches `~/.bashrc` to add `~/.local/bin` — runs at **step 11**. The warning therefore always fires on any re-install where `~/.local/bin` is not already in the active session's PATH, even though the installer is about to fix it.

In install 3 (the most recent run), the output shows:

```
⚠ guardkit-py CLI not found in PATH                   ← line 109 (step 5)
ℹ You may need to restart your shell or add ~/.local/bin to PATH

...66 lines of other output...

ℹ Updating shell integration to add ~/.local/bin to PATH...   ← line 175 (step 11)
✓ Updated PATH in /home/richardwoollcott/.bashrc to include ~/.local/bin
ℹ Please restart your shell or run: source /home/richardwoollcott/.bashrc
```

The warning is factually correct (the CLI is not in the current session's PATH) but misleading — it implies a problem that the same install run resolves 66 lines later. Users who notice only the warning may believe the install failed.

**File**: `installer/scripts/install.sh`
**Function**: `install_python_package()` (~lines 480-494) and `main()` (~lines 1860-1892)
**Evidence**: `docs/reviews/linux_install/linux_install_3.md` lines 103-110 vs 175-177
**Review**: `tasks/backlog/TASK-REV-LI03-linux-install-3-analysis.md` Issue 1

## Root Cause

`main()` step ordering (relevant lines):

```bash
install_python_package    # step 5 — CLI check fires here (line 1871)
backup_existing           # step 6
create_directories        # step 7
install_global_files      # step 8
install_global_agents     # step 9
create_cli_commands       # step 10
setup_shell_integration   # step 11 — PATH is patched here (line 1877)
```

The CLI check in `install_python_package()` (~lines 480-494):

```bash
if command -v guardkit-py &> /dev/null; then
    print_success "guardkit-py CLI command is available"
else
    set +e
    local cli_path=$(python3 -c "import shutil; p=shutil.which('guardkit-py'); print(p if p else '')" 2>/dev/null)
    set -e
    if [ -n "$cli_path" ]; then
        print_success "guardkit-py CLI found at: $cli_path"
    else
        print_warning "guardkit-py CLI not found in PATH"
        print_info "You may need to restart your shell or add ~/.local/bin to PATH"
    fi
fi
```

## Acceptance Criteria

- [ ] On a re-install where `~/.local/bin` is not in the active session's PATH, the installer does **not** emit `⚠ guardkit-py CLI not found in PATH` as a standalone mid-install warning
- [ ] The user is still clearly told they need to restart their shell once — at the right time (after the PATH fix is applied), not before
- [ ] On a fresh install where shell integration is being written for the first time, the same behaviour applies
- [ ] On a system where `~/.local/bin` IS already in PATH (e.g. after a shell restart), `✓ guardkit-py CLI command is available` is printed as before (no regression)

## Implementation Notes

**Preferred approach — defer and consolidate the check:**

Remove the warning from `install_python_package()` entirely and add a single, definitive CLI check at the end of `main()`, just before `print_summary()`. At that point `setup_shell_integration()` has already run, so the message can be contextually accurate:

```bash
# In main(), after setup_shell_integration() and all other steps:
verify_cli_reachability   # new function called at step ~19
print_summary
```

The new `verify_cli_reachability()` function:

```bash
verify_cli_reachability() {
    if command -v guardkit-py &> /dev/null; then
        print_success "guardkit-py CLI is available in PATH"
    elif [ -f "$HOME/.local/bin/guardkit-py" ]; then
        # Binary exists but session PATH hasn't been updated yet
        print_info "guardkit-py installed to ~/.local/bin — restart your shell or run: source ~/.bashrc"
    else
        print_warning "guardkit-py CLI not found — check your PATH includes ~/.local/bin and ~/.agentecflow/bin"
    fi
}
```

**Alternative approach — update the message in place:**

If moving the check is too disruptive, update the `else` branch in `install_python_package()` to check whether the binary exists at `~/.local/bin/guardkit-py`:

```bash
else
    if [ -f "$HOME/.local/bin/guardkit-py" ]; then
        print_info "guardkit-py installed to ~/.local/bin — PATH will be updated by shell integration step"
    else
        print_warning "guardkit-py CLI not found in PATH"
        print_info "You may need to restart your shell or add ~/.local/bin to PATH"
    fi
fi
```

The preferred approach (deferred check) is cleaner. The alternative is a minimal change if the preferred is out of scope.

## Test Requirements

- [ ] Run `./install.sh` in a shell where `~/.local/bin` is NOT in PATH — confirm no `⚠` warning mid-install; confirm a single clear `ℹ` message about restarting shell appears at or near the end
- [ ] Run `./install.sh` in a shell where `~/.local/bin` IS in PATH (after previous install + shell restart) — confirm `✓ guardkit-py CLI is available in PATH` is printed
- [ ] No regression on the PATH patching itself (TASK-FIX-LI03 must still work)

## Related

- Review: `tasks/backlog/TASK-REV-LI03-linux-install-3-analysis.md` Issue 1
- Evidence: `docs/reviews/linux_install/linux_install_3.md` lines 103-110, 175-177
- Installer: `installer/scripts/install.sh` — `install_python_package()` (~lines 480-494), `main()` (~lines 1860-1892)
- PATH fix that this warning now contradicts: `tasks/completed/2026-02/TASK-FIX-LI03-path-patch-on-reinstall.md`
