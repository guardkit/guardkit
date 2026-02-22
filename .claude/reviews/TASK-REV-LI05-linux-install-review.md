# Review Report: TASK-REV-LI05

**Task**: Analyse fifth Linux installation of GuardKit on Dell ProMax GB10 (aarch64)
**Mode**: Code quality / installer analysis
**Depth**: Standard
**Reviewed**: 2026-02-22
**Install log**: `docs/reviews/linux_install/linux_install_5.md`
**Install timestamp**: `20260222_151405` (15:14 UTC)

---

## Executive Summary

Install 5 captured the state of the installer after **TASK-FIX-LI09 only**. Despite the task description saying install 5 was run after both TASK-FIX-LI08 and TASK-FIX-LI09, the log evidence is unambiguous: the summary still shows `AI Agents: 30`, confirming TASK-FIX-LI08 was not yet applied. The current `install.sh` on disk also confirms this — `print_summary()` at line 1527 still counts only `$INSTALL_DIR/agents/` (30 global agents).

**TASK-FIX-LI09 is cleanly resolved**: no `WARNING:` lines appear anywhere in the install 5 output.

All previously fixed items (TASK-FIX-LI06, TASK-FIX-LI07 Issue B) remain intact — no regressions.

No new issues are present in install 5.

**Outcome**: A sixth install will be required to verify TASK-FIX-LI08 once that fix lands.

---

## Fix Verification

### TASK-FIX-LI09: Suppress pip `WARNING:` → RESOLVED ✅

| Attribute | Value |
|-----------|-------|
| Expected | No `WARNING:` lines in install output |
| Observed | Zero `WARNING:` lines anywhere in install 5 log |
| `install.sh` lines 428/436 | Both pip calls now carry `--no-warn-script-location` |

**Analysis:**

Both pip invocations in `install_python_package()` now include the flag:

```bash
# Line 428 — primary (--break-system-packages)
python3 -m pip install -e "$repo_root[autobuild]" --break-system-packages --no-warn-script-location 2>&1

# Line 436 — fallback (--user)
python3 -m pip install -e "$repo_root[autobuild]" --user --no-warn-script-location 2>&1
```

The `WARNING: The script guardkit-py is installed in '/home/richardwoollcott/.local/bin' which is not on PATH.` line that appeared in install 4 is completely absent from install 5. Fix is clean.

Note: Line 35 of the install 5 log reads `Defaulting to user installation because normal site-packages is not writeable`. This is a pip informational message (not `WARNING:` level) emitted when the `--break-system-packages` attempt resolves to user mode on this system. This is pre-existing behavior, not a regression.

**Verdict**: `resolved` ✅

---

### TASK-FIX-LI08: Agent count in `print_summary()` → NOT RESOLVED ⚠️

| Attribute | Value |
|-----------|-------|
| Expected | `🤖 AI Agents: 62 (including clarification-questioner)` |
| Observed (install 5, line 294) | `🤖 AI Agents: 30 (including clarification-questioner)` |
| Current `print_summary()` in `install.sh` (line 1527) | `find "$INSTALL_DIR/agents/" -name "*.md"` — counts global agents only |
| Task status | Still in `tasks/backlog/` |

**Analysis:**

The fix recommended in TASK-REV-LI04 was not applied before install 5 was captured. The current `print_summary()` at line 1527 reads:

```bash
local agent_count=$(find "$INSTALL_DIR/agents/" -name "*.md" 2>/dev/null | wc -l)
```

This counts only the 30 global agents in `$INSTALL_DIR/agents/`. Stack agents (32) live in `$INSTALL_DIR/stack-agents/<template>/` and are not included. The install-time counter in `install_global_agents()` (lines 689–691) correctly counts both directories and prints `Installed 62 total agents` (install 5 log, line 134), but `print_summary()` does not mirror this logic.

The required fix (unchanged from TASK-REV-LI04 recommendation) is:

```bash
local global_agent_count=$(find "$INSTALL_DIR/agents/" -name "*.md" 2>/dev/null | wc -l)
local stack_agent_count=$(find "$INSTALL_DIR/stack-agents/" -name "*.md" 2>/dev/null | wc -l)
local agent_count=$((global_agent_count + stack_agent_count))
```

**Verdict**: `not-resolved` — TASK-FIX-LI08 still pending, install 5 was taken before the fix landed.

---

## Regression Checks

### TASK-FIX-LI06: No mid-install `⚠` PATH warning → NO REGRESSION ✅

| Expected | Observed |
|----------|----------|
| PATH notice uses `ℹ` (info), not `⚠` (warning) | Line 282: `ℹ guardkit-py installed to ~/.local/bin — restart your shell or run: source ~/.bashrc` |

Clean. The `ℹ` prefix is correct and the line appears just before the summary, exactly as fixed.

### TASK-FIX-LI07 Issue B: Template descriptions → NO REGRESSION ✅

| Expected | Observed |
|----------|----------|
| `fastmcp-python` shows description | Line 308: `• fastmcp-python - FastMCP Python server with tool registration and async patterns` ✅ |
| `mcp-typescript` shows description | Line 309: `• mcp-typescript - MCP TypeScript server with @modelcontextprotocol/sdk and Zod validation` ✅ |

Both descriptions present. No regression.

---

## New Issues in Install 5

None found. The install 5 output is clean apart from the unresolved TASK-FIX-LI08 summary count.

---

## Full Fix Status Table

| Fix | Expected | Install 5 Observed | Status |
|-----|----------|--------------------|--------|
| TASK-FIX-LI09: Suppress pip `WARNING:` | No `WARNING:` lines | No `WARNING:` lines | ✅ RESOLVED |
| TASK-FIX-LI08: Agent count in summary | `AI Agents: 62` | `AI Agents: 30` | ⚠️ NOT RESOLVED |
| TASK-FIX-LI06: No mid-install `⚠` PATH warning | `ℹ` info only | `ℹ` info only | ✅ NO REGRESSION |
| TASK-FIX-LI07 Issue B: Template descriptions | `fastmcp-python`, `mcp-typescript` described | Both described | ✅ NO REGRESSION |

---

## Recommendations

| Priority | Task | Description |
|----------|------|-------------|
| Normal | TASK-FIX-LI08 (existing) | Apply the `print_summary()` fix to count both `agents/` and `stack-agents/` |
| Normal | TASK-REV-LI06 (new) | Run a sixth install after TASK-FIX-LI08 lands to confirm summary shows 62 |

No new `TASK-FIX-LI10+` items are required.

---

## Installer Status After LI05

- **TASK-FIX-LI09**: ✅ Clean — pip output has no `WARNING:` lines
- **TASK-FIX-LI08**: ⚠️ Still pending — summary still shows 30 agents
- **All other fixes**: ✅ No regressions

The installer cannot be declared fully stable on aarch64 Ubuntu until TASK-FIX-LI08 is applied and verified in install 6. All other aspects of the install are clean.

---

## Post-Review Note

**Decision**: [A]ccept — 2026-02-22

TASK-FIX-LI08 was applied to `installer/scripts/install.sh` immediately after this review. `print_summary()` now reads:

```bash
local global_agent_count=$(find "$INSTALL_DIR/agents/" -name "*.md" 2>/dev/null | wc -l)
local stack_agent_count=$(find "$INSTALL_DIR/stack-agents/" -name "*.md" 2>/dev/null | wc -l)
local agent_count=$((global_agent_count + stack_agent_count))
```

A sixth install (TASK-REV-LI06) should be run to confirm the summary now shows `AI Agents: 62`.
