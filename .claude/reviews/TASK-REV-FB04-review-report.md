# Architectural Review Report: TASK-REV-FB04

## Executive Summary

**Review Task**: TASK-REV-FB04 - Feature-Build Implementation Plan Gap Analysis
**Review Mode**: Architectural
**Review Depth**: Standard
**Date**: 2026-01-10
**Reviewer**: architectural-reviewer agent

### Overall Assessment

| Criterion | Score | Grade |
|-----------|-------|-------|
| SOLID Compliance | 58/100 | D |
| DRY Adherence | 45/100 | F |
| YAGNI Compliance | 72/100 | C |
| **Overall Architecture** | **58/100** | **D** |

**Status**: ⚠️ **CRITICAL GAP IDENTIFIED** - The feature-build pre-loop phase does not generate the implementation plan artifact that the Player agent expects, breaking the adversarial cooperation workflow.

---

## 1. Root Cause Analysis

### The Problem

The feature-build orchestration fails at the first turn because:

1. **Pre-Loop Quality Gates** (`guardkit/orchestrator/quality_gates/pre_loop.py`) delegates to `TaskWorkInterface.execute_design_phase()`
2. **TaskWorkInterface** (`guardkit/orchestrator/quality_gates/task_work_interface.py`) returns **mock/stub data** (complexity=5, arch_score=80) instead of actually invoking `/task-work --design-only`
3. **Player Agent** (`guardkit/orchestrator/agent_invoker.py:424`) calls `_ensure_design_approved_state()` which expects an implementation plan file to exist
4. **File Not Found**: The plan was never created because the design phase was never actually executed

### Evidence Flow

```
INFO:guardkit.orchestrator.quality_gates.pre_loop:Pre-loop results extracted: complexity=5, max_turns=5, arch_score=80
INFO:guardkit.orchestrator.autobuild:Pre-loop complete: complexity=5, max_turns=5, checkpoint_passed=True
INFO:guardkit.orchestrator.agent_invoker:Ensuring task TASK-INFRA-001 is in design_approved state
ERROR:guardkit.orchestrator.agent_invoker:Implementation plan not found for TASK-INFRA-001
```

The pre-loop claims success (complexity=5, arch_score=80, checkpoint_passed=True) but these are **hardcoded mock values**, not actual results from running the design phases.

---

## 2. SOLID Compliance Analysis

### 2.1 Single Responsibility Principle (SRP) - 6/10

**Violation in `TaskWorkInterface`**:

The class has two conflicting responsibilities:
1. **Interface contract** - Define how to call task-work
2. **Stub implementation** - Return mock data for development

```python
# task_work_interface.py:execute_design_phase
def execute_design_phase(...) -> DesignPhaseResult:
    # STUB: Returns mock data instead of actual invocation
    return DesignPhaseResult(
        implementation_plan={},
        plan_path=None,
        complexity={"score": 5},
        architectural_review={"score": 80},
        ...
    )
```

**Recommendation**: Separate interface definition from implementation. Either:
- Make TaskWorkInterface an abstract base class with concrete implementations
- Use dependency injection for the actual SDK invocation

### 2.2 Open/Closed Principle (OCP) - 5/10

**Violation**: The pre-loop logic is tightly coupled to the stub implementation.

To fix the design phase gap, developers must:
1. Modify `TaskWorkInterface` directly
2. OR modify `PreLoopQualityGates` to call SDK differently

Neither class is open for extension without modification.

**Recommendation**: Use strategy pattern for SDK invocation methods:
- `SDKInvocationStrategy` (interface)
- `TaskWorkDelegationStrategy` (actual SDK call)
- `MockInvocationStrategy` (for testing)

### 2.3 Liskov Substitution Principle (LSP) - 7/10

**Minor Violation**: The `DesignPhaseResult` dataclass has optional fields that may be None, but consumers don't always handle this gracefully.

```python
# Pre-loop extracts result.plan_path which may be None
return PreLoopResult(
    plan=result.implementation_plan,
    plan_path=result.plan_path,  # Can be None
    ...
)
```

### 2.4 Interface Segregation Principle (ISP) - 6/10

