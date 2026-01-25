---
id: TASK-FB-TIMEOUT1
title: Increase Default SDK Timeout to 600s
status: completed
task_type: implementation
created: 2026-01-09T12:00:00Z
updated: 2026-01-09T16:00:00Z
priority: high
tags: [feature-build, autobuild, timeout, configuration]
complexity: 2
parent_feature: feature-build-fixes
wave: 2
implementation_mode: direct
conductor_workspace: feature-build-fixes-wave2-1
related_review: TASK-REV-FB01
supersedes: TASK-SDK-e7f2
---

# Increase Default SDK Timeout to 600s

## Problem

The default SDK timeout of 300 seconds is insufficient for the multi-phase feature-build workflow. Phase analysis shows:

| Phase | Typical Duration |
|-------|------------------|
| Pre-Loop (2-2.8) | 125-315s |
| Loop (3-5.5) | 180-420s |
| **Total** | 305-735s |

Even simple tasks can exceed 300s, causing unnecessary timeouts.

## Requirements

1. Increase `DEFAULT_SDK_TIMEOUT` from 300 to 600 seconds
2. Update environment variable documentation
3. Ensure CLI validation allows the new default

## Acceptance Criteria

- [x] `DEFAULT_SDK_TIMEOUT` is 600 in `agent_invoker.py`
- [x] Tests pass with new default
- [x] Documentation updated in CLAUDE.md

## Implementation

### Change 1: Update Default Constant

File: `guardkit/orchestrator/agent_invoker.py`

```python
# Before
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "300"))

# After
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "600"))
```

### Change 2: Update Documentation

File: `CLAUDE.md` - Update the SDK Timeout Configuration section to reflect the new default.

## Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/agent_invoker.py:44` | Change 300 to 600 |
| `CLAUDE.md` | Update default value in documentation |

## Test Plan

1. Verify constant is 600
2. Run existing tests (should pass)
3. Manually test `guardkit autobuild task` without `--sdk-timeout` flag

## Estimated Effort

15 minutes

## Dependencies

- Should be done AFTER Wave 1 fixes (TASK-FB-RPT1, TASK-FB-PATH1)
- Without the report/path fixes, increased timeout still results in failures

## Notes

- This task supersedes TASK-SDK-e7f2 (existing backlog task)
- 600s provides buffer for complex tasks while not being excessive
- Users can still override with `--sdk-timeout` flag or task frontmatter
