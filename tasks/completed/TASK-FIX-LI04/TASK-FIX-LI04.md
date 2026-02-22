---
id: TASK-FIX-LI04
title: Fix bash set -e crash caused by ((counter++)) returning 0 in setup_python_bin_symlinks
status: completed
created: 2026-02-22T13:45:00Z
updated: 2026-02-22T14:05:00Z
completed: 2026-02-22T14:05:00Z
completed_location: tasks/completed/TASK-FIX-LI04/
priority: high
tags: [installer, linux, bash, set-e, arithmetic, symlinks, post-install-summary]
task_type: bug-fix
complexity: 2
parent_review: TASK-REV-LI02
---

# Task: Fix bash set -e crash caused by ((counter++)) returning 0 in setup_python_bin_symlinks

## Description

`setup_python_bin_symlinks()` in `installer/scripts/install.sh` uses the `((counter++))` pattern to increment four counters (`symlinks_created`, `symlinks_updated`, `symlinks_skipped`, `errors`). In bash, `((expr))` is an arithmetic command whose exit status is `1` when the expression evaluates to `0`. When a counter starts at `0` and is incremented with `((counter++))`, the expression returns the **pre-increment value** (i.e., `0`), causing bash to exit immediately when `set -e` is active.

This is the root cause of two observed symptoms from install 2:

1. **Issue 2**: The function exits silently mid-loop, so neither the per-symlink `print_info` lines nor the final summary (`✓ Python command symlinks configured successfully`) are printed
2. **Issue 3**: Because the function exits via `set -e`, `main()` also exits before reaching `print_summary()` — so the entire post-install "Next Steps" banner is never shown

**File**: `installer/scripts/install.sh`
**Function**: `setup_python_bin_symlinks()` (~lines 1649-1777)
**Evidence**: `docs/reviews/linux_install/linux_install_2.md` lines 192-194 (script terminates after "Found 93 Python command script(s)")
**Review**: `tasks/backlog/TASK-REV-LI02-linux-install-2-analysis.md` Issues 2 & 3

## Root Cause

In `setup_python_bin_symlinks()`, four counter variables are incremented using `((counter++))`:

| Counter | Location | Trigger |
|---------|----------|---------|
| `((symlinks_skipped++))` | `__init__.py` skip | First file skipped (from 0) |
| `((symlinks_skipped++))` | `test_*` skip | First test file skipped (from 0) |
| `((symlinks_skipped++))` | Already-correct symlink | First up-to-date symlink (from 0) — most common on re-install |
| `((symlinks_created++))` | New symlink created | First new symlink (from 0) — most common on fresh install |
| `((symlinks_updated++))` | Symlink retargeted | First updated symlink (from 0) |
| `((errors++))` | Conflict or unreadable | First error (from 0) |

On a re-install where all 93 symlinks already exist and are correct, the very first iteration hits the "already correct" path and executes `((symlinks_skipped++))` with `symlinks_skipped=0`. The expression evaluates to `0` → exit status `1` → `set -e` terminates the script.

This explains why the log shows exactly `ℹ Found 93 Python command script(s)` and then nothing further — the crash occurs at the very first iteration of the loop.

## Acceptance Criteria

- [ ] All four counter increments in `setup_python_bin_symlinks()` replaced with `set -e`-safe equivalents
- [ ] On re-install (all symlinks already exist and correct), the function completes and prints: `✓ Python command symlinks configured successfully` with Created/Updated/Skipped/Location breakdown
- [ ] On fresh install (symlinks being created), the function completes and prints the same success summary
- [ ] After the function returns normally, `print_summary()` in `main()` is reached and the full post-install banner (with "Next Steps") is printed
- [ ] No regression: symlink creation, update, and conflict-detection logic is unchanged

## Implementation Notes

Replace all four `((counter++))` occurrences with `counter=$((counter + 1))`, which is always safe under `set -e` because the RHS `$((expr))` is a parameter expansion, not a command — its exit code is always `0`.

**Find**: `((symlinks_created++))` → **Replace**: `symlinks_created=$((symlinks_created + 1))`
**Find**: `((symlinks_updated++))` → **Replace**: `symlinks_updated=$((symlinks_updated + 1))`
**Find**: `((symlinks_skipped++))` → **Replace**: `symlinks_skipped=$((symlinks_skipped + 1))`
**Find**: `((errors++))` → **Replace**: `errors=$((errors + 1))`

There are multiple occurrences of `((symlinks_skipped++))` and `((errors++))` — all must be replaced.

Alternative (also acceptable): append `|| true` to each arithmetic command, e.g. `((symlinks_skipped++)) || true`. However, `counter=$((counter + 1))` is clearer and more idiomatic for simple counters.

**Do not** use `let "counter++"` — `let` has the same `set -e` behaviour as `((...))`.

## Verification

After the fix, a re-install should produce output similar to:

```
ℹ Setting up Python command script symlinks...
ℹ Found 93 Python command script(s)

✓ Python command symlinks configured successfully
ℹ   Created: 0
ℹ   Updated: 0
ℹ   Skipped: 93
ℹ   Location: /home/richardwoollcott/.agentecflow/bin
ℹ Commands can now be executed from any directory

════════════════════════════════════════════════════════
✅ GuardKit installation complete!
════════════════════════════════════════════════════════
...
⚠ Next Steps:
  1. Restart your shell or run: source ~/.bashrc
  ...
```

## Test Requirements

- [ ] Run `./install.sh` on a machine with all 93 symlinks already correct — confirm full summary and post-install banner print
- [ ] Run `./install.sh` on a clean machine — confirm fresh-install symlinks are created and summary prints
- [ ] `grep -n 'AGENTICFLOW_VERSION\|((symlinks\|((errors' installer/scripts/install.sh` returns zero matches (confirms all occurrences replaced)
- [ ] No regression on macOS

## Related

- Review: `tasks/backlog/TASK-REV-LI02-linux-install-2-analysis.md` (Issues 2 and 3)
- Companion fix: `tasks/backlog/TASK-FIX-LI03-path-patch-on-reinstall.md`
- Prior `set -e` fix: `tasks/completed/TASK-FIX-LI02-version-variable-typo.md` (same class of bug)
- Installer: `installer/scripts/install.sh` — `setup_python_bin_symlinks()` (~lines 1649-1777)
- Evidence: `docs/reviews/linux_install/linux_install_2.md` lines 192-194
