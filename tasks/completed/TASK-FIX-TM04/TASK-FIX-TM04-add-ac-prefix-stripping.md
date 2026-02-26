---
id: TASK-FIX-TM04
title: Add AC-XXX prefix stripping to _strip_criterion_prefix()
status: completed
task_type: implementation
created: 2026-02-25T12:00:00Z
completed: 2026-02-25T13:00:00Z
completed_location: tasks/completed/TASK-FIX-TM04/
priority: medium
tags: [autobuild, coach-validator, text-matching, defense-in-depth, P2]
complexity: 1
parent_review: TASK-REV-0828
feature_id: FEAT-TM-FIX
wave: 2
implementation_mode: direct
dependencies: [TASK-FIX-TM01]
files_touched: [guardkit/orchestrator/quality_gates/coach_validator.py]
---

# Task: Add `AC-XXX:` prefix stripping to `_strip_criterion_prefix()`

## Problem

The vLLM Player on Turn 2 formatted `requirements_addressed` entries with `AC-XXX:` prefixes (e.g., `AC-001: Settings class has log_level field with default INFO`). The `_strip_criterion_prefix()` method at coach_validator.py:1803-1843 strips markdown checkboxes, bullets, and numbered prefixes, but does NOT strip `AC-XXX:` patterns.

This prevents exact matching even when the text after the prefix matches.

## Solution

Add `AC-XXX:` prefix stripping at the end of `_strip_criterion_prefix()`, before the return:

```python
# At end of _strip_criterion_prefix(), before return:
ac_match = re.match(r'^AC-\d+:\s*', cleaned)
if ac_match:
    cleaned = cleaned[ac_match.end():].strip()
```

## Acceptance Criteria

1. `_strip_criterion_prefix()` strips `AC-NNN:` prefixes (e.g., `AC-001:`, `AC-123:`)
2. Stripping preserves text after the prefix
3. Non-AC prefixes continue to work (bullets, checkboxes, numbered lists)
4. All existing coach_validator tests pass (376 tests)
5. New test covers AC-prefix stripping

## Architectural Invariants (MUST preserve)

- **INV-4**: `_strip_criterion_prefix()` is being EXTENDED (not replaced) — existing prefix patterns preserved

## Test Approach

```python
def test_strip_criterion_prefix_ac_pattern():
    """Verify AC-XXX: prefix is stripped."""
    validator = CoachValidator(...)
    result = validator._strip_criterion_prefix('AC-001: Settings class has log_level field')
    assert result == 'Settings class has log_level field'

def test_strip_criterion_prefix_existing_patterns_preserved():
    """Verify existing prefix patterns still work."""
    validator = CoachValidator(...)
    assert validator._strip_criterion_prefix('- [ ] Some criterion') == 'Some criterion'
    assert validator._strip_criterion_prefix('1. Some criterion') == 'Some criterion'
```

## Evidence

- vLLM Turn 2 data: `AC-001: Settings class has log_level field with default INFO`
- Review: `.claude/reviews/TASK-REV-0828-review-report.md`
