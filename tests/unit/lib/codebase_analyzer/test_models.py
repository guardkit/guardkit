"""
Unit tests for codebase_analyzer models - TASK-FIX-A1B2

Tests for TechnologyItemInfo, TechnologyInfo field updates, and ConfidenceScore
auto-correction validation.

Target: 80%+ line coverage, 75%+ branch coverage
"""

import pytest
import sys
from pathlib import Path

# Add lib path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "installer" / "core" / "lib"))

from codebase_analyzer.models import (
    TechnologyItemInfo,
    TechnologyInfo,
    FrameworkInfo,
    ConfidenceScore,
    ConfidenceLevel,
)


# =============================================================================
# TechnologyItemInfo Tests
# =============================================================================

class TestTechnologyItemInfo:
    """Test TechnologyItemInfo model for rich technology metadata."""

    def test_basic_creation_with_name_only(self):
        """Test TechnologyItemInfo with only required name field."""
        item = TechnologyItemInfo(name="pytest")
        assert item.name == "pytest"
        assert item.type is None
        assert item.purpose is None
        assert item.provider is None
        assert item.language is None
        assert item.confidence is None

    def test_with_full_metadata(self):
        """Test TechnologyItemInfo with all optional fields."""
        item = TechnologyItemInfo(
            name="DeepEval",
            type="LLM testing framework",
            purpose="LLM-based testing",
            provider="DeepEval.ai",
            language="Python",
            confidence=0.9
        )
        assert item.name == "DeepEval"
        assert item.type == "LLM testing framework"
        assert item.purpose == "LLM-based testing"
        assert item.provider == "DeepEval.ai"
        assert item.language == "Python"
        assert item.confidence == 0.9

    def test_database_metadata(self):
        """Test TechnologyItemInfo for database with provider info."""
        item = TechnologyItemInfo(
            name="Cloud Firestore",
            type="NoSQL document database",
            provider="Firebase/Google Cloud"
        )
        assert item.name == "Cloud Firestore"
        assert item.type == "NoSQL document database"
        assert item.provider == "Firebase/Google Cloud"

    def test_infrastructure_metadata(self):
        """Test TechnologyItemInfo for infrastructure tool."""
        item = TechnologyItemInfo(
            name="Firebase Hosting",
            purpose="Static site hosting",
            confidence=0.95
        )
        assert item.name == "Firebase Hosting"
        assert item.purpose == "Static site hosting"
        assert item.confidence == 0.95

    def test_confidence_validation_bounds(self):
        """Test confidence field validates between 0 and 1."""
        # Valid bounds
        item_low = TechnologyItemInfo(name="test", confidence=0.0)
        assert item_low.confidence == 0.0

        item_high = TechnologyItemInfo(name="test", confidence=1.0)
        assert item_high.confidence == 1.0

        # Invalid bounds
        with pytest.raises(ValueError):
            TechnologyItemInfo(name="test", confidence=-0.1)

        with pytest.raises(ValueError):
            TechnologyItemInfo(name="test", confidence=1.1)

    def test_json_deserialization(self):
        """Test TechnologyItemInfo from JSON dict (simulates AI response)."""
        json_data = {
            "name": "DeepEval",
            "language": "Python",
            "purpose": "LLM-based testing",
            "confidence": 0.9
        }
        item = TechnologyItemInfo(**json_data)
        assert item.name == "DeepEval"
        assert item.language == "Python"


# =============================================================================
# TechnologyInfo Field Tests
# =============================================================================

