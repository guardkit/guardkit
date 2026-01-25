---
id: TASK-P45-f3a1
title: Add Phase 4.5 test enforcement resilience mechanisms
status: completed
created: 2026-01-08T12:10:00Z
updated: 2026-01-08T20:30:00Z
completed: 2026-01-08T20:30:00Z
completed_location: tasks/completed/TASK-P45-f3a1/
priority: medium
tags: [phase-4.5, test-enforcement, resilience, error-detection, phased-implementation]
parent_task: TASK-REV-9AC5
complexity: 6
estimated_effort: 1-2 days (phased)
actual_effort: ~2 hours
review_recommendation: R6
related_findings: [Finding-5]
implementation_approach: phased
phases:
  - name: error-fingerprinting
    complexity: 5
    effort: 4-6 hours
    priority: medium
    status: deferred
    notes: Per architectural review - implement if Phases 2&4 insufficient
  - name: per-iteration-timeout
    complexity: 3
    effort: 2-3 hours
    priority: high
    status: completed
  - name: complexity-assessment
    complexity: 6
    effort: 4-6 hours
    priority: medium
    status: deferred
    notes: Per architectural review - implement if Phases 2&4 insufficient
  - name: early-exit-with-guidance
    complexity: 4
    effort: 3-4 hours
    priority: high
    status: completed
completion:
  completed_at: "2026-01-08T20:30:00Z"
  completed_by: task-work
  phases_implemented: [per-iteration-timeout, early-exit-with-guidance]
  phases_deferred: [error-fingerprinting, complexity-assessment]
  files_created:
    - installer/core/commands/lib/test_enforcement_resilience.py
    - tests/unit/test_test_enforcement_resilience.py
  tests_passed: 35
  quality_gates:
    tests: passed
    architectural_review: 82/100 (approved)
  organized_files:
    - TASK-P45-f3a1-phase-resilience-mechanisms.md
---

# Task: Add Phase 4.5 test enforcement resilience mechanisms

## Context

**From Review**: TASK-REV-9AC5 Finding 5 (MEDIUM severity)

Phase 4.5 Test Enforcement Loop lacks defensive mechanisms to detect when errors are beyond auto-fix capability, resulting in wasted time retrying the same unfixable error.

**Evidence from TASK-INFRA-001**:
- Phase 4.5 spent 180s (3 attempts × 60s) trying to fix Pydantic v2 CORS parsing errors
- Same error occurred in all 3 attempts (no detection of repetition)
- Each attempt analyzed same 8 failures, generated fix, re-ran all 40 tests
- Eventually timed out at 300s without recognizing "unfixable"

**Complementary to R1**: While R1 provides more time (600s), R6 ensures that time is used wisely by detecting unfixable errors early.

## Phased Implementation Strategy

### Phase 1: Error Fingerprinting (Complexity: 5/10, MEDIUM)

**Goal**: Detect when the same error repeats across attempts.

**Files to Create/Modify**:
- `installer/core/commands/lib/test_enforcement_resilience.py` (new)
- `installer/core/commands/lib/phase_execution.py` (integrate)

**Implementation**:
```python
import hashlib
import re
from typing import List

def fingerprint_error(error_output: str) -> str:
    """Create unique fingerprint for error pattern."""
    # Normalize error (remove line numbers, timestamps, paths)
    normalized = re.sub(r'line \d+', 'line X', error_output)
    normalized = re.sub(r'/[^:]+:', '/PATH:', normalized)
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', normalized)

    # Hash for comparison
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]

def detect_repeated_error(
    current_errors: str,
    previous_fingerprints: List[str]
) -> bool:
    """Check if current error matches any previous attempt."""
    current_fp = fingerprint_error(current_errors)
    return current_fp in previous_fingerprints
```

