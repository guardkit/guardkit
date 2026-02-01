---
id: TASK-AB-RATE-LIMIT
title: Add Rate Limit Detection to AutoBuild - Stop on Rate Limit
status: completed
created: 2026-02-01T19:00:00Z
completed: 2026-02-01T20:15:00Z
priority: high
task_type: feature
tags: [autobuild, resilience, error-handling, rate-limit]
complexity: 5
estimate_hours: 3
actual_hours: 1.25
source: TASK-REV-GR6003
technical_debt_id: TD-001
completed_location: tasks/completed/TASK-AB-RATE-LIMIT/
---

# Add Rate Limit Detection to AutoBuild

## Description

Implement rate limit detection in AutoBuild so that when an API rate limit is hit, the build **stops immediately** instead of wasting turns on futile retries.

### Background

During FEAT-0F4A Phase 2 build, TASK-GR6-003 failed after 15 turns due to API rate limits. The system wasted 14 turns retrying when it should have stopped on the first detection. The error message appeared as:

```
ERROR: [TASK-GR6-003] Last output (500 chars): You've hit your limit · resets 4pm (Europe/London)
```

### Current Behavior
- Rate limit errors treated as generic failures
- System retries up to max_turns (wasted 14 turns)
- No reset time information provided
- User must diagnose from logs

### Desired Behavior
- Detect rate limit errors immediately
- Stop AutoBuild on first detection
- Parse and display estimated reset time
- Provide actionable resume command
- Preserve worktree for later resume

## Acceptance Criteria

- [x] New `RateLimitExceededError` exception in `guardkit/orchestrator/exceptions.py`
- [x] `detect_rate_limit()` function detects rate limit patterns in error messages
- [x] Patterns detected include:
  - "hit your limit" (with optional reset time parsing)
  - "rate limit"
  - "too many requests"
  - "429"
  - "quota exceeded"
- [x] Rate limit errors are raised (not returned as generic failures)
- [x] `RateLimitExceededError` added to `UNRECOVERABLE_ERRORS` in autobuild.py
- [x] New `rate_limited` decision type in `OrchestrationResult`
- [x] Clear error message includes:
  - Confirmation that rate limit was hit
  - Estimated reset time (if parseable)
  - Worktree preservation notice
  - Resume command for user
- [x] Tests verify rate limit detection and handling
- [x] Build stops on first rate limit detection (no retries)

## Implementation Plan

### Phase 1: Add Exception and Detection (exceptions.py)

```python
class RateLimitExceededError(AgentInvokerError):
    """Raised when API rate limit is exceeded.

    Attributes:
        reset_time: Estimated reset time from error message (if parseable)
    """
    def __init__(self, message: str, reset_time: Optional[str] = None):
        super().__init__(message)
        self.reset_time = reset_time
```

### Phase 2: Add Detection Function (agent_invoker.py)

```python
import re
from typing import Tuple, Optional

def detect_rate_limit(error_text: str) -> Tuple[bool, Optional[str]]:
    """Detect if error is a rate limit error.

    Args:
        error_text: Error message or output text to check

    Returns:
        Tuple of (is_rate_limit, reset_time)
        reset_time is None if not parseable
    """
    patterns = [
        (r"hit your limit.*resets?\s+(\d+(?::\d+)?(?:\s*(?:am|pm))?(?:\s*\([^)]+\))?)", True),
        (r"rate limit", False),
        (r"too many requests", False),
        (r"429", False),
        (r"quota exceeded", False),
    ]

    text_lower = error_text.lower()
    for pattern, has_reset_time in patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            reset_time = match.group(1) if has_reset_time and match.lastindex else None
            return True, reset_time

    return False, None
```

### Phase 3: Update Error Handling (agent_invoker.py ~line 2477)

In the `except Exception` block of `_invoke_task_work_implement`:

```python
except Exception as e:
    error_msg = str(e)

    # Check for rate limit in error message
    is_rate_limit, reset_time = detect_rate_limit(error_msg)

    # Also check collected output for rate limit messages
    if not is_rate_limit and collected_output:
        last_output = " ".join(collected_output)[-500:]
        is_rate_limit, reset_time = detect_rate_limit(last_output)

    if is_rate_limit:
        logger.error(f"[{task_id}] RATE LIMIT EXCEEDED")
        if reset_time:
            logger.error(f"[{task_id}] Estimated reset: {reset_time}")
        raise RateLimitExceededError(
            f"API rate limit exceeded. Reset: {reset_time or 'unknown'}",
            reset_time=reset_time
        )

    # Original generic error handling continues...
    error_msg = f"Unexpected error executing task-work: {str(e)}"
    # ... rest of existing code
```