class TestTechnologyInfoFields:
    """Test TechnologyInfo with Union[str, TechnologyItemInfo] fields."""

    def test_testing_frameworks_with_strings(self):
        """Test testing_frameworks with simple string list (backward compatible)."""
        tech = TechnologyInfo(
            primary_language="Python",
            testing_frameworks=["pytest", "unittest"],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert tech.testing_frameworks == ["pytest", "unittest"]
        assert tech.testing_framework_list == ["pytest", "unittest"]

    def test_testing_frameworks_with_objects(self):
        """Test testing_frameworks with TechnologyItemInfo objects."""
        tech = TechnologyInfo(
            primary_language="Python",
            testing_frameworks=[
                TechnologyItemInfo(name="pytest", language="Python"),
                TechnologyItemInfo(name="DeepEval", purpose="LLM testing")
            ],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert len(tech.testing_frameworks) == 2
        assert isinstance(tech.testing_frameworks[0], TechnologyItemInfo)
        assert tech.testing_framework_list == ["pytest", "DeepEval"]

    def test_testing_frameworks_mixed(self):
        """Test testing_frameworks with mixed strings and objects."""
        tech = TechnologyInfo(
            primary_language="Python",
            testing_frameworks=[
                TechnologyItemInfo(name="pytest"),
                "unittest",
                TechnologyItemInfo(name="DeepEval", confidence=0.9)
            ],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert len(tech.testing_frameworks) == 3
        assert tech.testing_framework_list == ["pytest", "unittest", "DeepEval"]

    def test_databases_with_strings(self):
        """Test databases with simple string list."""
        tech = TechnologyInfo(
            primary_language="Python",
            databases=["PostgreSQL", "Redis"],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert tech.database_list == ["PostgreSQL", "Redis"]

    def test_databases_with_objects(self):
        """Test databases with TechnologyItemInfo objects."""
        tech = TechnologyInfo(
            primary_language="JavaScript",
            databases=[
                TechnologyItemInfo(
                    name="Cloud Firestore",
                    type="NoSQL document database",
                    provider="Firebase/Google Cloud"
                )
            ],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert len(tech.databases) == 1
        assert tech.database_list == ["Cloud Firestore"]

    def test_infrastructure_with_strings(self):
        """Test infrastructure with simple string list."""
        tech = TechnologyInfo(
            primary_language="Python",
            infrastructure=["Docker", "Kubernetes"],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert tech.infrastructure_list == ["Docker", "Kubernetes"]

    def test_infrastructure_with_objects(self):
        """Test infrastructure with TechnologyItemInfo objects."""
        tech = TechnologyInfo(
            primary_language="JavaScript",
            infrastructure=[
                TechnologyItemInfo(
                    name="Firebase Hosting",
                    purpose="Static site hosting",
                    confidence=0.95
                )
            ],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert len(tech.infrastructure) == 1
        assert tech.infrastructure_list == ["Firebase Hosting"]

    def test_empty_lists(self):
        """Test that empty lists work for all fields."""
        tech = TechnologyInfo(
            primary_language="Go",
            testing_frameworks=[],
            databases=[],
            infrastructure=[],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert tech.testing_framework_list == []
        assert tech.database_list == []
        assert tech.infrastructure_list == []

    def test_json_deserialization_from_ai_response(self):
        """Test complete TechnologyInfo from AI JSON response."""
        ai_json = {
            "primary_language": "Python",
            "testing_frameworks": [
                {"name": "DeepEval", "language": "Python", "purpose": "LLM-based testing", "confidence": 0.9},
                "pytest"
            ],
            "databases": [
                {"name": "Cloud Firestore", "type": "NoSQL document database", "provider": "Firebase/Google Cloud"}
            ],
            "infrastructure": [
                {"name": "Firebase Hosting", "purpose": "Static site hosting", "confidence": 0.95}
            ],
            "confidence": {"level": "high", "percentage": 95.0}
        }
        tech = TechnologyInfo(**ai_json)

        assert tech.primary_language == "Python"
        assert len(tech.testing_frameworks) == 2
        assert tech.testing_framework_list == ["DeepEval", "pytest"]
        assert tech.database_list == ["Cloud Firestore"]
        assert tech.infrastructure_list == ["Firebase Hosting"]


# =============================================================================
# ConfidenceScore Auto-Correction Tests
# =============================================================================

class TestConfidenceScoreAutoCorrection:
    """Test ConfidenceScore validator auto-corrects level to match percentage."""

    def test_auto_correct_high_to_medium(self):
        """Test that 'high' level with 85% is auto-corrected to 'medium'."""
        # 85% is in MEDIUM range (70-89)
        score = ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=85.0)
        assert score.level == ConfidenceLevel.MEDIUM
        assert score.percentage == 85.0

    def test_auto_correct_low_to_high(self):
        """Test that 'low' level with 95% is auto-corrected to 'high'."""
        score = ConfidenceScore(level=ConfidenceLevel.LOW, percentage=95.0)
        assert score.level == ConfidenceLevel.HIGH

    def test_auto_correct_medium_to_uncertain(self):
        """Test that 'medium' level with 30% is auto-corrected to 'uncertain'."""
        score = ConfidenceScore(level=ConfidenceLevel.MEDIUM, percentage=30.0)
        assert score.level == ConfidenceLevel.UNCERTAIN

    def test_no_correction_when_matching_high(self):
        """Test no correction when level matches percentage (HIGH)."""
        score = ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        assert score.level == ConfidenceLevel.HIGH

    def test_no_correction_when_matching_medium(self):
        """Test no correction when level matches percentage (MEDIUM)."""
        score = ConfidenceScore(level=ConfidenceLevel.MEDIUM, percentage=80.0)
        assert score.level == ConfidenceLevel.MEDIUM

    def test_no_correction_when_matching_low(self):
        """Test no correction when level matches percentage (LOW)."""
        score = ConfidenceScore(level=ConfidenceLevel.LOW, percentage=60.0)
        assert score.level == ConfidenceLevel.LOW

    def test_no_correction_when_matching_uncertain(self):
        """Test no correction when level matches percentage (UNCERTAIN)."""
        score = ConfidenceScore(level=ConfidenceLevel.UNCERTAIN, percentage=40.0)
        assert score.level == ConfidenceLevel.UNCERTAIN

    def test_boundary_90_is_high(self):
        """Test that exactly 90% is HIGH."""
        score = ConfidenceScore(level=ConfidenceLevel.LOW, percentage=90.0)
        assert score.level == ConfidenceLevel.HIGH

    def test_boundary_70_is_medium(self):
        """Test that exactly 70% is MEDIUM."""
        score = ConfidenceScore(level=ConfidenceLevel.LOW, percentage=70.0)
        assert score.level == ConfidenceLevel.MEDIUM

    def test_boundary_50_is_low(self):
        """Test that exactly 50% is LOW."""
        score = ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=50.0)
        assert score.level == ConfidenceLevel.LOW

    def test_boundary_49_is_uncertain(self):
        """Test that 49% is UNCERTAIN."""
        score = ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=49.0)
        assert score.level == ConfidenceLevel.UNCERTAIN

    def test_json_deserialization_with_mismatch(self):
        """Test JSON with level/percentage mismatch is auto-corrected."""
        json_data = {"level": "high", "percentage": 85.0}
        score = ConfidenceScore(**json_data)
        assert score.level == ConfidenceLevel.MEDIUM  # Auto-corrected


# =============================================================================
# Backward Compatibility Tests
# =============================================================================

class TestBackwardCompatibility:
    """Test that existing code patterns continue to work."""

    def test_framework_list_still_works(self):
        """Test existing framework_list property still works."""
        tech = TechnologyInfo(
            primary_language="Python",
            frameworks=[
                FrameworkInfo(name="FastAPI", purpose="Web API"),
                "React"
            ],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )
        assert tech.framework_list == ["FastAPI", "React"]

    def test_string_only_lists_still_work(self):
        """Test that pure string lists still work for all fields."""
        tech = TechnologyInfo(
            primary_language="Python",
            frameworks=["Django", "FastAPI"],
            testing_frameworks=["pytest", "unittest"],
            databases=["PostgreSQL"],
            infrastructure=["Docker"],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )

        assert tech.framework_list == ["Django", "FastAPI"]
        assert tech.testing_framework_list == ["pytest", "unittest"]
        assert tech.database_list == ["PostgreSQL"]
        assert tech.infrastructure_list == ["Docker"]

    def test_iteration_over_lists(self):
        """Test that list properties support iteration."""
        tech = TechnologyInfo(
            primary_language="Python",
            testing_frameworks=[
                TechnologyItemInfo(name="pytest"),
                "unittest"
            ],
            confidence=ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)
        )

        # Iterate over testing_framework_list
        names = []
        for name in tech.testing_framework_list:
            names.append(name)

        assert names == ["pytest", "unittest"]


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests with realistic AI response data."""

    def test_kartlog_ai_response_pattern(self):
        """Test with kartlog-style AI response that was failing before fix."""
        ai_response = {
            "primary_language": "JavaScript",
            "frameworks": [
                {"name": "SvelteKit", "purpose": "Full-stack framework", "version": "2.0"}
            ],
            "testing_frameworks": [
                {"name": "DeepEval", "language": "Python", "purpose": "LLM-based testing", "confidence": 0.9}
            ],
            "databases": [
                {"name": "Cloud Firestore", "type": "NoSQL document database", "provider": "Firebase/Google Cloud"}
            ],
            "infrastructure": [
                {"name": "Firebase Hosting", "purpose": "Static site hosting", "confidence": 0.95}
            ],
            "confidence": {"level": "high", "percentage": 85.0}
        }

        # This should NOT raise validation errors anymore
        tech = TechnologyInfo(**ai_response)

        assert tech.primary_language == "JavaScript"
        assert tech.testing_framework_list == ["DeepEval"]
        assert tech.database_list == ["Cloud Firestore"]
        assert tech.infrastructure_list == ["Firebase Hosting"]
        # Confidence level should be auto-corrected
        assert tech.confidence.level == ConfidenceLevel.MEDIUM


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
