# Review Report: TASK-REV-LI04

**Task**: Analyse fourth Linux installation of GuardKit on Dell ProMax GB10 (aarch64)
**Mode**: Code quality / installer analysis
**Depth**: Standard
**Reviewed**: 2026-02-22
**Install log**: `docs/reviews/linux_install/linux_install_4.md`
**Install timestamp**: `20260222_143237` (14:32 UTC)

---

## Executive Summary

Install 4 is functionally clean. TASK-FIX-LI07's change (ls → find in `print_summary()`) is confirmed present in the current codebase; the discrepancy seen in install 4 is explained entirely by timing — the fix was committed at 15:05, 33 minutes after the install ran.

However, the fix as specified is semantically incomplete: changing `ls -1 "$INSTALL_DIR/agents/"*.md` to `find "$INSTALL_DIR/agents/" -name "*.md"` within a flat directory yields the same count (30). Stack agents live in `$INSTALL_DIR/stack-agents/`, which `print_summary()` does not include. A post-fix install would still print `AI Agents: 30`, not 62.

Issue 2 (pip WARNING) was not addressed in any previous task. Both pip install calls in `install_python_package()` lack `--no-warn-script-location`.

Two small fix tasks are raised: TASK-FIX-LI08 (correct the agent count) and TASK-FIX-LI09 (suppress pip warning).

---

## Issue Triage

### Issue 1 — Agent count in `print_summary()` → NEEDS FURTHER FIX

| Attribute | Value |
|-----------|-------|
| Expected (per acceptance criteria) | `AI Agents: 62` |
| Observed (install 4, line 296) | `AI Agents: 30` |
| TASK-FIX-LI07 ls→find fix | **APPLIED** (line 1527) |
| Fix effective? | **NO** — semantically a no-op for flat structure |

**Analysis:**

`print_summary()` at line 1527 now reads:
```bash
local agent_count=$(find "$INSTALL_DIR/agents/" -name "*.md" 2>/dev/null | wc -l)
```

The `ls -1 "$INSTALL_DIR/agents/"*.md` → `find` change is present. Install 4 was captured 33 minutes before the fix was committed, confirming the timing explanation in the task description.

**However**, global agents are installed flat into `$INSTALL_DIR/agents/` (all 30 .md files directly at the top level — confirmed by install log lines 137–167 which list them without any subdirectory structure). Stack agents are installed into `$INSTALL_DIR/stack-agents/<template>/` (a sibling directory, not a subdirectory of `agents/`).

Because of this structure:
- `ls -1 "$INSTALL_DIR/agents/"*.md` = 30
- `find "$INSTALL_DIR/agents/" -name "*.md"` = 30 (identical — no subdirectories to recurse into)

The fix was correctly applied per its specification, but the specification was incomplete. To show 62, `print_summary()` must count both `agents/` (30) and `stack-agents/` (32) — mirroring exactly what `install_global_agents()` does at lines 689–691:
```bash
local global_agent_count=$(ls -1 "$INSTALL_DIR/agents/"*.md 2>/dev/null | wc -l)
local stack_agent_count=$(find "$INSTALL_DIR/stack-agents" -name "*.md" 2>/dev/null | wc -l)
local total_agents=$((global_agent_count + stack_agent_count))
```

**Required fix**: Update `print_summary()` line 1527 to:
```bash
local global_agent_count=$(find "$INSTALL_DIR/agents/" -name "*.md" 2>/dev/null | wc -l)
local stack_agent_count=$(find "$INSTALL_DIR/stack-agents/" -name "*.md" 2>/dev/null | wc -l)
local agent_count=$((global_agent_count + stack_agent_count))
```

**Verdict**: `bug-fix-required` → **TASK-FIX-LI08**

---

### Issue 2 — pip `WARNING:` on install → BUG-FIX-REQUIRED

| Attribute | Value |
|-----------|-------|
| Symptom (install 4, lines 103–104) | `WARNING: The script guardkit-py is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.` |
| Previous fix task | None |
| Current state in `install.sh` | Both pip calls at lines 428 and 436 lack `--no-warn-script-location` |

**Analysis:**

`install_python_package()` contains two `pip install` invocations:

```bash
# Line 428 — primary (--break-system-packages)
python3 -m pip install -e "$repo_root[autobuild]" --break-system-packages 2>&1

# Line 436 — fallback (--user)
python3 -m pip install -e "$repo_root[autobuild]" --user 2>&1
```

Neither carries `--no-warn-script-location`. pip emits the `WARNING:` when the script entry point (`guardkit-py`) is installed into a directory not currently in `$PATH`. On this machine, `~/.local/bin` exists and `guardkit-py` is installed there, but it is not in `$PATH` at install time (the installer defers PATH configuration to shell restart). pip cannot know that the installer is handling PATH separately — hence the warning.

The installer correctly suppresses its own PATH-related messages (TASK-FIX-LI06), but cannot suppress pip's stderr without passing `--no-warn-script-location`. This is now the only `WARNING:` level output remaining in the install.

**Required fix**: Add `--no-warn-script-location` to both pip invocations.

**Verdict**: `bug-fix-required` → **TASK-FIX-LI09**

---

## Secondary Findings (Out of Scope — No Task Required)

### `ls -1` in `install_global_agents()` (line 689)

```bash
local global_agent_count=$(ls -1 "$INSTALL_DIR/agents/"*.md 2>/dev/null | wc -l)
```

This is the install-time counter for the "Installed 62 total agents" message. Since global agents are installed flat in `agents/`, `ls -1 *.md` and `find -name "*.md"` are equivalent here. No functional problem. No action required.

### `ls -1` in `guardkit doctor` health check (line 1036)

```bash
agent_count=$(ls -1 "$AGENTECFLOW_HOME/agents/"*.md 2>/dev/null | wc -l)
```

This is in the `doctor` subcommand health check. Shows 30 (global agents only). Stack agents are not shown. This is lower priority than the install summary and is consistent with only checking the Claude Code-accessible agents path. Out of scope for this review.

---

## Fixes Verified from LI03

| Fix | Expected | Result |
|-----|----------|--------|
| TASK-FIX-LI06: PATH warning removed from mid-install | `ℹ` deferred to just before summary | Line 284: `ℹ guardkit-py installed to ~/.local/bin` ✅ |
| TASK-FIX-LI07 Issue B: Template descriptions | `fastmcp-python`, `mcp-typescript` show descriptions | Lines 310–311: both have descriptions ✅ |
| TASK-FIX-LI07 Issue A: Agent count via `find` | Summary shows 62 | Shows 30 (fix applied but insufficient) ⚠️ |
| TASK-FIX-LI03: PATH check shows "already configured" | No re-patch needed | Line 173: `ℹ Shell integration already configured` ✅ |

---

## Recommendations

| Priority | Task | Description |
|----------|------|-------------|
| Normal | TASK-FIX-LI08 | Update `print_summary()` to count both `agents/` and `stack-agents/` |
| Normal | TASK-FIX-LI09 | Add `--no-warn-script-location` to both pip install calls in `install_python_package()` |

---

## Installer Status After LI04

After TASK-FIX-LI08 and TASK-FIX-LI09 are applied, the Linux installer on aarch64 Ubuntu will be **clean**:

- No `WARNING:` lines in install output
- Summary shows correct total agent count (62)
- All previously fixed items remain fixed
- Shell integration, PATH handling, template descriptions, symlinks, and backup/restore all working correctly

The installer can be considered **stable on aarch64 Ubuntu** for the primary use case (re-install from source repo with Python user install) once these two small fixes land.
