"""
Unit tests for TemplateGenerator

Tests the core template generation functionality including:
- Template generation from example files
- AI placeholder extraction
- Template validation
- Pattern identification
- Deduplication
"""

import pytest
from pathlib import Path
from datetime import datetime
from typing import List

from lib.template_generator import (
    TemplateGenerator,
    CodeTemplate,
    TemplateCollection,
    ValidationResult,
    MockAIClient,
)
from lib.codebase_analyzer.models import (
    CodebaseAnalysis,
    TechnologyInfo,
    ArchitectureInfo,
    QualityInfo,
    ExampleFile,
    LayerInfo,
    ConfidenceScore,
    ConfidenceLevel,
)


def create_mock_confidence() -> ConfidenceScore:
    """Create a mock confidence score."""
    return ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)


def create_mock_codebase_analysis(
    example_files: List[ExampleFile] = None,
    layers: List[LayerInfo] = None
) -> CodebaseAnalysis:
    """Create a mock CodebaseAnalysis for testing."""
    if example_files is None:
        example_files = []
    if layers is None:
        layers = []

    return CodebaseAnalysis(
        codebase_path="/test/project",
        technology=TechnologyInfo(
            primary_language="C#",
            frameworks=["ASP.NET Core"],
            testing_frameworks=["xUnit"],
            confidence=create_mock_confidence()
        ),
        architecture=ArchitectureInfo(
            patterns=["Repository", "Domain-Driven Design"],
            architectural_style="Clean Architecture",
            layers=layers,
            dependency_flow="Inward",
            confidence=create_mock_confidence()
        ),
        quality=QualityInfo(
            overall_score=85.0,
            solid_compliance=90.0,
            dry_compliance=85.0,
            yagni_compliance=80.0,
            confidence=create_mock_confidence()
        ),
        example_files=example_files
    )


