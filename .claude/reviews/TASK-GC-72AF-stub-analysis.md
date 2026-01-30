# Stub Implementation Analysis: TASK-GC-72AF

**Date**: 2026-01-29
**Task**: Graphiti Core Migration
**Purpose**: Understand why the original `/task-work` produced stub implementations instead of working code

---

## Executive Summary

The original `/task-work` execution produced a 431-line file that **looked complete** but contained **non-functional stub implementations**. The file had:
- ✅ Proper class structure and documentation
- ✅ Correct method signatures
- ✅ Type hints and docstrings
- ❌ **No actual graphiti-core library integration**
- ❌ **Methods that return empty/None without doing anything**

This is a critical pattern that needs to be understood and prevented.

---

## What Was Written (Original Stub)

### The Stub Pattern

The original implementation created methods with this pattern:

```python
async def _execute_search(
    self,
    query: str,
    group_ids: Optional[List[str]] = None,
    num_results: int = 10
) -> List[Dict[str, Any]]:
    """Execute the actual search against Graphiti.
    [... good docstring ...]
    """
    # In production, this would call Graphiti's search API
    return []  # <-- STUB: Returns empty, does nothing
```

```python
async def _create_episode(
    self,
    name: str,
    episode_body: str,
    group_id: str
) -> Optional[str]:
    """Create an episode in Graphiti.
    [... good docstring ...]
    """
    # In production, this would call Graphiti's episode API
    return None  # <-- STUB: Returns None, does nothing
```

### What Should Have Been Written

The working implementation (after manual completion):

```python
async def _execute_search(
    self,
    query: str,
    group_ids: Optional[List[str]] = None,
    num_results: int = 10
) -> List[Dict[str, Any]]:
    """Execute the actual search against Graphiti."""
    if not self._graphiti:
        return []

    try:
        results = await self._graphiti.search(
            query,
            group_ids=group_ids,
            num_results=num_results
        )
        # Convert Edge objects to dictionaries
        return [
            {
                "uuid": edge.uuid,
                "fact": edge.fact,
                "name": getattr(edge, "name", None),
                "created_at": str(edge.created_at) if edge.created_at else None,
                "score": getattr(edge, "_score", 0.0),
            }
            for edge in results
        ]
    except Exception as e:
        logger.warning(f"Search request failed: {e}")
        return []
```

---

## Root Cause Analysis

### Probable Cause 1: Missing Concrete API Examples

**Observation**: The task description said "migrate from zepai/graphiti Docker REST API to graphiti-core Python library" but did NOT include:
- graphiti-core API documentation
- Example usage code
- Import statements needed
- Object types returned (e.g., `Edge` objects)

**Result**: The AI knew it needed to wrap graphiti-core but didn't know HOW to call it.

**Evidence**: The stub comments explicitly state:
```python
# In production, this would call Graphiti's search API
# In production, this would call Graphiti's episode API
```

This indicates the AI knew what to do conceptually but lacked the concrete implementation details.

### Probable Cause 2: Test-First Pattern Without Mocking Guidance

**Observation**: The task may have led to tests being written before implementation. When tests mock the internal methods (`_execute_search`, `_create_episode`), the stubs technically "pass" all tests.

**Evidence**: Looking at the test file, all tests mock the internal methods:
```python
mock_graphiti = MagicMock()
mock_graphiti.search = AsyncMock(return_value=[mock_edge])
client._graphiti = mock_graphiti
```

The tests never actually called the real graphiti-core library, so stubs passed.

### Probable Cause 3: "Structure First" Cognitive Pattern

**Observation**: AI models often follow a pattern of:
1. Write structure/scaffolding
2. Fill in implementation details

If context is limited or conversation is long, the second step may not happen.

**Evidence**: The original file was 431 lines with perfect structure, docstrings, and type hints - but missing 50 lines of actual implementation.

### Probable Cause 4: No Integration Test Requirement

**Observation**: The acceptance criteria didn't require running against a real Neo4j instance. Unit tests with mocks passed.

**Evidence**: Integration tests in the test file are marked `@pytest.mark.integration` and `@pytest.mark.skip`. They were never run during the original task-work.

### Probable Cause 5: "Graceful Degradation" Masking Failure

**Observation**: The design pattern of "return empty on failure" made stubs indistinguishable from working code in tests.

**Evidence**: Both stub and working code return `[]` on failure. Without calling the real API, there's no way to distinguish them.

---

