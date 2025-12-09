# Implementation Plan: TASK-FIX-AE01

**Task**: Fix agent-enhance duplicate content bug and improve error handling
**Created**: 2025-12-08
**Complexity**: 5/10 (Medium)
**Architectural Review**: 78/100 (Approved with Recommendations)

## Executive Summary

Implement priority fixes from code quality review (TASK-REV-FB49):
1. **Finding 2 (High)**: Duplicate content bug in applier.py
2. **Finding 3 (Medium)**: Poor JSON error messages in enhancer.py
3. **Finding 1 (Medium)**: Partial JSON recovery (DEFERRED - YAGNI)

**Estimated Duration**: 4-6 hours (after scope adjustment)
**Risk Level**: Low

## Scope (Adjusted Per Architectural Review)

### In Scope (Must Have)
1. Fix duplicate content bug with fuzzy section matching
2. Improve JSON parsing error messages with context
3. Extract normalization logic (DRY)
4. Handle section header edge cases

### Out of Scope (Deferred - YAGNI)
- Partial JSON recovery in parser.py (existing hybrid fallback sufficient)

## Files to Modify

| File | Change Type | Est. Lines | Description |
|------|------------|------------|-------------|
| applier.py | Add methods | +45 | `_section_exists()`, `_normalize_section_name()` |
| enhancer.py | Modify handler | +20 | Improved JSONDecodeError context |
| test_applier_duplicate_detection.py | NEW | +120 | Unit tests for fuzzy matching |
| test_enhancer_error_messages.py | NEW | +90 | Unit tests for error context |

**Total**: ~275 lines (65 production, 210 test)

## Implementation Details

### 1. applier.py - Fuzzy Section Matching

Add new methods:
```python
def _normalize_section_name(self, section_name: str) -> str:
    """Normalize section name for comparison."""
    return section_name.replace('_', ' ').strip().lower()

def _section_exists(self, content: str, section_name: str) -> bool:
    """Check if section already exists (case-insensitive, fuzzy)."""
    normalized = self._normalize_section_name(section_name)

    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('##'):
            header_text = stripped[2:].lstrip()
            existing = self._normalize_section_name(header_text)
            if normalized in existing or existing in normalized:
                return True
    return False
```

Update `_merge_content()` line 224:
```python
# OLD: if section_header not in existing_content:
# NEW:
if not self._section_exists(existing_content, section_name):
```

### 2. enhancer.py - Error Context Improvement

Update JSONDecodeError handler (lines 401-405):
```python
except json.JSONDecodeError as e:
    duration = time.time() - start_time
    error_pos = e.pos if hasattr(e, 'pos') else 0
    context_start = max(0, error_pos - 50)
    context_end = min(len(result_text), error_pos + 50)
    context_snippet = result_text[context_start:context_end]

    logger.error(
        f"AI response parsing failed after {duration:.2f}s\n"
        f"  Error: {e.msg} at position {error_pos}\n"
        f"  Context: ...{context_snippet}...\n"
        f"  Response size: {len(result_text)} chars\n"
        f"  Likely cause: AI response truncated or corrupted\n"
        f"  Suggestion: Re-run with --static for reliable results"
    )
    raise ValidationError(f"Invalid JSON at position {error_pos}: {e.msg}")
```

## Test Strategy

### Test Files to Create
1. `tests/lib/agent_enhancement/test_applier_duplicate_detection.py`
2. `tests/lib/agent_enhancement/test_enhancer_error_messages.py`

### Coverage Targets
- New methods: ≥90% line coverage
- Overall module: Maintain ≥80%

## Acceptance Criteria

- [ ] Duplicate sections no longer created when running /agent-enhance
- [ ] JSON errors show 50 chars context around error position
- [ ] Error messages include actionable suggestions
- [ ] All existing tests pass
- [ ] New tests achieve ≥90% coverage for new code

## Risks and Mitigations

| Risk | Probability | Mitigation |
|------|------------|------------|
| Fuzzy matching too permissive | Medium | Add tests for false positives |
| Breaking existing tests | Low | Run full test suite before/after |
| Performance regression | Low | Keep error handling fast |

## Rollback Plan

```bash
git revert <commit-hash>
```
