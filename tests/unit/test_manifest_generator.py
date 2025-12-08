"""
Unit Tests for Manifest Generator

Tests manifest generation from codebase analysis including:
- Data model validation
- Name and identity generation
- Framework extraction and classification
- Placeholder detection
- Complexity calculation
- JSON serialization
"""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add lib directory to path - must be added to use lib. imports
lib_path = Path(__file__).parent.parent.parent / "installer" / "global" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Import directly from .py files to avoid package __init__.py circular imports
# Import using importlib to bypass package initialization
import importlib.util
import sys as _sys

def import_module_from_path(module_name, file_path):
    """Import a module directly from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    _sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import the specific .py files we need
codebase_models = import_module_from_path(
    "codebase_analyzer.models",
    lib_path / "codebase_analyzer" / "models.py"
)
template_models = import_module_from_path(
    "template_creation.models",
    lib_path / "template_creation" / "models.py"
)
manifest_gen = import_module_from_path(
    "template_creation.manifest_generator",
    lib_path / "template_creation" / "manifest_generator.py"
)

# Extract the classes we need
ArchitectureInfo = codebase_models.ArchitectureInfo
CodebaseAnalysis = codebase_models.CodebaseAnalysis
ConfidenceLevel = codebase_models.ConfidenceLevel
ConfidenceScore = codebase_models.ConfidenceScore
ExampleFile = codebase_models.ExampleFile
LayerInfo = codebase_models.LayerInfo
QualityInfo = codebase_models.QualityInfo
TechnologyInfo = codebase_models.TechnologyInfo

ManifestGenerator = manifest_gen.ManifestGenerator
FrameworkInfo = template_models.FrameworkInfo
PlaceholderInfo = template_models.PlaceholderInfo
TemplateManifest = template_models.TemplateManifest


@pytest.fixture
def sample_confidence():
    """Sample confidence score."""
    return ConfidenceScore(
        level=ConfidenceLevel.HIGH,
        percentage=90.0,
        reasoning="High confidence analysis"
    )


@pytest.fixture
def sample_technology(sample_confidence):
    """Sample technology info."""
    return TechnologyInfo(
        primary_language="Python",
        frameworks=["FastAPI", "SQLAlchemy"],
        testing_frameworks=["pytest"],
        build_tools=["pip"],
        databases=["PostgreSQL"],
        infrastructure=["Docker"],
        confidence=sample_confidence
    )


@pytest.fixture
def sample_architecture(sample_confidence):
    """Sample architecture info."""
    return ArchitectureInfo(
        patterns=["Repository", "Dependency Injection", "CQRS"],
        architectural_style="Clean Architecture",
        layers=[
            LayerInfo(
                name="Domain",
                description="Core business logic",
                typical_files=["*.py"],
                dependencies=[]
            ),
            LayerInfo(
                name="Application",
                description="Use cases",
                typical_files=["*_service.py"],
                dependencies=["Domain"]
            ),
            LayerInfo(
                name="Infrastructure",
                description="External concerns",
                typical_files=["*_repository.py"],
                dependencies=["Domain"]
            ),
        ],
        key_abstractions=["Entity", "Repository", "UseCase"],
        dependency_flow="Inward toward domain",
        confidence=sample_confidence
    )


@pytest.fixture
def sample_quality(sample_confidence):
    """Sample quality info."""
    return QualityInfo(
        overall_score=85.0,
        solid_compliance=90.0,
        dry_compliance=85.0,
        yagni_compliance=80.0,
        test_coverage=92.0,
        code_smells=["Long method in UserService"],
        strengths=["Clear separation of concerns", "Good test coverage"],
        improvements=["Refactor long methods"],
        confidence=sample_confidence
    )


@pytest.fixture
def sample_analysis(sample_technology, sample_architecture, sample_quality):
    """Sample codebase analysis."""
    return CodebaseAnalysis(
        codebase_path="/tmp/sample-project",
        analyzed_at=datetime.now(),
        technology=sample_technology,
        architecture=sample_architecture,
        quality=sample_quality,
        example_files=[
            ExampleFile(
                path="domain/user.py",
                purpose="User entity",
                layer="Domain",
                patterns_used=["Entity"],
                key_concepts=["Aggregate Root"]
            )
        ],
        agent_used=True,
        analysis_version="0.1.0"
    )


class TestManifestGenerator:
    """Test ManifestGenerator class."""

    def test_initialization(self, sample_analysis):
        """Test generator initialization."""
        generator = ManifestGenerator(sample_analysis)
        assert generator.analysis == sample_analysis

    def test_generate_manifest(self, sample_analysis):
        """Test complete manifest generation."""
        generator = ManifestGenerator(sample_analysis)
        manifest = generator.generate()

        # Verify manifest structure
        assert isinstance(manifest, TemplateManifest)
        assert manifest.schema_version == "1.0.0"
        assert manifest.name
        assert manifest.display_name
        assert manifest.description
        assert manifest.version == "1.0.0"
        assert manifest.language == "Python"
        assert len(manifest.frameworks) > 0
        assert manifest.architecture == "Clean Architecture"
        assert len(manifest.patterns) > 0
        assert len(manifest.layers) > 0
        assert len(manifest.placeholders) >= 3  # ProjectName, Namespace, Author
        assert len(manifest.tags) > 0
        assert manifest.category in ["backend", "frontend", "mobile", "desktop", "fullstack", "general"]
        assert 1 <= manifest.complexity <= 10
        assert manifest.confidence_score == 90.0

    def test_generate_name(self, sample_analysis):
        """Test template name generation."""
        generator = ManifestGenerator(sample_analysis)
        name = generator._generate_name()

        assert isinstance(name, str)
        assert "python" in name.lower()
        assert "clean-architecture" in name.lower()
        assert name.endswith("-template")

    def test_generate_display_name(self, sample_analysis):
        """Test display name generation."""
        generator = ManifestGenerator(sample_analysis)
        display_name = generator._generate_display_name()

        assert isinstance(display_name, str)
        assert display_name[0].isupper()  # Title case
        assert "-template" not in display_name.lower()

    def test_generate_description(self, sample_analysis):
        """Test description generation."""
        generator = ManifestGenerator(sample_analysis)
        description = generator._generate_description()

        assert isinstance(description, str)
        assert "Python" in description
        assert "Clean Architecture" in description

    @patch("subprocess.run")
    def test_infer_author_success(self, mock_run, sample_analysis):
        """Test author inference from git config."""
        mock_run.return_value = MagicMock(returncode=0, stdout="John Doe\n")

        generator = ManifestGenerator(sample_analysis)
        author = generator._infer_author()

        assert author == "John Doe"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_infer_author_failure(self, mock_run, sample_analysis):
        """Test author inference failure."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        generator = ManifestGenerator(sample_analysis)
        author = generator._infer_author()

        assert author is None