## What This Pattern Looks Like

### Detection Signals

1. **Comment markers**: `# In production, this would...`
2. **Empty returns**: Methods that `return []` or `return None` without logic
3. **Missing imports**: No `from graphiti_core import Graphiti`
4. **No library-specific code**: No calls to external library methods
5. **Test mocking at wrong level**: Tests mock the method that should be implemented

### Why It's Hard to Detect

1. **Tests pass**: All unit tests pass because they mock the stubs
2. **Type checks pass**: Return types are correct (`List[Dict]`, `Optional[str]`)
3. **Code looks complete**: Good structure, docstrings, comments
4. **Graceful degradation**: Empty returns are "valid" behavior

---

## Prevention Recommendations

### 1. Explicit Implementation Requirement in Task Description

**Bad**:
> Migrate from REST API to graphiti-core library

**Good**:
> Migrate from REST API to graphiti-core library.
> - Must use `from graphiti_core import Graphiti`
> - Must call `Graphiti.search()` and `Graphiti.add_episode()`
> - Provide working code, NOT stubs or placeholders
> - No `# TODO` or `# In production, this would...` comments

### 2. Include Library Documentation in Context

When migrating to a new library, include:
- Import statements
- Example API usage
- Return types from the library
- Any initialization requirements

### 3. Integration Test Requirement

Add to acceptance criteria:
```yaml
acceptance_criteria:
  - "Unit tests pass"
  - "Integration test with real Neo4j must be run manually and verified"
  - "No stub implementations (methods must contain library calls)"
```

### 4. Stub Detection Quality Gate

Add to Phase 4.5 (Test Enforcement):

```python
def detect_stubs(file_content: str) -> List[str]:
    """Detect potential stub implementations."""
    stubs = []

    # Pattern 1: Comments indicating production TODO
    if re.search(r'#.*In production.*would', file_content):
        stubs.append("Found '# In production, this would...' comment")

    # Pattern 2: Methods that only return empty/None
    for match in re.finditer(r'async def (\w+)\(.*?\):\s*""".*?"""\s*return (\[\]|None)', file_content, re.DOTALL):
        stubs.append(f"Method {match.group(1)} returns {match.group(2)} without logic")

    # Pattern 3: Missing expected imports
    if 'graphiti' in file_content.lower() and 'from graphiti_core import' not in file_content:
        stubs.append("File mentions graphiti but doesn't import graphiti_core")

    return stubs
```

### 5. Library Usage Verification

Add a check that verifies the target library is actually called:

```python
def verify_library_usage(file_content: str, required_imports: List[str], required_calls: List[str]) -> bool:
    """Verify a file actually uses the required library."""
    for imp in required_imports:
        if imp not in file_content:
            return False
    for call in required_calls:
        if call not in file_content:
            return False
    return True
```

### 6. Acceptance Criteria Template

For library migration tasks:

```yaml
acceptance_criteria:
  - "All existing functionality preserved"
  - "Uses {library_name} import: `from {library} import {class}`"
  - "Calls {library_name} methods: {method1}, {method2}"
  - "No placeholder/stub implementations"
  - "No TODO comments in production code"
  - "Integration test passes with real {service}"
```

---

## Summary

| Aspect | What Happened | What Should Happen |
|--------|---------------|-------------------|
| Structure | ✅ Perfect | ✅ Keep |
| Documentation | ✅ Perfect | ✅ Keep |
| Type hints | ✅ Perfect | ✅ Keep |
| Library imports | ❌ Missing | Must include |
| Library calls | ❌ Stub returns | Must call library |
| Integration test | ❌ Skipped | Must verify manually |
| Stub detection | ❌ None | Add to quality gate |

---

## Action Items for GuardKit

1. **Add stub detection to Phase 4.5** - Flag files with empty-return methods
2. **Update task-create template** - Include "no stubs" in acceptance criteria
3. **Add library migration checklist** - Required imports/calls specified
4. **Integration test checkpoint** - Human must verify integration before IN_REVIEW

---

## Conclusion

The stub pattern occurred because:
1. Missing concrete API examples in task context
2. Unit tests passed despite stubs (due to mocking)
3. Graceful degradation made stubs "valid" behavior
4. No integration test requirement

Prevention requires:
1. Explicit "no stubs" requirements
2. Library documentation in context
3. Integration test checkpoints
4. Automated stub detection

**This is a systemic issue that will recur unless these preventions are implemented.**