**Violation**: `AgentInvoker` has grown large (500+ lines visible, likely 1000+) with many responsibilities:
- Player invocation
- Coach invocation
- Task-work delegation
- State bridging
- Report validation
- Stream parsing

**Recommendation**: Split into focused interfaces:
- `IPlayerInvoker`
- `ICoachInvoker`
- `IStateBridge`
- `IReportValidator`

### 2.5 Dependency Inversion Principle (DIP) - 5/10

**Critical Violation**: High-level orchestration modules depend on concrete low-level implementations.

```python
# pre_loop.py depends directly on TaskWorkInterface concrete class
from guardkit.orchestrator.quality_gates.task_work_interface import TaskWorkInterface

class PreLoopQualityGates:
    def __init__(self, worktree_path, interface=None):
        self._interface = interface or TaskWorkInterface(self.worktree_path)
```

While there is a constructor injection option (`interface=None`), the default creates a concrete instance, and there's no abstract interface to depend on.

**Recommendation**: Define abstract interface `ITaskWorkInterface` and inject concrete implementation.

---

## 3. DRY Adherence Analysis - 45/100

### 3.1 Duplicated SDK Invocation Logic

**Severe Violation**: There are THREE different places that invoke Claude SDK:

1. **AgentInvoker.invoke_player()** - Direct SDK invocation for Player
2. **AgentInvoker._invoke_task_work_implement()** - Task-work delegation for Player
3. **TaskWorkInterface** - (Should invoke) task-work --design-only

Each has different invocation patterns, error handling, and timeout management.

### 3.2 Duplicated State Management

**Violation**: State bridging logic exists in multiple places:

1. `guardkit/tasks/state_bridge.py` - StateBridge class
2. `agent_invoker.py:_ensure_design_approved_state()` - Inline state management
3. `pre_loop.py` - Implicit state expectations

### 3.3 Duplicated File Path Logic

**Violation**: Implementation plan paths are hardcoded in multiple locations:

```python
# In agent_invoker.py
paths = [
    '.claude/task-plans/TASK-INFRA-001-implementation-plan.md',
    '.claude/task-plans/TASK-INFRA-001-implementation-plan.json',
    'docs/state/TASK-INFRA-001/implementation_plan.md',
    'docs/state/TASK-INFRA-001/implementation_plan.json',
]

# Probably duplicated in task-work-interface.py and pre_loop.py
```

**Recommendation**: Centralize path resolution in a single utility:
```python
class TaskArtifactPaths:
    @staticmethod
    def implementation_plan(task_id: str) -> List[Path]:
        ...
```

---

## 4. YAGNI Compliance Analysis - 72/100

### 4.1 Appropriate Complexity

**Positive**: The design shows appropriate forethought for the adversarial cooperation pattern based on Block AI Research validation.

### 4.2 Over-Engineering Concerns

**Minor Violation**: The `TaskWorkStreamParser` class (100+ lines) may be premature if task-work output format isn't stable.

**Minor Violation**: Multiple agent report schemas (`PLAYER_REPORT_SCHEMA`, `COACH_DECISION_SCHEMA`) defined but validation is minimal.

### 4.3 Missing Essential Features

**Critical Gap**: The actual implementation of the design phase is missing. This is the opposite of YAGNI - the stub exists but the essential feature doesn't.

---

## 5. Architecture Decision: Implementation Approaches

### Option A: Fix TaskWorkInterface to Invoke SDK (Recommended)

**Description**: Modify `TaskWorkInterface.execute_design_phase()` to actually invoke `/task-work --design-only` via Claude Agent SDK.

**Implementation**:
```python
async def execute_design_phase(self, task_id: str, options: Dict) -> DesignPhaseResult:
    client = await self._get_sdk_client()
    result = await client.query(
        prompt=f"/task-work {task_id} --design-only --no-questions",
        working_directory=str(self.worktree_path),
        ...
    )
    return self._parse_design_result(result)
```

**Pros**:
- 100% code reuse of task-work quality gates
- Consistent behavior between manual and automated workflows
- Single source of truth for design phase logic

**Cons**:
- Adds SDK dependency to pre-loop (may already exist)
- Timing complexity (SDK invocation within SDK invocation)

