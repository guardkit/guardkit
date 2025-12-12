"""
Unit tests for PathPatternInferrer

Tests intelligent path pattern inference from codebase analysis.
"""

from datetime import datetime

import pytest

from installer.core.lib.codebase_analyzer.models import (
    ArchitectureInfo,
    CodebaseAnalysis,
    ConfidenceLevel,
    ConfidenceScore,
    LayerInfo,
    QualityInfo,
    TechnologyInfo,
)
from installer.core.lib.template_generator.path_pattern_inferrer import (
    PathPatternInferrer,
)


@pytest.fixture
def minimal_analysis():
    """Create minimal CodebaseAnalysis for testing."""
    return CodebaseAnalysis(
        codebase_path="/test/path",
        analyzed_at=datetime.now(),
        technology=TechnologyInfo(
            primary_language="Python",
            frameworks=["FastAPI"],
            testing_frameworks=["pytest"],
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=95.0
            )
        ),
        architecture=ArchitectureInfo(
            patterns=["Repository"],
            architectural_style="Layered",
            layers=[],
            dependency_flow="Inward toward domain",
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=90.0
            )
        ),
        quality=QualityInfo(
            overall_score=85.0,
            solid_compliance=80.0,
            dry_compliance=85.0,
            yagni_compliance=90.0,
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=88.0
            )
        ),
    )


@pytest.fixture
def analysis_with_layers():
    """Create CodebaseAnalysis with layer information."""
    return CodebaseAnalysis(
        codebase_path="/test/path",
        analyzed_at=datetime.now(),
        technology=TechnologyInfo(
            primary_language="Python",
            frameworks=["FastAPI"],
            testing_frameworks=["pytest"],
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=95.0
            )
        ),
        architecture=ArchitectureInfo(
            patterns=["Repository"],
            architectural_style="Clean Architecture",
            layers=[
                LayerInfo(
                    name="Infrastructure",
                    description="Data access and persistence",
                    typical_files=[
                        "src/infrastructure/repositories/user_repository.py",
                        "src/infrastructure/database/connection.py"
                    ],
                    dependencies=["Domain"]
                ),
                LayerInfo(
                    name="Presentation",
                    description="API endpoints and views",
                    typical_files=[
                        "src/presentation/api/routes.py",
                        "src/presentation/views/user_view.py"
                    ],
                    dependencies=["Application"]
                )
            ],
            dependency_flow="Inward toward domain",
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=92.0
            )
        ),
        quality=QualityInfo(
            overall_score=88.0,
            solid_compliance=85.0,
            dry_compliance=87.0,
            yagni_compliance=92.0,
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=89.0
            )
        ),
    )


class TestPathPatternInferrerInit:
    """Test PathPatternInferrer initialization."""

    def test_initializes_with_analysis(self, minimal_analysis):
        """Test inferrer initializes with CodebaseAnalysis."""
        inferrer = PathPatternInferrer(minimal_analysis)

        assert inferrer.analysis == minimal_analysis
        assert isinstance(inferrer._layer_paths, dict)
        assert isinstance(inferrer._extension_patterns, dict)

    def test_builds_extension_patterns_for_python(self, minimal_analysis):
        """Test extension patterns for Python projects."""
        inferrer = PathPatternInferrer(minimal_analysis)

        assert 'source' in inferrer._extension_patterns
        assert 'test' in inferrer._extension_patterns
        assert '**/*.py' in inferrer._extension_patterns['source']

    def test_builds_extension_patterns_for_typescript(self):
        """Test extension patterns for TypeScript projects."""
        analysis = CodebaseAnalysis(
            codebase_path="/test/path",
            analyzed_at=datetime.now(),
            technology=TechnologyInfo(
                primary_language="TypeScript",
                frameworks=["React"],
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
            ),
            architecture=ArchitectureInfo(
                patterns=[],
                architectural_style="Component-based",
                dependency_flow="One-way data flow",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=85.0,
                solid_compliance=80.0,
                dry_compliance=85.0,
                yagni_compliance=90.0,
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=88.0)
            ),
        )

        inferrer = PathPatternInferrer(analysis)

        assert '**/*.{ts,tsx,js,jsx}' in inferrer._extension_patterns['source']


