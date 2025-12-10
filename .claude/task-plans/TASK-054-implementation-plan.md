# TASK-054 Implementation Plan: Add Prefix Support and Inference

**Task ID:** TASK-054
**Title:** Add prefix support and inference
**Status:** in_progress
**Complexity:** 5/10
**Estimated Duration:** 3-4 hours
**Date:** 2025-11-10

## 1. Overview

Implement intelligent prefix support for task IDs, including automatic inference from epic links, tags, and task titles. This enhancement makes hash IDs more organized and human-friendly by grouping related tasks under common prefixes.

**Current State:**
- Basic prefix support exists in `generate_task_id()` (manual specification)
- Prefix validation is basic (`is_valid_prefix()`)
- No inference capabilities
- No prefix registry or mappings

**Target State:**
- Full prefix inference from epic, tags, and title keywords
- Comprehensive prefix validation with normalization
- Prefix registry for consistency
- Clear user feedback when prefix is inferred
- User override capability

## 2. Requirements Analysis

### Acceptance Criteria
1. ✅ Manual prefix specification via `prefix:` parameter (already exists)
2. 🔨 Automatic prefix inference from epic (epic:EPIC-001 → E01)
3. 🔨 Automatic prefix inference from tags (tags:[docs] → DOC)
4. 🔨 Automatic prefix inference from title keywords
5. 🔨 Comprehensive prefix validation (2-4 uppercase alphanumeric)
6. 🔨 Prefix registry for consistency
7. 🔨 User override of inferred prefix
8. 🔨 Clear messaging when prefix is inferred

### Test Requirements
- Unit tests for manual prefix specification
- Unit tests for epic-based inference
- Unit tests for tag-based inference
- Unit tests for title-based inference
- Unit tests for prefix validation
- Integration tests with /task-create
- Test coverage ≥85%

## 3. Technical Design

### 3.1 Architecture

**Pattern:** Function-based with data-driven mappings
**Location:** `installer/core/lib/id_generator.py`
**Dependencies:** `re`, `typing` (already imported)

**Design Principles:**
- **Priority-based inference**: Manual > Epic > Tags > Title > None
- **Data-driven**: Use dictionaries for extensibility
- **Fail-safe**: Return None if no inference possible
- **Validation-first**: Always validate before using prefix

### 3.2 Data Structures

#### Standard Prefix Registry
```python
STANDARD_PREFIXES: Dict[str, str] = {
    # Domain-based
    "DOC": "Documentation",
    "TEST": "Testing",
    "FIX": "Bug fixes",
    "FEAT": "Features",
    "REFA": "Refactoring",

    # Stack-based
    "API": "API/Backend",
    "UI": "User interface",
    "DB": "Database",
    "INFR": "Infrastructure",
}
```

#### Tag-to-Prefix Mapping
```python
TAG_PREFIX_MAP: Dict[str, str] = {
    "docs": "DOC",
    "documentation": "DOC",
    "test": "TEST",
    "testing": "TEST",
    "bug": "FIX",
    "bugfix": "FIX",
    "fix": "FIX",
    "feature": "FEAT",
    "api": "API",
    "backend": "API",
    "ui": "UI",
    "frontend": "UI",
    "database": "DB",
    "db": "DB",
    "infra": "INFR",
    "infrastructure": "INFR",
}
```

#### Title Keyword Patterns
```python
TITLE_KEYWORDS: Dict[str, str] = {
    r"^fix\b": "FIX",
    r"^bug\b": "FIX",
    r"\bdocument": "DOC",
    r"\btest": "TEST",
    r"\bapi\b": "API",
    r"\bui\b": "UI",
    r"\bdatabase\b": "DB",
}
```

### 3.3 Core Functions

#### Function 1: `infer_prefix()`
**Purpose:** Infer prefix from task context with priority order

**Signature:**
```python
def infer_prefix(
    epic: Optional[str] = None,
    tags: Optional[List[str]] = None,
    title: Optional[str] = None,
    manual_prefix: Optional[str] = None
) -> Optional[str]
```

**Logic:**
1. If `manual_prefix` provided → validate and return
2. If `epic` provided → extract number (EPIC-001 → E01)
3. If `tags` provided → lookup in TAG_PREFIX_MAP
4. If `title` provided → match against TITLE_KEYWORDS patterns
5. Otherwise → return None

#### Function 2: `validate_prefix()`
**Purpose:** Enhanced validation with normalization

**Signature:**
```python
def validate_prefix(prefix: str) -> str
```

**Logic:**
1. Check if empty → raise ValueError
2. Uppercase the prefix
3. Remove invalid characters (keep only A-Z, 0-9)
4. Truncate to 4 characters if longer
5. Check length (2-4) → raise ValueError if too short
6. Return normalized prefix

#### Function 3: `register_prefix()`
**Purpose:** Register custom prefix in registry

