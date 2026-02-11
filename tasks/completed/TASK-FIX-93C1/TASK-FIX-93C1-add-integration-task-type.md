---
id: TASK-FIX-93C1
title: "Add INTEGRATION task type for wiring and integration tasks"
status: completed
created: 2026-02-11T22:00:00Z
completed: 2026-02-11T23:30:00Z
priority: medium
tags: [autobuild, quality-gates, task-type-detection, zero-test-anomaly, new-feature]
task_type: feature
complexity: 5
parent_review: TASK-REV-93E1
fix_id: FIX-93E1-C
---

# Task: Add INTEGRATION Task Type (FIX-93E1-C, P2)

## Description

Tasks titled with integration/wiring verbs (e.g., "Integrate database health check", "Wire up payment endpoint", "Connect auth middleware") fall through to the FEATURE default in `detect_task_type()` because "integrate" is not in any keyword list. The FEATURE profile enforces full quality gates including `zero_test_blocking=True`, which is too strict for integration tasks that may not create their own test files.

A new `TaskType.INTEGRATION` with an appropriate quality gate profile resolves this classification gap. The INTEGRATION profile should have `tests_required=True` (tests are desirable) but `zero_test_blocking=False` (missing task-specific tests should not block approval).

## Root Cause

`detect_task_type()` (task_type_detector.py:176-270) checks keywords in priority order: INFRASTRUCTURE → TESTING → REFACTOR → DOCUMENTATION → SCAFFOLDING → FEATURE (default). "Integrate", "integration", "wire", "connect", and "hook up" are not in any keyword list, causing all integration tasks to default to FEATURE.

The FEATURE profile (`task_types.py:183-191`) enforces:
- `tests_required=True` + `zero_test_blocking=True` → blocking zero-test anomaly
- `arch_review_required=True` → requires 60+ architecture score
- `coverage_required=True` → requires 80% coverage

This is grossly over-specified for small wiring tasks.

## Changes Required

### 1. Add TaskType.INTEGRATION Enum Value

**File**: `guardkit/models/task_types.py`

Add to the `TaskType` enum (between INFRASTRUCTURE and DOCUMENTATION, or at end):
```python
INTEGRATION = "integration"
```

Update the docstring to include INTEGRATION description.

### 2. Add INTEGRATION Quality Gate Profile

**File**: `guardkit/models/task_types.py`

Add to `DEFAULT_PROFILES`:
```python
TaskType.INTEGRATION: QualityGateProfile(
    arch_review_required=False,   # Wiring tasks don't need arch review
    arch_review_threshold=0,
    coverage_required=False,      # Integration testing is separate concern
    coverage_threshold=0.0,
    tests_required=True,          # Integration tests should pass if they exist
    plan_audit_required=True,     # Ensure integration is complete
    zero_test_blocking=False,     # Integration tasks may not have task-specific tests
),
```

### 3. Add Integration Keywords

**File**: `guardkit/lib/task_type_detector.py`

Add `TaskType.INTEGRATION` to `KEYWORD_MAPPINGS` with keywords:
```python
TaskType.INTEGRATION: [
    "integrate",
    "integration",
    "wire",
    "wiring",
    "connect",
    "hook up",
    "hookup",
    "endpoint integration",
],
```

### 4. Update Priority Order

**File**: `guardkit/lib/task_type_detector.py`

Add `TaskType.INTEGRATION` to the priority loop at line 257-262. Position: between INFRASTRUCTURE and TESTING (integration is more specific than general testing keywords but less specific than infrastructure).

```python
for task_type in [
    TaskType.INFRASTRUCTURE,
    TaskType.INTEGRATION,      # NEW: after infrastructure, before testing
    TaskType.TESTING,
    TaskType.REFACTOR,
    TaskType.DOCUMENTATION,
    TaskType.SCAFFOLDING,
]:
```

### 5. Update Task Type Summary

**File**: `guardkit/lib/task_type_detector.py`

Add to `get_task_type_summary()` at line 292-300:
```python
TaskType.INTEGRATION: "Integration and wiring",
```

### 6. Update Feature Plan Spec (Optional)

**File**: `installer/core/commands/feature-plan.md`

Add INTEGRATION to the task_type assignment rules section (~line 1248-1267) so the LLM knows when to assign `integration` as a task type.

## Acceptance Criteria

- [ ] AC-001: `TaskType.INTEGRATION` exists as an enum value with value `"integration"`
- [ ] AC-002: `DEFAULT_PROFILES[TaskType.INTEGRATION]` has `tests_required=True`, `zero_test_blocking=False`, `arch_review_required=False`, `coverage_required=False`
- [ ] AC-003: `detect_task_type("Integrate database health check")` returns `TaskType.INTEGRATION`
- [ ] AC-004: `detect_task_type("Wire up payment endpoint")` returns `TaskType.INTEGRATION`
- [ ] AC-005: `detect_task_type("Connect auth middleware")` returns `TaskType.INTEGRATION`
- [ ] AC-006: `detect_task_type("Implement user authentication")` still returns `TaskType.FEATURE` (no false positives)
- [ ] AC-007: `detect_task_type("Add Docker configuration")` still returns `TaskType.INFRASTRUCTURE` (priority preserved)
- [ ] AC-008: `get_profile(TaskType.INTEGRATION)` returns the correct profile
- [ ] AC-009: `get_profile(None)` still returns FEATURE profile (backward compatibility)
- [ ] AC-010: `_resolve_task_type()` in coach_validator.py accepts "integration" as a valid task_type string
- [ ] AC-011: `get_task_type_summary(TaskType.INTEGRATION)` returns a meaningful string
- [ ] AC-012: All existing task type detector tests pass without modification
- [ ] AC-013: All existing task types tests pass without modification
- [ ] AC-014: New tests cover INTEGRATION keyword matching, profile configuration, and Coach resolution (at least 10 new tests)

