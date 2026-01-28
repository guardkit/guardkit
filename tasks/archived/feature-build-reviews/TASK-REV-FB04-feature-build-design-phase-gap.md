---
id: TASK-REV-FB04
title: "Analyze Feature-Build Implementation Plan Gap"
priority: high
status: review_complete
task_type: review
created: 2026-01-10T10:30:00Z
updated: 2026-01-10T11:30:00Z
complexity: 7
review_results:
  mode: architectural
  depth: standard
  score: 58
  findings_count: 8
  recommendations_count: 8
  decision: implement_option_a
  report_path: .claude/reviews/TASK-REV-FB04-review-report.md
  completed_at: 2026-01-10T11:30:00Z
tags:
  - feature-build
  - autobuild
  - architectural-review
  - pre-loop
  - design-phase
related_tasks:
  - TASK-REV-FB01
  - TASK-REV-FB02
  - TASK-FB-W3
references:
  - docs/reviews/feature-build/no_implementation_plan.md
  - docs/research/guardkit-agent/adversarial-cooperation-validation.md
  - tasks/backlog/feature-build/README.md
---

# TASK-REV-FB04: Feature-Build Implementation Plan Gap Analysis

## Summary

Analyze the failure mode observed when running `/feature-build` where the Player-Coach adversarial loop cannot execute because no implementation plan exists. The architecture should execute `/task-work --design-only` during pre-loop phase to generate the implementation plan before running Player-Coach loops.

## Problem Statement

Based on the test output in [docs/reviews/feature-build/no_implementation_plan.md](../../docs/reviews/feature-build/no_implementation_plan.md):

```
ERROR:guardkit.orchestrator.agent_invoker:Implementation plan not found for TASK-INFRA-001:
Implementation plan not found for TASK-INFRA-001. Expected at one of:
['.claude/task-plans/TASK-INFRA-001-implementation-plan.md',
 '.claude/task-plans/TASK-INFRA-001-implementation-plan.json',
 'docs/state/TASK-INFRA-001/implementation_plan.md',
 'docs/state/TASK-INFRA-001/implementation_plan.json'].
Run task-work --design-only first to generate the plan.
```

**Root Cause**: The pre-loop quality gate runs successfully (`complexity=5, arch_score=80, checkpoint_passed=True`) but does not generate the implementation plan artifact that the subsequent Player agent expects.

## Evidence

### Pre-Loop Output (Successful but Incomplete)
```
INFO:guardkit.orchestrator.autobuild:Phase 2 (Pre-Loop): Executing quality gates for TASK-INFRA-001
INFO:guardkit.orchestrator.quality_gates.pre_loop:Executing pre-loop quality gates for TASK-INFRA-001
INFO:guardkit.orchestrator.quality_gates.task_work_interface:Executing design phase for TASK-INFRA-001
INFO:guardkit.orchestrator.quality_gates.pre_loop:Pre-loop results extracted: complexity=5, max_turns=5, arch_score=80
INFO:guardkit.orchestrator.autobuild:Pre-loop complete: complexity=5, max_turns=5, checkpoint_passed=True
```

### Worktree State After Pre-Loop
- `.claude/task-plans/` directory does not exist
- `docs/state/TASK-INFRA-001/` directory does not exist
- Task was moved to `design_approved` state without an actual design artifact

### Player Agent Expectation
The `AgentInvoker.invoke_player()` method at [guardkit/orchestrator/agent_invoker.py](../../guardkit/orchestrator/agent_invoker.py):1980-2015 calls `_ensure_design_approved_state()` which expects:
1. Task to be in `design_approved` state
2. Implementation plan to exist at one of the expected paths

## Architectural Analysis

### Current Flow (Broken)

```
/feature-build FEAT-XXX
    │
    ├─→ Phase 1 (Setup): Create worktree ✅
    │
    ├─→ Phase 2 (Pre-Loop): Quality gates ⚠️ INCOMPLETE
    │   │
    │   └─→ TaskWorkInterface.execute_design_phase()
    │       │
    │       └─→ Returns mock data (complexity=5, arch_score=80)
    │           but does NOT generate implementation plan file
    │
    └─→ Phase 3 (Loop): Player-Coach ❌ FAILS
        │
        └─→ AgentInvoker.invoke_player()
            │
            └─→ _ensure_design_approved_state()
                │
                └─→ ERROR: Implementation plan not found
```

### Expected Flow (Per Adversarial Cooperation Design)

```
/feature-build FEAT-XXX
    │
    ├─→ Phase 1 (Setup): Create worktree ✅
    │
    ├─→ Phase 2 (Pre-Loop): Full Design Phase ✅
    │   │
    │   └─→ Execute /task-work {task_id} --design-only via SDK
    │       │
    │       ├─→ Phase 1.6: Clarifying Questions (--no-questions for automation)
    │       ├─→ Phase 2: Implementation Planning → Creates implementation_plan.md
    │       ├─→ Phase 2.5A: Pattern Suggestions
    │       ├─→ Phase 2.5B: Architectural Review
    │       ├─→ Phase 2.7: Complexity Evaluation → Creates complexity_score.json
    │       └─→ Phase 2.8: Human Checkpoint (auto-approve for feature-build)
    │
    └─→ Phase 3 (Loop): Player-Coach ✅
        │
        └─→ Player reads implementation plan
        └─→ Coach validates against plan
```

