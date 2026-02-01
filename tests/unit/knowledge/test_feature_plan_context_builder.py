"""
TDD Tests for FeaturePlanContextBuilder (RED Phase)

These tests define the expected behavior of FeaturePlanContextBuilder.
Tests will FAIL initially until implementation is complete.

Test Strategy:
- Mock GraphitiClient to avoid Neo4j dependency
- Mock FeatureDetector where appropriate
- Use async fixtures for async tests
- Target coverage: 85%+
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import Optional, List, Dict, Any

from guardkit.knowledge.feature_plan_context import (
    FeaturePlanContext,
    FeaturePlanContextBuilder,
)
from guardkit.knowledge.feature_detector import FeatureDetector
from guardkit.knowledge.graphiti_client import GraphitiClient


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project root directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def feature_spec_content() -> str:
    """Sample feature specification markdown content."""
    return """---
id: FEAT-GR-003
title: Graphiti Enhanced Context
---

# Feature Specification

Enhance feature planning with rich context from Graphiti.

## Success Criteria
- Query related features
- Query relevant patterns
- Query warnings from past implementations

## Technical Requirements
- Integrate GraphitiClient
- Parse feature specs
- Build context dataclass
"""


@pytest.fixture
def mock_graphiti_client() -> MagicMock:
    """Create a mock GraphitiClient."""
    client = MagicMock(spec=GraphitiClient)
    client.enabled = True
    client.search = AsyncMock(return_value=[])
    client.add_episode = AsyncMock(return_value="episode-uuid-123")
    return client


@pytest.fixture
def mock_feature_detector(project_root: Path) -> MagicMock:
    """Create a mock FeatureDetector."""
    detector = MagicMock(spec=FeatureDetector)
    detector.detect_feature_id = MagicMock(return_value=None)
    detector.find_feature_spec = MagicMock(return_value=None)
    detector.find_related_features = MagicMock(return_value=[])
    return detector


# =========================================================================
# 1. INITIALIZATION TESTS (3 tests)
# =========================================================================


class TestFeaturePlanContextBuilderInitialization:
    """Test FeaturePlanContextBuilder initialization."""

    def test_constructor_accepts_project_root_path(self, project_root: Path):
        """Test constructor accepts Path object for project_root."""
        builder = FeaturePlanContextBuilder(project_root=project_root)
        assert builder is not None
        # Constructor should store project_root
        assert hasattr(builder, "project_root")

    def test_constructor_handles_none_project_root(self):
        """Test constructor raises TypeError when project_root is None."""
        with pytest.raises(TypeError, match="project_root cannot be None"):
            FeaturePlanContextBuilder(project_root=None)

    def test_constructor_initializes_dependencies(self, project_root: Path):
        """Test constructor initializes FeatureDetector and GraphitiClient."""
        builder = FeaturePlanContextBuilder(project_root=project_root)
        # Should have feature_detector attribute
        assert hasattr(builder, "feature_detector")
        # Should have graphiti_client attribute
        assert hasattr(builder, "graphiti_client")


# =========================================================================
# 2. BUILD_CONTEXT BASIC TESTS (4 tests)
# =========================================================================


class TestBuildContextBasic:
    """Test build_context basic functionality."""

    @pytest.mark.asyncio
    async def test_returns_feature_plan_context_instance(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test build_context returns FeaturePlanContext instance."""
        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement authentication feature",
            context_files=[],
            tech_stack="python",
        )

        assert isinstance(result, FeaturePlanContext)

    @pytest.mark.asyncio
    async def test_with_description_containing_feature_id(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test build_context with description containing feature ID."""
        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement FEAT-GR-003 for enhanced context",
            context_files=[],
            tech_stack="python",
        )

        assert isinstance(result, FeaturePlanContext)
        # Should detect FEAT-GR-003 from description

    @pytest.mark.asyncio
    async def test_with_explicit_context_files_parameter(
        self, project_root: Path, mock_graphiti_client: MagicMock, tmp_path: Path
    ):
        """Test build_context with explicit context_files parameter."""
        # Create some context files
        context_file = tmp_path / "context.md"
        context_file.write_text("Context information")

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature",
            context_files=[context_file],
            tech_stack="python",
        )

        assert isinstance(result, FeaturePlanContext)
        # Should use provided context files

    @pytest.mark.asyncio
    async def test_with_tech_stack_parameter(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test build_context with tech_stack parameter."""
        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack="typescript"
        )

        assert isinstance(result, FeaturePlanContext)
        # Should use tech_stack to query patterns_{tech_stack}