class TestLanguageVersionInference:
    """Test language version inference methods."""

    def test_infer_python_version_from_file(self, sample_analysis):
        """Test Python version inference from .python-version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .python-version file
            version_file = Path(tmpdir) / ".python-version"
            version_file.write_text("3.11.0")

            sample_analysis.codebase_path = tmpdir
            generator = ManifestGenerator(sample_analysis)

            version = generator._infer_python_version()
            assert version == ">=3.11.0"

    def test_infer_python_version_not_found(self, sample_analysis):
        """Test Python version inference when no version file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_analysis.codebase_path = tmpdir
            generator = ManifestGenerator(sample_analysis)

            version = generator._infer_python_version()
            assert version is None

    def test_infer_dotnet_version(self, sample_analysis):
        """Test .NET version inference from .csproj."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .csproj file
            csproj = Path(tmpdir) / "test.csproj"
            csproj.write_text("""
                <Project Sdk="Microsoft.NET.Sdk">
                    <PropertyGroup>
                        <TargetFramework>net8.0</TargetFramework>
                    </PropertyGroup>
                </Project>
            """)

            sample_analysis.codebase_path = tmpdir
            sample_analysis.technology.primary_language = "C#"
            generator = ManifestGenerator(sample_analysis)

            version = generator._infer_dotnet_version()
            assert version == "net8.0"

    def test_infer_node_version(self, sample_analysis):
        """Test Node.js version inference from package.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create package.json
            package_json = Path(tmpdir) / "package.json"
            package_json.write_text(json.dumps({
                "engines": {
                    "node": ">=18.0.0"
                }
            }))

            sample_analysis.codebase_path = tmpdir
            sample_analysis.technology.primary_language = "TypeScript"
            generator = ManifestGenerator(sample_analysis)

            version = generator._infer_node_version()
            assert version == ">=18.0.0"