class TestTemplateGenerator:
    """Test TemplateGenerator class."""

    def test_initialization(self):
        """Test TemplateGenerator initialization."""
        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)

        assert generator.analysis == analysis
        assert generator.ai_client is not None
        assert isinstance(generator.generated_templates, list)

    def test_initialization_with_custom_ai_client(self):
        """Test initialization with custom AI client."""
        analysis = create_mock_codebase_analysis()
        ai_client = MockAIClient()
        generator = TemplateGenerator(analysis, ai_client=ai_client)

        assert generator.ai_client == ai_client

    def test_generate_empty_analysis(self):
        """Test generation with no example files."""
        analysis = create_mock_codebase_analysis(example_files=[])
        generator = TemplateGenerator(analysis, ai_client=MockAIClient())

        collection = generator.generate()

        assert collection.total_count == 0
        assert len(collection.templates) == 0
        assert collection.by_type == {}

    def test_generate_with_max_templates(self):
        """Test generation with max_templates limit."""
        example_files = [
            ExampleFile(
                path="src/Domain/Products/GetProducts.cs",
                purpose="Get products",
                layer="Domain",
                patterns_used=["Repository"]
            ),
            ExampleFile(
                path="src/Domain/Orders/GetOrders.cs",
                purpose="Get orders",
                layer="Domain"
            ),
            ExampleFile(
                path="src/Domain/Users/GetUsers.cs",
                purpose="Get users",
                layer="Domain"
            ),
        ]

        analysis = create_mock_codebase_analysis(example_files=example_files)
        generator = TemplateGenerator(analysis, ai_client=MockAIClient())

        # Create actual files for testing
        test_dir = Path("/tmp/test_templates")
        test_dir.mkdir(exist_ok=True)

        for example in example_files:
            file_path = test_dir / example.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("namespace TestProject.Domain;\n\npublic class GetProducts {}")

        # Update analysis codebase_path
        analysis.codebase_path = str(test_dir)

        # Test with max_templates=2
        collection = generator.generate(max_templates=2)

        # Should only generate 2 templates
        assert collection.total_count <= 2
        assert len(collection.templates) <= 2

    def test_extract_placeholders_from_content(self):
        """Test placeholder extraction from template content."""
        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)

        content = "namespace {{ProjectName}}.{{Layer}};\n\npublic class {{Verb}}{{Entity}}"
        placeholders = generator._extract_placeholders_from_content(content)

        assert "ProjectName" in placeholders
        assert "Layer" in placeholders
        assert "Verb" in placeholders
        assert "Entity" in placeholders
        assert len(placeholders) == 4

    def test_extract_placeholders_no_placeholders(self):
        """Test placeholder extraction with no placeholders."""
        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)

        content = "namespace TestProject.Domain;\n\npublic class GetProducts {}"
        placeholders = generator._extract_placeholders_from_content(content)

        assert len(placeholders) == 0

    def test_infer_language_csharp(self):
        """Test language inference for C# files."""
        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)

        language = generator._infer_language(Path("test.cs"))
        assert language == "C#"

    def test_infer_language_typescript(self):
        """Test language inference for TypeScript files."""
        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)

        language = generator._infer_language(Path("test.ts"))
        assert language == "TypeScript"

    def test_infer_language_python(self):
        """Test language inference for Python files."""
        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)

        language = generator._infer_language(Path("test.py"))
        assert language == "Python"

    def test_infer_language_unknown(self):
        """Test language inference for unknown extensions."""
        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)

        language = generator._infer_language(Path("test.xyz"))
        assert language == "Unknown"

    def test_infer_template_path_with_layer(self):
        """Test template path inference with layers."""
        layers = [
            LayerInfo(
                name="Domain",
                description="Business logic",
                typical_files=[],
                dependencies=[]
            )
        ]
        analysis = create_mock_codebase_analysis(layers=layers)

        example_file = ExampleFile(
            path="src/Domain/Products/GetProducts.cs",
            purpose="Get products",
            layer="Domain"
        )

        generator = TemplateGenerator(analysis)
        template_path = generator._infer_template_path(example_file)

        # New implementation uses lowercase for consistency
        assert "templates/domain/" in template_path
        assert ".template" in template_path

    def test_infer_template_path_fallback(self):
        """Test template path inference fallback."""
        analysis = create_mock_codebase_analysis()

        example_file = ExampleFile(
            path="src/Unknown/Test.cs",
            purpose="Test file"
        )

        generator = TemplateGenerator(analysis)
        template_path = generator._infer_template_path(example_file)

        assert "templates/" in template_path
        assert ".template" in template_path

    def test_create_template_name(self):
        """Test template name creation."""
        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)

        example_file = ExampleFile(
            path="src/Domain/GetProducts.cs",
            purpose="Get products"
        )

        name = generator._create_template_name(example_file)
        assert name == "GetProducts.cs.template"

    def test_identify_patterns_result_type(self):
        """Test pattern identification for Result type pattern."""
        content = """
        public ErrorOr<Product> GetProduct(int id)
        {
            if (id <= 0)
                return Error.Validation("Invalid ID");

            return new Product { Id = id };
        }
        """

        example_file = ExampleFile(
            path="test.cs",
            purpose="Test",
            patterns_used=[]
        )

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        patterns = generator._identify_patterns(content, example_file)

        assert "Result type pattern" in patterns

    def test_identify_patterns_async_await(self):
        """Test pattern identification for async/await."""
        content = """
        public async Task<Product> GetProduct(int id)
        {
            var product = await _repository.GetByIdAsync(id);
            return product;
        }
        """

        example_file = ExampleFile(
            path="test.cs",
            purpose="Test",
            patterns_used=[]
        )

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        patterns = generator._identify_patterns(content, example_file)

        assert "Async/await" in patterns

    def test_identify_patterns_repository(self):
        """Test pattern identification for Repository pattern."""
        content = """
        public class ProductRepository : IProductRepository
        {
            public async Task<Product> GetByIdAsync(int id)
            {
                // implementation
            }
        }
        """

        example_file = ExampleFile(
            path="test.cs",
            purpose="Test",
            patterns_used=[]
        )

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        patterns = generator._identify_patterns(content, example_file)

        assert "Repository pattern" in patterns

    def test_identify_patterns_existing_patterns(self):
        """Test that existing patterns from example file are preserved."""
        content = "public class Test {}"

        example_file = ExampleFile(
            path="test.cs",
            purpose="Test",
            patterns_used=["Factory pattern", "Singleton"]
        )

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        patterns = generator._identify_patterns(content, example_file)

        assert "Factory pattern" in patterns
        assert "Singleton" in patterns

    def test_validate_template_valid(self):
        """Test validation of valid template."""
        valid_template = CodeTemplate(
            name="Test.template",
            original_path="test.cs",
            template_path="templates/test.template",
            content="namespace {{ProjectName}};\n\npublic class {{ClassName}} {}",
            placeholders=["ProjectName", "ClassName"],
            file_type="code",
            language="C#",
            quality_score=8.0
        )

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        result = generator._validate_template(valid_template)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_template_empty_content(self):
        """Test validation fails for empty content."""
        invalid_template = CodeTemplate(
            name="Test.template",
            original_path="test.cs",
            template_path="templates/test.template",
            content="",
            placeholders=["ProjectName"],
            file_type="code",
            language="C#"
        )

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        result = generator._validate_template(invalid_template)

        assert not result.is_valid
        assert "Template content is empty" in result.errors

    def test_validate_template_invalid_placeholder_format(self):
        """Test validation fails for invalid placeholder format."""
        invalid_template = CodeTemplate(
            name="Test.template",
            original_path="test.cs",
            template_path="templates/test.template",
            content="namespace {{project_name}};",
            placeholders=["project_name"],  # Should be PascalCase
            file_type="code",
            language="C#"
        )

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        result = generator._validate_template(invalid_template)

        assert not result.is_valid
        assert any("Invalid placeholder format" in err for err in result.errors)

    def test_validate_template_no_placeholders_warning(self):
        """Test validation warns when no placeholders found."""
        template = CodeTemplate(
            name="Test.template",
            original_path="test.cs",
            template_path="templates/test.template",
            content="namespace TestProject;\n\npublic class Test {}",
            placeholders=[],
            file_type="code",
            language="C#"
        )

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        result = generator._validate_template(template)

        assert result.is_valid  # Still valid, just a warning
        assert "No placeholders found in template" in result.warnings

    def test_template_deduplication(self):
        """Test template deduplication."""
        templates = [
            CodeTemplate(
                name="Test1.template",
                original_path="test1.cs",
                template_path="templates/test1.template",
                content="namespace {{ProjectName}}; class {{ClassName}} {}",
                placeholders=["ProjectName", "ClassName"],
                file_type="code"
            ),
            CodeTemplate(
                name="Test2.template",
                original_path="test2.cs",
                template_path="templates/test2.template",
                content="namespace {{ProjectName}}; class {{ClassName}} {}",  # Same structure
                placeholders=["ProjectName", "ClassName"],
                file_type="code"
            ),
            CodeTemplate(
                name="Test3.template",
                original_path="test3.cs",
                template_path="templates/test3.template",
                content="interface {{InterfaceName}} {}",  # Different
                placeholders=["InterfaceName"],
                file_type="code"
            )
        ]

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        unique = generator._deduplicate_templates(templates)

        # Should keep Test1 and Test3 (Test2 is duplicate of Test1)
        assert len(unique) == 2

    def test_template_hash(self):
        """Test template hash generation."""
        template = CodeTemplate(
            name="Test.template",
            original_path="test.cs",
            template_path="templates/test.template",
            content="namespace {{ProjectName}}; class {{ClassName}} {}",
            placeholders=["ProjectName", "ClassName"],
            file_type="domain_operation"
        )

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        hash_value = generator._template_hash(template)

        assert "domain_operation" in hash_value
        assert "ClassName" in hash_value
        assert "ProjectName" in hash_value

    def test_count_by_type(self):
        """Test counting templates by type."""
        templates = [
            CodeTemplate(
                name="T1",
                original_path="t1",
                template_path="t1",
                content="test",
                file_type="domain_operation"
            ),
            CodeTemplate(
                name="T2",
                original_path="t2",
                template_path="t2",
                content="test",
                file_type="domain_operation"
            ),
            CodeTemplate(
                name="T3",
                original_path="t3",
                template_path="t3",
                content="test",
                file_type="repository"
            ),
        ]

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        counts = generator._count_by_type(templates)

        assert counts["domain_operation"] == 2
        assert counts["repository"] == 1

    def test_save_templates(self, tmp_path):
        """Test saving templates to disk."""
        templates = [
            CodeTemplate(
                name="Test.template",
                original_path="test.cs",
                template_path="templates/domain/Test.template",
                content="namespace {{ProjectName}}; class {{ClassName}} {}",
                placeholders=["ProjectName", "ClassName"],
                file_type="domain_operation"
            )
        ]

        collection = TemplateCollection(
            templates=templates,
            total_count=1,
            by_type={"domain_operation": 1}
        )

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)

        output_dir = tmp_path / "output"
        generator.save_templates(collection, output_dir)

        # Check file was created
        template_file = output_dir / "templates/domain/Test.template"
        assert template_file.exists()
        assert "{{ProjectName}}" in template_file.read_text()

    def test_parse_ai_response_with_placeholders(self):
        """Test parsing AI response with PLACEHOLDERS section."""
        response = """```csharp
namespace {{ProjectName}}.Domain;

public class {{ClassName}}
{
    // implementation
}
```
PLACEHOLDERS: ProjectName, ClassName"""

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        template_content, placeholders = generator._parse_ai_response(response)

        assert "{{ProjectName}}" in template_content
        assert "{{ClassName}}" in template_content
        assert "ProjectName" in placeholders
        assert "ClassName" in placeholders

    def test_parse_ai_response_without_placeholders_section(self):
        """Test parsing AI response without PLACEHOLDERS section (fallback)."""
        response = """```csharp
namespace {{ProjectName}}.Domain;

public class {{ClassName}}
{
    // implementation
}
```"""

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        template_content, placeholders = generator._parse_ai_response(response)

        # Should extract placeholders from content
        assert "ProjectName" in placeholders
        assert "ClassName" in placeholders

    def test_fallback_placeholder_extraction_csharp(self):
        """Test fallback placeholder extraction for C#."""
        content = "namespace MyCompany.MyApp.Domain;\n\npublic class GetProducts {}"

        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)
        template_content, placeholders = generator._fallback_placeholder_extraction(content, "C#")

        assert "{{ProjectName}}" in template_content
        assert "ProjectName" in placeholders

    def test_create_extraction_prompt(self):
        """Test extraction prompt creation."""
        analysis = create_mock_codebase_analysis()
        generator = TemplateGenerator(analysis)

        prompt = generator._create_extraction_prompt(
            content="test content",
            file_path="test.cs",
            language="C#",
            purpose="Test file"
        )

        assert "C#" in prompt
        assert "test.cs" in prompt
        assert "Test file" in prompt
        assert "{{PlaceholderName}}" in prompt
        assert "PLACEHOLDERS:" in prompt