**Testing**:
```python
def test_fingerprint_error_normalizes():
    """Verify error normalization works."""
    error1 = "File '/path/foo.py', line 42: NameError"
    error2 = "File '/different/foo.py', line 99: NameError"

    fp1 = fingerprint_error(error1)
    fp2 = fingerprint_error(error2)

    # Same error type = same fingerprint
    assert fp1 == fp2

def test_detect_repeated_error():
    """Verify repeated error detection."""
    error1 = "Test failed: CORS parsing"
    error2 = "Test failed: CORS parsing"  # Same error
    error3 = "Test failed: Missing import"  # Different

    fingerprints = [fingerprint_error(error1)]

    assert detect_repeated_error(error2, fingerprints) is True
    assert detect_repeated_error(error3, fingerprints) is False
```

**Estimated Effort**: 4-6 hours

### Phase 2: Per-Iteration Timeout (Complexity: 3/10, HIGH)

**Goal**: Add timeout per fix attempt to prevent runaway iterations.

**Implementation**:
```python
import time
from typing import Optional
from dataclasses import dataclass

MAX_ITERATION_SECONDS = 60  # Max 60s per fix attempt

@dataclass
class FixResult:
    """Result of a fix attempt."""
    success: bool
    duration: float
    changes_made: List[str]
    error: Optional[str] = None

def attempt_fix_with_timeout(
    errors: str,
    iteration: int,
    max_seconds: int = MAX_ITERATION_SECONDS
) -> Optional[FixResult]:
    """Attempt fix with iteration-level timeout."""
    start_time = time.time()

    try:
        # Generate and apply fix
        fix_result = generate_and_apply_fix(errors)

        elapsed = time.time() - start_time
        if elapsed > max_seconds:
            logger.warning(
                f"Iteration {iteration} exceeded {max_seconds}s "
                f"({elapsed:.1f}s) - may be unfixable"
            )
            return None  # Signal to exit early

        return FixResult(
            success=True,
            duration=elapsed,
            changes_made=fix_result.files_modified,
        )

    except Exception as e:
        logger.error(f"Fix attempt {iteration} failed: {e}")
        return FixResult(
            success=False,
            duration=time.time() - start_time,
            changes_made=[],
            error=str(e),
        )
```

**Testing**:
```python
def test_attempt_fix_with_timeout_succeeds():
    """Verify successful fix within timeout."""
    with patch('lib.phase_execution.generate_and_apply_fix') as mock_fix:
        mock_fix.return_value = MockFixResult(files_modified=["config.py"])

        result = attempt_fix_with_timeout("Error", iteration=1, max_seconds=60)

        assert result is not None
        assert result.success is True
        assert result.duration < 60

def test_attempt_fix_timeout_returns_none():
    """Verify timeout returns None."""
    with patch('lib.phase_execution.generate_and_apply_fix') as mock_fix:
        # Simulate slow fix (>60s)
        mock_fix.side_effect = lambda: time.sleep(65)

        result = attempt_fix_with_timeout("Error", iteration=1, max_seconds=60)

        assert result is None
```

**Estimated Effort**: 2-3 hours

### Phase 3: Complexity Assessment (Complexity: 6/10, MEDIUM)

**Goal**: Assess whether errors are likely auto-fixable.

**Implementation**:
```python
from enum import Enum

class ErrorComplexity(Enum):
    SIMPLE = "simple"          # Typo, missing import
    MODERATE = "moderate"      # Logic error, type mismatch
    COMPLEX = "complex"        # Migration, architectural change
    UNFIXABLE = "unfixable"    # Requires external dependency change

UNFIXABLE_PATTERNS = [
    r"Pydantic.*migration",
    r"breaking change.*v\d+",
    r"deprecated.*removed",
    r"database schema.*mismatch",
    r"incompatible.*version",
    r"Settings.*v2.*parsing",  # Specific to Pydantic Settings v2
]

def assess_error_complexity(error_output: str) -> ErrorComplexity:
    """Assess if error is likely auto-fixable."""

    # Check for unfixable patterns
    for pattern in UNFIXABLE_PATTERNS:
        if re.search(pattern, error_output, re.IGNORECASE):
            return ErrorComplexity.UNFIXABLE

    # Check error count (many errors = complex)
    error_count = len(re.findall(r'FAILED|ERROR', error_output))
    if error_count >= 10:
        return ErrorComplexity.COMPLEX

    # Check stack depth (deep stacks = complex)
    stack_depth = len(re.findall(r'File ".*", line \d+', error_output))
    if stack_depth >= 5:
        return ErrorComplexity.COMPLEX

    # Simple errors (known patterns)
    if any(keyword in error_output for keyword in ['NameError', 'ImportError', 'IndentationError']):
        return ErrorComplexity.SIMPLE

    return ErrorComplexity.MODERATE
```

