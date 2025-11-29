---
task_id: TASK-51B2-A
title: Fix Unit Tests After AI-Native Template Creation Refactor
created: 2025-01-12
priority: high
type: testing
status: in_review
updated: 2025-01-12T15:30:00Z
reviewed: 2025-01-12T16:00:00Z
complexity: 3/10
estimated_effort: 1-2 hours
actual_effort: 1.3 hours
related_tasks:
  - TASK-51B2
labels:
  - testing
  - cleanup
  - task-51b2-followup
test_results:
  total: 18
  passed: 18
  failed: 0
  coverage_line: 100%
  coverage_branch: 100%
---

# TASK-51B2-A: Fix Unit Tests After AI-Native Template Creation Refactor

**Related**: TASK-51B2 (Revert to AI-Native Template Creation)
**Priority**: High
**Type**: Testing/Cleanup
**Complexity**: 3/10 (Low - straightforward test updates)
**Estimated Effort**: 1-2 hours

## Problem Statement

After TASK-51B2 removed detector code and Q&A sessions, unit tests in `test_template_create_orchestrator.py` are failing because they reference deprecated functionality:
- `skip_qa` config field (removed)
- `config_file` config field (removed)
- `_phase1_qa_session()` method (removed)
- Old Q&A workflow tests

**Current Test Status**:
- ❌ `test_orchestration_config_defaults` - Fails on `assert config.skip_qa`
- ❌ `test_orchestration_config_custom_values` - Fails on `skip_qa=True`
- ❌ `test_phase1_qa_session_success` - Method removed
- ❌ `test_phase1_qa_session_cancelled` - Method removed
- ❌ `test_phase1_qa_session_with_skip_qa` - Method removed

## Objectives

Update unit tests to match the AI-native workflow implemented in TASK-51B2, ensuring 100% pass rate.

## Tasks

### Task 1: Update Config Tests (10 minutes)

**File**: `tests/unit/test_template_create_orchestrator.py`

**Changes needed**:

1. **Line ~136**: Remove `skip_qa` assertion
   ```python
   # Before
   assert config.skip_qa is False

   # After
   # skip_qa removed in TASK-51B2 (AI-native workflow)
   ```

2. **Line ~149**: Remove `skip_qa` parameter
   ```python
   # Before
   config = OrchestrationConfig(
       skip_qa=True,
       # ...
   )

   # After
   config = OrchestrationConfig(
       # skip_qa removed in TASK-51B2
       # ...
   )
   ```

3. **Line ~159**: Remove `skip_qa` assertion
   ```python
   # Before
   assert config.skip_qa is True

   # After
   # skip_qa removed in TASK-51B2
   ```

### Task 2: Comment Out Old Q&A Tests (5 minutes)

**Tests to disable** (reference old Q&A workflow):
- `test_phase1_qa_session_success` (~line 187)
- `test_phase1_qa_session_cancelled` (~line 202)
- `test_phase1_qa_session_with_skip_qa` (~line 220)

**Action**: Comment out entire test functions with explanatory note:
```python
# TASK-51B2: Removed Phase 1 Q&A tests (AI-native workflow)
# The _phase1_qa_session() method was replaced with _phase1_ai_analysis()
# which receives codebase_path directly and AI infers all metadata.
# No Q&A sessions, no detector code - just AI analysis.
#
# def test_phase1_qa_session_success(mock_qa_class, mock_qa_answers):
#     """Test successful Q&A session execution"""
#     ...
```

### Task 3: Add Tests for New AI-Native Phase 1 (30 minutes)

**New test 1**: `test_phase1_ai_analysis_success`
```python
@patch('installer.global.commands.lib.template_create_orchestrator.CodebaseAnalyzer')
def test_phase1_ai_analysis_success(mock_analyzer_class):
    """Test AI-native Phase 1 analysis success (TASK-51B2)"""
    # Setup
    mock_analyzer = Mock()
    mock_analysis = Mock()
    mock_analysis.overall_confidence.percentage = 95
    mock_analyzer.analyze_codebase.return_value = mock_analysis
    mock_analyzer_class.return_value = mock_analyzer

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)
    codebase_path = Path("/test/codebase")

    # Execute
    result = orchestrator._phase1_ai_analysis(codebase_path)

    # Assert
    assert result is not None
    assert result == mock_analysis
    mock_analyzer.analyze_codebase.assert_called_once_with(
        codebase_path=codebase_path,
        template_context=None,  # AI-native: no context, AI infers everything
        save_results=False
    )
```

