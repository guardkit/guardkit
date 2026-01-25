# Implementation Plan: TASK-FIX-ARIMPL

**Task**: Skip architectural review gate for --implement-only mode
**Mode**: TDD (Test-Driven Development)
**Complexity**: 4/10 (Medium)

## Problem Statement

Feature tasks using `--implement-only` fail the architectural review quality gate in `CoachValidator` because:
- Phase 2.5B (Architectural Review) doesn't run in implement-only mode
- No arch score is generated in `task_work_results.json`
- `CoachValidator.verify_quality_gates()` reads `code_review.score` as 0 (default)
- Gate fails since 0 < 60 (threshold)

## Solution Design

Add `skip_arch_review` parameter to `CoachValidator.verify_quality_gates()` that overrides the profile's `arch_review_required` setting when True.

**Key Decision**: Use parameter-level override instead of task frontmatter to maintain separation of concerns. The orchestrator determines when arch review should be skipped based on workflow state.

## TDD Implementation Plan

### Phase 1: RED - Write Failing Tests

#### File: `tests/unit/test_coach_validator.py`

Add new test class after existing profile tests (line 1378):

```python
class TestSkipArchReview:
    """Test skip_arch_review parameter behavior."""

    def test_skip_arch_review_passes_with_zero_score(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that skip_arch_review=True bypasses arch review gate."""
        from guardkit.models.task_types import get_profile, TaskType

        # Write results with arch score = 0 (would normally fail)
        results = make_task_work_results(
            arch_score=0,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.FEATURE)

        # With skip_arch_review=True, should pass despite score=0
        status = validator.verify_quality_gates(
            results,
            profile=profile,
            skip_arch_review=True,
        )

        assert status.arch_review_required is False
        assert status.arch_review_passed is True
        assert status.all_gates_passed is True

    def test_skip_arch_review_false_enforces_gate(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that skip_arch_review=False enforces arch review gate."""
        from guardkit.models.task_types import get_profile, TaskType

        # Write results with arch score = 0
        results = make_task_work_results(
            arch_score=0,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.FEATURE)

        # With skip_arch_review=False, should fail with score=0
        status = validator.verify_quality_gates(
            results,
            profile=profile,
            skip_arch_review=False,
        )

        assert status.arch_review_required is True
        assert status.arch_review_passed is False
        assert status.all_gates_passed is False

    def test_skip_arch_review_default_false(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that skip_arch_review defaults to False."""
        from guardkit.models.task_types import get_profile, TaskType

        # Write results with arch score = 0
        results = make_task_work_results(
            arch_score=0,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.FEATURE)

        # Default behavior (no skip_arch_review param)
        status = validator.verify_quality_gates(
            results,
            profile=profile,
        )

        # Should enforce arch review (backward compatible)
        assert status.arch_review_required is True
        assert status.arch_review_passed is False

    def test_skip_arch_review_with_scaffolding_profile(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test skip_arch_review with scaffolding profile (already skips)."""
        from guardkit.models.task_types import get_profile, TaskType

        # Write results with arch score = 0
        results = make_task_work_results(
            arch_score=0,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.SCAFFOLDING)

        # Both profile and skip_arch_review skip arch review
        status = validator.verify_quality_gates(
            results,
            profile=profile,
            skip_arch_review=True,
        )

        # Should pass (redundant skip)
        assert status.arch_review_required is False
        assert status.arch_review_passed is True
        assert status.all_gates_passed is True

    def test_skip_arch_review_overrides_profile_requirement(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test that skip_arch_review overrides profile.arch_review_required."""
        from guardkit.models.task_types import get_profile, TaskType

        # Write results with low arch score
        results = make_task_work_results(
            arch_score=30,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        validator = CoachValidator(str(tmp_worktree))
        profile = get_profile(TaskType.FEATURE)  # arch_review_required=True

        # skip_arch_review should override profile requirement
        status = validator.verify_quality_gates(
            results,
            profile=profile,
            skip_arch_review=True,
        )

        # Profile says required, but skip_arch_review overrides
        assert status.arch_review_required is False
        assert status.arch_review_passed is True
        assert status.all_gates_passed is True

    def test_validate_with_skip_arch_review_integration(
        self,
        tmp_worktree,
        task_work_results_dir,
    ):
        """Test full validate() flow with skip_arch_review."""
        # Write results with arch score = 0
        results = make_task_work_results(
            arch_score=0,
            requirements_met=["Criterion 1"],
        )
        write_task_work_results(task_work_results_dir, results)

        task = {
            "task_type": "feature",
            "acceptance_criteria": ["Criterion 1"],
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="All passed",
                stderr="",
            )

            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate(
                "TASK-001",
                1,
                task,
                skip_arch_review=True,
            )

        # Should approve despite arch score = 0
        assert result.decision == "approve"
        assert result.quality_gates.arch_review_required is False
        assert result.quality_gates.arch_review_passed is True
```

