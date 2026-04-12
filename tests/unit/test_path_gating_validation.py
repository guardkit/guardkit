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
    has_unquoted_glob,
    suggest_paths,
    validate_rules_path_gating,
    validate_rules_glob_quoting,
    validate_rules_yaml_frontmatter,
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
            "code-style.md": '---\npaths: "**/*.py"\n---\n\n# Style',
            "testing.md": '---\npaths: "tests/**/*"\n---\n\n# Tests',
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


# ============================================================================
# 5. has_unquoted_glob Tests
# ============================================================================


class TestHasUnquotedGlob:
    """Test unquoted glob pattern detection in frontmatter."""

    def test_unquoted_glob_detected(self):
        """Detect unquoted asterisk in paths: value."""
        assert has_unquoted_glob("paths: **/*.py") is True

    def test_unquoted_glob_single_star(self):
        """Detect single unquoted asterisk."""
        assert has_unquoted_glob("paths: *.py") is True

    def test_unquoted_glob_with_prefix(self):
        """Detect unquoted glob after a directory prefix."""
        assert has_unquoted_glob("paths: src/**/*.ts") is True

    def test_quoted_glob_passes(self):
        """Properly quoted globs are not flagged."""
        assert has_unquoted_glob('paths: "**/*.py"') is False

    def test_single_quoted_glob_passes(self):
        """Single-quoted globs are not flagged."""
        assert has_unquoted_glob("paths: '**/*.py'") is False

    def test_array_syntax_passes(self):
        """YAML array syntax with quoted values passes."""
        assert has_unquoted_glob('paths: ["**/*.py", "tests/**/*"]') is False

    def test_no_paths_key(self):
        """No paths: key returns False."""
        assert has_unquoted_glob("description: some rule") is False

    def test_quoted_comma_separated_passes(self):
        """Comma-separated quoted values pass."""
        assert has_unquoted_glob('paths: "**/*.py, **/*.pyx"') is False

    def test_unquoted_comma_separated_detected(self):
        """Unquoted comma-separated values with glob detected."""
        assert has_unquoted_glob("paths: **/*.py, **/*.pyx") is True


# ============================================================================
# 6. validate_rules_glob_quoting Tests
# ============================================================================


class TestValidateRulesGlobQuoting:
    """Test the glob quoting validation function."""

    def test_no_rules_dir(self, tmp_path):
        """Return empty when .claude/rules/ doesn't exist."""
        issues = validate_rules_glob_quoting(tmp_path)
        assert issues == []

    def test_properly_quoted_no_issues(self, tmp_path):
        """No issues for properly quoted glob patterns."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "code-style.md").write_text(
            '---\npaths: "**/*.py, **/*.pyx"\n---\n\n# Code Style'
        )
        (rules_dir / "testing.md").write_text(
            '---\npaths: "tests/**/*.py"\n---\n\n# Testing'
        )

        issues = validate_rules_glob_quoting(tmp_path)
        assert issues == []

    def test_unquoted_glob_detected(self, tmp_path):
        """Detect unquoted glob pattern and report with file path."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "bad.md").write_text(
            "---\npaths: **/*.py\n---\n\n# Bad"
        )

        issues = validate_rules_glob_quoting(tmp_path)
        assert len(issues) == 1
        assert "bad.md" in issues[0].message
        assert "unquoted glob" in issues[0].message
        assert issues[0].severity == IssueSeverity.HIGH
        assert issues[0].category == IssueCategory.PATH_GATING
        assert issues[0].fixable is True

    def test_fix_description_includes_quoted_value(self, tmp_path):
        """Fix description shows properly quoted value."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "bad.md").write_text(
            "---\npaths: src/**/*.ts\n---\n\n# Bad"
        )

        issues = validate_rules_glob_quoting(tmp_path)
        assert len(issues) == 1
        assert '"src/**/*.ts"' in issues[0].fix_description

    def test_files_without_frontmatter_skipped(self, tmp_path):
        """Files without frontmatter are silently skipped."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "no-fm.md").write_text("# No frontmatter\nContent")

        issues = validate_rules_glob_quoting(tmp_path)
        assert issues == []

    def test_files_without_paths_key_skipped(self, tmp_path):
        """Files with frontmatter but no paths: key are skipped."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "other.md").write_text(
            "---\ndescription: A rule\n---\n\n# Other"
        )

        issues = validate_rules_glob_quoting(tmp_path)
        assert issues == []

    def test_nested_rules_files_checked(self, tmp_path):
        """Validate files in subdirectories like patterns/."""
        patterns_dir = tmp_path / ".claude" / "rules" / "patterns"
        patterns_dir.mkdir(parents=True)

        (patterns_dir / "bad-pattern.md").write_text(
            "---\npaths: **/handlers/*.py\n---\n\n# Bad Pattern"
        )

        issues = validate_rules_glob_quoting(tmp_path)
        assert len(issues) == 1
        assert "patterns/bad-pattern.md" in issues[0].location

    def test_mixed_quoted_and_unquoted(self, tmp_path):
        """Only flag files with unquoted patterns."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "good.md").write_text(
            '---\npaths: "**/*.py"\n---\n\n# Good'
        )
        (rules_dir / "bad.md").write_text(
            "---\npaths: **/*.py\n---\n\n# Bad"
        )

        issues = validate_rules_glob_quoting(tmp_path)
        assert len(issues) == 1
        assert "bad.md" in issues[0].message


