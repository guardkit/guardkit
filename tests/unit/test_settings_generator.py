"""
Unit Tests for Settings Generator

Tests the SettingsGenerator class and related models.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add lib to path for imports (backup in case conftest doesn't run)
lib_parent_path = Path(__file__).parent.parent.parent / "installer" / "core"
if str(lib_parent_path) not in sys.path:
    sys.path.insert(0, str(lib_parent_path))

import pytest

from lib.settings_generator import (
    SettingsGenerator,
    TemplateSettings,
    NamingConvention,
    FileOrganization,
    LayerMapping,
    CodeStyle,
    CaseStyle,
    TestLocation,
    GenerationError
)
from lib.settings_generator.validator import (
    TemplateSettingsValidator,
    ValidationResult
)
from lib.codebase_analyzer.models import (
    CodebaseAnalysis,
    TechnologyInfo,
    ArchitectureInfo,
    QualityInfo,
    LayerInfo,
    ExampleFile,
    ConfidenceScore,
    ConfidenceLevel
)


# Test Fixtures
@pytest.fixture
def mock_confidence_score():
    """Create a mock confidence score."""
    return ConfidenceScore(
        level=ConfidenceLevel.HIGH,
        percentage=95.0,
        reasoning="High confidence test data"
    )


@pytest.fixture
def mock_python_analysis(mock_confidence_score):
    """Create mock CodebaseAnalysis for Python project."""
    return CodebaseAnalysis(
        codebase_path="/test/project",
        analyzed_at=datetime.now(),
        technology=TechnologyInfo(
            primary_language="Python",
            frameworks=["FastAPI", "Pydantic"],
            testing_frameworks=["pytest"],
            build_tools=["pip"],
            databases=[],
            infrastructure=[],
            confidence=mock_confidence_score
        ),
        architecture=ArchitectureInfo(
            patterns=["Clean Architecture", "Repository"],
            architectural_style="Layered",
            layers=[
                LayerInfo(
                    name="Domain",
                    description="Business logic",
                    typical_files=["*.py"],
                    dependencies=[]
                ),
                LayerInfo(
                    name="Application",
                    description="Use cases",
                    typical_files=["*.py"],
                    dependencies=["Domain"]
                ),
                LayerInfo(
                    name="Infrastructure",
                    description="External concerns",
                    typical_files=["*.py"],
                    dependencies=["Domain", "Application"]
                ),
            ],
            key_abstractions=["Repository", "Entity", "UseCase"],
            dependency_flow="Inward toward domain",
            confidence=mock_confidence_score
        ),
        quality=QualityInfo(
            overall_score=85.0,
            solid_compliance=80.0,
            dry_compliance=75.0,
            yagni_compliance=90.0,
            test_coverage=85.0,
            code_smells=[],
            strengths=["Clean separation", "Good test coverage"],
            improvements=["Add more integration tests"],
            confidence=mock_confidence_score
        ),
        example_files=[
            ExampleFile(
                path="src/domain/entities/user.py",
                purpose="User entity",
                layer="Domain",
                patterns_used=["Entity"],
                key_concepts=["Domain model"]
            ),
            ExampleFile(
                path="src/application/use_cases/create_user.py",
                purpose="Create user use case",
                layer="Application",
                patterns_used=["UseCase"],
                key_concepts=["Application service"]
            ),
        ]
    )


@pytest.fixture
def mock_csharp_analysis(mock_confidence_score):
    """Create mock CodebaseAnalysis for C# project."""
    return CodebaseAnalysis(
        codebase_path="/test/maui-project",
        analyzed_at=datetime.now(),
        technology=TechnologyInfo(
            primary_language="C#",
            frameworks=[".NET MAUI", "CommunityToolkit.Mvvm"],
            testing_frameworks=["xUnit"],
            build_tools=["dotnet"],
            databases=[],
            infrastructure=[],
            confidence=mock_confidence_score
        ),
        architecture=ArchitectureInfo(
            patterns=["MVVM", "CQRS"],
            architectural_style="MVVM",
            layers=[
                LayerInfo(
                    name="Domain",
                    description="Business logic",
                    typical_files=["*.cs"],
                    dependencies=[]
                ),
                LayerInfo(
                    name="Presentation",
                    description="UI layer",
                    typical_files=["*.xaml", "*.cs"],
                    dependencies=["Domain"]
                ),
            ],
            key_abstractions=["ViewModel", "Model", "Command"],
            dependency_flow="Presentation -> Domain",
            confidence=mock_confidence_score
        ),
        quality=QualityInfo(
            overall_score=90.0,
            solid_compliance=85.0,
            dry_compliance=80.0,
            yagni_compliance=95.0,
            test_coverage=75.0,
            code_smells=[],
            strengths=["Clean MVVM", "Good separation"],
            improvements=[],
            confidence=mock_confidence_score
        ),
        example_files=[
            ExampleFile(
                path="src/Domain/GetProducts.cs",
                purpose="Get products operation",
                layer="Domain",
                patterns_used=["CQRS"],
                key_concepts=["Query"]
            ),
            ExampleFile(
                path="src/Presentation/ViewModels/ProductViewModel.cs",
                purpose="Product view model",
                layer="Presentation",
                patterns_used=["MVVM"],
                key_concepts=["ViewModel"]
            ),
        ]
    )


