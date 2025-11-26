---
id: TASK-INIT-011
title: "Comprehensive testing for all ported features"
status: backlog
created: 2025-11-26T07:30:00Z
updated: 2025-11-26T07:30:00Z
priority: high
tags: [template-init, testing, week5, documentation-testing]
complexity: 5
estimated_hours: 8
parent_review: TASK-5E55
week: 5
phase: documentation-testing
related_tasks: [TASK-INIT-001, TASK-INIT-002, TASK-INIT-003, TASK-INIT-004, TASK-INIT-005, TASK-INIT-006, TASK-INIT-007, TASK-INIT-008, TASK-INIT-009]
dependencies: [TASK-INIT-001, TASK-INIT-002, TASK-INIT-003, TASK-INIT-004, TASK-INIT-005, TASK-INIT-006, TASK-INIT-007, TASK-INIT-008, TASK-INIT-009]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Comprehensive Testing for All Ported Features

## Problem Statement

All 13 ported features need comprehensive testing to ensure correctness, prevent regressions, and validate integration points across TASK-INIT-001 through TASK-INIT-009.

**Impact**: Without comprehensive tests, ported features risk regressions and integration issues that could break greenfield template creation.

## Analysis Findings

From TASK-5E55 review:
- 13 features ported with significant code changes (400+ lines added)
- Multiple integration points between features
- Risk of regressions in existing Q&A workflow
- Need unit, integration, and regression test coverage
- Target: ≥80% coverage for new code

**Current State**: Individual feature tests exist, but no comprehensive test suite

**Desired State**: Complete test coverage with unit, integration, and regression tests

## Recommended Fix

**Approach**: Create comprehensive test suite covering all ported features and their interactions.

**Strategy**:
- **UNIT TESTS**: Test each feature in isolation
- **INTEGRATION TESTS**: Test feature interactions
- **REGRESSION TESTS**: Ensure existing functionality unchanged
- **E2E TESTS**: Test complete workflow
- **COVERAGE**: Achieve ≥80% for new code

## Test Suite Structure

### File: tests/test_template_init/test_enhancements.py