**Expected Result**: All 6 tests should FAIL (RED phase) because `skip_arch_review` parameter doesn't exist yet.

### Phase 2: GREEN - Implement Minimum Code

#### Step 2.1: Add Parameter to `verify_quality_gates()`

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Location**: Line 506 (method signature)

```python
def verify_quality_gates(
    self,
    task_work_results: Dict[str, Any],
    profile: Optional[QualityGateProfile] = None,
    skip_arch_review: bool = False,
) -> QualityGateStatus:
```

**Documentation update** (line 511-533):

```python
"""Verify task-work quality gates passed.

Checks the following gates from task-work results, respecting the quality
gate profile which determines which gates are required for the task type:
- tests_passed: From Phase 4.5 test results
- coverage_met: From Phase 4.5 coverage check
- arch_review_passed: From Phase 5 code review (score >= threshold)
- plan_audit_passed: From Phase 5.5 plan audit (0 violations)

Parameters
----------
task_work_results : Dict[str, Any]
    Results from task-work execution
profile : Optional[QualityGateProfile]
    Quality gate profile for task type. If None, uses FEATURE profile
    (backward compatible with existing calls without profile parameter).
skip_arch_review : bool
    If True, bypasses architectural review requirement regardless of profile.
    Used for --implement-only mode where arch review occurs in design phase.
    Default: False (enforce profile requirement).

Returns
-------
QualityGateStatus
    Status of all quality gates with requirement flags
"""
```

#### Step 2.2: Implement Skip Logic

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Location**: Line 580-591 (arch review logic)

Replace existing arch review logic:

```python
# Architectural review - may be in separate code_review field or not present
# If arch review not required by profile OR skip_arch_review=True, skip gate
if not profile.arch_review_required or skip_arch_review:
    arch_review_passed = True
    if skip_arch_review:
        logger.debug("Architectural review skipped per skip_arch_review parameter")
    else:
        logger.debug("Architectural review not required per task type profile, skipping")
else:
    code_review = task_work_results.get("code_review", {})
    arch_score = code_review.get("score", 0)  # Default to 0 if not present
    arch_review_passed = arch_score >= profile.arch_review_threshold
    logger.debug(
        f"Extracted arch_review_passed={arch_review_passed} "
        f"(score={arch_score}, threshold={profile.arch_review_threshold})"
    )
```

#### Step 2.3: Update QualityGateStatus Initialization

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Location**: Line 604-613 (QualityGateStatus instantiation)

Update to reflect skip override:

```python
status = QualityGateStatus(
    tests_passed=tests_passed,
    coverage_met=coverage_met,
    arch_review_passed=arch_review_passed,
    plan_audit_passed=plan_audit_passed,
    tests_required=profile.tests_required,
    coverage_required=profile.coverage_required,
    arch_review_required=profile.arch_review_required and not skip_arch_review,
    plan_audit_required=profile.plan_audit_required,
)
```

#### Step 2.4: Add Parameter to `validate()` Method

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Location**: Line 328-356 (validate method signature and call)

Update method signature:

```python
def validate(
    self,
    task_id: str,
    turn: int,
    task: Dict[str, Any],
    skip_arch_review: bool = False,
) -> CoachValidationResult:
```

Update verify_quality_gates call (line 394):

```python
gates_status = self.verify_quality_gates(
    task_work_results,
    profile=profile,
    skip_arch_review=skip_arch_review,
)
```

Update docstring to document parameter.

#### Step 2.5: Wire Parameter in `agent_invoker.py`

**File**: `guardkit/orchestrator/agent_invoker.py`
**Location**: Find where CoachValidator.validate() is called

**Note**: Based on code review, `agent_invoker.py` currently uses SDK invocation for Coach, not `CoachValidator.validate()`. The validator is used elsewhere in the orchestration flow.

**Action**: Search for where `CoachValidator` is instantiated and validate() is called. This is likely in the autobuild orchestrator.

**Expected Result**: All 6 tests should PASS (GREEN phase).

### Phase 3: REFACTOR - Improve Design

#### Refactor 3.1: Add Logging for Override Behavior

Enhance logging to make skip behavior clear in logs:

```python
# Log final decision at INFO level for visibility
if skip_arch_review:
    logger.info(
        f"Quality gate evaluation complete (arch_review skipped via parameter): "
        f"tests={status.tests_passed} (required={status.tests_required}), "
        f"coverage={status.coverage_met} (required={status.coverage_required}), "
        f"arch=SKIPPED (required={profile.arch_review_required}, overridden=True), "
        f"audit={status.plan_audit_passed} (required={status.plan_audit_required}), "
        f"ALL_PASSED={status.all_gates_passed}"
    )
else:
    logger.info(
        f"Quality gate evaluation complete: "
        f"tests={status.tests_passed} (required={status.tests_required}), "
        f"coverage={status.coverage_met} (required={status.coverage_required}), "
        f"arch={status.arch_review_passed} (required={status.arch_review_required}), "
        f"audit={status.plan_audit_passed} (required={status.plan_audit_required}), "
        f"ALL_PASSED={status.all_gates_passed}"
    )
```

