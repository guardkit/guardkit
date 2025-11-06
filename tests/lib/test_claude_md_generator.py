"""
Unit Tests for CLAUDE.md Generator

Tests the generation of comprehensive CLAUDE.md documentation from
CodebaseAnalysis results.
"""

import pytest
from datetime import datetime
from pathlib import Path

from lib.codebase_analyzer.models import (
    CodebaseAnalysis,
    TechnologyInfo,
    ArchitectureInfo,
    QualityInfo,
    LayerInfo,
    ExampleFile,
    ConfidenceScore,
    ConfidenceLevel,
)
from lib.template_generator import (
    ClaudeMdGenerator,
    TemplateClaude,
)


# Test Fixtures

@pytest.fixture
def basic_technology_info():
    """Basic technology info fixture"""
    return TechnologyInfo(
        primary_language="Python",
        frameworks=["FastAPI", "pytest"],
        testing_frameworks=["pytest", "coverage"],
        build_tools=["pip", "setuptools"],
        databases=["PostgreSQL"],
        infrastructure=["Docker"],
        confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
    )


@pytest.fixture
def csharp_technology_info():
    """C# technology info fixture"""
    return TechnologyInfo(
        primary_language="C#",
        frameworks=[".NET MAUI 8.0", "CommunityToolkit.Mvvm"],
        testing_frameworks=["xUnit", "FluentAssertions"],
        build_tools=["dotnet"],
        databases=[],
        infrastructure=[],
        confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=92.0)
    )


@pytest.fixture
def mvvm_architecture_info():
    """MVVM architecture info fixture"""
    return ArchitectureInfo(
        patterns=["MVVM", "Dependency Injection", "Observer"],
        architectural_style="Model-View-ViewModel (MVVM)",
        layers=[
            LayerInfo(
                name="Domain",
                description="Business logic and entities",
                typical_files=["*.cs"],
                dependencies=[]
            ),
            LayerInfo(
                name="Presentation",
                description="Views and ViewModels",
                typical_files=["*.xaml", "*ViewModel.cs"],
                dependencies=["Domain"]
            ),
        ],
        key_abstractions=["Entity", "ViewModel", "Command"],
        dependency_flow="View → ViewModel → Model",
        confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
    )


@pytest.fixture
def clean_architecture_info():
    """Clean Architecture info fixture"""
    return ArchitectureInfo(
        patterns=["Clean Architecture", "CQRS", "Repository"],
        architectural_style="Clean Architecture",
        layers=[
            LayerInfo(
                name="Domain",
                description="Core business logic (innermost layer)",
                typical_files=["*.cs"],
                dependencies=[]
            ),
            LayerInfo(
                name="Application",
                description="Use cases and application services",
                typical_files=["*Handler.cs", "*Command.cs"],
                dependencies=["Domain"]
            ),
            LayerInfo(
                name="Infrastructure",
                description="External concerns (database, API clients)",
                typical_files=["*Repository.cs", "*Client.cs"],
                dependencies=["Application", "Domain"]
            ),
            LayerInfo(
                name="Presentation",
                description="API controllers and UI",
                typical_files=["*Controller.cs"],
                dependencies=["Application"]
            ),
        ],
        key_abstractions=["Entity", "Repository", "UseCase"],
        dependency_flow="Dependencies point inward toward Domain",
        confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=93.0)
    )


@pytest.fixture
def quality_info():
    """Quality info fixture"""
    return QualityInfo(
        overall_score=85.0,
        solid_compliance=88.0,
        dry_compliance=82.0,
        yagni_compliance=90.0,
        test_coverage=78.5,
        code_smells=["Long methods in legacy code"],
        strengths=[
            "Clear separation of concerns",
            "Consistent naming conventions",
            "Good test coverage"
        ],
        improvements=[
            "Increase test coverage to 85%",
            "Refactor long methods"
        ],
        confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=91.0)
    )


