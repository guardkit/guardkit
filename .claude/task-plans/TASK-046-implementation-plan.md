# Implementation Plan: TASK-046 - Hash-Based ID Generator

**Status**: Draft
**Created**: 2025-01-10
**Complexity**: 5/10 (Medium)
**Estimated Duration**: 3-4 hours

## 1. Overview

Implement a collision-free hash-based task ID generator using SHA-256 with progressive length scaling. This replaces the sequential numbering system that led to duplicate IDs (TASK-003 appearing twice).

**Key Innovation**: Cryptographic hashing eliminates duplicates by design, while progressive length scaling keeps IDs compact for small projects.

## 2. Architecture

### 2.1 File Structure
```
installer/core/lib/
├── id_generator.py          # Main implementation (NEW)
└── __init__.py             # May need update for exports

tests/
└── test_id_generator.py    # Comprehensive test suite (NEW)
```

### 2.2 Core Components

#### Component 1: Hash Generator
**Function**: `generate_task_id(prefix: Optional[str] = None, existing_ids: Set[str] = None) -> str`

**Responsibilities**:
- Determine hash length based on task count
- Generate cryptographic seed
- Create SHA-256 hash
- Check for collisions (rare but possible)
- Format with optional prefix

**Algorithm**:
1. Count existing tasks → determine hash length (4/5/6 chars)
2. Create seed: `datetime.now(datetime.UTC).isoformat() + secrets.token_hex(8)`
3. Hash seed: `hashlib.sha256(seed.encode()).hexdigest()`
4. Extract first N characters of hex digest
5. Check collision against existing_ids set
6. If collision, regenerate (max 10 attempts)
7. Return formatted: `TASK-{prefix}-{hash}` or `TASK-{hash}`

#### Component 2: Task Counter
**Function**: `count_existing_tasks() -> int`

**Responsibilities**:
- Scan all task directories (backlog, in_progress, in_review, completed, blocked)
- Count `.md` files matching pattern `TASK-*.md`
- Return total count for scaling logic

**Implementation**:
```python
def count_existing_tasks() -> int:
    """Count all tasks across directories."""
    task_dirs = [
        'tasks/backlog',
        'tasks/in_progress',
        'tasks/in_review',
        'tasks/completed',
        'tasks/blocked'
    ]
    count = 0
    for dir_path in task_dirs:
        if Path(dir_path).exists():
            count += len(list(Path(dir_path).glob('TASK-*.md')))
    return count
```

#### Component 3: Collision Checker
**Function**: `task_exists(task_id: str) -> bool`

**Responsibilities**:
- Check if task ID already exists in filesystem
- Support for both formats: `TASK-{hash}` and `TASK-{prefix}-{hash}`

**Implementation**:
```python
def task_exists(task_id: str) -> bool:
    """Check if task ID exists in any directory."""
    task_dirs = ['tasks/backlog', 'tasks/in_progress', 'tasks/in_review',
                 'tasks/completed', 'tasks/blocked']
    for dir_path in task_dirs:
        if Path(f"{dir_path}/{task_id}.md").exists():
            return True
    return False
```

### 2.3 Length Scaling Logic

| Task Count | Hash Length | Collision Risk | Rationale |
|-----------|-------------|----------------|-----------|
| 0-499     | 4 chars     | ~0.006% at 500 | Compact for small projects |
| 500-1,499 | 5 chars     | ~0.015% at 1,500 | Balanced |
| 1,500+    | 6 chars     | ~0.000% at 5,000 | Enterprise scale |

**Formula**:
```python
def get_hash_length(task_count: int) -> int:
    if task_count < 500:
        return 4
    elif task_count < 1500:
        return 5
    else:
        return 6
```

## 3. Implementation Details

### 3.1 Core Function Implementation

```python
import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set

def generate_task_id(
    prefix: Optional[str] = None,
    existing_ids: Optional[Set[str]] = None,
    max_attempts: int = 10
) -> str:
    """
    Generate collision-free hash-based task ID.

    Args:
        prefix: Optional prefix (e.g., 'E01', 'DOC', 'FIX')
        existing_ids: Optional set of existing IDs for collision check
        max_attempts: Maximum collision resolution attempts

    Returns:
        Task ID in format 'TASK-{hash}' or 'TASK-{prefix}-{hash}'

    Raises:
        RuntimeError: If unable to generate unique ID after max_attempts
    """
    task_count = count_existing_tasks()
    hash_length = get_hash_length(task_count)

    for attempt in range(max_attempts):
        # Generate seed from timestamp + random bytes
        seed = f"{datetime.now(timezone.utc).isoformat()}{secrets.token_hex(8)}"

        # Create SHA-256 hash
        hash_obj = hashlib.sha256(seed.encode())
        task_hash = hash_obj.hexdigest()[:hash_length].upper()

        # Format ID
        if prefix:
            task_id = f"TASK-{prefix}-{task_hash}"
        else:
            task_id = f"TASK-{task_hash}"

        # Check collision
        if existing_ids is not None:
            if task_id not in existing_ids:
                return task_id
        elif not task_exists(task_id):
            return task_id

    raise RuntimeError(
        f"Failed to generate unique task ID after {max_attempts} attempts"
    )
```

### 3.2 Edge Cases & Error Handling