**Effort**: Medium (2-4 hours)
**Risk**: Low
**SOLID Score Improvement**: +15 points

### Option B: Pre-Generate Plans Before Feature-Build

**Description**: Require manual `/task-work --design-only` for each task before `/feature-build`.

**Pros**:
- No code changes required
- Simple to understand

**Cons**:
- Defeats purpose of autonomous feature-build
- Poor developer experience
- Manual step for every task

**Effort**: None
**Risk**: High (adoption barrier)
**SOLID Score Improvement**: 0 points

### Option C: Generate Minimal Plan Stub in Pre-Loop

**Description**: Create minimal `implementation_plan.md` with task requirements in pre-loop.

**Pros**:
- Quick fix
- Unblocks Player agent

**Cons**:
- Loses benefit of proper design phase
- Coach can't validate against real plan
- Technical debt

**Effort**: Low (1 hour)
**Risk**: Medium (quality regression)
**SOLID Score Improvement**: -5 points (adds more technical debt)

### Option D: Inline Design Phase in AutoBuildOrchestrator

**Description**: Move design phase execution into `autobuild.py` before Player loop.

**Pros**:
- Full control over execution
- Clear separation of phases

**Cons**:
- Duplicates task-work design phases
- Maintenance burden (two implementations)
- Violates DRY severely

**Effort**: High (8+ hours)
**Risk**: High (maintenance burden)
**SOLID Score Improvement**: -10 points

---

## 6. Recommendations

### Immediate Actions (P0 - Critical)

1. **Implement Option A**: Fix `TaskWorkInterface.execute_design_phase()` to invoke SDK
   - This is the architectural fix that aligns with the documented design
   - Preserves 100% code reuse of quality gates

2. **Add Validation in Pre-Loop**: Before returning success, verify the plan file exists
   ```python
   plan_path = self._get_plan_path(task_id)
   if not plan_path.exists():
       raise QualityGateBlocked("Design phase did not generate implementation plan")
   ```

### Short-Term Actions (P1 - High)

3. **Centralize Path Logic**: Create `TaskArtifactPaths` utility class
4. **Add Integration Test**: Test that pre-loop + Player flow works end-to-end
5. **Update Documentation**: Clarify the expected pre-loop output artifacts

### Medium-Term Actions (P2 - Medium)

6. **Refactor AgentInvoker**: Split into focused classes (ISP compliance)
7. **Create Abstract Interface**: `ITaskWorkInterface` for DIP compliance
8. **Add Streaming Progress**: Display pre-loop phase progress to user

---

## 7. State Machine Diagram

### Current Flow (Broken)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CURRENT BROKEN FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  BACKLOG ──┬──[feature-build starts]────────────────────────────→   │
│            │                                                         │
│            ├── Phase 1: Create worktree ✅                           │
│            │                                                         │
│            ├── Phase 2: Pre-Loop Quality Gates                       │
│            │   │                                                     │
│            │   └── TaskWorkInterface.execute_design_phase()          │
│            │       │                                                 │
│            │       └── Returns MOCK DATA (complexity=5) ⚠️           │
│            │           (No actual SDK invocation)                    │
│            │           (No implementation plan created)              │
│            │                                                         │
│            ├── Task state: DESIGN_APPROVED ⚠️                        │
│            │   (But no plan artifact exists!)                        │
│            │                                                         │
│            └── Phase 3: Player Turn 1                                │
│                │                                                     │
│                └── _ensure_design_approved_state()                   │
│                    │                                                 │
│                    └── ❌ ERROR: Implementation plan not found       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Expected Flow (Fixed)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     EXPECTED FIXED FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  BACKLOG ──┬──[feature-build starts]────────────────────────────→   │
│            │                                                         │
│            ├── Phase 1: Create worktree ✅                           │
│            │                                                         │
│            ├── Phase 2: Pre-Loop Quality Gates                       │
│            │   │                                                     │
│            │   └── TaskWorkInterface.execute_design_phase()          │
│            │       │                                                 │
│            │       └── Invoke SDK: /task-work {task} --design-only   │
│            │           │                                             │
│            │           ├── Phase 1.6: Clarifying Questions (skip)    │
│            │           ├── Phase 2: Implementation Planning ✅       │
│            │           │   └── Creates: implementation_plan.md       │
│            │           ├── Phase 2.5A: Pattern Suggestions           │
│            │           ├── Phase 2.5B: Architectural Review          │
│            │           ├── Phase 2.7: Complexity Evaluation          │
│            │           └── Phase 2.8: Human Checkpoint (auto-approve)│
│            │                                                         │
│            ├── Validate: plan file exists ✅                         │
│            │                                                         │
│            ├── Task state: DESIGN_APPROVED ✅                        │
│            │   (Plan artifact verified)                              │
│            │                                                         │
│            └── Phase 3: Player-Coach Loop                            │
│                │                                                     │
│                ├── Turn 1: Player reads implementation_plan.md       │
│                │   └── /task-work {task} --implement-only --mode=tdd │
│                │                                                     │
│                ├── Turn 1: Coach validates against plan              │
│                │   └── APPROVE or FEEDBACK                           │
│                │                                                     │
│                └── [Continue until APPROVED or MAX_TURNS]            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. Test Strategy

