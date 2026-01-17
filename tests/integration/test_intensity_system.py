"""
Integration tests for intensity system.

Tests the complete intensity auto-detection system including:
- Provenance-based detection (parent_review, feature_id)
- Complexity-based fallback for fresh tasks
- --intensity flag override behavior
- High-risk keyword detection
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

# Import intensity detector module using importlib
# Path: .../guardkit/.conductor/columbus-v1/tests/integration/test_intensity_system.py
# Need to go up 5 levels to get to guardkit repo root
main_repo = Path(__file__).parent.parent.parent.parent.parent
intensity_detector_path = (
    main_repo / "guardkit" / "orchestrator" / "intensity_detector.py"
)
spec = importlib.util.spec_from_file_location(
    "intensity_detector", str(intensity_detector_path)
)
intensity_detector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(intensity_detector)

# Import functions and classes
IntensityLevel = intensity_detector.IntensityLevel
determine_intensity = intensity_detector.determine_intensity
HIGH_RISK_KEYWORDS = intensity_detector.HIGH_RISK_KEYWORDS

# Import frontmatter parser using importlib
parser_path = main_repo / "installer" / "core" / "lib" / "agent_formatting" / "parser.py"
spec = importlib.util.spec_from_file_location("parser", str(parser_path))
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)

extract_frontmatter = parser.extract_frontmatter


def load_task_fixture(fixture_name: str) -> dict:
    """
    Load task fixture file and parse frontmatter.

    Args:
        fixture_name: Name of fixture file (e.g., "task-from-review.md")

    Returns:
        Dictionary with task data from frontmatter plus description
    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / "intensity" / fixture_name
    content = fixture_path.read_text()

    # Extract frontmatter
    frontmatter, _ = extract_frontmatter(content)

    # Extract description from markdown body
    lines = content.split("\n")
    description_lines = []
    in_description = False

    for line in lines:
        if line.strip() == "## Description":
            in_description = True
            continue
        if in_description:
            if line.startswith("## "):  # Next section
                break
            description_lines.append(line)

    description = "\n".join(description_lines).strip()

    # Build task data dict
    task_data = {
        "task_id": frontmatter.get("id"),
        "description": description or frontmatter.get("title", ""),
        "complexity": frontmatter.get("complexity", 5),
        "parent_review": frontmatter.get("parent_review"),
        "feature_id": frontmatter.get("feature_id"),
    }

    return task_data


class TestProvenanceDetection:
    """Test provenance-based intensity detection."""

    def test_task_from_review_low_complexity_gets_minimal(self):
        """Task with parent_review and complexity ≤4 should get MINIMAL intensity."""
        task = load_task_fixture("task-from-review.md")
        assert task["complexity"] == 3
        assert task["parent_review"] == "TASK-REV-TEST"

        intensity = determine_intensity(task)
        assert intensity == IntensityLevel.MINIMAL

    def test_task_from_review_higher_complexity_gets_light(self):
        """Task with parent_review and complexity >4 should get LIGHT intensity."""
        task = load_task_fixture("task-from-review.md")
        # Modify complexity for this test
        task["complexity"] = 6
        task["parent_review"] = "TASK-REV-TEST"

        intensity = determine_intensity(task)
        assert intensity == IntensityLevel.LIGHT

    def test_task_from_feature_low_complexity_gets_minimal(self):
        """Task with feature_id and complexity ≤3 should get MINIMAL intensity."""
        task = {
            "task_id": "TASK-TEST",
            "description": "Simple feature task",
            "complexity": 3,
            "parent_review": None,
            "feature_id": "FEAT-TEST",
        }

        intensity = determine_intensity(task)
        assert intensity == IntensityLevel.MINIMAL

    def test_task_from_feature_medium_complexity_gets_light(self):
        """Task with feature_id and complexity 4-5 should get LIGHT intensity."""
        task = load_task_fixture("task-from-feature.md")
        assert task["complexity"] == 4
        assert task["feature_id"] == "FEAT-TEST"

        intensity = determine_intensity(task)
        assert intensity == IntensityLevel.LIGHT

    def test_task_from_feature_high_complexity_gets_standard(self):
        """Task with feature_id and complexity >5 should get STANDARD intensity."""
        task = load_task_fixture("task-from-feature.md")
        task["complexity"] = 7

        intensity = determine_intensity(task)
        assert intensity == IntensityLevel.STANDARD


