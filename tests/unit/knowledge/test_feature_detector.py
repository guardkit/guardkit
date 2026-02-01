"""
Comprehensive Test Suite for FeatureDetector Class

Tests feature ID detection, feature spec discovery, and related feature finding.

Coverage Target: >=85%
Test Count: 15+ tests

NOTE: These tests are designed to FAIL in TDD RED phase because
the FeatureDetector class does not exist yet.
"""

import pytest
from pathlib import Path
from guardkit.knowledge.feature_detector import FeatureDetector


@pytest.fixture
def temp_project_root(tmp_path):
    """Create a temporary project root directory."""
    return tmp_path


@pytest.fixture
def feature_detector(temp_project_root):
    """Create a FeatureDetector instance for testing."""
    return FeatureDetector(project_root=temp_project_root)


@pytest.fixture
def project_with_features(tmp_path):
    """Create a project with feature directories and spec files."""
    # Create feature directories
    docs_features = tmp_path / "docs" / "features"
    guardkit_features = tmp_path / ".guardkit" / "features"
    features_dir = tmp_path / "features"

    docs_features.mkdir(parents=True)
    guardkit_features.mkdir(parents=True)
    features_dir.mkdir(parents=True)

    # Create feature spec files
    (docs_features / "FEAT-GR-003-graphiti-enhanced-context.md").write_text(
        "# Graphiti Enhanced Context\n\nFeature description..."
    )
    (guardkit_features / "FEAT-SKEL-001-skeleton-workflow.md").write_text(
        "# Skeleton Workflow\n\nFeature description..."
    )
    (features_dir / "FEAT-AUTH-123-oauth-integration.md").write_text(
        "# OAuth Integration\n\nFeature description..."
    )

    # Create related features (same prefix)
    (docs_features / "FEAT-GR-001-graphiti-mvp.md").write_text(
        "# Graphiti MVP\n\nFeature description..."
    )
    (docs_features / "FEAT-GR-002-graphiti-persistence.md").write_text(
        "# Graphiti Persistence\n\nFeature description..."
    )

    # Create unrelated feature
    (features_dir / "FEAT-UI-001-dashboard.md").write_text(
        "# Dashboard UI\n\nFeature description..."
    )

    return tmp_path


# ============================================================================
# 1. Feature ID Detection Tests (5 tests)
# ============================================================================

class TestDetectFeatureId:
    """Test feature ID extraction from descriptions."""

    def test_detect_valid_feature_id_simple(self, feature_detector):
        """Test detection of simple feature ID (FEAT-XX-NNN)."""
        description = "Implement FEAT-GR-001 for graphiti integration"
        result = feature_detector.detect_feature_id(description)
        assert result == "FEAT-GR-001"

    def test_detect_valid_feature_id_complex(self, feature_detector):
        """Test detection of complex feature ID with multiple segments."""
        description = "Work on FEAT-SKEL-001 skeleton workflow"
        result = feature_detector.detect_feature_id(description)
        assert result == "FEAT-SKEL-001"

    def test_detect_feature_id_with_alphanumeric_prefix(self, feature_detector):
        """Test detection with alphanumeric prefix (FEAT-A1B2-123)."""
        description = "Building FEAT-AUTH-123 for OAuth support"
        result = feature_detector.detect_feature_id(description)
        assert result == "FEAT-AUTH-123"

    def test_detect_feature_id_returns_none_when_no_pattern(self, feature_detector):
        """Test that None is returned when no feature ID pattern is found."""
        description = "Just a regular task description with no feature ID"
        result = feature_detector.detect_feature_id(description)
        assert result is None

    def test_detect_feature_id_returns_none_for_empty_string(self, feature_detector):
        """Test that None is returned for empty description."""
        result = feature_detector.detect_feature_id("")
        assert result is None

    def test_detect_feature_id_case_sensitive(self, feature_detector):
        """Test that feature ID detection is case-sensitive."""
        description = "Lower case feat-gr-001 should not match"
        result = feature_detector.detect_feature_id(description)
        assert result is None

    def test_detect_feature_id_first_match_when_multiple(self, feature_detector):
        """Test that first feature ID is returned when multiple are present."""
        description = "FEAT-GR-001 and FEAT-GR-002 both mentioned"
        result = feature_detector.detect_feature_id(description)
        assert result == "FEAT-GR-001"


# ============================================================================
# 2. Feature Spec Discovery Tests (5 tests)
# ============================================================================

class TestFindFeatureSpec:
    """Test finding feature spec files by feature ID."""

    def test_find_feature_spec_in_docs_features(self, project_with_features):
        """Test finding feature spec in docs/features/ directory."""
        detector = FeatureDetector(project_root=project_with_features)
        result = detector.find_feature_spec("FEAT-GR-003")

        assert result is not None
        assert isinstance(result, Path)
        assert result.name == "FEAT-GR-003-graphiti-enhanced-context.md"
        assert "docs/features" in str(result)

    def test_find_feature_spec_in_guardkit_features(self, project_with_features):
        """Test finding feature spec in .guardkit/features/ directory."""
        detector = FeatureDetector(project_root=project_with_features)
        result = detector.find_feature_spec("FEAT-SKEL-001")

        assert result is not None
        assert isinstance(result, Path)
        assert result.name == "FEAT-SKEL-001-skeleton-workflow.md"
        assert ".guardkit/features" in str(result)

    def test_find_feature_spec_in_features_root(self, project_with_features):
        """Test finding feature spec in features/ directory."""
        detector = FeatureDetector(project_root=project_with_features)
        result = detector.find_feature_spec("FEAT-AUTH-123")

        assert result is not None
        assert isinstance(result, Path)
        assert result.name == "FEAT-AUTH-123-oauth-integration.md"
        assert str(result).endswith("features/FEAT-AUTH-123-oauth-integration.md")

    def test_find_feature_spec_returns_none_when_not_found(self, project_with_features):
        """Test that None is returned when feature spec doesn't exist."""
        detector = FeatureDetector(project_root=project_with_features)
        result = detector.find_feature_spec("FEAT-NONEXISTENT-999")

        assert result is None

    def test_find_feature_spec_with_missing_directories(self, temp_project_root):
        """Test graceful handling when feature directories don't exist."""
        detector = FeatureDetector(project_root=temp_project_root)
        result = detector.find_feature_spec("FEAT-GR-001")

        assert result is None


