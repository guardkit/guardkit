---
id: TASK-REV-0614
title: "Review clarifying questions regression in feature-plan command"
status: review_complete
created: 2025-12-13T16:15:00Z
updated: 2025-12-13T16:30:00Z
priority: high
tags: [clarifying-questions, feature-plan, regression, ux, bug]
complexity: 6
task_type: review
review_mode: technical-debt
review_depth: standard
review_results:
  mode: technical-debt
  depth: standard
  findings_count: 5
  recommendations_count: 4
  root_cause: "Clarification module exists but not integrated with task_review_orchestrator.py"
  report_path: .claude/reviews/TASK-REV-0614-review-report.md
  completed_at: 2025-12-13T16:30:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review clarifying questions regression in feature-plan command

## Problem Statement

When running `/feature-plan` with an ambiguous feature description like "lets create the base application infrastructure", the system should ask clarifying questions (Context A: Review Scope Clarification) **before** executing the analysis. Instead, the system proceeds directly with assumptions:

### Evidence from Test

**Input:** `/feature-plan lets create the base application infrastructure`

**Expected Behavior (per feature-plan.md documentation):**
1. Create review task automatically
2. **Ask Context A clarification questions** (focus, depth, trade-offs)
3. Execute analysis based on clarified scope
4. Present decision checkpoint

**Actual Behavior (from user test):**
1. Created review task: `TASK-REV-07FC`
2. **Skipped clarification questions entirely**
3. Assumed FastAPI without asking (major assumption)
4. Proceeded directly to full technical analysis
5. Never asked user to clarify:
   - What technology stack?
   - What kind of application?
   - What are the priorities?
   - What scope/depth is expected?

### Documentation Gap

From `/feature-plan.md` (lines 64-75):
```markdown
### Context A: Review Scope Clarification

**When**: During Step 2 (Execute Task Review), before analysis begins.

**Gating**: Context A triggers for decision mode tasks (which feature-plan uses)
unless `--no-questions` is specified.
```

The documentation clearly states clarification should trigger for decision mode tasks, but it didn't.

## Review Objectives

1. **Root Cause Analysis**: Why did clarifying questions fail to trigger?
   - Is complexity scoring not applied to feature-plan created tasks?
   - Is the clarification gating logic not integrated with feature-plan orchestration?
   - Is task-review skipping Context A when called from feature-plan?

2. **Gap Identification**: What's missing in the implementation?
   - Check if `lib/clarification/` modules are integrated with task-review
   - Verify feature-plan properly propagates clarification flags
   - Check if complexity is being calculated for review tasks

3. **UAT Scenario Validation**: Compare against UAT Scenario 4
   - Scenario 4 specifically tests feature-plan with clarification
   - This test case should have triggered Context A questions
   - Validate the documented workflow matches implementation

4. **Ambiguity Detection**: Should there be additional detection?
   - The input "lets create the base application infrastructure" is highly ambiguous
   - No technology stack specified
   - No application type specified
   - System made major assumptions (FastAPI) without verification

## Scope

### In Scope
- Review clarification integration with feature-plan workflow
- Review task-review Context A gating logic
- Review complexity scoring for auto-created review tasks
- Identify implementation gaps
- Recommend fixes

### Out of Scope
- Full implementation of fixes (that will be a separate task-work task)
- Changes to other commands (task-work, task-create)
- Performance optimization

## Review Focus Areas

### 1. Clarification Module Integration
- [ ] Check if `lib/clarification/` modules exist and are complete
- [ ] Verify `generate_review_questions()` is being called
- [ ] Check `display_questions_full()` integration

### 2. Feature-Plan Orchestration
- [ ] Review `installer/core/commands/feature-plan.md` execution flow
- [ ] Check flag propagation to task-review
- [ ] Verify decision mode triggers clarification

### 3. Task-Review Gating Logic
- [ ] Review Phase 1 clarification trigger conditions
- [ ] Check complexity-based gating rules
- [ ] Verify `--no-questions` isn't being applied incorrectly

### 4. Complexity Scoring
- [ ] Check if auto-created review tasks get complexity assigned
- [ ] Verify complexity >=4 for decision mode triggers Context A
- [ ] Review default complexity for feature-plan tasks

## Acceptance Criteria

- [ ] Root cause identified and documented
- [ ] Gap analysis completed
- [ ] Implementation recommendations provided
- [ ] Priority assessment for fix
- [ ] Test cases for regression prevention

## Test Evidence Location

See: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/reviews/clarifying-questions/feature-plan-test.md`

This file contains the full output from the test where clarifying questions should have been asked but weren't.

## Related Documentation

- [feature-plan.md](installer/core/commands/feature-plan.md) - Command specification with clarification flow
- [task-review.md](installer/core/commands/task-review.md) - Review command with Context A/B clarification
- [clarification-uat-scenarios.md](docs/testing/clarification-uat-scenarios.md) - UAT Scenario 4
- [CLAUDE.md](CLAUDE.md) - Clarifying Questions section

## Related Tasks

- `tasks/backlog/TASK-REV-PD01-clarifying-questions-regression-risk-analysis.md` - Prior regression risk analysis
- Clarifying Questions feature implementation (completed)

## Implementation Notes

This is a review task. After review completion, choose:
- **[I]mplement** to create implementation tasks for the fix
- **[A]ccept** if this is a documentation issue only
- **[R]evise** if deeper analysis needed

## Review Execution Log

**Executed**: 2025-12-13T16:30:00Z
**Mode**: technical-debt
**Depth**: standard

### Findings Summary

1. **TD-001**: Clarification module not integrated with orchestrator (Critical)
2. **TD-002**: Tests mock workflow instead of testing real code (High)
3. **TD-003**: Documentation-reality mismatch (High)
4. **TD-004**: `should_clarify()` exists but unused (Medium)
5. **TD-005**: Feature-plan relies on markdown interpretation only (Medium)

### Root Cause

The clarification module (`lib/clarification/`) is complete and passes unit tests, but `task_review_orchestrator.py` never imports or calls any clarification functions.

### Decision

**[I]mplement** - Created 4 implementation subtasks in `tasks/backlog/clarifying-questions-fix/`

### Implementation Tasks Created

| Task | Priority | Description |
|------|----------|-------------|
| TASK-CLQ-FIX-001 | Critical | Integrate clarification into task-review orchestrator |
| TASK-CLQ-FIX-002 | High | Create feature-plan Python orchestrator |
| TASK-CLQ-FIX-003 | Medium | Update integration tests |
| TASK-CLQ-FIX-004 | Medium | Add end-to-end smoke test |

**Estimated Fix Time**: 6-9 hours (1-1.5 days)

### Full Report

See: [.claude/reviews/TASK-REV-0614-review-report.md](.claude/reviews/TASK-REV-0614-review-report.md)
