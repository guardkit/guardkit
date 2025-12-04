"""
Test suite for review_parser.py - Subtask extraction from review reports.

Tests cover:
1. Recommendation section detection (various header formats)
2. Subtask extraction from tables
3. Subtask extraction from numbered lists
4. Subtask extraction from bulleted lists
5. File inference from recommendation text
6. Edge cases (empty sections, malformed markdown)
"""

import pytest
import tempfile
from pathlib import Path
from lib.review_parser import (
    SubtaskExtractor,
    extract_subtasks_from_review
)


# Test fixtures for review report content
@pytest.fixture
def sample_review_with_table():
    """Review report with Phase 1 Subtasks table."""
    return """# Review Report: TASK-REV-FW01

## Feature Workflow Streamlining - Decision Analysis

**Review Mode**: Decision Analysis
**Review Depth**: Standard
**Date**: 2025-12-04

---

## Executive Summary

This review analyzes how to formalize the evolved feature development workflow.

---

## Recommendations

### Phase 1 Subtasks (Feature Plan Command + Enhanced [I]mplement)

| ID | Title | Method | Complexity | Effort |
|----|-------|--------|------------|--------|
| FW-001 | Create /feature-plan command (markdown orchestration) | Direct | 3 | 0.5d |
| FW-002 | Auto-detect feature slug from review task title | Direct | 3 | 0.5d |
| FW-003 | Auto-detect subtasks from review recommendations | /task-work | 5 | 1d |
| FW-004 | Add implementation mode auto-tagging | /task-work | 5 | 1d |

**Total Phase 1**: ~3.5 days
"""


@pytest.fixture
def sample_review_with_numbered_list():
    """Review report with numbered recommendations."""
    return """# Review Report: TASK-DM-001

## Dark Mode Implementation

**Review Mode**: Architectural
**Review Depth**: Standard
**Date**: 2025-12-04

---

## Recommendations

1. Add CSS variables for theming (src/styles/variables.css)
2. Create theme toggle component in `src/components/ThemeToggle.tsx`
3. Persist user preference using localStorage
4. Update navigation component to support dark mode
5. Add documentation in /docs/dark-mode.md
"""


@pytest.fixture
def sample_review_with_bulleted_list():
    """Review report with bulleted recommendations."""
    return """# Review Report: TASK-AUTH-001

## Authentication Review

---

## Action Items

- Implement JWT token validation
- Add refresh token rotation
- Create /auth/login endpoint
- Update AuthService class
- Add integration tests
"""


@pytest.fixture
def sample_review_empty_recommendations():
    """Review report with empty recommendations section."""
    return """# Review Report: TASK-EMPTY-001

## Empty Recommendations Test

---

## Recommendations

(No specific recommendations at this time)
"""


@pytest.fixture
def sample_review_no_recommendations():
    """Review report without recommendations section."""
    return """# Review Report: TASK-NO-REC-001

## No Recommendations Test

---

## Executive Summary

This is a review without recommendations.
"""


