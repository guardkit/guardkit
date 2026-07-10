# /task-review — install-sh-backup-existing-moves-the-whole-claude-dir-should — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /task-review install-sh-backup-existing-moves-the-whole-claude-dir-should — 2026-07-09T05:38:36Z

### Prompt

```
/task-review "install.sh backup_existing moves the whole ~/.claude dir — should it exclude Claude Code state?" --mode=decision --depth=quick
```

### Assistant response

I'll execute this decision review. First, Phase 0 (ad-hoc task creation) and locating the actual code in parallel.

`guardkit task` isn't a subcommand. Let me check the CLI and read the actual code.

The concern is confirmed: `backup_existing()` does `mv "$HOME/.claude"` — it **moves the entire directory**, not a copy. Let me check `INSTALL_DIR`, the call site, and the more surgical backup logic that also exists (lines 1677–1689).
