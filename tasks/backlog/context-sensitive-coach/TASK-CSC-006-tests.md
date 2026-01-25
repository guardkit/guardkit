---
id: TASK-CSC-006
title: Add unit and integration tests
status: backlog
created: 2026-01-23T11:30:00Z
priority: medium
tags: [context-sensitive-coach, testing, quality-gates]
task_type: testing
complexity: 4
parent_review: TASK-REV-CSC1
feature_id: FEAT-CSC
wave: 4
implementation_mode: task-work
conductor_workspace: csc-wave4-tests
dependencies:
  - TASK-CSC-005
---

# Task: Add Unit and Integration Tests

## Description

Add comprehensive tests for all context-sensitive Coach components to ensure correctness and prevent regressions.

## Acceptance Criteria

- [ ] Unit tests for `UniversalContextGatherer` (>80% coverage)
- [ ] Unit tests for `FastClassifier` (>80% coverage)
- [ ] Unit tests for `AIContextAnalyzer` with mock AI (>80% coverage)
- [ ] Unit tests for `ContextCache` (>80% coverage)
- [ ] Integration tests for `ContextSensitiveCoachValidator`
- [ ] Test fixtures for various scenarios
- [ ] All tests pass and coverage meets thresholds

## Implementation Notes

### Test Location

Create in: `tests/unit/quality_gates/context_analysis/`

```
tests/unit/quality_gates/context_analysis/
├── __init__.py
├── test_models.py
├── test_classifier.py
├── test_ai_analyzer.py
├── test_cache.py
└── test_integration.py
```

### Test Fixtures

```python
# tests/conftest.py additions

@pytest.fixture
def trivial_context():
    """Context for trivially small implementation."""
    return UniversalContext(
        lines_added=20,
        lines_deleted=0,
        lines_modified=0,
        files_created=1,
        files_modified=0,
        files_deleted=0,
        file_extensions={".py": 1},
        source_files=1,
        test_files=0,
        config_files=0,
        has_dependency_changes=False,
        new_external_dependencies=0,
    )

@pytest.fixture
def complex_context():
    """Context for complex implementation."""
    return UniversalContext(
        lines_added=450,
        lines_deleted=50,
        lines_modified=100,
        files_created=8,
        files_modified=5,
        files_deleted=2,
        file_extensions={".py": 10, ".json": 3},
        source_files=10,
        test_files=3,
        config_files=3,
        has_dependency_changes=True,
        new_external_dependencies=3,
    )

@pytest.fixture
def mock_ai_response_declarative():
    """Mock AI response for declarative code."""
    return {
        "testability_score": 15,
        "patterns": ["declarative_config"],
        "is_declarative": True,
        "arch_review_recommended": False,
        "rationale": "Pure Pydantic model with no logic"
    }

@pytest.fixture
def mock_ai_response_logic():
    """Mock AI response for code with business logic."""
    return {
        "testability_score": 85,
        "patterns": ["business_logic", "data_access"],
        "is_declarative": False,
        "arch_review_recommended": True,
        "rationale": "Authentication service with complex validation"
    }
```

### Unit Test Examples

```python
# test_classifier.py

class TestFastClassifier:
    def test_trivial_classification(self, trivial_context):
        classifier = FastClassifier()
        result = classifier.classify(trivial_context)

        assert result.category == ScopeCategory.TRIVIAL
        assert result.confidence >= 0.8
        assert not result.needs_ai_analysis
        assert result.recommended_profile == "minimal"

    def test_complex_classification(self, complex_context):
        classifier = FastClassifier()
        result = classifier.classify(complex_context)

        assert result.category == ScopeCategory.COMPLEX
        assert result.confidence >= 0.8
        assert not result.needs_ai_analysis
        assert result.recommended_profile == "strict"

    def test_uncertain_requires_ai(self):
        """Middle-ground context should require AI analysis."""
        context = UniversalContext(
            lines_added=150,  # In the uncertain range
            ...
        )
        classifier = FastClassifier()
        result = classifier.classify(context)

        assert result.category == ScopeCategory.UNCERTAIN
        assert result.needs_ai_analysis
```

```python
# test_ai_analyzer.py

class TestAIContextAnalyzer:
    @pytest.mark.asyncio
    async def test_parse_valid_response(self, mock_ai_response_declarative):
        analyzer = AIContextAnalyzer()
        result = analyzer._parse_response(json.dumps(mock_ai_response_declarative))

        assert result.testability_score == 15
        assert "declarative_config" in result.patterns
        assert result.is_declarative
        assert not result.arch_review_recommended

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self):
        analyzer = AIContextAnalyzer()
        result = analyzer._parse_response("not valid json")

        # Should return conservative defaults
        assert result.testability_score == 50
        assert result.arch_review_recommended  # Conservative
```

### Integration Test Examples

```python
# test_integration.py

class TestContextSensitiveCoachIntegration:
    @pytest.mark.asyncio
    async def test_trivial_task_uses_minimal_profile(self, tmp_path, trivial_context):
        """Trivial tasks should bypass AI and use minimal profile."""
        validator = ContextSensitiveCoachValidator(str(tmp_path))

        # Mock the context gatherer to return trivial context
        validator.context_gatherer.gather = Mock(return_value=trivial_context)

        result = await validator.validate("TASK-001", 1, {"acceptance_criteria": []})

        # Should not have called AI
        assert validator.ai_analyzer.analyze.call_count == 0

    @pytest.mark.asyncio
    async def test_feature_flag_off_uses_base_validator(self, tmp_path, monkeypatch):
        """When feature flag is off, should use base CoachValidator."""
        monkeypatch.setenv("GUARDKIT_CONTEXT_SENSITIVE_COACH", "false")

        validator = get_coach_validator(str(tmp_path))
        assert isinstance(validator, CoachValidator)
        assert not isinstance(validator, ContextSensitiveCoachValidator)
```

## Testing Strategy

1. **Unit tests**: Test each component in isolation with mocks
2. **Integration tests**: Test full flow with mock AI
3. **Snapshot tests**: Compare profile selection against known inputs
4. **Edge cases**: Empty diffs, single files, large diffs, binary files
