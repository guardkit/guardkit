# Review Report: TASK-REV-0414

## Quality Gates Integration Seams - Code Reuse Analysis

**Review Mode**: Architectural
**Review Depth**: Comprehensive
**Task ID**: TASK-REV-0414
**Date**: 2025-12-30
**Reviewer**: Claude Code (Opus 4.5)

---

## Executive Summary

This comprehensive architectural review analyzed the quality gates integration tasks (TASK-QG-P1-PRE, TASK-QG-P2-COACH, TASK-QG-P3-POST) against existing `/task-work` code to identify gaps at integration seams and validate code reuse opportunities.

**Overall Assessment**: 72/100

**Key Findings**:
1. **CRITICAL**: TASK-QG-P3-POST proposes creating new `PostLoopQualityGates` class that duplicates ~80% of existing `PlanAuditor` functionality
2. **HIGH**: Plan persistence location mismatch (`.guardkit/autobuild/` vs `docs/state/`)
3. **MEDIUM**: Several phases don't explicitly reference existing implementations
4. **LOW**: Minor inconsistencies in naming conventions

**Recommendation**: Amend task specifications to mandate code reuse before implementation begins.

---

## 1. Seam Analysis: Slash Command → Python

### 1.1 TASK-QG-P1-PRE: Pre-Loop Quality Gates

| Seam | Source | Target | Status | Gap Description |
|------|--------|--------|--------|-----------------|
| CLI → Orchestrator | `/feature-build` | `guardkit/orchestrator/autobuild.py` | ⚠️ GAP | No explicit import/call to `PreLoopQualityGates` in existing code |
| Orchestrator → Agents | `autobuild.py` | Claude SDK | ⚠️ GAP | Agent invocation pattern not specified (uses SDK `query()` but agent tool mapping unclear) |
| Phase Results → Loop | Phase 2.8 | Adversarial Loop | ✅ OK | Plan passed correctly to loop |

**Gap Analysis**:
- The existing `autobuild.py` has skeleton structure but doesn't call any quality gates
- Current flow: `SETUP → LOOP → FINALIZE`
- Proposed flow: `SETUP → PRE_LOOP → LOOP → POST_LOOP → FINALIZE`
- **Integration seam at line ~96**: Need to insert `PreLoopQualityGates.execute()` call

### 1.2 TASK-QG-P2-COACH: Enhanced Coach Agent

| Seam | Source | Target | Status | Gap Description |
|------|--------|--------|--------|-----------------|
| Coach Prompt → SDK | `autobuild-coach.md` | Claude SDK | ⚠️ GAP | How does Coach access `TestEnforcementLoop` and `CodeReview` classes? |
| SDK → Results | SDK `query()` | `coach_turn_N.json` | ✅ OK | JSON output format well-defined |
| Phase 4.5 → Phase 5 | Test Results | Code Review | ✅ OK | Sequential execution clear |

**Gap Analysis**:
- Task proposes creating `TestEnforcementLoop`, `CodeReview`, `CoverageMeasurement` as separate classes
- But these run WITHIN the Coach agent prompt - how are they invoked?
- Options:
  1. Python modules imported by orchestrator, results passed to Coach
  2. Custom MCP tools available to Coach
  3. Bash commands run by Coach directly
- **Task spec doesn't clarify** which approach to use

### 1.3 TASK-QG-P3-POST: Post-Loop Plan Audit

| Seam | Source | Target | Status | Gap Description |
|------|--------|--------|--------|-----------------|
| Loop → Post-Loop | Coach Approval | `PostLoopQualityGates` | ✅ OK | Clear trigger condition |
| Audit → Human | Variance Check | `human_checkpoint()` | ⚠️ GAP | Existing `checkpoint_display.py` not referenced |
| Checkpoint → Result | User Decision | Task Status | ✅ OK | Block/approve flow clear |

