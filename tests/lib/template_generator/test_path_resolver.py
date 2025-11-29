"""
Tests for template path resolution strategies.

Tests the Strategy pattern implementation that resolves template file paths
based on architectural layers and filename patterns.
"""

import pytest
import importlib

# Import using importlib to avoid 'global' keyword issue
_path_resolver_module = importlib.import_module('installer.global.lib.template_generator.path_resolver')
_models_module = importlib.import_module('installer.global.lib.codebase_analyzer.models')

LayerClassificationStrategy = _path_resolver_module.LayerClassificationStrategy
PatternClassificationStrategy = _path_resolver_module.PatternClassificationStrategy
TemplatePathResolver = _path_resolver_module.TemplatePathResolver
PATTERN_MAPPINGS = _path_resolver_module.PATTERN_MAPPINGS

ExampleFile = _models_module.ExampleFile
CodebaseAnalysis = _models_module.CodebaseAnalysis
ArchitectureInfo = _models_module.ArchitectureInfo
LayerInfo = _models_module.LayerInfo
TechnologyInfo = _models_module.TechnologyInfo
QualityInfo = _models_module.QualityInfo
ConfidenceScore = _models_module.ConfidenceScore
ConfidenceLevel = _models_module.ConfidenceLevel


# Fixtures

@pytest.fixture
def sample_analysis():
    """Create sample codebase analysis."""
    return CodebaseAnalysis(
        codebase_path="/test/project",
        technology=TechnologyInfo(
            primary_language="C#",
            frameworks=[".NET MAUI"],
            build_tools=["dotnet"],
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=90.0,
            ),
        ),
        architecture=ArchitectureInfo(
            architectural_style="Layered Architecture",
            layers=[
                LayerInfo(name="domain", description="Domain layer"),
                LayerInfo(name="application", description="Application layer"),
                LayerInfo(name="infrastructure", description="Infrastructure layer"),
                LayerInfo(name="presentation", description="Presentation layer"),
            ],
            patterns=[],
            dependency_flow="Inward toward domain",
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=90.0,
            ),
        ),
        quality=QualityInfo(
            overall_score=85.0,
            solid_compliance=80.0,
            dry_compliance=85.0,
            yagni_compliance=90.0,
            confidence=ConfidenceScore(
                level=ConfidenceLevel.MEDIUM,
                percentage=85.0,
            ),
        ),
        example_files=[],
    )


@pytest.fixture
def example_file_repository_with_layer():
    """Example file: Repository with layer info."""
    return ExampleFile(
        path="src/Repositories/UserRepository.cs",
        purpose="User data access repository",
        layer="application",
        patterns_used=["Repository"],
        key_concepts=["Data Access"],
    )


@pytest.fixture
def example_file_service_with_layer():
    """Example file: Service with layer info."""
    return ExampleFile(
        path="src/Services/AuthService.cs",
        purpose="Authentication service",
        layer="application",
        patterns_used=["Service"],
        key_concepts=["Authentication"],
    )


@pytest.fixture
def example_file_view_with_layer():
    """Example file: View with layer info."""
    return ExampleFile(
        path="src/Views/DomainCameraView.cs",
        purpose="Camera view for domain",
        layer="presentation",
        patterns_used=["View"],
        key_concepts=["UI"],
    )


@pytest.fixture
def example_file_entity_with_layer():
    """Example file: Entity with layer info."""
    return ExampleFile(
        path="src/Models/ConfigurationPayload.cs",
        purpose="Configuration data entity",
        layer="domain",
        patterns_used=["Entity"],
        key_concepts=["Domain Model"],
    )


@pytest.fixture
def example_file_engine_with_layer():
    """Example file: Engine with layer info."""
    return ExampleFile(
        path="src/Engines/ConfigurationEngine.cs",
        purpose="Configuration processing engine",
        layer="infrastructure",
        patterns_used=["Engine"],
        key_concepts=["Processing"],
    )


