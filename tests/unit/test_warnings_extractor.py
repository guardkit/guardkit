"""
Unit tests for warnings_extractor module.

Tests the extraction of warnings/constraints from ParsedSpec into
a standalone markdown file for Graphiti seeding.

Coverage Target: >= 80%
"""

from pathlib import Path

from guardkit.planning.warnings_extractor import extract_warnings


class TestExtractWarnings:
    """Tests for extract_warnings function."""

    def test_extract_warnings_creates_file(self, tmp_path: Path) -> None:
        """Test that extract_warnings creates the markdown file."""
        warnings = [
            "Warning 1: Do not modify existing files",
            "Warning 2: Keep backward compatibility",
        ]
        feature_id = "FEAT-TEST-001"

        result = extract_warnings(warnings, feature_id, tmp_path)

        assert result is not None
        assert result.exists()
        assert result.name == "FEAT-TEST-001-warnings.md"

    def test_extract_warnings_returns_none_for_empty_list(
        self, tmp_path: Path
    ) -> None:
        """Test that extract_warnings returns None for empty warnings list."""
        result = extract_warnings([], "FEAT-TEST-002", tmp_path)

        assert result is None

    def test_extract_warnings_file_content_includes_title(
        self, tmp_path: Path
    ) -> None:
        """Test that the markdown file includes the feature_id in title."""
        warnings = ["Test warning"]
        feature_id = "FEAT-FP-002"

        result = extract_warnings(warnings, feature_id, tmp_path)

        assert result is not None
        content = result.read_text()
        assert "# Warnings & Constraints: FEAT-FP-002" in content

    def test_extract_warnings_file_content_includes_introduction(
        self, tmp_path: Path
    ) -> None:
        """Test that the markdown file includes introduction text."""
        warnings = ["Test warning"]
        feature_id = "FEAT-XYZ-123"

        result = extract_warnings(warnings, feature_id, tmp_path)

        assert result is not None
        content = result.read_text()
        assert "FEAT-XYZ-123 has the following warnings" in content
        assert "must be observed during implementation" in content

    def test_extract_warnings_file_content_includes_bullet_points(
        self, tmp_path: Path
    ) -> None:
        """Test that warnings are formatted as bullet points."""
        warnings = [
            "Warning 1: First constraint",
            "Warning 2: Second constraint",
            "Warning 3: Third constraint",
        ]
        feature_id = "FEAT-TEST-003"

        result = extract_warnings(warnings, feature_id, tmp_path)

        assert result is not None
        content = result.read_text()
        assert "- Warning 1: First constraint" in content
        assert "- Warning 2: Second constraint" in content
        assert "- Warning 3: Third constraint" in content

    def test_extract_warnings_default_output_dir(self) -> None:
        """Test that default output_dir is docs/warnings."""
        # We test the function signature default, not actual file creation
        import inspect
        from guardkit.planning.warnings_extractor import extract_warnings

        sig = inspect.signature(extract_warnings)
        output_dir_param = sig.parameters["output_dir"]
        assert output_dir_param.default == Path("docs/warnings")

    def test_extract_warnings_creates_output_dir_if_not_exists(
        self, tmp_path: Path
    ) -> None:
        """Test that the function creates output directory if it doesn't exist."""
        output_dir = tmp_path / "nested" / "warnings"
        warnings = ["A warning"]
        feature_id = "FEAT-NESTED"

        result = extract_warnings(warnings, feature_id, output_dir)

        assert result is not None
        assert output_dir.exists()
        assert result.parent == output_dir

    def test_extract_warnings_single_warning(self, tmp_path: Path) -> None:
        """Test extraction with a single warning."""
        warnings = ["Only one warning"]
        feature_id = "FEAT-SINGLE"

        result = extract_warnings(warnings, feature_id, tmp_path)

        assert result is not None
        content = result.read_text()
        assert "- Only one warning" in content

    def test_extract_warnings_special_characters(self, tmp_path: Path) -> None:
        """Test that special characters in warnings are preserved."""
        warnings = [
            "Warning with `code blocks` and **markdown**",
            "Warning with path: /path/to/file.py",
            "Warning with colon: key: value",
        ]
        feature_id = "FEAT-SPECIAL"

        result = extract_warnings(warnings, feature_id, tmp_path)

        assert result is not None
        content = result.read_text()
        assert "`code blocks`" in content
        assert "**markdown**" in content
        assert "/path/to/file.py" in content

    def test_extract_warnings_idempotent(self, tmp_path: Path) -> None:
        """Test that running extract_warnings multiple times is idempotent."""
        warnings = ["Consistent warning"]
        feature_id = "FEAT-IDEM"

        result1 = extract_warnings(warnings, feature_id, tmp_path)
        content1 = result1.read_text() if result1 else ""

        result2 = extract_warnings(warnings, feature_id, tmp_path)
        content2 = result2.read_text() if result2 else ""

        assert content1 == content2