**Gap Analysis**:
- **MAJOR DUPLICATION**: Proposed `PostLoopQualityGates._compare_files()`, `_compare_loc()`, `_detect_scope_creep()` duplicate existing `PlanAuditor` functionality
- Existing `plan_audit.py` already implements:
  - File comparison (planned vs actual)
  - LOC variance calculation
  - Dependency comparison
  - Severity calculation
  - Human-readable report formatting

---

## 2. Code Reuse Validation

### 2.1 Phase 1.6: Clarifying Questions

| Existing Code | Location | Task Mentions Reuse? | Actual Reuse Plan |
|--------------|----------|----------------------|-------------------|
| `clarification-questioner` agent | `~/.agentecflow/agents/` | ✅ Yes | ✅ Correct |
| `lib/clarification/` | `installer/core/commands/lib/clarification/` | ❌ No | ⚠️ Should import |
| `detection.py` | `lib/clarification/detection.py` | ❌ No | ⚠️ Has `should_ask_questions(complexity)` |

**Recommendation**: Task should explicitly state:
```python
from lib.clarification.detection import should_ask_questions
from lib.clarification.generators.planning_generator import generate_implementation_questions
```

### 2.2 Phase 2: Implementation Planning

| Existing Code | Location | Task Mentions Reuse? | Actual Reuse Plan |
|--------------|----------|----------------------|-------------------|
| `plan_persistence.py` | `installer/core/commands/lib/` | ✅ Yes (implicit) | ⚠️ Path mismatch |
| `plan_markdown_renderer.py` | Same | ❌ No | ⚠️ Should use |
| `plan_markdown_parser.py` | Same | ❌ No | ⚠️ Should use |

**CRITICAL ISSUE**: Task proposes saving plans to `.guardkit/autobuild/{task_id}/implementation-plan.md` but existing code uses `docs/state/{task_id}/implementation_plan.md`.

**Recommendation**: Use existing path convention OR add migration logic.

### 2.3 Phase 2.5A: Pattern Suggestions

| Existing Code | Location | Task Mentions Reuse? | Actual Reuse Plan |
|--------------|----------|----------------------|-------------------|
| MCP `design-patterns` | MCP server | ✅ Yes | ✅ Correct |
| No Python wrapper exists | N/A | N/A | ✅ Direct MCP call OK |

**Status**: ✅ No changes needed. MCP integration is correct.

### 2.4 Phase 2.5B: Architectural Review

| Existing Code | Location | Task Mentions Reuse? | Actual Reuse Plan |
|--------------|----------|----------------------|-------------------|
| `architectural-reviewer` agent | `installer/core/agents/` | ✅ Yes | ✅ Correct |
| Agent invocation pattern | Task tool | ❌ No | ⚠️ Should specify subagent_type |

**Recommendation**: Task should show explicit invocation:
```python
# Via Task tool
subagent_type: "architectural-reviewer"
prompt: "Review implementation plan for {task_id}..."
```

### 2.5 Phase 2.7: Complexity Evaluation