## Regression Constraints (Must Not Regress)

| Prior Fix | Risk | Notes |
|-----------|------|-------|
| TASK-AQG-002 | LOW | `zero_test_blocking=False` for INTEGRATION — correct. Existing FEATURE/REFACTOR profiles unchanged. |
| All others | NONE | Task type classification is upstream and independent of all fix chains |

### Consumer Audit for New Enum Value

All consumers verified safe:
- `task_type_detector.py`: Add to KEYWORD_MAPPINGS + priority loop + summary — **REQUIRES CHANGES**
- `task_types.py`: Add to enum + DEFAULT_PROFILES — **REQUIRES CHANGES**
- `coach_validator.py:_resolve_task_type()`: Validates via `TaskType(value)` enum constructor — auto-works
- `coach_validator.py:_TASK_TYPE_ALIASES`: Optionally add alias — **OPTIONAL**
- `autobuild.py`: Reads from frontmatter, passes through — no changes needed
- `progress.py`: Displays task_type but doesn't switch on it — no changes needed
- `feature-plan.md`: LLM instruction — **OPTIONAL UPDATE**
- `implement_orchestrator.py`: Calls `detect_task_type()` — auto-works

## Test Plan

1. Existing `test_task_type_detector.py` tests must pass unchanged
2. Existing `test_task_types.py` tests must pass unchanged
3. New keyword matching tests:
   - "Integrate database health check" → INTEGRATION
   - "Wire up payment endpoint" → INTEGRATION
   - "Connect auth middleware" → INTEGRATION
   - "integration test setup" → TESTING (not INTEGRATION — "test" matches TESTING first? No, INTEGRATION is before TESTING in priority. Need to verify: "integration test" should match INTEGRATION, not TESTING. If this is undesirable, adjust keywords.)
4. New negative tests:
   - "Implement user authentication" → FEATURE (unchanged)
   - "Add Docker configuration" → INFRASTRUCTURE (unchanged)
   - "Set up project scaffold" → SCAFFOLDING (unchanged)
5. New profile tests:
   - INTEGRATION profile has correct field values
   - `get_profile(TaskType.INTEGRATION)` returns correct profile
   - `QualityGateProfile.for_type(TaskType.INTEGRATION)` works
6. New Coach resolution tests:
   - `_resolve_task_type({"task_type": "integration"})` returns `TaskType.INTEGRATION`
7. Run full zero-test anomaly suites with INTEGRATION profile

### Keyword Overlap Concern

The keyword "integration" appears in the TESTING list as part of "integration test" (line 118). Since INTEGRATION will be checked BEFORE TESTING in priority order:
- "integration test setup" → matches "integration" → INTEGRATION (not TESTING)
- "add integration tests" → matches "integration" → INTEGRATION (not TESTING)

This may be undesirable. **Mitigation options**:
1. Use "integrate" but NOT "integration" as a keyword (avoids overlap with "integration test")
2. Keep "integration" and accept that "add integration tests" becomes INTEGRATION type (tests are still required, just not zero_test_blocking)
3. Move INTEGRATION after TESTING in priority (but then "integration test" matches TESTING, and "integrate database" falls through to... still INTEGRATION)

**Recommendation**: Use keywords `"integrate"`, `"wire"`, `"wiring"`, `"connect"`, `"hook up"`, `"hookup"` — but NOT `"integration"` to avoid overlap with "integration test". The verb form "integrate" captures the intent without conflicting.

## Dependencies

- Independent of TASK-FIX-93B1 (recursive glob) and TASK-FIX-93A1 (tests_written)
- Can be implemented in parallel with the other fixes
- Should be implemented last for correct priority ordering (P2)

## Key Files

| File | Role |
|------|------|
| `guardkit/models/task_types.py` | TaskType enum + DEFAULT_PROFILES |
| `guardkit/lib/task_type_detector.py` | KEYWORD_MAPPINGS + priority loop + summary |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | _resolve_task_type() + _TASK_TYPE_ALIASES |
| `installer/core/commands/feature-plan.md` | LLM task_type assignment rules |
| `tests/unit/test_task_type_detector.py` | Task type detector tests |
| `tests/unit/test_task_types.py` | Task types tests |
| `tests/unit/test_coach_validator.py` | Coach validator tests |

## Reference

- Review report: `.claude/reviews/TASK-REV-93E1-review-report.md` (AC-006, AC-008, AC-009)
- Parent review: TASK-REV-93E1