@pytest.fixture
def example_file_repository_no_layer():
    """Example file: Repository WITHOUT layer info (fallback test)."""
    return ExampleFile(
        path="src/Data/ProductRepository.cs",
        purpose="Product data access",
        layer=None,  # No layer info - should use fallback
        patterns_used=["Repository"],
        key_concepts=["Data Access"],
    )


@pytest.fixture
def example_file_service_no_layer():
    """Example file: Service WITHOUT layer info (fallback test)."""
    return ExampleFile(
        path="src/Business/OrderService.cs",
        purpose="Order processing service",
        layer=None,  # No layer info - should use fallback
        patterns_used=["Service"],
        key_concepts=["Business Logic"],
    )


@pytest.fixture
def example_file_unknown_pattern():
    """Example file: Unknown pattern (should use parent dir or fallback)."""
    return ExampleFile(
        path="src/Utilities/StringHelper.cs",
        purpose="String utility helper",
        layer=None,
        patterns_used=[],
        key_concepts=["Utilities"],
    )


# LayerClassificationStrategy Tests

class TestLayerClassificationStrategy:
    """Test suite for LayerClassificationStrategy."""

    def test_classify_repository_with_layer(self, example_file_repository_with_layer, sample_analysis):
        """Test classification of Repository with layer info."""
        strategy = LayerClassificationStrategy()
        result = strategy.classify(example_file_repository_with_layer, sample_analysis)

        assert result is not None
        assert result == "templates/application/repositories/UserRepository.cs.template"

    def test_classify_service_with_layer(self, example_file_service_with_layer, sample_analysis):
        """Test classification of Service with layer info."""
        strategy = LayerClassificationStrategy()
        result = strategy.classify(example_file_service_with_layer, sample_analysis)

        assert result is not None
        assert result == "templates/application/services/AuthService.cs.template"

    def test_classify_view_with_layer(self, example_file_view_with_layer, sample_analysis):
        """Test classification of View with layer info."""
        strategy = LayerClassificationStrategy()
        result = strategy.classify(example_file_view_with_layer, sample_analysis)

        assert result is not None
        assert result == "templates/presentation/views/DomainCameraView.cs.template"

    def test_classify_entity_with_layer(self, example_file_entity_with_layer, sample_analysis):
        """Test classification of Entity with layer info."""
        strategy = LayerClassificationStrategy()
        result = strategy.classify(example_file_entity_with_layer, sample_analysis)

        assert result is not None
        # Entity files should go to domain/models/ directory
        assert result == "templates/domain/models/ConfigurationPayload.cs.template"

    def test_classify_engine_with_layer(self, example_file_engine_with_layer, sample_analysis):
        """Test classification of Engine with layer info."""
        strategy = LayerClassificationStrategy()
        result = strategy.classify(example_file_engine_with_layer, sample_analysis)

        assert result is not None
        assert result == "templates/infrastructure/engines/ConfigurationEngine.cs.template"

    def test_classify_without_layer_returns_none(self, example_file_repository_no_layer, sample_analysis):
        """Test that files without layer info return None."""
        strategy = LayerClassificationStrategy()
        result = strategy.classify(example_file_repository_no_layer, sample_analysis)

        assert result is None

    def test_infer_pattern_from_repository(self):
        """Test pattern inference from Repository filename."""
        strategy = LayerClassificationStrategy()
        pattern = strategy._infer_pattern("src/Repositories/UserRepository.cs")

        assert pattern == "repositories"

    def test_infer_pattern_from_service(self):
        """Test pattern inference from Service filename."""
        strategy = LayerClassificationStrategy()
        pattern = strategy._infer_pattern("src/Services/AuthService.cs")

        assert pattern == "services"

    def test_infer_pattern_from_viewmodel(self):
        """Test pattern inference from ViewModel filename."""
        strategy = LayerClassificationStrategy()
        pattern = strategy._infer_pattern("src/ViewModels/MainViewModel.cs")

        assert pattern == "viewmodels"

    def test_infer_pattern_fallback_to_parent_dir(self):
        """Test fallback to parent directory name when pattern not recognized."""
        strategy = LayerClassificationStrategy()
        pattern = strategy._infer_pattern("src/CustomDir/SomeFile.cs")

        assert pattern == "customdir"

    def test_infer_pattern_all_mappings(self):
        """Test that all PATTERN_MAPPINGS work correctly."""
        strategy = LayerClassificationStrategy()

        for suffix, expected_pattern in PATTERN_MAPPINGS:
            filename = f"Test{suffix}.cs"
            pattern = strategy._infer_pattern(f"src/Test/{filename}")
            assert pattern == expected_pattern, f"Failed for {suffix}"