class TestBuildLayerPaths:
    """Test layer path extraction."""

    def test_builds_layer_paths_from_analysis(self, analysis_with_layers):
        """Test extracting layer paths from typical_files."""
        inferrer = PathPatternInferrer(analysis_with_layers)

        assert 'infrastructure' in inferrer._layer_paths
        assert 'presentation' in inferrer._layer_paths

        # Check Infrastructure layer paths
        infra_paths = inferrer._layer_paths['infrastructure']
        assert any('repositories' in path for path in infra_paths)
        assert any('database' in path for path in infra_paths)

        # Check Presentation layer paths
        pres_paths = inferrer._layer_paths['presentation']
        assert any('api' in path for path in pres_paths)
        assert any('views' in path for path in pres_paths)

    def test_handles_empty_layers(self, minimal_analysis):
        """Test handling analysis with no layers."""
        inferrer = PathPatternInferrer(minimal_analysis)

        assert inferrer._layer_paths == {}


class TestInferForAgent:
    """Test main inference method."""

    def test_infers_from_layer_paths(self, analysis_with_layers):
        """Test path inference from layer information."""
        inferrer = PathPatternInferrer(analysis_with_layers)

        # Repository specialist should match Infrastructure layer
        paths = inferrer.infer_for_agent("repository-specialist", ["SQLAlchemy"])

        assert paths  # Should have patterns
        assert any('repositories' in paths.lower() for paths in paths.split(', '))

    def test_infers_from_technology(self, minimal_analysis):
        """Test path inference from technology."""
        inferrer = PathPatternInferrer(minimal_analysis)

        paths = inferrer.infer_for_agent("api-specialist", ["FastAPI"])

        assert paths
        # Should include FastAPI-specific patterns
        assert 'router' in paths.lower() or 'api' in paths.lower()

    def test_fallback_to_name_based(self, minimal_analysis):
        """Test fallback to name-based inference."""
        inferrer = PathPatternInferrer(minimal_analysis)

        # Agent with no technology matches, should fall back to name
        paths = inferrer.infer_for_agent("viewmodel-specialist", [])

        assert paths
        assert 'viewmodel' in paths.lower()

    def test_deduplicates_patterns(self, analysis_with_layers):
        """Test pattern deduplication."""
        inferrer = PathPatternInferrer(analysis_with_layers)

        # Multiple sources might suggest same pattern
        paths = inferrer.infer_for_agent("repository-specialist", ["SQLAlchemy"])
        path_list = paths.split(', ')

        # Should not have duplicates
        assert len(path_list) == len(set(path_list))

    def test_limits_to_five_patterns(self, analysis_with_layers):
        """Test limiting output to 5 patterns maximum."""
        inferrer = PathPatternInferrer(analysis_with_layers)

        # Create scenario with many potential patterns
        paths = inferrer.infer_for_agent(
            "database-repository-specialist",
            ["SQLAlchemy", "Alembic", "Pytest"]
        )
        path_list = paths.split(', ')

        assert len(path_list) <= 5

    def test_returns_empty_for_unknown_agent(self, minimal_analysis):
        """Test handling of unrecognized agent names."""
        inferrer = PathPatternInferrer(minimal_analysis)

        # Completely unknown agent type
        paths = inferrer.infer_for_agent("unknown-specialist", [])

        # Should return empty string (no patterns)
        assert paths == ""

    def test_handles_multiple_technologies(self, minimal_analysis):
        """Test agent with multiple technologies."""
        inferrer = PathPatternInferrer(minimal_analysis)

        paths = inferrer.infer_for_agent(
            "api-specialist",
            ["FastAPI", "SQLAlchemy", "Pytest"]
        )

        # Should include patterns from multiple technologies
        assert paths
        path_list = paths.split(', ')
        assert len(path_list) >= 2


class TestMatchesLayer:
    """Test layer matching logic."""

    def test_matches_infrastructure_keywords(self):
        """Test matching Infrastructure layer keywords."""
        analysis = CodebaseAnalysis(
            codebase_path="/test",
            analyzed_at=datetime.now(),
            technology=TechnologyInfo(
                primary_language="Python",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
            ),
            architecture=ArchitectureInfo(
                patterns=[],
                architectural_style="Layered",
                dependency_flow="Inward",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=85.0,
                solid_compliance=80.0,
                dry_compliance=85.0,
                yagni_compliance=90.0,
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=88.0)
            ),
        )
        inferrer = PathPatternInferrer(analysis)

        assert inferrer._matches_layer("repository-specialist", "infrastructure")
        assert inferrer._matches_layer("database-handler", "infrastructure")
        assert inferrer._matches_layer("data-access-layer", "infrastructure")

    def test_matches_presentation_keywords(self):
        """Test matching Presentation layer keywords."""
        analysis = CodebaseAnalysis(
            codebase_path="/test",
            analyzed_at=datetime.now(),
            technology=TechnologyInfo(
                primary_language="Python",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
            ),
            architecture=ArchitectureInfo(
                patterns=[],
                architectural_style="Layered",
                dependency_flow="Inward",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=85.0,
                solid_compliance=80.0,
                dry_compliance=85.0,
                yagni_compliance=90.0,
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=88.0)
            ),
        )
        inferrer = PathPatternInferrer(analysis)

        assert inferrer._matches_layer("viewmodel-specialist", "presentation")
        assert inferrer._matches_layer("ui-component-builder", "presentation")
        assert inferrer._matches_layer("page-controller", "presentation")

    def test_does_not_match_unrelated_layer(self):
        """Test no match for unrelated layer."""
        analysis = CodebaseAnalysis(
            codebase_path="/test",
            analyzed_at=datetime.now(),
            technology=TechnologyInfo(
                primary_language="Python",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
            ),
            architecture=ArchitectureInfo(
                patterns=[],
                architectural_style="Layered",
                dependency_flow="Inward",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=85.0,
                solid_compliance=80.0,
                dry_compliance=85.0,
                yagni_compliance=90.0,
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=88.0)
            ),
        )
        inferrer = PathPatternInferrer(analysis)

        assert not inferrer._matches_layer("repository-specialist", "presentation")
        assert not inferrer._matches_layer("viewmodel-specialist", "infrastructure")


