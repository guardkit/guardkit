"""
Test Suite for ADR File Generator

Tests the generation of Architecture Decision Record (ADR) markdown files
from Decision Log entries in research templates.

Coverage Target: >=85%
"""

from pathlib import Path
from datetime import date

import pytest

from guardkit.planning.spec_parser import Decision
from guardkit.planning.adr_generator import generate_adrs


# ============================================================================
# 1. Basic Functionality Tests (5 tests)
# ============================================================================

class TestBasicFunctionality:
    """Tests for core ADR generation functionality."""

    def test_returns_list_of_paths(self, tmp_path):
        """Test that generate_adrs returns a list of Path objects."""
        decisions = [
            Decision(
                number="D1",
                title="Use Regex Parser",
                rationale="Simple and maintainable",
                alternatives_rejected="Complex parser library",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)

        assert isinstance(result, list)
        assert all(isinstance(path, Path) for path in result)

    def test_empty_decisions_returns_empty_list(self, tmp_path):
        """Test that empty decisions list returns empty list."""
        result = generate_adrs([], "FEAT-FP-002", output_dir=tmp_path)

        assert result == []

    def test_creates_adr_files(self, tmp_path):
        """Test that ADR files are created in output directory."""
        decisions = [
            Decision(
                number="D1",
                title="Use Regex Parser",
                rationale="Simple and maintainable",
                alternatives_rejected="Complex parser library",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)

        assert len(result) == 1
        assert result[0].exists()

    def test_multiple_decisions_create_multiple_files(self, tmp_path):
        """Test that multiple decisions create multiple ADR files."""
        decisions = [
            Decision(
                number="D1",
                title="Use Regex Parser",
                rationale="Simple",
                alternatives_rejected="Library",
                adr_status="Accepted"
            ),
            Decision(
                number="D2",
                title="Store ADRs in docs/adr",
                rationale="Standard location",
                alternatives_rejected="Root directory",
                adr_status="Accepted"
            ),
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)

        assert len(result) == 2
        assert all(path.exists() for path in result)

    def test_output_directory_created_if_not_exists(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        output_dir = tmp_path / "docs" / "adr"
        assert not output_dir.exists()

        decisions = [
            Decision(
                number="D1",
                title="Test Decision",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=output_dir)

        assert output_dir.exists()
        assert len(result) == 1


# ============================================================================
# 2. File Naming Tests (6 tests)
# ============================================================================

class TestFileNaming:
    """Tests for ADR file naming convention."""

    def test_filename_format(self, tmp_path):
        """Test that filename follows ADR-FP-{number}-{slug}.md format."""
        decisions = [
            Decision(
                number="D1",
                title="Use Regex Parser",
                rationale="Simple",
                alternatives_rejected="Library",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)

        assert result[0].name == "ADR-FP-002-use-regex-parser.md"

    def test_slug_generation_lowercase(self, tmp_path):
        """Test that slug is lowercase."""
        decisions = [
            Decision(
                number="D1",
                title="Use UPPERCASE Title",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)

        assert result[0].name == "ADR-FP-002-use-uppercase-title.md"

    def test_slug_generation_spaces_to_hyphens(self, tmp_path):
        """Test that spaces are replaced with hyphens in slug."""
        decisions = [
            Decision(
                number="D1",
                title="Multiple Word Title Here",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)

        assert result[0].name == "ADR-FP-002-multiple-word-title-here.md"

    def test_slug_generation_removes_special_chars(self, tmp_path):
        """Test that special characters are removed from slug."""
        decisions = [
            Decision(
                number="D1",
                title="Title with @#$% Special! Characters?",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)

        # Should remove special chars but keep alphanumeric and hyphens
        assert result[0].name == "ADR-FP-002-title-with-special-characters.md"

    def test_slug_generation_truncates_to_50_chars(self, tmp_path):
        """Test that slug is truncated to 50 characters."""
        long_title = "This is a very long decision title that should be truncated to fifty characters maximum"
        decisions = [
            Decision(
                number="D1",
                title=long_title,
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)

        # Filename format is ADR-FP-002-{slug}.md
        # Extract slug part (between last dash before .md and .md)
        slug_part = result[0].stem.replace("ADR-FP-002-", "")
        assert len(slug_part) <= 50

    def test_feature_id_extracted_correctly(self, tmp_path):
        """Test that feature number is extracted from various feature ID formats."""
        decisions = [
            Decision(
                number="D1",
                title="Test",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        # Test with different feature ID formats
        result1 = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)
        assert "ADR-FP-002-test.md" in result1[0].name

        # Clean up
        result1[0].unlink()

        result2 = generate_adrs(decisions, "FP-002", output_dir=tmp_path)
        assert "ADR-FP-002-test.md" in result2[0].name


# ============================================================================
# 3. Content Generation Tests (7 tests)
# ============================================================================

class TestContentGeneration:
    """Tests for ADR file content structure."""

    def test_adr_contains_status_section(self, tmp_path):
        """Test that ADR contains Status section."""
        decisions = [
            Decision(
                number="D1",
                title="Test Decision",
                rationale="Test rationale",
                alternatives_rejected="Test alternatives",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)
        content = result[0].read_text()

        assert "## Status" in content
        assert "Accepted" in content

    def test_adr_contains_date_section(self, tmp_path):
        """Test that ADR contains Date section with current date."""
        decisions = [
            Decision(
                number="D1",
                title="Test Decision",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)
        content = result[0].read_text()

        assert "## Date" in content
        # Should contain today's date in ISO format
        today = date.today().isoformat()
        assert today in content

    def test_adr_contains_context_section(self, tmp_path):
        """Test that ADR contains Context section."""
        decisions = [
            Decision(
                number="D1",
                title="Test Decision",
                rationale="Test rationale",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)
        content = result[0].read_text()

        assert "## Context" in content

    def test_adr_contains_decision_section(self, tmp_path):
        """Test that ADR contains Decision section with title."""
        decisions = [
            Decision(
                number="D1",
                title="Use Regex Parser",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)
        content = result[0].read_text()

        assert "## Decision" in content
        assert "Use Regex Parser" in content

    def test_adr_contains_rationale_section(self, tmp_path):
        """Test that ADR contains Rationale section with rationale text."""
        decisions = [
            Decision(
                number="D1",
                title="Test",
                rationale="Simple and maintainable solution",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)
        content = result[0].read_text()

        assert "## Rationale" in content
        assert "Simple and maintainable solution" in content

    def test_adr_contains_alternatives_rejected_section(self, tmp_path):
        """Test that ADR contains Alternatives Rejected section."""
        decisions = [
            Decision(
                number="D1",
                title="Test",
                rationale="Test",
                alternatives_rejected="Complex parser library with high learning curve",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)
        content = result[0].read_text()

        assert "## Alternatives Rejected" in content
        assert "Complex parser library with high learning curve" in content

    def test_adr_contains_consequences_section(self, tmp_path):
        """Test that ADR contains Consequences section."""
        decisions = [
            Decision(
                number="D1",
                title="Test",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)
        content = result[0].read_text()

        assert "## Consequences" in content


# ============================================================================
# 4. Duplicate Detection Tests (5 tests)
# ============================================================================

class TestDuplicateDetection:
    """Tests for duplicate ADR detection."""

    def test_skips_duplicate_when_check_enabled(self, tmp_path):
        """Test that duplicate ADRs are skipped when check_duplicates=True."""
        decisions = [
            Decision(
                number="D1",
                title="Use Regex Parser",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        # Generate first time
        result1 = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path, check_duplicates=True)
        assert len(result1) == 1

        # Generate second time - should skip
        result2 = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path, check_duplicates=True)
        assert len(result2) == 0

    def test_overwrites_duplicate_when_check_disabled(self, tmp_path):
        """Test that duplicate ADRs are overwritten when check_duplicates=False."""
        decisions = [
            Decision(
                number="D1",
                title="Use Regex Parser",
                rationale="Original rationale",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        # Generate first time
        result1 = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path, check_duplicates=False)
        original_content = result1[0].read_text()

        # Modify decision and generate again
        decisions[0].rationale = "Updated rationale"
        result2 = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path, check_duplicates=False)
        updated_content = result2[0].read_text()

        assert len(result2) == 1
        assert "Updated rationale" in updated_content
        assert "Original rationale" not in updated_content

    def test_duplicate_detection_by_title(self, tmp_path):
        """Test that duplicate detection is based on title, not decision number."""
        # Create first ADR
        decisions1 = [
            Decision(
                number="D1",
                title="Use Regex Parser",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]
        generate_adrs(decisions1, "FEAT-FP-002", output_dir=tmp_path)

        # Try to create ADR with same title but different number
        decisions2 = [
            Decision(
                number="D5",  # Different number
                title="Use Regex Parser",  # Same title
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]
        result = generate_adrs(decisions2, "FEAT-FP-002", output_dir=tmp_path, check_duplicates=True)

        assert len(result) == 0  # Should skip duplicate

    def test_different_titles_not_detected_as_duplicate(self, tmp_path):
        """Test that different titles are not detected as duplicates."""
        decisions1 = [
            Decision(
                number="D1",
                title="Use Regex Parser",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]
        generate_adrs(decisions1, "FEAT-FP-002", output_dir=tmp_path)

        decisions2 = [
            Decision(
                number="D2",
                title="Store ADRs in docs/adr",  # Different title
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]
        result = generate_adrs(decisions2, "FEAT-FP-002", output_dir=tmp_path, check_duplicates=True)

        assert len(result) == 1  # Should create new ADR

    def test_check_duplicates_default_is_true(self, tmp_path):
        """Test that check_duplicates defaults to True."""
        decisions = [
            Decision(
                number="D1",
                title="Use Regex Parser",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        # Generate first time without check_duplicates parameter
        result1 = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)
        assert len(result1) == 1

        # Generate second time - should skip by default
        result2 = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)
        assert len(result2) == 0


# ============================================================================
# 5. Edge Cases Tests (6 tests)
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_decision_with_empty_title(self, tmp_path):
        """Test handling of decision with empty title."""
        decisions = [
            Decision(
                number="D1",
                title="",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        # Should either skip or handle gracefully
        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)

        # Implementation choice: could skip empty titles or use fallback
        # Testing that it doesn't crash
        assert isinstance(result, list)

    def test_decision_with_special_chars_in_all_fields(self, tmp_path):
        """Test decision with special characters in all fields."""
        decisions = [
            Decision(
                number="D1",
                title="Use <html> & \"quotes\"",
                rationale="It's the best! 100% certain.",
                alternatives_rejected="Nothing & everything",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)

        assert len(result) == 1
        content = result[0].read_text()
        assert "Use <html>" in content
        assert '"quotes"' in content or '&quot;quotes&quot;' in content

    def test_decision_with_multiline_rationale(self, tmp_path):
        """Test decision with multiline rationale text."""
        decisions = [
            Decision(
                number="D1",
                title="Test Decision",
                rationale="Line 1\nLine 2\nLine 3",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)
        content = result[0].read_text()

        assert "Line 1" in content
        assert "Line 2" in content
        assert "Line 3" in content

    def test_different_adr_statuses(self, tmp_path):
        """Test decisions with different ADR statuses."""
        decisions = [
            Decision(
                number="D1",
                title="Proposed Decision",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Proposed"
            ),
            Decision(
                number="D2",
                title="Superseded Decision",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Superseded"
            ),
        ]

        result = generate_adrs(decisions, "FEAT-FP-002", output_dir=tmp_path)

        assert len(result) == 2
        content1 = result[0].read_text()
        content2 = result[1].read_text()

        assert "Proposed" in content1
        assert "Superseded" in content2

    def test_feature_id_without_prefix(self, tmp_path):
        """Test feature ID that doesn't start with FEAT-."""
        decisions = [
            Decision(
                number="D1",
                title="Test",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        # Should handle feature IDs without FEAT- prefix
        result = generate_adrs(decisions, "ABC-123", output_dir=tmp_path)

        assert len(result) == 1
        # Should still generate valid filename
        assert result[0].name.startswith("ADR-ABC-123-")

    def test_output_dir_default_is_docs_adr(self, tmp_path, monkeypatch):
        """Test that default output directory is docs/adr relative to current directory."""
        # Change to tmp_path as working directory
        monkeypatch.chdir(tmp_path)

        decisions = [
            Decision(
                number="D1",
                title="Test",
                rationale="Test",
                alternatives_rejected="None",
                adr_status="Accepted"
            )
        ]

        # Use default output_dir
        result = generate_adrs(decisions, "FEAT-FP-002")

        # Should create in docs/adr relative to current directory
        expected_dir = tmp_path / "docs" / "adr"
        assert result[0].parent == expected_dir
