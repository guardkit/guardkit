# Review Report: TASK-REV-ac2e

## Executive Summary

`install.sh`'s `backup_existing()` treats the shared `~/.claude` directory as a guardkit-owned
install surface and `mv`s it wholesale to a timestamped backup on every run, destroying Claude
Code user state (auto-memory, settings.json, transcripts, todos). The protection it provides is
already implemented — correctly and surgically — by `setup_claude_integration()`, which owns the
only two guardkit entries inside that directory. **Decision: remove `.claude` from the sweep
(Option A, 92/100), with a two-sided grep-signature regression test.** Verified live incident:
2026-07-08 23:19 re-run wiped the primary machine's Claude Code memory index mid-session;
recovered via `rsync -a --ignore-existing` from the backup only because it was noticed within
minutes. 10+ accumulated `~/.claude.backup.*` dirs date the behaviour to at least May 2026.

## Review Details

- **Mode**: Decision analysis
- **Depth**: Quick
- **Task**: TASK-REV-ac2e (ad-hoc, created via Phase 0 description form — first production use)
- **Reviewer**: software-architect agent (independent verdict) + operator forensics
- **Fleet-memory context**: unavailable (store DISABLED) — reviewed from codebase analysis only

## Findings

1. **Destructive redundancy**: `backup_existing()` (install.sh ~465-486) sweeps `.claude` into
   the same wholesale `mv` treatment as the guardkit-owned `.agentecflow`/`.agenticflow`/
   `.agentic-flow` dirs. But `setup_claude_integration()` (install.sh 1666-1710) already handles
   `~/.claude` correctly on every run: creates the dir if missing, backs up *only* a real (non-
   symlink) `commands`/`agents` subdir, removes stale symlinks, re-links, verifies targets. The
   whole-dir `mv` adds zero protective value for guardkit state.
2. **Live data loss**: 2026-07-08 23:19 run destroyed the in-use Claude Code auto-memory
   (8 files) and all settings/transcripts; three such backups were created on 2026-07-08 alone.
3. **Routine trigger**: house kickoff docs advise "simply re-run install.sh" after command-spec
   changes, so the destructive path is exercised routinely, not rarely.
4. **Secondary (dogfood)**: the installed `~/.agentecflow/bin/guardkit` shell wrapper does not
   dispatch the Python CLI's `task`/`memory` subcommands ("Unknown command: task"); the Python
   entry point `guardkit-py` does. task-review.md Phase 0 should name the working invocation.
5. **Secondary (hygiene)**: timestamped backups of the guardkit-owned dirs accumulate without
   retention (10+ since May). Disk-growth only — separate follow-up, not bundled here.

## Recommendations

1. Delete `[ -d "$HOME/.claude" ] && existing_dirs+=(".claude")` from `backup_existing()`
   (~install.sh:473). Leave the three guardkit-owned dirs in the sweep untouched.
2. Add `tests/unit/test_claude_dir_backup_safety.py` (grep-able-signature convention, per
   test_command_anchor_hygiene.py): (a) negative — `.claude` must not appear in the
   `backup_existing()` function body; (b) positive — `setup_claude_integration()` must still
   carry its symlink-aware guards, so the safe mechanism can't be silently deleted either.
3. CHANGELOG entry describing the fix and the incident class it prevents. (ADR disproportionate
   for a one-line bugfix at quick depth.)
4. Do NOT pursue selective-backup (Option B) or copy-then-merge (Option C) — superseded by A.
5. (Secondary, this session) task-review.md Phase 0: name `guardkit-py` as the fallback binary.
6. (Secondary, follow-up ticket) backup retention policy for the guardkit-owned dirs.

## Decision Matrix

| Option | Score | Effort | Risk | Recommendation |
|--------|-------|--------|------|----------------|
| A. Remove `.claude` from the sweep | 92 | S | Low | **ADOPT** — setup_claude_integration already covers guardkit's two entries |
| B. Selective backup inside backup_existing | 45 | M | Medium | Reject — duplicates existing symlink-aware logic; divergence risk |
| C. Copy-then-merge (cp -a + rsync restore) | 40 | L | Med-High | Reject — solves a problem A eliminates; heavy I/O on routine re-runs |
| D. Status quo + documented recovery | 12 | S | High | Reject — normalizes recurring data loss; depends on operator vigilance |

## Context Used

- Fleet-memory: none (store DISABLED).
- Operator memory `guardkit-install-wipes-claude-dir` (2026-07-08 incident forensics + recovery).

## Appendix

- Evidence paths: install.sh:465-486 (backup_existing), :1666-1710 (setup_claude_integration),
  :2112 (call site); `~/.claude.backup.20260708_{101507,122238,231934}` and 7+ older.
- Provenance: this review is the first production run of the ad-hoc description-form entry
  (guardkit `546a82d4`, scope `ai-transition/docs/task-review-adhoc-entry-scope-2026-07-08.md`).
