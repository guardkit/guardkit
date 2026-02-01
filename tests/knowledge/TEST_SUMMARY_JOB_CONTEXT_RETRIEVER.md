# Test Summary: JobContextRetriever (TDD RED Phase)

## Overview

Comprehensive test suite for the JobContextRetriever class following Test-Driven Development (TDD) RED phase.

**Status**: RED (All tests failing - implementation not yet created)
**Test Count**: 40 tests
**Coverage Target**: >=85%
**Location**: `tests/knowledge/test_job_context_retriever.py`

## Test Breakdown by Category

### 1. RetrievedContext Dataclass Tests (8 tests)
Tests the `RetrievedContext` dataclass structure and methods:
- ✗ `test_dataclass_exists` - Verify dataclass exists
- ✗ `test_dataclass_has_required_fields` - Check all required fields present
- ✗ `test_dataclass_can_be_instantiated` - Create instance with fields
- ✗ `test_dataclass_context_categories_are_lists` - All categories are list types
- ✗ `test_dataclass_has_to_prompt_method` - to_prompt() method exists
- ✗ `test_to_prompt_returns_string` - to_prompt() returns formatted string
- ✗ `test_to_prompt_includes_budget_info` - Budget info in prompt output
- ✗ `test_to_prompt_includes_context_categories` - Categories in prompt output

### 2. JobContextRetriever Class Tests (5 tests)
Tests the main retriever class structure:
- ✗ `test_class_exists` - JobContextRetriever class exists
- ✗ `test_class_can_be_instantiated` - Create instance with graphiti client
- ✗ `test_class_has_retrieve_method` - retrieve() method exists
- ✗ `test_retrieve_is_async` - retrieve() is async method
- ✗ `test_class_stores_graphiti_client` - Graphiti client stored correctly

### 3. Basic Retrieve Method Tests (5 tests)
Tests core retrieve() functionality:
- ✗ `test_retrieve_returns_retrieved_context` - Returns RetrievedContext instance
- ✗ `test_retrieve_uses_task_analyzer` - TaskAnalyzer integration
- ✗ `test_retrieve_uses_budget_calculator` - DynamicBudgetCalculator integration
- ✗ `test_retrieve_sets_task_id_in_result` - Task ID propagated to result
- ✗ `test_retrieve_sets_budget_total` - Budget total set from calculator

### 4. Context Category Query Tests (6 tests)
Tests Graphiti queries for each context category:
- ✗ `test_queries_feature_context` - Queries feature_specs group
- ✗ `test_queries_similar_outcomes` - Queries task_outcomes group
- ✗ `test_queries_relevant_patterns` - Queries patterns_{stack} group
- ✗ `test_queries_architecture_context` - Queries project_architecture group
- ✗ `test_queries_warnings` - Queries failure_patterns group
- ✗ `test_queries_domain_knowledge` - Queries domain_knowledge group

### 5. AutoBuild Context Tests (4 tests)
Tests AutoBuild-specific context loading:
- ✗ `test_loads_autobuild_context_when_applicable` - AutoBuild context loaded when is_autobuild=True
- ✗ `test_queries_role_constraints_for_autobuild` - Queries role_constraints group
- ✗ `test_queries_turn_states_for_autobuild` - Queries turn_states group
- ✗ `test_autobuild_context_empty_when_not_applicable` - Empty when is_autobuild=False

### 6. Relevance Filtering Tests (3 tests)
Tests relevance threshold filtering:
- ✗ `test_filters_by_relevance_threshold_first_of_type` - 0.5 threshold for first-of-type
- ✗ `test_filters_by_relevance_threshold_standard` - 0.6 threshold for standard tasks
- ✗ `test_handles_results_without_score` - Results without score kept

### 7. Budget Trimming Tests (3 tests)
Tests budget allocation and trimming:
- ✗ `test_trims_results_to_fit_budget` - Results trimmed when exceeding budget
- ✗ `test_respects_category_allocations` - Each category respects allocation
- ✗ `test_tracks_budget_used` - Budget used calculated correctly

### 8. Empty Results Tests (2 tests)
Tests handling of empty Graphiti results:
- ✗ `test_handles_empty_graphiti_results` - Empty lists for all categories
- ✗ `test_handles_none_graphiti_results` - None results handled gracefully