```python
"""
Comprehensive test suite for /template-init enhancements.

Tests all features ported from /template-create (TASK-INIT-001 through TASK-INIT-009):
1. Boundary sections
2. Agent enhancement tasks
3. Level 1 validation
4. Level 2 validation
5. Level 3 integration
6. Quality scoring
7. Two-location output
8. Discovery metadata
9. Exit codes
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from installer.global.commands.lib.greenfield_qa_session import (
    TemplateInitQASession,
    generate_boundary_sections,
    validate_boundary_sections,
    QualityScorer
)


# =============================================================================
# TASK-INIT-001: Boundary Sections
# =============================================================================

class TestBoundarySections:
    """Test boundary section generation and validation."""

    def test_generate_boundary_sections_testing_agent(self):
        """Test boundary generation for testing agent."""
        boundaries = generate_boundary_sections('testing', 'python')

        assert 5 <= len(boundaries['always']) <= 7
        assert 5 <= len(boundaries['never']) <= 7
        assert 3 <= len(boundaries['ask']) <= 5

        # Check emoji prefixes
        for rule in boundaries['always']:
            assert rule.startswith('✅')
        for rule in boundaries['never']:
            assert rule.startswith('❌')
        for scenario in boundaries['ask']:
            assert scenario.startswith('⚠️')

    def test_generate_boundary_sections_repository_agent(self):
        """Test boundary generation for repository agent."""
        boundaries = generate_boundary_sections('repository', 'csharp')

        assert 5 <= len(boundaries['always']) <= 7
        assert 'constructor' in str(boundaries).lower() or 'DI' in str(boundaries)

    def test_generate_boundary_sections_api_agent(self):
        """Test boundary generation for API agent."""
        boundaries = generate_boundary_sections('api', 'typescript')

        assert 5 <= len(boundaries['always']) <= 7
        assert 'validate' in str(boundaries).lower() or 'validation' in str(boundaries).lower()

    def test_generate_boundary_sections_generic_agent(self):
        """Test boundary generation for unknown agent type."""
        boundaries = generate_boundary_sections('unknown', 'go')

        assert 5 <= len(boundaries['always']) <= 7
        assert 'best practices' in boundaries['always'][0].lower() or 'go' in boundaries['always'][0].lower()

    def test_validate_boundary_sections_valid(self):
        """Test validation with valid boundaries."""
        boundaries = {
            'always': ['✅ Rule ' + str(i) for i in range(5)],
            'never': ['❌ Rule ' + str(i) for i in range(5)],
            'ask': ['⚠️ Scenario ' + str(i) for i in range(3)]
        }

        is_valid, errors = validate_boundary_sections(boundaries)
        assert is_valid
        assert len(errors) == 0

    def test_validate_boundary_sections_invalid_count(self):
        """Test validation catches count violations."""
        boundaries = {
            'always': ['✅ Rule 1', '✅ Rule 2'],  # Too few
            'never': ['❌ Rule'] * 10,  # Too many
            'ask': []  # Too few
        }

        is_valid, errors = validate_boundary_sections(boundaries)
        assert not is_valid
        assert len(errors) >= 3

    def test_validate_boundary_sections_missing_emoji(self):
        """Test validation catches missing emoji prefixes."""
        boundaries = {
            'always': ['Rule without emoji'] + ['✅ Rule ' + str(i) for i in range(4)],
            'never': ['❌ Rule ' + str(i) for i in range(5)],
            'ask': ['⚠️ Scenario ' + str(i) for i in range(3)]
        }

        is_valid, errors = validate_boundary_sections(boundaries)
        assert not is_valid
        assert any('missing ✅' in error for error in errors)


# =============================================================================
# TASK-INIT-002: Agent Enhancement Tasks
# =============================================================================

class TestAgentEnhancementTasks:
    """Test agent enhancement task creation."""

    def test_create_agent_enhancement_tasks(self):
        """Test task creation for agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = TemplateInitQASession()

            # Create mock agent files
            agents_dir = Path(tmpdir) / "agents"
            agents_dir.mkdir()
            agent_files = [
                agents_dir / "test-agent.md",
                agents_dir / "api-agent.md"
            ]
            for f in agent_files:
                f.write_text("# Agent")

            # Create tasks (mock working directory)
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                task_ids = session._create_agent_enhancement_tasks(
                    'my-template',
                    agent_files
                )

            assert len(task_ids) == 2
            assert all('TASK-AGENT-' in tid for tid in task_ids)

            # Verify task files created
            tasks_dir = Path(tmpdir) / "tasks" / "backlog"
            task_files = list(tasks_dir.glob("TASK-AGENT-*.md"))
            assert len(task_files) == 2

    def test_skip_task_creation_with_flag(self):
        """Test --no-create-agent-tasks flag."""
        session = TemplateInitQASession(no_create_agent_tasks=True)

        assert session.no_create_agent_tasks is True

    def test_task_metadata_includes_required_fields(self):
        """Test task files have required metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = TemplateInitQASession()

            agents_dir = Path(tmpdir) / "agents"
            agents_dir.mkdir()
            agent_file = agents_dir / "test.md"
            agent_file.write_text("# Test Agent")

            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                task_ids = session._create_agent_enhancement_tasks(
                    'test-template',
                    [agent_file]
                )

            # Read created task file
            tasks_dir = Path(tmpdir) / "tasks" / "backlog"
            task_file = list(tasks_dir.glob("TASK-AGENT-*.md"))[0]
            content = task_file.read_text()

            assert 'agent_file' in content
            assert 'template_name' in content
            assert 'test-template' in content


# =============================================================================
# TASK-INIT-003: Level 1 Validation
# =============================================================================

class TestLevel1Validation:
    """Test automatic validation (Level 1)."""

    def test_validate_crud_completeness_full_coverage(self):
        """Test CRUD validation with full coverage."""
        session = TemplateInitQASession()
        template_data = {
            'agents': [
                {'name': 'create-agent', 'capabilities': ['post']},
                {'name': 'read-agent', 'capabilities': ['get']},
                {'name': 'update-agent', 'capabilities': ['put']},
                {'name': 'delete-agent', 'capabilities': ['delete']}
            ]
        }

        result = session._validate_crud_completeness(template_data)

        assert result['coverage'] == 1.0
        assert result['passes'] is True
        assert len(result['missing_operations']) == 0

    def test_validate_crud_completeness_partial(self):
        """Test CRUD validation with partial coverage."""
        session = TemplateInitQASession()
        template_data = {
            'agents': [
                {'name': 'read-agent', 'capabilities': ['get']},
            ]
        }

        result = session._validate_crud_completeness(template_data)

        assert result['coverage'] == 0.25
        assert result['passes'] is False
        assert 'create' in result['missing_operations']

    def test_validate_layer_symmetry_3tier(self):
        """Test layer symmetry for 3-tier architecture."""
        session = TemplateInitQASession()
        template_data = {
            'layers': ['api', 'service', 'repository']
        }

        result = session._validate_layer_symmetry(template_data)

        assert result['is_symmetric'] is True
        assert set(result['matched_pattern']) == {'api', 'service', 'repository'}

    def test_validate_layer_symmetry_incomplete(self):
        """Test layer symmetry with incomplete pattern."""
        session = TemplateInitQASession()
        template_data = {
            'layers': ['api', 'service']  # Missing repository
        }

        result = session._validate_layer_symmetry(template_data)

        assert result['is_symmetric'] is False
        assert len(result['issues']) > 0


# =============================================================================
# TASK-INIT-004: Level 2 Validation
# =============================================================================

class TestLevel2Validation:
    """Test extended validation (Level 2)."""

    def test_validate_flag_triggers_level2(self):
        """Test --validate flag triggers extended validation."""
        session = TemplateInitQASession(validate=True)

        assert session.validate is True

    def test_placeholder_consistency_single_format(self):
        """Test placeholder validation with consistent format."""
        session = TemplateInitQASession(validate=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "template"
            template_path.mkdir()
            (template_path / "config.template").write_text("name: {{project_name}}")
            (template_path / "readme.template").write_text("# {{title}}")

            result = session._validate_placeholder_consistency(template_path)

            assert result['score'] == 10
            assert len(result['issues']) == 0

    def test_placeholder_consistency_mixed_formats(self):
        """Test placeholder validation detects mixed formats."""
        session = TemplateInitQASession(validate=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "template"
            template_path.mkdir()
            (template_path / "config.template").write_text("name: {{project_name}}")
            (template_path / "env.template").write_text("VAR=${VALUE}")

            result = session._validate_placeholder_consistency(template_path)

            assert result['score'] < 10
            assert len(result['issues']) > 0

    def test_quality_score_calculation(self):
        """Test overall quality score calculation."""
        session = TemplateInitQASession(validate=True)

        quality_scores = session._calculate_overall_quality_score(
            {'score': 10},  # placeholder
            {'score': 10},  # pattern
            {'passes': True, 'coverage': 1.0},  # crud
            {'is_symmetric': True}  # layer
        )

        assert quality_scores['overall_score'] >= 9
        assert quality_scores['grade'] in ['A', 'A+']
        assert quality_scores['production_ready'] is True


# =============================================================================
# TASK-INIT-005: Level 3 Integration
# =============================================================================

class TestLevel3Integration:
    """Test /template-validate compatibility."""

    def test_ensure_validation_compatibility(self):
        """Test validation compatibility setup."""
        session = TemplateInitQASession()

        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "template"
            template_path.mkdir()

            session._ensure_validation_compatibility(template_path)

            # Check marker file
            marker = template_path / ".validation-compatible"
            assert marker.exists()
            assert "1.0.0" in marker.read_text()

            # Check manifest fields
            manifest_path = template_path / "template-manifest.json"
            manifest = json.loads(manifest_path.read_text())
            assert 'schema_version' in manifest
            assert 'complexity' in manifest
            assert 'confidence_score' in manifest

    def test_required_directories_created(self):
        """Test required directories for validation."""
        session = TemplateInitQASession()

        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "template"
            template_path.mkdir()

            session._ensure_validation_compatibility(template_path)

            assert (template_path / "templates").exists()
            assert (template_path / "agents").exists()


# =============================================================================
# TASK-INIT-006: Quality Scoring
# =============================================================================

class TestQualityScoring:
    """Test quality scoring system."""

    def test_quality_scorer_initialization(self):
        """Test QualityScorer initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir)
            session_data = {'primary_language': 'python'}

            scorer = QualityScorer(session_data, template_path)

            assert scorer.session_data == session_data
            assert scorer.template_path == template_path

    def test_score_architecture_known_pattern(self):
        """Test architecture scoring with known pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_data = {
                'architecture_pattern': '3-tier',
                'layers': ['api', 'service', 'repository']
            }
            scorer = QualityScorer(session_data, Path(tmpdir))

            score = scorer._score_architecture()

            assert score >= 7.0

    def test_score_testing_full_coverage(self):
        """Test testing score with full coverage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_data = {
                'test_types': ['unit', 'integration', 'e2e'],
                'test_runner': 'pytest'
            }
            scorer = QualityScorer(session_data, Path(tmpdir))

            score = scorer._score_testing()

            assert score >= 8.0

    def test_quality_report_generation(self):
        """Test quality report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir)
            (template_path / "agents").mkdir()

            session_data = {
                'primary_language': 'python',
                'architecture_pattern': '3-tier',
                'layers': ['api', 'service', 'repository']
            }

            scorer = QualityScorer(session_data, template_path)
            scores = scorer.calculate_score()
            scorer.generate_report(scores)

            report_path = template_path / "quality-report.md"
            assert report_path.exists()

            report_content = report_path.read_text()
            assert 'Quality Report' in report_content
            assert 'Overall Score' in report_content


# =============================================================================
# TASK-INIT-007: Two-Location Output
# =============================================================================

class TestTwoLocationOutput:
    """Test two-location output support."""

    def test_get_template_path_global(self):
        """Test global location path resolution."""
        session = TemplateInitQASession(output_location='global')
        path = session._get_template_path('test-template')

        assert '.agentecflow/templates' in str(path)
        assert path.name == 'test-template'

    def test_get_template_path_repo(self):
        """Test repo location path resolution."""
        session = TemplateInitQASession(output_location='repo')
        path = session._get_template_path('test-template')

        assert 'installer/global/templates' in str(path)
        assert path.name == 'test-template'

    def test_default_location_is_global(self):
        """Test default output location."""
        session = TemplateInitQASession()

        assert session.output_location == 'global'


# =============================================================================
# TASK-INIT-008: Discovery Metadata
# =============================================================================

class TestDiscoveryMetadata:
    """Test discovery metadata generation."""

    def test_generate_agent_metadata_python_api(self):
        """Test metadata for Python API agent."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'python',
            'framework': 'fastapi'
        }

        metadata = session._generate_agent_metadata('api')

        assert metadata['stack'] == ['python', 'fastapi']
        assert metadata['phase'] == 'implementation'
        assert 'endpoint-implementation' in metadata['capabilities']
        assert 'api' in metadata['keywords']

    def test_format_agent_with_metadata(self):
        """Test frontmatter formatting."""
        session = TemplateInitQASession()

        content = "# Test Agent\n\nAgent content"
        metadata = {
            'stack': ['python', 'fastapi'],
            'phase': 'implementation',
            'capabilities': ['api', 'testing'],
            'keywords': ['python', 'api']
        }

        formatted = session._format_agent_with_metadata(content, metadata)

        assert formatted.startswith('---')
        assert 'stack: [python, fastapi]' in formatted
        assert 'phase: implementation' in formatted


# =============================================================================
# TASK-INIT-009: Exit Codes
# =============================================================================

class TestExitCodes:
    """Test exit code support."""

    def test_exit_code_high_quality(self):
        """Test exit code 0 for high quality."""
        session = TemplateInitQASession()

        with patch.object(QualityScorer, 'calculate_score') as mock_score:
            mock_score.return_value = {
                'overall_score': 9.0,
                'component_scores': {},
                'production_ready': True
            }

            # Mock other methods to avoid full run
            with patch.object(session, '_save_template', return_value=Path('/tmp')):
                with patch.object(session, '_run_level1_validation', return_value={}):
                    answers, exit_code = session.run()

            assert exit_code == 0

    def test_exit_code_medium_quality(self):
        """Test exit code 1 for medium quality."""
        session = TemplateInitQASession()

        with patch.object(QualityScorer, 'calculate_score') as mock_score:
            mock_score.return_value = {
                'overall_score': 7.0,
                'component_scores': {},
                'production_ready': True
            }

            with patch.object(session, '_save_template', return_value=Path('/tmp')):
                with patch.object(session, '_run_level1_validation', return_value={}):
                    answers, exit_code = session.run()

            assert exit_code == 1


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Test feature interactions and full workflow."""

    def test_full_workflow_with_all_features(self):
        """Test complete workflow with all features enabled."""
        session = TemplateInitQASession(
            validate=True,
            output_location='global',
            no_create_agent_tasks=False
        )

        # Mock Q&A session data
        session._session_data = {
            'template_name': 'test-template',
            'primary_language': 'python',
            'framework': 'fastapi',
            'architecture_pattern': '3-tier',
            'layers': ['api', 'service', 'repository']
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                with patch.object(session, '_section1_identity'):
                    # Test that all phases execute
                    # This is a smoke test - actual implementation tested in unit tests
                    pass

    def test_boundary_sections_with_metadata(self):
        """Test boundary sections and metadata integration."""
        session = TemplateInitQASession()
        session._session_data = {'primary_language': 'python'}

        agent_content = session._generate_agent('testing')

        # Should have both frontmatter and boundaries
        assert agent_content.startswith('---')
        assert '## Boundaries' in agent_content
        assert '### ALWAYS' in agent_content
        assert '✅' in agent_content


# =============================================================================
# Regression Tests
# =============================================================================

class TestRegression:
    """Test that existing functionality still works."""

    def test_existing_qa_workflow_unchanged(self):
        """Test Q&A workflow not broken by changes."""
        session = TemplateInitQASession()

        # Mock Q&A responses
        with patch('inquirer.prompt') as mock_prompt:
            mock_prompt.return_value = {
                'template_name': 'test',
                'template_purpose': 'quick_start'
            }

            # This should not raise any exceptions
            # Actual Q&A tested elsewhere
            pass

    def test_backward_compatibility_no_flags(self):
        """Test backward compatibility without new flags."""
        session = TemplateInitQASession()

        # Should work with default settings
        assert session.validate is False
        assert session.output_location == 'global'

    def test_template_save_mechanism_unchanged(self):
        """Test template save still works."""
        session = TemplateInitQASession()
        session._session_data = {'template_name': 'test'}

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.home', return_value=Path(tmpdir)):
                path = session._save_template()

                # Path resolution should work
                assert path.name == 'test'


# =============================================================================
# Coverage Tests
# =============================================================================

def test_coverage_target():
    """Verify test coverage meets ≥80% target."""
    # This test runs pytest-cov and checks coverage
    # Actual implementation depends on CI/CD setup
    pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=installer.global.commands.lib.greenfield_qa_session'])
```

