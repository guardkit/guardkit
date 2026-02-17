---
id: TASK-INFR-1670
title: Split infrastructure classification into tiered patterns with precedence rule
status: backlog
created: 2026-02-17T00:00:00Z
updated: 2026-02-17T00:00:00Z
priority: high
tags: [autobuild, coach-validator, classification, infrastructure]
task_type: feature
complexity: 3
parent_review: TASK-REV-BA4B
feature_id: FEAT-INFRA
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Split infrastructure classification into tiered patterns with precedence rule

## Description

The current `_classify_test_failure` method uses a flat list of patterns (`_INFRA_FAILURE_PATTERNS`) that includes both high-confidence infrastructure indicators (ConnectionRefusedError) and ambiguous ones (ImportError). This creates a ~30% false-positive surface area where code bugs could be misclassified as infrastructure failures.

Split the patterns into two tiers and update the classification method to return both the classification and confidence level. Define a clear precedence rule for when both tiers match.

## Acceptance Criteria

- [ ] `_INFRA_FAILURE_PATTERNS` split into `_INFRA_HIGH_CONFIDENCE` and `_INFRA_AMBIGUOUS` class attributes
- [ ] `_classify_test_failure()` returns a tuple `(classification: str, confidence: str)` instead of just `str`
- [ ] Precedence rule: high-confidence wins if ANY high-confidence pattern matches, regardless of ambiguous patterns
- [ ] Return values: `("infrastructure", "high")`, `("infrastructure", "ambiguous")`, or `("code", "n/a")`
- [ ] All callers of `_classify_test_failure` updated for the new return type
- [ ] Feedback text still uses "infrastructure" classification for both tiers (user-facing message unchanged)
- [ ] Only "high" confidence is eligible for conditional approval (used by TASK-INFR-24DB)
- [ ] Existing test_coach_failure_classification.py tests updated for new return type
- [ ] New tests for mixed-tier edge cases:
  - ConnectionRefusedError + ModuleNotFoundError: psycopg2 → ("infrastructure", "high")
  - ImportError only → ("infrastructure", "ambiguous")
  - AssertionError only → ("code", "n/a")

## Key Files

- `guardkit/orchestrator/quality_gates/coach_validator.py` - Classification method (line 2063), pattern list (line 362), callers (line 576)
- `tests/unit/test_coach_failure_classification.py` - Existing tests

## Implementation Notes

High-confidence patterns (safe for conditional approval):
```python
_INFRA_HIGH_CONFIDENCE = [
    "ConnectionRefusedError", "ConnectionError", "Connection refused",
    "could not connect to server", "OperationalError",
    "psycopg2", "psycopg", "asyncpg",
    "sqlalchemy.exc.OperationalError", "django.db.utils.OperationalError",
    "pymongo.errors.ServerSelectionTimeoutError", "redis.exceptions.ConnectionError",
]
```

Ambiguous patterns (infrastructure feedback only, not conditional approval):
```python
_INFRA_AMBIGUOUS = [
    "ModuleNotFoundError", "ImportError", "No module named",
]
```

The method should check high-confidence first. If any match, return high regardless of ambiguous matches.
