---
id: TASK-REV-FB09
title: Analyze task_work_results.json Not Found After TASK-FB-FIX-009/010/011
status: review_complete
task_type: review
created: 2026-01-12T10:30:00Z
updated: 2026-01-12T14:30:00Z
priority: critical
tags: [feature-build, autobuild, debugging, task-work-results, coach-validator]
complexity: 6
review_mode: architectural
review_depth: comprehensive
decision_required: true
review_results:
  mode: architectural
  depth: comprehensive
  score: 45
  findings_count: 5
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-FB09-review-report.md
  completed_at: 2026-01-12T14:30:00Z
  root_cause: "_write_task_work_results() method exists but is never called in _invoke_task_work_implement() flow"
  architecture_score: 45
  solid_score: 55
  dry_score: 60
  yagni_score: 70
implementation_decision:
  choice: "[I]mplement"
  decided_at: 2026-01-12T14:45:00Z
  implementation_tasks:
    - TASK-FB-FIX-012
  task_location: tasks/backlog/TASK-FB-FIX-012-integrate-results-writer.md
---

# Review Task: Analyze task_work_results.json Not Found After Recent Fixes

## Problem Statement

After implementing TASK-FB-FIX-009 (sdk_timeout propagation), TASK-FB-FIX-010 (enable_pre_loop cascade), and TASK-FB-FIX-011 (config propagation tests), the feature-build command now successfully completes the pre-loop design phase (implementation plan is found), but the Player-Coach loop fails because `task_work_results.json` is not being created by the Player's task-work invocation.

**Key Progress Achieved:**
- ✅ Pre-loop design phase completes successfully (24 turns)
- ✅ Implementation plan found at `docs/state/TASK-INFRA-001/implementation_plan.md`
- ✅ SDK timeout properly propagated (1800s)
- ❌ Coach validation fails: "Task-work results not found"

## Evidence from Feature-Build Output

Source: `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/reviews/feature-build/feature_build_after_FB08.md`

### Pre-Loop Success

```
INFO:guardkit.orchestrator.quality_gates.pre_loop:Pre-loop validated plan exists at:
    /Users/.../worktrees/FEAT-3DEB/docs/state/TASK-INFRA-001/implementation_plan.md
INFO:guardkit.orchestrator.quality_gates.pre_loop:Pre-loop results extracted: complexity=3, max_turns=3, arch_score=80
INFO:guardkit.orchestrator.autobuild:Pre-loop complete: complexity=3, max_turns=3, checkpoint_passed=True
```

### Player-Coach Loop Failure

```
INFO:guardkit.orchestrator.agent_invoker:task-work completed successfully for TASK-INFRA-001
INFO:guardkit.orchestrator.agent_invoker:task_work_results.json not found, detecting git changes for TASK-INFRA-001
WARNING:guardkit.orchestrator.quality_gates.coach_validator:Task-work results not found at
    /Users/.../worktrees/FEAT-3DEB/.guardkit/autobuild/TASK-INFRA-001/task_work_results.json
```

This pattern repeats for all 3 turns, resulting in MAX_TURNS_EXCEEDED.

## Historical Context

### Review Timeline (TASK-REV-FB01 to FB08)

| Review | Issue | Fix Applied | Status |
|--------|-------|-------------|--------|
| FB01 | Initial architecture review | N/A (approved) | ✅ |
| FB02 | Task-work delegation disabled | TASK-FB-DEL1: Enable delegation | ✅ |
| FB04 | Mock data returned, no SDK invocation | TASK-FB-FIX-001: Replace subprocess with SDK | ✅ |
| FB05 | Message parsing bug (ContentBlock) | TASK-FB-FIX-005: Fix ContentBlock extraction | ✅ |
| FB07 | Path resolution bug (relative vs absolute) | TASK-FB-FIX-007: Fix pre-loop path resolution | ✅ |
| FB08 | SDK timeout not propagating | TASK-FB-FIX-009/010/011: Fix config cascade | ✅ |

