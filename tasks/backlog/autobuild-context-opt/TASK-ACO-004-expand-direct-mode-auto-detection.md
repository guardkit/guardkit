---
id: TASK-ACO-004
title: Expand direct mode auto-detection for complexity <=3
task_type: feature
parent_review: TASK-REV-A781
feature_id: FEAT-ACO
wave: 2
implementation_mode: task-work
complexity: 2
dependencies:
  - TASK-ACO-001
status: pending
priority: medium
---

# TASK-ACO-004: Expand Direct Mode Auto-Detection

## Objective

Enhance `_get_implementation_mode()` in `agent_invoker.py` to automatically detect and route complexity <=3 tasks to direct mode, bypassing the SDK session entirely for simple tasks.

## Context

Direct mode tasks execute inline (~60-120s preamble) vs task-work SDK sessions (~1,800s preamble). Currently, direct mode requires explicit `implementation_mode: direct` in task frontmatter. This task adds automatic detection for simple tasks.

## Deliverables

### 1. Update `_get_implementation_mode()`

**File**: `guardkit/orchestrator/agent_invoker.py`

```python
def _get_implementation_mode(self, task_id: str) -> str:
    # Existing: check frontmatter for explicit implementation_mode
    impl_mode = task_data.get("frontmatter", {}).get("implementation_mode")
    if impl_mode == "direct":
        return "direct"

    # NEW: Auto-detect direct mode for simple tasks
    complexity = task_data.get("frontmatter", {}).get("complexity", 5)
    if complexity <= 3:
        # Check for high-risk keywords that would require full task-work
        risk_keywords = ["security", "auth", "migration", "database", "api"]
        title = task_data.get("frontmatter", {}).get("title", "").lower()
        body = task_data.get("body", "").lower()
        has_risk = any(kw in title or kw in body for kw in risk_keywords)

        if not has_risk:
            logger.info(
                f"[{task_id}] Auto-detected direct mode "
                f"(complexity={complexity}, no risk keywords)"
            )
            return "direct"

    return "task-work"
```

## Acceptance Criteria

- [ ] Tasks with `complexity <= 3` AND no risk keywords auto-route to direct mode
- [ ] Tasks with `complexity <= 3` BUT containing risk keywords remain in task-work mode
- [ ] Tasks with explicit `implementation_mode: direct` in frontmatter still work
- [ ] Tasks with `complexity > 3` unaffected (still default to task-work)
- [ ] Auto-detection is logged for observability
- [ ] Default complexity (when not set) remains 5 (not auto-detected as direct)

## Risk Keywords

The following keywords in task title or body prevent auto-detection:
- `security` — security-sensitive changes need full review
- `auth` — authentication changes need full review
- `migration` — data migration needs careful handling
- `database` — schema changes need careful handling
- `api` — API changes may have downstream impact

## Files Modified

| File | Change |
|------|--------|
| `guardkit/orchestrator/agent_invoker.py` | Update `_get_implementation_mode()` |

## Testing

- Unit test: complexity 2, no risk keywords → "direct"
- Unit test: complexity 3, title contains "auth" → "task-work"
- Unit test: complexity 5, no risk keywords → "task-work"
- Unit test: complexity not set (default 5) → "task-work"
- Unit test: explicit `implementation_mode: direct` in frontmatter → "direct"