**Edge Cases**:
1. **Empty prefix**: Treat as None
2. **Whitespace prefix**: Strip and validate
3. **Long prefix**: No restriction (user's choice)
4. **Special characters in prefix**: Allow (will be part of ID)
5. **No existing tasks**: Default to 4-char hash

**Error Scenarios**:
1. **Collision after 10 attempts**: Raise RuntimeError (extremely rare)
2. **Invalid task directory**: Return 0 count (graceful degradation)
3. **Filesystem errors**: Propagate with context

### 3.3 Performance Optimizations

1. **Caching task count**: Not needed (count is fast ~1ms for 10K tasks)
2. **Set vs filesystem check**: Use existing_ids set when available
3. **Hash algorithm**: SHA-256 is optimal (fast + secure)
4. **Early exit**: Return immediately on non-collision

**Benchmarks**:
- Generate 1,000 IDs: Target <1 second (expected ~200-300ms)
- Generate 10,000 IDs: Expected ~2-3 seconds
- Count 10,000 tasks: Expected ~5-10ms

## 4. Testing Strategy

### 4.1 Unit Tests

**Test File**: `tests/test_id_generator.py`

#### Test Suite Breakdown

**1. Hash Generation Tests** (5 tests)
- `test_generate_basic_id`: No prefix, default length
- `test_generate_id_with_prefix`: With prefix
- `test_hash_format`: Verify uppercase hex format
- `test_hash_uniqueness`: Generate 100 IDs, all unique
- `test_deterministic_length`: Verify length based on count

**2. Length Scaling Tests** (4 tests)
- `test_length_4_chars_under_500`: 0-499 tasks → 4 chars
- `test_length_5_chars_500_to_1499`: 500-1499 tasks → 5 chars
- `test_length_6_chars_over_1500`: 1500+ tasks → 6 chars
- `test_length_boundary_conditions`: Test exact boundaries (499, 500, 1499, 1500)

**3. Prefix Tests** (4 tests)
- `test_prefix_none`: None prefix → `TASK-XXXX`
- `test_prefix_standard`: "E01" → `TASK-E01-XXXX`
- `test_prefix_empty_string`: "" → `TASK-XXXX`
- `test_prefix_special_chars`: "FIX-123" → `TASK-FIX-123-XXXX`

**4. Collision Tests** (3 tests)
- `test_no_collision_10000_ids`: Generate 10K IDs, all unique
- `test_collision_detection_with_set`: Pass existing_ids set
- `test_collision_retry_logic`: Mock collision, verify retry

**5. Performance Tests** (2 tests)
- `test_generate_1000_ids_under_1_second`: Performance target
- `test_count_tasks_performance`: Measure counting overhead

**6. Edge Case Tests** (5 tests)
- `test_whitespace_prefix`: " E01 " → strip
- `test_empty_task_dirs`: No tasks → 4 char hash
- `test_max_attempts_exceeded`: Force failure scenario
- `test_task_exists_check`: Verify filesystem check
- `test_concurrent_generation`: Thread safety (if needed)

**Total**: 23 tests

### 4.2 Coverage Requirements

- **Target**: ≥90% (Task requires ≥90%)
- **Critical paths**: 100% (hash generation, collision check)
- **Edge cases**: 100% (error handling)
- **Performance**: Verified via benchmarks

### 4.3 Test Execution

```bash
# Run all tests
pytest tests/test_id_generator.py -v

# With coverage
pytest tests/test_id_generator.py -v --cov=installer/core/lib/id_generator --cov-report=term --cov-report=html

# Performance only
pytest tests/test_id_generator.py -v -k performance
```

## 5. Dependencies

**Standard Library Only** (Zero external dependencies):
- `hashlib` - SHA-256 hashing
- `secrets` - Cryptographic random
- `datetime` - Timestamp generation
- `pathlib` - File system operations
- `typing` - Type hints

## 6. Integration Points

**Current Integration**: None (new standalone module)

**Future Integration** (separate tasks):
- TASK-047: Validation utilities will import this module
- TASK-048: `/task-create` command will use `generate_task_id()`
- TASK-049: External mapper will reference hash IDs

## 7. Rollout Plan

**Phase 1** (This task):
- Implement core generator
- Comprehensive testing
- Documentation

**Phase 2** (TASK-048):
- Integrate into `/task-create`
- Migrate existing commands

**Phase 3** (TASK-047):
- Add validation layer
- Duplicate detection utilities

## 8. Quality Gates

### 8.1 Pre-Implementation Checklist
- [x] Requirements clear and complete
- [x] Algorithm validated (POC exists)
- [x] Test strategy defined
- [x] No external dependencies needed

### 8.2 Implementation Checklist
- [ ] All functions implemented per spec
- [ ] Type hints on all public functions
- [ ] Docstrings with examples
- [ ] Error handling complete

### 8.3 Testing Checklist
- [ ] 23 unit tests passing
- [ ] Coverage ≥90%
- [ ] Zero collisions in 10K test
- [ ] Performance: 1K IDs < 1 second
- [ ] All edge cases covered

### 8.4 Review Checklist
- [ ] Code follows Python best practices
- [ ] No security issues (uses secrets module correctly)
- [ ] Documentation complete
- [ ] Ready for integration (TASK-048)

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|---------|------------|
| Hash collision | Very Low | High | Retry logic + length scaling |
| Performance degradation | Low | Medium | Benchmarking + optimization |
| Integration complexity | Low | Medium | Separate integration task |
| Filesystem errors | Low | Low | Graceful error handling |

## 10. Success Metrics

- ✅ Zero collisions in 10,000 ID generation test
- ✅ Performance: 1,000 IDs in <1 second
- ✅ Test coverage ≥90%
- ✅ All acceptance criteria met
- ✅ No external dependencies
- ✅ Ready for integration in TASK-048

## 11. Files to Create/Modify

### New Files
1. `installer/core/lib/id_generator.py` (~150 lines)
2. `tests/test_id_generator.py` (~400 lines)

### Modified Files
None (standalone implementation)

### Documentation
- Implementation plan: `.claude/task-plans/TASK-046-implementation-plan.md` (this file)

**Total New Lines**: ~550
**Total Modified Lines**: 0

---

**Plan Status**: Ready for Phase 2.5 (Architectural Review)
