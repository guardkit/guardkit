# TASK-049: Implementation Plan
## External ID Mapper for PM Tools

**Created:** 2025-11-10T14:20:00Z
**Status:** In Progress
**Complexity:** 6/10 (Medium)

---

## 1. Overview

Implement a bidirectional mapping system between GuardKit's internal hash-based IDs and external sequential IDs used by PM tools (JIRA, Azure DevOps, Linear, GitHub).

### Goals
- Enable seamless integration with external PM tools
- Maintain collision-free internal hash IDs
- Support 4 major PM tool ID formats
- Thread-safe counter management
- Persistent storage via JSON (TASK-050 dependency)

---

## 2. Architecture Design

### 2.1 Module Structure
```
installer/global/lib/
├── external_id_mapper.py       (NEW - core mapper)
└── id_generator.py            (EXISTING - hash ID generation)

tests/
└── test_external_id_mapper.py  (NEW - comprehensive tests)
```

### 2.2 Data Structures

**Mapping Storage:**
```python
{
  "TASK-E01-b2c4": {
    "jira": "PROJ-456",
    "azure_devops": "1234",
    "linear": "TEAM-789",
    "github": "234"
  }
}
```

**Counter Storage:**
```python
{
  "jira": {"PROJ": 457, "TEST": 12},
  "azure_devops": 1235,
  "linear": {"TEAM": 789, "DESIGN": 45},
  "github": 234
}
```

### 2.3 Thread Safety
Use `threading.Lock()` for atomic counter increments across concurrent operations.

---

## 3. Implementation Steps

### Phase 3.1: Core Mapper Class (30 min)
**File:** `installer/global/lib/external_id_mapper.py`

**Components:**
1. `ExternalIDMapper` class with in-memory storage
2. Thread lock for counter safety
3. Data structures initialization

**Functions:**
- `__init__(self)` - Initialize storage and locks
- `_init_tool_counter(self, tool: str, key: str = None)` - Setup counter

### Phase 3.2: Mapping Functions (45 min)

**Create Mapping:**
```python
def map_to_external(
    self,
    internal_id: str,
    tool: str,
    project_key: str = "PROJ"
) -> str:
    """
    Map internal hash ID to external sequential ID.

    Args:
        internal_id: TASK-XXX-hash format
        tool: jira|azure_devops|linear|github
        project_key: Project/team identifier

    Returns:
        External ID string (e.g., "PROJ-456")
    """
```

**Reverse Lookup:**
```python
def get_internal_id(
    self,
    external_id: str,
    tool: str
) -> Optional[str]:
    """
    Get internal ID from external ID.

    Args:
        external_id: External format (e.g., "PROJ-456")
        tool: PM tool name

    Returns:
        Internal hash ID or None
    """
```

**Counter Management:**
```python
def increment_counter(
    self,
    tool: str,
    key: str = None
) -> int:
    """
    Thread-safe counter increment.

    Args:
        tool: PM tool name
        key: Project/team key (for JIRA/Linear)

    Returns:
        Next sequential number
    """
```

**Get All Mappings:**
```python
def get_all_mappings(
    self,
    internal_id: str
) -> Dict[str, str]:
    """
    Get all external IDs for internal ID.

    Returns:
        {"jira": "PROJ-456", "github": "234", ...}
    """
```

### Phase 3.3: Format Handlers (30 min)

**Shared Helper (DRY improvement):**
```python
def _format_keyed_id(self, key: str, number: int) -> str:
    """Shared format handler for JIRA/Linear."""
    return f"{key.upper()}-{number}"
```

**JIRA Format:**
```python
def _format_jira_id(self, project_key: str, number: int) -> str:
    return self._format_keyed_id(project_key, number)
```

**Azure DevOps Format:**
```python
def _format_azure_id(self, number: int) -> str:
    return str(number)
```

**Linear Format:**
```python
def _format_linear_id(self, team_key: str, number: int) -> str:
    return self._format_keyed_id(team_key, number)
```

**GitHub Format:**
```python
def _format_github_id(self, number: int) -> str:
    return str(number)  # '#' prefix handled at display layer
```

### Phase 3.4: Validation & Error Handling (20 min)

**Input Validation:**
- Tool name in allowed list
- Valid internal ID format (regex)
- Non-empty project/team keys
- Positive counter values

**Error Cases:**
- Invalid tool name → `ValueError`
- Invalid ID format → `ValueError`
- Mapping not found → Return `None`
- Concurrent access → Lock ensures safety

