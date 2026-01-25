---
id: TASK-FIX-SDKTMO
title: "Increase SDK timeout for feature-build parallel execution"
status: completed
created: 2026-01-24T00:35:00Z
updated: 2026-01-24T01:20:00Z
completed: 2026-01-24T01:20:00Z
priority: medium
tags: [fix, sdk-timeout, feature-build, autobuild, performance]
task_type: feature
complexity: 2
parent_review: TASK-REV-FB25
feature_id: FEAT-FB-FIXES
implementation_mode: task-work
wave: 2
depends_on: [TASK-FIX-COVNULL, TASK-FIX-INDTEST]
estimated_hours: 1
previous_state: in_review
state_transition_reason: "Task completed - SDK timeout increased to 900s"
completed_location: tasks/completed/TASK-FIX-SDKTMO/
---

# Increase SDK timeout for feature-build parallel execution

## Problem

SDK timeout of 600s (10 minutes) is insufficient for complex tasks that spawn subagents (like test-orchestrator), especially during parallel execution.

### Evidence from logs:
```
ERROR:[TASK-FHA-003] SDK TIMEOUT: task-work execution exceeded 600s timeout
ERROR:[TASK-FHA-003] Messages processed before timeout: 255
ERROR:[TASK-FHA-003] Last output: ...test-orchestrator agent invocation in progress...
```

### Contributing factors:
- Parallel execution of 3 tasks in Wave 1
- Each task spawns test-orchestrator subagent
- Nested agent invocations increase latency
- API rate limiting may cause delays

## Solution

### Option A: Increase default timeout for feature-build (IMPLEMENTED)

In `guardkit/orchestrator/feature_orchestrator.py`:

```python
# Default timeout for feature-build should be higher
DEFAULT_FEATURE_SDK_TIMEOUT = 900  # 15 minutes instead of 10
```

### Option B: Dynamic timeout based on task count

```python
def _calculate_timeout(self, wave_task_count: int) -> int:
    """Calculate SDK timeout based on wave complexity."""
    base_timeout = 600  # 10 minutes base
    per_task_buffer = 60  # +1 minute per parallel task
    return base_timeout + (wave_task_count * per_task_buffer)
```

### Option C: Add timeout monitoring with early warning

```python
async def _monitor_timeout(self, timeout: int, task_id: str):
    """Monitor SDK execution and warn at 80% threshold."""
    warning_threshold = int(timeout * 0.8)
    await asyncio.sleep(warning_threshold)
    logger.warning(f"[{task_id}] Approaching timeout ({warning_threshold}s elapsed)")
```

## Recommendation

**Option A** is the quickest fix. Consider combining with Option B for smarter resource allocation.

## Acceptance Criteria

- [x] Feature-build default SDK timeout increased to 900s (15 minutes)
- [x] CLI flag `--sdk-timeout` continues to work as override
- [x] Task frontmatter `autobuild.sdk_timeout` continues to work
- [x] Documentation updated with new default
- [ ] No timeout errors for standard feature-build runs (requires runtime verification)

## Implementation Notes

### Files modified:
1. `guardkit/orchestrator/feature_orchestrator.py` - Default timeout (line 1233)
2. `guardkit/orchestrator/autobuild.py` - Default sdk_timeout parameter (line 320)
3. `.claude/rules/autobuild.md` - Documentation (lines 86, 170, 180-181)

### Tests updated:
1. `tests/unit/test_autobuild_orchestrator.py` - `test_default_sdk_timeout_propagated`, `test_sdk_timeout_default_value`
2. `tests/unit/test_feature_orchestrator.py` - `test_execute_task_uses_default_sdk_timeout_when_not_specified`

### Current timeout cascade:
1. CLI flag: `--sdk-timeout 900`
2. Task frontmatter: `autobuild.sdk_timeout: 900`
3. Environment: `GUARDKIT_SDK_TIMEOUT=900`
4. Default: 900 (changed from 600)

## Testing

```bash
# Run feature-build with verbose logging
guardkit autobuild feature FEAT-XXX --verbose

# Verify timeout is 900s in logs
# INFO:...SDK timeout: 900s
```

## Related

- Parent review: TASK-REV-FB25
- Related fix: TASK-FIX-COVNULL, TASK-FIX-INDTEST
- Documentation: .claude/rules/autobuild.md
