---
id: TASK-FIX-AE01
title: Fix agent-enhance duplicate content bug and improve error handling
status: completed
created: 2025-12-08T12:00:00Z
updated: 2025-12-09T00:00:00Z
completed: 2025-12-09T00:00:00Z
priority: high
tags: [agent-enhance, bug-fix, applier, error-handling, json-parsing]
task_type: implementation
complexity: 5
related_tasks: [TASK-REV-FB49]
previous_state: in_review
state_transition_reason: "Task completed successfully - all quality gates passed"
completed_location: tasks/completed/TASK-FIX-AE01/
organized_files: [TASK-FIX-AE01.md, implementation_plan.md, code-review-report.md]
test_results:
  status: passed
  coverage: 95
  last_run: 2025-12-08T23:40:00Z
code_review:
  status: approved
  score: 8.5
  reviewer: code-reviewer agent
plan_audit:
  status: passed
  scope_variance: none
---

# Task: Fix agent-enhance duplicate content bug and improve error handling

## Description

Implement the priority fixes identified in the code quality review (TASK-REV-FB49) of the `/agent-enhance` command. This task addresses the duplicate content bug in the applier module and improves error messaging for JSON parsing failures.

## Background

Review findings from TASK-REV-FB49:
- **Finding 2 (High)**: `_merge_content()` in applier.py produces duplicate sections requiring manual cleanup (21 lines removed post-enhancement)
- **Finding 3 (Medium)**: JSON parsing errors show character positions with no context, making debugging impossible
- **Finding 1 (Medium)**: No partial recovery from large malformed JSON responses

## Acceptance Criteria

### Must Have

- [x] Fix duplicate content bug in `applier.py:_merge_content()`
  - ✅ Implemented fuzzy section header matching (`_section_exists()`, `_normalize_section_name()`)
  - ✅ Handles case variations, underscore variations, and partial matches
  - ✅ Added 21 unit tests for duplicate detection

- [x] Improve JSON parsing error messages in `enhancer.py`
  - ✅ Shows 100-char context window around error position (50 before/after)
  - ✅ Provides likely cause diagnosis (truncation, corruption)
  - ✅ Suggests actionable next steps (use --static)
  - ✅ Added 14 unit tests for error context extraction

### Should Have (Deferred - YAGNI per Architectural Review)

- [ ] ~~Add partial JSON recovery in `parser.py`~~ DEFERRED
  - Existing hybrid fallback sufficient
  - Deferred per architectural review recommendation

### Could Have

- [ ] Add template-based code example extraction to static fallback
  - Not implemented (out of scope for this task)

## Implementation Scope

### Files to Modify

1. `installer/core/lib/agent_enhancement/applier.py`
   - Add `_section_exists()` method with fuzzy matching
   - Update `_merge_content()` to use new method

2. `installer/core/lib/agent_enhancement/enhancer.py`
   - Improve `json.JSONDecodeError` handler (lines 401-405)
   - Add context extraction and actionable suggestions

3. `installer/core/lib/agent_enhancement/parser.py`
   - Add `_attempt_partial_recovery()` method
   - Integrate into `parse()` as final fallback

### Test Coverage Required

- Unit tests for `_section_exists()` fuzzy matching
- Unit tests for partial JSON recovery
- Integration test for error message quality

## Technical Notes

### Duplicate Content Fix

```python
def _section_exists(self, content: str, section_name: str) -> bool:
    """
    Check if section already exists (case-insensitive, fuzzy).
    """
    normalized = section_name.replace('_', ' ').strip().lower()
    for line in content.split('\n'):
        if line.strip().startswith('## '):
            existing = line.strip()[3:].lower()
            if normalized in existing or existing in normalized:
                return True
    return False
```

### Error Message Improvement

```python
except json.JSONDecodeError as e:
    error_pos = e.pos if hasattr(e, 'pos') else 0
    context_start = max(0, error_pos - 50)
    context_end = min(len(result_text), error_pos + 50)
    context = result_text[context_start:context_end]

    logger.error(
        f"AI response parsing failed\n"
        f"  Error: {e.msg} at position {error_pos}\n"
        f"  Context: ...{context}...\n"
        f"  Likely cause: AI response truncated or corrupted\n"
        f"  Suggestion: Re-run with --static for reliable results"
    )
```

## Review Report

Full analysis available at: `.claude/reviews/TASK-REV-FB49-review-report.md`

## Estimated Effort

- Duplicate content fix: 2-4 hours
- Error message improvement: 1-2 hours
- Partial JSON recovery: 4-8 hours
- Testing: 2-4 hours

**Total**: 9-18 hours (1-2 days)