# ============================================================================
# 7. GlobalTemplateValidationSection Glob Quoting Integration
# ============================================================================


class TestGlobalSectionGlobQuoting:
    """Test Section 7 integration with glob quoting validation."""

    def _create_template(self, tmp_path, rules_files=None):
        """Helper to create template with required files."""
        (tmp_path / "manifest.json").write_text("{}")
        (tmp_path / "CLAUDE.md").write_text("# CLAUDE")
        (tmp_path / "README.md").write_text("# README")

        if rules_files:
            rules_dir = tmp_path / ".claude" / "rules"
            rules_dir.mkdir(parents=True)
            for name, content in rules_files.items():
                (rules_dir / name).write_text(content)

    def test_unquoted_glob_reduces_score(self, tmp_path):
        """Unquoted glob patterns reduce the section score."""
        self._create_template(tmp_path, rules_files={
            "bad.md": "---\npaths: **/*.py\n---\n\n# Bad",
        })

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        assert result.score < 10.0
        assert result.metadata["glob_quoting_issues"] == 1

    def test_quoted_glob_no_score_impact(self, tmp_path):
        """Properly quoted globs have no score impact."""
        self._create_template(tmp_path, rules_files={
            "good.md": '---\npaths: "**/*.py"\n---\n\n# Good',
        })

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        assert result.score == 10.0
        assert result.metadata["glob_quoting_issues"] == 0

    def test_multiple_unquoted_globs_capped_deduction(self, tmp_path):
        """Score deduction for unquoted globs is capped at 3.0."""
        self._create_template(tmp_path, rules_files={
            f"bad-{i}.md": f"---\npaths: **/*.py\n---\n\n# Bad {i}"
            for i in range(5)
        })

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        # 5 glob issues * 1.0 = 5.0, capped at 3.0  → -3.0
        # 5 yaml issues * 1.0 = 5.0, capped at 3.0  → -3.0
        # Total deduction: -6.0, score = 10.0 - 6.0 = 4.0
        assert result.score >= 4.0
        assert result.score <= 4.0


# ============================================================================
# 8. validate_rules_yaml_frontmatter Tests
# ============================================================================