# =========================================================================
# 3. FEATURE DETECTION INTEGRATION TESTS (3 tests)
# =========================================================================


class TestFeatureDetectionIntegration:
    """Test integration with FeatureDetector."""

    @pytest.mark.asyncio
    async def test_auto_detects_feature_id_from_description(
        self,
        project_root: Path,
        mock_graphiti_client: MagicMock,
        mock_feature_detector: MagicMock,
    ):
        """Test auto-detection of feature ID from description."""
        mock_feature_detector.detect_feature_id.return_value = "FEAT-GR-003"

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client
        builder.feature_detector = mock_feature_detector

        await builder.build_context(
            description="Implement FEAT-GR-003 for context",
            context_files=[],
            tech_stack="python",
        )

        # Should have called detect_feature_id
        mock_feature_detector.detect_feature_id.assert_called_once_with(
            "Implement FEAT-GR-003 for context"
        )

    @pytest.mark.asyncio
    async def test_finds_feature_spec_file_when_feature_id_detected(
        self,
        project_root: Path,
        mock_graphiti_client: MagicMock,
        mock_feature_detector: MagicMock,
        tmp_path: Path,
    ):
        """Test finding feature spec file when feature ID is detected."""
        # Create a feature spec file
        feature_spec_path = tmp_path / "FEAT-GR-003-enhanced-context.md"
        feature_spec_path.write_text(
            """---
id: FEAT-GR-003
title: Enhanced Context
---

Feature specification content.
"""
        )

        mock_feature_detector.detect_feature_id.return_value = "FEAT-GR-003"
        mock_feature_detector.find_feature_spec.return_value = feature_spec_path

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client
        builder.feature_detector = mock_feature_detector

        await builder.build_context(
            description="Implement FEAT-GR-003", context_files=[], tech_stack="python"
        )

        # Should have called find_feature_spec
        mock_feature_detector.find_feature_spec.assert_called_once_with("FEAT-GR-003")

    @pytest.mark.asyncio
    async def test_handles_no_feature_id_gracefully(
        self,
        project_root: Path,
        mock_graphiti_client: MagicMock,
        mock_feature_detector: MagicMock,
    ):
        """Test graceful handling when no feature ID is detected."""
        mock_feature_detector.detect_feature_id.return_value = None

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client
        builder.feature_detector = mock_feature_detector

        result = await builder.build_context(
            description="Implement some feature", context_files=[], tech_stack="python"
        )

        # Should still return valid context
        assert isinstance(result, FeaturePlanContext)
        # Should not crash or raise exception


# =========================================================================
# 4. GRAPHITI QUERY TESTS (6 tests)
# =========================================================================


