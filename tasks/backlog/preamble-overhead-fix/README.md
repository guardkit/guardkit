# Preamble Overhead Fix

## Problem

The task-work session preamble consumes ~1,800 seconds (30 minutes) before autobuild implementation work begins. Three compounding root causes identified in TASK-REV-A781:

1. **Context injection** (60%): ~1MB of commands/rules loaded per SDK session
2. **Serial subagent phases** (25%): Phases 1.6-2.8 run 3-5 subagents sequentially
3. **Double session init** (15%): Pre-loop and Player each create separate SDK sessions

## Solution

Two-phase fix targeting ~1,200s reduction (1,800s -> ~600s):

- **Wave 1** (Quick wins): `--autobuild-mode` flag + expanded direct mode
- **Wave 2** (Main fix): Inline execution protocol, eliminate user command loading

## Tasks

| Task | Wave | Complexity | Method | Description |
|------|------|------------|--------|-------------|
| TASK-POF-001 | 1 | 2 | direct | Add `--autobuild-mode` composite flag |
| TASK-POF-002 | 1 | 2 | direct | Expand direct mode auto-detection |
| TASK-POF-003 | 2 | 5 | task-work | Inline design phase execution protocol |
| TASK-POF-004 | 2 | 5 | task-work | Inline implement phase execution protocol |

## Verification

After each wave, run a canary autobuild task and measure preamble duration:
```bash
time guardkit autobuild task TASK-CANARY --verbose 2>&1 | grep -E "Phase|Starting|Complete"
```

## Parent Review

TASK-REV-A781 - Root Cause Analysis of Task-Work Session Preamble Overhead