**Signature:**
```python
def register_prefix(prefix: str, description: str) -> None
```

**Logic:**
1. Validate prefix format
2. Add to STANDARD_PREFIXES dictionary

## 4. Implementation Steps

### Phase 1: Add Data Structures (30 min)
1. Add `STANDARD_PREFIXES` dictionary
2. Add `TAG_PREFIX_MAP` dictionary
3. Add `TITLE_KEYWORDS` dictionary
4. Add imports: `from typing import Dict, List`

**Estimated Lines:** +60 lines

### Phase 2: Implement Core Functions (60 min)
1. Implement `validate_prefix()` function
2. Implement `infer_prefix()` function
3. Implement `register_prefix()` function

**Estimated Lines:** +100 lines

### Phase 3: Update Existing Functions (15 min)
1. Enhance `is_valid_prefix()` to use new `validate_prefix()`
2. Update `__all__` exports

**Estimated Lines:** +10 lines (modifications)

### Phase 4: Add Documentation (15 min)
1. Update module docstring
2. Add comprehensive docstrings for new functions

**Estimated Lines:** +80 lines (docstrings)

## 5. Testing Strategy

### 5.1 Unit Tests

**Test File:** `tests/lib/test_id_generator_prefix_inference.py` (new file)

#### Test Suite 1: Prefix Validation
- test_validate_prefix_uppercase()
- test_validate_prefix_truncate()
- test_validate_prefix_invalid_chars()
- test_validate_prefix_too_short()
- test_validate_prefix_empty()

#### Test Suite 2: Epic Inference
- test_infer_prefix_from_epic()
- test_infer_prefix_epic_invalid_format()
- test_infer_prefix_epic_with_padding()

#### Test Suite 3: Tag Inference
- test_infer_prefix_from_tags()
- test_infer_prefix_multiple_tags()
- test_infer_prefix_tags_case_insensitive()

#### Test Suite 4: Title Inference
- test_infer_prefix_from_title()
- test_infer_prefix_title_no_match()

#### Test Suite 5: Priority Order
- test_infer_prefix_manual_override()
- test_infer_prefix_epic_over_tags()
- test_infer_prefix_tags_over_title()

#### Test Suite 6: Registry Management
- test_register_prefix()
- test_register_prefix_validates()

### 5.2 Coverage Goals

**Target:** ≥85% coverage

## 6. File Changes Summary

### Modified Files
1. **installer/core/lib/id_generator.py**
   - Add 3 new dictionaries
   - Add 3 new functions
   - Enhance is_valid_prefix()
   - Update module docstring and __all__ exports
   - **Estimated:** +250 lines

### New Files
1. **tests/lib/test_id_generator_prefix_inference.py**
   - Unit tests for prefix inference
   - **Estimated:** ~200 lines

**Total New Lines:** ~450 lines
**Files Modified:** 1
**Files Created:** 1

## 7. Risk Assessment

### Complexity: 5/10 (Medium)

**Low Risk Areas:**
- Data structures (dictionaries) - straightforward
- Validation logic - well-defined rules
- Registry management - simple dictionary operations

**Medium Risk Areas:**
- Epic parsing regex - must handle various formats
- Title keyword matching - pattern complexity
- Priority logic - multiple conditional branches

**Mitigation:**
- Comprehensive unit tests for regex patterns
- Test all priority combinations
- Clear docstrings with examples

### Backwards Compatibility
**Status:** ✅ Fully compatible

- Existing `generate_task_id()` unchanged
- New functions are additive
- No breaking changes to API

## 8. Success Criteria

### Functional
- ✅ All 8 acceptance criteria met
- ✅ All inference priority levels work correctly
- ✅ Prefix validation handles all edge cases
- ✅ Registry management works as expected

### Quality
- ✅ Test coverage ≥85%
- ✅ All tests pass (100% pass rate)
- ✅ No compilation errors
- ✅ Comprehensive docstrings

## 9. Timeline

| Phase | Task | Duration |
|-------|------|----------|
| 1 | Add data structures | 30 min |
| 2 | Implement core functions | 60 min |
| 3 | Update existing functions | 15 min |
| 4 | Add documentation | 15 min |
| 5 | Write unit tests | 90 min |
| 6 | Code review & fixes | 30 min |

**Total Estimated Time:** 4 hours

## 10. Design Decisions

1. **Why dictionary-based mappings?**
   - Easy to extend without code changes
   - Clear separation of data and logic
   - Easy to customize per project

2. **Why priority order (manual > epic > tags > title)?**
   - Manual gives users full control
   - Epic is most specific context
   - Tags are explicit categorization
   - Title is inferred/ambiguous

3. **Why 2-4 character prefixes?**
   - Balance between readability and uniqueness
   - Consistent with existing validation
   - Matches common prefix patterns

---

**Implementation Status:** Ready to begin Phase 1
