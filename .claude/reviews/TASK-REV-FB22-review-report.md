# Review Report: TASK-REV-FB22 (Revised)

## Executive Summary

This review analyzes the feature-build test results from `docs/reviews/feature-build/after_FB21_fixes.md` following TASK-REV-FB21 fixes. The initial analysis identified surface-level issues, but deeper investigation reveals **systemic design limitations** in the quality gate system.

**Key Finding**: The task_type + profile system is too binary. Simple feature tasks (complexity 2-3) are held to the same architectural review standards as complex features (complexity 7+), causing legitimate implementations to fail.

## Review Details

- **Mode**: Decision Analysis (Revised)
- **Depth**: Comprehensive (per user request)
- **Evidence**: Task files with autobuild state, feature-plan spec, task_types.py

## Deep Analysis: The Actual Task Files

### TASK-FHA-001 (Correctly Handled)
```yaml
task_type: scaffolding
complexity: 2
```
- **Title**: "Create project structure and pyproject.toml"
- **Creates**: Directories, pyproject.toml, requirements files
- **Profile Used**: scaffolding (arch_review_required=False)
- **Result**: Quality gates ALL_PASSED=True
- **Failure**: Independent test verification (bootstrap problem - tests don't exist)

### TASK-FHA-002 (Problematic)
```yaml
task_type: feature
complexity: 3
```
- **Title**: "Implement core configuration"
- **Creates**: 30-line Pydantic Settings class, .env.example
- **Profile Used**: feature (arch_review_required=True, threshold=60)
- **Result**: `arch_review_passed=False` (score not written, defaults to 0)
- **The Question**: Should a 30-line config file require 60+ architectural review score?

### TASK-FHA-003 (Problematic)
```yaml
task_type: feature
complexity: 2
```
- **Title**: "Create FastAPI app entry point"
- **Creates**: ~20-line main.py with app initialization
- **Profile Used**: feature (arch_review_required=True, threshold=60)
- **Result**: `arch_review_passed=False`
- **The Question**: Should a 20-line app initialization require 60+ architectural review score?

## Root Cause Analysis

### Layer 1: task_type Pattern Matching Inconsistency

Per feature-plan.md (lines 960-968), the rules are:
- "Create project structure", "Setup...", "Initialize...", "Configure..." → `scaffolding`
- "Implement..." → `feature`

**Observation**:
- FHA-003 title is "**Create** FastAPI app entry point"
- Rule says "Create..." → scaffolding
- But it was assigned `feature`

**Root Cause**: Either the pattern matching isn't working, or "Create X" where X sounds like "code" (FastAPI app) triggers feature instead.

### Layer 2: The Scaffolding/Feature Boundary is Poorly Defined

The current definition from `task_types.py`:
```python
SCAFFOLDING: "Configuration files, project setup, templates"
FEATURE: "Feature implementation, bug fixes, enhancements"
```

**The Gray Zone**:
- Creating a Pydantic Settings class - config or feature?
- Creating FastAPI app initialization - setup or feature?
- Both write Python code, but both are foundational boilerplate

**The Problem**: These tasks ARE writing code (not just config files), so `feature` isn't wrong per se. But they're **simple** code with no real architecture to review.

### Layer 3: Quality Gates Lack Complexity Sensitivity

Current system from `task_types.py`:
```python
TaskType.FEATURE: QualityGateProfile(
    arch_review_required=True,
    arch_review_threshold=60,  # Fixed threshold regardless of complexity
    ...
)
```

**The Problem**:
- A complexity-2 task (20-line app init) has same threshold as complexity-8 (authentication system)
- The system has no concept of "simple feature" vs "complex feature"
- Complexity score exists but isn't used to modulate quality gate requirements

### Layer 4: Architectural Review Score Not Being Written

The `code_review.score` field is missing from `task_work_results.json`:

```python
# coach_validator.py line 576
code_review = task_work_results.get("code_review", {})
arch_score = code_review.get("score", 0)  # Default to 0 if not present
```

**Question**: Is the architectural reviewer even running? Or is it running but not writing the score?

This needs investigation, but even if fixed, a 20-line config file might still not score 60+.

## Proposed Solutions

### Solution 1: Add Complexity-Modulated Thresholds (Recommended)

Instead of static threshold=60 for all features, modulate based on complexity:

```python
def get_arch_review_threshold(complexity: int) -> int:
    """Return arch review threshold based on task complexity.

    Complexity 1-3: No arch review (simple code)
    Complexity 4-5: Lower threshold (40)
    Complexity 6-7: Standard threshold (60)
    Complexity 8+:  Higher threshold (70)
    """
    if complexity <= 3:
        return 0  # Skip arch review for simple tasks
    elif complexity <= 5:
        return 40
    elif complexity <= 7:
        return 60
    else:
        return 70
```

**Benefits**:
- Simple feature tasks (complexity 2-3) get appropriate rigor
- Complex tasks still get full scrutiny
- Uses existing complexity scores (no new data needed)

### Solution 2: Add SIMPLE_FEATURE Task Type

Add a new task type for simple implementation tasks:

```python
TaskType.SIMPLE_FEATURE = "simple_feature"

DEFAULT_PROFILES[TaskType.SIMPLE_FEATURE] = QualityGateProfile(
    arch_review_required=False,  # Or True with threshold=40
    arch_review_threshold=0,
    coverage_required=True,
    coverage_threshold=70.0,  # Slightly lower
    tests_required=True,
    plan_audit_required=True,
)
```

**Assignment Rule**:
- `feature` tasks with complexity ≤ 3 → `simple_feature`
- Or detect via heuristics (LOC, single-file, boilerplate patterns)

### Solution 3: Smarter Coach Analysis

Make Coach more context-aware:

1. **Examine actual implementation scope**:
   - Lines of code changed
   - Number of files modified
   - Cyclomatic complexity of new code

2. **Adjust expectations dynamically**:
   - 20 LOC + 1 file + simple patterns → skip/reduce arch review
   - 500 LOC + 10 files + complex logic → full arch review

3. **Log rationale**:
   - "Skipping arch review: implementation scope (23 LOC, 1 file) below threshold"

### Solution 4: Fix Independent Test Verification for Scaffolding

The bootstrap problem: scaffolding task creates test infrastructure, but Coach tries to run tests before they exist.

```python
# In CoachValidator.validate()
if profile.tests_required is False:
    # Skip independent test verification for scaffolding
    test_result = IndependentTestResult(
        tests_passed=True,
        test_command="skipped",
        test_output_summary="Independent test verification skipped for scaffolding task",
        duration_seconds=0.0,
    )
else:
    test_result = self.run_independent_tests()
```

### Solution 5: Fix code_review.score Writing

Ensure the architectural review actually writes its score to task_work_results.json:

```python
# In agent_invoker or task-work result writer
task_work_results["code_review"] = {
    "score": arch_review_score,
    "threshold": profile.arch_review_threshold,
    "passed": arch_review_score >= profile.arch_review_threshold,
}
```

## Recommended Implementation Order

| Priority | Solution | Impact | Effort |
|----------|----------|--------|--------|
| 1 | Solution 1 (Complexity-modulated thresholds) | High | Medium |
| 2 | Solution 4 (Fix scaffolding independent tests) | Medium | Low |
| 3 | Solution 5 (Ensure code_review.score written) | Medium | Low |
| 4 | Solution 3 (Smart Coach analysis) | High | High |

**Why Solution 1 First**:
- Addresses the fundamental design limitation
- Uses existing data (complexity scores)
- Minimal code change (add function, update profile lookup)
- Immediately benefits all feature tasks

## Evidence Summary

### Task State from Autobuild

**TASK-FHA-002** (5 turns, all failed):
```yaml
turns:
- turn: 1
  feedback: '- Architectural review score below threshold: '
- turn: 2
  feedback: '- task-work execution exceeded 600s timeout: '
- turn: 3
  feedback: '- Architectural review score below threshold: '
- turn: 4
  feedback: "- Coverage threshold not met: \n- Architectural review score below threshold: "
- turn: 5
  feedback: '- Architectural review score below threshold: '
```

**TASK-FHA-003** (5 turns, all failed):
```yaml
turns:
- turn: 1
  feedback: '- task-work execution exceeded 600s timeout: '
- turn: 2
  feedback: '- Architectural review score below threshold: '
- turn: 5
  feedback: "- Tests did not pass: \n- Coverage threshold not met: \n- Architectural review score below threshold: "
```

### Log Evidence

From test output, showing profile selection:
```
TASK-FHA-001: "Using quality gate profile for task type: scaffolding"
              → ALL_PASSED=True (but fails independent tests)

TASK-FHA-002: "Using quality gate profile for task type: feature"
              → arch_review_passed=False, ALL_PASSED=False

TASK-FHA-003: "Using quality gate profile for task type: feature"
              → arch_review_passed=False, ALL_PASSED=False
```

## Progress Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| Task type data flow fix | Working | scaffolding detected when set |
| Profile selection | Working | Correct profile used per task_type |
| Arch review scoring | Not Working | code_review.score not being written |
| System design | Needs Enhancement | Binary thresholds don't fit reality |

## Conclusions

The TASK-REV-FB21 fixes successfully repaired the task_type → profile data flow. However, this revealed a deeper design issue: **the quality gate system is too binary for real-world task variety**.

Simple feature tasks (complexity 2-3) writing basic code:
1. Correctly get `feature` type (they ARE writing code)
2. Incorrectly get full 60-threshold arch review (overkill for 20 LOC)
3. Fail because simple boilerplate can't score 60+ on architectural review

The solution isn't to reclassify everything as scaffolding (they do write code), but to make quality gates **complexity-sensitive**.

---

**Review Status**: REVIEW_COMPLETE (Revised)
**Decision Recommended**: [I]mplement - Multiple layered fixes needed:
1. Complexity-modulated thresholds (design change)
2. Fix scaffolding independent tests (code fix)
3. Ensure code_review.score written (code fix)
4. Consider smarter Coach analysis (future enhancement)
