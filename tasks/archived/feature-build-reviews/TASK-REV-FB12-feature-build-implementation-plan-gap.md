---
id: TASK-REV-FB12
title: Review feature-build human checkpoint blocking issue
status: review_complete
created: 2026-01-13T16:00:00Z
updated: 2026-01-14T16:15:00Z
priority: critical
tags: [feature-build, architecture-review, human-checkpoint, phase-2.8, security-trigger]
task_type: review
complexity: 7
previous_reviews: [TASK-REV-FB01, TASK-REV-FB02, TASK-REV-FB03, TASK-REV-FB04, TASK-REV-FB05, TASK-REV-FB06, TASK-REV-FB07, TASK-REV-FB08, TASK-REV-FB09, TASK-REV-FB10, TASK-REV-FB11]
review_results:
  findings_count: 7
  recommendations_count: 6
  report_path: .claude/reviews/TASK-REV-FB12-review-report.md
  implementation_task: TASK-FB-FIX-019
  decision: implement
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Review: Feature-Build Human Checkpoint Blocking Issue

## CRITICAL FINDING (Updated 2026-01-13T16:30:00Z)

**ROOT CAUSE IDENTIFIED**: The Phase 2.8 human checkpoint is triggered by security keywords (secret_key, JWT, algorithm) in the task content. When running via SDK automation, there is **no human to respond to the checkpoint**, causing the session to hang indefinitely until timeout.

### Evidence from Manual Test

From `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/reviews/feature-build/RE-FB12_stand_alone_manual_design.md`:

```
Phase 2.7 (Complexity Evaluation):
  Complexity Score: 2/10 (Low)
  Force-Review Trigger: ACTIVE
  - Security keywords (secret_key, JWT, algorithm) detected
  Final Decision: FULL_REQUIRED (Phase 2.6 Checkpoint mandatory)

Phase 2.8 (Checkpoint):
  OPTIONS:
    [A]pprove  - Proceed with current plan
    [M]odify   - Edit plan before implementation
    [V]iew     - Show complete plan in pager
    [C]ancel   - Cancel task, return to backlog

  Your choice [A/M/V/C]:

  User answered Claude's questions:
    · Do you approve this implementation plan for TASK-INFRA-001? → Approve
```

**Total time for manual design-only**: 46 minutes (with human approval at checkpoint)

### The Blocking Mechanism

1. **Complexity Evaluator** (Phase 2.7) detects security keywords in task content
2. **Force-Review Trigger** activates, overriding the low complexity score (2/10)
3. **Review Mode** set to `FULL_REQUIRED` instead of `AUTO_PROCEED`
4. **Phase 2.8 Checkpoint** presents interactive options requiring human input
5. **SDK Session** hangs waiting for input that never comes
6. **Timeout** occurs after 600-7200 seconds depending on configuration

### Why This Wasn't Caught Earlier

- Previous reviews focused on SDK timeout propagation and path issues
- The human checkpoint only activates when force-review triggers are present
- Test tasks without security keywords would auto-proceed
- Manual testing always had a human present to approve

## Background

This is a continuation of the feature-build timeout investigation series (FB01-FB11). Previous reviews identified and fixed:

- SDK timeout propagation (FB-FIX-009)
- Task artifact path centralization (FB-FIX-003)
- Pre-loop decision logic (FB-FIX-015, FB-FIX-016, FB-FIX-017)

Despite documentation-level fixes per TASK-REV-FB11 recommendations, feature-build is **still failing**.

## Evidence Files

- **Primary**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/reviews/feature-build/feature_build_following_fixes_to_docs.md`
- **Previous Review**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/.claude/reviews/TASK-REV-FB11-review-report.md`
- **Manual Design Test**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/reviews/feature-build/stand_alone_manual_design.md`

## Observed Failure Mode

### Scenario 1: Pre-Loop Disabled (Default for Feature-Build)

When `enable_pre_loop=False` (the new default per FB11 recommendations):

```
ERROR:guardkit.orchestrator.agent_invoker:Implementation plan not found for TASK-INFRA-001
Expected at:
  - .guardkit/worktrees/FEAT-3DEB/.claude/task-plans/TASK-INFRA-001-implementation-plan.md
  - .guardkit/worktrees/FEAT-3DEB/docs/state/TASK-INFRA-001/implementation_plan.md
```

**Root Cause**: The Player agent invokes `/task-work --implement-only` which **requires** an implementation plan to exist. When pre-loop is disabled, no plan is created, causing immediate failure.

### Scenario 2: Pre-Loop Enabled

When `--enable-pre-loop` is used, the design phase runs but still times out (~90 minutes for complexity 3/10 task).

**Root Cause**: As identified in FB11, the design phase generates extensive artifacts (1200+ lines across multiple files) regardless of task complexity.

## Critical Architecture Gap

The current architecture has a **circular dependency**:

```
Without Pre-Loop:
  ├── Player calls /task-work --implement-only
  ├── --implement-only REQUIRES implementation plan
  └── No plan exists → FAILURE

With Pre-Loop:
  ├── Design phase creates implementation plan
  ├── Takes 60-90 minutes per task
  └── Timeout or excessive duration → FAILURE
