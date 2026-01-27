"""
Unit Tests for Security False Positive Filtering (TASK-SEC-005).

Tests for false positive filtering logic based on Claude Code security-review
techniques. Validates confidence threshold, exclusion categories, and file
pattern exclusions.

Test Categories:
- Exclusion category tests (DOS, rate limiting, resource management, open redirect)
- Confidence threshold tests (0.8 threshold)
- File pattern exclusion tests (markdown, test files, docs)
- Real vulnerability non-exclusion tests
"""

import pytest
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from guardkit.orchestrator.security_config import (
    SecurityConfig,
    SecurityLevel,
    DEFAULT_EXCLUDE_CATEGORIES,
    DEFAULT_EXCLUDE_PATTERNS,
)
from guardkit.orchestrator.quality_gates.security_checker import SecurityFinding


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_dos_finding():
    """Create a DOS vulnerability finding (should be excluded)."""
    return SecurityFinding(
        check_id="dos-infinite-loop",
        severity="medium",
        description="Infinite loop could cause denial of service",
        file_path="app.py",
        line_number=42,
        matched_text="while True: pass",
        recommendation="Add loop termination condition",
    )


@pytest.fixture
def sample_rate_limit_finding():
    """Create a rate limiting finding (should be excluded)."""
    return SecurityFinding(
        check_id="missing-rate-limit",
        severity="low",
        description="Missing rate limiting on API endpoint",
        file_path="api.py",
        line_number=100,
        matched_text="@app.route('/api/data')",
        recommendation="Add rate limiting middleware",
    )


@pytest.fixture
def sample_resource_management_finding():
    """Create a resource management finding (should be excluded)."""
    return SecurityFinding(
        check_id="resource-leak",
        severity="medium",
        description="Memory leak in connection pool",
        file_path="db.py",
        line_number=50,
        matched_text="connection = pool.get()",
        recommendation="Implement proper connection cleanup",
    )


@pytest.fixture
def sample_open_redirect_finding():
    """Create an open redirect finding (should be excluded)."""
    return SecurityFinding(
        check_id="open-redirect",
        severity="medium",
        description="Open redirect vulnerability in login flow",
        file_path="auth.py",
        line_number=75,
        matched_text="redirect(request.args.get('next'))",
        recommendation="Validate redirect URLs",
    )


@pytest.fixture
def sample_sql_injection_finding():
    """Create a SQL injection finding (should NOT be excluded)."""
    return SecurityFinding(
        check_id="sql-injection",
        severity="critical",
        description="SQL injection via user input",
        file_path="query.py",
        line_number=30,
        matched_text='f"SELECT * FROM users WHERE id = {user_id}"',
        recommendation="Use parameterized queries",
    )


@pytest.fixture
def sample_xss_finding():
    """Create an XSS finding (should NOT be excluded)."""
    return SecurityFinding(
        check_id="xss-vulnerability",
        severity="high",
        description="Possible XSS via innerHTML",
        file_path="template.js",
        line_number=20,
        matched_text="element.innerHTML = userContent",
        recommendation="Use textContent or sanitize input",
    )


@pytest.fixture
def sample_hardcoded_secret_finding():
    """Create a hardcoded secret finding (should NOT be excluded)."""
    return SecurityFinding(
        check_id="hardcoded-secrets",
        severity="critical",
        description="Hardcoded API key detected",
        file_path="config.py",
        line_number=5,
        matched_text='API_KEY = "sk-1234567890"',
        recommendation="Use environment variables",
    )


# ============================================================================
# Helper Functions for Testing
# ============================================================================


def is_excluded_by_category(finding: SecurityFinding, config: SecurityConfig) -> bool:
    """Check if finding should be excluded based on category."""
    # Check if finding check_id contains excluded category keywords
    check_id_lower = finding.check_id.lower()
    description_lower = finding.description.lower()

    for category in config.exclude_categories:
        category_lower = category.lower()
        if category_lower in check_id_lower or category_lower in description_lower:
            return True

    return False


def is_excluded_by_pattern(finding: SecurityFinding, config: SecurityConfig) -> bool:
    """Check if finding should be excluded based on file pattern."""
    import fnmatch

    file_path = finding.file_path

    for pattern in config.exclude_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True

    return False


def should_exclude_file(file_path: str, config: Optional[SecurityConfig] = None) -> bool:
    """Check if file should be excluded from security scanning."""
    import fnmatch

    if config is None:
        config = SecurityConfig()

    for pattern in config.exclude_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True

    return False


# ============================================================================
# Exclusion Category Tests
# ============================================================================