**New test 2**: `test_phase1_ai_analysis_path_not_exists`
```python
def test_phase1_ai_analysis_path_not_exists():
    """Test Phase 1 handles non-existent codebase path"""
    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)
    bad_path = Path("/nonexistent/path")

    result = orchestrator._phase1_ai_analysis(bad_path)

    assert result is None
```

**New test 3**: `test_phase1_ai_analysis_metadata_inference`
```python
@patch('installer.global.commands.lib.template_create_orchestrator.CodebaseAnalyzer')
def test_phase1_ai_analysis_metadata_inference(mock_analyzer_class):
    """Test AI infers metadata when template_context is None (TASK-51B2)"""
    # Setup
    mock_analyzer = Mock()
    mock_analysis = Mock()
    mock_analysis.metadata.template_name = "fastapi-python"
    mock_analysis.metadata.primary_language = "Python"
    mock_analysis.metadata.framework = "FastAPI"
    mock_analysis.overall_confidence.percentage = 92
    mock_analyzer.analyze_codebase.return_value = mock_analysis
    mock_analyzer_class.return_value = mock_analyzer

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)
    codebase_path = Path("/test/fastapi-project")

    # Execute
    result = orchestrator._phase1_ai_analysis(codebase_path)

    # Assert - AI inferred metadata
    assert result.metadata.template_name == "fastapi-python"
    assert result.metadata.primary_language == "Python"
    assert result.metadata.framework == "FastAPI"

    # Assert - no template_context was provided (AI-native)
    call_args = mock_analyzer.analyze_codebase.call_args
    assert call_args.kwargs['template_context'] is None
```

### Task 4: Run Integration Tests (10 minutes)

**File**: `tests/integration/test_ai_native_template_creation.py`

**Execute**:
```bash
pytest tests/integration/test_ai_native_template_creation.py -v --tb=short
```

**Expected**:
- ✅ `test_react_typescript_project_inference` - React project detected
- ✅ `test_fastapi_python_project_inference` - FastAPI project detected
- ✅ `test_nextjs_fullstack_project_inference` - Next.js project detected
- ✅ `test_no_interactive_prompts` - No input() calls
- ✅ `test_ci_cd_compatibility` - Works in CI/CD env

**Note**: These require AI agent invocation, may take 5-10 minutes total.

### Task 5: Run Full Unit Test Suite (5 minutes)

**Execute**:
```bash
pytest tests/unit/ -v --ignore=tests/unit/test_smart_defaults_detector.py
```

**Expected**: 100% pass rate (excluding deleted detector tests)

**If failures remain**: Document each failure, identify root cause, fix systematically.

## Acceptance Criteria

- [ ] All unit tests pass (excluding deleted detector tests)
- [ ] No references to `skip_qa` remain in test files
- [ ] No references to `config_file` remain in test files
- [ ] No references to `_phase1_qa_session()` remain (except in commented code)
- [ ] 3 new tests added for `_phase1_ai_analysis()`
- [ ] Integration tests execute successfully (5/5 passing)
- [ ] Test coverage maintained at ≥80% for orchestrator module
- [ ] Test execution time < 5 minutes (unit), < 15 minutes (integration)

## Testing Checklist

### Quick Fix Verification
```bash
# 1. Update config tests (Task 1)
# Edit tests/unit/test_template_create_orchestrator.py

# 2. Run config tests only
pytest tests/unit/test_template_create_orchestrator.py::test_orchestration_config_defaults -v
pytest tests/unit/test_template_create_orchestrator.py::test_orchestration_config_custom_values -v

# Expected: PASSED (2/2)
```

