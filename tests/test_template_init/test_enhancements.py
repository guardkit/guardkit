"""
Comprehensive test suite for /template-init enhancements.

Tests all features ported from /template-create (TASK-INIT-001 through TASK-INIT-009):
1. Boundary sections (TASK-INIT-001)
2. Agent enhancement tasks (TASK-INIT-002)
3. Level 1 validation (TASK-INIT-003 - not implemented in greenfield_qa_session.py yet)
4. Level 2 validation (TASK-INIT-004 - not implemented in greenfield_qa_session.py yet)
5. Level 3 integration (TASK-INIT-005 - partially implemented)
6. Quality scoring (TASK-INIT-006 - placeholder implementation)
7. Two-location output (TASK-INIT-007 - not implemented in greenfield_qa_session.py yet)
8. Discovery metadata (TASK-INIT-008)
9. Exit codes (TASK-INIT-009)
"""

import pytest
import tempfile
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

# Mock inquirer before importing greenfield_qa_session
mock_inquirer = Mock()
mock_inquirer.Text = Mock
mock_inquirer.List = Mock
mock_inquirer.Checkbox = Mock
mock_inquirer.Confirm = Mock
mock_inquirer.prompt = Mock(return_value={})
mock_inquirer.confirm = Mock(return_value=True)
sys.modules['inquirer'] = mock_inquirer

from greenfield_qa_session import (
    TemplateInitQASession,
    GreenfieldAnswers,
    generate_boundary_sections,
    validate_boundary_sections,
)

# Force INQUIRER_AVAILABLE to True for testing by patching the module
import greenfield_qa_session as gqa_module
gqa_module.INQUIRER_AVAILABLE = True


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
        # Check for DI-related content
        boundaries_str = str(boundaries)
        assert 'constructor' in boundaries_str.lower() or 'DI' in boundaries_str or 'inject' in boundaries_str.lower()

    def test_generate_boundary_sections_api_agent(self):
        """Test boundary generation for API agent."""
        boundaries = generate_boundary_sections('api', 'typescript')

        assert 5 <= len(boundaries['always']) <= 7
        boundaries_str = str(boundaries)
        assert 'validate' in boundaries_str.lower() or 'validation' in boundaries_str.lower()

    def test_generate_boundary_sections_service_agent(self):
        """Test boundary generation for service agent."""
        boundaries = generate_boundary_sections('service', 'python')

        assert 5 <= len(boundaries['always']) <= 7
        boundaries_str = str(boundaries)
        # Check for service-specific patterns
        assert 'inject' in boundaries_str.lower() or 'DI' in boundaries_str

    def test_generate_boundary_sections_generic_agent(self):
        """Test boundary generation for unknown agent type."""
        boundaries = generate_boundary_sections('unknown', 'go')

        assert 5 <= len(boundaries['always']) <= 7
        # Should have generic best practices
        boundaries_str = boundaries['always'][0].lower()
        assert 'go' in boundaries_str or 'best practices' in boundaries_str

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

    def test_validate_boundary_sections_all_sections_required(self):
        """Test validation requires all three sections."""
        boundaries = {
            'always': ['✅ Rule ' + str(i) for i in range(5)],
            'never': ['❌ Rule ' + str(i) for i in range(5)]
            # Missing 'ask' section
        }

        is_valid, errors = validate_boundary_sections(boundaries)
        assert not is_valid


# =============================================================================
# TASK-INIT-002: Agent Enhancement Tasks
# =============================================================================

