"""
Unit Tests for Path-Gating Validation (Section 7)

Tests the rules path-gating validation that checks .claude/rules/*.md
files for paths: frontmatter to enable conditional loading.

Coverage Target: >=85%
"""

import pytest
from pathlib import Path

from installer.core.lib.template_validation.sections.section_07_global import (
    has_paths_frontmatter,
    suggest_paths,
    validate_rules_path_gating,
    GlobalTemplateValidationSection,
)
from installer.core.lib.template_validation.models import (
    IssueCategory,
    IssueSeverity,
)


# ============================================================================
# 1. has_paths_frontmatter Tests
# ============================================================================


class TestHasPathsFrontmatter:
    """Test frontmatter detection logic."""

    def test_valid_paths_frontmatter(self):
        """Detect paths: in standard YAML frontmatter."""
        content = "---\npaths: src/**/*.py\n---\n\n# Title\nContent"
        assert has_paths_frontmatter(content) is True

    def test_paths_with_multiple_patterns(self):
        """Detect paths: with comma-separated patterns."""
        content = '---\npaths: src/**/*.py, tests/**/*.py\n---\n\n# Title'
        assert has_paths_frontmatter(content) is True

    def test_paths_with_array_syntax(self):
        """Detect paths: using YAML array syntax."""
        content = '---\npaths: ["src/**/*.ts", "lib/**/*.tsx"]\n---\n\n# Title'
        assert has_paths_frontmatter(content) is True

    def test_paths_with_quotes(self):
        """Detect paths: with quoted values."""
        content = '---\npaths: "**/models.py", "**/schemas.py"\n---\n\n# Title'
        assert has_paths_frontmatter(content) is True

    def test_paths_with_other_frontmatter(self):
        """Detect paths: alongside other frontmatter keys."""
        content = "---\npaths: src/**/*.py\ndescription: Some rule\n---\n\n# Title"
        assert has_paths_frontmatter(content) is True

    def test_no_frontmatter(self):
        """Return False when no frontmatter exists."""
        content = "# Title\n\nContent without frontmatter"
        assert has_paths_frontmatter(content) is False

    def test_frontmatter_without_paths(self):
        """Return False when frontmatter exists but without paths: key."""
        content = "---\ndescription: A rule file\nauthor: test\n---\n\n# Title"
        assert has_paths_frontmatter(content) is False

    def test_empty_frontmatter(self):
        """Return False for empty frontmatter."""
        content = "---\n\n---\n\n# Title"
        assert has_paths_frontmatter(content) is False

    def test_paths_in_body_not_frontmatter(self):
        """Return False when paths: appears in body but not frontmatter."""
        content = "# Title\n\npaths: this is body text, not frontmatter"
        assert has_paths_frontmatter(content) is False

    def test_empty_content(self):
        """Return False for empty content."""
        assert has_paths_frontmatter("") is False

    def test_incomplete_frontmatter(self):
        """Return False for incomplete frontmatter (no closing ---)."""
        content = "---\npaths: src/**/*.py\n\n# Title"
        assert has_paths_frontmatter(content) is False


# ============================================================================
# 2. suggest_paths Tests
# ============================================================================


class TestSuggestPaths:
    """Test path suggestion logic."""

    def test_known_filename_code_style(self):
        """Suggest patterns for code-style.md."""
        result = suggest_paths("code-style.md")
        assert "**/*.py" in result
        assert "**/*.ts" in result

    def test_known_filename_testing(self):
        """Suggest patterns for testing.md."""
        result = suggest_paths("testing.md")
        assert "tests/" in result

    def test_known_filename_docker(self):
        """Suggest patterns for docker.md."""
        result = suggest_paths("docker.md")
        assert "Dockerfile" in result

    def test_known_filename_workflow(self):
        """Suggest patterns for workflow.md."""
        result = suggest_paths("workflow.md")
        assert "tasks/" in result

    def test_unknown_filename_gets_fallback(self):
        """Unknown filenames get a TODO fallback suggestion."""
        result = suggest_paths("custom-rules.md")
        assert "**/*" in result
        assert "TODO" in result


# ============================================================================
# 3. validate_rules_path_gating Tests
# ============================================================================