**Testing**:
```python
def test_assess_pydantic_migration_as_unfixable():
    """Verify Pydantic migration detected as unfixable."""
    error = "SettingsError: Pydantic Settings v2 parsing failed"

    complexity = assess_error_complexity(error)

    assert complexity == ErrorComplexity.UNFIXABLE

def test_assess_simple_import_error():
    """Verify simple import error detected."""
    error = "ImportError: No module named 'foo'"

    complexity = assess_error_complexity(error)

    assert complexity == ErrorComplexity.SIMPLE
```

**Estimated Effort**: 4-6 hours

### Phase 4: Early Exit with Guidance (Complexity: 4/10, HIGH)

**Goal**: Exit Phase 4.5 early when errors are unfixable, provide user guidance.

**Implementation**:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Phase45Result:
    """Result of Phase 4.5 execution."""
    success: bool
    attempts: int
    recommendation: str
    guidance: Optional[str] = None

def execute_phase_4_5_with_resilience(
    test_result: TestResult,
    max_attempts: int = 3
) -> Phase45Result:
    """Execute Phase 4.5 with resilience mechanisms."""

    previous_fingerprints = []

    for attempt in range(1, max_attempts + 1):
        logger.info(f"Phase 4.5 Attempt {attempt}/{max_attempts}")

        # Assess complexity BEFORE attempting fix
        complexity = assess_error_complexity(test_result.output)

        if complexity == ErrorComplexity.UNFIXABLE:
            return Phase45Result(
                success=False,
                attempts=attempt,
                recommendation="MANUAL_FIX_REQUIRED",
                guidance=(
                    f"Error appears to be beyond auto-fix capability.\n"
                    f"Detected pattern: {complexity.value}\n"
                    f"Recommendation: Review error and apply manual fix.\n"
                    f"Common causes: Library migration, breaking API changes, "
                    f"external dependency updates."
                ),
            )

        # Check for repeated error (after Attempt 1)
        if attempt > 1:
            if detect_repeated_error(test_result.output, previous_fingerprints):
                return Phase45Result(
                    success=False,
                    attempts=attempt,
                    recommendation="SAME_ERROR_REPEATED",
                    guidance=(
                        f"Same error occurred in Attempt {attempt} as previous attempts.\n"
                        f"Suggests error is beyond current auto-fix capability.\n"
                        f"Exiting early to save time."
                    ),
                )

        # Record fingerprint for next iteration
        current_fp = fingerprint_error(test_result.output)
        previous_fingerprints.append(current_fp)

        # Attempt fix with per-iteration timeout
        fix_result = attempt_fix_with_timeout(
            errors=test_result.output,
            iteration=attempt,
            max_seconds=60,
        )

        if fix_result is None:
            # Timeout or failure - exit early
            return Phase45Result(
                success=False,
                attempts=attempt,
                recommendation="ITERATION_TIMEOUT",
                guidance=f"Fix attempt {attempt} exceeded timeout - likely too complex for auto-fix",
            )

        # Re-run tests
        test_result = run_tests()

        if test_result.passed:
            return Phase45Result(
                success=True,
                attempts=attempt,
                recommendation="AUTO_FIX_SUCCEEDED",
            )

    # Exhausted all attempts
    return Phase45Result(
        success=False,
        attempts=max_attempts,
        recommendation="MAX_ATTEMPTS_EXCEEDED",
        guidance="All auto-fix attempts exhausted. Manual intervention required.",
    )
```

**Integration** (`phase_execution.py`):
```python
# Replace existing Phase 4.5 loop with resilient version
result = execute_phase_4_5_with_resilience(test_result, max_attempts=3)

