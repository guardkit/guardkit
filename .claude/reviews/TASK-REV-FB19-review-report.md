# Review Report: TASK-REV-FB19

**Task**: Analyze feature-build test results and architectural score gate issue
**Mode**: Decision Analysis
**Depth**: Standard
**Date**: 2025-01-21

---

## Executive Summary

The feature-build workflow is functioning correctly, but the AutoBuild test against FEAT-1D98 (FastAPI Health App) failed due to **two distinct issues**:

1. **PRIMARY (Bug)**: The `code_review.score` field is not being written to `task_work_results.json`, causing CoachValidator to default to score=0, which always fails the ≥60 threshold.

2. **SECONDARY (Design Gap)**: Even if the bug is fixed, applying architectural review (SOLID/DRY/YAGNI) to scaffolding tasks like "Setup project structure and pyproject.toml" is inappropriate - there's no code architecture to review.

The recommended path forward involves both a bug fix and a task type-based quality gate profile system.

---

## Root Cause Analysis

### Finding 1: Missing Architectural Score in task_work_results.json (BUG)

**Severity**: Critical
**Evidence**: `guardkit/orchestrator/agent_invoker.py:2239-2256`

The `_write_task_work_results()` method creates the following structure:

```python
results: Dict[str, Any] = {
    "task_id": task_id,
    "timestamp": ...,
    "completed": completed,
    "phases": result_data.get("phases", {}),
    "quality_gates": {
        "tests_passing": ...,
        "tests_passed": ...,
        "tests_failed": ...,
        "coverage": ...,
        "coverage_met": ...,
        "all_passed": ...,
    },
    "files_modified": ...,
    "files_created": ...,
    "summary": ...,
}
```

**Note the absence of `code_review` field.**

Meanwhile, CoachValidator expects (`coach_validator.py:466-472`):

```python
code_review = task_work_results.get("code_review", {})
arch_score = code_review.get("score", 0)  # Default to 0 if not present
arch_review_passed = arch_score >= self.ARCH_REVIEW_THRESHOLD  # 60
```

**Result**: Score defaults to 0, which is always < 60, causing consistent failure.

### Finding 2: Phase 2.5B Results Not Persisted

**Severity**: Critical
**Evidence**: The architectural review happens in Phase 2.5B during `task-work --design-only`, but when `--implement-only` runs (which is what AutoBuild uses), it skips Phase 2.5 entirely.

**Flow**:
1. AutoBuild Pre-Loop: `task-work --design-only` → Phase 2.5B runs, score generated (but not persisted)
2. AutoBuild Loop: `task-work --implement-only` → Phase 3-5.5 only, no architectural review
3. Coach reads `task_work_results.json` → No `code_review.score` field → defaults to 0

**Note**: In the test case, pre-loop was disabled (`enable_pre_loop=False`), so Phase 2.5B never ran at all.

### Finding 3: Inappropriate Quality Gates for Scaffolding Tasks

**Severity**: Design Gap
**Evidence**: TASK-HLTH-61B6 "Setup project structure and pyproject.toml"

The task creates:
- `pyproject.toml` - Configuration file
- Directory structure

There is **no code architecture** to evaluate against SOLID/DRY/YAGNI. Applying these principles to configuration files is nonsensical.

### Finding 4: Coverage Gate Behavior (Secondary)

**Severity**: Low (consequential)
**Evidence**: Turns 4-5 showed `coverage_met=None`

When no tests exist (scaffolding task), coverage calculation returns None. The coach interprets `None` as failure:

```python
coverage_met = quality_gates.get("coverage_met", True)  # Default True if not present
```

This is actually correct behavior - it defaults to True when absent. The real issue is the architectural score gate.

---

## Decision Analysis

### Option A: Fix Bug Only (Minimal Intervention)

**Description**: Write `code_review.score` to `task_work_results.json` during Phase 2.5B and persist it for Coach validation.

**Pros**:
- Fixes immediate blocker
- Minimal code change
- Preserves current quality gate model

