"""
Unit tests for AI template generator stub

Tests the minimal AI generator implementation for TASK-011.
"""

import pytest
import sys
from pathlib import Path

# Add installer path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"))

from template_init.ai_generator import AITemplateGenerator
from template_init.models import GreenfieldTemplate
from template_init.errors import TemplateGenerationError


class MockAnswers:
    """Mock GreenfieldAnswers for testing"""

    def __init__(self):
        self.template_name = "Test Template"
        self.template_purpose = "Test template for unit testing"
        self.primary_language = "Python"
        self.framework = "FastAPI"
        self.framework_version = "0.100.0"
        self.architecture_pattern = "Clean Architecture"
        self.domain_modeling = "DDD"
        self.unit_testing_framework = "pytest"
        self.test_pattern = "AAA"
        self.error_handling = "Result[T]"


class TestAITemplateGenerator:
    """Test AITemplateGenerator stub implementation"""

    def test_create_generator(self):
        """Test creating generator instance"""
        generator = AITemplateGenerator()
        assert generator is not None
        assert generator.greenfield_context is None

    def test_create_generator_with_context(self):
        """Test creating generator with greenfield context"""
        mock_answers = MockAnswers()
        generator = AITemplateGenerator(greenfield_context=mock_answers)
        assert generator.greenfield_context is mock_answers

    def test_generate_template(self):
        """Test generating template from answers"""
        mock_answers = MockAnswers()
        generator = AITemplateGenerator()

        template = generator.generate(mock_answers)

        assert isinstance(template, GreenfieldTemplate)
        assert template.name == "test-template"  # Sanitized name
        assert isinstance(template.manifest, dict)
        assert isinstance(template.settings, dict)
        assert isinstance(template.claude_md, str)
        assert isinstance(template.project_structure, dict)
        assert isinstance(template.code_templates, dict)
        assert template.inferred_analysis is not None

    def test_sanitize_name(self):
        """Test name sanitization"""
        generator = AITemplateGenerator()

        # Test various inputs
        assert generator._sanitize_name("Test Template") == "test-template"
        assert generator._sanitize_name("My Company Template") == "my-company-template"
        assert generator._sanitize_name("test-template") == "test-template"
        assert generator._sanitize_name("Test  Template") == "test-template"  # Multiple spaces
        assert generator._sanitize_name("Test_Template") == "testtemplate"
        assert generator._sanitize_name("Test@#$Template") == "testtemplate"
        assert generator._sanitize_name("-test-template-") == "test-template"  # Trim hyphens

    def test_generate_manifest(self):
        """Test manifest generation"""
        mock_answers = MockAnswers()
        generator = AITemplateGenerator()

        manifest = generator._generate_manifest(mock_answers)

        assert isinstance(manifest, dict)
        assert manifest["name"] == "test-template"
        assert manifest["version"] == "1.0.0"
        assert manifest["description"] == mock_answers.template_purpose
        assert "technology_stack" in manifest
        assert manifest["technology_stack"]["primary_language"] == "Python"
        assert manifest["technology_stack"]["framework"] == "FastAPI"
        assert "architecture" in manifest
        assert manifest["architecture"]["pattern"] == "Clean Architecture"
        assert "testing" in manifest
        assert manifest["testing"]["framework"] == "pytest"
        assert manifest["stub_implementation"] is True

    def test_generate_settings(self):
        """Test settings generation"""
        mock_answers = MockAnswers()
        generator = AITemplateGenerator()

        settings = generator._generate_settings(mock_answers)

        assert isinstance(settings, dict)
        assert settings["template"]["name"] == "test-template"
        assert settings["template"]["type"] == "greenfield"
        assert settings["technology"]["language"] == "Python"
        assert settings["technology"]["framework"] == "FastAPI"
        assert settings["architecture"]["pattern"] == "Clean Architecture"
        assert settings["testing"]["framework"] == "pytest"
        assert settings["testing"]["coverage_threshold"] == 80
        assert settings["quality_gates"]["compilation"] == "required"
        assert settings["quality_gates"]["tests_pass"] == "required"

    def test_generate_claude_md(self):
        """Test CLAUDE.md generation"""
        mock_answers = MockAnswers()
        generator = AITemplateGenerator()

        claude_md = generator._generate_claude_md(mock_answers)

        assert isinstance(claude_md, str)
        assert len(claude_md) > 0
        assert "Test Template" in claude_md
        assert "Python" in claude_md
        assert "FastAPI" in claude_md
        assert "Clean Architecture" in claude_md
        assert "pytest" in claude_md
        assert "GuardKit" in claude_md
        assert "#" in claude_md  # Has markdown headers

    def test_generate_project_structure_python(self):
        """Test project structure for Python"""
        mock_answers = MockAnswers()
        mock_answers.primary_language = "Python"
        generator = AITemplateGenerator()

        structure = generator._generate_project_structure(mock_answers)

        assert isinstance(structure, dict)
        assert "src" in structure
        assert "tests" in structure
        assert "docs" in structure
        assert "README.md" in structure
        assert "requirements.txt" in structure

    def test_generate_project_structure_typescript(self):
        """Test project structure for TypeScript"""
        mock_answers = MockAnswers()
        mock_answers.primary_language = "TypeScript"
        generator = AITemplateGenerator()

        structure = generator._generate_project_structure(mock_answers)

        assert isinstance(structure, dict)
        assert "src" in structure
        assert "tests" in structure
        assert "package.json" in structure

    def test_generate_project_structure_csharp(self):
        """Test project structure for C#"""
        mock_answers = MockAnswers()
        mock_answers.primary_language = "C#"
        generator = AITemplateGenerator()

        structure = generator._generate_project_structure(mock_answers)

        assert isinstance(structure, dict)
        assert "src" in structure
        assert "tests" in structure
        assert "*.sln" in structure

    def test_generate_project_structure_unknown(self):
        """Test project structure for unknown language"""
        mock_answers = MockAnswers()
        mock_answers.primary_language = "Go"
        generator = AITemplateGenerator()

        structure = generator._generate_project_structure(mock_answers)

        # Should return generic structure
        assert isinstance(structure, dict)
        assert "src" in structure
        assert "tests" in structure
        assert "docs" in structure
        assert "README.md" in structure

    def test_generate_code_templates(self):
        """Test code templates generation (stub returns empty)"""
        mock_answers = MockAnswers()
        generator = AITemplateGenerator()

        templates = generator._generate_code_templates(mock_answers)

        assert isinstance(templates, dict)
        assert len(templates) == 0  # Stub returns empty dict

    def test_create_inferred_analysis(self):
        """Test inferred analysis creation"""
        mock_answers = MockAnswers()
        generator = AITemplateGenerator()

        analysis = generator._create_inferred_analysis(mock_answers)

        assert analysis is not None
        assert hasattr(analysis, "primary_language")
        assert analysis.primary_language == "Python"
        assert hasattr(analysis, "framework")
        assert analysis.framework == "FastAPI"
        assert hasattr(analysis, "architecture_pattern")
        assert analysis.architecture_pattern == "Clean Architecture"
        assert hasattr(analysis, "testing_framework")
        assert analysis.testing_framework == "pytest"
        assert hasattr(analysis, "project_type")
        assert hasattr(analysis, "complexity")

    def test_generate_with_minimal_answers(self):
        """Test generation with minimal answers"""

        class MinimalAnswers:
            template_name = "minimal"
            template_purpose = "minimal test"
            primary_language = "Python"
            framework = "Flask"
            architecture_pattern = "MVC"
            unit_testing_framework = "unittest"
            error_handling = "Exceptions"

        minimal = MinimalAnswers()
        generator = AITemplateGenerator()

        template = generator.generate(minimal)

        assert template.name == "minimal"
        assert template.manifest["technology_stack"]["framework"] == "Flask"
        assert template.settings["architecture"]["pattern"] == "MVC"

    def test_generate_with_special_characters(self):
        """Test generation with special characters in name"""

        class SpecialAnswers:
            template_name = "Test@#$%Template!!!"
            template_purpose = "test"
            primary_language = "Python"
            framework = "Django"
            architecture_pattern = "MVT"
            unit_testing_framework = "pytest"
            error_handling = "Exceptions"

        special = SpecialAnswers()
        generator = AITemplateGenerator()

        template = generator.generate(special)

        # Should sanitize special characters
        assert template.name == "testtemplate"
        assert template.name.isalnum() or "-" in template.name

    def test_generate_preserves_answer_data(self):
        """Test that generation preserves all answer data in manifest"""
        mock_answers = MockAnswers()
        generator = AITemplateGenerator()

        template = generator.generate(mock_answers)

        # Verify all key data preserved
        assert template.manifest["technology_stack"]["primary_language"] == mock_answers.primary_language
        assert template.manifest["technology_stack"]["framework"] == mock_answers.framework
        assert template.manifest["architecture"]["pattern"] == mock_answers.architecture_pattern
        assert template.manifest["testing"]["framework"] == mock_answers.unit_testing_framework
        assert template.manifest["description"] == mock_answers.template_purpose

    def test_generate_error_handling(self):
        """Test error handling in generation"""

        class BadAnswers:
            # Missing required attributes
            pass

        bad = BadAnswers()
        generator = AITemplateGenerator()

        with pytest.raises(TemplateGenerationError):
            generator.generate(bad)

    def test_complete_workflow(self):
        """Test complete generation workflow"""
        mock_answers = MockAnswers()
        generator = AITemplateGenerator(greenfield_context=mock_answers)

        # Generate template
        template = generator.generate(mock_answers)

        # Verify completeness
        assert template.name
        assert template.manifest
        assert template.settings
        assert template.claude_md
        assert template.project_structure
        assert template.code_templates is not None  # Can be empty
        assert template.inferred_analysis

        # Verify serialization works
        data = template.to_dict()
        assert isinstance(data, dict)
        assert "name" in data
        assert "manifest" in data
        assert "settings" in data

        # Verify deserialization works
        restored = GreenfieldTemplate.from_dict(data, inferred_analysis=template.inferred_analysis)
        assert restored.name == template.name
        assert restored.manifest == template.manifest