class TestMockAIClient:
    """Test MockAIClient."""

    def test_mock_client_csharp(self):
        """Test mock client generates C# template."""
        client = MockAIClient()
        prompt = "Convert this C# file..."

        response = client.generate(prompt)

        assert "namespace {{ProjectName}}" in response
        assert "PLACEHOLDERS:" in response

    def test_mock_client_typescript(self):
        """Test mock client generates TypeScript template."""
        client = MockAIClient()
        prompt = "Convert this TypeScript file..."

        response = client.generate(prompt)

        assert "{{EntityName}}" in response
        assert "PLACEHOLDERS:" in response

    def test_mock_client_python(self):
        """Test mock client generates Python template."""
        client = MockAIClient()
        prompt = "Convert this Python file..."

        response = client.generate(prompt)

        assert "{{EntityName}}" in response
        assert "@dataclass" in response
        assert "PLACEHOLDERS:" in response

    def test_mock_client_analyze_code(self):
        """Test mock client code analysis."""
        client = MockAIClient()
        result = client.analyze_code("test code", "C#")

        assert "language" in result
        assert "patterns" in result
        assert result["language"] == "C#"

    def test_mock_client_extract_patterns(self):
        """Test mock client pattern extraction."""
        client = MockAIClient()
        code = "public async ErrorOr<Product> GetProduct() { await repository.Get(); }"

        patterns = client.extract_patterns(code, "C#")

        assert "Result type pattern" in patterns
        assert "Async/await" in patterns


