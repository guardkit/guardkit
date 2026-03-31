---
id: TASK-REV-LI03
title: Analyse third Linux installation of GuardKit on Dell ProMax GB10 (aarch64)
status: backlog
created: 2026-02-22T14:15:00Z
updated: 2026-02-22T14:15:00Z
priority: high
tags: [review, linux, installation, arm64, aarch64, path, installer, dell-promax]
task_type: review
complexity: 3
decision_required: false
hardware: Dell ProMax GB10 (aarch64/ARM64)
install_log: docs/reviews/linux_install/linux_install_3.md
parent_review: TASK-REV-LI02
related_fixes: [TASK-FIX-LI03, TASK-FIX-LI04, TASK-FIX-LI05]
---

# Task: Analyse third Linux installation of GuardKit on Dell ProMax GB10 (aarch64)

## Description

Review the output of the third GuardKit installation on Linux (Dell ProMax GB10, aarch64), run after implementing [TASK-FIX-LI03](../../completed/2026-02/TASK-FIX-LI03-path-patch-on-reinstall.md), [TASK-FIX-LI04](../../completed/TASK-FIX-LI04/TASK-FIX-LI04.md), and [TASK-FIX-LI05](../../completed/2026-02/TASK-FIX-LI05/TASK-FIX-LI05.md).

**Installation log**: `docs/reviews/linux_install/linux_install_3.md`
**Target machine**: Dell ProMax GB10, `aarch64` architecture, Ubuntu (bash shell)
**Installer**: `installer/scripts/install.sh`
**Installed to**: `/home/richardwoollcott/.agentecflow`
**Context**: Re-install over an existing installation

This is a substantially successful install — all three LI02 fixes are confirmed working and the post-install summary now prints for the first time. Three minor issues remain.

---

## Fixes Verified From LI02

| Fix | Expected | Observed | Status |
|-----|----------|----------|--------|
| TASK-FIX-LI03: PATH patched on re-install | `✓ Updated PATH in ~/.bashrc to include ~/.local/bin` | Lines 175-176: exact message confirmed | ✅ FIXED |
| TASK-FIX-LI04: Symlink counter crash | Per-symlink `Created:` lines + full success summary | Lines 196-278: 76 symlinks listed individually, summary with Created/Updated/Skipped/Location | ✅ FIXED |
| TASK-FIX-LI04: Post-install summary | Full "Next Steps" banner printed | Lines 289-337: complete summary with all sections | ✅ FIXED |
| TASK-FIX-LI05: Claude Code integration verified | `✓ Commands/Agents available in Claude Code (via symlink)` | Lines 319-322 in post-install summary confirm both symlinks resolve | ✅ VERIFIED |

**New in install 3** (not present in earlier installs):
- Lines 279-284: Package detection marker file created (`~/.agentecflow/guardkit.marker.json`)
- Lines 285-287: Installation validation step (`✅ Python imports validated successfully`)
- Lines 289-337: Complete post-install summary with templates, commands, Claude Code status, AutoBuild status, and Next Steps

---

## Issues Found

### Issue 1 — UX: `⚠ guardkit-py CLI not found in PATH` fires before shell integration is patched

**Symptom** (lines 103-110):

```
WARNING: The script guardkit-py is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
...
⚠ guardkit-py CLI not found in PATH
ℹ You may need to restart your shell or add ~/.local/bin to PATH
```

Immediately followed at lines 175-177 by:

```
ℹ Updating shell integration to add ~/.local/bin to PATH...
✓ Updated PATH in /home/richardwoollcott/.bashrc to include ~/.local/bin
ℹ Please restart your shell or run: source /home/richardwoollcott/.bashrc
```

**Root cause**: The CLI reachability check (which emits the `⚠` warning) runs immediately after `pip install`, which is step 3 of `main()`. The `setup_shell_integration()` call — which patches `~/.bashrc` — runs later in step N. The `.bashrc` patch is correct and will take effect after the user restarts their shell. However, the `⚠ guardkit-py CLI not found in PATH` warning creates the false impression that the install has failed, when in fact the fix has been applied and requires only a shell restart.

**Impact**: UX confusion — the user sees a warning immediately before the installer reports it is being fixed. The install is functionally successful.

**Fix options**:
1. Move the CLI check to after `setup_shell_integration()` so it can confirm the fix was applied (preferred)
2. Change the `⚠` message to `ℹ guardkit-py will be available after restarting your shell (PATH is being updated)` when the installer detects that `~/.local/bin` exists but is not yet in PATH
3. Suppress the check on re-installs where shell integration will handle it

---

### Issue 2 — UX: Agent count in post-install summary undercounts stack-specific agents

**Symptom** (line 299):

```
🤖 AI Agents: 30 (including clarification-questioner)
```

But the install step at line 138 reports:

```
✓ Installed 62 total agents (30 global + 32 stack-specific)
```

**Root cause**: `print_summary()` counts agents with:

```bash
local agent_count=$(ls -1 "$INSTALL_DIR/agents/"*.md 2>/dev/null | wc -l)
```

This glob only matches `.md` files directly in `~/.agentecflow/agents/`. Stack-specific agents are installed into subdirectories (e.g., `~/.agentecflow/agents/react-typescript/`, `~/.agentecflow/agents/fastapi-python/`) and are not matched by `*.md` at depth 1. The 32 stack-specific agents are silently excluded from the count.

