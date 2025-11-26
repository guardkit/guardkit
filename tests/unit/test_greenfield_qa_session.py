"""
Unit tests for greenfield_qa_session module.

Tests cover GreenfieldAnswers dataclass and TemplateInitQASession workflow
including all 10 sections, conditional logic, and session persistence.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import from installer/global/commands/lib
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "global" / "commands" / "lib"))

from greenfield_qa_session import (
    GreenfieldAnswers,
    TemplateInitQASession,
    INQUIRER_AVAILABLE,
    generate_boundary_sections,
    validate_boundary_sections
)


class TestGreenfieldAnswers:
    """Test GreenfieldAnswers dataclass."""

    def test_greenfield_answers_initialization(self):
        """Test GreenfieldAnswers can be initialized with all required fields."""
        answers = GreenfieldAnswers(
            template_name="test-template",
            template_purpose="production",
            primary_language="csharp",
            framework="maui",
            framework_version="latest",
            architecture_pattern="mvvm",
            domain_modeling="rich",
            layer_organization="single",
            standard_folders=["src", "tests"],
            unit_testing_framework="auto",
            testing_scope=["unit", "integration"],
            test_pattern="aaa",
            error_handling="result",
            validation_approach="fluent",
            dependency_injection="builtin",
            configuration_approach="both"
        )

        assert answers.template_name == "test-template"
        assert answers.template_purpose == "production"
        assert answers.primary_language == "csharp"
        assert answers.framework == "maui"
        assert answers.framework_version == "latest"
        assert answers.architecture_pattern == "mvvm"
        assert answers.domain_modeling == "rich"
        assert answers.layer_organization == "single"
        assert answers.standard_folders == ["src", "tests"]
        assert answers.unit_testing_framework == "auto"
        assert answers.testing_scope == ["unit", "integration"]
        assert answers.test_pattern == "aaa"
        assert answers.error_handling == "result"
        assert answers.validation_approach == "fluent"
        assert answers.dependency_injection == "builtin"
        assert answers.configuration_approach == "both"

    def test_greenfield_answers_optional_fields(self):
        """Test optional fields default to None."""
        answers = GreenfieldAnswers(
            template_name="test",
            template_purpose="prototype",
            primary_language="python",
            framework="fastapi",
            framework_version="latest",
            architecture_pattern="clean",
            domain_modeling="functional",
            layer_organization="by-layer",
            standard_folders=["src"],
            unit_testing_framework="pytest",
            testing_scope=["unit"],
            test_pattern="bdd",
            error_handling="exceptions",
            validation_approach="minimal",
            dependency_injection="builtin",
            configuration_approach="env"
        )

        assert answers.ui_architecture is None
        assert answers.navigation_pattern is None
        assert answers.data_access is None
        assert answers.api_pattern is None
        assert answers.state_management is None
        assert answers.documentation_paths is None
        assert answers.documentation_text is None
        assert answers.documentation_urls is None
        assert answers.documentation_usage is None

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        answers = GreenfieldAnswers(
            template_name="test-template",
            template_purpose="production",
            primary_language="typescript",
            framework="react-nextjs",
            framework_version="latest",
            architecture_pattern="clean",
            domain_modeling="rich",
            layer_organization="by-feature",
            standard_folders=["src", "tests"],
            unit_testing_framework="vitest",
            testing_scope=["unit"],
            test_pattern="aaa",
            error_handling="result",
            validation_approach="manual",
            dependency_injection="builtin",
            configuration_approach="json",
            ui_architecture="component",
            navigation_pattern="recommended"
        )

        data = answers.to_dict()

        assert isinstance(data, dict)
        assert data["template_name"] == "test-template"
        assert data["template_purpose"] == "production"
        assert data["primary_language"] == "typescript"
        assert data["framework"] == "react-nextjs"
        assert data["ui_architecture"] == "component"
        assert data["navigation_pattern"] == "recommended"

    def test_to_dict_with_paths(self):
        """Test to_dict converts Path objects to strings."""
        answers = GreenfieldAnswers(
            template_name="test",
            template_purpose="prototype",
            primary_language="python",
            framework="fastapi",
            framework_version="latest",
            architecture_pattern="clean",
            domain_modeling="functional",
            layer_organization="single",
            standard_folders=["src"],
            unit_testing_framework="pytest",
            testing_scope=["unit"],
            test_pattern="bdd",
            error_handling="exceptions",
            validation_approach="minimal",
            dependency_injection="builtin",
            configuration_approach="env",
            documentation_paths=[Path("/docs/adr.md"), Path("/docs/standards.md")]
        )

        data = answers.to_dict()
        assert isinstance(data["documentation_paths"], list)
        assert all(isinstance(p, str) for p in data["documentation_paths"])
        assert "/docs/adr.md" in data["documentation_paths"]
        assert "/docs/standards.md" in data["documentation_paths"]

    def test_from_dict_reconstruction(self):
        """Test reconstruction from dictionary."""
        original_data = {
            "template_name": "test-template",
            "template_purpose": "production",
            "primary_language": "csharp",
            "framework": "maui",
            "framework_version": "latest",
            "architecture_pattern": "mvvm",
            "domain_modeling": "rich",
            "layer_organization": "single",
            "standard_folders": ["src", "tests"],
            "unit_testing_framework": "auto",
            "testing_scope": ["unit"],
            "test_pattern": "aaa",
            "error_handling": "result",
            "validation_approach": "fluent",
            "dependency_injection": "builtin",
            "configuration_approach": "both",
            "ui_architecture": "mvvm",
            "navigation_pattern": "recommended",
            "documentation_paths": ["/docs/adr.md"]
        }

        answers = GreenfieldAnswers.from_dict(original_data)

        assert answers.template_name == "test-template"
        assert answers.framework == "maui"
        assert answers.ui_architecture == "mvvm"
        assert isinstance(answers.documentation_paths[0], Path)
        assert str(answers.documentation_paths[0]) == "/docs/adr.md"

    def test_roundtrip_serialization(self):
        """Test to_dict and from_dict roundtrip."""
        original = GreenfieldAnswers(
            template_name="roundtrip-test",
            template_purpose="team_standards",
            primary_language="go",
            framework="gin",
            framework_version="v1.9.0",
            architecture_pattern="hexagonal",
            domain_modeling="functional",
            layer_organization="by-layer",
            standard_folders=["src", "tests", "docs"],
            unit_testing_framework="testing",
            testing_scope=["unit", "integration"],
            test_pattern="aaa",
            error_handling="result",
            validation_approach="manual",
            dependency_injection="manual",
            configuration_approach="env",
            api_pattern="rest"
        )

        # Convert to dict and back
        data = original.to_dict()
        reconstructed = GreenfieldAnswers.from_dict(data)

        assert reconstructed.template_name == original.template_name
        assert reconstructed.template_purpose == original.template_purpose
        assert reconstructed.primary_language == original.primary_language
        assert reconstructed.framework == original.framework
        assert reconstructed.framework_version == original.framework_version
        assert reconstructed.standard_folders == original.standard_folders
        assert reconstructed.testing_scope == original.testing_scope


@pytest.mark.skipif(not INQUIRER_AVAILABLE, reason="inquirer not installed")
class TestTemplateInitQASession:
    """Test TemplateInitQASession workflow."""

    def test_session_initialization(self):
        """Test session can be initialized."""
        session = TemplateInitQASession()
        assert session.answers is None
        assert session._session_data == {}

    def test_is_ui_framework_detection(self):
        """Test UI framework detection."""
        session = TemplateInitQASession()

        # UI frameworks
        assert session._is_ui_framework("maui") is True
        assert session._is_ui_framework("blazor") is True
        assert session._is_ui_framework("wpf") is True
        assert session._is_ui_framework("react-nextjs") is True
        assert session._is_ui_framework("react-vite") is True
        assert session._is_ui_framework("angular") is True
        assert session._is_ui_framework("vue") is True

        # Non-UI frameworks
        assert session._is_ui_framework("aspnet-core") is False
        assert session._is_ui_framework("fastapi") is False
        assert session._is_ui_framework("nestjs") is False
        assert session._is_ui_framework("express") is False

    def test_is_backend_framework_detection(self):
        """Test backend framework detection."""
        session = TemplateInitQASession()

        # Backend frameworks
        assert session._is_backend_framework("aspnet-core") is True
        assert session._is_backend_framework("nestjs") is True
        assert session._is_backend_framework("express") is True
        assert session._is_backend_framework("fastapi") is True
        assert session._is_backend_framework("django") is True
        assert session._is_backend_framework("flask") is True

        # Non-backend frameworks
        assert session._is_backend_framework("maui") is False
        assert session._is_backend_framework("blazor") is False
        assert session._is_backend_framework("react-nextjs") is False

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section1_identity(self, mock_prompt):
        """Test Section 1: Template Identity."""
        mock_prompt.return_value = {
            "template_name": "my-template",
            "template_purpose": "production"
        }

        session = TemplateInitQASession()
        session._section1_identity()

        assert session._session_data["template_name"] == "my-template"
        assert session._session_data["template_purpose"] == "production"
        assert mock_prompt.called

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section3_architecture(self, mock_prompt):
        """Test Section 3: Architecture."""
        mock_prompt.return_value = {
            "architecture_pattern": "mvvm",
            "domain_modeling": "rich"
        }

        session = TemplateInitQASession()
        session._section3_architecture()

        assert session._session_data["architecture_pattern"] == "mvvm"
        assert session._session_data["domain_modeling"] == "rich"

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section4_structure(self, mock_prompt):
        """Test Section 4: Project Structure."""
        mock_prompt.return_value = {
            "layer_organization": "single",
            "standard_folders": ["src", "tests"]
        }

        session = TemplateInitQASession()
        session._section4_structure()

        assert session._session_data["layer_organization"] == "single"
        assert session._session_data["standard_folders"] == ["src", "tests"]

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section5_testing(self, mock_prompt):
        """Test Section 5: Testing Strategy."""
        # Mock multiple prompts in sequence
        mock_prompt.side_effect = [
            {"unit_testing_framework_choice": "auto"},
            {"testing_scope": ["unit", "integration"], "test_pattern": "aaa"}
        ]

        session = TemplateInitQASession()
        session._section5_testing()

        assert session._session_data["unit_testing_framework"] == "auto"
        assert session._session_data["testing_scope"] == ["unit", "integration"]
        assert session._session_data["test_pattern"] == "aaa"

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section6_error_handling(self, mock_prompt):
        """Test Section 6: Error Handling."""
        mock_prompt.return_value = {
            "error_handling": "result",
            "validation_approach": "fluent"
        }

        session = TemplateInitQASession()
        session._section6_error_handling()

        assert session._session_data["error_handling"] == "result"
        assert session._session_data["validation_approach"] == "fluent"

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section7_dependencies(self, mock_prompt):
        """Test Section 7: Dependency Management."""
        mock_prompt.return_value = {
            "dependency_injection": "builtin",
            "configuration_approach": "both"
        }

        session = TemplateInitQASession()
        session._section7_dependencies()

        assert session._session_data["dependency_injection"] == "builtin"
        assert session._session_data["configuration_approach"] == "both"

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section8_ui_navigation(self, mock_prompt):
        """Test Section 8: UI/Navigation."""
        mock_prompt.return_value = {
            "ui_architecture": "mvvm",
            "navigation_pattern": "recommended"
        }

        session = TemplateInitQASession()
        session._section8_ui_navigation()

        assert session._session_data["ui_architecture"] == "mvvm"
        assert session._session_data["navigation_pattern"] == "recommended"

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section9_additional_patterns_with_data_access(self, mock_prompt):
        """Test Section 9: Additional Patterns with data access."""
        mock_prompt.side_effect = [
            {"needs_data_access": True},
            {"data_access": "repository"}
        ]

        session = TemplateInitQASession()
        session._session_data["framework"] = "console"  # Non-backend, non-UI
        session._section9_additional_patterns()

        assert session._session_data["data_access"] == "repository"
        assert session._session_data["api_pattern"] is None
        assert session._session_data["state_management"] is None

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section9_with_backend_framework(self, mock_prompt):
        """Test Section 9 with backend framework triggers API questions."""
        mock_prompt.side_effect = [
            {"needs_data_access": False},
            {"api_pattern": "rest"}
        ]

        session = TemplateInitQASession()
        session._session_data["framework"] = "fastapi"  # Backend framework
        session._section9_additional_patterns()

        assert session._session_data["data_access"] is None
        assert session._session_data["api_pattern"] == "rest"

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section9_with_ui_framework(self, mock_prompt):
        """Test Section 9 with UI framework triggers state management questions."""
        mock_prompt.side_effect = [
            {"needs_data_access": False},
            {"state_management_choice": "recommended"}
        ]

        session = TemplateInitQASession()
        session._session_data["framework"] = "react-nextjs"  # UI framework
        session._section9_additional_patterns()

        assert session._session_data["state_management"] == "recommended"

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section10_documentation_with_paths(self, mock_prompt):
        """Test Section 10: Documentation with file paths."""
        mock_prompt.side_effect = [
            {"documentation_input_type": "paths"},
            {"doc_paths": "/docs/adr.md,/docs/standards.md"},
            {"documentation_usage": "strict"}
        ]

        session = TemplateInitQASession()
        session._section10_documentation()

        assert session._session_data["documentation_paths"] is not None
        assert len(session._session_data["documentation_paths"]) == 2
        assert all(isinstance(p, Path) for p in session._session_data["documentation_paths"])

    @patch('greenfield_qa_session.inquirer.prompt')
    def test_section10_documentation_none(self, mock_prompt):
        """Test Section 10: No documentation."""
        mock_prompt.return_value = {"documentation_input_type": "none"}

        session = TemplateInitQASession()
        session._section10_documentation()

        assert session._session_data["documentation_paths"] is None
        assert session._session_data["documentation_text"] is None
        assert session._session_data["documentation_urls"] is None
        assert session._session_data["documentation_usage"] is None

    def test_save_session(self, tmp_path):
        """Test session persistence."""
        session_file = tmp_path / "test-session.json"

        answers = GreenfieldAnswers(
            template_name="save-test",
            template_purpose="prototype",
            primary_language="python",
            framework="fastapi",
            framework_version="latest",
            architecture_pattern="clean",
            domain_modeling="functional",
            layer_organization="single",
            standard_folders=["src"],
            unit_testing_framework="pytest",
            testing_scope=["unit"],
            test_pattern="bdd",
            error_handling="exceptions",
            validation_approach="minimal",
            dependency_injection="builtin",
            configuration_approach="env"
        )

        session = TemplateInitQASession()
        session.answers = answers
        session.save_session(session_file)

        assert session_file.exists()
        data = json.loads(session_file.read_text())
        assert data["template_name"] == "save-test"
        assert data["primary_language"] == "python"

    def test_load_session(self, tmp_path):
        """Test session loading."""
        session_file = tmp_path / "test-session.json"

        # Create test session data
        test_data = {
            "template_name": "load-test",
            "template_purpose": "production",
            "primary_language": "csharp",
            "framework": "maui",
            "framework_version": "latest",
            "architecture_pattern": "mvvm",
            "domain_modeling": "rich",
            "layer_organization": "single",
            "standard_folders": ["src", "tests"],
            "unit_testing_framework": "auto",
            "testing_scope": ["unit"],
            "test_pattern": "aaa",
            "error_handling": "result",
            "validation_approach": "fluent",
            "dependency_injection": "builtin",
            "configuration_approach": "both"
        }

        session_file.write_text(json.dumps(test_data, indent=2))

        # Load session
        answers = TemplateInitQASession.load_session(session_file)

        assert answers is not None
        assert answers.template_name == "load-test"
        assert answers.primary_language == "csharp"
        assert answers.framework == "maui"

    def test_load_session_file_not_found(self, tmp_path):
        """Test loading non-existent session returns None."""
        session_file = tmp_path / "nonexistent.json"
        answers = TemplateInitQASession.load_session(session_file)
        assert answers is None

    @patch('greenfield_qa_session.inquirer.prompt')
    @patch('greenfield_qa_session.inquirer.confirm')
    def test_full_run_success(self, mock_confirm, mock_prompt):
        """Test full Q&A session run successfully."""
        # Mock all sections
        mock_prompt.side_effect = [
            # Section 1
            {"template_name": "full-test", "template_purpose": "production"},
            # Section 2 - language
            {"primary_language": "python"},
            # Section 2 - framework
            {"framework": "fastapi"},
            # Section 2 - version
            {"framework_version_choice": "latest"},
            # Section 3
            {"architecture_pattern": "clean", "domain_modeling": "functional"},
            # Section 4
            {"layer_organization": "by-layer", "standard_folders": ["src", "tests"]},
            # Section 5 - framework
            {"unit_testing_framework_choice": "auto"},
            # Section 5 - scope/pattern
            {"testing_scope": ["unit"], "test_pattern": "aaa"},
            # Section 6
            {"error_handling": "exceptions", "validation_approach": "minimal"},
            # Section 7
            {"dependency_injection": "builtin", "configuration_approach": "env"},
            # Section 9 - data access
            {"needs_data_access": False},
            # Section 9 - API pattern (backend framework)
            {"api_pattern": "rest"},
            # Section 10 - documentation
            {"documentation_input_type": "none"}
        ]

        # Mock confirmation
        mock_confirm.return_value = True

        session = TemplateInitQASession()
        answers = session.run()

        assert answers is not None
        assert answers.template_name == "full-test"
        assert answers.primary_language == "python"
        assert answers.framework == "fastapi"

    @patch('greenfield_qa_session.inquirer.prompt')
    @patch('greenfield_qa_session.inquirer.confirm')
    def test_full_run_cancelled(self, mock_confirm, mock_prompt):
        """Test Q&A session cancelled by user."""
        # Mock minimal sections
        mock_prompt.side_effect = [
            {"template_name": "cancel-test", "template_purpose": "prototype"},
            {"primary_language": "python"},
            {"framework": "fastapi"},
            {"framework_version_choice": "latest"},
            {"architecture_pattern": "simple", "domain_modeling": "data-centric"},
            {"layer_organization": "single", "standard_folders": ["src"]},
            {"unit_testing_framework_choice": "auto"},
            {"testing_scope": ["unit"], "test_pattern": "none"},
            {"error_handling": "minimal", "validation_approach": "minimal"},
            {"dependency_injection": "none", "configuration_approach": "minimal"},
            {"needs_data_access": False},
            {"api_pattern": "rest"},
            {"documentation_input_type": "none"}
        ]

        # User cancels at confirmation
        mock_confirm.return_value = False

        session = TemplateInitQASession()
        answers = session.run()

        assert answers is None


@pytest.mark.skipif(not INQUIRER_AVAILABLE, reason="inquirer not installed")
class TestConditionalSections:
    """Test conditional section logic."""

    @patch('greenfield_qa_session.inquirer.prompt')
    @patch('greenfield_qa_session.inquirer.confirm')
    def test_ui_framework_triggers_section8(self, mock_confirm, mock_prompt):
        """Test UI framework triggers UI/Navigation section."""
        # Setup session with UI framework
        mock_prompt.side_effect = [
            {"template_name": "ui-test", "template_purpose": "prototype"},
            {"primary_language": "csharp"},
            {"framework": "maui"},
            {"framework_version_choice": "latest"},
            {"architecture_pattern": "mvvm", "domain_modeling": "rich"},
            {"layer_organization": "single", "standard_folders": ["src", "tests"]},
            {"unit_testing_framework_choice": "auto"},
            {"testing_scope": ["unit"], "test_pattern": "aaa"},
            {"error_handling": "result", "validation_approach": "fluent"},
            {"dependency_injection": "builtin", "configuration_approach": "json"},
            # Section 8 should be triggered
            {"ui_architecture": "mvvm", "navigation_pattern": "recommended"},
            # Section 9
            {"needs_data_access": False},
            {"state_management_choice": "recommended"},
            # Section 10
            {"documentation_input_type": "none"}
        ]

        mock_confirm.return_value = True

        session = TemplateInitQASession()
        answers = session.run()

        assert answers is not None
        assert answers.framework == "maui"
        assert answers.ui_architecture == "mvvm"
        assert answers.navigation_pattern == "recommended"

    @patch('greenfield_qa_session.inquirer.prompt')
    @patch('greenfield_qa_session.inquirer.confirm')
    def test_backend_framework_triggers_api_questions(self, mock_confirm, mock_prompt):
        """Test backend framework triggers API pattern questions."""
        mock_prompt.side_effect = [
            {"template_name": "backend-test", "template_purpose": "production"},
            {"primary_language": "typescript"},
            {"framework": "nestjs"},
            {"framework_version_choice": "latest"},
            {"architecture_pattern": "clean", "domain_modeling": "rich"},
            {"layer_organization": "by-layer", "standard_folders": ["src", "tests"]},
            {"unit_testing_framework_choice": "auto"},
            {"testing_scope": ["unit", "integration"], "test_pattern": "bdd"},
            {"error_handling": "result", "validation_approach": "manual"},
            {"dependency_injection": "builtin", "configuration_approach": "both"},
            # Section 9 - API pattern should be triggered
            {"needs_data_access": True},
            {"data_access": "repository"},
            {"api_pattern": "repr"},
            # Section 10
            {"documentation_input_type": "none"}
        ]

        mock_confirm.return_value = True

        session = TemplateInitQASession()
        answers = session.run()

        assert answers is not None
        assert answers.framework == "nestjs"
        assert answers.api_pattern == "repr"


@pytest.mark.skipif(not INQUIRER_AVAILABLE, reason="inquirer not installed")
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_session_without_inquirer_raises_error(self):
        """Test session raises error if inquirer not available."""
        with patch('greenfield_qa_session.INQUIRER_AVAILABLE', False):
            with pytest.raises(ImportError, match="inquirer library not installed"):
                TemplateInitQASession()

    def test_save_session_without_answers(self, tmp_path, capsys):
        """Test save_session with no answers prints warning."""
        session = TemplateInitQASession()
        session.save_session(tmp_path / "test.json")

        captured = capsys.readouterr()
        assert "No answers to save" in captured.out

    def test_from_dict_without_paths(self):
        """Test from_dict handles missing documentation_paths gracefully."""
        data = {
            "template_name": "test",
            "template_purpose": "prototype",
            "primary_language": "python",
            "framework": "fastapi",
            "framework_version": "latest",
            "architecture_pattern": "clean",
            "domain_modeling": "functional",
            "layer_organization": "single",
            "standard_folders": ["src"],
            "unit_testing_framework": "pytest",
            "testing_scope": ["unit"],
            "test_pattern": "bdd",
            "error_handling": "exceptions",
            "validation_approach": "minimal",
            "dependency_injection": "builtin",
            "configuration_approach": "env"
        }

        answers = GreenfieldAnswers.from_dict(data)
        assert answers.documentation_paths is None


class TestBoundarySections:
    """Test boundary section generation and validation (TASK-INIT-001)."""

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

        assert len(boundaries['always']) == 5
        assert len(boundaries['never']) == 5
        assert len(boundaries['ask']) == 3

        # Verify repository-specific content
        assert any('DI pattern' in rule for rule in boundaries['always'])
        assert any('ErrorOr<T>' in rule for rule in boundaries['always'])
        assert any('SQL injection' in rule for rule in boundaries['never'])

    def test_generate_boundary_sections_api_agent(self):
        """Test boundary generation for API agent."""
        boundaries = generate_boundary_sections('api', 'typescript')

        assert len(boundaries['always']) == 5
        assert len(boundaries['never']) == 5
        assert len(boundaries['ask']) == 3

        # Verify API-specific content
        assert any('Validate all input' in rule for rule in boundaries['always'])
        assert any('HTTP status codes' in rule for rule in boundaries['always'])
        assert any('authentication' in rule for rule in boundaries['never'])

    def test_generate_boundary_sections_service_agent(self):
        """Test boundary generation for service agent."""
        boundaries = generate_boundary_sections('service', 'python')

        assert len(boundaries['always']) == 5
        assert len(boundaries['never']) == 5
        assert len(boundaries['ask']) == 3

        # Verify service-specific content
        assert any('constructor' in rule for rule in boundaries['always'])
        assert any('python naming conventions' in rule.lower() for rule in boundaries['always'])

    def test_generate_boundary_sections_generic_agent(self):
        """Test boundary generation for unknown agent type."""
        boundaries = generate_boundary_sections('unknown', 'go')

        assert len(boundaries['always']) == 5
        assert len(boundaries['never']) == 5
        assert len(boundaries['ask']) == 3

        # Verify generic content with technology
        assert any('go best practices' in rule.lower() for rule in boundaries['always'])

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
            'always': ['✅ Rule 1', '✅ Rule 2'],  # Too few (need 5-7)
            'never': ['❌ Rule'] * 10,  # Too many (need 5-7)
            'ask': []  # Too few (need 3-5)
        }

        is_valid, errors = validate_boundary_sections(boundaries)
        assert not is_valid
        assert len(errors) >= 3
        assert any('ALWAYS' in error for error in errors)
        assert any('NEVER' in error for error in errors)
        assert any('ASK' in error for error in errors)

    def test_validate_boundary_sections_missing_emoji(self):
        """Test validation catches missing emoji prefixes."""
        boundaries = {
            'always': ['Rule without emoji'] + ['✅ Rule ' + str(i) for i in range(4)],
            'never': ['❌ Rule ' + str(i) for i in range(5)],
            'ask': ['⚠️ Scenario ' + str(i) for i in range(3)]
        }

        is_valid, errors = validate_boundary_sections(boundaries)
        assert not is_valid
        assert any('missing ✅ prefix' in error for error in errors)

    def test_validate_boundary_sections_edge_cases(self):
        """Test validation with edge case counts."""
        # Minimum valid counts
        boundaries_min = {
            'always': ['✅ Rule ' + str(i) for i in range(5)],
            'never': ['❌ Rule ' + str(i) for i in range(5)],
            'ask': ['⚠️ Scenario ' + str(i) for i in range(3)]
        }
        is_valid, errors = validate_boundary_sections(boundaries_min)
        assert is_valid

        # Maximum valid counts
        boundaries_max = {
            'always': ['✅ Rule ' + str(i) for i in range(7)],
            'never': ['❌ Rule ' + str(i) for i in range(7)],
            'ask': ['⚠️ Scenario ' + str(i) for i in range(5)]
        }
        is_valid, errors = validate_boundary_sections(boundaries_max)
        assert is_valid


@pytest.mark.skipif(not INQUIRER_AVAILABLE, reason="inquirer not installed")
class TestAgentGeneration:
    """Test agent generation with boundaries (TASK-INIT-001)."""

    def test_generated_agents_include_boundaries(self):
        """Test that generated agents include valid boundaries."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'python',
            'framework': 'fastapi'
        }

        agent_content = session._generate_agent('testing', 'testing-agent')

        assert '## Boundaries' in agent_content
        assert '### ALWAYS' in agent_content
        assert '### NEVER' in agent_content
        assert '### ASK' in agent_content
        assert '✅' in agent_content
        assert '❌' in agent_content
        assert '⚠️' in agent_content

    def test_generate_agent_with_different_types(self):
        """Test agent generation for different agent types."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'typescript',
            'framework': 'react-nextjs'
        }

        for agent_type in ['testing', 'repository', 'api', 'service']:
            agent_content = session._generate_agent(agent_type)
            assert '## Boundaries' in agent_content
            assert f'type: {agent_type}' in agent_content

    def test_generate_agent_boundary_placement(self):
        """Test boundaries are placed after Quick Start section."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'csharp',
            'framework': 'maui'
        }

        agent_content = session._generate_agent('repository')

        # Boundaries should come after Quick Start
        quick_start_idx = agent_content.find('## Quick Start')
        boundaries_idx = agent_content.find('## Boundaries')

        assert quick_start_idx > 0
        assert boundaries_idx > quick_start_idx

    def test_generate_agent_validates_boundaries(self, capsys):
        """Test agent generation validates boundaries and shows warnings."""
        session = TemplateInitQASession()
        session._session_data = {
            'primary_language': 'python',
            'framework': 'fastapi'
        }

        # This should not produce warnings as boundaries are valid
        agent_content = session._generate_agent('testing')

        captured = capsys.readouterr()
        # No validation warnings should be printed for valid boundaries
        assert '⚠️ Boundary validation warnings' not in captured.out

    def test_generate_base_agent_content(self):
        """Test base agent content generation."""
        session = TemplateInitQASession()

        content = session._generate_base_agent_content(
            'testing',
            'my-testing-agent',
            'python',
            'fastapi'
        )

        assert 'name: my-testing-agent' in content
        assert 'type: testing' in content
        assert 'technology: python' in content
        assert 'framework: fastapi' in content
        assert '## Quick Start' in content

    def test_integration_with_existing_qa_workflow(self):
        """Ensure boundary generation doesn't break existing Q&A workflow."""
        session = TemplateInitQASession()

        # Mock Q&A responses
        with patch('greenfield_qa_session.inquirer.prompt') as mock_prompt:
            mock_prompt.return_value = {
                'template_name': 'test',
                'template_purpose': 'quick_start'
            }
            session._section1_identity()

        assert session._session_data['template_name'] == 'test'

        # Now test agent generation works with this data
        session._session_data['primary_language'] = 'python'
        session._session_data['framework'] = 'fastapi'

        agent_content = session._generate_agent('testing')
        assert '## Boundaries' in agent_content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=greenfield_qa_session", "--cov-report=term-missing"])
