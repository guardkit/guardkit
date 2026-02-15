---
id: TASK-POF-002
title: Expand direct mode auto-detection for complexity ≤3
status: backlog
task_type: implementation
created: 2026-02-15T14:00:00Z
updated: 2026-02-15T14:00:00Z
priority: high
complexity: 2
tags: [autobuild, preamble, performance, quick-win]
parent_review: TASK-REV-A781
feature_id: preamble-overhead-fix
implementation_mode: direct
wave: 1
parallel_group: wave-1
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Expand Direct Mode Auto-Detection

## Description

Currently, tasks only use direct mode if explicitly marked `implementation_mode: direct` in frontmatter. Expand this to auto-detect tasks eligible for direct mode based on complexity and risk keywords.

Direct mode avoids the entire task-work preamble (~1,800s overhead) by sending a custom prompt directly to the SDK with `setting_sources=["project"]` (~78KB context vs ~1,078KB).

## Acceptance Criteria

- [ ] `_get_implementation_mode()` in `agent_invoker.py` returns `"direct"` for tasks with complexity ≤3 AND no high-risk keywords
- [ ] High-risk keywords list reuses `HIGH_RISK_KEYWORDS` from `intensity_detector.py`
- [ ] Explicit `implementation_mode: direct` in frontmatter still overrides auto-detection
- [ ] Explicit `implementation_mode: task-work` in frontmatter prevents auto-detection (opt-out)
- [ ] Logging indicates when auto-detection routes to direct mode
- [ ] No behavior change for complexity ≥4 tasks

## Files to Modify

1. `guardkit/orchestrator/agent_invoker.py` - Modify `_get_implementation_mode()` (~line 1995-2034)
2. Tests for the auto-detection logic

## Implementation Notes

- `_get_implementation_mode()` currently only checks frontmatter for explicit `implementation_mode` field
- Add complexity check: load task metadata, check complexity score and description for high-risk keywords
- Import `HIGH_RISK_KEYWORDS` from `guardkit.orchestrator.intensity_detector` to avoid duplication
- This won't help Wave 2 tasks (complexity 4-6) but reduces overhead for all simple tasks