class TestTemplateCollection:
    """Test TemplateCollection model."""

    def test_template_collection_creation(self):
        """Test creating a template collection."""
        templates = [
            CodeTemplate(
                name="T1",
                original_path="t1",
                template_path="t1",
                content="test",
                file_type="domain_operation"
            )
        ]

        collection = TemplateCollection(
            templates=templates,
            total_count=1,
            by_type={"domain_operation": 1}
        )

        assert len(collection.templates) == 1
        assert collection.total_count == 1
        assert collection.by_type["domain_operation"] == 1

    def test_template_collection_empty(self):
        """Test creating an empty template collection."""
        collection = TemplateCollection(
            templates=[],
            total_count=0,
            by_type={}
        )

        assert len(collection.templates) == 0
        assert collection.total_count == 0


class TestValidationResult:
    """Test ValidationResult model."""

    def test_validation_result_valid(self):
        """Test creating a valid validation result."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )

        assert result.is_valid
        assert not result.has_errors
        assert not result.has_warnings

    def test_validation_result_with_errors(self):
        """Test validation result with errors."""
        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=[]
        )

        assert not result.is_valid
        assert result.has_errors
        assert len(result.errors) == 2

    def test_validation_result_with_warnings(self):
        """Test validation result with warnings."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Warning 1"]
        )

        assert result.is_valid
        assert not result.has_errors
        assert result.has_warnings