**Cons**:
- Scaffolding tasks will still need >60 architectural score
- Doesn't address fundamental mismatch between task types and quality gates
- May still fail on config-only tasks

**Effort**: Low (1-2 hours)
**Risk**: Medium - may just shift the failure to "score is low because there's no architecture"

### Option B: Task Type-Based Quality Gate Profiles (Comprehensive)

**Description**: Introduce task type classification with different quality gate profiles:

| Task Type | Arch Review | Coverage | Tests | Plan Audit |
|-----------|-------------|----------|-------|------------|
| scaffolding | Skip | Skip | Optional | Required |
| feature | Required ≥60 | Required ≥80% | Required | Required |
| infrastructure | Skip | Skip | Required | Required |
| documentation | Skip | Skip | Skip | Skip |

**Implementation**:
1. Add `task_type` field to task frontmatter (default: `feature`)
2. Modify CoachValidator to read task type and apply appropriate profile
3. Add CLI flag `--skip-arch-review` for manual override

**Pros**:
- Addresses root design issue
- Makes quality gates contextually appropriate
- Scaffolding tasks pass naturally
- Clear mental model for users

**Cons**:
- More implementation effort
- Requires task metadata changes
- Potential for misclassification

**Effort**: Medium (4-8 hours)
**Risk**: Low - well-defined scope, backwards compatible

### Option C: Override Mechanism Only

**Description**: Add explicit skip flags without task type classification:

```yaml
autobuild:
  skip_arch_review: true
  skip_coverage: true
```

**Pros**:
- Quick to implement
- User has full control

**Cons**:
- Requires manual annotation per task
- No automatic intelligence
- Error-prone for feature planning

**Effort**: Low-Medium (2-4 hours)
**Risk**: Medium - shifts burden to users

### Option D: Hybrid Approach (Recommended)

**Description**: Fix the bug (Option A) AND implement task type profiles (Option B), plus allow manual overrides (Option C).

**Implementation Order**:
1. **Immediate**: Fix the `code_review.score` persistence bug
2. **Short-term**: Add task type classification with default profiles
3. **Ongoing**: Allow manual overrides for edge cases

**Effort**: Medium (6-12 hours total)
**Risk**: Low - incremental delivery, each step adds value

---

## Decision Matrix

| Criterion | Weight | Option A | Option B | Option C | Option D |
|-----------|--------|----------|----------|----------|----------|
| Fixes immediate bug | 30% | ✅ 10 | ✅ 10 | ❌ 0 | ✅ 10 |
| Handles scaffolding tasks | 25% | ❌ 3 | ✅ 10 | ✅ 8 | ✅ 10 |
| Implementation effort | 15% | ✅ 10 | ⚠️ 6 | ✅ 8 | ⚠️ 5 |
| User experience | 15% | ⚠️ 5 | ✅ 9 | ⚠️ 6 | ✅ 9 |
| Backwards compatible | 15% | ✅ 10 | ✅ 8 | ✅ 10 | ✅ 8 |
| **Weighted Score** | | **7.2** | **8.6** | **6.2** | **8.6** |

**Recommendation**: **Option D (Hybrid Approach)** - provides both immediate fix and long-term solution.

---

## Secondary Analysis: Test Scenario Selection

### Current Test Case
- FEAT-1D98: FastAPI Health App
- First task: "Setup project structure and pyproject.toml" (scaffolding)

### Assessment
This is a **reasonable test case** for validating the overall feature-build workflow, but it exposed quality gate issues because:
1. It starts with scaffolding (Wave 1)
2. Scaffolding doesn't produce code to review architecturally

### Alternative Test Scenarios

| Scenario | Tests | Appropriate For |
|----------|-------|-----------------|
| Health endpoint scaffolding | Workflow, worktree mgmt | End-to-end integration |
| CRUD endpoint implementation | All quality gates | Feature code validation |
| Adding validation to endpoint | Code review, tests | Incremental development |
| Algorithm implementation | TDD mode, coverage | Test-first validation |

### Recommendation
Keep the current test case for integration testing, but add a second test case that starts with a **feature task** (not scaffolding) to validate quality gates appropriately.

