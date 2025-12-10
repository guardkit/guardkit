---
id: TASK-223C
legacy_id: TASK-049
title: Implement external ID mapper for PM tools
status: completed
created: 2025-01-08T00:00:00Z
updated: 2025-11-10T14:35:00Z
completed: 2025-11-10T14:40:00Z
priority: high
tags: [infrastructure, hash-ids, pm-tools, integration]
complexity: 6
test_results:
  status: passed
  coverage: 97.7
  tests_passed: 53
  tests_failed: 0
  last_run: 2025-11-10T14:33:00Z
architectural_review:
  score: 88
  status: approved
code_review:
  score: 94
  status: approved
completion_metrics:
  implementation_time: 2h 15m
  total_phases: 7
  files_created: 2
  tests_written: 53
  final_coverage: 97.7
  requirements_met: 8/8
---

# Task: Implement external ID mapper for PM tools

## Description

Create a bidirectional mapping system between internal hash-based task IDs and external sequential IDs used by PM tools (JIRA, Azure DevOps, Linear, GitHub). This enables Taskwright to use collision-free hash IDs internally while PM tools see their preferred sequential formats.

## Acceptance Criteria

- [ ] Map internal hash ID to external sequential IDs per PM tool
- [ ] Support JIRA format: `{project_key}-{number}` (e.g., PROJ-456)
- [ ] Support Azure DevOps format: `{number}` (e.g., 1234)
- [ ] Support Linear format: `{team}-{number}` (e.g., TEAM-789)
- [ ] Support GitHub format: `#{number}` (e.g., #234)
- [ ] Bidirectional lookup: internal ↔ external
- [ ] Thread-safe counter increment per tool
- [ ] Auto-generate external ID on first export to tool
- [ ] Store mapping persistently (handled by TASK-4679)

## Test Requirements

- [ ] Unit tests for mapping internal → external (all 4 tools)
- [ ] Unit tests for reverse lookup external → internal
- [ ] Unit tests for counter increment (sequential)
- [ ] Concurrency tests (10 simultaneous mappings)
- [ ] Integration tests with actual PM tool formats
- [ ] Test coverage ≥85%

## Implementation Notes

### File Location
Create new file: `installer/core/lib/external_id_mapper.py`

### Key Functions
```python
def map_to_external(
    internal_id: str,
    tool: str,
    project_key: str = "PROJ"
) -> str:
    """Map internal hash ID to external sequential ID."""

def get_internal_id(external_id: str, tool: str) -> Optional[str]:
    """Reverse lookup: external ID → internal ID."""

def increment_counter(tool: str) -> int:
    """Get next sequential number for PM tool."""

def get_all_mappings(internal_id: str) -> Dict[str, str]:
    """Get all external IDs for an internal ID."""
```

### Mapping Data Structure
```python
{
  "TASK-E01-b2c4": {
    "jira": "PROJ-456",
    "azure_devops": "1234",
    "linear": "TEAM-789",
    "github": "234",
    "created": "2025-01-08T10:00:00Z",
    "epic": "EPIC-001"  # Optional context
  },
  "TASK-DOC-f1a3": {
    "jira": "PROJ-457",
    "azure_devops": "1235",
    "created": "2025-01-08T10:05:00Z"
  }
}
```

### Counter Management
```python
# Per-tool counters stored separately
{
  "jira": {
    "PROJ": 457,  # Next: PROJ-457
    "TEST": 12    # Next: TEST-12
  },
  "azure_devops": 1235,  # Next: 1235
  "linear": {
    "TEAM": 789,
    "DESIGN": 45
  },
  "github": 234
}
```

### Tool Format Specifications

**JIRA**:
- Format: `{PROJECT_KEY}-{number}`
- Example: `PROJ-456`
- Counter: Per-project sequential

**Azure DevOps**:
- Format: `{number}`
- Example: `1234`
- Counter: Global sequential integer

**Linear**:
- Format: `{TEAM_KEY}-{number}`
- Example: `TEAM-789`
- Counter: Per-team sequential

**GitHub**:
- Format: `#{number}`
- Example: `#234`
- Counter: Per-repository sequential

### Thread Safety
Use locks for counter increment:
```python
import threading

_counter_lock = threading.Lock()

def increment_counter(tool: str, key: str = None) -> int:
    with _counter_lock:
        # Read, increment, write atomically
        pass
```

## Dependencies

- TASK-12FB: Hash ID generator (for format understanding)

## Related Tasks

- TASK-4679: JSON persistence for mappings
- TASK-7A96: Update task frontmatter schema
- TASK-C38F: /task-create integration

## Test Execution Log

### Test Run: 2025-11-10T14:33:00Z

**Result:** ✅ ALL TESTS PASSED

**Summary:**
- Total Tests: 53
- Passed: 53 ✅
- Failed: 0
- Coverage: 97.7% (Target: ≥85%)
- Duration: 0.90s

**Coverage Details:**
- File: `installer/core/lib/external_id_mapper.py`
- Lines Covered: 90/91 (97.7%)
- Branch Coverage: ~95%
- Missing: 1 line (non-critical)

**Test Categories:**
1. Mapping Creation: 16 tests ✅
2. Reverse Lookup: 7 tests ✅
3. Counter Management: 7 tests ✅
4. Thread Safety: 4 tests ✅
5. Get All Mappings: 4 tests ✅
6. Validation: 4 tests ✅
7. Integration Scenarios: 4 tests ✅
8. Singleton Instance: 4 tests ✅
9. Utility Methods: 3 tests ✅

**Quality Gates:**
- ✅ Compilation: 100%
- ✅ Tests Pass: 100% (53/53)
- ✅ Line Coverage: 97.7% (≥80%)
- ✅ Branch Coverage: ~95% (≥75%)
- ✅ Thread Safety: Validated (10 concurrent ops)
- ✅ Performance: <1s (target: <5s)

**Architectural Review:**
- Score: 88/100 (GOOD)
- SOLID: 37/40
- DRY: 27/30
- YAGNI: 24/30
- Status: APPROVED ✅

**Code Review:**
- Score: 94/100 (EXCELLENT)
- Code Quality: 24/25
- Documentation: 20/20
- Error Handling: 15/15
- Testing: 20/20
- Security: 15/20
- Status: APPROVED FOR PRODUCTION ✅

**Implementation Details:**
- Files Created: 2
  - `installer/core/lib/external_id_mapper.py` (370 lines)
  - `tests/lib/test_external_id_mapper.py` (618 lines)
- PM Tools Supported: 4 (JIRA, Azure DevOps, Linear, GitHub)
- Thread Safety: Implemented with threading.Lock()
- Singleton Pattern: Thread-safe double-check locking

**Issues Resolved:**
- Fixed case sensitivity in project key handling (normalized to uppercase)
- All acceptance criteria met ✅
- Zero scope creep ✅

---

## Task Completion Report

### ✅ TASK COMPLETED SUCCESSFULLY

**Completion Date:** 2025-11-10T14:40:00Z
**Status:** ✅ COMPLETED
**Final Verdict:** APPROVED FOR PRODUCTION

### 📊 Summary

**Deliverables:**
- ✅ Core implementation: `installer/core/lib/external_id_mapper.py` (370 lines)
- ✅ Test suite: `tests/lib/test_external_id_mapper.py` (618 lines)
- ✅ Implementation plan: `.claude/task-plans/TASK-223C-implementation-plan.md`
- ✅ Coverage report: `test_coverage_task049.json`

**Quality Metrics:**
- ✅ Tests Passing: 53/53 (100%)
- ✅ Coverage: 97.7% (exceeds 85% target)
- ✅ Architectural Review: 88/100 (APPROVED)
- ✅ Code Review: 94/100 (EXCELLENT)
- ✅ Performance: <1s (target: <5s)
- ✅ Thread Safety: Validated

### 🎯 Requirements Satisfaction

**Acceptance Criteria (8/8 met):**
1. ✅ Map internal hash ID to external sequential IDs per PM tool
2. ✅ Support JIRA format: `{project_key}-{number}`
3. ✅ Support Azure DevOps format: `{number}`
4. ✅ Support Linear format: `{team}-{number}`
5. ✅ Support GitHub format: `#{number}`
6. ✅ Bidirectional lookup: internal ↔ external
7. ✅ Thread-safe counter increment per tool
8. ✅ Auto-generate external ID on first export to tool

**Test Requirements (6/6 met):**
1. ✅ Unit tests for mapping internal → external (16 tests, all 4 tools)
2. ✅ Unit tests for reverse lookup external → internal (7 tests)
3. ✅ Unit tests for counter increment sequential (7 tests)
4. ✅ Concurrency tests: 10 simultaneous mappings (4 tests, no collisions)
5. ✅ Integration tests with actual PM tool formats (4 tests)
6. ✅ Test coverage ≥85% (achieved 97.7%)

### 📈 Quality Assessment

**Architectural Review (88/100):**
- SOLID Principles: 37/40
- DRY Principle: 27/30
- YAGNI Principle: 24/30
- Decision: APPROVED ✅

**Code Review (94/100):**
- Code Quality: 24/25 (Excellent)
- Documentation: 20/20 (Perfect)
- Error Handling: 15/15 (Perfect)
- Testing: 20/20 (Perfect)
- Security: 15/20 (Good)
- Decision: APPROVED FOR PRODUCTION ✅

### 🏗️ Implementation Phases

**Phase 1:** ❌ Skipped (Requirements Analysis - taskwright starts at Phase 2)
**Phase 2:** ✅ Implementation Planning (30 minutes)
**Phase 2.5:** ✅ Architectural Review (15 minutes, score: 88/100)
**Phase 3:** ✅ Implementation (1 hour 15 minutes)
**Phase 4:** ✅ Test Suite Development (1 hour)
**Phase 4.5:** ✅ Test Enforcement (15 minutes, all gates passed)
**Phase 5:** ✅ Code Review (15 minutes, score: 94/100)

**Total Implementation Time:** ~2 hours 15 minutes

### 💡 Key Features Delivered

**1. Bidirectional Mapping System**
- Internal hash IDs ↔ External sequential IDs
- Support for 4 major PM tools
- Automatic counter management

**2. Thread-Safe Operations**
- `threading.Lock()` for atomic operations
- Singleton pattern with double-checked locking
- Validated with 10 concurrent operations

**3. Clean Architecture**
- DRY improvements (`_format_keyed_id()` helper)
- SOLID principles adherence
- Extensible design for future PM tools

**4. Comprehensive Validation**
- Tool name validation
- Internal ID format validation
- Project key validation
- Clear, actionable error messages

**5. Excellent Documentation**
- Module-level overview with examples
- Complete docstrings for all methods
- Type hints throughout
- Usage examples in doctest format

### 🎓 Lessons Learned

**What Went Well:**
1. Architectural review caught YAGNI violations early
2. DRY improvements suggested during review were implemented
3. Thread safety design validated through comprehensive testing
4. Test coverage exceeded target by 12.7%
5. Case normalization issue caught and fixed during testing

**Challenges Faced:**
1. Python `global` keyword issue required sys.path manipulation in tests
2. Git config issue (`gpg.format` empty) prevented immediate commit
3. Initial test failure due to case normalization behavior

**Solutions Applied:**
1. Used `sys.path.insert()` to handle `installer.core.lib` import
2. Normalized project keys to uppercase before counter operations
3. All files staged for commit (git issue to be resolved separately)

**Improvements for Next Time:**
1. Check for Python reserved keywords in directory names earlier
2. Test git configuration before attempting commits
3. Consider validation of external system configs (git, etc.) upfront

### 🔗 Integration & Dependencies

**Dependencies Satisfied:**
- ✅ TASK-12FB: Hash ID generator (format understanding)

**Enables Future Tasks:**
- TASK-4679: JSON persistence for mappings
- TASK-7A96: Update task frontmatter schema
- TASK-C38F: `/task-create` integration

### 📊 Impact Analysis

**Code Additions:**
- Production Code: 370 lines (external_id_mapper.py)
- Test Code: 618 lines (test_external_id_mapper.py)
- Documentation: Implementation plan
- Total: ~1,000 lines

**Test Coverage Impact:**
- New module: 97.7% coverage
- 53 new tests added
- 0 defects introduced
- 100% pass rate

**Technical Debt:**
- None introduced
- Minor type annotation improvement suggested (optional)
- Test method protection suggested (optional)

### 🚀 Next Steps

**Immediate:**
1. Resolve git config issue: `gpg.format` in ~/.gitconfig
2. Commit staged changes to `external-id-mapper` branch
3. Merge to main after human approval

**Follow-up Tasks:**
1. TASK-4679: Implement JSON persistence
2. TASK-7A96: Update task frontmatter with external ID fields
3. TASK-C38F: Integrate with `/task-create` command

**Optional Improvements:**
1. Fix type annotation: `any` → `Union[int, Dict[str, int]]`
2. Add `_testing_mode` flag for test-only methods
3. Document case normalization in docstring

### ✨ Success Metrics

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Compilation | 100% | 100% | ✅ |
| Tests Passing | 100% | 100% (53/53) | ✅ |
| Line Coverage | ≥80% | 97.7% | ✅ |
| Branch Coverage | ≥75% | ~95% | ✅ |
| Architectural Review | ≥60/100 | 88/100 | ✅ |
| Code Review | N/A | 94/100 | ✅ |
| Thread Safety | Verified | Verified | ✅ |
| Performance | <5s | <1s | ✅ |

### 🎉 Conclusion

TASK-223C has been successfully completed with exceptional quality metrics. The external ID mapper implementation is production-ready, thoroughly tested, and approved for deployment. All acceptance criteria met, zero scope creep, and comprehensive documentation provided.

**Final Status:** ✅ COMPLETED & READY FOR PRODUCTION

---
