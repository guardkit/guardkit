---
id: TASK-REV-8BCC
title: Review Feature Build 'config' Attribute Error
status: completed
task_type: review
created: 2025-01-08T21:30:00Z
updated: 2026-01-08T22:15:00Z
priority: high
tags: [autobuild, feature-build, bug-analysis, config-error]
complexity: 5
review_mode: code-quality
review_depth: standard
related_tasks:
  - TASK-SDK-a7f3  # SDK connection fix (completed)
  - TASK-WKT-b2c4  # Worktree manager fix (completed)
  - TASK-STATE-d4e9  # State bridging (Phase 1 completed, Phase 2 pending)
  - TASK-P45-f3a1  # Phase 4.5 test enforcement (in progress)
  - TASK-WKT-c5d7  # Worktree improvements (pending)
review_results:
  mode: code-quality
  depth: standard
  score: 85
  findings_count: 1
  recommendations_count: 2
  decision: fix_recommended
  report_path: .claude/reviews/TASK-REV-8BCC-review-report.md
  completed_at: 2026-01-08T22:15:00Z
---

# Review Task: Feature Build 'config' Attribute Error

## Context

After implementing the following tasks from the feature-build improvement roadmap:

**Week 1 (Critical + Quick Wins) - COMPLETED:**
1. ✅ TASK-SDK-a7f3 (R1 - CRITICAL) - SDK connection and timeout improvements
2. ✅ TASK-WKT-b2c4 (R2 - HIGH) - Worktree manager fixes
3. ✅ TASK-STATE-d4e9 Phase 1 (R4 - HIGH) - Task state bridging

**Week 2 (Strategic Improvements) - IN PROGRESS:**
4. TASK-STATE-d4e9 Phase 2 (R4 - HIGH) - Task state bridging Phase 2
5. TASK-P45-f3a1 Phases 2 & 4 (R6 - MEDIUM) - Phase 4.5 test enforcement
6. TASK-WKT-c5d7 (R3 - MEDIUM) - Worktree improvements

The `/feature-build` command is failing with a new error:

```
Error: 'Feature' object has no attribute 'config'
```

## Error Details

**Source File:** `docs/reviews/feature-build/feature-build-output.md`

**Error Location:** Line 101 of the output log
```
✗ TASK-INFRA-001: Error - 'Feature' object has no attribute 'config'
```

**Execution Context:**
- Command: `guardkit autobuild feature FEAT-119C --max-turns 5`
- Phase: Wave 1 execution (TASK-INFRA-001)
- Feature loaded successfully (10 tasks, 8 waves)
- Worktree created successfully
- Failed during task execution, not feature loading

## Review Objectives

1. **Root Cause Analysis**: Identify where `Feature.config` is being accessed and why it doesn't exist
2. **Regression Check**: Determine if this was introduced by recent task implementations
3. **Impact Assessment**: Evaluate which code paths are affected
4. **Fix Recommendation**: Propose solution(s) with minimal regression risk

## Files to Analyze

### Primary Suspects
- `guardkit/orchestrator/feature_orchestrator.py` - Feature orchestration logic
- `guardkit/orchestrator/feature_loader.py` - Feature YAML loading
- `guardkit/orchestrator/autobuild.py` - AutoBuild task execution
- `guardkit/orchestrator/schemas.py` - Feature dataclass definition (NEW FILE)

### Secondary Files
- `guardkit/cli/autobuild.py` - CLI entry point
- `guardkit/orchestrator/agent_invoker.py` - Agent invocation (recently modified)
- `guardkit/worktrees/manager.py` - Worktree management (recently modified)

## Review Questions

1. **Where is `Feature.config` accessed?**
   - Is it in `feature_orchestrator.py` during task execution?
   - Is it in `agent_invoker.py` when invoking the Player agent?

2. **What should `config` contain?**
   - AutoBuild configuration (max_turns, sdk_timeout, mode)?
   - Feature-level settings?
   - Task-level overrides?

3. **When was this regression introduced?**
   - Was `config` ever a valid attribute?
   - Did a recent refactor remove it?
   - Is it a new requirement from recent changes?

4. **What's the minimal fix?**
   - Add `config` attribute to Feature dataclass?
   - Pass config separately instead of accessing via Feature?
   - Fix the accessor to use correct attribute name?

## Acceptance Criteria

- [ ] Root cause identified with specific file:line reference
- [ ] Regression source identified (if applicable)
- [ ] Impact on other features assessed
- [ ] Fix recommendation with code example provided
- [ ] Test case to prevent regression defined

## Test Requirements

After implementing the fix:
- [ ] `guardkit autobuild feature FEAT-XXX` executes without 'config' error
- [ ] All existing autobuild unit tests pass
- [ ] Feature orchestrator handles missing config gracefully

## Implementation Notes

This is a **review task** - use `/task-review TASK-REV-8BCC` to analyze.

If implementation is needed, the review will create a follow-up implementation task.

## References

- Feature build output: `docs/reviews/feature-build/feature-build-output.md`
- Previous review: `TASK-REV-66B4` (feature-build error analysis)
- Related review: `TASK-REV-9AC5` (feature-build output analysis)