## Key Files to Analyze

### Pre-Loop Implementation
- [guardkit/orchestrator/quality_gates/pre_loop.py](../../guardkit/orchestrator/quality_gates/pre_loop.py)
- [guardkit/orchestrator/quality_gates/task_work_interface.py](../../guardkit/orchestrator/quality_gates/task_work_interface.py)

### Agent Invoker (Where Error Occurs)
- [guardkit/orchestrator/agent_invoker.py](../../guardkit/orchestrator/agent_invoker.py):1980-2015 (`_ensure_design_approved_state`)
- [guardkit/orchestrator/agent_invoker.py](../../guardkit/orchestrator/agent_invoker.py):358-525 (`invoke_player`)

### State Bridge
- [guardkit/tasks/state_bridge.py](../../guardkit/tasks/state_bridge.py) - Bridges AutoBuild state with task-work state

### Research Context
- [docs/research/guardkit-agent/adversarial-cooperation-validation.md](../../docs/research/guardkit-agent/adversarial-cooperation-validation.md)
- [docs/research/guardkit-agent/FEATURE-005-adversarial-orchestrator.md](../../docs/research/guardkit-agent/FEATURE-005-adversarial-orchestrator.md)

## Review Questions

1. **Pre-Loop Gap**: Why does `TaskWorkInterface.execute_design_phase()` return mock data instead of actually invoking `/task-work --design-only`?

2. **SDK Integration**: Should pre-loop invoke `/task-work --design-only` via Claude Agent SDK (like Player does) instead of subprocess/import fallback?

3. **Plan Persistence**: Where should the implementation plan be written and what format (JSON vs Markdown)?

4. **State Bridging**: How should the state bridge handle the case where pre-loop completes but plan doesn't exist?

5. **Automation Flags**: What flags should be passed to `/task-work --design-only` for autonomous feature-build execution?
   - `--no-questions` - Skip clarification (Phase 1.6)
   - `--defaults` - Use default answers
   - Auto-approve checkpoint (Phase 2.8)

## Acceptance Criteria

### Analysis Deliverables
- [ ] Root cause analysis document explaining the gap between pre-loop and Player expectations
- [ ] Architectural decision: SDK invocation vs subprocess vs direct import for design phase
- [ ] Specification for how `/task-work --design-only` should be invoked during pre-loop
- [ ] State machine diagram showing proper transitions: backlog → design_approved (with plan) → in_progress

### Recommendations
- [ ] Concrete implementation approach (modify pre-loop? modify task-work-interface? modify agent-invoker?)
- [ ] Estimated effort for each approach
- [ ] Risk assessment for each approach
- [ ] Test strategy to verify fix

## Context References

### From adversarial-cooperation-validation.md
> "The Player agent reads requirements and implements solutions... The Coach agent validates implementations against requirements."

The current architecture assumes the Player has access to an implementation plan, but the plan is never generated.

### From FEATURE-005-adversarial-orchestrator.md
> "Phase 2 (Pre-Loop): Executing quality gates for TASK-XXX"

The pre-loop is currently a mock implementation that doesn't actually execute the design phases.

### From task-work.md (Phase 2.7)
> "Save to: docs/state/{task_id}/implementation_plan.json"

This is the expected artifact that should be created but isn't.

## Implementation Approach Options

### Option A: Fix TaskWorkInterface to Actually Invoke SDK
- Modify `_execute_via_import()` to actually run `/task-work --design-only` via SDK query()
- Pros: Reuses existing task-work quality gates (100% code reuse)
- Cons: Adds SDK dependency to pre-loop, timing complexity

### Option B: Pre-Generate Plans Before Feature-Build
- Require `/task-work --design-only` to be run for each task before `/feature-build`
- Pros: Simple, no code changes
- Cons: Defeats purpose of autonomous feature-build

### Option C: Generate Minimal Plan Stub in Pre-Loop
- Create minimal implementation_plan.md with task requirements
- Pros: Quick fix
- Cons: Loses benefit of proper design phase, Coach can't validate against proper plan

### Option D: Inline Design Phase in AutoBuildOrchestrator
- Move design phase execution into autobuild.py before Player loop
- Pros: Full control, clear separation
- Cons: Duplicates task-work design phases, maintenance burden

**Recommended**: Option A - Fix TaskWorkInterface to invoke SDK with `/task-work --design-only`

## Notes for Reviewer

This task represents a critical architectural gap between the documented adversarial cooperation pattern and the actual implementation. The Player-Coach loop cannot function without the implementation plan artifact.

Priority is HIGH because this blocks all feature-build functionality.