@pytest.fixture
def mock_typescript_analysis(mock_confidence_score):
    """Create mock CodebaseAnalysis for TypeScript project."""
    return CodebaseAnalysis(
        codebase_path="/test/react-project",
        analyzed_at=datetime.now(),
        technology=TechnologyInfo(
            primary_language="TypeScript",
            frameworks=["React", "Next.js"],
            testing_frameworks=["Jest", "Playwright"],
            build_tools=["npm"],
            databases=[],
            infrastructure=[],
            confidence=mock_confidence_score
        ),
        architecture=ArchitectureInfo(
            patterns=["Component-Based", "Hooks"],
            architectural_style="Feature-based",
            layers=[
                LayerInfo(
                    name="Components",
                    description="React components",
                    typical_files=["*.tsx"],
                    dependencies=[]
                ),
                LayerInfo(
                    name="Services",
                    description="API services",
                    typical_files=["*.ts"],
                    dependencies=[]
                ),
            ],
            key_abstractions=["Component", "Hook", "Service"],
            dependency_flow="Components -> Services",
            confidence=mock_confidence_score
        ),
        quality=QualityInfo(
            overall_score=88.0,
            solid_compliance=82.0,
            dry_compliance=85.0,
            yagni_compliance=90.0,
            test_coverage=80.0,
            code_smells=[],
            strengths=["Modern React patterns"],
            improvements=[],
            confidence=mock_confidence_score
        ),
        example_files=[
            ExampleFile(
                path="src/components/ProductList.tsx",
                purpose="Product list component",
                layer="Components",
                patterns_used=["Hooks"],
                key_concepts=["Component"]
            ),
        ]
    )