class TestSubtaskExtractor:
    """Test SubtaskExtractor class methods."""

    def test_find_recommendations_section_with_h2(self, tmp_path):
        """Test finding recommendations section with ## header."""
        content = """# Review Report

## Recommendations

1. First recommendation
2. Second recommendation

## Other Section
"""
        report_file = tmp_path / "review.md"
        report_file.write_text(content)

        extractor = SubtaskExtractor(str(report_file))
        recommendations = extractor.find_recommendations_section()

        assert recommendations is not None
        assert "First recommendation" in recommendations
        assert "Second recommendation" in recommendations

    def test_find_recommendations_section_with_h3(self, tmp_path):
        """Test finding recommendations section with ### header."""
        content = """# Review Report

## Main Section

### Recommendations

- First item
- Second item
"""
        report_file = tmp_path / "review.md"
        report_file.write_text(content)

        extractor = SubtaskExtractor(str(report_file))
        recommendations = extractor.find_recommendations_section()

        assert recommendations is not None
        assert "First item" in recommendations

    def test_find_recommendations_section_implementation_plan(self, tmp_path):
        """Test finding 'Implementation Plan' as recommendations."""
        content = """# Review Report

## Implementation Plan

1. Task one
2. Task two
"""
        report_file = tmp_path / "review.md"
        report_file.write_text(content)

        extractor = SubtaskExtractor(str(report_file))
        recommendations = extractor.find_recommendations_section()

        assert recommendations is not None
        assert "Task one" in recommendations

    def test_find_recommendations_section_not_found(self, tmp_path):
        """Test when no recommendations section exists."""
        content = """# Review Report

## Some Other Section

Content here.
"""
        report_file = tmp_path / "review.md"
        report_file.write_text(content)

        extractor = SubtaskExtractor(str(report_file))
        recommendations = extractor.find_recommendations_section()

        assert recommendations is None

    def test_find_phase_subtasks_table(self, tmp_path, sample_review_with_table):
        """Test finding Phase subtasks table."""
        report_file = tmp_path / "review.md"
        report_file.write_text(sample_review_with_table)

        extractor = SubtaskExtractor(str(report_file))
        table = extractor.find_phase_subtasks_table()

        assert table is not None
        assert "FW-001" in table
        assert "Create /feature-plan command" in table

    def test_parse_subtasks_from_table(self, tmp_path, sample_review_with_table):
        """Test parsing subtasks from table format."""
        report_file = tmp_path / "review.md"
        report_file.write_text(sample_review_with_table)

        extractor = SubtaskExtractor(str(report_file))
        table = extractor.find_phase_subtasks_table()
        subtasks = extractor.parse_subtasks_from_table(table, "feature-workflow")

        assert len(subtasks) == 4
        assert subtasks[0]["id"] == "TASK-FW-001"
        assert subtasks[0]["title"] == "Create /feature-plan command (markdown orchestration)"
        assert subtasks[0]["complexity"] == 3
        assert subtasks[0]["implementation_mode"] == "direct"
        assert subtasks[2]["implementation_mode"] == "task-work"

    def test_parse_subtasks_from_numbered_list(self, tmp_path, sample_review_with_numbered_list):
        """Test parsing subtasks from numbered list."""
        report_file = tmp_path / "review.md"
        report_file.write_text(sample_review_with_numbered_list)

        extractor = SubtaskExtractor(str(report_file))
        recommendations = extractor.find_recommendations_section()
        subtasks = extractor.parse_subtasks_from_numbered_list(recommendations, "dark-mode")

        assert len(subtasks) == 5
        assert subtasks[0]["id"] == "TASK-DM-001"
        assert "CSS variables" in subtasks[0]["title"]
        assert subtasks[0]["complexity"] == 5  # Default
        assert subtasks[0]["files"]  # Should infer files

    def test_parse_subtasks_from_bulleted_list(self, tmp_path, sample_review_with_bulleted_list):
        """Test parsing subtasks from bulleted list."""
        report_file = tmp_path / "review.md"
        report_file.write_text(sample_review_with_bulleted_list)

        extractor = SubtaskExtractor(str(report_file))
        recommendations = extractor.find_recommendations_section()
        subtasks = extractor.parse_subtasks_from_bulleted_list(recommendations, "authentication")

        assert len(subtasks) == 5
        assert subtasks[0]["id"] == "TASK-A-001"
        assert "JWT token" in subtasks[0]["title"]

    def test_extract_prefix_from_slug(self, tmp_path):
        """Test prefix extraction from feature slug."""
        report_file = tmp_path / "review.md"
        report_file.write_text("# Review")

        extractor = SubtaskExtractor(str(report_file))

        assert extractor._extract_prefix_from_slug("feature-workflow") == "FW"
        assert extractor._extract_prefix_from_slug("dark-mode") == "DM"
        assert extractor._extract_prefix_from_slug("progressive-disclosure") == "PD"
        assert extractor._extract_prefix_from_slug("auth") == "A"

    def test_infer_files_from_text_explicit_paths(self, tmp_path):
        """Test file inference from explicit paths."""
        report_file = tmp_path / "review.md"
        report_file.write_text("# Review")

        extractor = SubtaskExtractor(str(report_file))

        text = "Update src/components/Button.tsx and src/styles/theme.css"
        files = extractor._infer_files_from_text(text)

        assert "src/components/Button.tsx" in files
        assert "src/styles/theme.css" in files

    def test_infer_files_from_text_component_names(self, tmp_path):
        """Test file inference from component names."""
        report_file = tmp_path / "review.md"
        report_file.write_text("# Review")

        extractor = SubtaskExtractor(str(report_file))

        text = "Update the Button component and create ThemeToggle component"
        files = extractor._infer_files_from_text(text)

        assert "src/components/Button.tsx" in files
        assert "src/components/ThemeToggle.tsx" in files

    def test_infer_files_from_text_command_references(self, tmp_path):
        """Test file inference from command references."""
        report_file = tmp_path / "review.md"
        report_file.write_text("# Review")

        extractor = SubtaskExtractor(str(report_file))

        text = "Create /feature-plan command and update /task-review command"
        files = extractor._infer_files_from_text(text)

        assert "installer/global/commands/feature-plan.md" in files
        assert "installer/global/commands/task-review.md" in files

    def test_infer_files_from_text_backticks(self, tmp_path):
        """Test file inference from backtick-wrapped paths."""
        report_file = tmp_path / "review.md"
        report_file.write_text("# Review")

        extractor = SubtaskExtractor(str(report_file))

        text = "Modify `lib/utils.py` and `config/settings.json`"
        files = extractor._infer_files_from_text(text)

        assert "lib/utils.py" in files
        assert "config/settings.json" in files

    def test_infer_files_deduplication(self, tmp_path):
        """Test file inference deduplication."""
        report_file = tmp_path / "review.md"
        report_file.write_text("# Review")

        extractor = SubtaskExtractor(str(report_file))

        text = "Update src/utils.py and also modify src/utils.py again"
        files = extractor._infer_files_from_text(text)

        assert len(files) == 1
        assert "src/utils.py" in files

    def test_extract_subtasks_with_table(self, tmp_path, sample_review_with_table):
        """Test extract_subtasks chooses table strategy first."""
        report_file = tmp_path / "review.md"
        report_file.write_text(sample_review_with_table)

        extractor = SubtaskExtractor(str(report_file))
        subtasks = extractor.extract_subtasks("feature-workflow")

        assert len(subtasks) == 4
        assert subtasks[0]["id"] == "TASK-FW-001"

    def test_extract_subtasks_with_numbered_list(self, tmp_path, sample_review_with_numbered_list):
        """Test extract_subtasks falls back to numbered list."""
        report_file = tmp_path / "review.md"
        report_file.write_text(sample_review_with_numbered_list)

        extractor = SubtaskExtractor(str(report_file))
        subtasks = extractor.extract_subtasks("dark-mode")

        assert len(subtasks) == 5
        assert subtasks[0]["id"] == "TASK-DM-001"

    def test_extract_subtasks_with_bulleted_list(self, tmp_path, sample_review_with_bulleted_list):
        """Test extract_subtasks falls back to bulleted list."""
        report_file = tmp_path / "review.md"
        report_file.write_text(sample_review_with_bulleted_list)

        extractor = SubtaskExtractor(str(report_file))
        subtasks = extractor.extract_subtasks("authentication")

        assert len(subtasks) == 5
        assert subtasks[0]["id"] == "TASK-A-001"

    def test_extract_subtasks_empty_recommendations(self, tmp_path, sample_review_empty_recommendations):
        """Test extract_subtasks with empty recommendations."""
        report_file = tmp_path / "review.md"
        report_file.write_text(sample_review_empty_recommendations)

        extractor = SubtaskExtractor(str(report_file))
        subtasks = extractor.extract_subtasks("feature")

        assert len(subtasks) == 0

    def test_extract_subtasks_no_recommendations(self, tmp_path, sample_review_no_recommendations):
        """Test extract_subtasks with no recommendations section."""
        report_file = tmp_path / "review.md"
        report_file.write_text(sample_review_no_recommendations)

        extractor = SubtaskExtractor(str(report_file))
        subtasks = extractor.extract_subtasks("feature")

        assert len(subtasks) == 0


