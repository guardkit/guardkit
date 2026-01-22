---
task_id: TASK-FBSDK-018
saved_at: 2025-01-22T07:30:00Z
version: 1
complexity_score: 3
architectural_review_score: null
status: draft
---

# Implementation Plan: TASK-FBSDK-018

## Summary

Add `code_review` field to `task_work_results.json` output in `agent_invoker.py` to fix CoachValidator architectural review validation.

**Root cause**: `_write_task_work_results()` does not include `code_review.score` field that CoachValidator expects, causing all architectural review checks to fail (score defaults to 0, failing ≥60 threshold).

**Solution**: Extract architectural review score from `result_data` and add `code_review` field to results dictionary with score and optional SOLID/DRY/YAGNI subscores.

## Files to Modify

1. `guardkit/orchestrator/agent_invoker.py` (lines 2239-2256)
   - Add `code_review` field to results dictionary
   - Extract score from `result_data.get("architectural_review", {})`
   - Include optional subscores when available

2. `tests/unit/test_agent_invoker_task_work_results.py` (new file)
   - Unit tests verifying `code_review` field serialization
   - Test with score present
   - Test with score missing (defaults to 0)
   - Test with optional subscores

## Implementation Phases

### Phase 1: Modify agent_invoker.py (15 min)

**Location**: `guardkit/orchestrator/agent_invoker.py:2239-2256`

**Change**: Add `code_review` field after `quality_gates` field:

```python
results: Dict[str, Any] = {
    "task_id": task_id,
    "timestamp": datetime.now().isoformat(),
    "completed": completed,
    "phases": result_data.get("phases", {}),
    "quality_gates": {
        "tests_passing": tests_failed == 0 if tests_failed is not None else None,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "coverage": coverage,
        "coverage_met": coverage >= 80 if coverage is not None else None,
        "all_passed": quality_gates_passed,
    },
    "code_review": {
        "score": result_data.get("architectural_review", {}).get("score", 0),
        "solid_score": result_data.get("architectural_review", {}).get("solid_score"),
        "dry_score": result_data.get("architectural_review", {}).get("dry_score"),
        "yagni_score": result_data.get("architectural_review", {}).get("yagni_score"),
    },
    "plan_audit": {
        "violations": result_data.get("plan_audit", {}).get("violations", 0),
    },
    "files_modified": sorted(list(set(result_data.get("files_modified", [])))),
    "files_created": sorted(list(set(result_data.get("files_created", [])))),
    "summary": self._generate_summary(result_data),
}
```

**Rationale**:
- Default score to 0 when missing (matches CoachValidator's default behavior)
- Optional subscores can be None (not required for basic validation)
- Consistent field structure with existing patterns

### Phase 2: Add Unit Tests (20 min)

**File**: `tests/unit/test_agent_invoker_task_work_results.py`

**Test cases**:

1. `test_write_task_work_results_includes_code_review_with_score()`
   - Verify `code_review.score` written correctly
   - Input: `architectural_review.score = 75`
   - Expected: `code_review.score = 75` in JSON

2. `test_write_task_work_results_includes_code_review_without_score()`
   - Verify default score of 0 when missing
   - Input: No `architectural_review` field
   - Expected: `code_review.score = 0` in JSON

3. `test_write_task_work_results_includes_code_review_with_subscores()`
   - Verify optional subscores written when available
   - Input: All SOLID/DRY/YAGNI subscores
   - Expected: All subscores in JSON

4. `test_write_task_work_results_includes_code_review_with_partial_subscores()`
   - Verify None values for missing subscores
   - Input: Only `solid_score` present
   - Expected: `solid_score` value, others None

**Test pattern** (following existing test patterns):
```python
def test_write_task_work_results_includes_code_review_with_score(tmp_path):
    """Verify code_review field written with score."""
    # Setup mock result_data
    result_data = {
        "architectural_review": {
            "score": 75,
            "solid_score": 8,
            "dry_score": 9,
            "yagni_score": 8,
        },
        "tests_passed": 5,
        "tests_failed": 0,
        "coverage_lines": 85,
    }

    # Call _write_task_work_results()
    results_file = agent_invoker._write_task_work_results(
        task_id="TASK-TEST",
        result_data=result_data,
        documentation_level="minimal"
    )

    # Verify code_review field in JSON
    results = json.loads(results_file.read_text())
    assert "code_review" in results
    assert results["code_review"]["score"] == 75
    assert results["code_review"]["solid_score"] == 8
    assert results["code_review"]["dry_score"] == 9
    assert results["code_review"]["yagni_score"] == 8
```

## External Dependencies

None - uses existing Python stdlib (`json`, `datetime`)

## Estimated Metrics

- **Duration**: 35 minutes total
  - Phase 1: 15 minutes (modify agent_invoker.py)
  - Phase 2: 20 minutes (write unit tests)

- **Lines of Code**: ~50 LOC
  - Production: ~10 LOC (agent_invoker.py change)
  - Tests: ~40 LOC (4 test cases)

- **Files Modified**: 1
  - `guardkit/orchestrator/agent_invoker.py`

- **Files Created**: 1
  - `tests/unit/test_agent_invoker_task_work_results.py`

## Test Summary

**Coverage target**: 100% (simple field addition, easy to test)

**Test types**:
- Unit tests for field serialization
- Integration test via existing CoachValidator tests (already written)

**Testing strategy**:
- Verify field written correctly when score present
- Verify default value (0) when score missing
- Verify optional subscores handled correctly
- No mocking needed (direct JSON serialization)

## Risks

**Low Risk** (complexity: 3/10)

1. **Breaking change risk**: LOW
   - Additive change (new field, no removals)
   - CoachValidator already expects this field
   - Backward compatible (field was just missing)

2. **Test coverage risk**: NONE
   - Simple field addition with direct tests
   - Integration already covered by CoachValidator tests

3. **Performance risk**: NONE
   - No additional computation
   - Simple dictionary access

## Architecture Notes

**Pattern**: Dataclass-style dictionary construction (existing pattern in agent_invoker.py)

**Field extraction**: Uses `.get()` with defaults for safety:
```python
result_data.get("architectural_review", {}).get("score", 0)
```

**Consistency**: Matches existing `quality_gates` and `plan_audit` field structures

**Validation**: No additional validation needed (CoachValidator handles threshold checks)