# Tests for SettingsGenerator
class TestSettingsGenerator:
    """Test SettingsGenerator class."""

    def test_generate_python_settings(self, mock_python_analysis):
        """Test settings generation from Python analysis."""
        generator = SettingsGenerator(mock_python_analysis)
        settings = generator.generate()

        assert settings.schema_version == "1.0.0"
        assert len(settings.naming_conventions) > 0
        assert settings.file_organization is not None
        assert len(settings.layer_mappings) > 0
        assert settings.code_style is not None

        # Check Python-specific conventions
        assert "class" in settings.naming_conventions
        assert settings.naming_conventions["class"].case_style == CaseStyle.PASCAL_CASE
        assert "function" in settings.naming_conventions
        assert settings.naming_conventions["function"].case_style == CaseStyle.SNAKE_CASE

        # Check code style
        assert settings.code_style.indent_size == 4
        assert settings.code_style.line_length == 88  # Black default

    def test_generate_csharp_settings(self, mock_csharp_analysis):
        """Test settings generation from C# analysis."""
        generator = SettingsGenerator(mock_csharp_analysis)
        settings = generator.generate()

        assert settings.schema_version == "1.0.0"

        # Check C#-specific conventions
        assert "class" in settings.naming_conventions
        assert settings.naming_conventions["class"].case_style == CaseStyle.PASCAL_CASE
        assert "interface" in settings.naming_conventions
        assert settings.naming_conventions["interface"].prefix == "I"

        # Check layer mappings
        assert "Domain" in settings.layer_mappings
        assert "Presentation" in settings.layer_mappings
        assert "{{ProjectName}}" in settings.layer_mappings["Domain"].namespace_pattern

        # Check file patterns
        assert "*.cs" in settings.layer_mappings["Domain"].file_patterns
        assert "!*Test.cs" in settings.layer_mappings["Domain"].file_patterns

    def test_generate_typescript_settings(self, mock_typescript_analysis):
        """Test settings generation from TypeScript analysis."""
        generator = SettingsGenerator(mock_typescript_analysis)
        settings = generator.generate()

        assert settings.schema_version == "1.0.0"

        # Check TypeScript-specific conventions
        assert "class" in settings.naming_conventions
        assert "function" in settings.naming_conventions
        assert settings.naming_conventions["function"].case_style == CaseStyle.CAMEL_CASE

        # Check code style
        assert settings.code_style.indent_size == 2  # TypeScript default
        assert settings.code_style.trailing_commas is True

    def test_file_organization_by_layer(self, mock_python_analysis):
        """Test file organization inference with multiple layers."""
        generator = SettingsGenerator(mock_python_analysis)
        settings = generator.generate()

        # Multiple layers should trigger by_layer organization
        assert settings.file_organization.by_layer is True

    def test_file_organization_by_feature(self, mock_typescript_analysis):
        """Test file organization inference with feature-based architecture."""
        generator = SettingsGenerator(mock_typescript_analysis)
        settings = generator.generate()

        # Feature-based architecture should trigger by_feature
        assert settings.file_organization.by_feature is True

    def test_test_location_separate(self, mock_python_analysis):
        """Test test location inference."""
        generator = SettingsGenerator(mock_python_analysis)
        settings = generator.generate()

        # Should default to separate
        assert settings.file_organization.test_location == TestLocation.SEPARATE

    def test_layer_mappings_creation(self, mock_python_analysis):
        """Test layer mappings creation."""
        generator = SettingsGenerator(mock_python_analysis)
        settings = generator.generate()

        # Should have mappings for all layers
        assert len(settings.layer_mappings) == 3
        assert "Domain" in settings.layer_mappings
        assert "Application" in settings.layer_mappings
        assert "Infrastructure" in settings.layer_mappings

        # Check directory patterns
        assert settings.layer_mappings["Domain"].directory == "src/Domain"
        assert settings.layer_mappings["Application"].directory == "src/Application"

    def test_generation_options(self, mock_python_analysis):
        """Test generation options creation."""
        generator = SettingsGenerator(mock_python_analysis)
        settings = generator.generate()

        assert settings.generation_options is not None
        assert settings.generation_options["preserve_comments"] is True
        assert settings.generation_options["auto_format"] is True

    def test_to_json(self, mock_python_analysis):
        """Test JSON serialization."""
        generator = SettingsGenerator(mock_python_analysis)
        settings = generator.generate()

        json_str = generator.to_json(settings)

        # Should be valid JSON
        data = json.loads(json_str)
        assert data["schema_version"] == "1.0.0"
        assert "naming_conventions" in data
        assert "file_organization" in data

    def test_save_to_file(self, mock_python_analysis, tmp_path):
        """Test saving settings to file."""
        generator = SettingsGenerator(mock_python_analysis)
        settings = generator.generate()

        output_file = tmp_path / "settings.json"
        generator.save(settings, output_file)

        # File should exist
        assert output_file.exists()

        # Content should be valid JSON
        content = output_file.read_text()
        data = json.loads(content)
        assert data["schema_version"] == "1.0.0"

    def test_save_creates_directory(self, mock_python_analysis, tmp_path):
        """Test save creates parent directories."""
        generator = SettingsGenerator(mock_python_analysis)
        settings = generator.generate()

        output_file = tmp_path / "nested" / "dir" / "settings.json"
        generator.save(settings, output_file)

        # File and directories should exist
        assert output_file.exists()
        assert output_file.parent.exists()

    def test_generation_error_handling(self, mock_confidence_score):
        """Test error handling during generation."""
        # Create invalid analysis (missing required fields handled by Pydantic)
        # For this test, we'll use a minimal analysis
        minimal_analysis = CodebaseAnalysis(
            codebase_path="/test",
            analyzed_at=datetime.now(),
            technology=TechnologyInfo(
                primary_language="UnknownLanguage",
                confidence=mock_confidence_score
            ),
            architecture=ArchitectureInfo(
                patterns=[],
                architectural_style="Unknown",
                layers=[],
                key_abstractions=[],
                dependency_flow="Unknown",
                confidence=mock_confidence_score
            ),
            quality=QualityInfo(
                overall_score=50.0,
                solid_compliance=50.0,
                dry_compliance=50.0,
                yagni_compliance=50.0,
                confidence=mock_confidence_score
            )
        )

        generator = SettingsGenerator(minimal_analysis)
        settings = generator.generate()

        # Should still generate something (with defaults)
        assert settings is not None
        assert settings.schema_version == "1.0.0"