class TestGraphitiQueries:
    """Test Graphiti query integration."""

    @pytest.mark.asyncio
    async def test_queries_related_features_group(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test querying related_features group."""
        mock_graphiti_client.search.return_value = [
            {
                "uuid": "related-1",
                "fact": "Related feature 1",
                "name": "FEAT-GR-001",
            }
        ]

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack="python"
        )

        # Should have queried related_features
        assert mock_graphiti_client.search.called
        # Check if search was called with group containing "related_features" or similar
        calls = mock_graphiti_client.search.call_args_list
        # At least one call should mention related features or feature_specs
        assert any("feature" in str(call).lower() for call in calls)

    @pytest.mark.asyncio
    async def test_queries_patterns_tech_stack_group(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test querying patterns_{tech_stack} group."""
        mock_graphiti_client.search.return_value = [
            {"uuid": "pattern-1", "fact": "Pattern for python", "name": "Repository"}
        ]

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack="python"
        )

        # Should have queried patterns group
        calls = mock_graphiti_client.search.call_args_list
        # At least one call should mention patterns
        assert any("pattern" in str(call).lower() for call in calls)

    @pytest.mark.asyncio
    async def test_queries_failure_patterns_group(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test querying failure_patterns group."""
        mock_graphiti_client.search.return_value = [
            {
                "uuid": "failure-1",
                "fact": "Avoid this approach",
                "name": "Anti-pattern",
            }
        ]

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack="python"
        )

        # Should have queried failure_patterns
        calls = mock_graphiti_client.search.call_args_list
        # At least one call should mention failures or warnings
        assert any(
            "failure" in str(call).lower() or "warning" in str(call).lower()
            for call in calls
        )

    @pytest.mark.asyncio
    async def test_queries_role_constraints_group(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test querying role_constraints group (AutoBuild support)."""
        mock_graphiti_client.search.return_value = [
            {
                "uuid": "role-1",
                "fact": "Player must implement, Coach must validate",
                "name": "Role Constraints",
            }
        ]

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack="python"
        )

        # Should have queried role_constraints
        calls = mock_graphiti_client.search.call_args_list
        # At least one call should mention roles or constraints
        assert any("role" in str(call).lower() for call in calls)

    @pytest.mark.asyncio
    async def test_queries_quality_gate_configs_group(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test querying quality_gate_configs group (AutoBuild support)."""
        mock_graphiti_client.search.return_value = [
            {
                "uuid": "gate-1",
                "fact": "Coverage threshold: 80%",
                "name": "Quality Gates",
            }
        ]

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack="python"
        )

        # Should have queried quality_gate_configs
        calls = mock_graphiti_client.search.call_args_list
        # At least one call should mention quality or gates
        assert any("quality" in str(call).lower() or "gate" in str(call).lower() for call in calls)

    @pytest.mark.asyncio
    async def test_queries_implementation_modes_group(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test querying implementation_modes group (AutoBuild support)."""
        mock_graphiti_client.search.return_value = [
            {
                "uuid": "mode-1",
                "fact": "Use TDD for complex logic",
                "name": "Implementation Modes",
            }
        ]

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack="python"
        )

        # Should have queried implementation_modes
        calls = mock_graphiti_client.search.call_args_list
        # At least one call should mention implementation or modes
        assert any(
            "implementation" in str(call).lower() or "mode" in str(call).lower()
            for call in calls
        )


# =========================================================================
# 5. GRACEFUL DEGRADATION TESTS (3 tests)
# =========================================================================


