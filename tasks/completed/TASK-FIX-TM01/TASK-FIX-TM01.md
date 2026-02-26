---
id: TASK-FIX-TM01
title: Align _extract_keywords() with regex splitting from synthetic_report.py
status: completed
updated: 2026-02-25T13:05:00Z
completed: 2026-02-25T13:05:00Z
task_type: implementation
created: 2026-02-25T12:00:00Z
priority: critical
tags: [autobuild, coach-validator, text-matching, bug-fix, P0]
complexity: 2
parent_review: TASK-REV-0828
feature_id: FEAT-TM-FIX
wave: 1
implementation_mode: task-work
dependencies: []
files_touched: [guardkit/orchestrator/quality_gates/coach_validator.py]
---

# Task: Align `_extract_keywords()` with regex splitting from synthetic_report.py

## Problem

`_extract_keywords()` in `coach_validator.py:1868` uses `.split()` (whitespace splitting) which preserves markdown formatting characters (backticks, quotes) as part of keyword tokens. This causes keyword-based matching (Strategy 3) to fail when acceptance criteria contain backtick-delimited code or quoted strings.

**Example failure**:
- AC text: `` `Settings` class has `log_level` field with default "INFO" ``
- Keywords extracted (current): `['\`settings\`', '\`log_level\`', '"info"', ...]`
- Keywords extracted (fixed): `['settings', 'log_level', 'info', ...]`

**Impact**: Turn 2 goes from 0/7 to 5/7 matched criteria. Turn 3 goes from 1/7 to 2/7.

## Solution

Change line 1868 from whitespace splitting to regex splitting, matching the existing production implementation in `synthetic_report.py:348` (`_extract_criterion_keywords()`):

```python
# BEFORE (line 1868)
words = text.lower().split()

# AFTER
import re  # already imported at module top
words = re.split(r'[^a-zA-Z0-9_]+', text.lower())
```

Also filter empty strings from the split result (regex split can produce empty strings at boundaries):

```python
words = [w for w in re.split(r'[^a-zA-Z0-9_]+', text.lower()) if w]
```

## Acceptance Criteria

1. `_extract_keywords()` uses `re.split(r'[^a-zA-Z0-9_]+', ...)` instead of `.split()`
2. Empty strings from regex splitting are filtered out
3. STOPWORDS filtering continues to work correctly
4. All existing coach_validator tests pass (376 tests)
5. New test covers keyword extraction from backtick-formatted text
6. New test covers keyword extraction from quote-formatted text

## Architectural Invariants (MUST preserve)

- **INV-1**: `_match_by_promises()` path is NOT modified
- **INV-4**: `_strip_criterion_prefix()` is NOT modified
- **INV-6**: After this fix, `_extract_keywords()` is ALIGNED with `_extract_criterion_keywords()` in synthetic_report.py

## Test Approach

```python
def test_extract_keywords_strips_backticks():
    """Verify backtick-delimited text produces clean keywords."""
    validator = CoachValidator(...)
    keywords = validator._extract_keywords('`Settings` class has `log_level` field')
    assert 'settings' in keywords
    assert 'log_level' in keywords
    assert '`settings`' not in keywords

def test_extract_keywords_strips_quotes():
    """Verify quoted text produces clean keywords."""
    validator = CoachValidator(...)
    keywords = validator._extract_keywords('default "INFO"')
    assert 'info' in keywords
    assert '"info"' not in keywords
```

## Evidence

- Simulation: Turn 2 Jaccard similarity jumps from 30% → 100% for AC-001–005
- Reference: `synthetic_report.py:348` already uses the correct pattern
- Review: `.claude/reviews/TASK-REV-0828-review-report.md`
