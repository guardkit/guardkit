---
id: TASK-REV-fb03
title: Analyze Task-Work Delegation Regression in Feature-Build
status: completed
task_type: review
created: 2026-01-10T09:00:00Z
updated: 2026-01-10T11:15:00Z
priority: critical
tags: [feature-build, autobuild, regression, task-work-delegation, critical-bug]
complexity: 7
review_mode: decision
review_depth: comprehensive
evidence_files:
  - docs/reviews/feature-build/complete_failure.md
  - docs/reviews/feature-build/feature_build_output_following_fixes.md
related_tasks:
  - TASK-FB-DEL1 (completed - caused regression)
  - TASK-REV-fb02 (previous review)
  - TASK-FB-RPT1 (completed)
  - TASK-FB-PATH1 (completed)
review_results:
  mode: decision
  depth: comprehensive
  score: 95
  findings_count: 5
  recommendations_count: 4
  decision: option_b_sdk_delegation
  report_path: .claude/reviews/TASK-REV-fb03-review-report.md
  completed_at: 2026-01-10T10:30:00Z
  root_cause: "Missing CLI command - guardkit task-work does not exist"
implementation_decision:
  choice: "[I]mplement"
  selected_option: "Option B - SDK-based delegation"
  implementation_tasks:
    - TASK-SDK-001
    - TASK-SDK-002
    - TASK-SDK-003
    - TASK-SDK-004
  feature_folder: tasks/backlog/sdk-delegation-fix/
  decided_at: 2026-01-10T11:15:00Z
---

# Analyze Task-Work Delegation Regression in Feature-Build

## Problem Statement

After enabling task-work delegation (TASK-FB-DEL1), feature-build now **completely fails** - a regression from the previous state where at least Turn 5 succeeded.

### Before TASK-FB-DEL1 (Previous Behavior)
- Invocation method: "via **direct SDK**"
- Turn 5: ✓ success - "6 files created, 1 modified, 1 tests (passing)"
- Issue: task_work_results.json not found (but implementation worked)

### After TASK-FB-DEL1 (Current Behavior - REGRESSION)
- Invocation method: "via **task-work delegation**"
- ALL turns (1-5): ✗ error - "Player failed - attempting state recovery"
- Issue: Complete failure, NO successful turns

## Evidence

### Critical Log Lines (complete_failure.md)

```
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via task-work delegation for TASK-INFRA-001 (turn 1)
```

This confirms TASK-FB-DEL1 fix is active. Then **every turn fails**:

```
│ 1      │ Player Implementation     │ ✗ error      │ Player failed - attempting state recovery │
│ 2      │ Player Implementation     │ ✗ error      │ Player failed - attempting state recovery │
│ 3      │ Player Implementation     │ ✗ error      │ Player failed - attempting state recovery │
│ 4      │ Player Implementation     │ ✗ error      │ Player failed - attempting state recovery │
│ 5      │ Player Implementation     │ ✗ error      │ Player failed - attempting state recovery │
```

**Result**: MAX_TURNS_EXCEEDED with 0 progress (vs previous 6 files created on Turn 5)

### Comparison Table

| Metric | Before TASK-FB-DEL1 | After TASK-FB-DEL1 |
|--------|---------------------|-------------------|
| Invocation Method | "via direct SDK" | "via task-work delegation" |
| Turn 1 | ✗ error (state recovered) | ✗ error |
| Turn 5 | ✓ success (6 files, 1 test) | ✗ error |
| Files Created | 6 | 0 |
| Tests Passing | 1 | 0 |
| task_work_results.json | Not found | Not found |
| Overall Outcome | Partial success | **Complete failure** |

## Root Cause Hypothesis

TASK-FB-DEL1 changed the invocation path from direct SDK to task-work delegation:

```python
# Before (direct SDK - working)
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via direct SDK for TASK-INFRA-001

# After (task-work delegation - broken)
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via task-work delegation for TASK-INFRA-001
```

Possible issues with the delegation path:

### H1: Skill Tool Not Available in Context
- Task-work delegation uses the Skill tool to invoke `/task-work`
- The Skill tool may not be available when running from Python orchestrator
- Direct SDK worked because it bypassed the Skill layer

### H2: CWD/Path Issues in Delegation
- task-work delegation runs in a different context
- Working directory may not be the worktree
- task_work_results.json written to wrong location

### H3: Missing System Prompt/Context
- task-work --implement-only expects certain state
- Delegation doesn't pass required context
- Skill invocation fails silently

### H4: Error Not Captured
- Delegation errors may be swallowed
- No clear error message in logs about WHY Player failed
- Need to examine what happens after "Invoking Player via task-work delegation"

## Questions to Answer

### Q1: What error occurs during task-work delegation?
The logs show "Player failed - attempting state recovery" but don't show the actual error. Need to find:
- What exception is raised?
- Is the Skill tool even being invoked?
- Is task-work --implement-only running at all?

### Q2: Why did direct SDK work (partially) while delegation fails completely?
- Direct SDK: Player completed implementation on Turn 5
- Delegation: Player fails immediately on all turns
- What's fundamentally different about the execution paths?

### Q3: Was the delegation implementation tested?
TASK-FB-DEL1 completion notes mention "All 41 tests passing" but:
- Were tests actually exercising the delegation path?
- Were tests mocked in a way that hid the issue?
- Is there an integration test gap?

### Q4: Is there a configuration cascade issue?
- Does delegation require additional configuration?
- Are all required parameters being passed through?
- Is the worktree path being correctly propagated?

## Scope of Review

### Must Investigate

1. **AgentInvoker code changes**: What did TASK-FB-DEL1 actually change?
2. **Error capture**: Why don't we see the actual error?
3. **Execution path diff**: What's different between direct SDK and delegation?
4. **Test coverage**: Were the delegation tests adequate?

### Files to Examine

| File | Purpose |
|------|---------|
| `guardkit/orchestrator/agent_invoker.py` | Check delegation implementation (TASK-FB-DEL1 changes) |
| `guardkit/orchestrator/autobuild.py` | Check how invoker is called |
| `tests/unit/test_agent_invoker.py` | Check test coverage for delegation |
| `tasks/completed/TASK-FB-DEL1/` | Review what was implemented |

## Recommended Actions

### Immediate (Regression Fix)
1. **Revert TASK-FB-DEL1** if delegation fundamentally broken
2. **OR** Fix delegation implementation if issue is identifiable

### Root Cause Analysis
1. Add detailed logging to delegation path
2. Capture and log actual exception when Player fails
3. Trace execution path from invoker through to task-work

### Prevention
1. Integration test for delegation (not just unit test with mocks)
2. End-to-end test before marking delegation fix complete

## Success Criteria

- [ ] Root cause of regression identified
- [ ] Clear action plan: fix delegation OR revert to direct SDK
- [ ] Recommendation on whether delegation approach is viable
- [ ] If proceeding with delegation: specific fixes identified

## Severity Assessment

**CRITICAL** - This is a regression that makes feature-build completely unusable:
- Previous state: Partial success (Turn 5 worked)
- Current state: Complete failure (all turns fail)
- Feature-build is now worse than before the "fix"

## Notes

This review has **higher priority than TASK-REV-fb02** because:
1. TASK-REV-fb02 was about task_work_results.json not found (nuisance)
2. This review is about complete execution failure (blocking)

The system was making progress before (files created, tests passing on Turn 5). Now it makes no progress at all.