class TestValidateRulesYamlFrontmatter:
    """Test YAML frontmatter validation using yaml.safe_load()."""

    def test_no_rules_dir(self, tmp_path):
        """Return empty when .claude/rules/ doesn't exist."""
        issues = validate_rules_yaml_frontmatter(tmp_path)
        assert issues == []

    def test_valid_yaml_no_issues(self, tmp_path):
        """No issues for valid YAML frontmatter."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "code-style.md").write_text(
            '---\npaths: "**/*.py, **/*.pyx"\n---\n\n# Code Style'
        )
        (rules_dir / "testing.md").write_text(
            '---\npaths: ["tests/**/*.py", "**/*.test.ts"]\n---\n\n# Testing'
        )

        issues = validate_rules_yaml_frontmatter(tmp_path)
        assert issues == []

    def test_unquoted_glob_detected(self, tmp_path):
        """Detect unquoted glob pattern (failure pattern 1)."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "bad.md").write_text(
            "---\npaths: **/*.py\n---\n\n# Bad"
        )

        issues = validate_rules_yaml_frontmatter(tmp_path)
        assert len(issues) == 1
        assert issues[0].severity == IssueSeverity.HIGH
        assert issues[0].category == IssueCategory.PATH_GATING
        assert "bad.md" in issues[0].location
        assert "Invalid YAML" in issues[0].message
        assert issues[0].fixable is True

    def test_comma_separated_quoted_strings_detected(self, tmp_path):
        """Detect comma-separated quoted strings (failure pattern 2)."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "bad.md").write_text(
            '---\npaths: "**/*.py", "**/*.pyx"\n---\n\n# Bad'
        )

        issues = validate_rules_yaml_frontmatter(tmp_path)
        assert len(issues) == 1
        assert "bad.md" in issues[0].location
        assert "Invalid YAML" in issues[0].message

    def test_files_without_frontmatter_skipped(self, tmp_path):
        """Files without frontmatter are silently skipped."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "no-fm.md").write_text("# No frontmatter\nContent")

        issues = validate_rules_yaml_frontmatter(tmp_path)
        assert issues == []

    def test_nested_rules_files_checked(self, tmp_path):
        """Validate files in subdirectories like patterns/."""
        patterns_dir = tmp_path / ".claude" / "rules" / "patterns"
        patterns_dir.mkdir(parents=True)

        (patterns_dir / "bad-pattern.md").write_text(
            "---\npaths: **/*.py\n---\n\n# Bad Pattern"
        )

        issues = validate_rules_yaml_frontmatter(tmp_path)
        assert len(issues) == 1
        assert "patterns/bad-pattern.md" in issues[0].location

    def test_multiple_invalid_files(self, tmp_path):
        """Report issues for each invalid file."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "bad1.md").write_text(
            "---\npaths: **/*.py\n---\n\n# Bad 1"
        )
        (rules_dir / "bad2.md").write_text(
            '---\npaths: "a", "b"\n---\n\n# Bad 2'
        )
        (rules_dir / "good.md").write_text(
            '---\npaths: "**/*.py"\n---\n\n# Good'
        )

        issues = validate_rules_yaml_frontmatter(tmp_path)
        assert len(issues) == 2

    def test_fix_description_includes_guidance(self, tmp_path):
        """Fix description provides actionable guidance."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "bad.md").write_text(
            "---\npaths: **/*.py\n---\n\n# Bad"
        )

        issues = validate_rules_yaml_frontmatter(tmp_path)
        assert len(issues) == 1
        assert "quote glob" in issues[0].fix_description.lower()

    def test_valid_frontmatter_without_paths(self, tmp_path):
        """Valid frontmatter without paths: key passes."""
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)

        (rules_dir / "desc-only.md").write_text(
            "---\ndescription: A rule file\n---\n\n# Desc Only"
        )

        issues = validate_rules_yaml_frontmatter(tmp_path)
        assert issues == []


# ============================================================================
# 9. GlobalTemplateValidationSection YAML Frontmatter Integration
# ============================================================================


class TestGlobalSectionYamlFrontmatter:
    """Test Section 7 integration with YAML frontmatter validation."""

    def _create_template(self, tmp_path, rules_files=None):
        """Helper to create template with required files."""
        (tmp_path / "manifest.json").write_text("{}")
        (tmp_path / "CLAUDE.md").write_text("# CLAUDE")
        (tmp_path / "README.md").write_text("# README")

        if rules_files:
            rules_dir = tmp_path / ".claude" / "rules"
            rules_dir.mkdir(parents=True)
            for name, content in rules_files.items():
                (rules_dir / name).write_text(content)

    def test_invalid_yaml_reduces_score(self, tmp_path):
        """Invalid YAML frontmatter reduces the section score."""
        self._create_template(tmp_path, rules_files={
            "bad.md": "---\npaths: **/*.py\n---\n\n# Bad",
        })

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        assert result.score < 10.0
        assert result.metadata["yaml_frontmatter_issues"] == 1

    def test_valid_yaml_no_score_impact(self, tmp_path):
        """Valid YAML frontmatter has no score impact."""
        self._create_template(tmp_path, rules_files={
            "good.md": '---\npaths: "**/*.py"\n---\n\n# Good',
        })

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        assert result.score == 10.0
        assert result.metadata["yaml_frontmatter_issues"] == 0

    def test_yaml_issues_capped_deduction(self, tmp_path):
        """Score deduction for YAML issues is capped at 3.0."""
        self._create_template(tmp_path, rules_files={
            f"bad-{i}.md": f"---\npaths: **/*.py\n---\n\n# Bad {i}"
            for i in range(5)
        })

        section = GlobalTemplateValidationSection()
        result = section.execute(tmp_path)

        # YAML issues: 5 * 1.0 = 5.0, capped at 3.0
        # Glob quoting issues also fire for same files: 5 * 1.0, capped at 3.0
        # 10.0 - 3.0 - 3.0 = 4.0
        assert result.score >= 4.0