# Tests for Models
class TestNamingConvention:
    """Test NamingConvention model."""

    def test_naming_convention_creation(self):
        """Test creating a naming convention."""
        conv = NamingConvention(
            element_type="class",
            pattern="{{Name}}",
            case_style=CaseStyle.PASCAL_CASE,
            suffix=".cs",
            examples=["Product", "Order"]
        )

        assert conv.element_type == "class"
        assert conv.pattern == "{{Name}}"
        assert conv.case_style == CaseStyle.PASCAL_CASE
        assert conv.suffix == ".cs"
        assert len(conv.examples) == 2

    def test_naming_convention_with_prefix(self):
        """Test naming convention with prefix."""
        conv = NamingConvention(
            element_type="interface",
            pattern="I{{Name}}",
            case_style=CaseStyle.PASCAL_CASE,
            prefix="I"
        )

        assert conv.prefix == "I"


class TestFileOrganization:
    """Test FileOrganization model."""

    def test_file_organization_by_layer(self):
        """Test file organization by layer."""
        org = FileOrganization(
            by_layer=True,
            by_feature=False,
            test_location=TestLocation.SEPARATE
        )

        assert org.by_layer is True
        assert org.by_feature is False
        assert org.test_location == TestLocation.SEPARATE

    def test_file_organization_defaults(self):
        """Test file organization defaults."""
        org = FileOrganization(
            test_location=TestLocation.SEPARATE
        )

        assert org.by_layer is True  # Default
        assert org.by_feature is False  # Default


class TestLayerMapping:
    """Test LayerMapping model."""

    def test_layer_mapping_creation(self):
        """Test creating a layer mapping."""
        mapping = LayerMapping(
            name="Domain",
            directory="src/Domain",
            namespace_pattern="{{ProjectName}}.Domain",
            file_patterns=["*.cs"]
        )

        assert mapping.name == "Domain"
        assert mapping.directory == "src/Domain"
        assert mapping.namespace_pattern == "{{ProjectName}}.Domain"
        assert "*.cs" in mapping.file_patterns


class TestCodeStyle:
    """Test CodeStyle model."""

    def test_code_style_python(self):
        """Test Python code style."""
        style = CodeStyle(
            indentation="spaces",
            indent_size=4,
            line_length=88,
            trailing_commas=True
        )

        assert style.indentation == "spaces"
        assert style.indent_size == 4
        assert style.line_length == 88
        assert style.trailing_commas is True

    def test_code_style_validation(self):
        """Test code style validation."""
        with pytest.raises(Exception):  # Pydantic will raise validation error
            CodeStyle(
                indentation="spaces",
                indent_size=20,  # Outside valid range (1-8)
                line_length=88
            )


