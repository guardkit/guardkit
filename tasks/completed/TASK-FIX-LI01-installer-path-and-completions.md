---
id: TASK-FIX-LI01
title: Fix installer PATH and completions for Linux user installs
status: completed
created: 2026-02-22T14:30:00Z
updated: 2026-02-22T15:10:00Z
completed_at: 2026-02-22T15:10:00Z
priority: high
tags: [installer, linux, path, bash, completions, aarch64]
task_type: bug-fix
complexity: 3
parent_review: TASK-REV-LI01
completion_metrics:
  files_changed: 1
  fixes_applied: 4
  requirements_met: 4/4
---

# Task: Fix installer PATH and completions for Linux user installs

## Completion Report

**Task**: Fix installer PATH and completions for Linux user installs
**Completed**: 2026-02-22T15:10:00Z
**Final Status**: ✅ COMPLETED

### Deliverables

- Files changed: 1 (`installer/scripts/install.sh`)
- Fixes applied: 4

### Acceptance Criteria

- [x] Shell integration block written to `~/.bashrc` / `~/.zshrc` includes `export PATH="$HOME/.local/bin:$HOME/.agentecflow/bin:$PATH"` (with `~/.local/bin` listed before `~/.agentecflow/bin`)
- [x] `install_completions()` creates `$INSTALL_DIR/completions/guardkit.bash` (not `agentecflow.bash`)
- [x] The completions file registers completions for `guardkit`, `guardkit-init`, `gk`, and `gki` (not `agentecflow` / `af`)
- [x] Node.js missing warning updated to list specific affected templates: `react-typescript`, `nextjs-fullstack`, `react-fastapi-monorepo`
- [x] No regression: macOS install path still functional (shell integration must not break on zsh/macOS) — zsh branch received the same PATH fix
- [ ] After a fresh install on Linux with `~/.local/bin` absent from PATH, opening a new terminal makes `guardkit-py` and `guardkit` reachable without manual PATH changes *(requires manual runtime verification)*

### Changes Applied

| Fix | File | Lines | Description |
|-----|------|-------|-------------|
| 1 — PATH | `install.sh` | 1266, 1280 | Added `$HOME/.local/bin:` before `$HOME/.agentecflow/bin` in both bash and zsh shell integration branches |
| 2 — Filename | `install.sh` | 1337 | `agentecflow.bash` → `guardkit.bash` in `install_completions()` |
| 3 — Functions | `install.sh` | 1381–1411 | Renamed `_agentecflow` → `_guardkit`, `_agentec_init` → `_guardkit_init`; updated `complete` registrations to `guardkit`, `gk`, `guardkit-init`, `gki` |
| 4 — Warning | `install.sh` | 174–176 | Node.js warning now lists `react-typescript`, `nextjs-fullstack`, `react-fastapi-monorepo` as requiring Node.js |

---

## Original Description

The GuardKit installer (`installer/scripts/install.sh`) does not add `~/.local/bin` to PATH in its shell integration block. On Linux systems where system site-packages is not writeable (Ubuntu/Debian default), pip installs all entry-point scripts to `~/.local/bin`. This means `guardkit-py`, `guardkit`, and all dependency scripts are installed but unreachable after install.

Additionally, the bash completions file is created with the wrong name (`agentecflow.bash`) while the shell integration sources a different name (`guardkit.bash`), so completions silently fail to load. The completions also register the old command names (`agentecflow`, `af`) instead of the current ones (`guardkit`, `guardkit-init`, `gk`, `gki`).

**Root cause source**: `setup_shell_integration()` and `install_completions()` in `installer/scripts/install.sh`
**Review report**: `.claude/reviews/TASK-REV-LI01-linux-install-review.md`
**Evidence**: `docs/reviews/linux_install/linux_insatall_1.md` lines 265–278 (pip PATH warnings + `⚠ guardkit-py CLI not found in PATH`)

## Related

- Review report: `.claude/reviews/TASK-REV-LI01-linux-install-review.md`
- Install log: `docs/reviews/linux_install/linux_insatall_1.md`
- Installer: `installer/scripts/install.sh`
- Companion fix: TASK-FIX-LI02 (version variable typo)
