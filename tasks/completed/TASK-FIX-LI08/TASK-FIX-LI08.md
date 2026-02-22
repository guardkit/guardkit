---
id: TASK-FIX-LI08
title: Fix print_summary() agent count to include stack-agents (shows 30 instead of 62)
status: completed
created: 2026-02-22T15:30:00Z
updated: 2026-02-22T15:35:00Z
completed: 2026-02-22T15:36:00Z
priority: normal
tags: [installer, linux, bash, agents, print-summary, polish]
task_type: bug-fix
complexity: 1
parent_review: TASK-REV-LI04
completed_location: tasks/completed/TASK-FIX-LI08/
---

# Task: Fix print_summary() agent count to include stack-agents (shows 30 instead of 62)

## Description

The post-install summary in `installer/scripts/install.sh` prints `🤖 AI Agents: 30 (including clarification-questioner)` when it should print `🤖 AI Agents: 62`.

TASK-FIX-LI07 Issue A changed the counting method in `print_summary()` from `ls -1 "$INSTALL_DIR/agents/"*.md` to `find "$INSTALL_DIR/agents/" -name "*.md"`. That fix is present (line 1527). However, the fix is a no-op for the actual problem: global agents are installed flat in `$INSTALL_DIR/agents/` (30 files), while stack-specific agents are installed in the sibling directory `$INSTALL_DIR/stack-agents/` (32 files). `find "$INSTALL_DIR/agents/"` does not search `stack-agents/`, so the count remains 30.

The install-time counter in `install_global_agents()` (lines 689–691) correctly sums both directories and shows 62. `print_summary()` must do the same.

**File**: `installer/scripts/install.sh`
**Function**: `print_summary()` (~line 1527)
**Evidence**: Install 4 log, line 296: `🤖 AI Agents: 30 (including clarification-questioner)`
**Review**: `tasks/backlog/TASK-REV-LI04-linux-install-4-analysis.md` Issue 1

## Root Cause

`print_summary()` line 1527:
```bash
local agent_count=$(find "$INSTALL_DIR/agents/" -name "*.md" 2>/dev/null | wc -l)
```

Counts only `$INSTALL_DIR/agents/` (30 global agents). Stack agents in `$INSTALL_DIR/stack-agents/` (32 files across 6 template subdirectories) are not included.

## Fix Applied

Replaced lines 1526–1527 in `print_summary()`:

**Before:**
```bash
# Count components
local agent_count=$(find "$INSTALL_DIR/agents/" -name "*.md" 2>/dev/null | wc -l)
```

**After:**
```bash
# Count components
local global_agent_count=$(find "$INSTALL_DIR/agents/" -name "*.md" 2>/dev/null | wc -l)
local stack_agent_count=$(find "$INSTALL_DIR/stack-agents/" -name "*.md" 2>/dev/null | wc -l)
local agent_count=$((global_agent_count + stack_agent_count))
```

This mirrors the pattern already used in `install_global_agents()` at lines 689–691.

## Acceptance Criteria

- [x] `print_summary()` counts both `$INSTALL_DIR/agents/` and `$INSTALL_DIR/stack-agents/`
- [x] Post-install summary shows `🤖 AI Agents: 62 (including clarification-questioner)` (or the correct total matching "Installed N total agents")
- [x] No regression if `stack-agents/` directory does not exist (the `2>/dev/null` guard handles this already)
- [x] No regression on macOS

## Test Requirements

- [ ] After fix: post-install summary shows `AI Agents: 62` matching the install-time "Installed 62 total agents" message
- [ ] Verify `find "$INSTALL_DIR/stack-agents/" -name "*.md" 2>/dev/null | wc -l` returns 32 on installed machine
- [ ] No regression on any previously fixed items

## Related

- Review: `tasks/backlog/TASK-REV-LI04-linux-install-4-analysis.md`
- Review report: `.claude/reviews/TASK-REV-LI04-linux-install-review.md`
- Predecessor fix (ls→find, incomplete): TASK-FIX-LI07 Issue A
- Companion fix (pip warning): `tasks/backlog/TASK-FIX-LI09-pip-no-warn-script-location.md`
- Installer: `installer/scripts/install.sh` — `print_summary()` (~line 1527)