---

## Findings Summary

| # | Finding | Severity | Category |
|---|---------|----------|----------|
| 1 | `code_review.score` not written to `task_work_results.json` | Critical | Bug |
| 2 | Phase 2.5B results not persisted for `--implement-only` | Critical | Bug |
| 3 | Architectural review inappropriate for scaffolding tasks | High | Design |
| 4 | No task type classification system | Medium | Design |
| 5 | Coverage gate fails on config-only tasks | Low | Design |

---

## Recommendations

### R1: Fix Architectural Score Persistence (Priority: P0)

**What**: Modify `_write_task_work_results()` to include `code_review.score` field.

**Where**: `guardkit/orchestrator/agent_invoker.py:2239-2256`

**Implementation**:
```python
results: Dict[str, Any] = {
    # ... existing fields ...
    "code_review": {
        "score": result_data.get("architectural_review", {}).get("score", 0),
        "solid_score": result_data.get("architectural_review", {}).get("solid_score"),
        "dry_score": result_data.get("architectural_review", {}).get("dry_score"),
        "yagni_score": result_data.get("architectural_review", {}).get("yagni_score"),
    },
    "plan_audit": {
        "violations": result_data.get("plan_audit", {}).get("violations", 0),
    },
}
```

### R2: Implement Task Type Quality Gate Profiles (Priority: P1)

**What**: Add task type classification with appropriate quality gate profiles.

**Types**:
- `scaffolding`: Skip arch review, skip coverage
- `feature`: All gates required (default)
- `infrastructure`: Skip arch review, require tests
- `documentation`: Minimal gates

**Where**:
- Task frontmatter: `task_type: scaffolding`
- CoachValidator: Read task type, apply profile

### R3: Add Manual Override Flags (Priority: P2)

**What**: Allow explicit quality gate overrides in task frontmatter or CLI.

**Options**:
```yaml
autobuild:
  skip_arch_review: true
  skip_coverage: true
```

Or CLI: `guardkit autobuild task TASK-XXX --skip-arch-review`

### R4: Add Feature Code Test Case (Priority: P2)

**What**: Create a second feature-build test that starts with a feature task (not scaffolding) to validate quality gates work correctly for code.

---

## Implementation Tasks (If Approved)

### Wave 1: Bug Fix (Blocking)

| Task ID | Title | Complexity | Dependencies |
|---------|-------|------------|--------------|
| TASK-FBSDK-018 | Write code_review.score to task_work_results.json | 3 | None |
| TASK-FBSDK-019 | Persist Phase 2.5B results for implement-only mode | 4 | TASK-FBSDK-018 |

### Wave 2: Task Type Profiles

| Task ID | Title | Complexity | Dependencies |
|---------|-------|------------|--------------|
| TASK-FBSDK-020 | Define task type schema and quality gate profiles | 4 | None |
| TASK-FBSDK-021 | Modify CoachValidator to apply task type profiles | 5 | TASK-FBSDK-020 |
| TASK-FBSDK-022 | Update feature-plan to auto-detect task types | 4 | TASK-FBSDK-020 |

### Wave 3: Overrides and Testing

| Task ID | Title | Complexity | Dependencies |
|---------|-------|------------|--------------|
| TASK-FBSDK-023 | Add skip_arch_review CLI and frontmatter flags | 3 | TASK-FBSDK-021 |
| TASK-FBSDK-024 | Create feature-code test case for quality gates | 3 | TASK-FBSDK-019 |

---

## Appendix: Code References

### CoachValidator Quality Gate Check
`guardkit/orchestrator/quality_gates/coach_validator.py:466-472`

### Task Work Results Writer
`guardkit/orchestrator/agent_invoker.py:2178-2269`

### Test Log Reference
`docs/reviews/feature-build/after_FBSDK-015_016_017.md`

---

## Review Metadata

```yaml
review_id: TASK-REV-FB19
mode: decision
depth: standard
duration: ~2 hours
findings_count: 5
recommendations_count: 4
decision: Option D (Hybrid Approach)
```