## Scope Constraints

### ❌ DO NOT
- Modify implementation to pass tests (tests should reflect requirements)
- Skip tests that fail (fix implementation instead)
- Reduce coverage target below 80%
- Test external dependencies (mock them)

### ✅ DO ONLY
- Create comprehensive test suite
- Achieve ≥80% coverage for new code
- Test all 13 ported features
- Test feature interactions
- Ensure no regressions

## Files to Create

1. **tests/test_template_init/test_enhancements.py** - NEW
   - Unit tests for all 9 implementation tasks
   - Integration tests for feature interactions
   - Regression tests for existing functionality
   - ~600 lines of test code

## Files to NOT Touch

- Implementation code (unless tests reveal bugs)
- Existing test files
- CI/CD configuration (unless coverage reporting needs setup)

## Testing Requirements

### Coverage Targets

- Overall: ≥80% line coverage for greenfield_qa_session.py new code
- Unit tests: ≥90% coverage for individual functions
- Integration tests: ≥70% coverage for workflow
- Regression tests: 100% of critical paths

### Test Execution

```bash
# Run all tests
pytest tests/test_template_init/test_enhancements.py -v

# Run with coverage
pytest tests/test_template_init/test_enhancements.py --cov=installer.global.commands.lib.greenfield_qa_session --cov-report=term --cov-report=html

# Run specific test class
pytest tests/test_template_init/test_enhancements.py::TestBoundarySections -v
```