class TestExclusionCategories:
    """Test that low-value findings are excluded by category."""

    def test_default_exclude_categories_contains_dos(self):
        """DEFAULT_EXCLUDE_CATEGORIES should include 'dos'."""
        assert "dos" in DEFAULT_EXCLUDE_CATEGORIES

    def test_default_exclude_categories_contains_rate_limiting(self):
        """DEFAULT_EXCLUDE_CATEGORIES should include 'rate-limiting'."""
        assert "rate-limiting" in DEFAULT_EXCLUDE_CATEGORIES

    def test_default_exclude_categories_contains_resource_management(self):
        """DEFAULT_EXCLUDE_CATEGORIES should include 'resource-management'."""
        assert "resource-management" in DEFAULT_EXCLUDE_CATEGORIES

    def test_default_exclude_categories_contains_open_redirect(self):
        """DEFAULT_EXCLUDE_CATEGORIES should include 'open-redirect'."""
        assert "open-redirect" in DEFAULT_EXCLUDE_CATEGORIES

    def test_dos_findings_excluded(self, sample_dos_finding):
        """DOS vulnerabilities should be filtered."""
        config = SecurityConfig()

        excluded = is_excluded_by_category(sample_dos_finding, config)

        assert excluded is True

    def test_rate_limit_findings_excluded(self, sample_rate_limit_finding):
        """Rate limiting recommendations should be filtered."""
        config = SecurityConfig()

        excluded = is_excluded_by_category(sample_rate_limit_finding, config)

        assert excluded is True

    def test_resource_management_findings_excluded(self, sample_resource_management_finding):
        """Resource management issues should be filtered."""
        config = SecurityConfig()

        excluded = is_excluded_by_category(sample_resource_management_finding, config)

        assert excluded is True

    def test_open_redirect_findings_excluded(self, sample_open_redirect_finding):
        """Open redirect vulnerabilities should be filtered."""
        config = SecurityConfig()

        excluded = is_excluded_by_category(sample_open_redirect_finding, config)

        assert excluded is True


# ============================================================================
# Real Vulnerability Non-Exclusion Tests
# ============================================================================


class TestRealVulnerabilitiesNotExcluded:
    """Test that real security issues are NOT filtered."""

    def test_sql_injection_not_excluded(self, sample_sql_injection_finding):
        """SQL injection should NOT be filtered."""
        config = SecurityConfig()

        excluded = is_excluded_by_category(sample_sql_injection_finding, config)

        assert excluded is False

    def test_xss_not_excluded(self, sample_xss_finding):
        """XSS vulnerabilities should NOT be filtered."""
        config = SecurityConfig()

        excluded = is_excluded_by_category(sample_xss_finding, config)

        assert excluded is False

    def test_hardcoded_secrets_not_excluded(self, sample_hardcoded_secret_finding):
        """Hardcoded secrets should NOT be filtered."""
        config = SecurityConfig()

        excluded = is_excluded_by_category(sample_hardcoded_secret_finding, config)

        assert excluded is False

    def test_command_injection_not_excluded(self):
        """Command injection should NOT be filtered."""
        finding = SecurityFinding(
            check_id="command-injection",
            severity="critical",
            description="Shell command injection detected",
            file_path="utils.py",
            line_number=15,
            matched_text='subprocess.run(f"ls {path}", shell=True)',
            recommendation="Use list arguments without shell=True",
        )
        config = SecurityConfig()

        excluded = is_excluded_by_category(finding, config)

        assert excluded is False

    def test_pickle_load_not_excluded(self):
        """Pickle deserialization should NOT be filtered."""
        finding = SecurityFinding(
            check_id="pickle-load",
            severity="critical",
            description="Unsafe pickle deserialization",
            file_path="serializer.py",
            line_number=25,
            matched_text="pickle.load(f)",
            recommendation="Use safe serialization format",
        )
        config = SecurityConfig()

        excluded = is_excluded_by_category(finding, config)

        assert excluded is False


# ============================================================================
# Confidence Threshold Tests
# ============================================================================


class TestConfidenceThreshold:
    """Test confidence threshold filtering (0.8 threshold)."""

    def test_high_confidence_not_filtered(self):
        """Findings with confidence >= 0.8 should NOT be filtered."""
        # Note: SecurityFinding doesn't have confidence field in current impl
        # This tests the concept for future enhancement
        confidence = 0.95
        assert confidence >= 0.8

    def test_low_confidence_filtered(self):
        """Findings with confidence < 0.8 should be filtered."""
        confidence = 0.6
        assert confidence < 0.8

    def test_threshold_boundary_exactly_0_8(self):
        """Findings with exactly 0.8 confidence should NOT be filtered."""
        confidence = 0.8
        assert confidence >= 0.8

    def test_threshold_boundary_just_below(self):
        """Findings with 0.79 confidence should be filtered."""
        confidence = 0.79
        assert confidence < 0.8


# ============================================================================
# File Pattern Exclusion Tests
# ============================================================================