@pytest.fixture
def example_files():
    """Example files fixture"""
    return [
        ExampleFile(
            path="src/domain/products/get_products.py",
            purpose="Demonstrates domain operation pattern",
            layer="Domain",
            patterns_used=["CQRS Query", "Repository"],
            key_concepts=["Domain operation", "Query pattern"]
        ),
        ExampleFile(
            path="src/presentation/views/product_page.xaml",
            purpose="Demonstrates MVVM view",
            layer="Presentation",
            patterns_used=["MVVM", "Data Binding"],
            key_concepts=["View", "XAML"]
        ),
        ExampleFile(
            path="src/presentation/viewmodels/product_view_model.cs",
            purpose="Demonstrates MVVM ViewModel",
            layer="Presentation",
            patterns_used=["MVVM", "Observer"],
            key_concepts=["ViewModel", "Commands"]
        ),
    ]


@pytest.fixture
def basic_codebase_analysis(basic_technology_info, clean_architecture_info, quality_info):
    """Basic codebase analysis fixture"""
    return CodebaseAnalysis(
        codebase_path="/test/project",
        analyzed_at=datetime(2025, 11, 6, 12, 0, 0),
        technology=basic_technology_info,
        architecture=clean_architecture_info,
        quality=quality_info,
        example_files=[],
    )


@pytest.fixture
def mvvm_codebase_analysis(csharp_technology_info, mvvm_architecture_info, quality_info, example_files):
    """MVVM codebase analysis fixture"""
    return CodebaseAnalysis(
        codebase_path="/test/mvvm-project",
        analyzed_at=datetime(2025, 11, 6, 12, 0, 0),
        technology=csharp_technology_info,
        architecture=mvvm_architecture_info,
        quality=quality_info,
        example_files=example_files,
    )


# Test TemplateClaude Model

def test_template_claude_creation():
    """Test TemplateClaude model creation"""
    claude = TemplateClaude(
        schema_version="1.0.0",
        architecture_overview="# Architecture",
        technology_stack="# Tech Stack",
        project_structure="# Structure",
        naming_conventions="# Naming",
        patterns="# Patterns",
        examples="# Examples",
        quality_standards="# Quality",
        agent_usage="# Agents",
        generated_at="2025-11-06T12:00:00Z",
        confidence_score=0.95
    )

    assert claude.schema_version == "1.0.0"
    assert claude.confidence_score == 0.95
    assert "# Architecture" in claude.architecture_overview


def test_template_claude_to_markdown():
    """Test TemplateClaude to_markdown conversion"""
    claude = TemplateClaude(
        schema_version="1.0.0",
        architecture_overview="# Architecture Overview\nMVVM pattern",
        technology_stack="# Technology Stack\nC# + .NET MAUI",
        project_structure="# Project Structure\nSrc/",
        naming_conventions="# Naming\nPascalCase",
        patterns="# Patterns\nMVVM",
        examples="# Examples\nCode here",
        quality_standards="# Quality\n80% coverage",
        agent_usage="# Agents\nUse MVVM agent",
        generated_at="2025-11-06T12:00:00Z",
        confidence_score=0.92
    )

    markdown = claude.to_markdown()

    assert "# Claude Code Project Instructions" in markdown
    assert "**Generated**: 2025-11-06T12:00:00Z" in markdown
    assert "**Confidence**: 92%" in markdown
    assert "# Architecture Overview" in markdown
    assert "# Technology Stack" in markdown
    assert "# Project Structure" in markdown


# Test ClaudeMdGenerator

def test_generator_initialization(basic_codebase_analysis):
    """Test generator initialization"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    assert generator.analysis == basic_codebase_analysis


def test_generate_complete_claude(basic_codebase_analysis):
    """Test complete CLAUDE.md generation"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    claude = generator.generate()

    assert isinstance(claude, TemplateClaude)
    assert claude.schema_version == "1.0.0"
    assert claude.architecture_overview
    assert claude.technology_stack
    assert claude.project_structure
    assert claude.naming_conventions
    assert claude.patterns
    assert claude.quality_standards
    assert claude.generated_at
    assert 0.0 <= claude.confidence_score <= 1.0