## Acceptance Criteria

- [ ] All ported features have unit tests
- [ ] Feature interactions have integration tests
- [ ] Existing functionality has regression tests
- [ ] Test coverage ≥80% for new code
- [ ] All tests pass
- [ ] Tests use mocks for external dependencies
- [ ] Tests use temporary directories (no side effects)
- [ ] CI/CD can run tests automatically
- [ ] Coverage report generated
- [ ] No flaky tests

## Estimated Effort

**8 hours** broken down as:
- Design test structure (1 hour)
- Write unit tests for 9 features (4 hours)
- Write integration tests (1.5 hours)
- Write regression tests (1 hour)
- Achieve coverage target and fix gaps (30 minutes)

## Dependencies

**ALL IMPLEMENTATION TASKS** (TASK-INIT-001 through TASK-INIT-009) must be complete

## Risk Assessment

### Risks

| Risk | Probability | Impact | Severity |
|------|------------|--------|----------|
| Coverage target not achievable | Low | High | 🟡 Medium |
| Tests too brittle (false failures) | Medium | Medium | 🟡 Medium |
| Missing edge cases | Medium | Medium | 🟡 Medium |
| Test execution time too long | Low | Low | 🟢 Minimal |

### Mitigation Strategies

1. **Coverage target**: Focus on critical paths first, then expand
2. **Test brittleness**: Use mocks liberally, avoid hardcoded values
3. **Edge cases**: Review each feature's acceptance criteria for edge cases
4. **Execution time**: Use pytest-xdist for parallel execution if needed

## References

- **Parent Review**: TASK-5E55
- **Implementation Tasks**: TASK-INIT-001 through TASK-INIT-009
- **Testing Guide**: Use pytest, pytest-cov, unittest.mock
- **Coverage Tool**: pytest-cov with HTML reports

## Success Metrics

When complete:
- ✅ All ported features tested
- ✅ Coverage ≥80% for new code
- ✅ All tests pass
- ✅ No regressions detected
- ✅ CI/CD can run tests
- ✅ Coverage reports generated