class TestFrameworkExtraction:
    """Test framework extraction and classification."""

    def test_extract_frameworks(self, sample_analysis):
        """Test framework extraction."""
        generator = ManifestGenerator(sample_analysis)
        frameworks = generator._extract_frameworks()

        assert isinstance(frameworks, list)
        assert len(frameworks) == 3  # FastAPI, SQLAlchemy, pytest

        # Check framework info structure
        for fw in frameworks:
            assert isinstance(fw, FrameworkInfo)
            assert fw.name
            assert fw.purpose in ["testing", "ui", "data", "core"]

    def test_infer_framework_purpose_testing(self, sample_analysis):
        """Test testing framework classification."""
        generator = ManifestGenerator(sample_analysis)

        assert generator._infer_framework_purpose("pytest") == "testing"
        assert generator._infer_framework_purpose("jest") == "testing"
        assert generator._infer_framework_purpose("xunit") == "testing"

    def test_infer_framework_purpose_ui(self, sample_analysis):
        """Test UI framework classification."""
        generator = ManifestGenerator(sample_analysis)

        assert generator._infer_framework_purpose("React") == "ui"
        assert generator._infer_framework_purpose("Vue") == "ui"
        assert generator._infer_framework_purpose("MAUI") == "ui"

    def test_infer_framework_purpose_data(self, sample_analysis):
        """Test data framework classification."""
        generator = ManifestGenerator(sample_analysis)

        assert generator._infer_framework_purpose("SQLAlchemy") == "data"
        assert generator._infer_framework_purpose("EntityFramework") == "data"
        assert generator._infer_framework_purpose("Prisma") == "data"

    def test_infer_framework_purpose_core(self, sample_analysis):
        """Test core framework classification."""
        generator = ManifestGenerator(sample_analysis)

        assert generator._infer_framework_purpose("FastAPI") == "core"
        assert generator._infer_framework_purpose("Express") == "core"
        assert generator._infer_framework_purpose("Django") == "core"

    def test_infer_framework_version_python(self, sample_analysis):
        """Test framework version inference for Python."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create requirements.txt
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("fastapi==0.104.0\npytest==7.4.0")

            sample_analysis.codebase_path = tmpdir
            generator = ManifestGenerator(sample_analysis)

            version = generator._infer_framework_version("fastapi")
            assert version == "0.104.0"


class TestPlaceholderExtraction:
    """Test intelligent placeholder extraction."""

    def test_extract_placeholders(self, sample_analysis):
        """Test placeholder extraction."""
        generator = ManifestGenerator(sample_analysis)
        placeholders = generator._extract_placeholders()

        # Standard placeholders
        assert "ProjectName" in placeholders
        assert "Namespace" in placeholders
        assert "Author" in placeholders

        # Check placeholder structure
        for name, info in placeholders.items():
            assert isinstance(info, PlaceholderInfo)
            assert info.name.startswith("{{")
            assert info.name.endswith("}}")
            assert info.description

    def test_project_name_placeholder(self, sample_analysis):
        """Test ProjectName placeholder."""
        generator = ManifestGenerator(sample_analysis)
        placeholders = generator._extract_placeholders()

        project_name = placeholders["ProjectName"]
        assert project_name.name == "{{ProjectName}}"
        assert project_name.required is True
        assert project_name.pattern == "^[A-Za-z][A-Za-z0-9_]*$"

    def test_namespace_placeholder(self, sample_analysis):
        """Test Namespace placeholder."""
        generator = ManifestGenerator(sample_analysis)
        placeholders = generator._extract_placeholders()

        namespace = placeholders["Namespace"]
        assert namespace.name == "{{Namespace}}"
        assert namespace.required is True
        assert "\\" in namespace.pattern  # Supports dotted notation


class TestUtilityMethods:
    """Test utility methods for tags, category, and complexity."""

    def test_generate_tags(self, sample_analysis):
        """Test tag generation."""
        generator = ManifestGenerator(sample_analysis)
        tags = generator._generate_tags()

        assert isinstance(tags, list)
        assert len(tags) > 0
        assert "python" in tags
        assert "clean-architecture" in tags

        # Check deduplication
        assert len(tags) == len(set(tags))

    def test_infer_category_backend(self, sample_analysis):
        """Test backend category inference."""
        generator = ManifestGenerator(sample_analysis)
        category = generator._infer_category()

        assert category == "backend"  # FastAPI is backend

    def test_infer_category_frontend(self, sample_technology, sample_architecture, sample_quality):
        """Test frontend category inference."""
        sample_technology.frameworks = ["React", "TailwindCSS"]
        analysis = CodebaseAnalysis(
            codebase_path="/tmp/test",
            technology=sample_technology,
            architecture=sample_architecture,
            quality=sample_quality,
            agent_used=True
        )

        generator = ManifestGenerator(analysis)
        category = generator._infer_category()

        assert category == "frontend"

    def test_infer_category_mobile(self, sample_technology, sample_architecture, sample_quality):
        """Test mobile category inference."""
        sample_technology.frameworks = ["MAUI"]
        analysis = CodebaseAnalysis(
            codebase_path="/tmp/test",
            technology=sample_technology,
            architecture=sample_architecture,
            quality=sample_quality,
            agent_used=True
        )

        generator = ManifestGenerator(analysis)
        category = generator._infer_category()

        assert category == "mobile"

    def test_calculate_complexity_simple(self, sample_analysis):
        """Test complexity calculation for simple project."""
        # Modify to be simple (1 layer, 1 framework, 1 pattern)
        sample_analysis.architecture.layers = [
            LayerInfo(name="Application", description="App layer", typical_files=[], dependencies=[])
        ]
        sample_analysis.technology.frameworks = ["Flask"]
        sample_analysis.technology.testing_frameworks = []
        sample_analysis.architecture.patterns = ["MVC"]

        generator = ManifestGenerator(sample_analysis)
        complexity = generator._calculate_complexity()

        assert 1 <= complexity <= 4  # Should be low

    def test_calculate_complexity_complex(self, sample_analysis):
        """Test complexity calculation for complex project."""
        # Already has 3 layers, 2 frameworks + 1 testing = 3, 3 patterns
        generator = ManifestGenerator(sample_analysis)
        complexity = generator._calculate_complexity()

        assert 7 <= complexity <= 10  # Should be high

    def test_extract_requirements(self, sample_analysis):
        """Test requirement extraction."""
        generator = ManifestGenerator(sample_analysis)
        requirements = generator._extract_requirements()

        assert isinstance(requirements, list)
        assert "agent:python-domain-specialist" in requirements
        assert "agent:architectural-reviewer" in requirements  # Clean Architecture

    def test_extract_requirements_javascript(self, sample_technology, sample_architecture, sample_quality):
        """Test that JavaScript projects don't get TypeScript specialist."""
        sample_technology.primary_language = "JavaScript"
        sample_architecture.architectural_style = "Modular"  # Not Clean Architecture
        analysis = CodebaseAnalysis(
            codebase_path="/tmp/test",
            technology=sample_technology,
            architecture=sample_architecture,
            quality=sample_quality,
            agent_used=True
        )

        generator = ManifestGenerator(analysis)
        requirements = generator._extract_requirements()

        assert isinstance(requirements, list)
        assert "agent:typescript-domain-specialist" not in requirements
        assert "agent:javascript-domain-specialist" not in requirements

    def test_extract_requirements_typescript(self, sample_technology, sample_architecture, sample_quality):
        """Test that TypeScript projects correctly get TypeScript specialist."""
        sample_technology.primary_language = "TypeScript"
        sample_architecture.architectural_style = "Modular"  # Not Clean Architecture
        analysis = CodebaseAnalysis(
            codebase_path="/tmp/test",
            technology=sample_technology,
            architecture=sample_architecture,
            quality=sample_quality,
            agent_used=True
        )

        generator = ManifestGenerator(analysis)
        requirements = generator._extract_requirements()

        assert isinstance(requirements, list)
        assert "agent:typescript-domain-specialist" in requirements


