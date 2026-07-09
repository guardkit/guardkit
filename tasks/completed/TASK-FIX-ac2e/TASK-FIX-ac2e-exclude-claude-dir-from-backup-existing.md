---
id: TASK-FIX-ac2e
title: Exclude ~/.claude from install.sh backup_existing() wholesale sweep
priority: high
status: completed
task_type: feature
parent_review: TASK-REV-ac2e
implementation_mode: direct
---

# Exclude ~/.claude from install.sh backup_existing() wholesale sweep

## Objective

Implement Option A from TASK-REV-ac2e (score 92/100): stop `backup_existing()` from `mv`-ing
the shared `~/.claude` directory (Claude Code auto-memory, settings, transcripts) on every
install.sh run. `setup_claude_integration()` already handles the only two guardkit-owned
entries (`commands`/`agents` symlinks) surgically.

## Acceptance Criteria

- [x] `[ -d "$HOME/.claude" ] && existing_dirs+=(".claude")` removed from backup_existing()
- [x] The three guardkit-owned dirs (.agentecflow/.agenticflow/.agentic-flow) remain swept
- [x] Regression guard test (grep-signature style): `.claude` absent from backup_existing()
      body AND setup_claude_integration() symlink guards still present
- [x] CHANGELOG entry
- [x] Live verification: install.sh re-run leaves ~/.claude (memory files) intact, no new
      ~/.claude.backup.* created