# PatternClassificationStrategy Tests

class TestPatternClassificationStrategy:
    """Test suite for PatternClassificationStrategy."""

    def test_classify_repository_without_layer(self, example_file_repository_no_layer, sample_analysis):
        """Test classification of Repository without layer info (fallback)."""
        strategy = PatternClassificationStrategy()
        result = strategy.classify(example_file_repository_no_layer, sample_analysis)

        assert result is not None
        assert result == "templates/application/repositories/ProductRepository.cs.template"

    def test_classify_service_without_layer(self, example_file_service_no_layer, sample_analysis):
        """Test classification of Service without layer info (fallback)."""
        strategy = PatternClassificationStrategy()
        result = strategy.classify(example_file_service_no_layer, sample_analysis)

        assert result is not None
        assert result == "templates/application/services/OrderService.cs.template"

    def test_classify_unknown_pattern_returns_none(self, example_file_unknown_pattern, sample_analysis):
        """Test that unknown patterns return None."""
        strategy = PatternClassificationStrategy()
        result = strategy.classify(example_file_unknown_pattern, sample_analysis)

        assert result is None

    def test_classify_entity(self, sample_analysis):
        """Test classification of Entity pattern."""
        strategy = PatternClassificationStrategy()
        example = ExampleFile(
            path="src/Models/UserEntity.cs",
            purpose="User entity",
            layer=None,
        )
        result = strategy.classify(example, sample_analysis)

        assert result is not None
        assert result == "templates/domain/entities/UserEntity.cs.template"

    def test_classify_view(self, sample_analysis):
        """Test classification of View pattern."""
        strategy = PatternClassificationStrategy()
        example = ExampleFile(
            path="src/UI/LoginView.cs",
            purpose="Login view",
            layer=None,
        )
        result = strategy.classify(example, sample_analysis)

        assert result is not None
        assert result == "templates/presentation/views/LoginView.cs.template"

    def test_classify_engine(self, sample_analysis):
        """Test classification of Engine pattern."""
        strategy = PatternClassificationStrategy()
        example = ExampleFile(
            path="src/Processing/DataEngine.cs",
            purpose="Data processing engine",
            layer=None,
        )
        result = strategy.classify(example, sample_analysis)

        assert result is not None
        assert result == "templates/infrastructure/engines/DataEngine.cs.template"


# TemplatePathResolver Tests