class TestValidateRulesPathGating:
    """Test the full validation function."""

    def test_no_rules_dir(self, tmp_path):
        """Return empty results when .claude/rules/ doesn't exist."""
        issues, total, gated, ungated = validate_rules_path_gating(tmp_path)
        assert issues == []
        assert total == 0
        assert gated == 0
        assert ungated == []

    def test_all_files_gated(self, tmp_path):
        """Return no issues when all files have paths: frontmatter."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "code-style.md").write_text(
            "---\npaths: **/*.py\n---\n\n# Code Style"
        )
        (rules_dir / "testing.md").write_text(
            "---\npaths: tests/**/*.py\n---\n\n# Testing"
        )

        issues, total, gated, ungated = validate_rules_path_gating(tmp_path)
        assert issues == []
        assert total == 2
        assert gated == 2
        assert ungated == []

    def test_missing_frontmatter_detected(self, tmp_path):
        """Detect files missing paths: frontmatter."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "code-style.md").write_text(
            "---\npaths: **/*.py\n---\n\n# Code Style"
        )
        (rules_dir / "no-paths.md").write_text("# Missing Frontmatter\nContent")

        issues, total, gated, ungated = validate_rules_path_gating(tmp_path)
        assert len(issues) == 1
        assert total == 2
        assert gated == 1
        assert len(ungated) == 1
        assert ".claude/rules/no-paths.md" in ungated[0]

    def test_issue_severity_and_category(self, tmp_path):
        """Verify issue severity and category are correct."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "ungated.md").write_text("# No frontmatter")

        issues, _, _, _ = validate_rules_path_gating(tmp_path)
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.MEDIUM
        assert issues[0].category == IssueCategory.PATH_GATING
        assert issues[0].fixable is True

    def test_issue_includes_suggestion(self, tmp_path):
        """Verify issue message includes path suggestion."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "testing.md").write_text("# Testing\nNo frontmatter")

        issues, _, _, _ = validate_rules_path_gating(tmp_path)
        assert "Suggested: paths:" in issues[0].message
        assert "tests/" in issues[0].message

    def test_nested_rules_files(self, tmp_path):
        """Validate files in subdirectories like patterns/."""
        rules_dir = tmp_path / ".claude" / "rules" / "patterns"
        rules_dir.mkdir(parents=True)

        (rules_dir / "dataclasses.md").write_text("# Dataclasses\nNo frontmatter")

        issues, total, gated, ungated = validate_rules_path_gating(tmp_path)
        assert total == 1
        assert gated == 0
        assert ".claude/rules/patterns/dataclasses.md" in ungated[0]

    def test_mixed_gated_and_ungated(self, tmp_path):
        """Handle mix of gated and ungated files."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "a.md").write_text("---\npaths: **/*.py\n---\n\n# A")
        (rules_dir / "b.md").write_text("# B - no frontmatter")
        (rules_dir / "c.md").write_text("---\npaths: src/**/*\n---\n\n# C")
        (rules_dir / "d.md").write_text("# D - no frontmatter")

        issues, total, gated, ungated = validate_rules_path_gating(tmp_path)
        assert total == 4
        assert gated == 2
        assert len(issues) == 2
        assert len(ungated) == 2


# ============================================================================
# 4. GlobalTemplateValidationSection Integration Tests
# ============================================================================


class TestGlobalTemplateValidationSection:
    """Test the full Section 7 execution with path-gating."""

    def _create_template(self, tmp_path, with_required=True, rules_files=None):
        """Helper to create a template directory structure."""
        if with_required:
            (tmp_path / "manifest.json").write_text("{}")
            (tmp_path / "CLAUDE.md").write_text("# CLAUDE")
            (tmp_path / "README.md").write_text("# README")

        if rules_files:
            rules_dir = tmp_path / ".claude" / "rules"
            rules_dir.mkdir(parents=True)
            for name, content in rules_files.items():
                (rules_dir / name).write_text(content)

    def test_full_coverage_positive_finding(self, tmp_path):
        """100% path-gating coverage produces positive finding."""
        self._create_template(tmp_path, rules_files={
            "code-style.md": "---\npaths: **/*.py\n---\n\n# Style",
            "testing.md": "---\npaths: tests/**/*\n---\n\n# Tests",
        })

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        assert result.score == 10.0
        positive_findings = [f for f in result.findings if f.is_positive]
        titles = [f.title for f in positive_findings]
        assert "Full Path-Gating Coverage" in titles
        assert result.metadata["path_gating_coverage_pct"] == 100.0

    def test_partial_coverage_negative_finding(self, tmp_path):
        """Partial path-gating coverage produces negative finding and score deduction."""
        self._create_template(tmp_path, rules_files={
            "code-style.md": "---\npaths: **/*.py\n---\n\n# Style",
            "no-paths.md": "# No frontmatter",
        })

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        assert result.score < 10.0
        negative_findings = [f for f in result.findings if not f.is_positive]
        assert any("Incomplete Path-Gating" in f.title for f in negative_findings)
        assert result.metadata["path_gating_coverage_pct"] == 50.0

    def test_no_rules_dir_no_path_gating_issues(self, tmp_path):
        """Templates without .claude/rules/ get no path-gating issues."""
        self._create_template(tmp_path)

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        assert result.metadata["path_gating_total"] == 0
        assert result.metadata["path_gating_coverage_pct"] == 100.0

    def test_score_deduction_capped(self, tmp_path):
        """Score deduction for ungated files is capped at 3.0."""
        self._create_template(tmp_path, rules_files={
            f"rule-{i}.md": "# No frontmatter" for i in range(10)
        })

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        # 10 ungated * 0.5 = 5.0, but capped at 3.0
        # 10.0 - 3.0 = 7.0
        assert result.score == 7.0

    def test_recommendations_for_ungated(self, tmp_path):
        """Ungated files produce a recommendation."""
        self._create_template(tmp_path, rules_files={
            "ungated.md": "# No frontmatter",
        })

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        assert len(result.recommendations) >= 1
        assert "paths:" in result.recommendations[0].title.lower() or \
               "paths:" in result.recommendations[0].description.lower()

    def test_metadata_includes_ungated_file_list(self, tmp_path):
        """Metadata includes list of ungated files."""
        self._create_template(tmp_path, rules_files={
            "gated.md": "---\npaths: **/*\n---\n\n# Gated",
            "ungated.md": "# No frontmatter",
        })

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        assert ".claude/rules/ungated.md" in result.metadata["path_gating_ungated_files"]
        assert len(result.metadata["path_gating_ungated_files"]) == 1