class TestJSONSerialization:
    """Test JSON serialization and file operations."""

    def test_to_json(self, sample_analysis):
        """Test JSON serialization."""
        generator = ManifestGenerator(sample_analysis)
        manifest = generator.generate()

        json_str = generator.to_json(manifest)

        # Verify valid JSON
        data = json.loads(json_str)
        assert data["schema_version"] == "1.0.0"
        assert data["language"] == "Python"
        assert "frameworks" in data
        assert "placeholders" in data

    def test_save_manifest(self, sample_analysis):
        """Test manifest file saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "manifest.json"

            generator = ManifestGenerator(sample_analysis)
            manifest = generator.generate()
            generator.save(manifest, output_path)

            # Verify file exists and is valid JSON
            assert output_path.exists()
            data = json.loads(output_path.read_text())
            assert data["schema_version"] == "1.0.0"
            assert data["language"] == "Python"

    def test_save_creates_directories(self, sample_analysis):
        """Test that save creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "manifest.json"

            generator = ManifestGenerator(sample_analysis)
            manifest = generator.generate()
            generator.save(manifest, output_path)

            assert output_path.exists()
            assert output_path.parent.exists()


class TestManifestModel:
    """Test TemplateManifest model validation."""

    def test_manifest_creation(self):
        """Test manifest model creation."""
        manifest = TemplateManifest(
            name="test-template",
            display_name="Test Template",
            description="A test template",
            language="Python",
            architecture="Layered",
            category="backend",
            complexity=5,
            confidence_score=85.0
        )

        assert manifest.name == "test-template"
        assert manifest.schema_version == "1.0.0"
        assert manifest.version == "1.0.0"

    def test_manifest_to_dict(self):
        """Test manifest dict conversion."""
        manifest = TemplateManifest(
            name="test-template",
            display_name="Test Template",
            description="A test template",
            language="Python",
            architecture="Layered",
            category="backend",
            complexity=5,
            confidence_score=85.0
        )

        data = manifest.to_dict()
        assert isinstance(data, dict)
        assert data["name"] == "test-template"

    def test_complexity_validation(self):
        """Test complexity score validation."""
        # Valid complexity
        manifest = TemplateManifest(
            name="test",
            display_name="Test",
            description="Test",
            language="Python",
            architecture="Layered",
            category="backend",
            complexity=5,
            confidence_score=85.0
        )
        assert manifest.complexity == 5

        # Invalid complexity (should raise validation error)
        with pytest.raises(Exception):  # Pydantic validation error
            TemplateManifest(
                name="test",
                display_name="Test",
                description="Test",
                language="Python",
                architecture="Layered",
                category="backend",
                complexity=11,  # > 10
                confidence_score=85.0
            )


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_minimal_analysis(self):
        """Test with minimal analysis data."""
        minimal_analysis = CodebaseAnalysis(
            codebase_path="/tmp/minimal",
            technology=TechnologyInfo(
                primary_language="Python",
                frameworks=[],
                confidence=ConfidenceScore(level=ConfidenceLevel.LOW, percentage=60.0)
            ),
            architecture=ArchitectureInfo(
                patterns=[],
                architectural_style="Unknown",
                layers=[],
                key_abstractions=[],
                dependency_flow="Unknown",
                confidence=ConfidenceScore(level=ConfidenceLevel.LOW, percentage=60.0)
            ),
            quality=QualityInfo(
                overall_score=50.0,
                solid_compliance=50.0,
                dry_compliance=50.0,
                yagni_compliance=50.0,
                confidence=ConfidenceScore(level=ConfidenceLevel.LOW, percentage=60.0)
            ),
            agent_used=False,
            fallback_reason="Agent unavailable"
        )

        generator = ManifestGenerator(minimal_analysis)
        manifest = generator.generate()

        # Should still generate valid manifest
        assert manifest.name
        assert manifest.language == "Python"
        assert manifest.category == "general"

    def test_nonexistent_project_path(self, sample_analysis):
        """Test with nonexistent project path."""
        sample_analysis.codebase_path = "/nonexistent/path"

        generator = ManifestGenerator(sample_analysis)
        manifest = generator.generate()

        # Should still generate manifest
        assert manifest.language_version is None  # Can't detect version
        assert manifest.author is None  # Can't get git config

    def test_empty_frameworks_list(self, sample_technology, sample_architecture, sample_quality):
        """Test with empty frameworks list."""
        sample_technology.frameworks = []
        sample_technology.testing_frameworks = []
        analysis = CodebaseAnalysis(
            codebase_path="/tmp/test",
            technology=sample_technology,
            architecture=sample_architecture,
            quality=sample_quality,
            agent_used=True
        )

        generator = ManifestGenerator(analysis)
        manifest = generator.generate()

        assert len(manifest.frameworks) == 0
        assert manifest.category == "general"
