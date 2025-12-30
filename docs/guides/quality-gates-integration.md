## Quality Gates Integration Guide

This guide explains how quality gates are integrated into the AutoBuild workflow, providing automated quality enforcement at key phases of task implementation.

### Table of Contents

1. [Overview](#overview)
2. [Pre-Loop Quality Gates](#pre-loop-quality-gates)
3. [Loop Quality Gates](#loop-quality-gates)
4. [Failure Scenarios](#failure-scenarios)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Overview

GuardKit's quality gates provide automated quality enforcement at critical points in the task workflow, preventing broken code from reaching production.

### What Are Quality Gates?

Quality gates are automated checkpoints that verify:
- **Architectural quality** (SOLID, DRY, YAGNI principles)
- **Test coverage** (line, branch, function coverage)
- **Implementation fidelity** (matches approved plan)
- **Code quality** (maintainability, complexity)

### When Do Quality Gates Execute?

Quality gates execute at three stages:

1. **Pre-Loop** (Phases 1.6-2.8): Before implementation begins
2. **Loop** (Player-Coach turns): During implementation
3. **Post-Loop** (Finalization): After implementation completes

---

## Pre-Loop Quality Gates

Pre-loop quality gates execute **before** the Player-Coach adversarial loop, ensuring that only well-designed tasks proceed to implementation.

### Phase 1.6: Clarifying Questions

**Purpose**: Reduce rework by confirming user intent before planning.

**Complexity Gating**:
- Complexity 1-2: Skipped
- Complexity 3-4: Quick questions (15s timeout)
- Complexity 5+: Full questions (blocking)

**Example**:
```bash
/task-work TASK-a3f8

Phase 1.6: Clarifying Questions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Q1. Implementation Scope
    [M]inimal, [S]tandard, [C]omplete?
    Your choice: S

Q2. Testing Strategy
    [U]nit, [I]ntegration, [F]ull coverage?
    Your choice: I
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Flags**:
- `--no-questions`: Skip clarification
- `--with-questions`: Force clarification
- `--answers="1:S 2:I"`: Inline answers

### Phase 2: Implementation Planning

**Purpose**: Generate detailed implementation plan before coding.

**Outputs**:
- Files to create/modify
- Estimated lines of code
- Implementation phases
- Dependencies

**Saved To**: `.claude/task-plans/{TASK-ID}-implementation-plan.md`

### Phase 2.5B: Architectural Review

**Purpose**: Verify SOLID, DRY, and YAGNI compliance before implementation.

**Scoring**:
- **85-100**: Excellent architecture, proceed
- **60-84**: Acceptable with minor concerns
- **<60**: Blocked, redesign required

**Quality Metrics**:
```yaml
SOLID:
  single_responsibility: 9/10
  open_closed: 8/10
  liskov_substitution: 9/10
  interface_segregation: 8/10
  dependency_inversion: 9/10

DRY:
  code_duplication: 9/10
  abstraction_level: 8/10

YAGNI:
  feature_necessity: 9/10
  complexity_justification: 8/10

Overall Score: 88/100
```

**Blocking Behavior**:
```python
if architectural_score < 60:
    raise QualityGateBlocked(
        gate_name="architectural_review",
        score=45,
        threshold=60,
        message="Architecture needs redesign before implementation"
    )
```

### Phase 2.7: Complexity Evaluation

**Purpose**: Assess task complexity and determine max_turns for adversarial loop.

**Complexity Scale** (0-10):
- **1-3 (Simple)**: Basic CRUD, config changes, straightforward features
- **4-6 (Medium)**: Multi-file features, API integration, moderate logic
- **7-10 (Complex)**: State machines, parallel execution, architectural changes

**Complexity-to-Max-Turns Mapping**:
```python
COMPLEXITY_TURNS_MAP = {
    (1, 3): 3,   # Simple: Quick completion
    (4, 6): 5,   # Medium: Standard iterations
    (7, 10): 7,  # Complex: Extended iterations
}
```

**Factors Evaluated**:
- File count (0-3 points)
- Pattern familiarity (0-2 points)
- Risk assessment (0-3 points)
- Dependencies (0-2 points)

### Phase 2.8: Human Checkpoint

**Purpose**: Pause for human review on complex tasks before implementation.

**Trigger Conditions**:
- Complexity >= 7
- High-risk changes (security, breaking, schema)
- Explicit `--design-first` flag

**Checkpoint Options**:
- **[A]pprove**: Proceed to implementation
- **[M]odify**: Edit plan and re-run Phase 2.8
- **[S]implify**: Reduce scope and recalculate complexity
- **[R]eject**: Abort task (return to backlog)
- **[P]ostpone**: Save state for later

**Example**:
```bash
Phase 2.8: Human Checkpoint (Complexity 8/10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Implementation Plan Ready

Estimated Effort: 8-12 hours
Files to Create: 10
Estimated LOC: 500
Architectural Score: 92/100

[A]pprove   [M]odify   [S]implify   [R]eject   [P]ostpone

Your choice: A
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Loop Quality Gates

Loop quality gates execute **during** the Player-Coach adversarial loop, validating each implementation iteration.

### Player Agent Responsibilities

The Player agent implements code according to the approved plan and reports results:

**Player Report Structure**:
```json
{
  "task_id": "TASK-a3f8",
  "turn": 1,
  "files_modified": ["src/auth.py"],
  "files_created": ["src/oauth.py", "tests/test_oauth.py"],
  "tests_written": ["tests/test_oauth.py"],
  "tests_run": true,
  "tests_passed": true,
  "test_output_summary": "12 tests passed, 0 failed",
  "implementation_notes": "Implemented OAuth2 with token refresh",
  "concerns": [],
  "requirements_addressed": ["OAuth2 support", "Token refresh"],
  "requirements_remaining": []
}
```

### Coach Agent Responsibilities

The Coach agent validates Player implementation via two mechanisms:

1. **Task-Work Results Validation** (Lightweight, Preferred):
   - Reads Phase 4.5 test results
   - Reads Phase 5 code review scores
   - Reads Phase 5.5 plan audit results
   - Runs independent test verification

2. **Full SDK Invocation** (Fallback):
   - Used if task-work results unavailable
   - Runs complete validation independently

**Coach Decision Logic**:
```python
def validate_implementation(player_report, task):
    # Read task-work quality gate results
    test_results = read_phase_4_5_results()
    code_review = read_phase_5_results()
    plan_audit = read_phase_5_5_results()

    # Run independent tests (trust but verify)
    independent_tests = run_tests()

    # Validate requirements
    requirements_met = check_requirements(task.acceptance_criteria)

    # Quality gate checks
    if not test_results.all_passing:
        return "feedback", "Tests failing: {failed_tests}"

    if test_results.coverage.lines < 80:
        return "feedback", "Line coverage {cov}% below 80% threshold"

    if plan_audit.scope_creep_detected:
        return "feedback", "Scope creep: {variance}% LOC variance"

    if not requirements_met:
        return "feedback", "Requirements not satisfied: {missing}"

    return "approve", "Implementation meets all quality gates"
```

**Coach Decision Outcomes**:
- **approve**: Implementation ready for human review
- **feedback**: Issues detected, Player must address

**Coach Decision Structure**:
```json
{
  "task_id": "TASK-a3f8",
  "turn": 1,
  "decision": "approve",
  "quality_gates": {
    "tests": {"passed": true, "score": 100},
    "coverage": {"passed": true, "score": 87},
    "architectural_review": {"passed": true, "score": 92},
    "plan_audit": {"passed": true, "score": 95}
  },
  "independent_test_result": {
    "tests_run": true,
    "tests_passed": true,
    "command": "pytest tests/",
    "output_summary": "All tests passed"
  },
  "requirements_validation": {
    "all_met": true,
    "met": ["OAuth2 support", "Token refresh"],
    "missing": []
  },
  "rationale": "Implementation meets all quality gates"
}
```

### Phase 4.5: Test Enforcement Loop

**Purpose**: Ensure 100% test pass rate before moving task to IN_REVIEW.

**Auto-Fix Behavior**:
```python
for attempt in range(1, 4):  # Max 3 attempts
    test_results = run_tests()

    if test_results.all_passing:
        break

    if attempt < 3:
        # Auto-fix: Analyze failures and regenerate
        failures = analyze_failures(test_results)
        apply_fixes(failures)
    else:
        # Block task after 3 failed attempts
        raise QualityGateBlocked(
            gate_name="test_enforcement",
            message=f"Tests still failing after {attempt} attempts"
        )
```

**Quality Thresholds**:
- **Compilation**: 100% (must compile)
- **Tests passing**: 100% (zero failures tolerated)
- **Line coverage**: ≥80%
- **Branch coverage**: ≥75%

### Phase 5.5: Plan Audit

**Purpose**: Detect scope creep by comparing implementation to approved plan.

**Audit Checks**:
```python
def audit_implementation(plan, implementation):
    checks = {
        "files_match": compare_files(plan.files, implementation.files),
        "loc_variance": calculate_variance(plan.loc, implementation.loc),
        "scope_creep": detect_scope_creep(plan, implementation),
        "implementation_complete": check_completeness(plan, implementation)
    }

    # Acceptable variance thresholds
    if checks["loc_variance"] > 20:  # ±20%
        checks["scope_creep"] = True

    return checks
```

**Plan Audit Results**:
```yaml
files_match: true
implementation_completeness: 100%
scope_creep_detected: false
loc_variance_percent: 5
duration_variance_percent: 10
```

---

## Failure Scenarios

Understanding how quality gates handle failures helps debug blocked tasks.

### Test Failures

**Scenario**: Player reports test failures.

**Auto-Fix Loop**:
```
Turn 1: Player implements → Tests fail
        ↓
        Coach analyzes failures
        ↓
        Coach provides specific feedback

Turn 2: Player applies fixes → Tests fail
        ↓
        Coach re-analyzes
        ↓
        Coach provides updated feedback

Turn 3: Player applies fixes → Tests pass
        ↓
        Coach approves
```

**Blocking Condition**: Tests fail after 3 auto-fix attempts.

**Resolution**:
```bash
# Review failure logs
cat .guardkit/autobuild/TASK-a3f8/coach_turn_3.json

# Inspect worktree
cd .guardkit/worktrees/TASK-a3f8
pytest tests/ -v  # Run tests manually

# Fix issues and re-run task-work
/task-work TASK-a3f8 --implement-only
```

### Scope Creep Detection

**Scenario**: Implementation significantly larger than plan.

**Detection Logic**:
```python
plan_loc = 250
implementation_loc = 400
variance = (implementation_loc - plan_loc) / plan_loc * 100  # 60%

if variance > 20:
    scope_creep_detected = True
```

**Coach Feedback**:
```
Implementation 60% larger than planned (400 LOC vs 250 LOC).

Possible causes:
- Additional features added beyond acceptance criteria
- Plan underestimated complexity
- Refactoring expanded scope

Recommendations:
1. Review if new features are necessary (YAGNI)
2. Update plan to reflect actual scope
3. Split task if too large
```

**Resolution**:
```bash
# Option 1: Update plan to match implementation
/task-refine TASK-a3f8 --update-plan

# Option 2: Remove extra features
/task-work TASK-a3f8 --simplify

# Option 3: Split into multiple tasks
/task-create "Extract feature X to separate task" parent:TASK-a3f8
```

### Low Architectural Score

**Scenario**: Architectural review score < 60.

**Blocking Behavior**:
```bash
Phase 2.5B: Architectural Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ Quality Gate Blocked

Architectural Score: 45/100 (threshold: 60)

Issues:
- SOLID violations: Tight coupling in auth module
- DRY violations: Duplicate validation logic
- YAGNI concerns: Premature optimization in caching

Status: BLOCKED (pre_loop_blocked)
Worktree: Preserved for review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Resolution**:
```bash
# Review architectural issues
cat .guardkit/autobuild/TASK-a3f8/architectural-review.md

# Redesign implementation plan
/task-work TASK-a3f8 --design-only

# Address architectural concerns
# - Decouple auth module
# - Extract common validation logic
# - Remove premature optimizations

# Re-run with updated plan
/task-work TASK-a3f8 --implement-only
```

### Max Turns Exceeded

**Scenario**: Task reaches max_turns without approval.

**Outcome**:
```bash
Turn 5: Player implements → Coach provides feedback
        ↓
        Max turns (5) reached
        ↓
        Status: max_turns_exceeded
        ↓
        Worktree preserved for inspection
```

**Resolution**:
```bash
# Review turn history
cat .guardkit/autobuild/TASK-a3f8/player_turn_*.json
cat .guardkit/autobuild/TASK-a3f8/coach_turn_*.json

# Check last Coach feedback
cat .guardkit/autobuild/TASK-a3f8/coach_turn_5.json

# Options:
# 1. Manual intervention
cd .guardkit/worktrees/TASK-a3f8
# Fix issues manually
git add . && git commit -m "Manual fixes"

# 2. Increase max_turns and resume
/task-work TASK-a3f8 --resume --max-turns=10

# 3. Split into smaller tasks
/task-create "Subtask 1" parent:TASK-a3f8
/task-create "Subtask 2" parent:TASK-a3f8
```

---

## Best Practices

### When to Use AutoBuild

**Good Candidates**:
- Well-defined requirements
- Clear acceptance criteria
- Standard implementation patterns
- Low-medium risk changes

**Bad Candidates**:
- Exploratory work
- Unclear requirements
- Novel architectures
- High-risk changes requiring human judgment

### Complexity Guidelines

**Simple Tasks (1-3)**:
- Single file changes
- Config updates
- Bug fixes
- Documentation

**Medium Tasks (4-6)**:
- Multi-file features
- API integrations
- Authentication flows
- Standard CRUD operations

**Complex Tasks (7-10)**:
- State machines
- Parallel execution
- Architectural changes
- Multi-system integration

### Quality Gate Configuration

**For Simple Tasks**:
```yaml
autobuild:
  enabled: true
  max_turns: 3
  base_branch: main
```

**For Medium Tasks**:
```yaml
autobuild:
  enabled: true
  max_turns: 5
  base_branch: main
  pre_loop:
    no_questions: false  # Allow clarification
```

**For Complex Tasks**:
```yaml
autobuild:
  enabled: true
  max_turns: 7
  base_branch: main
  pre_loop:
    with_questions: true  # Force clarification
    docs: comprehensive
```

---

## Troubleshooting

### Quality Gate Not Executing

**Symptom**: Pre-loop gates skipped, immediate loop execution.

**Cause**: `enable_pre_loop: false` in orchestrator config.

**Fix**:
```python
orchestrator = AutoBuildOrchestrator(
    repo_root=Path.cwd(),
    max_turns=5,
    enable_pre_loop=True,  # Enable pre-loop gates
)
```

### Checkpoint Not Triggering

**Symptom**: Complex task proceeds without human checkpoint.

**Cause**: Complexity evaluation incorrect or checkpoint bypassed.

**Fix**:
```bash
# Force design-first workflow
/task-work TASK-a3f8 --design-only

# Review and approve plan manually
cat .claude/task-plans/TASK-a3f8-implementation-plan.md

# Proceed to implementation
/task-work TASK-a3f8 --implement-only
```

### Tests Keep Failing

**Symptom**: Tests fail repeatedly, auto-fix loop exhausted.

**Cause**: Test assumptions incorrect or environment issues.

**Debug Steps**:
```bash
# 1. Review test failures
cd .guardkit/worktrees/TASK-a3f8
pytest tests/ -v --tb=short

# 2. Check test assumptions
cat tests/test_feature.py

# 3. Verify environment
python -m pytest --version
pip list | grep -i test

# 4. Run tests individually
pytest tests/test_feature.py::test_specific_case -v

# 5. Fix and re-run
/task-work TASK-a3f8 --implement-only
```

### Worktree Not Preserved

**Symptom**: Worktree deleted after orchestration.

**Cause**: None - worktrees are **always** preserved per architectural review.

**Verify**:
```bash
ls -la .guardkit/worktrees/TASK-a3f8
git worktree list
```

### Coach Always Provides Feedback

**Symptom**: Coach never approves, continuous feedback loop.

**Cause**: Quality thresholds too strict or legitimate quality issues.

**Debug**:
```bash
# Review Coach decisions
cat .guardkit/autobuild/TASK-a3f8/coach_turn_*.json

# Check quality gate scores
cat .guardkit/autobuild/TASK-a3f8/task_work_results.json

# Adjust thresholds if needed (in task frontmatter)
quality_thresholds:
  line_coverage: 75  # Lower from 80%
  branch_coverage: 70  # Lower from 75%
```

---

## Related Documentation

- [AutoBuild Overview](../CLAUDE.md#autobuild---autonomous-task-implementation)
- [Task Workflow](../CLAUDE.md#workflow-overview)
- [BDD Workflow for Agentic Systems](./bdd-workflow-for-agentic-systems.md)
- [Design-First Workflow](./design-first-workflow.md)

---

## Summary

Quality gates provide automated quality enforcement at three stages:

1. **Pre-Loop** (Phases 1.6-2.8): Validate design before implementation
2. **Loop** (Player-Coach turns): Validate each implementation iteration
3. **Post-Loop** (Finalization): Preserve worktree for human review

Key benefits:
- **Prevents broken code** from reaching production
- **Automates quality verification** (tests, coverage, architecture)
- **Reduces rework** through early detection of issues
- **Provides transparency** via detailed turn history and reports

Remember: Quality gates are **enablers**, not blockers. They catch issues early when they're cheaper to fix, reducing total development time.
