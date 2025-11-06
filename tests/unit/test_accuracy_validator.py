"""
Unit Tests for AccuracyValidator

Tests the accuracy validation logic for template creation.
"""

import pytest
from tests.lib.template_testing.accuracy_validator import (
    AccuracyValidator,
    GroundTruth,
    AccuracyReport
)


class TestAccuracyValidator:
    """Unit tests for AccuracyValidator."""
    
    @pytest.fixture
    def sample_ground_truth(self):
        """Create sample ground truth for testing."""
        return GroundTruth(
            project_name="test_project",
            tech_stack="python",
            patterns=["Repository", "Dependency Injection"],
            key_files=["main.py", "repository.py"],
            dependencies=["fastapi", "pytest"],
            architecture_style="Clean Architecture",
            testing_framework="pytest"
        )
    
    def test_validate_tech_stack_match(self, sample_ground_truth):
        """Test tech stack validation with exact match."""
        validator = AccuracyValidator(sample_ground_truth)
        
        report = validator.validate_tech_stack("python")
        
        assert report.accuracy_percentage == 100.0
        assert len(report.matches) == 1
        assert len(report.missing) == 0
        assert len(report.extra) == 0
    
    def test_validate_tech_stack_mismatch(self, sample_ground_truth):
        """Test tech stack validation with mismatch."""
        validator = AccuracyValidator(sample_ground_truth)
        
        report = validator.validate_tech_stack("react")
        
        assert report.accuracy_percentage == 0.0
        assert len(report.matches) == 0
        assert len(report.missing) == 1
        assert len(report.extra) == 1
    
    def test_validate_patterns_all_match(self, sample_ground_truth):
        """Test pattern validation with all matches."""
        validator = AccuracyValidator(sample_ground_truth)
        
        report = validator.validate_patterns(["Repository", "Dependency Injection"])
        
        assert report.accuracy_percentage == 100.0
        assert set(report.matches) == {"Repository", "Dependency Injection"}
        assert len(report.missing) == 0
    
    def test_validate_patterns_partial_match(self, sample_ground_truth):
        """Test pattern validation with partial matches."""
        validator = AccuracyValidator(sample_ground_truth)
        
        report = validator.validate_patterns(["Repository", "Factory"])
        
        assert report.accuracy_percentage == 50.0
        assert "Repository" in report.matches
        assert "Dependency Injection" in report.missing
        assert "Factory" in report.extra
    
    def test_validate_patterns_empty_expected(self):
        """Test pattern validation with empty expected list."""
        ground_truth = GroundTruth(
            project_name="test",
            tech_stack="python",
            patterns=[],
            key_files=[],
            dependencies=[],
            architecture_style="Layered"
        )
        validator = AccuracyValidator(ground_truth)
        
        report = validator.validate_patterns(["Repository"])
        
        assert report.accuracy_percentage == 100.0
    
    def test_validate_key_files_all_match(self, sample_ground_truth):
        """Test key files validation with all matches."""
        validator = AccuracyValidator(sample_ground_truth)
        
        report = validator.validate_key_files(["main.py", "repository.py"])
        
        assert report.accuracy_percentage == 100.0
        assert set(report.matches) == {"main.py", "repository.py"}
    
    def test_validate_dependencies_all_match(self, sample_ground_truth):
        """Test dependencies validation with all matches."""
        validator = AccuracyValidator(sample_ground_truth)
        
        report = validator.validate_dependencies(["fastapi", "pytest"])
        
        assert report.accuracy_percentage == 100.0
        assert set(report.matches) == {"fastapi", "pytest"}
    
    def test_validate_architecture_match(self, sample_ground_truth):
        """Test architecture validation with match."""
        validator = AccuracyValidator(sample_ground_truth)
        
        report = validator.validate_architecture("Clean Architecture")
        
        assert report.accuracy_percentage == 100.0
        assert len(report.matches) == 1
    
    def test_get_overall_accuracy(self, sample_ground_truth):
        """Test overall accuracy calculation."""
        validator = AccuracyValidator(sample_ground_truth)
        
        validator.validate_tech_stack("python")  # 100%
        validator.validate_patterns(["Repository"])  # 50%
        validator.validate_architecture("Clean Architecture")  # 100%
        
        overall = validator.get_overall_accuracy()
        
        assert overall == pytest.approx(83.33, abs=0.1)
    
    def test_get_summary(self, sample_ground_truth):
        """Test summary generation."""
        validator = AccuracyValidator(sample_ground_truth)
        
        validator.validate_tech_stack("python")
        validator.validate_patterns(["Repository", "Dependency Injection"])
        
        summary = validator.get_summary()
        
        assert "overall_accuracy" in summary
        assert summary["overall_accuracy"] == 100.0
        assert summary["total_validations"] == 2
        assert len(summary["reports"]) == 2
    
    def test_assert_accuracy_threshold_pass(self, sample_ground_truth):
        """Test accuracy threshold assertion when passing."""
        validator = AccuracyValidator(sample_ground_truth)
        
        validator.validate_tech_stack("python")
        validator.validate_patterns(["Repository", "Dependency Injection"])
        
        # Should not raise
        validator.assert_accuracy_threshold(90.0)
    
    def test_assert_accuracy_threshold_fail(self, sample_ground_truth):
        """Test accuracy threshold assertion when failing."""
        validator = AccuracyValidator(sample_ground_truth)
        
        validator.validate_tech_stack("react")  # 0%
        validator.validate_patterns([])  # 0%
        
        with pytest.raises(AssertionError, match="below threshold"):
            validator.assert_accuracy_threshold(90.0)