class TestGetTechnologyPattern:
    """Test technology pattern lookup."""

    def test_returns_pattern_for_known_technology(self, minimal_analysis):
        """Test returning pattern for known technologies."""
        inferrer = PathPatternInferrer(minimal_analysis)

        assert inferrer._get_technology_pattern("FastAPI") is not None
        assert inferrer._get_technology_pattern("React") is not None
        assert inferrer._get_technology_pattern("SQLAlchemy") is not None

    def test_returns_none_for_unknown_technology(self, minimal_analysis):
        """Test returning None for unknown technologies."""
        inferrer = PathPatternInferrer(minimal_analysis)

        assert inferrer._get_technology_pattern("UnknownFramework") is None


class TestFallbackInference:
    """Test fallback name-based inference."""

    def test_infers_common_agent_types(self, minimal_analysis):
        """Test inference for common agent types."""
        inferrer = PathPatternInferrer(minimal_analysis)

        # Repository
        patterns = inferrer._fallback_inference("repository-specialist")
        assert any('repositories' in p.lower() for p in patterns)

        # Service
        patterns = inferrer._fallback_inference("service-handler")
        assert any('services' in p.lower() for p in patterns)

        # Testing
        patterns = inferrer._fallback_inference("testing-specialist")
        assert any('tests' in p.lower() or 'test' in p.lower() for p in patterns)

    def test_returns_empty_for_unknown_type(self, minimal_analysis):
        """Test returning empty list for unknown agent type."""
        inferrer = PathPatternInferrer(minimal_analysis)

        patterns = inferrer._fallback_inference("completely-unknown-agent")
        assert patterns == []


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_agent_without_technologies(self, analysis_with_layers):
        """Test handling agent with empty technologies list."""
        inferrer = PathPatternInferrer(analysis_with_layers)

        # Should still work with layer matching
        paths = inferrer.infer_for_agent("repository-specialist", [])
        assert paths  # Should get patterns from layer matching

    def test_handles_case_insensitive_matching(self, minimal_analysis):
        """Test case-insensitive agent name matching."""
        inferrer = PathPatternInferrer(minimal_analysis)

        paths1 = inferrer.infer_for_agent("Repository-Specialist", [])
        paths2 = inferrer.infer_for_agent("repository-specialist", [])
        paths3 = inferrer.infer_for_agent("REPOSITORY-SPECIALIST", [])

        # All should produce similar results
        assert paths1 == paths2 == paths3

    def test_handles_empty_typical_files(self):
        """Test handling layers with empty typical_files."""
        analysis = CodebaseAnalysis(
            codebase_path="/test",
            analyzed_at=datetime.now(),
            technology=TechnologyInfo(
                primary_language="Python",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
            ),
            architecture=ArchitectureInfo(
                patterns=[],
                architectural_style="Layered",
                layers=[
                    LayerInfo(
                        name="Infrastructure",
                        description="Data layer",
                        typical_files=[],  # Empty
                        dependencies=[]
                    )
                ],
                dependency_flow="Inward",
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
            ),
            quality=QualityInfo(
                overall_score=85.0,
                solid_compliance=80.0,
                dry_compliance=85.0,
                yagni_compliance=90.0,
                confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=88.0)
            ),
        )

        inferrer = PathPatternInferrer(analysis)

        # Should still work, falling back to other methods
        paths = inferrer.infer_for_agent("repository-specialist", [])
        assert isinstance(paths, str)