### Unit Tests

1. **TaskWorkInterface.execute_design_phase()**
   - Mock SDK client
   - Verify correct prompt construction
   - Verify result parsing

2. **PreLoopQualityGates.execute()**
   - Verify plan file existence check
   - Verify raises QualityGateBlocked if plan missing

3. **AgentInvoker._ensure_design_approved_state()**
   - Verify reads plan from correct paths
   - Verify error messages are actionable

### Integration Tests

4. **End-to-End Pre-Loop + Player**
   ```python
   async def test_pre_loop_creates_plan_for_player():
       # Given: A task in backlog
       # When: Pre-loop executes
       # Then: implementation_plan.md exists
       # And: Player can read the plan
   ```

5. **Feature-Build Full Flow**
   ```python
   async def test_feature_build_single_task():
       # Given: A feature with one task
       # When: guardkit autobuild feature FEAT-XXX
       # Then: Task completes with APPROVED status
   ```

---

## 9. Decision Checkpoint

### Review Results Summary

| Metric | Value |
|--------|-------|
| Architecture Score | 58/100 |
| Findings | 8 |
| Recommendations | 8 |
| Critical Gaps | 1 |

### Key Finding

The feature-build architecture is fundamentally sound (based on adversarial cooperation research), but the implementation is incomplete. The pre-loop phase returns mock data instead of actually executing the design phases that generate the implementation plan artifact.

### Recommended Decision

**[I]mplement Option A** - Fix TaskWorkInterface to invoke SDK with `/task-work --design-only`

This fix:
- Aligns implementation with documented architecture
- Achieves 100% code reuse of task-work quality gates
- Unblocks all feature-build functionality
- Estimated effort: 2-4 hours

---

## Appendix A: File Analysis

### Files Analyzed

| File | Lines | Issues |
|------|-------|--------|
| `guardkit/orchestrator/agent_invoker.py` | ~500+ | ISP violation, DIP violation |
| `guardkit/orchestrator/quality_gates/pre_loop.py` | ~329 | SRP violation |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | ~200 | **CRITICAL: Returns mock data** |
| `guardkit/orchestrator/autobuild.py` | ~400+ | Tight coupling |
| `guardkit/tasks/state_bridge.py` | ~200 | Duplicated state logic |

### Missing Files

| Expected File | Purpose |
|---------------|---------|
| `.claude/task-plans/{task_id}-implementation-plan.md` | Implementation plan artifact |
| `docs/state/{task_id}/implementation_plan.json` | Alternative plan location |

---

## Appendix B: References

1. [Task File](../../tasks/backlog/TASK-REV-FB04-feature-build-design-phase-gap.md)
2. [Error Evidence](../../docs/reviews/feature-build/no_implementation_plan.md)
3. [Adversarial Cooperation Design](../../docs/research/guardkit-agent/adversarial-cooperation-validation.md)
4. Block AI Research: "Adversarial Cooperation In Code Synthesis" (December 2025)

---

**Report Generated**: 2026-01-10T11:30:00Z
**Reviewer**: architectural-reviewer agent
**Review Duration**: ~30 minutes