#### Refactor 3.2: Extract Skip Logic

Consider extracting to helper method if logic becomes complex:

```python
def _should_skip_arch_review(
    self,
    profile: QualityGateProfile,
    skip_arch_review: bool,
) -> bool:
    """Determine if architectural review should be skipped.

    Parameters
    ----------
    profile : QualityGateProfile
        Quality gate profile for task type
    skip_arch_review : bool
        Explicit skip parameter

    Returns
    -------
    bool
        True if arch review should be skipped
    """
    return not profile.arch_review_required or skip_arch_review
```

**Decision**: Keep inline for now (YAGNI). Extract only if skip logic becomes more complex.

## Files to Modify

1. **`guardkit/orchestrator/quality_gates/coach_validator.py`** (~50 lines)
   - Add `skip_arch_review` parameter to `verify_quality_gates()` (line 506)
   - Add `skip_arch_review` parameter to `validate()` (line 328)
   - Implement skip logic in arch review section (line 580-591)
   - Update QualityGateStatus initialization (line 604-613)
   - Update logging (line 616-623)
   - Update docstrings

2. **`tests/unit/test_coach_validator.py`** (~150 lines)
   - Add `TestSkipArchReview` class with 6 tests (after line 1378)

3. **`guardkit/orchestrator/agent_invoker.py`** (future work)
   - Pass `skip_arch_review=True` when implement-only mode is detected
   - This may be in the autobuild orchestrator, not agent_invoker
   - Defer to actual call site investigation

## Acceptance Criteria Mapping

1. ✅ **AC-001**: Tests pass with `skip_arch_review=True` despite arch_score=0
2. ✅ **AC-002**: Tests fail with `skip_arch_review=False` when arch_score < 60
3. ✅ **AC-003**: Default behavior (no parameter) maintains backward compatibility
4. ✅ **AC-004**: Parameter overrides profile's `arch_review_required` setting
5. ✅ **AC-005**: Works with profiles that already skip arch review (redundant skip)
6. ✅ **AC-006**: Full `validate()` flow respects `skip_arch_review` parameter

## Edge Cases Considered

1. **Scaffolding profile + skip_arch_review**: Both skip arch review (redundant but safe)
2. **Missing arch score**: Default 0 causes failure unless skipped
3. **Backward compatibility**: Default `skip_arch_review=False` maintains current behavior
4. **Profile override**: `skip_arch_review=True` overrides `profile.arch_review_required=True`

## Testing Strategy

**TDD Red-Green-Refactor**:
1. RED: Write 6 failing tests in `TestSkipArchReview`
2. GREEN: Implement minimum code to pass tests
3. REFACTOR: Improve logging and extract helper if needed

**Test Coverage**:
- Parameter behavior (True/False/default)
- Profile interaction (override vs redundant skip)
- Integration with full validate() flow
- Backward compatibility

**Run Tests**:
```bash
pytest tests/unit/test_coach_validator.py::TestSkipArchReview -v
```

## Dependencies

- No new external dependencies
- Uses existing `QualityGateProfile` from `guardkit.models.task_types`
- Extends existing parameter pattern (profile parameter added in TASK-FBSDK-021)

## Implementation Time Estimate

- **Phase 1 (RED)**: 30 minutes (write 6 tests)
- **Phase 2 (GREEN)**: 45 minutes (implement parameter + logic)
- **Phase 3 (REFACTOR)**: 15 minutes (improve logging)
- **Total**: ~90 minutes

## Follow-Up Work

After this task completes:

1. **Wire in orchestrator**: Update autobuild orchestrator to pass `skip_arch_review=True` for `--implement-only` mode
2. **Integration test**: Add end-to-end test for feature-build with pre-loop disabled
3. **Documentation**: Update AutoBuild docs to explain arch review skip behavior

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Skipping arch review reduces quality | Low | Medium | Only skip when arch review occurred in design phase (design-first workflow) |
| Backward compatibility break | Low | High | Default `False` maintains current behavior |
| Test coverage gaps | Low | Medium | 6 comprehensive tests covering all scenarios |

## Architecture Review Notes

**SOLID Compliance**:
- **S**: CoachValidator has single responsibility (validate quality gates)
- **O**: Parameter extension (open/closed principle)
- **L**: QualityGateStatus contract maintained
- **I**: No interface segregation issues
- **D**: No dependency changes

**DRY**: Reuses existing profile-based skip logic pattern

**YAGNI**: Minimal change - only adds parameter, no speculative features

**Score Estimate**: 75/100 (Good quality, follows existing patterns)
