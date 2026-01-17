---
id: TASK-REV-FB13
title: Analyze feature-build pre-loop architecture regression - implementation plan generation
status: review_complete
created: 2026-01-14T19:30:00Z
updated: 2026-01-14T20:30:00Z
priority: critical
decision: implement
decision_date: 2026-01-14T20:30:00Z
implementation_task: TASK-FB-FIX-b41d
tags:
  - feature-build
  - architecture-review
  - pre-loop
  - implementation-plan
  - regression-analysis
task_type: review
complexity: 7
decision_required: true
parent_context:
  - TASK-REV-FB01
  - TASK-REV-FB02
  - TASK-REV-FB03
  - TASK-REV-FB04
  - TASK-REV-FB05
  - TASK-REV-FB07
  - TASK-REV-FB08
  - TASK-REV-FB09
  - TASK-REV-FB10
  - TASK-REV-FB11
  - TASK-REV-FB12
  - TASK-REV-FE8A
  - TASK-FB-FIX-015
  - TASK-FB-FIX-019
review_scope:
  - guardkit/orchestrator/quality_gates/pre_loop.py
  - guardkit/orchestrator/quality_gates/task_work_interface.py
  - guardkit/orchestrator/feature_orchestrator.py
  - guardkit/orchestrator/autobuild.py
  - installer/core/commands/task-work.md
  - installer/core/commands/feature-build.md
---

# Review Task: Analyze Feature-Build Pre-Loop Architecture Regression

## Problem Statement

Following the implementation of TASK-FB-FIX-019, `/feature-build` fails with:

```
QualityGateBlocked: Design phase did not return plan path
```

**User's Concern**: The recent bug fixes (particularly TASK-FB-FIX-015) may have fundamentally broken the architecture by:
1. Disabling pre-loop by default for feature-build (`enable_pre_loop=False`)
2. But still expecting an implementation plan for the Player-Coach loops

**User's Original Intent**: The feature-build command should:
1. Run `/task-work TASK-XXX --design-only` to generate an implementation plan
2. Run `/task-work TASK-XXX --implement-only` using the approved plan in the Player-Coach loop

**Current Behavior**: With `enable_pre_loop=False` (introduced by TASK-FB-FIX-015):
- No implementation plan is generated
- Player-Coach loop attempts to run WITHOUT a plan
- System fails when trying to extract the non-existent plan

## Review Objectives

1. **Architectural Analysis**: Determine if TASK-FB-FIX-015 introduced a fundamental regression
2. **Design Intent Validation**: Clarify the intended architecture for feature-build
3. **Historical Context**: Review all FB reviews (FB01-FB12, FE8A) for context
4. **Root Cause Identification**: Identify whether the issue is:
   - A) `enable_pre_loop=False` is wrong for feature-build
   - B) Feature-build should use `--design-only` + `--implement-only` workflow
   - C) Player-Coach loop should work without an implementation plan
   - D) Plans should come from a different source (e.g., feature-plan output)

## Key Questions to Answer

### Q1: What was the original design intent?

According to the user, the intended flow was:
```
/feature-build TASK-XXX
  ├── Step 1: /task-work TASK-XXX --design-only → generates implementation plan
  ├── Step 2: Human approves (or auto-approves in SDK mode)
  └── Step 3: Player-Coach loop uses the approved plan for implementation
```

Is this accurate based on the documentation and reviews?

### Q2: What did TASK-FB-FIX-015 change?

TASK-FB-FIX-015 changed `_resolve_enable_pre_loop()` to return `False` by default for feature-build.

**Rationale given**: Feature tasks from `/feature-plan` already have detailed specs, so pre-loop duplicates work.

**User's counter-argument**: The feature-plan output is NOT the same as an implementation plan from `/task-work --design-only`:
- Feature-plan: High-level acceptance criteria and task breakdown
- Task-work design phase: Detailed implementation plan with file list, LOC estimates, test strategy

### Q3: Did reviews FB01-FB12 and FE8A recommend this approach?

Review the specific recommendations from each review:
- TASK-REV-FB11: Recommended "skip pre-loop for well-defined feature-build tasks"
- TASK-REV-FE8A: Found "FB-FIX-015, 016, 017 were NOT implemented"
- TASK-REV-FB12: Identified regex pattern issues for plan path extraction

Did any review recommend keeping pre-loop disabled without providing an alternative plan source?

### Q4: What does the Player-Coach loop actually need?

Analyze `guardkit/orchestrator/autobuild.py` and the Player agent:
- Does the Player agent REQUIRE an implementation plan?
- Can it work with just task acceptance criteria?
- What context does it actually use?

### Q5: What is the correct architectural fix?

Options to evaluate:
1. **Revert TASK-FB-FIX-015**: Re-enable pre-loop for feature-build
2. **Alternative plan source**: Use feature-plan output as the "plan" for Player
3. **Design-first workflow**: Feature-build should call `--design-only` then `--implement-only`
4. **No plan needed**: Modify Player to work without implementation plan

## Evidence to Examine

### Prior Reviews
- `.claude/reviews/TASK-REV-FB01-review-report.md` through `TASK-REV-FB12-review-report.md`
- `.claude/reviews/TASK-REV-FE8A-review-report.md`

### Implementation Files
- `guardkit/orchestrator/quality_gates/pre_loop.py` - Pre-loop execution and plan validation
- `guardkit/orchestrator/quality_gates/task_work_interface.py` - SDK delegation to task-work
- `guardkit/orchestrator/feature_orchestrator.py` - Feature orchestration with `enable_pre_loop` cascade
- `guardkit/orchestrator/autobuild.py` - AutoBuild orchestrator and Player-Coach loop

### Command Specifications
- `installer/core/commands/task-work.md` - Design-only/implement-only workflow
- `installer/core/commands/feature-build.md` - Feature-build intended workflow

### Recent Fixes
- `tasks/completed/TASK-FB-FIX-015/` - The contentious pre-loop default change
- `tasks/completed/TASK-FB-FIX-019/` - Plan path extraction and auto-approve checkpoint

## Acceptance Criteria

- [ ] Clear determination of whether TASK-FB-FIX-015 introduced a regression
- [ ] Documented architectural intent for feature-build pre-loop behavior
- [ ] Specific recommendation with implementation approach
- [ ] Risk assessment for each option
- [ ] Test plan to verify the fix

## Review Output

This review should produce:
1. Architecture analysis document
2. Decision matrix for options
3. Recommended fix with implementation task(s)
4. Verification test plan

## User Context

The user explicitly stated:
> "My opinion is that we need to run task-work with the design flag and then run the loop using task-work with the flag implementation only - that was my core idea and approach but this was unwound by recent bug fix attempts"

This opinion should be validated or refuted with evidence from the codebase and reviews.

## Next Steps

After this review completes:
1. If regression confirmed → Create implementation task to fix
2. If design intent unclear → Create ADR to document decision
3. If user's approach validated → Implement design-first workflow for feature-build
