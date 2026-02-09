---
id: TASK-FIX-FD01
title: Raise file descriptor soft limit for parallel AutoBuild
status: completed
completed: 2026-02-09T23:05:00Z
created: 2026-02-09T22:00:00Z
updated: 2026-02-09T23:00:00Z
priority: critical
tags: [fix, parallel, fd-limit, macos, feature-orchestrator, errno-24]
task_type: implementation
complexity: 2
feature: null
parent_review: TASK-REV-B9E1
test_results:
  status: passed
  coverage: 100
  last_run: 2026-02-09T23:00:00Z
  tests_passed: 8
  tests_failed: 0
---

# Task: Raise File Descriptor Soft Limit for Parallel AutoBuild

## Description

Add `resource.setrlimit()` at process startup to raise the macOS file descriptor soft limit from 256 to 4096. This is the P0 (critical) fix from TASK-REV-B9E1.

### Problem

macOS `launchctl limit maxfiles` defaults to 256 (soft) / unlimited (hard). Each parallel AutoBuild task consumes ~60-90 file descriptors (Claude Code CLI subprocess + Neo4j + OpenAI + git + runtime). With 3 parallel tasks in Wave 2, the total reaches ~320 FDs, exceeding the 256 limit and causing `[Errno 24] Too many open files` crashes at git checkpoint operations.

Evidence: FEAT-6EDD run 2 — SP-003 and SP-005 both crashed with `[Errno 24]` during `subprocess.run() → Popen() → os.pipe()` in `_execute_git_checkpoint()`.

### Solution

Add file descriptor limit elevation in `FeatureOrchestrator.__init__()`:

```python
import resource

soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
if soft < 4096:
    new_soft = min(4096, hard) if hard != resource.RLIM_INFINITY else 4096
    resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, hard))
    logger.info(f"Raised file descriptor limit: {soft} → {new_soft}")
```

### Why FeatureOrchestrator (not CLI entrypoint)

- Targeted: Only raises limit when parallel execution is needed
- Self-documenting: The fix is next to the code that needs it
- Testable: Can verify in unit tests without affecting CLI
- CLI entrypoint is also acceptable but less targeted

## Acceptance Criteria

- [x] `resource.setrlimit(RLIMIT_NOFILE)` called in `FeatureOrchestrator.__init__()` when parallel tasks will be dispatched
- [x] Soft limit raised to `min(4096, hard_limit)` — never exceeds hard limit
- [x] Log message at INFO level when limit is raised (include old and new values)
- [x] No-op when soft limit is already >= 4096 (no log noise)
- [x] Graceful handling if `setrlimit()` raises `ValueError` or `OSError` (log WARNING, continue)
- [x] Works on macOS (primary) and Linux (secondary)
- [x] Unit tests: verify limit is raised, verify no-op when already high, verify error handling
- [x] No regressions in existing FeatureOrchestrator tests

## Key Files

- `guardkit/orchestrator/feature_orchestrator.py` — Add `setrlimit()` in `__init__()` or `_execute_wave_parallel()`
- `tests/unit/test_feature_orchestrator.py` — New tests

## Context

- Review: TASK-REV-B9E1 (P0 fix)
- Review report: `.claude/reviews/TASK-REV-B9E1-review-report.md`
- Current limits: `launchctl limit maxfiles` = 256 soft / unlimited hard
- `kern.maxfilesperproc` = 245760 (hard limit is generous)
- FD budget at 4096: ~320 / 4096 = 7.8% utilization (comfortable)

## Dependencies

None — this is independent and should be implemented first.