if not result.success:
    # Log guidance for user
    logger.error(f"Phase 4.5 failed: {result.recommendation}")
    if result.guidance:
        logger.info(f"Guidance: {result.guidance}")

    # Block task (existing behavior)
    update_task_state(task_id, "blocked")
```

**Estimated Effort**: 3-4 hours

## Acceptance Criteria

**Phase 1 (Error Fingerprinting)**:
- [ ] `fingerprint_error()` function with normalization
- [ ] `detect_repeated_error()` function
- [ ] Unit tests for normalization and detection
- [ ] Integration with Phase 4.5 loop

**Phase 2 (Per-Iteration Timeout)**:
- [ ] `attempt_fix_with_timeout()` function
- [ ] `MAX_ITERATION_SECONDS` constant (60s)
- [ ] Timeout detection and early return
- [ ] Unit tests for timeout behavior

**Phase 3 (Complexity Assessment)**:
- [ ] `ErrorComplexity` enum
- [ ] `UNFIXABLE_PATTERNS` list with Pydantic v2 pattern
- [ ] `assess_error_complexity()` function
- [ ] Unit tests for all complexity levels

**Phase 4 (Early Exit)**:
- [ ] `execute_phase_4_5_with_resilience()` function
- [ ] Integration of all 4 mechanisms
- [ ] User-friendly guidance messages
- [ ] Unit tests for all exit conditions
- [ ] Integration tests for complete workflow

## Testing Strategy

**Unit Tests** (`test_test_enforcement_resilience.py`):
- Error fingerprinting (normalization, detection)
- Per-iteration timeout (success, timeout, failure)
- Complexity assessment (all 4 levels)
- Early exit logic (all exit conditions)

**Integration Tests** (`test_phase_4_5_resilience.py`):
- Unfixable error detected on Attempt 1
- Repeated error detected on Attempt 2
- Timeout exceeded on Attempt 1
- Max attempts exhausted
- Successful fix on Attempt 2

**Manual Test Scenario**:
```bash
# Create task with Pydantic v2 CORS error
guardkit autobuild task TASK-TEST --sdk-timeout 600

# Expected behavior:
# Attempt 1: Detects "unfixable" pattern, exits early with guidance
# Total time: ~60s (not 180s)
# Message: "Pydantic Settings v2 migration requires manual fix"
```

## Integration with Finding 1 (R1)

This recommendation **complements** R1 (timeout increase):

| Scenario | With R1 Only | With R1 + R6 |
|----------|--------------|--------------|
| **Fixable error** | 600s allows 3 attempts | Same - R6 doesn't interfere |
| **Unfixable error** | Wastes 270s on 3 futile attempts | Exits after 60s with guidance |
| **Repeated error** | Tries same fix 3 times | Detects repetition, exits early |
| **User experience** | Confusion why it timed out | Clear: "Beyond auto-fix capability" |

## Dependencies

None - can be implemented independently. Complements R1 (SDK timeout).

## Estimated Complexity: 6/10 (Total)

**Phased Approach**:
- Phase 1: 5/10 (4-6 hours)
- Phase 2: 3/10 (2-3 hours) - HIGH priority
- Phase 3: 6/10 (4-6 hours)
- Phase 4: 4/10 (3-4 hours) - HIGH priority
- **Total**: 6/10 (1-2 days)

**Recommendation**: Implement Phases 2 and 4 first (high priority), then Phases 1 and 3.

## Priority Justification

**MEDIUM**: While R1 is CRITICAL (provides time), R6 is strategic (uses time wisely). Without R6, even with 600s timeout, complex unfixable errors waste 270s on futile attempts.

**Value Proposition**: Saves 45% of timeout budget on unfixable errors, provides clear user guidance.

## References

- Review Report: `.claude/reviews/TASK-REV-9AC5-review-report.md`
- Finding 5: Phase 4.5 Lacks Resilience (Lines 453-624)
- Recommendation R6: Lines 939-1159
- Location: installer/core/commands/lib/phase_execution.py