```

## Questions to Investigate

### Q1: Why does Player require implementation plans?

The agent_invoker is checking for implementation plans before delegating to task-work. Is this check necessary? What happens if we skip it?

**File to examine**: `guardkit/orchestrator/agent_invoker.py`

### Q2: What is the Player actually supposed to do?

When pre-loop is disabled for feature-build (because tasks already have detailed specs from /feature-plan), what workflow should the Player follow?

Options:
- A) Implement directly from task acceptance criteria (no plan needed)
- B) Generate a lightweight plan inline during implementation
- C) Require plans to be pre-generated during /feature-plan

### Q3: Is the --implement-only flag appropriate?

The logs show `/task-work --implement-only` being invoked. Should feature-build use a different mode?

**File to examine**: `guardkit/orchestrator/quality_gates/task_work_interface.py`

### Q4: Can /task-work work without --design-only or --implement-only?

Running `/task-work TASK-XXX` (no flags) should execute all phases 2-5.5 including design. Is this a viable alternative?

### Q5: Was the standalone manual design working?

Per `stand_alone_manual_design.md`, running `/task-work TASK-INFRA-001 --design-only` manually worked and produced implementation plans. Why doesn't feature-build achieve the same result?

## Acceptance Criteria

- [ ] Root cause identified with code references
- [ ] Architecture decision: how should feature-build handle implementation plans?
- [ ] Recommended fix with effort estimate
- [ ] Test plan for validating fix
- [ ] Updated documentation requirements

## Recommended Review Approach

1. **Code Trace**: Follow execution path from feature-build → autobuild → agent_invoker → task_work_interface
2. **Compare Flows**: Manual `/task-work --design-only` vs automated feature-build pre-loop
3. **Identify Gap**: Where does the working manual flow diverge from automated flow?
4. **Design Decision**: Propose architecture change to resolve circular dependency

## Related Tasks

| Task ID | Description | Status |
|---------|-------------|--------|
| TASK-FB-FIX-015 | Default enable_pre_loop=false for feature-build | Completed |
| TASK-FB-FIX-016 | Increase default SDK timeout to 1800s | Completed |
| TASK-FB-FIX-017 | Update CLAUDE.md with pre-loop guidance | Completed |

## Notes

The user mentioned they could run `/task-work --design-only` independently as a diagnostic step, which was the "smoking gun" in previous investigations. Consider requesting this test if code review doesn't reveal the issue.

---

## UPDATED ANALYSIS (2026-01-13T16:30:00Z)

### New Evidence File

- **Standalone Design Test**: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/reviews/feature-build/RE-FB12_stand_alone_manual_design.md`

### Root Cause: Human Checkpoint in Automated Workflow

The manual `/task-work TASK-INFRA-001 --design-only` test revealed that Phase 2.8 presents an **interactive human checkpoint** when:
1. Security keywords are detected (secret_key, JWT, algorithm)
2. The complexity evaluator sets `review_mode: FULL_REQUIRED`

When feature-build runs via SDK, this checkpoint **blocks indefinitely** waiting for human input.

### Proposed Solutions

#### Option A: Auto-Approve in Automated Mode (Recommended)

Add an `--auto-approve` or `--non-interactive` flag that:
- Skips Phase 2.8 human checkpoint
- Auto-approves when complexity ≤ 6 (regardless of force-triggers)
- Logs the decision for audit trail

**Implementation**:
```python
# In task_work_interface.py or agent_invoker.py
if self.non_interactive and complexity_score <= 6:
    logger.info(f"Auto-approving design (non-interactive mode, complexity={complexity_score})")
    # Skip checkpoint, proceed to implementation
```

**Effort**: 2-4 hours

#### Option B: Disable Force-Triggers for Feature-Build

When `enable_pre_loop=True` for feature-build, disable security keyword force-triggers since:
- Tasks come from `/feature-plan` which already did architectural review
- The parent review task validated security considerations
- Feature-build is meant to be autonomous

**Implementation**:
```python
# In complexity evaluator or pre-loop
if context.is_feature_build:
    force_review_triggers = []  # Disable all triggers
```

**Effort**: 1-2 hours

#### Option C: Pre-Approve During Feature-Plan

Generate implementation plans during `/feature-plan` so they're already approved when feature-build runs.

**Pros**: Clean separation of concerns
**Cons**: Significant refactoring, longer feature-plan duration

**Effort**: 8-16 hours

#### Option D: Clarifying Questions Handler for SDK

Implement a callback mechanism in the SDK invocation that can:
- Detect clarifying question prompts
- Auto-respond based on predefined rules
- Or reject tasks that require human input

**Effort**: 4-8 hours (requires SDK integration work)

### Recommended Approach

**Option A + B Combined**:
1. Add `--non-interactive` flag to task-work (Option A)
2. Feature-build sets this flag automatically
3. Disable force-review triggers for feature-build tasks (Option B)
4. Log all auto-approval decisions for audit

This maintains safety for manual task-work while enabling autonomous feature-build.

### Test Plan

1. Create test task with security keywords (JWT, secret_key)
2. Run feature-build with `--enable-pre-loop`
3. Verify Phase 2.8 is skipped or auto-approved
4. Verify implementation proceeds without hanging
5. Check audit log for auto-approval entry

### Files to Modify

| File | Change |
|------|--------|
| `guardkit/orchestrator/agent_invoker.py` | Add non-interactive mode |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | Pass non-interactive flag to SDK |
| `guardkit/orchestrator/quality_gates/pre_loop.py` | Disable force-triggers for feature-build |
| `installer/core/commands/task-work.md` | Document --non-interactive flag |
| `installer/core/commands/feature-build.md` | Update SDK invocation docs |

### Acceptance Criteria (Updated)

- [x] Root cause identified: Phase 2.8 checkpoint blocks SDK sessions
- [ ] Architecture decision: Auto-approve in non-interactive mode
- [ ] Implementation: Add --non-interactive flag
- [ ] Feature-build: Automatically uses non-interactive mode
- [ ] Test: Verify security-keyword tasks complete autonomously
- [ ] Documentation: Update both commands