### Phase 4: Update AutoBuild (autobuild.py)

1. Add import:
```python
from guardkit.orchestrator.exceptions import (
    # ... existing imports ...
    RateLimitExceededError,
)
```

2. Update UNRECOVERABLE_ERRORS:
```python
UNRECOVERABLE_ERRORS = (
    PlanNotFoundError,
    StateValidationError,
    RateLimitExceededError,  # NEW: Stop immediately on rate limit
)
```

3. Add new decision type to OrchestrationResult (update the Literal type):
```python
final_decision: Literal["approved", "max_turns_exceeded", "error", "pre_loop_blocked", "rate_limited"]
```

4. Handle rate limit in orchestrate() method:
```python
except RateLimitExceededError as e:
    logger.error(f"Rate limit exceeded for {task_id}: {e}")
    return OrchestrationResult(
        task_id=task_id,
        success=False,
        total_turns=len(turn_history),
        final_decision="rate_limited",
        turn_history=turn_history,
        worktree=worktree,
        error=(
            f"Rate limit exceeded. Reset time: {e.reset_time or 'unknown'}. "
            f"Worktree preserved at: {worktree.path}\n"
            f"Resume with: guardkit autobuild task {task_id} --resume"
        ),
    )
```

### Phase 5: Tests

Create `tests/orchestrator/test_rate_limit_detection.py`:

```python
import pytest
from guardkit.orchestrator.agent_invoker import detect_rate_limit
from guardkit.orchestrator.exceptions import RateLimitExceededError

class TestRateLimitDetection:
    """Tests for rate limit detection."""

    def test_detect_hit_your_limit_with_reset_time(self):
        """Test detection of 'hit your limit' with reset time."""
        text = "You've hit your limit · resets 4pm (Europe/London)"
        is_rate_limit, reset_time = detect_rate_limit(text)
        assert is_rate_limit is True
        assert "4pm" in reset_time

    def test_detect_rate_limit_phrase(self):
        """Test detection of 'rate limit' phrase."""
        text = "API rate limit exceeded"
        is_rate_limit, reset_time = detect_rate_limit(text)
        assert is_rate_limit is True
        assert reset_time is None

    def test_detect_429(self):
        """Test detection of HTTP 429 status."""
        text = "Error 429: Too Many Requests"
        is_rate_limit, reset_time = detect_rate_limit(text)
        assert is_rate_limit is True

    def test_detect_quota_exceeded(self):
        """Test detection of quota exceeded."""
        text = "Your API quota exceeded for this period"
        is_rate_limit, reset_time = detect_rate_limit(text)
        assert is_rate_limit is True

    def test_no_rate_limit(self):
        """Test that non-rate-limit errors return False."""
        text = "Connection timeout after 30 seconds"
        is_rate_limit, reset_time = detect_rate_limit(text)
        assert is_rate_limit is False
        assert reset_time is None

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        text = "RATE LIMIT EXCEEDED"
        is_rate_limit, _ = detect_rate_limit(text)
        assert is_rate_limit is True


class TestRateLimitExceededError:
    """Tests for RateLimitExceededError exception."""

    def test_exception_with_reset_time(self):
        """Test exception stores reset time."""
        exc = RateLimitExceededError("Rate limit hit", reset_time="4pm")
        assert exc.reset_time == "4pm"
        assert "Rate limit hit" in str(exc)

    def test_exception_without_reset_time(self):
        """Test exception with no reset time."""
        exc = RateLimitExceededError("Rate limit hit")
        assert exc.reset_time is None
```

## Files to Modify

1. `guardkit/orchestrator/exceptions.py` - Add RateLimitExceededError
2. `guardkit/orchestrator/agent_invoker.py` - Add detect_rate_limit(), update error handling
3. `guardkit/orchestrator/autobuild.py` - Add to UNRECOVERABLE_ERRORS, handle new exception
4. `tests/orchestrator/test_rate_limit_detection.py` - New test file

## Related

- Source: TASK-REV-GR6003 (Technical Debt Review)
- Technical Debt ID: TD-001
- Review Report: `.claude/reviews/TASK-REV-GR6003-review-report.md`
- Original Failure: FEAT-0F4A Phase 2 build (14 wasted turns)

## Notes

- This is a HIGH priority fix to prevent wasted API calls and user time
- The fix should be backward compatible (no breaking changes)
- Consider future enhancement: automatic retry after reset time (out of scope for this task)
