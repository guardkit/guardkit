# Implementation Plan: TASK-047 - Add ID Validation and Collision Detection

**Task ID**: TASK-047
**Title**: Add ID validation and collision detection
**Status**: in_progress
**Complexity**: 4/10 (Medium)
**Mode**: Standard Development
**Created**: 2025-01-10

## Overview

Implement comprehensive validation and collision detection for task IDs to prevent duplicates. This includes format validation using regex patterns, duplicate checking across all task directories, subtask notation support, and performance-optimized registry caching.

## Requirements Analysis

### Functional Requirements
1. **Format Validation**: Validate task IDs against pattern `TASK-([A-Z0-9]{2,4}-)?[a-f0-9]{4,6}(\.\d+)?`
2. **Duplicate Detection**: Check for existing IDs across all task directories
3. **Subtask Support**: Validate subtask notation (e.g., `TASK-E01-b2c4.1`)
4. **Clear Error Messages**: Provide actionable error messages for validation failures
5. **Registry Caching**: Build and cache ID registry for performance

### Non-Functional Requirements
1. **Performance**: Validate 1,000 IDs in <100ms
2. **Thread Safety**: Support concurrent validation
3. **Test Coverage**: Achieve ≥85% code coverage
4. **Backward Compatibility**: Work with existing task file structure

## Architecture Design

### Module Structure
```
installer/global/lib/id_generator.py
├── Existing functions (unchanged)
│   ├── generate_task_id()
│   ├── count_existing_tasks()
│   └── task_exists()
└── New validation functions
    ├── validate_task_id()
    ├── check_duplicate()
    ├── build_id_registry()
    └── is_valid_prefix()
```

### Design Patterns
1. **Validation Pattern**: Separate format validation from business logic
2. **Registry Pattern**: Cache IDs for fast lookup (O(1) vs O(n))
3. **Fail-Fast Pattern**: Return immediately on first validation failure
4. **Lazy Loading**: Build registry only when needed

### Data Structures
- **ID Registry**: `Set[str]` for O(1) lookup performance
- **Validation Result**: Return boolean or Optional[str] for duplicate path
- **Error Messages**: String constants for consistency

## Implementation Plan

### Phase 1: Core Validation Functions

#### 1.1 Format Validation (`validate_task_id`)
```python
def validate_task_id(task_id: str) -> bool:
    """
    Validate task ID format.

    Pattern: TASK-([A-Z0-9]{2,4}-)?[a-f0-9]{4,6}(\.\d+)?

    Examples:
        TASK-a3f2          ✓ (simple hash)
        TASK-E01-a3f2      ✓ (with prefix)
        TASK-E01-a3f2.1    ✓ (with subtask)
        TASK-XYZ-a3f2      ✗ (invalid prefix - must be 2-4 chars)
        TASK-e01-A3F2      ✗ (hash must be lowercase)

    Args:
        task_id: Task ID to validate

    Returns:
        True if valid format, False otherwise
    """
```

**Implementation Steps**:
1. Compile regex pattern (cached for performance)
2. Match against full task ID
3. Return boolean result

**Testing**:
- Valid patterns: simple, with prefix, with subtask
- Invalid patterns: wrong format, case errors, length violations

#### 1.2 Prefix Validation (`is_valid_prefix`)
```python
def is_valid_prefix(prefix: str) -> bool:
    """
    Validate prefix format.

    Rules:
        - 2-4 uppercase alphanumeric characters
        - Examples: E01, DOC, FIX, EPIC

    Args:
        prefix: Prefix string to validate

    Returns:
        True if valid, False otherwise
    """
```

**Implementation Steps**:
1. Check length (2-4 characters)
2. Validate uppercase alphanumeric only
3. Return boolean result

**Testing**:
- Valid: E01, DOC, FIX1, EPIC
- Invalid: e01 (lowercase), X (too short), EXTRA (too long), E-01 (special chars)

### Phase 2: Duplicate Detection