class TestAgentEnhancementTasks:
    """Test agent enhancement task creation."""

    def test_create_agent_enhancement_tasks(self):
        """Test task creation for agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = TemplateInitQASession()
            session._session_data = {'primary_language': 'python'}

            # Create mock agent files
            agents_dir = Path(tmpdir) / "agents"
            agents_dir.mkdir()
            agent_files = [
                agents_dir / "test-agent.md",
                agents_dir / "api-agent.md"
            ]
            for f in agent_files:
                f.write_text("# Agent")

            # Change to tmpdir so task files are created there
            import os
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                task_ids = session._create_agent_enhancement_tasks(
                    'my-template',
                    agent_files
                )

                assert len(task_ids) == 2
                assert all('TASK-' in tid for tid in task_ids)

                # Verify task files created
                tasks_dir = Path(tmpdir) / "tasks" / "backlog"
                task_files = list(tasks_dir.glob("TASK-*.md"))
                assert len(task_files) == 2
            finally:
                os.chdir(original_cwd)

    def test_skip_task_creation_with_flag(self):
        """Test --no-create-agent-tasks flag."""
        session = TemplateInitQASession(no_create_agent_tasks=True)

        assert session.no_create_agent_tasks is True

    def test_task_metadata_includes_required_fields(self):
        """Test task files have required metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = TemplateInitQASession()
            session._session_data = {'primary_language': 'typescript'}

            agents_dir = Path(tmpdir) / "agents"
            agents_dir.mkdir()
            agent_file = agents_dir / "test.md"
            agent_file.write_text("# Test Agent")

            import os
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                task_ids = session._create_agent_enhancement_tasks(
                    'test-template',
                    [agent_file]
                )

                # Read created task file
                tasks_dir = Path(tmpdir) / "tasks" / "backlog"
                task_file = list(tasks_dir.glob("TASK-*.md"))[0]
                content = task_file.read_text()

                assert 'agent_file' in content
                assert 'template_name' in content
                assert 'test-template' in content
                assert 'typescript' in content  # Primary language included
            finally:
                os.chdir(original_cwd)

    def test_enhancement_task_includes_both_options(self):
        """Test enhancement tasks include both /agent-enhance and /task-work options."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session = TemplateInitQASession()
            session._session_data = {'primary_language': 'python'}

            agents_dir = Path(tmpdir) / "agents"
            agents_dir.mkdir()
            agent_file = agents_dir / "api-agent.md"
            agent_file.write_text("# API Agent")

            import os
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                task_ids = session._create_agent_enhancement_tasks(
                    'my-template',
                    [agent_file]
                )

                tasks_dir = Path(tmpdir) / "tasks" / "backlog"
                task_file = list(tasks_dir.glob("TASK-*.md"))[0]
                content = task_file.read_text()

                assert '/agent-enhance' in content
                assert '/task-work' in content
                assert 'Option A' in content
                assert 'Option B' in content
            finally:
                os.chdir(original_cwd)


# =============================================================================
# TASK-INIT-005: Level 3 Integration
# =============================================================================

class TestLevel3Integration:
    """Test /template-validate compatibility."""

    def test_ensure_validation_compatibility(self):
        """Test validation compatibility setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "template"
            template_path.mkdir()

            session = TemplateInitQASession()
            session.ensure_validation_compatibility(template_path)

            # Check marker file
            marker = template_path / ".validation-compatible"
            assert marker.exists()
            assert "1.0.0" in marker.read_text()

            # Check manifest fields
            manifest_path = template_path / "template-manifest.json"
            assert manifest_path.exists()
            manifest = json.loads(manifest_path.read_text())
            assert 'schema_version' in manifest
            assert 'complexity' in manifest
            assert 'confidence_score' in manifest
            assert 'validation_compatible' in manifest
            assert manifest['validation_compatible'] is True

    def test_required_directories_created(self):
        """Test required directories for validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "template"
            template_path.mkdir()

            session = TemplateInitQASession()
            session.ensure_validation_compatibility(template_path)

            assert (template_path / "templates").exists()
            assert (template_path / "agents").exists()

    def test_manifest_complexity_estimation(self):
        """Test complexity is estimated from template structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "template"
            template_path.mkdir()

            # Create agents and templates
            agents_dir = template_path / "agents"
            agents_dir.mkdir()
            for i in range(6):  # 6 agents = 3 points
                (agents_dir / f"agent{i}.md").write_text(f"# Agent {i}")

            templates_dir = template_path / "templates"
            templates_dir.mkdir()
            for i in range(9):  # 9 templates = 3 points
                (templates_dir / f"template{i}.txt").write_text(f"Template {i}")

            session = TemplateInitQASession()
            session.ensure_validation_compatibility(template_path)

            manifest_path = template_path / "template-manifest.json"
            manifest = json.loads(manifest_path.read_text())

            # complexity = 3 + (6 agents // 2) + (9 templates // 3) = 3 + 3 + 3 = 9
            expected_complexity = 3 + (6 // 2) + (9 // 3)
            assert manifest['complexity'] == expected_complexity

    def test_confidence_score_default(self):
        """Test default confidence score for greenfield."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "template"
            template_path.mkdir()

            session = TemplateInitQASession()
            session.ensure_validation_compatibility(template_path)

            manifest_path = template_path / "template-manifest.json"
            manifest = json.loads(manifest_path.read_text())

            # Greenfield defaults to 75 (no codebase analysis)
            assert manifest['confidence_score'] == 75


# =============================================================================
# TASK-INIT-006: Quality Scoring
# =============================================================================

class TestQualityScoring:
    """Test quality scoring system."""

    def test_placeholder_quality_score_base(self):
        """Test placeholder scoring starts at 5.0."""
        session = TemplateInitQASession()
        session._session_data = {}

        score = session._calculate_placeholder_quality_score()
        assert score >= 5.0

    def test_placeholder_quality_score_with_testing(self):
        """Test bonus for comprehensive testing."""
        session = TemplateInitQASession()
        session._session_data = {
            'testing_scope': ['unit', 'integration', 'e2e']
        }

        score = session._calculate_placeholder_quality_score()
        # Base (5.0) + unit (1.0) + integration (0.5) + 3+ tests (0.5) = 7.0
        assert score >= 7.0

    def test_placeholder_quality_score_with_error_handling(self):
        """Test bonus for error handling."""
        session = TemplateInitQASession()
        session._session_data = {
            'error_handling': 'result'
        }

        score = session._calculate_placeholder_quality_score()
        # Base (5.0) + result error handling (1.0) = 6.0
        assert score >= 6.0

    def test_placeholder_quality_score_with_di(self):
        """Test bonus for dependency injection."""
        session = TemplateInitQASession()
        session._session_data = {
            'dependency_injection': 'builtin'
        }

        score = session._calculate_placeholder_quality_score()
        # Base (5.0) + DI (0.5) = 5.5
        assert score >= 5.5

    def test_placeholder_quality_score_capped_at_10(self):
        """Test score is capped at 10.0."""
        session = TemplateInitQASession()
        session._session_data = {
            'testing_scope': ['unit', 'integration', 'e2e', 'performance'],
            'error_handling': 'result',
            'dependency_injection': 'builtin',
            'validation_approach': 'fluent',
            'architecture_pattern': 'clean',
            'documentation_paths': [Path('/docs')]
        }

        score = session._calculate_placeholder_quality_score()
        assert score <= 10.0

    def test_placeholder_quality_score_full_features(self):
        """Test score with all features enabled."""
        session = TemplateInitQASession()
        session._session_data = {
            'testing_scope': ['unit', 'integration', 'e2e'],
            'error_handling': 'result',
            'dependency_injection': 'builtin',
            'validation_approach': 'fluent',
            'architecture_pattern': 'clean',
            'documentation_text': 'Some docs'
        }

        score = session._calculate_placeholder_quality_score()
        # All bonuses applied, should be high
        assert score >= 9.0


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

    def test_generate_agent_metadata_testing_agent(self):
        """Test metadata for testing agent."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'typescript',
            'framework': 'react-nextjs'
        }

        metadata = session._generate_agent_metadata('testing')

        assert metadata['stack'] == ['typescript', 'react-nextjs']
        assert metadata['phase'] == 'implementation'
        assert 'test-execution' in metadata['capabilities']
        assert 'testing' in metadata['keywords']

    def test_generate_agent_metadata_repository_agent(self):
        """Test metadata for repository agent."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'csharp',
            'framework': 'aspnet-core'
        }

        metadata = session._generate_agent_metadata('repository')

        assert metadata['stack'] == ['csharp', 'aspnet-core']
        assert 'data-access' in metadata['capabilities']
        assert 'repository' in metadata['keywords']

    def test_generate_agent_metadata_service_agent(self):
        """Test metadata for service agent."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'java',
            'framework': 'spring-boot'
        }

        metadata = session._generate_agent_metadata('service')

        assert 'business-orchestration' in metadata['capabilities']
        assert 'service' in metadata['keywords']

    def test_generate_agent_metadata_generic_agent(self):
        """Test metadata for unknown agent type."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'rust',
            'framework': 'actix'
        }

        metadata = session._generate_agent_metadata('custom')

        assert metadata['stack'] == ['rust', 'actix']
        assert 'implementation' in metadata['capabilities']

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
        assert 'capabilities:' in formatted
        assert 'keywords:' in formatted

    def test_generate_agent_includes_metadata(self):
        """Test _generate_agent includes frontmatter metadata."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'python',
            'framework': 'fastapi'
        }

        agent_content = session._generate_agent('testing', 'test-agent')

        # Should have frontmatter
        assert agent_content.startswith('---')
        assert 'stack:' in agent_content
        assert 'phase:' in agent_content
        assert 'capabilities:' in agent_content