class TestTemplatePathResolver:
    """Test suite for TemplatePathResolver (orchestrator)."""

    def test_resolve_with_layer_classification(self, example_file_repository_with_layer, sample_analysis):
        """Test that resolver uses LayerClassificationStrategy when layer available."""
        resolver = TemplatePathResolver()
        result = resolver.resolve(example_file_repository_with_layer, sample_analysis)

        assert result == "templates/application/repositories/UserRepository.cs.template"
        assert resolver.classification_stats["LayerClassificationStrategy"] == 1
        assert resolver.total_files == 1

    def test_resolve_with_pattern_fallback(self, example_file_repository_no_layer, sample_analysis):
        """Test that resolver falls back to PatternClassificationStrategy."""
        resolver = TemplatePathResolver()
        result = resolver.resolve(example_file_repository_no_layer, sample_analysis)

        assert result == "templates/application/repositories/ProductRepository.cs.template"
        assert resolver.classification_stats["PatternClassificationStrategy"] == 1
        assert resolver.total_files == 1

    def test_resolve_with_complete_fallback(self, example_file_unknown_pattern, sample_analysis):
        """Test complete fallback to templates/other/."""
        resolver = TemplatePathResolver()
        result = resolver.resolve(example_file_unknown_pattern, sample_analysis)

        assert result == "templates/other/StringHelper.cs.template"
        assert resolver.classification_stats["Fallback"] == 1
        assert len(resolver.warnings) == 1
        assert "Could not classify" in resolver.warnings[0]

    def test_resolve_chain_of_responsibility(self, sample_analysis):
        """Test chain of responsibility with multiple files."""
        resolver = TemplatePathResolver()

        # File 1: Has layer (should use LayerClassificationStrategy)
        file1 = ExampleFile(path="src/UserRepository.cs", purpose="Test", layer="application")
        result1 = resolver.resolve(file1, sample_analysis)
        assert "application/repositories" in result1

        # File 2: No layer but has pattern (should use PatternClassificationStrategy)
        file2 = ExampleFile(path="src/OrderService.cs", purpose="Test", layer=None)
        result2 = resolver.resolve(file2, sample_analysis)
        assert "application/services" in result2

        # File 3: No layer, no pattern (should fallback)
        file3 = ExampleFile(path="src/Helper.cs", purpose="Test", layer=None)
        result3 = resolver.resolve(file3, sample_analysis)
        assert "other/Helper.cs.template" in result3

        # Verify statistics
        assert resolver.classification_stats["LayerClassificationStrategy"] == 1
        assert resolver.classification_stats["PatternClassificationStrategy"] == 1
        assert resolver.classification_stats["Fallback"] == 1
        assert resolver.total_files == 3

    def test_get_classification_summary_basic(self, sample_analysis):
        """Test classification summary generation."""
        resolver = TemplatePathResolver()

        # Process some files
        file1 = ExampleFile(path="src/UserRepository.cs", purpose="Test", layer="application")
        file2 = ExampleFile(path="src/OrderService.cs", purpose="Test", layer="application")
        resolver.resolve(file1, sample_analysis)
        resolver.resolve(file2, sample_analysis)

        summary = resolver.get_classification_summary()

        assert "Template Classification Summary:" in summary
        assert "LayerClassificationStrategy: 2 files (100.0%)" in summary

    def test_get_classification_summary_with_warning(self, sample_analysis):
        """Test classification summary with high fallback rate warning."""
        resolver = TemplatePathResolver()

        # Create scenario with >20% fallback rate
        # 2 successful, 3 fallbacks = 60% fallback rate
        for i in range(2):
            file = ExampleFile(path=f"src/Test{i}Repository.cs", purpose="Test", layer="application")
            resolver.resolve(file, sample_analysis)

        for i in range(3):
            file = ExampleFile(path=f"src/Helper{i}.cs", purpose="Test", layer=None)
            resolver.resolve(file, sample_analysis)

        summary = resolver.get_classification_summary()

        assert "Template Classification Summary:" in summary
        assert "Warning:" in summary
        assert "60.0%" in summary

    def test_get_fallback_rate(self, sample_analysis):
        """Test fallback rate calculation."""
        resolver = TemplatePathResolver()

        # 3 successful, 1 fallback = 25% fallback rate
        for i in range(3):
            file = ExampleFile(path=f"src/Test{i}Repository.cs", purpose="Test", layer="application")
            resolver.resolve(file, sample_analysis)

        file = ExampleFile(path="src/Helper.cs", purpose="Test", layer=None)
        resolver.resolve(file, sample_analysis)

        fallback_rate = resolver.get_fallback_rate()
        assert fallback_rate == 25.0

    def test_get_fallback_rate_zero_files(self):
        """Test fallback rate with zero files."""
        resolver = TemplatePathResolver()
        fallback_rate = resolver.get_fallback_rate()
        assert fallback_rate == 0.0

    def test_warnings_list_populated(self, sample_analysis):
        """Test that warnings list is populated for fallback cases."""
        resolver = TemplatePathResolver()

        # Process files that will fallback
        file1 = ExampleFile(path="src/Helper1.cs", purpose="Test", layer=None)
        file2 = ExampleFile(path="src/Helper2.cs", purpose="Test", layer=None)
        resolver.resolve(file1, sample_analysis)
        resolver.resolve(file2, sample_analysis)

        assert len(resolver.warnings) == 2
        assert "Could not classify: src/Helper1.cs" in resolver.warnings
        assert "Could not classify: src/Helper2.cs" in resolver.warnings

    def test_ambiguous_pattern_first_match(self, sample_analysis):
        """Test that ambiguous patterns use last suffix match."""
        resolver = TemplatePathResolver()

        # File with multiple pattern matches (e.g., "UserRepositoryService")
        # Should match "Service" because it's the last suffix (filename.endswith())
        file = ExampleFile(
            path="src/UserRepositoryService.cs",
            purpose="Test",
            layer="application"
        )
        result = resolver.resolve(file, sample_analysis)

        # Should match Service pattern (last suffix in filename)
        assert "services" in result


