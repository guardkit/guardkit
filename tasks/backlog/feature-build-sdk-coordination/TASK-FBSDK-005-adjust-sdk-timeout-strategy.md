---
id: TASK-FBSDK-005
title: Adjust SDK timeout strategy for feature-build
status: backlog
created: 2026-01-18T12:15:00Z
updated: 2026-01-18T12:15:00Z
priority: low
tags: [feature-build, sdk-timeout, optimization]
complexity: 2
parent_review: TASK-REV-F6CB
feature_id: FEAT-FBSDK
implementation_mode: direct
wave: 3
conductor_workspace: feature-build-sdk-wave3-1
depends_on:
  - TASK-FBSDK-003
  - TASK-FBSDK-004
---

# Task: Adjust SDK timeout strategy for feature-build

## Description

Test traces show successful work being done but not captured due to SDK timeout. The default 600s (10 minutes) is insufficient for TDD-style implementation where comprehensive test suites are created first.

## Analysis

| Scenario | Observed Duration | Current Timeout | Result |
|----------|-------------------|-----------------|--------|
| Simple feature task | 400-600s | 600s | Timeout |
| Complex feature task | 1200-2400s | 600s | Timeout |
| With pre-loop enabled | 3600-7200s | 600s | Timeout |

The work is completing, but the timeout fires before SDK signals completion.

## Implementation

### Option A: Use Pre-Loop-Aware Defaults (Recommended)

```python
# In FeatureOrchestrator
def _get_sdk_timeout(self, task: FeatureTask) -> int:
    """Get SDK timeout based on task context.

    Args:
        task: Feature task being executed

    Returns:
        Timeout in seconds
    """
    base_timeout = 1800  # 30 minutes base

    # Adjust for pre-loop
    if self.enable_pre_loop:
        base_timeout = 7200  # 2 hours with pre-loop

    # Adjust for complexity if available
    complexity = task.complexity or 5
    if complexity >= 7:
        base_timeout = int(base_timeout * 1.5)

    return base_timeout
```

### Option B: Document Timeout Tuning

Update `.claude/rules/autobuild.md` with timeout recommendations:

```markdown
## SDK Timeout Configuration

| Task Type | Pre-Loop | Recommended Timeout |
|-----------|----------|---------------------|
| Simple feature task | Off | 1800s (30 min) |
| Medium feature task | Off | 2400s (40 min) |
| Complex feature task | Off | 3600s (1 hour) |
| Any task | On | 7200s (2 hours) |

Use `--sdk-timeout` flag to override:
```bash
guardkit autobuild feature FEAT-XXX --sdk-timeout 3600
```
```

## Files to Modify

- `guardkit/orchestrator/feature_orchestrator.py` - Add `_get_sdk_timeout()` method
- `guardkit/orchestrator/autobuild.py` - Pass timeout to AgentInvoker
- `.claude/rules/autobuild.md` - Document timeout recommendations

## Acceptance Criteria

- [ ] Feature-build uses pre-loop-aware timeout defaults
- [ ] Complex tasks get extended timeout automatically
- [ ] Documentation updated with timeout recommendations
- [ ] `--sdk-timeout` flag continues to work as override

## Testing Strategy

1. **Unit Test**: Verify timeout calculation for different scenarios
2. **Manual Test**: Run feature-build with various task complexities

## Notes

This is a P3 optimization. The P0/P1 fixes will resolve the core issues; this improves success rate for edge cases.