#### 2.1 ID Registry Builder (`build_id_registry`)
```python
def build_id_registry() -> Set[str]:
    """
    Build registry of all existing task IDs.

    Scans all task directories and extracts task IDs from filenames.
    Uses Set for O(1) lookup performance.

    Returns:
        Set of existing task IDs (without .md extension)

    Performance:
        - 1,000 tasks: ~10ms
        - 5,000 tasks: ~50ms
    """
```

**Implementation Steps**:
1. Initialize empty set
2. Iterate through TASK_DIRECTORIES
3. For each directory, glob TASK-*.md files
4. Extract task ID from filename (remove .md)
5. Add to set
6. Return registry

**Optimizations**:
- Use set comprehension for speed
- Path.glob() is faster than os.walk()
- Single pass through all directories

**Testing**:
- Empty directories
- Mixed task formats
- Performance with 1,000+ tasks

#### 2.2 Duplicate Checker (`check_duplicate`)
```python
def check_duplicate(task_id: str) -> Optional[str]:
    """
    Check if task ID exists.

    Returns path to existing file if duplicate found,
    None otherwise.

    Args:
        task_id: Task ID to check

    Returns:
        Path to duplicate file if found, None otherwise

    Examples:
        >>> check_duplicate("TASK-a3f2")
        None  # Not a duplicate

        >>> check_duplicate("TASK-001")
        "tasks/backlog/TASK-001.md"  # Duplicate found
    """
```

**Implementation Steps**:
1. Build registry (or use cached)
2. Check if task_id in registry (O(1))
3. If found, locate file path
4. Return path or None

**Testing**:
- Non-existent IDs return None
- Existing IDs return correct path
- Check across all directories

### Phase 3: Integration with Existing Code

#### 3.1 Update `generate_task_id()`
**Changes**: None required - function already checks duplicates via `task_exists()`

#### 3.2 Error Message Constants
```python
ERROR_DUPLICATE = "❌ ERROR: Duplicate task ID: {task_id}\n   Existing file: {path}"
ERROR_INVALID_FORMAT = "❌ ERROR: Invalid task ID format: {task_id}\n   Expected: TASK-{{hash}} or TASK-{{prefix}}-{{hash}}"
ERROR_INVALID_PREFIX = "❌ ERROR: Invalid prefix: {prefix}\n   Expected: 2-4 uppercase alphanumeric characters"
```

### Phase 4: Performance Optimization

#### 4.1 Registry Caching
```python
# Module-level cache
_id_registry_cache: Optional[Set[str]] = None
_cache_timestamp: Optional[float] = None
CACHE_TTL = 5.0  # seconds

def get_id_registry(force_refresh: bool = False) -> Set[str]:
    """Get ID registry with caching."""
    global _id_registry_cache, _cache_timestamp

    now = time.time()
    cache_valid = (
        _id_registry_cache is not None and
        _cache_timestamp is not None and
        (now - _cache_timestamp) < CACHE_TTL
    )

    if force_refresh or not cache_valid:
        _id_registry_cache = build_id_registry()
        _cache_timestamp = now

    return _id_registry_cache
```

**Benefits**:
- Avoid rescanning filesystem for every validation
- 5-second TTL balances freshness vs performance
- Force refresh option for critical operations

#### 4.2 Thread Safety
```python
import threading

_registry_lock = threading.Lock()

def check_duplicate_threadsafe(task_id: str) -> Optional[str]:
    """Thread-safe duplicate checking."""
    with _registry_lock:
        return check_duplicate(task_id)
```

## Testing Strategy

### Unit Tests (15+ tests)

#### Format Validation Tests (5 tests)
1. `test_validate_simple_hash` - TASK-a3f2
2. `test_validate_with_prefix` - TASK-E01-a3f2
3. `test_validate_with_subtask` - TASK-E01-a3f2.1
4. `test_validate_invalid_format` - Invalid patterns
5. `test_validate_case_sensitivity` - Hash must be lowercase

