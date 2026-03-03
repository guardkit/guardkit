---
id: TASK-FIX-TM03
title: Add markdown formatting stripping to _match_by_text() normalization
status: backlog
task_type: feature
created: 2026-02-25T12:00:00Z
priority: high
tags: [autobuild, coach-validator, text-matching, defense-in-depth, P1]
complexity: 2
parent_review: TASK-REV-0828
feature_id: FEAT-TM-FIX
wave: 2
implementation_mode: task-work
dependencies: [TASK-FIX-TM01]
files_touched: [guardkit/orchestrator/quality_gates/coach_validator.py]
---

# Task: Add markdown formatting stripping to `_match_by_text()` normalization

## Problem

Acceptance criteria text often contains markdown formatting — backticks for code (`` `Settings` ``), quotes for values (`"INFO"`). Player responses typically omit this formatting. Strategies 1 (exact) and 2 (substring) in `_match_by_text()` fail because `settings` ≠ `` `settings` `` as strings.

This is a defense-in-depth fix that enables Strategies 1 and 2 to work even when the only difference is formatting, complementing Fix 1 (which fixes Strategy 3 keyword matching).

## Solution

Add a `_strip_markdown_formatting()` static method and apply it in `_match_by_text()` normalization:

```python
@staticmethod
def _strip_markdown_formatting(text: str) -> str:
    """Strip backticks and quotes from text for comparison.

    Strips: ` (backtick), " (double quote), ' (single quote), \u201c \u201d (smart quotes)
    Does NOT strip: _ (underscore) — significant in identifiers like log_level
    """
    return re.sub(r'[`"\'\u201c\u201d]', '', text)
```

Apply in `_match_by_text()` normalization (around lines 1914-1925):

```python
# Existing prefix stripping
stripped_met = [self._strip_criterion_prefix(r) for r in requirements_met]
# NEW: strip markdown formatting
stripped_met = [self._strip_markdown_formatting(r) for r in stripped_met]
normalized_met = {r.lower().strip() for r in stripped_met}

for i, criterion_text in enumerate(acceptance_criteria):
    stripped_criterion = self._strip_criterion_prefix(criterion_text)
    stripped_criterion = self._strip_markdown_formatting(stripped_criterion)  # NEW
    normalized = stripped_criterion.lower().strip()
```

## Acceptance Criteria

1. New `_strip_markdown_formatting()` static method strips backticks and quotes
2. Does NOT strip underscores (important for identifiers like `log_level`)
3. Applied to both `requirements_met` and `acceptance_criteria` in `_match_by_text()`
4. Strategy 1 (exact) and Strategy 2 (substring) benefit from stripping
5. All existing coach_validator tests pass (376 tests)
6. New test verifies backtick stripping enables exact match
7. New test verifies underscore preservation

## Architectural Invariants (MUST preserve)

- **INV-1**: `_match_by_promises()` is NOT modified
- **INV-4**: `_strip_criterion_prefix()` is NOT modified — new stripping is a separate step

## Test Approach

```python
def test_strip_markdown_formatting_backticks():
    """Verify backticks are stripped."""
    assert CoachValidator._strip_markdown_formatting('`Settings` class') == 'Settings class'

def test_strip_markdown_formatting_quotes():
    """Verify quotes are stripped."""
    assert CoachValidator._strip_markdown_formatting('default "INFO"') == 'default INFO'

def test_strip_markdown_formatting_preserves_underscores():
    """Verify underscores are preserved."""
    assert CoachValidator._strip_markdown_formatting('log_level') == 'log_level'

def test_match_by_text_with_formatting_differences():
    """Verify text matching succeeds when only formatting differs."""
    # AC: `Settings` class has `log_level` field with default "INFO"
    # Player: Settings class has log_level field with default INFO
    # Expected: Match (exact or substring)
```

## Evidence

- Simulation: Enables substring matching for AC-001–005 on Turn 2
- With Fix 4 (AC-prefix strip), also enables exact matching
- Review: `.claude/reviews/TASK-REV-0828-review-report.md`