### Current State

The pre-loop design phase is now fully functional. The issue has shifted to the Player-Coach loop:
- Player invokes `/task-work TASK-XXX --implement-only --mode=tdd`
- Task-work completes successfully (creates files, runs tests)
- But `task_work_results.json` is NOT being written
- Coach validator cannot find results → provides feedback → loops indefinitely

## Hypotheses to Investigate

### H1: task-work Skill Does Not Write task_work_results.json

The `/task-work` skill may not be configured to write `task_work_results.json` after implementation.

**Check:**
- Does `installer/core/commands/task-work.md` specify writing `task_work_results.json`?
- Is there a results writer in the task-work command implementation?

### H2: Results Written to Wrong Location

The results file may be written to a different path than where Coach is looking.

**Check:**
- Coach looks at: `.guardkit/autobuild/{task_id}/task_work_results.json`
- Does task-work write to a different location (e.g., `docs/state/{task_id}/`)?

### H3: Results Writer Not Triggered for --implement-only

The results writer may only be triggered for full task-work execution, not `--implement-only` mode.

**Check:**
- Are there different code paths for `--design-only` vs `--implement-only`?
- Is the results writer gated behind a condition?

### H4: SDK Context Issue

The SDK invocation may not provide the correct context for the skill to write results.

**Check:**
- What permissions and tools are allowed in the SDK invocation?
- Is the worktree path correctly passed as CWD?

### H5: Delegation Mode Not Writing Results

Even with task-work delegation enabled (TASK-FB-DEL1), the AgentInvoker fallback creates `player_turn_N.json` from git changes but doesn't write `task_work_results.json`.

**Check:**
- `agent_invoker.py` line 169: "task_work_results.json not found, detecting git changes"
- This suggests the fallback IS working, but Coach expects the primary file

## Files to Analyze

1. **Task-Work Command Spec**: `installer/core/commands/task-work.md`
   - Does it specify writing `task_work_results.json`?
   - What triggers results writing?

2. **AgentInvoker**: `guardkit/orchestrator/agent_invoker.py`
   - How does it invoke task-work?
   - What fallback logic exists?

3. **CoachValidator**: `guardkit/orchestrator/quality_gates/coach_validator.py`
   - Where does it look for results?
   - What happens when results not found?

4. **TaskWorkInterface**: `guardkit/orchestrator/quality_gates/task_work_interface.py`
   - Is this used for implement-only phase?
   - Does it write results?

5. **Previous Fix Tasks**:
   - `tasks/completed/TASK-SDK-003/` - "Create task_work_results.json writer"
   - `tasks/completed/TASK-FB-DEL1/` - "Enable task-work delegation"

## Expected Outputs

1. **Root Cause Identification**: Specific file:line where results should be written but aren't
2. **Architecture Assessment**: SOLID/DRY/YAGNI scores for affected components
3. **Implementation Recommendation**: Specific fix with code changes
4. **Test Strategy**: How to verify the fix works

## Decision Options

After review completion:

- **[A]ccept** - Archive findings, no action needed
- **[R]evise** - Request deeper analysis
- **[I]mplement** - Create implementation task(s) to fix
- **[C]ancel** - Discard review

## Success Criteria

- [x] Root cause identified with specific file:line (`agent_invoker.py:1593-1720` - `_write_task_work_results()` never called)
- [x] Path discrepancy (if any) documented (N/A - paths are correct, method just not invoked)
- [x] Implementation recommendation provided (See `.claude/reviews/TASK-REV-FB09-review-report.md`)
- [x] Architectural score calculated (45/100 - below threshold)
- [x] Decision checkpoint reached (Ready for decision)

## Related Tasks

- TASK-REV-FB01 through FB08: Previous feature-build reviews
- TASK-FB-FIX-001 through 011: Previous fixes
- TASK-SDK-003: task_work_results.json writer implementation
- TASK-FB-DEL1: Task-work delegation enablement