#### Prefix Validation Tests (4 tests)
6. `test_valid_prefix_2_chars` - E0
7. `test_valid_prefix_4_chars` - EPIC
8. `test_invalid_prefix_length` - Too short/long
9. `test_invalid_prefix_chars` - Lowercase or special chars

#### Duplicate Detection Tests (4 tests)
10. `test_check_duplicate_exists` - Find existing task
11. `test_check_duplicate_not_exists` - No duplicate
12. `test_build_id_registry` - Registry building
13. `test_registry_all_directories` - Check all 5 directories

#### Performance Tests (2 tests)
14. `test_validate_1000_ids_under_100ms` - Performance requirement
15. `test_build_registry_large_dataset` - 1,000+ tasks

#### Thread Safety Tests (1 test)
16. `test_concurrent_validation` - 10 threads validating simultaneously

### Integration Tests (3 tests)
17. `test_end_to_end_validation` - Full validation workflow
18. `test_integration_with_generate_task_id` - Ensure compatibility
19. `test_subtask_validation_workflow` - Subtask notation handling

### Coverage Targets
- **Line Coverage**: ≥85%
- **Branch Coverage**: ≥80%
- **Function Coverage**: 100%

## File Changes

### Modified Files
1. **installer/global/lib/id_generator.py** (~200 lines added)
   - Add validation functions
   - Add error message constants
   - Add registry caching logic
   - Add thread safety utilities
   - Update module exports

### New Test Files
2. **tests/unit/test_id_validation.py** (~400 lines)
   - Unit tests for all validation functions
   - Performance tests
   - Thread safety tests
   - Integration tests

### Documentation Updates
3. **Update docstrings** in id_generator.py
   - Document new functions
   - Add usage examples
   - Document performance characteristics

## Dependencies

### Required
- **TASK-046**: Hash ID generator (completed) - provides base infrastructure

### Optional
- **TASK-048**: Update /task-create command - will use these validation functions

## Risk Assessment

### Technical Risks
1. **Performance Risk**: Registry scanning could be slow with many tasks
   - **Mitigation**: Caching with 5s TTL, benchmarking with 10K tasks

2. **Race Condition Risk**: Concurrent access to registry
   - **Mitigation**: Thread locks, atomic operations

3. **Regex Complexity**: Complex pattern could have edge cases
   - **Mitigation**: Extensive test coverage, documented examples

### Low Risk
- Breaking existing code (only adds new functions)
- Data loss (read-only operations)
- Security issues (local filesystem only)

## Success Criteria

### Functional
- ✓ All acceptance criteria met
- ✓ Format validation works for all patterns
- ✓ Duplicate detection across all directories
- ✓ Clear error messages for all failures

### Non-Functional
- ✓ Performance: 1,000 validations in <100ms
- ✓ Test coverage: ≥85%
- ✓ Thread safety: No race conditions in concurrent tests
- ✓ Code quality: Passes architectural review (≥60/100)

## Implementation Sequence

1. **Phase 1**: Core validation (format, prefix) - 1 hour
2. **Phase 2**: Duplicate detection (registry, checker) - 1 hour
3. **Phase 3**: Performance optimization (caching, threading) - 0.5 hours
4. **Phase 4**: Testing (unit, integration, performance) - 1.5 hours
5. **Phase 5**: Documentation and review - 0.5 hours

**Total Estimated Time**: 4.5 hours

## Rollback Plan

If issues arise:
1. New functions are additive - simply don't use them
2. Existing functionality unchanged
3. No database or state changes to rollback

## Post-Implementation

### Monitoring
- Track validation performance in production
- Monitor cache hit rates
- Watch for validation failures

### Future Enhancements
- Async validation for large registries
- Persistent cache to disk
- Validation API endpoint
- CLI tool for bulk validation

---

**Plan Status**: APPROVED
**Reviewed By**: AI Architect
**Date**: 2025-01-10
