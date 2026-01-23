# Review Report: TASK-REV-FBVAL (Revised)

## Executive Summary

This review evaluates the **fundamental health of the feature-build system** before investing in additional Coach improvements. The user requested a revised analysis to verify basic infrastructure works.

**Key Finding**: The feature-build infrastructure WORKS. All orchestration, state management, SDK integration, worktree handling, and reporting components function correctly. The failures are **calibration bugs**, not architectural problems.

**Root Causes Identified**:
1. `code_review.score` not written to task_work_results.json (Coach sees score=0)
2. Independent test verification runs for scaffolding tasks (fails when no tests exist)

**Decision**: [I]mplement - Created two bug fix tasks to address root causes.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Duration**: 1.5 hours
- **Evidence Sources**:
  - TASK-REV-FB22 review report and test output
  - TASK-REV-CSC1 context-sensitive coach proposal
  - Feature-build documentation (`.claude/rules/autobuild.md`)
  - FastAPI template (`installer/core/templates/fastapi-python/`)

## Decision Analysis

### The Core Question

**Should we create a new FastAPI test project to validate feature-build before implementing FEAT-4C15?**

### Option Analysis

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **A: Full Validation First** | Create test project, run all proposed phases | Formal baseline, reusable test bed, comprehensive | Delays FEAT-4C15 by 1-2 weeks, redundant with FHA-* data | 4/10 |
| **B: Use Existing Baseline** | Proceed with FEAT-4C15 using FHA-* data | Immediate progress, data exists, faster to fix | Less formal, single test scenario | **8/10** |
| **C: Hybrid Approach** | Minimal test setup + parallel implementation | Quick validation, some new data | Complex coordination, split focus | 5/10 |
| **D: Defer Validation** | Focus solely on implementation | Maximum velocity | No comparison baseline | 3/10 |

### Selected Option: B (Use Existing Baseline)

**Rationale**:

1. **Data Already Exists**
   - TASK-REV-FB22 ran FHA-001 through FHA-005 (5 tasks)
   - 3 different task types tested
   - 15 Player-Coach iterations completed
   - Clear failure patterns documented

2. **Root Cause Well-Understood**
   - Quality gates are binary (same 60-threshold for all features)
   - Complexity scores exist but don't modulate thresholds
   - Simple code (20-30 LOC) fails gates designed for complex features

3. **Redundant Effort**
   - Proposed test would confirm same failures
   - No new information would be gained
   - Delays the actual fix by 1-2 weeks

4. **Better Validation Strategy**
   - Use FHA-* data as "before" baseline
   - Implement FEAT-4C15 to fix the issue
   - Create test project as "after" validation
   - Compare metrics to prove effectiveness

## Existing Baseline Data

### From TASK-REV-FB22 Test Run

| Task | Type | Complexity | LOC | Result | Failure Mode |
|------|------|------------|-----|--------|--------------|
| FHA-001 | scaffolding | 2 | ~15 | Gates passed, independent test failed | Bootstrap problem |
| FHA-002 | feature | 3 | ~30 | Gates failed | Arch review below threshold |
| FHA-003 | feature | 2 | ~20 | Gates failed | Arch review below threshold |
| FHA-004 | feature | 4 | N/A | Not reached | Blocked by Wave 1 |
| FHA-005 | feature | 3 | N/A | Not reached | Blocked by Wave 1 |

### Key Observations

1. **scaffolding type works**: FHA-001 passed quality gates (arch_review_required=False)
2. **feature type fails for simple tasks**: FHA-002/003 failed despite being simple boilerplate
3. **Root cause clear**: 20-30 LOC can't achieve 60+ arch review score
4. **Pattern repeatable**: Same failure across multiple turns (5 turns × 3 tasks)

## Preserved Validation Framework

The proposed test framework should be **preserved for post-implementation validation**:

### Proposed Project Structure

```
~/Projects/test-projects/fastapi-feature-build-validation/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   └── crud/
├── tests/
├── alembic/
├── pyproject.toml
└── README.md
```

### Metrics Framework (For Future Use)

| Metric | Description | Target (Post-FEAT-4C15) |
|--------|-------------|-------------------------|
| **Completion Rate** | Tasks approved / total | ≥80% |
| **Average Turns** | Iterations to approval | ≤3 |
| **Inappropriate Gate Failures** | Simple tasks failing strict gates | 0 |
| **Coverage (testable code)** | For code with testable logic | ≥70% |
| **Arch Review (complex only)** | For complexity ≥5 | ≥60 |