### Q&A Tests Verification
```bash
# 3. Comment out Q&A tests (Task 2)
# Edit tests/unit/test_template_create_orchestrator.py

# 4. Run orchestrator tests
pytest tests/unit/test_template_create_orchestrator.py -v

# Expected: Should not see test_phase1_qa_session_* tests
```

### New Tests Verification
```bash
# 5. Add new AI-native tests (Task 3)
# Edit tests/unit/test_template_create_orchestrator.py

# 6. Run new tests
pytest tests/unit/test_template_create_orchestrator.py::test_phase1_ai_analysis_success -v
pytest tests/unit/test_template_create_orchestrator.py::test_phase1_ai_analysis_path_not_exists -v
pytest tests/unit/test_template_create_orchestrator.py::test_phase1_ai_analysis_metadata_inference -v

# Expected: PASSED (3/3)
```

### Integration Tests Verification
```bash
# 7. Run integration tests (Task 4)
pytest tests/integration/test_ai_native_template_creation.py -v

# Expected: PASSED (5/5), ~5-10 minutes
```

### Full Suite Verification
```bash
# 8. Run complete unit test suite (Task 5)
pytest tests/unit/ -v --ignore=tests/unit/test_smart_defaults_detector.py

# Expected: 100% pass rate
```

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Unit test pass rate | 100% | All tests excluding deleted detector tests |
| Integration test pass rate | 100% | 5/5 tests passing |
| Test coverage | ≥80% | Orchestrator module coverage |
| Unit test execution time | <5 min | pytest duration |
| Integration test execution time | <15 min | pytest duration |

## Notes

### Integration Test Requirements
- Integration tests require real AI agent invocation (`architectural-reviewer`)
- Tests may need network access for agent communication
- Consider adding `@pytest.mark.integration` decorator:
  ```python
  @pytest.mark.integration
  def test_react_typescript_project_inference(...):
      ...
  ```
- Can use `pytest -m "not integration"` to skip in CI

### Optional: Add pytest.ini Configuration
```ini
[pytest]
markers =
    integration: marks tests as integration tests (deselect with '-m "not integration"')
```

### Test Isolation
- Integration tests use `tmp_path` fixture for isolation
- Each test creates its own sample project
- No state sharing between tests
- Cleanup handled by pytest automatically

## Related Files

**Tests to Update**:
- `tests/unit/test_template_create_orchestrator.py` (primary - 200+ lines)
- `tests/integration/test_ai_native_template_creation.py` (verify - already created)

**Reference Implementation**:
- `installer/global/commands/lib/template_create_orchestrator.py` (AI-native workflow)
- `installer/global/lib/codebase_analyzer/prompt_builder.py` (metadata inference)
- `installer/global/lib/codebase_analyzer/ai_analyzer.py` (analyzer interface)

## Risk Assessment

**Low Risk** - Test updates only, no production code changes:
- Changes confined to test files
- Straightforward refactoring (commenting out old tests, adding new tests)
- Integration tests already written and ready to run
- No impact on production behavior

**Mitigation**:
- Test changes in isolation (one test at a time)
- Verify each change with `pytest -v`
- Keep commented code for reference (don't delete)
- Document any unexpected failures

## Estimated Timeline

| Task | Duration | Cumulative |
|------|----------|------------|
| Update config tests | 10 min | 10 min |
| Comment out Q&A tests | 5 min | 15 min |
| Add new AI-native tests | 30 min | 45 min |
| Run integration tests | 10 min | 55 min |
| Run full test suite | 5 min | 60 min |
| **Total** | **60 min** | **1 hour** |

**Buffer**: Add 30-60 minutes for unexpected issues or additional test coverage.

**Total with buffer**: 1.5-2 hours (matches estimate)

---

**Status**: Ready for Implementation
**Blocked By**: None (TASK-51B2 is complete)
**Blocks**: None (optional cleanup task)
**Created**: 2025-01-12
**Priority**: High (ensure test suite is clean after major refactor)