def test_architecture_overview_mvvm(mvvm_codebase_analysis):
    """Test MVVM architecture overview generation"""
    generator = ClaudeMdGenerator(mvvm_codebase_analysis)
    overview = generator._generate_architecture_overview()

    assert "# Architecture Overview" in overview
    assert "MVVM" in overview
    assert "Model" in overview
    assert "View" in overview
    assert "ViewModel" in overview
    assert "Layers" in overview


def test_architecture_overview_clean(basic_codebase_analysis):
    """Test Clean Architecture overview generation"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    overview = generator._generate_architecture_overview()

    assert "# Architecture Overview" in overview
    assert "Clean Architecture" in overview
    assert "Domain" in overview
    assert "Application" in overview
    assert "Infrastructure" in overview
    assert "Dependency Flow" in overview


def test_technology_stack_generation(mvvm_codebase_analysis):
    """Test technology stack section generation"""
    generator = ClaudeMdGenerator(mvvm_codebase_analysis)
    stack = generator._generate_technology_stack()

    assert "# Technology Stack" in stack
    assert "C#" in stack
    assert ".NET MAUI" in stack
    assert "xUnit" in stack
    assert "Testing" in stack


def test_technology_stack_with_databases(basic_codebase_analysis):
    """Test technology stack with databases"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    stack = generator._generate_technology_stack()

    assert "Python" in stack
    assert "FastAPI" in stack
    assert "PostgreSQL" in stack
    assert "Docker" in stack


def test_project_structure_generation(basic_codebase_analysis):
    """Test project structure section generation"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    structure = generator._generate_project_structure()

    assert "# Project Structure" in structure
    assert "```" in structure  # Code block for tree
    assert "Directory Descriptions" in structure


def test_naming_conventions_no_examples(basic_codebase_analysis):
    """Test naming conventions with no example files"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    conventions = generator._generate_naming_conventions()

    assert "# Naming Conventions" in conventions
    assert "language-standard" in conventions.lower()


def test_naming_conventions_with_examples(mvvm_codebase_analysis):
    """Test naming conventions with example files"""
    generator = ClaudeMdGenerator(mvvm_codebase_analysis)
    conventions = generator._generate_naming_conventions()

    assert "# Naming Conventions" in conventions
    # Should group by purpose
    assert any(keyword in conventions for keyword in ["Domain", "View", "Model"])


def test_patterns_generation(basic_codebase_analysis):
    """Test patterns section generation"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    patterns = generator._generate_patterns()

    assert "# Patterns and Best Practices" in patterns
    assert "Architectural Patterns" in patterns
    assert "CQRS" in patterns or "Repository" in patterns


def test_language_best_practices_csharp(mvvm_codebase_analysis):
    """Test C# language-specific best practices"""
    generator = ClaudeMdGenerator(mvvm_codebase_analysis)
    practices = generator._generate_language_best_practices()

    practices_text = "\n".join(practices)
    assert "nullable reference types" in practices_text.lower()
    assert "async/await" in practices_text.lower()


def test_language_best_practices_python(basic_codebase_analysis):
    """Test Python language-specific best practices"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    practices = generator._generate_language_best_practices()

    practices_text = "\n".join(practices)
    assert "PEP 8" in practices_text
    assert "type hints" in practices_text.lower()


def test_examples_generation_no_files(basic_codebase_analysis):
    """Test examples generation with no example files"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    examples = generator._generate_examples()

    assert "# Code Examples" in examples
    assert "template files" in examples.lower()


def test_examples_generation_with_files(mvvm_codebase_analysis):
    """Test examples generation with example files"""
    generator = ClaudeMdGenerator(mvvm_codebase_analysis)
    examples = generator._generate_examples()

    assert "# Code Examples" in examples
    assert "Domain" in examples or "Presentation" in examples