# =============================================================================
# TASK-INIT-009: Exit Codes
# =============================================================================

class TestExitCodes:
    """Test exit code support."""

    def test_calculate_exit_code_high_quality(self):
        """Test exit code 0 for high quality (≥8/10)."""
        session = TemplateInitQASession()

        exit_code = session._calculate_exit_code(9.0)
        assert exit_code == 0

    def test_calculate_exit_code_medium_quality(self):
        """Test exit code 1 for medium quality (6-7.9/10)."""
        session = TemplateInitQASession()

        exit_code = session._calculate_exit_code(7.0)
        assert exit_code == 1

    def test_calculate_exit_code_low_quality(self):
        """Test exit code 2 for low quality (<6/10)."""
        session = TemplateInitQASession()

        exit_code = session._calculate_exit_code(5.0)
        assert exit_code == 2

    def test_calculate_exit_code_boundary_cases(self):
        """Test exit code boundary values."""
        session = TemplateInitQASession()

        # Exactly 8.0 should be 0
        assert session._calculate_exit_code(8.0) == 0

        # Just below 8.0 should be 1
        assert session._calculate_exit_code(7.9) == 1

        # Exactly 6.0 should be 1
        assert session._calculate_exit_code(6.0) == 1

        # Just below 6.0 should be 2
        assert session._calculate_exit_code(5.9) == 2

    def test_run_returns_exit_code_tuple(self):
        """Test run() returns (answers, exit_code) tuple."""
        session = TemplateInitQASession()

        # Mock the Q&A flow to return without user interaction
        with patch.object(session, '_section1_identity'):
            with patch.object(session, '_section2_technology'):
                with patch.object(session, '_section3_architecture'):
                    with patch.object(session, '_section4_structure'):
                        with patch.object(session, '_section5_testing'):
                            with patch.object(session, '_section6_error_handling'):
                                with patch.object(session, '_section7_dependencies'):
                                    with patch.object(session, '_section9_additional_patterns'):
                                        with patch.object(session, '_section10_documentation'):
                                            with patch('inquirer.confirm', return_value=True):
                                                # Set required session data
                                                session._session_data = {
                                                    'template_name': 'test',
                                                    'template_purpose': 'test',
                                                    'primary_language': 'python',
                                                    'framework': 'fastapi',
                                                    'framework_version': '0.100.0',
                                                    'architecture_pattern': 'clean',
                                                    'domain_modeling': 'rich',
                                                    'layer_organization': 'single',
                                                    'standard_folders': ['src', 'tests'],
                                                    'unit_testing_framework': 'pytest',
                                                    'testing_scope': ['unit'],
                                                    'test_pattern': 'aaa',
                                                    'error_handling': 'result',
                                                    'validation_approach': 'fluent',
                                                    'dependency_injection': 'builtin',
                                                    'configuration_approach': 'json'
                                                }

                                                result = session.run()
                                                assert isinstance(result, tuple)
                                                assert len(result) == 2
                                                answers, exit_code = result
                                                assert isinstance(exit_code, int)
                                                assert 0 <= exit_code <= 3

    def test_display_exit_code_info(self, capsys):
        """Test exit code information display."""
        session = TemplateInitQASession()

        session._display_exit_code_info(0, 9.0)
        captured = capsys.readouterr()

        assert 'Exit Code: 0' in captured.out
        assert 'SUCCESS' in captured.out
        assert '9.0' in captured.out


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Test feature interactions and full workflow."""

    def test_boundary_sections_with_metadata(self):
        """Test boundary sections and metadata integration."""
        session = TemplateInitQASession()
        session._session_data = {'primary_language': 'python', 'framework': 'fastapi'}

        agent_content = session._generate_agent('testing')

        # Should have both frontmatter and boundaries
        assert agent_content.startswith('---')
        assert '## Boundaries' in agent_content
        assert '### ALWAYS' in agent_content
        assert '✅' in agent_content
        assert 'stack:' in agent_content

    def test_metadata_language_specific_keywords(self):
        """Test metadata includes language-specific keywords."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'typescript',
            'framework': 'react-nextjs'
        }

        metadata = session._generate_agent_metadata('api')

        assert 'typescript' in metadata['keywords']
        assert 'react-nextjs' in metadata['keywords']

    def test_validation_compatibility_with_manifest(self):
        """Test validation compatibility creates complete manifest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_path = Path(tmpdir) / "template"
            template_path.mkdir()

            # Pre-create manifest with some fields
            existing_manifest = {
                'name': 'test-template',
                'version': '1.0.0'
            }
            manifest_path = template_path / "template-manifest.json"
            manifest_path.write_text(json.dumps(existing_manifest, indent=2))

            session = TemplateInitQASession()
            session.ensure_validation_compatibility(template_path)

            # Read updated manifest
            manifest = json.loads(manifest_path.read_text())

            # Original fields preserved
            assert manifest['name'] == 'test-template'
            assert manifest['version'] == '1.0.0'

            # New fields added
            assert 'schema_version' in manifest
            assert 'complexity' in manifest
            assert 'confidence_score' in manifest


# =============================================================================
# Regression Tests
# =============================================================================

class TestRegression:
    """Test that existing functionality still works."""

    def test_existing_qa_workflow_unchanged(self):
        """Test Q&A workflow not broken by changes."""
        session = TemplateInitQASession()

        # Basic initialization should work
        assert session.answers is None
        assert session._session_data == {}
        assert session.no_create_agent_tasks is False

    def test_backward_compatibility_no_flags(self):
        """Test backward compatibility without new flags."""
        session = TemplateInitQASession()

        # Default settings should work
        assert session.no_create_agent_tasks is False

    def test_answers_to_dict_serialization(self):
        """Test GreenfieldAnswers serialization."""
        answers = GreenfieldAnswers(
            template_name='test',
            template_purpose='test',
            primary_language='python',
            framework='fastapi',
            framework_version='0.100.0',
            architecture_pattern='clean',
            domain_modeling='rich',
            layer_organization='single',
            standard_folders=['src', 'tests'],
            unit_testing_framework='pytest',
            testing_scope=['unit'],
            test_pattern='aaa',
            error_handling='result',
            validation_approach='fluent',
            dependency_injection='builtin',
            configuration_approach='json'
        )

        data = answers.to_dict()
        assert data['template_name'] == 'test'
        assert data['primary_language'] == 'python'

    def test_answers_from_dict_deserialization(self):
        """Test GreenfieldAnswers deserialization."""
        data = {
            'template_name': 'test',
            'template_purpose': 'test',
            'primary_language': 'python',
            'framework': 'fastapi',
            'framework_version': '0.100.0',
            'architecture_pattern': 'clean',
            'domain_modeling': 'rich',
            'layer_organization': 'single',
            'standard_folders': ['src', 'tests'],
            'unit_testing_framework': 'pytest',
            'testing_scope': ['unit'],
            'test_pattern': 'aaa',
            'error_handling': 'result',
            'validation_approach': 'fluent',
            'dependency_injection': 'builtin',
            'configuration_approach': 'json'
        }

        answers = GreenfieldAnswers.from_dict(data)
        assert answers.template_name == 'test'
        assert answers.primary_language == 'python'


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_boundary_validation_empty_sections(self):
        """Test validation handles empty sections."""
        boundaries = {
            'always': [],
            'never': [],
            'ask': []
        }

        is_valid, errors = validate_boundary_sections(boundaries)
        assert not is_valid
        assert len(errors) >= 3

    def test_metadata_no_framework(self):
        """Test metadata generation without framework."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'go',
            'framework': ''
        }

        metadata = session._generate_agent_metadata('api')

        assert metadata['stack'] == ['go']
        assert 'implementation' in metadata['capabilities'] or 'endpoint-implementation' in metadata['capabilities']

    def test_quality_score_minimal_answers(self):
        """Test quality scoring with minimal answers."""
        session = TemplateInitQASession()
        session._session_data = {
            'testing_scope': [],
            'error_handling': 'minimal'
        }

        score = session._calculate_placeholder_quality_score()
        # Should still return a valid score (base = 5.0)
        assert 5.0 <= score <= 6.0

    def test_agent_generation_preserves_boundaries_format(self):
        """Test agent generation preserves boundary format."""
        session = TemplateInitQASession()
        session._session_data = {'primary_language': 'rust'}

        agent = session._generate_agent('api', 'api-agent')

        # Count boundary sections
        assert agent.count('### ALWAYS') == 1
        assert agent.count('### NEVER') == 1
        assert agent.count('### ASK') == 1

        # Verify emojis present
        assert '✅' in agent
        assert '❌' in agent
        assert '⚠️' in agent


# =============================================================================
# Main Test Runner
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=installer.core.commands.lib.greenfield_qa_session'])