class TestTemplateSettings:
    """Test TemplateSettings model."""

    def test_template_settings_creation(self):
        """Test creating template settings."""
        settings = TemplateSettings(
            schema_version="1.0.0",
            naming_conventions={
                "class": NamingConvention(
                    element_type="class",
                    pattern="{{Name}}",
                    case_style=CaseStyle.PASCAL_CASE
                )
            },
            file_organization=FileOrganization(
                test_location=TestLocation.SEPARATE
            ),
            layer_mappings={
                "Domain": LayerMapping(
                    name="Domain",
                    directory="src/Domain"
                )
            },
            code_style=CodeStyle()
        )

        assert settings.schema_version == "1.0.0"
        assert len(settings.naming_conventions) == 1
        assert "class" in settings.naming_conventions

    def test_template_settings_to_dict(self):
        """Test converting to dictionary."""
        settings = TemplateSettings(
            schema_version="1.0.0",
            naming_conventions={},
            file_organization=FileOrganization(
                test_location=TestLocation.SEPARATE
            ),
            layer_mappings={}
        )

        data = settings.to_dict()
        assert isinstance(data, dict)
        assert data["schema_version"] == "1.0.0"

    def test_template_settings_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "schema_version": "1.0.0",
            "naming_conventions": {
                "class": {
                    "element_type": "class",
                    "pattern": "{{Name}}",
                    "case_style": "PascalCase",
                    "examples": []
                }
            },
            "file_organization": {
                "by_layer": True,
                "by_feature": False,
                "test_location": "separate"
            },
            "layer_mappings": {}
        }

        settings = TemplateSettings.from_dict(data)
        assert settings.schema_version == "1.0.0"
        assert "class" in settings.naming_conventions


# Tests for Validator
class TestTemplateSettingsValidator:
    """Test TemplateSettingsValidator class."""

    def test_validate_valid_settings(self, mock_python_analysis):
        """Test validation of valid settings."""
        generator = SettingsGenerator(mock_python_analysis)
        settings = generator.generate()

        validator = TemplateSettingsValidator()
        result = validator.validate(settings)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_empty_naming_conventions(self):
        """Test validation fails with empty naming conventions."""
        settings = TemplateSettings(
            schema_version="1.0.0",
            naming_conventions={},  # Empty
            file_organization=FileOrganization(
                test_location=TestLocation.SEPARATE
            ),
            layer_mappings={}
        )

        validator = TemplateSettingsValidator()
        result = validator.validate(settings)

        assert result.is_valid is False
        assert any("naming_conventions" in error for error in result.errors)

    def test_validate_warnings(self, mock_python_analysis):
        """Test validation warnings."""
        generator = SettingsGenerator(mock_python_analysis)
        settings = generator.generate()

        # Remove examples to trigger warnings
        for conv in settings.naming_conventions.values():
            conv.examples = []

        validator = TemplateSettingsValidator()
        result = validator.validate(settings)

        # Should be valid but with warnings
        assert result.is_valid is True
        assert len(result.warnings) > 0

    def test_validate_compatibility_python(self, mock_python_analysis):
        """Test language compatibility validation for Python."""
        generator = SettingsGenerator(mock_python_analysis)
        settings = generator.generate()

        validator = TemplateSettingsValidator()
        result = validator.validate_compatibility(settings, "Python")

        # Python doesn't use namespaces, so should warn if present
        # (but our generator doesn't add them for Python, so should be clean)
        assert result.is_valid is True

    def test_validate_compatibility_csharp(self, mock_csharp_analysis):
        """Test language compatibility validation for C#."""
        generator = SettingsGenerator(mock_csharp_analysis)
        settings = generator.generate()

        validator = TemplateSettingsValidator()
        result = validator.validate_compatibility(settings, "C#")

        # C# requires namespaces, validator should check
        assert result.is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