---

## 4. Testing Strategy

### Phase 4.1: Unit Tests (60 min)
**File:** `tests/test_external_id_mapper.py`

**Test Categories:**

**Mapping Creation (8 tests):**
- Test JIRA format: `PROJ-1`, `PROJ-2`, etc.
- Test Azure DevOps format: `1`, `2`, etc.
- Test Linear format: `TEAM-1`, `TEAM-2`, etc.
- Test GitHub format: `1`, `2`, etc.
- Test auto-increment behavior
- Test multiple mappings per internal ID
- Test project key variations
- Test invalid tool names

**Reverse Lookup (4 tests):**
- Test successful lookup for each tool
- Test non-existent mapping
- Test case sensitivity
- Test format validation

**Counter Management (6 tests):**
- Test sequential increment
- Test per-project counters (JIRA)
- Test per-team counters (Linear)
- Test global counters (Azure DevOps, GitHub)
- Test counter initialization
- Test counter persistence

**Thread Safety (3 tests):**
- Test 10 simultaneous mappings
- Verify no counter collisions
- Verify all mappings created

**Integration Tests (4 tests):**
- Test round-trip: internal → external → internal
- Test multi-tool mapping for same internal ID
- Test format compliance with PM tool specs
- Test edge cases (empty keys, special chars)

### Phase 4.2: Test Execution Requirements
- Coverage target: ≥85%
- All tests must pass
- Concurrency test must complete <5s
- No race conditions detected

---

## 5. Quality Gates

### Phase 5.1: Architectural Review
- SOLID compliance check
- DRY principle verification
- YAGNI assessment
- Thread safety validation

### Phase 5.2: Code Review
- Function documentation complete
- Type hints present
- Error handling comprehensive
- No code duplication

### Phase 5.3: Test Quality
- Edge cases covered
- Concurrency tested
- Integration validated
- Coverage ≥85%

---

## 6. Integration Points

### Current Dependencies
- `installer/global/lib/id_generator.py` - Hash ID format understanding

### Future Dependencies (TASK-050)
- JSON persistence layer for mappings
- File-based counter storage
- Atomic file operations

### Integration Tasks
- TASK-048: `/task-create` to auto-generate external IDs
- TASK-051: Add external ID fields to task frontmatter
- TASK-050: Persist mappings to JSON files

---

## 7. Implementation Timeline

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| 3.1 | Core mapper class | 30 min | Pending |
| 3.2 | Mapping functions | 45 min | Pending |
| 3.3 | Format handlers | 30 min | Pending |
| 3.4 | Validation | 20 min | Pending |
| 4.1 | Unit tests | 60 min | Pending |
| 4.2 | Test execution | 10 min | Pending |
| 5.1 | Architectural review | 15 min | Pending |
| 5.2 | Code review | 15 min | Pending |

**Total Estimated Time:** 3 hours 45 minutes

---

## 8. Success Criteria

- [ ] All 4 PM tool formats supported
- [ ] Bidirectional mapping works correctly
- [ ] Thread-safe counter increments
- [ ] Test coverage ≥85%
- [ ] All tests pass
- [ ] No race conditions in concurrency tests
- [ ] Code passes architectural review
- [ ] Documentation complete

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Counter collision in concurrent ops | High | Use threading.Lock() |
| Invalid external ID format | Medium | Comprehensive validation |
| Missing TASK-046 dependency | High | Check id_generator.py exists |
| Counter persistence (TASK-050) | Low | In-memory for now, plan for future |

---

## 10. Notes

- This implementation provides in-memory mapping only
- TASK-050 will add JSON persistence
- Counter state will reset on process restart until TASK-050 complete
- Format handlers are extensible for future PM tools
- Thread safety critical for concurrent `/task-create` operations

---

## 11. Architectural Review Results

**Review Date:** 2025-11-10T14:25:00Z
**Score:** 88/100 (GOOD - Minor Improvements Recommended)
**Decision:** APPROVED ✅

**Changes Made:**
1. Removed `epic` field from mapping structure (YAGNI violation)
2. Removed `created` timestamp field (YAGNI violation)
3. Added `_format_keyed_id()` helper to reduce duplication (DRY improvement)

**Deferred Considerations:**
- `get_all_mappings()` kept as specified in acceptance criteria
- Counter Manager extraction (Priority 3, future enhancement)
- Lock Provider abstraction (Priority 3, distributed systems only)

---

**Plan Status:** Approved - Ready for Phase 3 Implementation
