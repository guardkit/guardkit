---
id: TASK-FIX-DFCB
title: Implement cross-platform subprocess cleanup for macOS
status: completed
completed: 2026-03-01T00:00:00Z
task_type: feature
parent_review: TASK-REV-A327
feature_id: FEAT-E4F5
wave: 2
implementation_mode: task-work
complexity: 4
priority: high
tags: [macos, subprocess, cleanup, p1, bugfix]
depends_on: []
---

# Task: Implement cross-platform subprocess cleanup for macOS

## Description

Replace the Linux-only `/proc`-based subprocess cleanup in `_kill_child_claude_processes()` with a cross-platform approach that works on macOS (Darwin). The current implementation checks for `/proc` and returns immediately with a warning on macOS, leaving zombie CLI subprocesses running after timeouts.

## Acceptance Criteria

- [x] `_kill_child_claude_processes()` terminates child Claude CLI processes on macOS
- [x] `_kill_child_claude_processes()` continues to work on Linux
- [x] No new hard dependency added (psutil optional, with fallback)
- [x] All existing tests pass
- [x] Unit test: Verify cleanup is attempted on Darwin platform
- [x] The existing Linux `/proc`-based path is preserved as the primary approach

## Implementation Notes

- File: `guardkit/orchestrator/agent_invoker.py`, lines 799-882
- Current code skips cleanup on macOS:
  ```python
  proc_path = Path("/proc")
  if not proc_path.exists():
      logger.warning("... /proc not available ...")
      return  # ← macOS: NO CLEANUP
  ```
- Options for cross-platform approach:
  1. **psutil** (optional dependency): `psutil.Process().children(recursive=True)` — cleanest but adds dependency
  2. **Tracked PID**: Store subprocess PID from SDK transport and `os.kill(pid, signal.SIGTERM)` directly
  3. **pgrep fallback**: `subprocess.run(["pgrep", "-P", str(os.getpid()), "claude|node"])` — no dependency but less reliable
- Recommend option 1 with option 3 as fallback
- The method is called from the cancellation monitor (line 1730) and `request_cancellation()` (line 797)