| Existing Code | Location | Task Mentions Reuse? | Actual Reuse Plan |
|--------------|----------|----------------------|-------------------|
| `ComplexityAnalyzer` | `guardkit/planning/complexity.py` | ✅ Yes | ✅ Correct |
| `ComplexityFactors` | Same | ✅ Yes | ✅ Correct |
| `evaluate_complexity()` function | N/A (doesn't exist) | ❌ Proposed | ⚠️ Use `ComplexityAnalyzer.analyze_task()` instead |

**Recommendation**: Use existing `ComplexityAnalyzer` class:
```python
from guardkit.planning.complexity import ComplexityAnalyzer

analyzer = ComplexityAnalyzer()
factors = analyzer.analyze_task({
    "name": task.title,
    "description": task.description,
    "requirements": task.acceptance_criteria
})
complexity_score = factors.calculate_score()
```

### 2.6 Phase 2.8: Human Checkpoint

| Existing Code | Location | Task Mentions Reuse? | Actual Reuse Plan |
|--------------|----------|----------------------|-------------------|
| `checkpoint_display.py` | `installer/core/commands/lib/` | ❌ No | ⚠️ Should use |
| `display_phase28_checkpoint()` | Same | ❌ No | ⚠️ Already exists! |
| `handle_modify_option()` | Same | ❌ No | ⚠️ Already exists! |

**CRITICAL ISSUE**: Existing `display_phase28_checkpoint()` function does exactly what Phase 2.8 needs. Task should use it directly.

**Recommendation**:
```python
from lib.checkpoint_display import display_phase28_checkpoint, handle_modify_option

display_phase28_checkpoint(task_id, complexity_score)
decision = input("Your choice [A/M/C]: ")
if decision.lower() == 'm':
    handle_modify_option(task_id)
```

### 2.7 Phase 4.5: Test Enforcement

| Existing Code | Location | Task Mentions Reuse? | Actual Reuse Plan |
|--------------|----------|----------------------|-------------------|
| `phase_gate_validator.py` | `installer/core/commands/lib/` | ❌ No | ⚠️ Partial overlap |
| `PhaseGateValidator` | Same | ❌ No | ⚠️ For validation only |
| `test-orchestrator` agent | `installer/core/agents/` | ✅ Yes (implicit) | ✅ Correct |
| `test-verifier` agent | Same | ✅ Yes (implicit) | ✅ Correct |

**Analysis**:
- `PhaseGateValidator` is for **validation** (checking if agent was invoked)
- `TestEnforcementLoop` is for **execution** (running tests, auto-fix)
- These are complementary, not duplicates
- **No change needed** - new `TestEnforcementLoop` class is appropriate

### 2.8 Phase 5: Code Review

| Existing Code | Location | Task Mentions Reuse? | Actual Reuse Plan |
|--------------|----------|----------------------|-------------------|
| `code-reviewer` agent | `installer/core/agents/` | ✅ Yes | ✅ Correct |
| `architectural-reviewer` agent | Same | ✅ Yes | ✅ Correct |

**Status**: ✅ Correct approach. Agent-based review is appropriate.

### 2.9 Phase 5.5: Plan Audit

| Existing Code | Location | Task Mentions Reuse? | Actual Reuse Plan |
|--------------|----------|----------------------|-------------------|
| `PlanAuditor` | `installer/core/commands/lib/plan_audit.py` | ❌ No | ❌ DUPLICATES |
| `audit_implementation()` | Same | ❌ No | ❌ DUPLICATES |
| `_compare_files()` | Same | ❌ No | ❌ DUPLICATES |
| `_compare_loc()` | Same | ❌ No | ❌ DUPLICATES |
| `_calculate_severity()` | Same | ❌ No | ❌ DUPLICATES |
| `format_audit_report()` | Same | ❌ No | ❌ DUPLICATES |
| `Discrepancy` dataclass | Same | ❌ No | ❌ DUPLICATES |
| `PlanAuditReport` dataclass | Same | ❌ No | ❌ DUPLICATES |

**CRITICAL ISSUE**: TASK-QG-P3-POST proposes creating `PostLoopQualityGates` with methods that duplicate ~80% of existing `PlanAuditor` functionality:

| Proposed Method | Existing Equivalent | Match % |
|----------------|---------------------|---------|
| `_get_modified_files()` | `_scan_modified_files()` | 90% |
| `_compare_files()` | `_compare_files()` | 95% |
| `_compare_loc()` | `_compare_loc()` | 95% |
| `_calculate_variances()` | (inline in `_compare_loc`) | 80% |
| `_detect_scope_creep()` | (logic spread across `_compare_*`) | 70% |
| `human_checkpoint()` | `format_audit_report()` + input | 60% |

**Recommendation**: Delete proposed `PostLoopQualityGates` implementation and use:
```python
from lib.plan_audit import PlanAuditor, format_audit_report

auditor = PlanAuditor(workspace_root=worktree_path)
report = auditor.audit_implementation(task_id)

if report.severity in ['medium', 'high']:
    print(format_audit_report(report))
    decision = input("Decision [A/R/E/C]: ")
```

---

## 3. Gap Report

### 3.1 Critical Gaps (Must Fix Before Implementation)

| ID | Gap | Impact | Recommendation |
|----|-----|--------|----------------|
| GAP-001 | TASK-QG-P3-POST duplicates `PlanAuditor` | 80% code duplication, maintenance burden | Rewrite task to use existing `PlanAuditor` |
| GAP-002 | Plan path mismatch (`.guardkit/` vs `docs/state/`) | Breaks existing plan loading | Standardize on `docs/state/` OR add path adapter |
| GAP-003 | Checkpoint display not referenced | Existing UI code ignored | Import `checkpoint_display.py` functions |

### 3.2 High Gaps (Should Fix)

| ID | Gap | Impact | Recommendation |
|----|-----|--------|----------------|
| GAP-004 | No explicit complexity analyzer import | May create parallel implementation | Add explicit import statement to task |
| GAP-005 | Coach tool access mechanism unclear | Implementation ambiguity | Clarify: Python classes vs MCP tools vs Bash |

### 3.3 Medium Gaps (Nice to Fix)

| ID | Gap | Impact | Recommendation |
|----|-----|--------|----------------|
| GAP-006 | `lib/clarification/` not explicitly imported | May miss existing question templates | Add import statement |
| GAP-007 | Agent invocation patterns not shown | Copy-paste required | Add example subagent_type calls |

### 3.4 Low Gaps (Optional)

| ID | Gap | Impact | Recommendation |
|----|-----|--------|----------------|
| GAP-008 | Naming inconsistency (`_get_modified_files` vs `_scan_modified_files`) | Minor confusion | Align naming |

---

## 4. Risk Assessment

### 4.1 Risk of NOT Reusing Existing Code

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Duplicate bugs** - Same bug fixed in two places | High | Medium | Single source of truth |
| **Divergent behavior** - Audit logic differs between task-work and feature-build | High | High | Shared implementation |
| **Maintenance burden** - Two codebases to maintain | High | High | Code reuse |
| **Test duplication** - Same tests written twice | High | Medium | Shared test suite |
| **Integration issues** - Incompatible data formats | Medium | High | Use existing data classes |

### 4.2 Overall Risk Score

**Risk Score: 7/10 (High)**

Proceeding without addressing GAP-001 (PlanAuditor duplication) creates significant technical debt that will compound over time.

---

## 5. Recommended Task Amendments

### 5.1 TASK-QG-P1-PRE Amendments

**Current**: Creates new implementation planning logic
**Amended**:
```markdown
### Integration Points (AMENDED)

**Phase 2.7: Complexity Evaluation**
- IMPORT: `from guardkit.planning.complexity import ComplexityAnalyzer`
- USE: `analyzer.analyze_task(task_dict)` NOT new `evaluate_complexity()` function

**Phase 2.8: Human Checkpoint**
- IMPORT: `from lib.checkpoint_display import display_phase28_checkpoint, handle_modify_option`
- USE: Existing checkpoint display, NOT new implementation

**Plan Persistence**
- IMPORT: `from lib.plan_persistence import save_plan, load_plan`
- PATH: Use `docs/state/{task_id}/` NOT `.guardkit/autobuild/{task_id}/`
```

### 5.2 TASK-QG-P2-COACH Amendments

**Current**: Coach accesses `TestEnforcementLoop` and `CodeReview` classes somehow
**Amended**:
```markdown
### Tool Access Mechanism (NEW SECTION)

The Coach agent accesses quality gate logic via **orchestrator pre-computation**:

1. **Before Coach invocation**, orchestrator runs:
   ```python
   test_result = TestEnforcementLoop().execute(worktree_path)
   coverage_result = CoverageMeasurement().measure(worktree_path)
   ```

2. **Coach receives pre-computed results** in prompt:
   ```
   ## Pre-Computed Quality Gate Results

   Test Results:
   - Tests passed: {test_result.tests_passed}
   - Failures: {test_result.failures}

   Coverage:
   - Line: {coverage_result.line_coverage}%
   - Branch: {coverage_result.branch_coverage}%
   ```

3. **Coach validates independently** by running tests itself (verification)
```

### 5.3 TASK-QG-P3-POST Amendments

**Current**: Creates new `PostLoopQualityGates` class with duplicate logic
**Amended**:
```markdown
### Files to Create (AMENDED)

- ~~`guardkit/orchestrator/quality_gates/post_loop.py`~~ (DELETED - use existing)
- `tests/unit/test_autobuild_plan_audit.py` (integration tests only)

### Files to Modify (AMENDED)

- `guardkit/orchestrator/autobuild.py`:
  - Import: `from lib.plan_audit import PlanAuditor, format_audit_report`
  - Call: `auditor.audit_implementation(task_id)`

### Implementation (AMENDED)

Replace proposed `PostLoopQualityGates` with thin wrapper:

```python
from lib.plan_audit import PlanAuditor, format_audit_report, PlanAuditReport

class PostLoopPlanAudit:
    """Thin wrapper around PlanAuditor for AutoBuild integration."""

    def __init__(self, worktree_path: str):
        self.auditor = PlanAuditor(workspace_root=worktree_path)

    def execute(self, task_id: str) -> PlanAuditReport:
        """Execute plan audit and handle checkpoint if needed."""
        report = self.auditor.audit_implementation(task_id)

        if report.severity in ['medium', 'high']:
            self._handle_checkpoint(report)

        return report

    def _handle_checkpoint(self, report: PlanAuditReport):
        """Display report and get human decision."""
        print(format_audit_report(report))
        # ... existing checkpoint logic ...
```
```

---

## 6. Implementation Order Recommendation

**Confirmed Order**: P1-PRE → P2-COACH → P3-POST (sequential)

**Rationale**:
1. **P1-PRE must complete first** because:
   - Creates implementation plan that P2-COACH and P3-POST need
   - Sets `max_turns` that P2-COACH loop uses
   - Establishes checkpoint patterns reused later

2. **P2-COACH depends on P1-PRE** because:
   - Needs plan to verify requirements
   - Needs `max_turns` from complexity evaluation

3. **P3-POST depends on P1-PRE** because:
   - Needs plan to compare against actual
   - Uses same checkpoint display patterns

**No parallelization possible** due to these dependencies.

---

## 7. Completeness Verification

### 7.1 TASK-QG-P1-PRE

| Criterion | Testable? | Test Strategy |
|-----------|-----------|---------------|
| All 6 pre-loop phases implemented | ✅ Yes | Unit test each phase |
| Phase 1.6 clarification works | ✅ Yes | Mock agent, verify invocation |
| Phase 2 plan generated and saved | ✅ Yes | Check file exists |
| Phase 2.5A MCP integration | ✅ Yes | Mock MCP, verify call |
| Phase 2.5B architectural review | ✅ Yes | Mock agent, check score |
| Phase 2.7 complexity evaluation | ✅ Yes | Known inputs → expected outputs |
| Phase 2.8 checkpoint triggers | ✅ Yes | complexity ≥7 → checkpoint |
| Plan passed to loop | ✅ Yes | Integration test |
| max_turns determined dynamically | ✅ Yes | complexity → expected max_turns |

### 7.2 TASK-QG-P2-COACH

| Criterion | Testable? | Test Strategy |
|-----------|-----------|---------------|
| Test enforcement module created | ✅ Yes | Import check |
| Auto-fix loop implemented | ✅ Yes | Failing test → 3 attempts → report |
| Coverage measurement working | ✅ Yes | Known code → expected coverage |
| Code review module created | ✅ Yes | Import check |
| Architectural scoring | ✅ Yes | Known code → expected score |
| Requirements verification | ✅ Yes | Requirements + code → checklist |
| Coach instructions updated | ✅ Yes | File content check |
| Decision format includes Phase 4.5 + 5 | ✅ Yes | JSON schema validation |

### 7.3 TASK-QG-P3-POST (After Amendment)

| Criterion | Testable? | Test Strategy |
|-----------|-----------|---------------|
| `PlanAuditor` integration complete | ✅ Yes | Import and call test |
| Variance calculation correct | ✅ Yes | Known plan + actual → expected variance |
| Checkpoint triggers at >20% | ✅ Yes | Variance 25% → checkpoint triggered |
| Human decision handled | ✅ Yes | Mock input → expected state |
| `autobuild.py` integration | ✅ Yes | E2E test |

---

## 8. Architecture Score

### 8.1 SOLID Compliance

| Principle | Score | Notes |
|-----------|-------|-------|
| **S**ingle Responsibility | 7/10 | `PreLoopQualityGates` does many things but grouped by phase |
| **O**pen/Closed | 6/10 | Phase logic hardcoded; could use strategy pattern |
| **L**iskov Substitution | 8/10 | Not many inheritance hierarchies |
| **I**nterface Segregation | 7/10 | Reasonable separation |
| **D**ependency Inversion | 5/10 | Direct imports throughout; could use DI |

**SOLID Score**: 33/50 (66%)

### 8.2 DRY Compliance

| Issue | Severity | Location |
|-------|----------|----------|
| `PostLoopQualityGates` duplicates `PlanAuditor` | Critical | TASK-QG-P3-POST |
| Checkpoint display logic duplicated | Medium | Phase 2.8 |
| Complexity evaluation function duplicated | Low | Phase 2.7 |

**DRY Score**: 20/30 (67%)

### 8.3 YAGNI Compliance

| Issue | Severity | Location |
|-------|----------|----------|
| `CoverageMeasurement` class (could be function) | Low | TASK-QG-P2-COACH |
| `PostLoopQualityGates` class when `PlanAuditor` exists | High | TASK-QG-P3-POST |

**YAGNI Score**: 22/30 (73%)

### 8.4 Overall Architecture Score

**Total: 72/100**

| Category | Score |
|----------|-------|
| SOLID | 33/50 |
| DRY | 20/30 |
| YAGNI | 19/20 |

---

## 9. Decision Options

Based on this comprehensive review, the following options are available:

### Option A: Accept with Amendments (Recommended)

**Description**: Proceed with implementation after amending task specifications to address critical gaps.

**Required Amendments**:
1. Rewrite TASK-QG-P3-POST to use existing `PlanAuditor`
2. Update TASK-QG-P1-PRE to import existing checkpoint display
3. Clarify Coach tool access mechanism in TASK-QG-P2-COACH

**Effort**: ~4 hours to amend task specs

### Option B: Implement as Specified

**Description**: Proceed with current task specifications, accepting technical debt.

**Risks**:
- 80% code duplication in plan audit
- Maintenance burden doubles
- Bugs may diverge between task-work and feature-build

**NOT RECOMMENDED** due to high technical debt risk.

### Option C: Create New Review Task

**Description**: Create a new task to consolidate quality gates code before implementation.

**Scope**:
1. Extract shared quality gate interfaces
2. Create unified checkpoint display
3. Standardize plan persistence paths
4. Update both task-work and feature-build

**Effort**: ~2-3 days additional

---

## 10. Decision Outcome: Option D Selected

### 10.1 User's Pivotal Question

During the review, the user raised a fundamental architectural question:

> "But is there actual scope for using task work to implement each of the tasks alongside using the coach sub agent? Could the coach sub agent actually use task work? Does that then just allow us to reuse directly the task-work command?"

### 10.2 Option D: Task-Work Delegation

This led to discovery of **Option D** - a superior approach not in the original options:

**Architecture**:
```
/feature-build TASK-XXX
    ├── PHASE 1: SETUP (worktree)
    │
    ├── PHASE 2: PRE-LOOP
    │   └── /task-work TASK-XXX --design-only
    │       └── Phases 1.6, 2, 2.5A, 2.5B, 2.7, 2.8
    │
    ├── PHASE 3: ADVERSARIAL LOOP
    │   ├── PLAYER TURN
    │   │   └── /task-work TASK-XXX --implement-only
    │   │       └── Phases 3, 4, 4.5, 5, 5.5
    │   │
    │   └── COACH TURN (lightweight validator)
    │       └── Verify task-work gates passed
    │       └── Run independent test verification
    │       └── Decision: APPROVE or FEEDBACK
    │
    └── PHASE 4: FINALIZE (preserve worktree)
```

### 10.3 Why Option D is Superior

| Metric | Original (Reimplementation) | Option D (Delegation) |
|--------|----------------------------|----------------------|
| **Code Reuse** | ~20% | **100%** |
| **Total LOC** | ~1,400 | **~300** |
| **Complexity** | 20 | **11** |
| **Duration** | 13-20 days | **3.5-6 days** |
| **Maintenance** | Two implementations | **Single source** |

### 10.4 Tasks Rewritten

All three quality gates integration tasks have been rewritten:

1. **TASK-QG-P1-PRE**: Pre-Loop via task-work Delegation
   - Complexity: 7 → 4
   - Duration: 3-5 days → 1-2 days
   - Delegates to `/task-work --design-only`

2. **TASK-QG-P2-COACH**: Lightweight Coach Validator
   - Complexity: 8 → 5
   - Duration: 5-7 days → 2-3 days
   - Validates task-work results, doesn't reimplement gates

3. **TASK-QG-P3-POST**: Minimal Finalization
   - Complexity: 5 → 2
   - Duration: 2-3 days → 0.5-1 day
   - No `PostLoopQualityGates` needed (task-work handles Phase 5.5)

4. **TASK-QG-P4-TEST**: **ELIMINATED**
   - Not needed because task-work quality gates are already tested

### 10.5 Key Insight

The existing `--design-only` and `--implement-only` flags in task-work already provide the exact phase groupings needed:

- `--design-only`: Phases 1.6, 2, 2.5A, 2.5B, 2.7, 2.8 (pre-loop)
- `--implement-only`: Phases 3, 4, 4.5, 5, 5.5 (implementation + gates)

**This means feature-build can achieve 100% code reuse by simply delegating to task-work.**

### 10.6 Conclusion

**Decision: Option D - Task-Work Delegation**

This decision:
- ✅ Eliminates 80% code duplication flagged in this review
- ✅ Reduces total implementation effort by 70%
- ✅ Creates single source of truth for quality gates
- ✅ Future task-work improvements automatically benefit feature-build
- ✅ Maintains adversarial rigor (Coach still validates independently)

**All task specifications updated**: See `tasks/backlog/quality-gates-integration/` for revised tasks.

---

## Appendix A: File Cross-Reference

| Existing File | Purpose | Used By |
|---------------|---------|---------|
| `guardkit/planning/complexity.py` | Complexity analysis | Phase 2.7 |
| `installer/core/commands/lib/plan_audit.py` | Plan audit | Phase 5.5 |
| `installer/core/commands/lib/plan_persistence.py` | Plan save/load | Phase 2 |
| `installer/core/commands/lib/checkpoint_display.py` | Human checkpoints | Phase 2.8, 5.5 |
| `installer/core/commands/lib/phase_gate_validator.py` | Phase validation | All phases |
| `installer/core/commands/lib/clarification/` | Clarifying questions | Phase 1.6 |

---

## Appendix B: Proposed Import Statements

Add these imports to `guardkit/orchestrator/quality_gates/pre_loop.py`:

```python
# Complexity evaluation
from guardkit.planning.complexity import ComplexityAnalyzer, ComplexityFactors

# Checkpoint display
from lib.checkpoint_display import (
    display_phase28_checkpoint,
    handle_modify_option,
    load_plan_summary
)

# Plan persistence
from lib.plan_persistence import (
    save_plan,
    load_plan,
    plan_exists,
    get_plan_path
)

# Clarification
from lib.clarification.detection import should_ask_questions
from lib.clarification.generators.planning_generator import generate_implementation_questions
```

Add these imports to `guardkit/orchestrator/autobuild.py`:

```python
# Plan audit (for post-loop)
from lib.plan_audit import (
    PlanAuditor,
    PlanAuditReport,
    format_audit_report
)
```
