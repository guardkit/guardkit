# Implementation Guide: Architectural Score Gate Fix

## Wave Execution Strategy

This feature uses 3 sequential waves with dependency chains. Each wave must complete before the next begins.

---

## Wave 1: Bug Fix (Blocking)

**Priority**: P0 - Critical
**Parallel Execution**: Yes (2 tasks can run in parallel)
**Estimated Duration**: 2-4 hours

### Tasks

| Task | Title | Workspace | Method |
|------|-------|-----------|--------|
| TASK-FBSDK-018 | Write code_review.score to task_work_results.json | arch-score-fix-wave1-1 | task-work |
| TASK-FBSDK-019 | Persist Phase 2.5B results for implement-only mode | arch-score-fix-wave1-2 | task-work |

### Execution Commands

```bash
# Parallel execution with Conductor (recommended)
conductor workspace create arch-score-fix-wave1-1
conductor workspace create arch-score-fix-wave1-2

# In workspace 1:
/task-work TASK-FBSDK-018

# In workspace 2:
/task-work TASK-FBSDK-019

# Or sequential:
/task-work TASK-FBSDK-018
/task-work TASK-FBSDK-019
```

### Verification

After Wave 1 completion, verify:
```bash
# Run unit tests
pytest tests/unit/test_agent_invoker_task_work_results.py -v
pytest tests/unit/test_coach_validator.py -v

# Check task_work_results.json includes code_review field
cat .guardkit/autobuild/TASK-XXX/task_work_results.json | jq '.code_review'
```

---

## Wave 2: Task Type Profiles

**Priority**: P1 - High
**Parallel Execution**: Partial (TASK-FBSDK-020 first, then 021/022 in parallel)
**Estimated Duration**: 4-8 hours
**Dependencies**: Wave 1 complete

### Tasks

| Task | Title | Workspace | Method | Depends On |
|------|-------|-----------|--------|------------|
| TASK-FBSDK-020 | Define task type schema and quality gate profiles | arch-score-fix-wave2-1 | task-work | Wave 1 |
| TASK-FBSDK-021 | Modify CoachValidator to apply task type profiles | arch-score-fix-wave2-2 | task-work | TASK-FBSDK-020 |
| TASK-FBSDK-022 | Update feature-plan to auto-detect task types | arch-score-fix-wave2-3 | task-work | TASK-FBSDK-020 |

### Execution Commands

```bash
# Phase 1: Define schema first
/task-work TASK-FBSDK-020

# Phase 2: Parallel execution of consumers
conductor workspace create arch-score-fix-wave2-2
conductor workspace create arch-score-fix-wave2-3

# In workspace 2:
/task-work TASK-FBSDK-021

# In workspace 3:
/task-work TASK-FBSDK-022
```

### Quality Gate Profiles

The following profiles should be implemented:

| Task Type | Arch Review | Coverage | Tests | Plan Audit |
|-----------|-------------|----------|-------|------------|
| `scaffolding` | Skip | Skip | Optional | Required |
| `feature` (default) | Required ≥60 | Required ≥80% | Required | Required |
| `infrastructure` | Skip | Skip | Required | Required |
| `documentation` | Skip | Skip | Skip | Skip |

### Verification

After Wave 2 completion:
```bash
# Run integration tests
pytest tests/integration/test_quality_gate_profiles.py -v

# Test scaffolding task passes without arch review
guardkit autobuild task TASK-SCAFFOLDING-001 --dry-run
```

---

## Wave 3: Overrides and Testing

**Priority**: P2 - Medium
**Parallel Execution**: Yes (2 tasks can run in parallel)
**Estimated Duration**: 2-4 hours
**Dependencies**: Wave 2 complete

### Tasks

| Task | Title | Workspace | Method |
|------|-------|-----------|--------|
| TASK-FBSDK-023 | Add skip_arch_review CLI and frontmatter flags | arch-score-fix-wave3-1 | task-work |
| TASK-FBSDK-024 | Create feature-code test case for quality gates | arch-score-fix-wave3-2 | task-work |

### Execution Commands

```bash
# Parallel execution
conductor workspace create arch-score-fix-wave3-1
conductor workspace create arch-score-fix-wave3-2

# In workspace 1:
/task-work TASK-FBSDK-023

# In workspace 2:
/task-work TASK-FBSDK-024
```

### Verification

After Wave 3 completion:
```bash
# Test override flag
guardkit autobuild task TASK-XXX --skip-arch-review

# Run feature-code test case
guardkit autobuild feature FEAT-TEST-CODE --max-turns 5

# Full test suite
pytest tests/ -v --cov=guardkit --cov-report=term
```

---

## Final Verification

After all waves complete:

```bash
# 1. Re-run original failing test case
cd /path/to/simple_feature_test
guardkit autobuild feature FEAT-1D98 --max-turns 5

# Expected: Wave 1 scaffolding task passes (skips arch review)
# Expected: Feature tasks evaluate arch review correctly

# 2. Run full test suite
pytest tests/ -v --cov=guardkit

# 3. Check for regressions
guardkit doctor
```

---

## Rollback Plan

If issues are discovered after deployment:

1. **Wave 3 rollback**: Remove CLI flags, revert test case
2. **Wave 2 rollback**: Remove task type profiles, use default behavior
3. **Wave 1 rollback**: Revert to previous agent_invoker.py

Each wave is independently revertable without affecting prior waves.

---

## Key Files to Modify

### Wave 1
- `guardkit/orchestrator/agent_invoker.py` (write code_review field)
- `guardkit/orchestrator/quality_gates/coach_validator.py` (verify reading)
- `tests/unit/test_agent_invoker_task_work_results.py` (add tests)

### Wave 2
- `guardkit/models/task_types.py` (new file: task type enum and profiles)
- `guardkit/orchestrator/quality_gates/coach_validator.py` (apply profiles)
- `installer/core/commands/feature-plan.md` (auto-detection logic)

### Wave 3
- `guardkit/cli/autobuild.py` (add --skip-arch-review flag)
- `guardkit/orchestrator/autobuild.py` (read frontmatter flag)
- `tests/integration/test_feature_code.py` (new test case)
