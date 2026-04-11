---
id: TASK-FIX-CF8D
title: Prune stale ~/.agentecflow/bin/ symlinks and add prune pass to install.sh
status: completed
created: 2026-04-11T17:55:00Z
updated: 2026-04-11T18:20:00Z
completed: 2026-04-11T18:20:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-FIX-CF8D/
priority: medium
tags: [cleanup, install-script, symlinks]
task_type: implementation
parent_review: TASK-REV-C1B4
feature_id: FEAT-E1AF
wave: 2
conductor_workspace: commands-lib-cleanup-wave2-1
implementation_mode: task-work
complexity: 4
depends_on: []
---

# Task: Clean dangling `~/.agentecflow/bin/` symlinks and teach `install.sh` to prune them on re-run

## Background

Surfaced by [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md) Section 1 "Bonus finding".
[TASK-FIX-E841](../../in_review/TASK-FIX-E841-repair-or-deprecate-template-validate-cli.md) deleted
`installer/core/commands/lib/template_validate_cli.py`, but the `~/.agentecflow/bin/template-validate-cli` symlink
still exists and still points at the deleted file. Post-review probe:

```bash
$ test -e ~/.agentecflow/bin/template-validate-cli && echo OK || echo DANGLING
DANGLING
```

Root cause: `install.sh`'s `setup_python_bin_symlinks()` function (lines 1797–1910) only creates and updates
symlinks when a target exists. It **never removes symlinks whose targets have been deleted**. So every time a
`commands/lib/*.py` file gets removed, its corresponding `bin/` symlink rots silently. E841 was the first observed
symptom; TASK-FIX-7A3E, TASK-FIX-8B4F, and TASK-REF-9C5A will each create new dangling symlinks unless we fix
this now.

This task is **Wave 2** because it must run **after** the Wave 1 deletion/relocation tasks — they create the
dangling symlinks that this task's prune pass cleans up. Additionally, it touches `install.sh` and therefore
must be sequential with TASK-ISH-D09E (Wave 3) which also touches that file.

## Description

Two parts: immediate cleanup, then permanent fix.

### Part A — Immediate cleanup (post-Wave-1 state)

1. List all dangling symlinks under `~/.agentecflow/bin/` that point into `installer/core/commands/lib/`:
   ```bash
   for link in ~/.agentecflow/bin/*; do
       if [ -L "$link" ] && [ ! -e "$link" ]; then
           target=$(readlink "$link")
           if [[ "$target" == */installer/core/commands/lib/* ]]; then
               echo "DANGLING: $link -> $target"
           fi
       fi
   done
   ```
2. Confirm each listed entry matches a file deleted by Wave 1 tasks (or E841). Do NOT touch dangling symlinks whose
   targets are outside the `commands/lib/` tree — those may be user-added and out of scope.
3. Remove the confirmed-dangling entries with `rm`.

### Part B — Permanent fix in `install.sh`

Add a **prune pass** to `setup_python_bin_symlinks()` (in `installer/scripts/install.sh`, currently lines
1797–1910) that runs **before** the symlink-creation loop. Pseudocode:

```bash
prune_stale_bin_symlinks() {
    local pruned=0
    for link in "$BIN_DIR"/*; do
        [ -L "$link" ] || continue
        local target
        target=$(readlink "$link")
        # Only prune symlinks whose targets are inside commands/ or commands/lib/
        # (never touch user-added symlinks to unrelated locations)
        case "$target" in
            */installer/core/commands/*) ;;
            *) continue ;;
        esac
        # Target exists? leave alone. Target missing? prune.
        if [ ! -e "$link" ]; then
            rm "$link"
            print_info "  Pruned stale symlink: $(basename "$link") -> $target"
            pruned=$((pruned + 1))
        fi
    done
    if [ "$pruned" -gt 0 ]; then
        print_success "Pruned $pruned stale symlinks"
    fi
}
```

Call `prune_stale_bin_symlinks` at the top of `setup_python_bin_symlinks`, before the `python_scripts` array is
populated.

### Safety rules

- **Only prune symlinks whose `readlink` target contains `installer/core/commands/`**. Never touch symlinks
  pointing anywhere else — they may be user-added or come from other installers.
- **Never prune non-symlink files** in `~/.agentecflow/bin/`. The regular `guardkit` and `guardkit-init` wrappers
  are real files, not symlinks.
- **Idempotent**: running install.sh twice in a row should have no additional effect on the second run.

### Tests / verification

- Pre-task state: confirm `template-validate-cli` is dangling (it currently is).
- After Part A: `test -e ~/.agentecflow/bin/template-validate-cli` returns failure **and** `ls -la` does not show
  the link at all.
- After Part B: delete any file in `commands/lib/` (e.g., create a temporary `zzz_test_prune.py`, run the installer,
  confirm the symlink is created; delete the file; run the installer again; confirm the symlink is removed).
- Running the installer on a pristine system still works and creates no unexpected output.

## Acceptance Criteria

- [ ] All dangling symlinks under `~/.agentecflow/bin/` that point into `commands/lib/` are removed.
- [ ] `install.sh` has a `prune_stale_bin_symlinks()` function that runs before symlink creation.
- [ ] Prune pass only touches symlinks whose targets contain `installer/core/commands/`.
- [ ] Prune pass is idempotent (two consecutive install runs produce the same state on the second run).
- [ ] Manual test: deleting a file in `commands/lib/` and re-running the installer removes the corresponding
      symlink.
- [ ] Pre-existing valid symlinks (e.g., `agent-format`, `task-breakdown`) are NOT touched.

## References

- Parent review: [TASK-REV-C1B4](../../in_review/TASK-REV-C1B4-audit-commands-lib-cli-shims.md) Section 1 "Bonus finding"
- Install script section: `installer/scripts/install.sh` lines 1797–1910 (`setup_python_bin_symlinks`)
- Dangling example: `~/.agentecflow/bin/template-validate-cli` → `installer/core/commands/lib/template_validate_cli.py` (deleted by E841)
- Pairs with: TASK-ISH-D09E (Wave 3, the structural fix to the blind-walk root cause)