### 9. Token Estimation Tests (2 tests)
Tests token estimation for budget tracking:
- ✗ `test_estimates_tokens_for_results` - Token estimation used for budget
- ✗ `test_token_estimation_accounts_for_all_categories` - All categories counted

### 10. Integration Tests (2 tests)
Tests complete end-to-end flows:
- ✗ `test_end_to_end_retrieval` - Complete standard retrieval flow
- ✗ `test_autobuild_end_to_end` - Complete AutoBuild retrieval flow

## Expected Failure Reason

All tests fail with:
```
ModuleNotFoundError: No module named 'guardkit.knowledge.job_context_retriever'
```

This is **expected** for TDD RED phase. The implementation file doesn't exist yet.

## Acceptance Criteria Coverage

The test suite covers all acceptance criteria from TASK-GR6-003:

1. ✓ **`retrieve(task, phase)` returns `RetrievedContext`**
   - Tested in: TestRetrieveBasics::test_retrieve_returns_retrieved_context
   - Tested in: TestIntegration::test_end_to_end_retrieval

2. ✓ **Uses TaskAnalyzer and DynamicBudgetCalculator**
   - Tested in: TestRetrieveBasics::test_retrieve_uses_task_analyzer
   - Tested in: TestRetrieveBasics::test_retrieve_uses_budget_calculator

3. ✓ **Queries Graphiti for each context category within budget**
   - Tested in: All TestContextCategoryQueries tests (6 tests)
   - Tested in: TestBudgetTrimming::test_respects_category_allocations

4. ✓ **Filters by relevance threshold (0.5-0.6)**
   - Tested in: TestRelevanceFiltering::test_filters_by_relevance_threshold_first_of_type
   - Tested in: TestRelevanceFiltering::test_filters_by_relevance_threshold_standard

5. ✓ **Trims results to fit budget allocation**
   - Tested in: TestBudgetTrimming::test_trims_results_to_fit_budget
   - Tested in: TestBudgetTrimming::test_respects_category_allocations

6. ✓ **Includes AutoBuild context when applicable**
   - Tested in: All TestAutoBuildContext tests (4 tests)
   - Tested in: TestIntegration::test_autobuild_end_to_end

## Context Categories Tested

The tests verify all 10 context categories:

**Standard Categories** (6):
- feature_context (feature_specs group)
- similar_outcomes (task_outcomes group)
- relevant_patterns (patterns_{stack} group)
- architecture_context (project_architecture group)
- warnings (failure_patterns group)
- domain_knowledge (domain_knowledge group)

**AutoBuild Categories** (4):
- role_constraints (AutoBuild)
- quality_gate_configs (AutoBuild)
- turn_states (AutoBuild)
- implementation_modes (AutoBuild)

## Mock Strategy

Tests use comprehensive mocking:

1. **GraphitiClient**: AsyncMock for search() method
2. **TaskAnalyzer**: Patched with mock characteristics
3. **DynamicBudgetCalculator**: Patched with mock budget
4. **Search Results**: Varied score values for filtering tests

## Key Test Patterns

1. **Async Testing**: All retrieve() tests use `@pytest.mark.asyncio`
2. **Mock Patching**: `unittest.mock.patch` for dependency injection
3. **Edge Cases**: Empty results, None results, missing scores
4. **Integration**: End-to-end flows with realistic data

## Next Steps (TDD GREEN Phase)

To make tests pass, implement:

1. **guardkit/knowledge/job_context_retriever.py**:
   - RetrievedContext dataclass
   - JobContextRetriever class
   - retrieve() async method
   - to_prompt() method

2. **Key Implementation Details**:
   - Integrate with TaskAnalyzer
   - Integrate with DynamicBudgetCalculator
   - Query Graphiti for each category
   - Filter by relevance threshold (0.5 for first-of-type, 0.6 otherwise)
   - Trim results to budget allocation
   - Track budget used with token estimation
   - Format output with to_prompt()

## References

- **Task**: TASK-GR6-003 - Implement JobContextRetriever
- **Feature**: FEAT-GR-006 - Job-Specific Context Retrieval
- **Dependencies**:
  - guardkit/knowledge/task_analyzer.py (implemented)
  - guardkit/knowledge/budget_calculator.py (implemented)
  - guardkit/knowledge/graphiti_client.py (implemented)

---

**TDD Phase**: RED (Tests written, implementation pending)
**Test Count**: 40 tests
**Coverage Target**: >=85%
**Status**: All tests failing as expected (module doesn't exist)
