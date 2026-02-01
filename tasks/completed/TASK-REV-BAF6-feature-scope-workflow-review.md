---
id: TASK-REV-BAF6
title: Review Feature Scope Limits and Iterative Workflow Improvements
status: completed
task_type: review
review_mode: decision
priority: high
created: 2026-01-31T10:00:00Z
tags: [architecture, workflow, scope-management, feature-plan, task-review]
complexity: 7
related_features:
  - FEAT-GR-MVP
  - FEAT-0F4A
review_results:
  mode: decision
  depth: standard
  recommendation: Option E - Enhanced Combination Approach
  findings_count: 4
  recommendations_count: 8
  decision: accepted
  report_path: .claude/reviews/TASK-REV-BAF6-review-report.md
  completed_at: 2026-01-31T12:00:00Z
---

# Review Feature Scope Limits and Iterative Workflow Improvements

## Problem Statement

The current `/feature-plan` and `/task-review` commands can generate features with excessive task counts (e.g., FEAT-GR-MVP has 1686+ task files in its worktree), which:

1. **Violates iterative development principles** - Large batches of work make diagnosis difficult when issues arise
2. **Increases risk surface area** - Too many changes in one scope make verification harder
3. **Reduces feedback loop frequency** - Can't test/verify incrementally with oversized features
4. **AutoBuild compatibility** - Large feature scopes may exceed practical AutoBuild turn limits

## Observed Issues

### FEAT-GR-MVP Analysis
- Worktree contains 1686+ markdown files
- Multiple nested features and archived tasks
- Scope expanded beyond original intent

### FEAT-0F4A (if applicable)
- Similar scope expansion pattern suspected
- Task count exceeding sensible breakdown

## Review Scope

Analyze and recommend changes to:

### 1. Feature Scope Limits in `/feature-plan`

**Questions to Answer:**
- What is a sensible maximum task count per feature? (Proposed: 5-10 tasks)
- Should features be auto-split when exceeding thresholds?
- How should complexity interact with task count limits?
- Should wave count have a maximum (e.g., 3 waves)?

**Recommendations Format:**
- Hard limits vs soft warnings
- Configuration options (.claude/settings.json)
- Automatic feature splitting heuristics

### 2. Iterative Implementation Support in `/task-review`

**Current [I]mplement Behavior:**
- Creates all subtasks at once
- Generates single YAML feature file
- No built-in verification checkpoints

**Proposed Improvements:**
- **Phased [I]mplement**: Create first wave only, verify, then continue
- **Checkpoint gates**: Require verification between waves
- **Incremental feature files**: Update YAML as waves complete

### 3. Default Feature File Generation

**Current State:**
- `/task-review [I]mplement` creates task markdown files
- Feature YAML generation requires manual `generate-feature-yaml` script call (or --no-structured to skip)

**Proposed Change:**
- `/task-review [I]mplement` should **always** generate `.guardkit/features/FEAT-XXX.yaml` by default
- This enables immediate `/feature-build` compatibility
- Consistent with `/feature-plan` behavior

### 4. AutoBuild Integration Considerations

**Questions:**
- How do scope limits interact with `/feature-build` turn limits?
- Should feature complexity influence max-turns default?
- What's the optimal task count for autonomous execution?

## Acceptance Criteria

1. **Scope Limit Recommendations**: Clear thresholds for task count, wave count, and complexity
2. **Workflow Improvements**: Specific changes to `/feature-plan` and `/task-review` commands
3. **Feature File Default**: Recommendation on making feature YAML generation default
4. **Implementation Priority**: Which changes provide highest value for iterative workflow

## Decision Options (Expected from Review)

After analysis, present options such as:

- **Option A**: Strict limits (max 7 tasks, max 3 waves, auto-split required)
- **Option B**: Soft limits with warnings (thresholds with override flags)
- **Option C**: Iterative-first mode (wave-by-wave implementation with gates)
- **Option D**: Combination approach

## Success Metrics

- Features stay within manageable scope (5-10 tasks typical)
- Iterative verification possible between waves
- AutoBuild can complete features within reasonable turn counts
- Reduced debugging surface area when issues arise

## Notes

This review directly addresses the core principle: "I like to work iteratively and then test/verify the work done before moving on to keep the surface area/scope of the changes workable such that when there is an issue we can sensibly diagnose it."

---

## Next Steps After Review

1. Execute: `/task-review TASK-REV-BAF6 --mode=decision --depth=standard`
2. At decision checkpoint, choose [I]mplement to generate improvement tasks
3. Implement changes in manageable waves with verification between each