### Task Categories (For Future Test Phases)

**Phase 1: Scaffolding** (Should pass now)
- Create project structure
- Add configuration management
- Database setup

**Phase 2: Simple Features** (Currently fail, should pass after FEAT-4C15)
- Health endpoints (complexity 2-3)
- Basic CRUD operations (complexity 3-4)

**Phase 3: Complex Features** (Should require full gates)
- Authentication system (complexity 6-7)
- Related entity management (complexity 5-6)

## Recommendations

### Immediate Actions

1. **Accept this review** - Archive findings, proceed with implementation
2. **Use existing baseline** - Reference FHA-* data for FEAT-4C15 calibration
3. **Proceed to FEAT-4C15** - Context-Sensitive Coach implementation

### Post-Implementation Actions

1. **Create test FastAPI project** - Per proposed structure
2. **Run feature-build with new thresholds** - Generate "after" data
3. **Compare before/after metrics** - Prove FEAT-4C15 effectiveness
4. **Document findings** - Update validation report

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Existing data insufficient | Low | Medium | FHA-* covers key failure modes |
| FEAT-4C15 implementation issues | Medium | High | Incremental testing during implementation |
| Test project scope creep | Medium | Medium | Strict phase boundaries, MVP focus |
| Validation delayed indefinitely | Low | Low | Schedule validation as follow-up task |

## Conclusions

Creating a new FastAPI test project **before** FEAT-4C15 would delay the fix without providing new information. The existing FHA-* test data from TASK-REV-FB22 demonstrates:

1. The problem exists (simple features fail strict gates)
2. The root cause is understood (binary thresholds don't fit complexity spectrum)
3. The solution is designed (Context-Sensitive Coach)

The proposed validation framework is **valuable but should be executed after implementation** to prove the fix works, not before to confirm the problem we already understand.

---

## Fundamental Health Assessment (Revised Analysis)

### Infrastructure Status

| Component | Status | Evidence |
|-----------|--------|----------|
| Feature Loading | ✅ Working | Loaded FEAT-A96D, 5 tasks, 3 waves |
| Worktree Creation | ✅ Working | Created `.guardkit/worktrees/FEAT-A96D` |
| Wave Orchestration | ✅ Working | Executed 3 parallel tasks in Wave 1 |
| Task State Transitions | ✅ Working | backlog → design_approved → in_progress → in_review |
| SDK Invocation | ✅ Working | Claude Agent SDK called, received responses |
| Player Execution | ✅ Working | task-work completed, created 33+ files |
| Coach Validation | ✅ Working | CoachValidator ran after every turn |
| State Persistence | ✅ Working | JSON reports saved for all turns |
| Progress Display | ✅ Working | Rich TUI showed all 15 turns |

**Verdict**: Infrastructure is sound. Problems are calibration bugs.

### Root Causes

1. **`code_review.score` not written** - Architectural reviewer may run, but score not captured in task_work_results.json. Coach defaults to 0.

2. **Independent tests run for scaffolding** - Profile sets `tests_required=False` for scaffolding, but independent test verification still runs and fails when tests don't exist.

## Implementation Tasks Created

### TASK-FIX-ARCH: Fix architectural review score not written
- **Priority**: High
- **Complexity**: 4
- **Goal**: Trace and fix data flow so `code_review.score` is populated
- **Impact**: Enables proper quality gate evaluation

### TASK-FIX-SCAF: Skip independent tests for scaffolding
- **Priority**: High
- **Complexity**: 2
- **Goal**: Honor `tests_required=False` in independent test verification
- **Impact**: Scaffolding tasks can complete successfully

## Recommended Execution Order

1. **TASK-FIX-SCAF** (complexity 2) - Quick win, unblocks scaffolding tasks
2. **TASK-FIX-ARCH** (complexity 4) - Requires investigation, unblocks feature tasks

After both fixes, re-run feature-build test to verify. If simple feature tasks still fail arch review, THEN consider complexity-modulated thresholds (FEAT-4C15).

---

**Review Status**: COMPLETED
**Decision**: [I]mplement - Created bug fix tasks

**Tasks Created**:
- `tasks/backlog/TASK-FIX-ARCH-fix-arch-review-score-missing.md`
- `tasks/backlog/TASK-FIX-SCAF-skip-independent-tests-scaffolding.md`

---

*Generated by /task-review on 2026-01-23*
*Review Mode: decision, Depth: standard (revised for fundamental health check)*
