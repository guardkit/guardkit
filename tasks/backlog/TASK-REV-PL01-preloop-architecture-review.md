---
id: TASK-REV-PL01
title: Review whether FB-FIX-015 (disable pre-loop) is still needed after FB-FIX-018
status: backlog
created: 2026-01-13T19:45:00Z
updated: 2026-01-13T19:45:00Z
priority: high
tags: [review, architecture, feature-build, pre-loop, decision-point]
task_type: review
complexity: 5
decision_required: true
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Review: Is FB-FIX-015 (Disable Pre-Loop) Still Needed?

## Background

The original AutoBuild architecture was designed with a **pre-loop design phase**:

```
AutoBuild Flow (Original Design):
  Setup → Pre-Loop (task-work --design-only) → Player-Coach Loop → Finalize
              │
              └── Purpose: Generate implementation plan BEFORE Player-Coach
```

This pre-loop was taking **89 minutes** for simple tasks, leading to two fixes:

| Fix | Description | Status |
|-----|-------------|--------|
| **FB-FIX-015** | Default `enable_pre_loop=false` for feature-build | Implemented |
| **FB-FIX-018** | Default documentation level to `minimal` | Implemented |

## The Concern

> "It concerns me that the original architecture was to do the implementation plan using task-work --design mode before running the player-coach loop and it seems as if we have undone this key part of the architecture due to the documentation bug which has now been fixed."

**Key Question**: Now that FB-FIX-018 fixes the documentation bug (reducing design phase from 89 min to ~15-20 min), should we **re-enable pre-loop by default** for feature-build?

## Questions to Investigate

### 1. What Was the Original Intent of Pre-Loop?

The pre-loop design phase was intended to:
- Generate a comprehensive implementation plan BEFORE Player-Coach iterations
- Provide architectural review (Phase 2.5B) to catch design issues early
- Create a human checkpoint (Phase 2.8) for approval before implementation
- Ensure consistency between design and implementation

### 2. Does Feature-Build Need Pre-Loop?

Feature-build tasks come from `/feature-plan` which already provides:
- Detailed acceptance criteria from review recommendations
- Architectural analysis from parent review
- Complexity scoring from task creation
- Implementation mode assignment (task-work/direct/manual)

**Question**: Is this sufficient, or does the Player need the formal implementation plan?

### 3. What Is the Time Budget Now?

With FB-FIX-018 implemented:
- **Before**: Pre-loop = 89 min, Loop = ~30 min → Total = ~119 min per task
- **After**: Pre-loop = ~15-20 min, Loop = ~30 min → Total = ~45-50 min per task

For a 7-task feature:
- **Without pre-loop**: 7 × 30 min = ~3.5 hours
- **With pre-loop**: 7 × 50 min = ~5.8 hours

**Question**: Is the 2.3 hour overhead (per feature) worth the design quality benefit?

### 4. What Does the Player Actually Use?

When Player executes `task-work --implement-only`, it uses:
- `docs/state/{task_id}/implementation_plan.md` - File list, phases, estimates
- `docs/state/{task_id}/implementation_plan.json` - Machine-readable plan
- Architectural review score from Phase 2.5B

**Question**: Does the Player actually benefit from having the plan, or can it implement effectively from just the task acceptance criteria?

### 5. What About Standalone Task-Build?

For `guardkit autobuild task TASK-XXX` (standalone, not feature), pre-loop is still enabled by default.

**Question**: Should feature-build and task-build have the same defaults?

## Options to Evaluate

### Option A: Keep FB-FIX-015 (Pre-Loop Disabled for Feature-Build)

**Rationale**: Feature tasks already have detailed specs from feature-plan; pre-loop is redundant.

**Pros**:
- Faster feature builds (~3.5 hours vs ~5.8 hours for 7 tasks)
- Less ceremony for well-defined tasks
- Feature-plan already provided architectural analysis

**Cons**:
- Player lacks formal implementation plan
- No human checkpoint before implementation
- Divergence from original architecture

### Option B: Revert FB-FIX-015 (Re-Enable Pre-Loop for Feature-Build)

**Rationale**: Now that FB-FIX-018 fixed the time issue, the original architecture should be restored.

**Pros**:
- Consistent with original design intent
- Player has implementation plan to follow
- Human checkpoint ensures approval before each task
- Architectural review catches issues early

**Cons**:
- 2.3 hour overhead per 7-task feature
- May be redundant with feature-plan analysis
- More ceremony

### Option C: Make Pre-Loop Configurable Per-Task

**Rationale**: Let the task complexity and requirements drive the decision.

**Implementation**:
```yaml
# In task frontmatter
autobuild:
  enable_pre_loop: true  # Override for complex tasks
```

**Pros**:
- Flexibility for different task types
- Simple tasks skip pre-loop, complex tasks use it
- User control

**Cons**:
- More configuration complexity
- Inconsistent behavior

### Option D: Hybrid - Pre-Loop for First Task Only

**Rationale**: Run pre-loop once per feature to establish patterns, then skip for subsequent tasks.

**Implementation**:
- Wave 1 tasks: Pre-loop enabled
- Wave 2+ tasks: Pre-loop disabled

**Pros**:
- Establishes design patterns early
- Subsequent tasks follow established patterns
- Balance of quality and speed

**Cons**:
- Complex implementation
- May not apply to all feature structures

## Evidence to Gather

1. **Test Feature-Build with Pre-Loop Enabled + FB-FIX-018**
   - Run with `--enable-pre-loop` flag
   - Measure actual duration with minimal docs
   - Verify ~15-20 min pre-loop time

2. **Compare Implementation Quality**
   - Run same task with and without pre-loop
   - Compare Player implementation quality
   - Check if implementation plan actually improves output

3. **Review Original Architecture Decision**
   - Why was pre-loop added in the first place?
   - What problems was it solving?
   - Are those problems still relevant?

## Acceptance Criteria

- [ ] Document the original intent of the pre-loop architecture
- [ ] Test feature-build with pre-loop enabled + FB-FIX-018 (measure time)
- [ ] Evaluate whether Player implementation quality differs with/without pre-loop
- [ ] Provide clear recommendation (keep FB-FIX-015 or revert)
- [ ] If reverting, create implementation task for the change

## Review Mode

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Focus**: Architecture decision - whether to preserve or restore original design

## Next Steps

Execute this review with:
```bash
/task-review TASK-REV-PL01 --mode=decision --depth=standard
```