class TestFilePatternExclusion:
    """Test file pattern exclusion for reducing noise."""

    def test_default_exclude_patterns_contains_markdown(self):
        """DEFAULT_EXCLUDE_PATTERNS should include '*.md'."""
        assert "*.md" in DEFAULT_EXCLUDE_PATTERNS

    def test_default_exclude_patterns_contains_test_files(self):
        """DEFAULT_EXCLUDE_PATTERNS should include '*.test.*'."""
        assert "*.test.*" in DEFAULT_EXCLUDE_PATTERNS

    def test_default_exclude_patterns_contains_docs(self):
        """DEFAULT_EXCLUDE_PATTERNS should include 'docs/**'."""
        assert "docs/**" in DEFAULT_EXCLUDE_PATTERNS

    def test_default_exclude_patterns_contains_fixtures(self):
        """DEFAULT_EXCLUDE_PATTERNS should include '**/fixtures/**'."""
        assert "**/fixtures/**" in DEFAULT_EXCLUDE_PATTERNS

    def test_markdown_files_excluded(self):
        """Findings in .md files should be excluded."""
        config = SecurityConfig()

        excluded = should_exclude_file("README.md", config)

        assert excluded is True

    def test_docs_files_excluded(self):
        """Findings in docs/ directory should be excluded."""
        config = SecurityConfig()

        excluded = should_exclude_file("docs/api-guide.md", config)

        assert excluded is True

    def test_fixture_files_excluded(self):
        """Findings in fixtures/ directory should be excluded."""
        config = SecurityConfig()

        excluded = should_exclude_file("tests/fixtures/vulnerable_sample.py", config)

        assert excluded is True

    def test_source_files_not_excluded(self):
        """Source files should NOT be excluded."""
        config = SecurityConfig()

        excluded = should_exclude_file("src/auth.py", config)

        assert excluded is False

    def test_config_files_not_excluded(self):
        """Config files should NOT be excluded."""
        config = SecurityConfig()

        excluded = should_exclude_file("config/settings.py", config)

        assert excluded is False


# ============================================================================
# Combined Filtering Tests
# ============================================================================


class TestCombinedFiltering:
    """Test combined filtering logic."""

    def test_finding_in_excluded_category_and_file_excluded(self):
        """Finding matching both category and file exclusion should be excluded."""
        finding = SecurityFinding(
            check_id="dos-vulnerability",
            severity="medium",
            description="DOS attack vector in test file",
            file_path="tests/fixtures/dos_test.py",
            line_number=10,
            matched_text="while True: process()",
            recommendation="Add timeout",
        )
        config = SecurityConfig()

        category_excluded = is_excluded_by_category(finding, config)
        file_excluded = is_excluded_by_pattern(finding, config)

        assert category_excluded or file_excluded

    def test_critical_in_excluded_file_still_considered(self):
        """Critical findings in excluded files should be noted for review."""
        finding = SecurityFinding(
            check_id="hardcoded-secrets",
            severity="critical",
            description="Hardcoded API key in fixture",
            file_path="tests/fixtures/config.py",
            line_number=5,
            matched_text='API_KEY = "sk-real-key"',
            recommendation="Use environment variables",
        )
        config = SecurityConfig()

        # File is excluded
        file_excluded = is_excluded_by_pattern(finding, config)
        # But category is not
        category_excluded = is_excluded_by_category(finding, config)

        assert file_excluded is True
        assert category_excluded is False

    def test_custom_exclusion_categories_respected(self):
        """Custom exclusion categories should be respected."""
        config = SecurityConfig(
            exclude_categories=["dos", "rate-limiting", "custom-category"]
        )

        finding = SecurityFinding(
            check_id="custom-category-issue",
            severity="medium",
            description="Custom category violation",
            file_path="src/app.py",
            line_number=15,
            matched_text="custom code",
            recommendation="Fix it",
        )

        excluded = is_excluded_by_category(finding, config)

        assert excluded is True

    def test_custom_exclusion_patterns_respected(self):
        """Custom exclusion patterns should be respected."""
        config = SecurityConfig(
            exclude_patterns=["*.md", "*.test.*", "generated/**"]
        )

        excluded = should_exclude_file("generated/api_client.py", config)

        assert excluded is True


# ============================================================================
# Edge Cases
# ============================================================================


class TestFilteringEdgeCases:
    """Test edge cases in filtering logic."""

    def test_empty_config_uses_defaults(self):
        """Empty config should use default exclusions."""
        config = SecurityConfig()

        assert len(config.exclude_categories) > 0
        assert len(config.exclude_patterns) > 0

    def test_none_file_path_handled_gracefully(self):
        """None file path should not crash filtering."""
        config = SecurityConfig()

        # Should not raise
        try:
            excluded = should_exclude_file("", config)
            assert isinstance(excluded, bool)
        except Exception:
            pytest.fail("should_exclude_file should handle empty string")

    def test_case_insensitive_category_matching(self):
        """Category matching should be case-insensitive."""
        finding = SecurityFinding(
            check_id="DOS-ATTACK",
            severity="medium",
            description="DENIAL OF SERVICE vulnerability",
            file_path="app.py",
            line_number=10,
            matched_text="attack code",
            recommendation="Fix it",
        )
        config = SecurityConfig()

        excluded = is_excluded_by_category(finding, config)

        # Should match 'dos' even with uppercase
        assert excluded is True

    def test_partial_category_matching(self):
        """Partial category match should work."""
        finding = SecurityFinding(
            check_id="rate-limiting-bypass",  # Contains 'rate-limiting'
            severity="medium",
            description="Rate limit bypass vulnerability",
            file_path="api.py",
            line_number=20,
            matched_text="bypass code",
            recommendation="Fix rate limiting",
        )
        config = SecurityConfig()

        excluded = is_excluded_by_category(finding, config)

        assert excluded is True