def test_quality_standards_generation(basic_codebase_analysis):
    """Test quality standards section generation"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    standards = generator._generate_quality_standards()

    assert "# Quality Standards" in standards
    assert "Testing" in standards
    assert "≥80%" in standards  # Coverage requirement
    assert "SOLID" in standards
    assert "DRY" in standards
    assert "YAGNI" in standards


def test_quality_standards_with_improvements(basic_codebase_analysis):
    """Test quality standards includes improvements"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    standards = generator._generate_quality_standards()

    assert "Areas for Improvement" in standards
    assert "Increase test coverage" in standards


def test_agent_usage_generation(basic_codebase_analysis):
    """Test agent usage section generation"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    usage = generator._generate_agent_usage()

    assert "# Agent Usage" in usage
    assert "domain-specific agents" in usage.lower()
    assert "testing agents" in usage.lower()


def test_save_to_file(basic_codebase_analysis, tmp_path):
    """Test saving CLAUDE.md to file"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    claude = generator.generate()

    output_file = tmp_path / "CLAUDE.md"
    generator.save(claude, output_file)

    assert output_file.exists()
    content = output_file.read_text(encoding='utf-8')
    assert "# Claude Code Project Instructions" in content
    assert "# Architecture Overview" in content


def test_full_markdown_generation(basic_codebase_analysis):
    """Test full markdown generation pipeline"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    claude = generator.generate()
    markdown = generator.to_markdown(claude)

    # Verify all major sections present
    assert "# Claude Code Project Instructions" in markdown
    assert "# Architecture Overview" in markdown
    assert "# Technology Stack" in markdown
    assert "# Project Structure" in markdown
    assert "# Naming Conventions" in markdown
    assert "# Patterns and Best Practices" in markdown
    assert "# Code Examples" in markdown
    assert "# Quality Standards" in markdown
    assert "# Agent Usage" in markdown


def test_confidence_score_propagation(basic_codebase_analysis):
    """Test confidence score is properly propagated"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    claude = generator.generate()

    # Should use overall confidence from analysis
    expected_confidence = basic_codebase_analysis.overall_confidence.percentage / 100.0
    assert abs(claude.confidence_score - expected_confidence) < 0.01


# Test Helper Methods