class TestGracefulDegradation:
    """Test graceful degradation when Graphiti is unavailable."""

    @pytest.mark.asyncio
    async def test_handles_graphiti_disabled(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test handling when Graphiti is disabled."""
        mock_graphiti_client.enabled = False

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack="python"
        )

        # Should return valid context with empty fields
        assert isinstance(result, FeaturePlanContext)
        assert result.related_features == []
        assert result.relevant_patterns == []
        assert result.warnings == []
        assert result.role_constraints == []
        assert result.quality_gate_configs == []
        assert result.implementation_modes == []

    @pytest.mark.asyncio
    async def test_handles_graphiti_query_failures_gracefully(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test graceful handling of Graphiti query failures."""
        # Simulate query failures
        mock_graphiti_client.enabled = True
        mock_graphiti_client.search.side_effect = Exception("Connection error")

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack="python"
        )

        # Should still return valid context
        assert isinstance(result, FeaturePlanContext)
        # Should have empty fields due to failed queries
        assert result.related_features == []
        assert result.relevant_patterns == []

    @pytest.mark.asyncio
    async def test_returns_valid_context_even_when_all_queries_fail(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test returns valid FeaturePlanContext even when all queries fail."""
        mock_graphiti_client.enabled = True
        mock_graphiti_client.search.side_effect = Exception("All queries failed")

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack="python"
        )

        # Must return valid FeaturePlanContext
        assert isinstance(result, FeaturePlanContext)
        # All enrichment fields should be empty but structure intact
        assert hasattr(result, "feature_spec")
        assert hasattr(result, "related_features")
        assert hasattr(result, "relevant_patterns")
        assert hasattr(result, "similar_implementations")
        assert hasattr(result, "project_architecture")
        assert hasattr(result, "warnings")
        assert hasattr(result, "role_constraints")
        assert hasattr(result, "quality_gate_configs")
        assert hasattr(result, "implementation_modes")


# =========================================================================
# 6. INTEGRATION TESTS (2 tests)
# =========================================================================


class TestIntegration:
    """Test full integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_flow_with_all_components(
        self,
        project_root: Path,
        mock_graphiti_client: MagicMock,
        mock_feature_detector: MagicMock,
        tmp_path: Path,
    ):
        """Test full flow with all components working together."""
        # Setup feature spec file
        feature_spec_path = tmp_path / "FEAT-GR-003.md"
        feature_spec_path.write_text(
            """---
id: FEAT-GR-003
title: Enhanced Context
---

Feature specification.
"""
        )

        # Configure mocks
        mock_feature_detector.detect_feature_id.return_value = "FEAT-GR-003"
        mock_feature_detector.find_feature_spec.return_value = feature_spec_path
        mock_graphiti_client.enabled = True
        mock_graphiti_client.search.return_value = [
            {"uuid": "test-1", "fact": "Test fact", "name": "Test"}
        ]
        mock_graphiti_client.add_episode.return_value = "episode-uuid"

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client
        builder.feature_detector = mock_feature_detector

        result = await builder.build_context(
            description="Implement FEAT-GR-003 for enhanced context",
            context_files=[],
            tech_stack="python",
        )

        # Verify all components interacted
        assert isinstance(result, FeaturePlanContext)
        mock_feature_detector.detect_feature_id.assert_called_once()
        mock_feature_detector.find_feature_spec.assert_called_once()
        assert mock_graphiti_client.search.call_count >= 1

    @pytest.mark.asyncio
    async def test_context_includes_all_expected_fields(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test that returned context includes all expected fields."""
        mock_graphiti_client.enabled = True
        mock_graphiti_client.search.return_value = [
            {"uuid": "test-1", "fact": "Test fact", "name": "Test"}
        ]

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack="python"
        )

        # Verify all required fields exist
        assert hasattr(result, "feature_spec")
        assert hasattr(result, "related_features")
        assert hasattr(result, "relevant_patterns")
        assert hasattr(result, "similar_implementations")
        assert hasattr(result, "project_architecture")
        assert hasattr(result, "warnings")

        # Verify AutoBuild support fields
        assert hasattr(result, "role_constraints")
        assert hasattr(result, "quality_gate_configs")
        assert hasattr(result, "implementation_modes")

        # Verify all fields are correct types
        assert isinstance(result.feature_spec, dict)
        assert isinstance(result.related_features, list)
        assert isinstance(result.relevant_patterns, list)
        assert isinstance(result.similar_implementations, list)
        assert isinstance(result.project_architecture, dict)
        assert isinstance(result.warnings, list)
        assert isinstance(result.role_constraints, list)
        assert isinstance(result.quality_gate_configs, list)
        assert isinstance(result.implementation_modes, list)


# =========================================================================
# EDGE CASES AND BOUNDARY CONDITIONS
# =========================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_description(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test build_context with empty description."""
        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="", context_files=[], tech_stack="python"
        )

        assert isinstance(result, FeaturePlanContext)

    @pytest.mark.asyncio
    async def test_empty_tech_stack(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test build_context with empty tech_stack."""
        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=[], tech_stack=""
        )

        assert isinstance(result, FeaturePlanContext)

    @pytest.mark.asyncio
    async def test_none_context_files(
        self, project_root: Path, mock_graphiti_client: MagicMock
    ):
        """Test build_context with None context_files."""
        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature", context_files=None, tech_stack="python"
        )

        assert isinstance(result, FeaturePlanContext)

    @pytest.mark.asyncio
    async def test_nonexistent_context_files(
        self, project_root: Path, mock_graphiti_client: MagicMock, tmp_path: Path
    ):
        """Test build_context with non-existent context files."""
        nonexistent_file = tmp_path / "nonexistent.md"

        builder = FeaturePlanContextBuilder(project_root=project_root)
        builder.graphiti_client = mock_graphiti_client

        result = await builder.build_context(
            description="Implement feature",
            context_files=[nonexistent_file],
            tech_stack="python",
        )

        # Should handle gracefully
        assert isinstance(result, FeaturePlanContext)