# Integration Tests

class TestIntegration:
    """Integration tests for the complete path resolution system."""

    def test_typical_dotnet_maui_project(self, sample_analysis):
        """Test classification of typical .NET MAUI project structure."""
        resolver = TemplatePathResolver()

        # Typical .NET MAUI files
        files = [
            ExampleFile(path="Services/ConfigurationService.cs", purpose="Config service", layer="application"),
            ExampleFile(path="Services/ApiClientService.cs", purpose="API client", layer="application"),
            ExampleFile(path="Repositories/ConfigurationRepository.cs", purpose="Config repo", layer="application"),
            ExampleFile(path="Repositories/UserRepository.cs", purpose="User repo", layer="application"),
            ExampleFile(path="Models/ConfigurationPayload.cs", purpose="Config entity", layer="domain"),
            ExampleFile(path="Errors/AppErrors.cs", purpose="App errors", layer="domain"),
            ExampleFile(path="Engines/ConfigurationEngine.cs", purpose="Config engine", layer="infrastructure"),
            ExampleFile(path="Views/DomainCameraView.cs", purpose="Camera view", layer="presentation"),
        ]

        results = [resolver.resolve(f, sample_analysis) for f in files]

        # Verify all classified correctly (not in 'other')
        for result in results:
            assert "other" not in result

        # Verify fallback rate is low
        fallback_rate = resolver.get_fallback_rate()
        assert fallback_rate == 0.0

        # Verify statistics
        assert resolver.classification_stats["LayerClassificationStrategy"] == 8
        assert resolver.total_files == 8

    def test_mixed_quality_project(self, sample_analysis):
        """Test project with mixed quality (some files have layer, some don't)."""
        resolver = TemplatePathResolver()

        files = [
            # Good: Has layer info
            ExampleFile(path="Services/UserService.cs", purpose="User service", layer="application"),
            # OK: No layer but has pattern
            ExampleFile(path="Data/OrderRepository.cs", purpose="Order repo", layer=None),
            # Poor: No layer, no pattern
            ExampleFile(path="Utilities/StringHelper.cs", purpose="Helper", layer=None),
        ]

        results = [resolver.resolve(f, sample_analysis) for f in files]

        # Verify expected paths
        assert results[0] == "templates/application/services/UserService.cs.template"
        assert results[1] == "templates/application/repositories/OrderRepository.cs.template"
        assert results[2] == "templates/other/StringHelper.cs.template"

        # Verify statistics
        assert resolver.classification_stats["LayerClassificationStrategy"] == 1
        assert resolver.classification_stats["PatternClassificationStrategy"] == 1
        assert resolver.classification_stats["Fallback"] == 1

        # Fallback rate should be 33.3%
        fallback_rate = resolver.get_fallback_rate()
        assert abs(fallback_rate - 33.33) < 0.1