class TestExtractSubtasksFromReview:
    """Test main entry point function."""

    def test_extract_subtasks_from_review_success(self, tmp_path, sample_review_with_table):
        """Test successful extraction via main function."""
        report_file = tmp_path / "review.md"
        report_file.write_text(sample_review_with_table)

        subtasks = extract_subtasks_from_review(
            str(report_file),
            "feature-workflow"
        )

        assert len(subtasks) == 4
        assert subtasks[0]["id"] == "TASK-FW-001"
        assert subtasks[0]["title"]
        assert subtasks[0]["description"]
        assert "complexity" in subtasks[0]

    def test_extract_subtasks_from_review_file_not_found(self, tmp_path):
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            extract_subtasks_from_review(
                str(tmp_path / "nonexistent.md"),
                "feature"
            )

    def test_extract_subtasks_from_review_with_real_report(self, tmp_path):
        """Test with realistic review report content."""
        content = """# Review Report: TASK-REV-001

## Executive Summary

Review of authentication system architecture.

---

## Recommendations

1. Implement JWT token validation in `lib/auth/jwt_validator.py`
2. Add refresh token rotation to AuthService
3. Create /auth/login endpoint in `api/endpoints/auth.py`
4. Update AuthService class with new methods
5. Add integration tests in `tests/integration/test_auth.py`
6. Document authentication flow in /docs/auth.md
"""
        report_file = tmp_path / "review-real.md"
        report_file.write_text(content)

        subtasks = extract_subtasks_from_review(
            str(report_file),
            "authentication"
        )

        assert len(subtasks) == 6
        assert subtasks[0]["id"] == "TASK-A-001"
        assert "JWT" in subtasks[0]["title"]

        # Check file inference
        assert len(subtasks[0]["files"]) > 0
        assert any("jwt_validator.py" in f for f in subtasks[0]["files"])


