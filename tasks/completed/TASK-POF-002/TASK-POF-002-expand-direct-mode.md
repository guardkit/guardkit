---
id: TASK-POF-002
title: Expand direct mode auto-detection for complexity ≤3
status: completed
task_type: implementation
created: 2026-02-15T14:00:00Z
updated: 2026-02-15T18:00:00Z
completed: 2026-02-15T18:00:00Z
priority: high
complexity: 2
tags: [autobuild, preamble, performance, quick-win]
parent_review: TASK-REV-A781
feature_id: preamble-overhead-fix
implementation_mode: direct
wave: 1
parallel_group: wave-1
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-15T18:00:00Z
  tests_passed: 329
  tests_failed: 0
  new_tests_added: 13
---

# Task: Expand Direct Mode Auto-Detection

## Description

Currently, tasks only use direct mode if explicitly marked `implementation_mode: direct` in frontmatter. Expand this to auto-detect tasks eligible for direct mode based on complexity and risk keywords.

Direct mode avoids the entire task-work preamble (~1,800s overhead) by sending a custom prompt directly to the SDK with `setting_sources=["project"]` (~78KB context vs ~1,078KB).

## Acceptance Criteria

- [x] `_get_implementation_mode()` in `agent_invoker.py` returns `"direct"` for tasks with complexity ≤3 AND no high-risk keywords
- [x] High-risk keywords list reuses `HIGH_RISK_KEYWORDS` from `intensity_detector.py`
- [x] Explicit `implementation_mode: direct` in frontmatter still overrides auto-detection
- [x] Explicit `implementation_mode: task-work` in frontmatter prevents auto-detection (opt-out)
- [x] Logging indicates when auto-detection routes to direct mode
- [x] No behavior change for complexity ≥4 tasks

## Files Modified

1. `guardkit/orchestrator/agent_invoker.py` - Modified `_get_implementation_mode()` + added `_auto_detect_direct_mode()`
2. `tests/unit/test_agent_invoker.py` - Added `TestDirectModeAutoDetection` class (13 tests)

## Implementation Notes

- `_get_implementation_mode()` now delegates to `_auto_detect_direct_mode()` when no explicit mode is set
- Auto-detection requires explicit `complexity` in frontmatter (no score = task-work)
- Imports `HIGH_RISK_KEYWORDS` from `guardkit.orchestrator.intensity_detector` (zero duplication)
- Checks both title and content for high-risk keywords (case-insensitive)
- Gracefully handles invalid complexity values (non-numeric → task-work)
- All 329 existing tests continue to pass