def test_sort_layers_hierarchically(basic_codebase_analysis):
    """Test layer sorting by typical hierarchy"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    layers = basic_codebase_analysis.architecture.layers

    sorted_layers = generator._sort_layers_hierarchically(layers)

    # Domain should come first
    assert sorted_layers[0].name == "Domain"
    # Infrastructure should come last
    assert sorted_layers[-1].name == "Infrastructure"


def test_group_examples_by_purpose(mvvm_codebase_analysis):
    """Test grouping example files by purpose"""
    generator = ClaudeMdGenerator(mvvm_codebase_analysis)
    grouped = generator._group_examples_by_purpose(mvvm_codebase_analysis.example_files)

    assert isinstance(grouped, dict)
    assert len(grouped) > 0
    # Should have domain and view categories
    assert any("Domain" in key for key in grouped.keys())


def test_infer_naming_pattern_verb_entity():
    """Test inferring verb-entity naming pattern"""
    generator = ClaudeMdGenerator(
        CodebaseAnalysis(
            codebase_path="/test",
            technology=TechnologyInfo(
                primary_language="Python",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            architecture=ArchitectureInfo(
                patterns=[],
                architectural_style="Layered",
                layers=[],
                key_abstractions=[],
                dependency_flow="Standard",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=80.0,
                solid_compliance=80.0,
                dry_compliance=80.0,
                yagni_compliance=80.0,
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            example_files=[]
        )
    )

    files = [
        ExampleFile(path="GetProducts.cs", purpose="query", patterns_used=[], key_concepts=[]),
        ExampleFile(path="CreateOrder.cs", purpose="command", patterns_used=[], key_concepts=[]),
    ]

    pattern = generator._infer_naming_pattern(files)
    assert pattern == "{{Verb}}{{Entity}}"


def test_infer_naming_pattern_suffix():
    """Test inferring suffix naming pattern"""
    generator = ClaudeMdGenerator(
        CodebaseAnalysis(
            codebase_path="/test",
            technology=TechnologyInfo(
                primary_language="Python",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            architecture=ArchitectureInfo(
                patterns=[],
                architectural_style="Layered",
                layers=[],
                key_abstractions=[],
                dependency_flow="Standard",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=80.0,
                solid_compliance=80.0,
                dry_compliance=80.0,
                yagni_compliance=80.0,
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            example_files=[]
        )
    )

    files = [
        ExampleFile(path="ProductPage.xaml", purpose="view", patterns_used=[], key_concepts=[]),
        ExampleFile(path="OrderPage.xaml", purpose="view", patterns_used=[], key_concepts=[]),
    ]

    pattern = generator._infer_naming_pattern(files)
    assert pattern == "{{Entity}}Page"


def test_has_verb_entity_pattern():
    """Test verb-entity pattern detection"""
    generator = ClaudeMdGenerator(
        CodebaseAnalysis(
            codebase_path="/test",
            technology=TechnologyInfo(
                primary_language="Python",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            architecture=ArchitectureInfo(
                patterns=[],
                architectural_style="Layered",
                layers=[],
                key_abstractions=[],
                dependency_flow="Standard",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=80.0,
                solid_compliance=80.0,
                dry_compliance=80.0,
                yagni_compliance=80.0,
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            example_files=[]
        )
    )

    assert generator._has_verb_entity_pattern("GetProducts") is True
    assert generator._has_verb_entity_pattern("CreateOrder") is True
    assert generator._has_verb_entity_pattern("UpdateUser") is True
    assert generator._has_verb_entity_pattern("ProductPage") is False
    assert generator._has_verb_entity_pattern("OrderService") is False


def test_find_common_suffix():
    """Test finding common suffix in names"""
    generator = ClaudeMdGenerator(
        CodebaseAnalysis(
            codebase_path="/test",
            technology=TechnologyInfo(
                primary_language="Python",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            architecture=ArchitectureInfo(
                patterns=[],
                architectural_style="Layered",
                layers=[],
                key_abstractions=[],
                dependency_flow="Standard",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=80.0,
                solid_compliance=80.0,
                dry_compliance=80.0,
                yagni_compliance=80.0,
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            example_files=[]
        )
    )

    # Test with Page suffix
    names = ["ProductPage", "OrderPage", "UserPage"]
    assert generator._find_common_suffix(names) == "Page"

    # Test with ViewModel suffix
    names = ["ProductViewModel", "OrderViewModel"]
    assert generator._find_common_suffix(names) == "ViewModel"

    # Test with no common suffix
    names = ["Product", "Order"]
    assert generator._find_common_suffix(names) is None


# Integration Tests

def test_end_to_end_mvvm_generation(mvvm_codebase_analysis, tmp_path):
    """Test end-to-end CLAUDE.md generation for MVVM project"""
    generator = ClaudeMdGenerator(mvvm_codebase_analysis)
    claude = generator.generate()

    # Save to file
    output_file = tmp_path / "CLAUDE.md"
    generator.save(claude, output_file)

    # Verify file content
    content = output_file.read_text(encoding='utf-8')

    # Check all major sections
    assert "# Claude Code Project Instructions" in content
    assert "MVVM" in content
    assert "C#" in content
    assert ".NET MAUI" in content
    assert "# Quality Standards" in content
    assert "nullable reference types" in content.lower()


def test_end_to_end_clean_arch_generation(basic_codebase_analysis, tmp_path):
    """Test end-to-end CLAUDE.md generation for Clean Architecture project"""
    generator = ClaudeMdGenerator(basic_codebase_analysis)
    claude = generator.generate()

    # Save to file
    output_file = tmp_path / "CLAUDE.md"
    generator.save(claude, output_file)

    # Verify file content
    content = output_file.read_text(encoding='utf-8')

    # Check all major sections
    assert "# Claude Code Project Instructions" in content
    assert "Clean Architecture" in content
    assert "Python" in content
    assert "Domain" in content
    assert "PEP 8" in content