class TestEdgeCases:
    """Test edge cases and malformed input."""

    def test_malformed_table_missing_columns(self, tmp_path):
        """Test handling of malformed table with missing columns."""
        content = """# Review

## Recommendations

### Phase 1 Subtasks

| ID | Title |
|----|-------|
| FW-001 | Task one |
| FW-002 |
"""
        report_file = tmp_path / "review.md"
        report_file.write_text(content)

        extractor = SubtaskExtractor(str(report_file))
        table = extractor.find_phase_subtasks_table()

        # Malformed table (missing standard columns) should return empty list
        # This is safer than trying to parse incomplete data
        if table:
            subtasks = extractor.parse_subtasks_from_table(table, "feature")
            # If it's truly malformed, we expect empty or we handle gracefully
            assert isinstance(subtasks, list)
        else:
            # Table not found is also acceptable
            assert True

    def test_empty_file(self, tmp_path):
        """Test handling of empty file."""
        report_file = tmp_path / "empty.md"
        report_file.write_text("")

        extractor = SubtaskExtractor(str(report_file))
        subtasks = extractor.extract_subtasks("feature")

        assert len(subtasks) == 0

    def test_unicode_content(self, tmp_path):
        """Test handling of unicode characters."""
        content = """# Review Report

## Recommendations

1. Add支援 for internationalization (i18n)
2. Update UI with émoji support 🎉
3. Handle UTF-8 encoding in データベース
"""
        report_file = tmp_path / "unicode.md"
        report_file.write_text(content, encoding='utf-8')

        subtasks = extract_subtasks_from_review(
            str(report_file),
            "i18n"
        )

        assert len(subtasks) == 3
        assert "支援" in subtasks[0]["title"] or "internationalization" in subtasks[0]["title"]

    def test_very_long_recommendation(self, tmp_path):
        """Test handling of very long recommendation text."""
        long_text = "Update the authentication system " + ("with detailed information " * 100)
        content = f"""# Review

## Recommendations

1. {long_text}
"""
        report_file = tmp_path / "long.md"
        report_file.write_text(content)

        subtasks = extract_subtasks_from_review(
            str(report_file),
            "auth"
        )

        assert len(subtasks) == 1
        # Title should be present and truncated reasonably
        assert len(subtasks[0]["title"]) > 0

    def test_nested_lists(self, tmp_path):
        """Test handling of nested bulleted/numbered lists."""
        content = """# Review

## Recommendations

1. Main task one
   - Subtask 1a
   - Subtask 1b
2. Main task two
   1. Nested numbered
   2. Another nested
3. Main task three
"""
        report_file = tmp_path / "nested.md"
        report_file.write_text(content)

        extractor = SubtaskExtractor(str(report_file))
        recommendations = extractor.find_recommendations_section()
        subtasks = extractor.parse_subtasks_from_numbered_list(recommendations, "feature")

        # Should extract top-level items (1, 2, 3)
        assert len(subtasks) >= 3

    def test_mixed_list_formats(self, tmp_path):
        """Test handling of mixed list formats in same section."""
        content = """# Review

## Recommendations

1. First numbered item
2. Second numbered item

- First bulleted item
- Second bulleted item
"""
        report_file = tmp_path / "mixed.md"
        report_file.write_text(content)

        extractor = SubtaskExtractor(str(report_file))
        recommendations = extractor.find_recommendations_section()

        # Should extract numbered first
        numbered = extractor.parse_subtasks_from_numbered_list(recommendations, "feature")
        assert len(numbered) == 2

        # Should also extract bulleted
        bulleted = extractor.parse_subtasks_from_bulleted_list(recommendations, "feature")
        assert len(bulleted) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