**Impact**: Misleading — users see `30 agents` but 62 were installed. Could cause confusion if a user tries to verify the install by checking this count.

**Fix**: Use `find` instead of `ls` glob:

```bash
local agent_count=$(find "$INSTALL_DIR/agents/" -name "*.md" 2>/dev/null | wc -l)
```

---

### Issue 3 — UX: Two new templates missing descriptions in post-install summary

**Symptom** (lines 313-314):

```
• fastmcp-python
• mcp-typescript
```

All other templates have a description (e.g., `• fastapi-python - FastAPI backend with layered architecture (9+/10)`). These two fall through the `case` statement in `print_summary()` to the bare `echo "  • $name"` branch.

**Root cause**: `fastmcp-python` and `mcp-typescript` were added as templates after the `print_summary()` case statement was written. The case statement in `install.sh` has entries for `default`, `react-typescript`, `fastapi-python`, `nextjs-fullstack`, `react-fastapi-monorepo` — but not `fastmcp-python` or `mcp-typescript`.

**Impact**: Minor — templates are listed but without descriptions. Users cannot determine their purpose from the summary alone.

**Fix**: Add case entries for the two new templates:

```bash
fastmcp-python)
    echo "  • $name - FastMCP Python server template"
    ;;
mcp-typescript)
    echo "  • $name - MCP TypeScript server template"
    ;;
```

(Descriptions to be confirmed against the template manifests.)

---

### Informational: `⚠ ANTHROPIC_API_KEY not set` (expected, by design)

**Symptom** (lines 325-327):

```
⚠ ANTHROPIC_API_KEY not set
    AutoBuild requires API credentials or Claude Code authentication
    Run 'guardkit doctor' to check configuration
```

**Status**: By design. This machine does not have `ANTHROPIC_API_KEY` set in the environment. GuardKit can still operate via Claude Code authentication. No action needed on the installer.

---

### Informational: pip PATH warnings remain (from pip itself)

**Symptom** (lines 103-104):

```
WARNING: The script guardkit-py is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.
Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
```

**Status**: This warning comes from pip itself and cannot be suppressed by the installer's shell integration fix. The installer can add `--no-warn-script-location` to the `pip install` invocation to suppress it. Low priority.

---

## Review Scope

### Files to Analyse

1. `installer/scripts/install.sh` — `main()` step ordering (Issue 1), `print_summary()` agent count and template descriptions (Issues 2 & 3)

### Key Questions to Answer

1. **Issue 1 sequencing**: At what step in `main()` is the CLI reachability check called vs. `setup_shell_integration()`? Can the check be moved or made conditional?
2. **Issue 2 agent count**: Confirm `find` vs `ls` glob fix. Are any `.md` files in the agents directory that should NOT be counted?
3. **Issue 3 template descriptions**: What are the canonical descriptions for `fastmcp-python` and `mcp-typescript`? Check their `manifest.json` or `README.md` in `installer/core/templates/`.

## Acceptance Criteria

- [ ] Root cause of Issue 1 confirmed in `main()` step ordering; fix proposed (move check or change message)
- [ ] Issue 2 agent count fix (`find` vs `ls` glob) confirmed and proposed
- [ ] Issue 3 template descriptions sourced from template manifests and proposed
- [ ] All issues triaged as `bug-fix-required`, `documentation-only`, `by-design`, or `deferred`
- [ ] Follow-up `TASK-FIX-LI06+` tasks created for each `bug-fix-required` finding
- [ ] Review report written to `.claude/reviews/TASK-REV-LI03-linux-install-review.md`

## Test Requirements

After fixes:
- [ ] Install on a machine with `~/.local/bin` not in PATH — confirm no `⚠ guardkit-py CLI not found in PATH` warning, or warning is clearly contextualised (Issue 1)
- [ ] Post-install summary shows `62` (or correct total) agents (Issue 2)
- [ ] Post-install summary shows descriptions for `fastmcp-python` and `mcp-typescript` (Issue 3)
- [ ] No regression on previous fix areas: PATH update still works, symlink summary still prints, post-install summary still shows

## Implementation Notes

This review is largely a **polish pass** — the three LI02 bugs are confirmed fixed and the installer is functionally sound for the first time. The remaining issues are all UX/display concerns in `print_summary()` and the CLI check ordering in `main()`. No new architectural issues have been introduced.

Complexity: 3 (lower than LI01/LI02 reviews — issues are smaller in scope).

## Related

- Install log (this review): `docs/reviews/linux_install/linux_install_3.md`
- Install log (install 2): `docs/reviews/linux_install/linux_install_2.md`
- Install log (install 1): `docs/reviews/linux_install/linux_insatall_1.md`
- Previous review: `tasks/backlog/TASK-REV-LI02-linux-install-2-analysis.md`
- Fixes from LI02: `tasks/completed/2026-02/TASK-FIX-LI03-path-patch-on-reinstall.md`, `tasks/completed/TASK-FIX-LI04/TASK-FIX-LI04.md`, `tasks/completed/2026-02/TASK-FIX-LI05/TASK-FIX-LI05.md`
- Installer: `installer/scripts/install.sh`