class TestComplexityFallback:
    """Test complexity-based detection for fresh tasks."""

    def test_fresh_simple_task_gets_minimal(self):
        """Fresh task with complexity ≤3 should get MINIMAL intensity."""
        task = load_task_fixture("task-fresh-simple.md")
        assert task["complexity"] == 2
        assert task["parent_review"] is None
        assert task["feature_id"] is None

        intensity = determine_intensity(task)
        assert intensity == IntensityLevel.MINIMAL

    def test_fresh_medium_task_gets_light(self):
        """Fresh task with complexity 4-5 should get LIGHT intensity."""
        task = {
            "task_id": "TASK-TEST",
            "description": "Medium complexity task",
            "complexity": 5,
            "parent_review": None,
            "feature_id": None,
        }

        intensity = determine_intensity(task)
        assert intensity == IntensityLevel.LIGHT

    def test_fresh_standard_task_gets_standard(self):
        """Fresh task with complexity 6 should get STANDARD intensity."""
        task = {
            "task_id": "TASK-TEST",
            "description": "Standard complexity task",
            "complexity": 6,
            "parent_review": None,
            "feature_id": None,
        }

        intensity = determine_intensity(task)
        assert intensity == IntensityLevel.STANDARD

    def test_fresh_complex_task_gets_strict(self):
        """Fresh task with complexity >6 should get STRICT intensity."""
        task = load_task_fixture("task-fresh-complex.md")
        assert task["complexity"] == 8
        assert task["parent_review"] is None
        assert task["feature_id"] is None

        intensity = determine_intensity(task)
        assert intensity == IntensityLevel.STRICT

    @pytest.mark.parametrize(
        "complexity,expected",
        [
            (1, IntensityLevel.MINIMAL),
            (2, IntensityLevel.MINIMAL),
            (3, IntensityLevel.MINIMAL),
            (4, IntensityLevel.LIGHT),
            (5, IntensityLevel.LIGHT),
            (6, IntensityLevel.STANDARD),
            (7, IntensityLevel.STRICT),
            (8, IntensityLevel.STRICT),
            (9, IntensityLevel.STRICT),
            (10, IntensityLevel.STRICT),
        ],
    )
    def test_complexity_thresholds(self, complexity: int, expected: IntensityLevel):
        """Test all complexity threshold boundaries for fresh tasks."""
        task = {
            "task_id": "TASK-TEST",
            "description": "Test task",
            "complexity": complexity,
            "parent_review": None,
            "feature_id": None,
        }

        intensity = determine_intensity(task)
        assert (
            intensity == expected
        ), f"Complexity {complexity} should give {expected.value}, got {intensity.value}"


class TestOverrideBehavior:
    """Test --intensity flag override behavior."""

    def test_override_minimal_to_strict(self):
        """Explicit --intensity=strict should override auto-detected MINIMAL."""
        task = load_task_fixture("task-fresh-simple.md")
        # Would normally be MINIMAL (complexity=2)
        auto_intensity = determine_intensity(task)
        assert auto_intensity == IntensityLevel.MINIMAL

        # But override forces STRICT
        intensity = determine_intensity(task, override="strict")
        assert intensity == IntensityLevel.STRICT

    def test_override_strict_to_minimal(self):
        """Explicit --intensity=minimal should override auto-detected STRICT."""
        task = load_task_fixture("task-fresh-complex.md")
        # Would normally be STRICT (complexity=8)
        auto_intensity = determine_intensity(task)
        assert auto_intensity == IntensityLevel.STRICT

        # But override forces MINIMAL
        intensity = determine_intensity(task, override="minimal")
        assert intensity == IntensityLevel.MINIMAL

    def test_override_case_insensitive(self):
        """Override should be case-insensitive."""
        task = load_task_fixture("task-fresh-simple.md")

        for override_value in ["STRICT", "Strict", "strict", "sTrIcT"]:
            intensity = determine_intensity(task, override=override_value)
            assert intensity == IntensityLevel.STRICT

    def test_invalid_override_falls_back_to_auto_detection(self):
        """Invalid override value should fall back to auto-detection."""
        task = load_task_fixture("task-fresh-simple.md")

        # Invalid override should be ignored
        intensity = determine_intensity(task, override="invalid-value")
        # Should fall back to auto-detection (MINIMAL for complexity=2)
        assert intensity == IntensityLevel.MINIMAL

    @pytest.mark.parametrize(
        "override_value,expected",
        [
            ("minimal", IntensityLevel.MINIMAL),
            ("light", IntensityLevel.LIGHT),
            ("standard", IntensityLevel.STANDARD),
            ("strict", IntensityLevel.STRICT),
        ],
    )
    def test_all_override_values(
        self, override_value: str, expected: IntensityLevel
    ):
        """Test all valid override values work correctly."""
        task = {
            "task_id": "TASK-TEST",
            "description": "Test task",
            "complexity": 5,
            "parent_review": None,
            "feature_id": None,
        }

        intensity = determine_intensity(task, override=override_value)
        assert intensity == expected