# ============================================================================
# 3. Related Features Discovery Tests (5 tests)
# ============================================================================

class TestFindRelatedFeatures:
    """Test finding related features with same prefix."""

    def test_find_related_features_same_prefix(self, project_with_features):
        """Test finding features with the same prefix (FEAT-GR-*)."""
        detector = FeatureDetector(project_root=project_with_features)
        result = detector.find_related_features("FEAT-GR-003")

        assert isinstance(result, list)
        assert len(result) == 2  # FEAT-GR-001 and FEAT-GR-002

        # Verify results are Path objects
        for path in result:
            assert isinstance(path, Path)
            assert "FEAT-GR-" in path.name

        # Verify self is excluded
        filenames = [p.name for p in result]
        assert "FEAT-GR-003-graphiti-enhanced-context.md" not in filenames
        assert "FEAT-GR-001-graphiti-mvp.md" in filenames
        assert "FEAT-GR-002-graphiti-persistence.md" in filenames

    def test_find_related_features_excludes_self(self, project_with_features):
        """Test that the feature itself is excluded from related features."""
        detector = FeatureDetector(project_root=project_with_features)
        result = detector.find_related_features("FEAT-GR-001")

        # Should find GR-002 and GR-003, but not GR-001
        filenames = [p.name for p in result]
        assert "FEAT-GR-001-graphiti-mvp.md" not in filenames
        assert len(result) == 2

    def test_find_related_features_different_prefix_excluded(self, project_with_features):
        """Test that features with different prefixes are excluded."""
        detector = FeatureDetector(project_root=project_with_features)
        result = detector.find_related_features("FEAT-GR-003")

        # Should only find FEAT-GR-* features, not FEAT-UI-* or FEAT-AUTH-*
        filenames = [p.name for p in result]
        for filename in filenames:
            assert filename.startswith("FEAT-GR-")

    def test_find_related_features_returns_empty_when_none(self, project_with_features):
        """Test empty list when no related features exist."""
        detector = FeatureDetector(project_root=project_with_features)
        result = detector.find_related_features("FEAT-UI-001")

        # UI-001 has no related features
        assert isinstance(result, list)
        assert len(result) == 0

    def test_find_related_features_invalid_feature_id(self, feature_detector):
        """Test graceful handling of invalid feature ID format."""
        result = feature_detector.find_related_features("INVALID-ID")

        assert isinstance(result, list)
        assert len(result) == 0


# ============================================================================
# 4. Edge Cases and Error Handling Tests (3 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_detector_with_none_project_root(self):
        """Test that FeatureDetector handles None project root."""
        # This should either raise TypeError or handle gracefully
        with pytest.raises(TypeError):
            FeatureDetector(project_root=None)

    def test_find_feature_spec_with_partial_match(self, project_with_features):
        """Test that partial matches are found (e.g., FEAT-GR without number)."""
        detector = FeatureDetector(project_root=project_with_features)

        # Should find any FEAT-GR-003 file even without full suffix
        result = detector.find_feature_spec("FEAT-GR-003")
        assert result is not None

    def test_default_feature_paths_exist(self, feature_detector):
        """Test that DEFAULT_FEATURE_PATHS class attribute exists."""
        assert hasattr(FeatureDetector, 'DEFAULT_FEATURE_PATHS')
        assert isinstance(FeatureDetector.DEFAULT_FEATURE_PATHS, list)
        assert len(FeatureDetector.DEFAULT_FEATURE_PATHS) == 3
        assert "docs/features" in FeatureDetector.DEFAULT_FEATURE_PATHS
        assert ".guardkit/features" in FeatureDetector.DEFAULT_FEATURE_PATHS
        assert "features" in FeatureDetector.DEFAULT_FEATURE_PATHS


# ============================================================================
# 5. Pattern Matching Tests (2 tests)
# ============================================================================

class TestFeatureIdPattern:
    """Test the FEATURE_ID_PATTERN regex."""

    def test_feature_id_pattern_exists(self, feature_detector):
        """Test that FEATURE_ID_PATTERN class attribute exists."""
        assert hasattr(FeatureDetector, 'FEATURE_ID_PATTERN')

    def test_feature_id_pattern_matches_valid_formats(self, feature_detector):
        """Test that pattern matches all valid feature ID formats."""
        valid_ids = [
            "FEAT-GR-003",
            "FEAT-SKEL-001",
            "FEAT-AUTH-123",
            "FEAT-A1B2-999",
            "FEAT-X-1"
        ]

        for feature_id in valid_ids:
            description = f"Test with {feature_id} in it"
            result = feature_detector.detect_feature_id(description)
            assert result == feature_id, f"Failed to match {feature_id}"