class TestHighRiskKeywords:
    """Test high-risk keyword detection forcing STRICT intensity."""

    @pytest.mark.parametrize(
        "keyword",
        [
            "security",
            "authentication",
            "authorization",
            "OAuth",
            "JWT",
            "breaking change",
            "migration",
            "encryption",
        ],
    )
    def test_high_risk_keywords_force_strict(self, keyword: str):
        """High-risk keywords should force STRICT intensity regardless of complexity."""
        task = {
            "task_id": "TASK-TEST",
            "description": f"Add {keyword} to the system",
            "complexity": 2,  # Would normally be MINIMAL
            "parent_review": None,
            "feature_id": None,
        }

        intensity = determine_intensity(task)
        assert (
            intensity == IntensityLevel.STRICT
        ), f"Keyword '{keyword}' should force STRICT"

    def test_high_risk_keywords_case_insensitive(self):
        """High-risk keyword detection should be case-insensitive."""
        for description in [
            "Add SECURITY measures",
            "Implement Authentication",
            "Update oauth flow",
            "Fix JWT validation",
        ]:
            task = {
                "task_id": "TASK-TEST",
                "description": description,
                "complexity": 3,
                "parent_review": None,
                "feature_id": None,
            }

            intensity = determine_intensity(task)
            assert (
                intensity == IntensityLevel.STRICT
            ), f"Description '{description}' should force STRICT"

    def test_high_risk_overrides_provenance(self):
        """High-risk keywords should override provenance-based detection."""
        task = {
            "task_id": "TASK-TEST",
            "description": "Add authentication to API",  # High-risk keyword
            "complexity": 3,
            "parent_review": "TASK-REV-TEST",  # Would normally give MINIMAL
            "feature_id": None,
        }

        intensity = determine_intensity(task)
        assert intensity == IntensityLevel.STRICT

    def test_high_risk_keywords_list_accessible(self):
        """HIGH_RISK_KEYWORDS should be accessible for reference."""
        assert isinstance(HIGH_RISK_KEYWORDS, list)
        assert len(HIGH_RISK_KEYWORDS) > 0
        assert "security" in HIGH_RISK_KEYWORDS
        assert "authentication" in HIGH_RISK_KEYWORDS


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_description_field(self):
        """Task without description should not crash."""
        task = {
            "task_id": "TASK-TEST",
            "complexity": 5,
            "parent_review": None,
            "feature_id": None,
            # No description field
        }

        # Should not raise exception
        intensity = determine_intensity(task)
        # Should fall back to complexity-based (5 = LIGHT)
        assert intensity == IntensityLevel.LIGHT

    def test_missing_complexity_field(self):
        """Task without complexity should default to medium (5)."""
        task = {
            "task_id": "TASK-TEST",
            "description": "Test task",
            "parent_review": None,
            "feature_id": None,
            # No complexity field
        }

        intensity = determine_intensity(task)
        # Should default to complexity=5 (LIGHT)
        assert intensity == IntensityLevel.LIGHT

    def test_empty_description(self):
        """Empty description should not trigger keyword detection."""
        task = {
            "task_id": "TASK-TEST",
            "description": "",
            "complexity": 3,
            "parent_review": None,
            "feature_id": None,
        }

        intensity = determine_intensity(task)
        # Should be MINIMAL (complexity=3, no high-risk keywords)
        assert intensity == IntensityLevel.MINIMAL

    def test_none_values_handled_gracefully(self):
        """None values in provenance fields should be handled."""
        task = {
            "task_id": "TASK-TEST",
            "description": "Test task",
            "complexity": 5,
            "parent_review": None,
            "feature_id": None,
        }

        # Should not raise exception
        intensity = determine_intensity(task)
        assert intensity == IntensityLevel.LIGHT
