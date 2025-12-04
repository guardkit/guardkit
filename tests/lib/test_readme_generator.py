#!/usr/bin/env python3
"""Unit tests for readme_generator module.

Tests the README generation functionality for feature subfolders, including
content extraction from review reports and template population.

Test Coverage:
    - ReviewReportParser.extract_executive_summary()
    - ReviewReportParser.extract_key_findings()
    - ReviewReportParser.extract_problem_statement()
    - ReviewReportParser.extract_recommendations()
    - ReviewReportParser.extract_scope()
    - ReviewReportParser.extract_success_criteria()
    - ReadmeGenerator.generate_subtask_table()
    - ReadmeGenerator.generate_readme()
    - generate_feature_readme() integration

Architecture:
    - Uses pytest fixtures for temporary file systems
    - Tests cover both happy path and edge cases
    - Includes tests with real review report structure
    - No external dependencies beyond pytest

Part of: TASK-FW-007 - Create README.md generator for features
Author: Claude (Anthropic)
Created: 2025-12-04
"""

import pytest
import sys
from pathlib import Path
from textwrap import dedent

# Add installer/global/lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "global"))

from lib.readme_generator import (
    ReviewReportParser,
    ReadmeGenerator,
    generate_feature_readme
)


class TestReviewReportParser:
    """Tests for ReviewReportParser class."""

    @pytest.fixture
    def sample_review_report(self, tmp_path):
        """Create a sample review report file."""
        report_content = dedent("""
        # Review Report: TASK-REV-001

        ## Executive Summary

        **Review Mode**: Architectural
        **Depth**: Standard
        **Duration**: 1.5 hours
        **Reviewer**: architectural-reviewer agent
        **Date**: 2025-12-04

        ### Key Findings

        This review analyzed the authentication system and identified critical security gaps.
        The current implementation lacks proper token validation and session management.

        **Root Cause**: Missing middleware for token validation and inadequate session expiry logic.

        **Severity**: HIGH - Security vulnerabilities that could lead to unauthorized access.

        ### Critical Gaps Identified

        1. **No Token Validation** - System doesn't verify JWT signatures
        2. **No Session Expiry** - Sessions never expire, creating security risk
        3. **Missing Rate Limiting** - No protection against brute force attacks

        ---

        ## Recommendations

        Implement a comprehensive authentication middleware that:

        1. **Token Validation**: Verify JWT signatures using public key cryptography
        2. **Session Management**: Implement 24-hour session expiry with refresh tokens
        3. **Rate Limiting**: Add Redis-based rate limiting for login endpoints
        4. **Audit Logging**: Log all authentication attempts for security monitoring

        ## Scope

        ### In Scope
        - JWT token validation middleware
        - Session management with Redis
        - Rate limiting implementation
        - Basic audit logging

        ### Out of Scope
        - Multi-factor authentication (deferred to Phase 2)
        - OAuth2 integration (separate feature)
        - Advanced threat detection (requires dedicated security platform)

        ## Success Criteria

        1. All JWT tokens are validated before processing requests
        2. Sessions expire after 24 hours of inactivity
        3. Rate limiting prevents >5 failed login attempts per minute
        4. All authentication events are logged with timestamp and IP
        """)

        report_path = tmp_path / "review-report.md"
        report_path.write_text(report_content)
        return report_path

    def test_extract_executive_summary(self, sample_review_report):
        """Test extraction of executive summary."""
        parser = ReviewReportParser(str(sample_review_report))
        summary = parser.extract_executive_summary()

        assert "Key Findings" in summary
        assert "critical security gaps" in summary
        assert "Review Mode" not in summary  # Metadata should be removed

    def test_extract_key_findings(self, sample_review_report):
        """Test extraction of key findings section."""
        parser = ReviewReportParser(str(sample_review_report))
        findings = parser.extract_key_findings()

        assert "critical security gaps" in findings
        assert "Root Cause" in findings
        assert "Severity" in findings  # Just check for "Severity" since the full text is there

    def test_extract_problem_statement(self, sample_review_report):
        """Test extraction of problem statement."""
        parser = ReviewReportParser(str(sample_review_report))
        problem = parser.extract_problem_statement()

        assert "No Token Validation" in problem
        assert "No Session Expiry" in problem
        assert "Missing Rate Limiting" in problem

    def test_extract_recommendations(self, sample_review_report):
        """Test extraction of recommendations."""
        parser = ReviewReportParser(str(sample_review_report))
        recommendations = parser.extract_recommendations()

        assert "Token Validation" in recommendations
        assert "Session Management" in recommendations
        assert "Rate Limiting" in recommendations
        assert "Audit Logging" in recommendations

    def test_extract_scope(self, sample_review_report):
        """Test extraction of in-scope and out-of-scope sections."""
        parser = ReviewReportParser(str(sample_review_report))
        in_scope, out_scope = parser.extract_scope()

        # In scope
        assert "JWT token validation" in in_scope
        assert "Session management with Redis" in in_scope

        # Out of scope
        assert "Multi-factor authentication" in out_scope
        assert "OAuth2 integration" in out_scope

    def test_extract_success_criteria(self, sample_review_report):
        """Test extraction of success criteria."""
        parser = ReviewReportParser(str(sample_review_report))
        criteria = parser.extract_success_criteria()

        assert "All JWT tokens are validated" in criteria
        assert "Sessions expire after 24 hours" in criteria
        assert "Rate limiting prevents" in criteria

    def test_parser_with_nonexistent_file(self, tmp_path):
        """Test parser handles nonexistent files gracefully."""
        parser = ReviewReportParser(str(tmp_path / "nonexistent.md"))

        assert parser.extract_executive_summary() == ""
        assert parser.extract_key_findings() == ""
        assert parser.extract_problem_statement() == ""
        assert parser.extract_recommendations() == ""

        in_scope, out_scope = parser.extract_scope()
        assert in_scope == ""
        assert out_scope == ""

    def test_parser_with_minimal_report(self, tmp_path):
        """Test parser with minimal report structure."""
        minimal_content = dedent("""
        # Review Report: TASK-REV-002

        ## Executive Summary

        This is a minimal review with just an executive summary.
        """)

        report_path = tmp_path / "minimal-report.md"
        report_path.write_text(minimal_content)

        parser = ReviewReportParser(str(report_path))
        summary = parser.extract_executive_summary()

        assert "minimal review" in summary
        assert parser.extract_recommendations() == ""  # Should handle missing sections


class TestReadmeGenerator:
    """Tests for ReadmeGenerator class."""

    @pytest.fixture
    def sample_subtasks(self):
        """Sample subtask data."""
        return [
            {
                'id': 'TASK-FW-001',
                'title': 'Create feature plan command',
                'method': 'direct',
                'status': 'backlog'
            },
            {
                'id': 'TASK-FW-002',
                'title': 'Auto-detect feature slug',
                'method': 'direct',
                'status': 'in_progress'
            },
            {
                'id': 'TASK-FW-003',
                'title': 'Auto-detect subtasks',
                'method': 'tdd',
                'status': 'completed'
            }
        ]

    def test_generate_subtask_table(self, sample_subtasks):
        """Test generation of subtask table."""
        generator = ReadmeGenerator()
        table = generator.generate_subtask_table(sample_subtasks)

        assert "| ID | Title | Method | Status |" in table
        assert "TASK-FW-001" in table
        assert "Create feature plan command" in table
        assert "direct" in table
        assert "backlog" in table
        assert "TASK-FW-003" in table
        assert "completed" in table

    def test_generate_subtask_table_empty(self):
        """Test subtask table with no subtasks."""
        generator = ReadmeGenerator()
        table = generator.generate_subtask_table([])

        assert "No subtasks defined yet" in table

    def test_generate_subtask_table_with_implementation_mode(self):
        """Test subtask table with implementation_mode field."""
        subtasks = [
            {
                'id': 'TASK-001',
                'title': 'Test task',
                'implementation_mode': 'tdd',  # Use implementation_mode instead of method
                'status': 'backlog'
            }
        ]

        generator = ReadmeGenerator()
        table = generator.generate_subtask_table(subtasks)

        assert "tdd" in table

    def test_generate_readme_with_complete_data(self, tmp_path, sample_subtasks):
        """Test README generation with complete review report data."""
        # Create a sample review report
        report_content = dedent("""
        # Review Report: TASK-REV-FW01

        ## Executive Summary

        This review analyzed the feature workflow streamlining requirements.

        ### Key Findings

        The current workflow requires too many manual steps for feature creation.

        ### Critical Gaps Identified

        1. No automated feature folder creation
        2. No README generation
        3. No subtask detection

        ## Recommendations

        Implement automated feature workflow tools:
        1. `/feature-plan` command
        2. Auto-detect feature slug from review
        3. Generate comprehensive README

        ## Scope

        ### In Scope
        - Feature folder creation automation
        - README generation from review reports
        - Subtask detection and organization

        ### Out of Scope
        - PM tool integration
        - Advanced analytics

        ## Success Criteria

        1. Features are created in <30 seconds
        2. READMEs include all required sections
        3. Subtasks are automatically organized
        """)

        report_path = tmp_path / "review-report.md"
        report_path.write_text(report_content)

        generator = ReadmeGenerator()
        readme = generator.generate_readme(
            feature_name="Feature Workflow Streamlining",
            feature_slug="feature-workflow-streamlining",
            review_task_id="TASK-REV-FW01",
            review_report_path=str(report_path),
            subtasks=sample_subtasks
        )

        # Verify sections are present
        assert "# Feature: Feature Workflow Streamlining" in readme
        assert "## Overview" in readme
        assert "## Problem Statement" in readme
        assert "## Solution" in readme
        assert "## Scope" in readme
        assert "### In Scope" in readme
        assert "### Out of Scope" in readme
        assert "## Success Criteria" in readme
        assert "## Subtasks" in readme
        assert "## Related Documents" in readme

        # Verify content is extracted
        assert "No automated feature folder creation" in readme
        assert "Implement automated feature workflow tools" in readme
        assert "Feature folder creation automation" in readme
        assert "PM tool integration" in readme
        assert "Features are created in <30 seconds" in readme

        # Verify subtasks are included
        assert "TASK-FW-001" in readme
        assert "Create feature plan command" in readme

        # Verify links
        assert "[TASK-REV-FW01](../TASK-REV-FW01.md)" in readme

    def test_generate_readme_with_missing_sections(self, tmp_path, sample_subtasks):
        """Test README generation when review report has missing sections."""
        # Create minimal report
        report_content = dedent("""
        # Review Report: TASK-REV-002

        ## Executive Summary

        Minimal review for testing.
        """)

        report_path = tmp_path / "minimal-report.md"
        report_path.write_text(report_content)

        generator = ReadmeGenerator()
        readme = generator.generate_readme(
            feature_name="Test Feature",
            feature_slug="test-feature",
            review_task_id="TASK-REV-002",
            review_report_path=str(report_path),
            subtasks=sample_subtasks
        )

        # Should have fallback text for missing sections
        assert "Problem statement to be extracted" in readme
        assert "Solution approach to be extracted" in readme
        assert "To be defined based on review" in readme

    def test_generate_readme_with_related_docs(self, tmp_path):
        """Test README generation with related documents."""
        report_path = tmp_path / "report.md"
        report_path.write_text("# Review Report")

        generator = ReadmeGenerator()
        related_docs = [
            {'title': 'Architecture Decision Record', 'path': '../adrs/ADR-001.md'},
            {'title': 'Research Document', 'path': '../research/auth-patterns.md'}
        ]

        readme = generator.generate_readme(
            feature_name="Test Feature",
            feature_slug="test-feature",
            review_task_id="TASK-REV-001",
            review_report_path=str(report_path),
            subtasks=[],
            related_docs=related_docs
        )

        assert "[Architecture Decision Record](../adrs/ADR-001.md)" in readme
        assert "[Research Document](../research/auth-patterns.md)" in readme


class TestGenerateFeatureReadme:
    """Integration tests for generate_feature_readme function."""

    def test_generate_and_write_readme(self, tmp_path):
        """Test complete README generation and file writing."""
        # Create review report
        report_content = dedent("""
        # Review Report: TASK-REV-INT-001

        ## Executive Summary

        Integration test review report.

        ### Key Findings

        Testing the full README generation flow.

        ## Recommendations

        1. Implement automated testing
        2. Add integration tests
        """)

        report_path = tmp_path / "review-report.md"
        report_path.write_text(report_content)

        # Define output path
        output_path = tmp_path / "feature-folder" / "README.md"

        subtasks = [
            {'id': 'TASK-001', 'title': 'Test task', 'method': 'direct', 'status': 'backlog'}
        ]

        # Generate README
        readme_content = generate_feature_readme(
            feature_name="Integration Test Feature",
            feature_slug="integration-test",
            review_task_id="TASK-REV-INT-001",
            review_report_path=str(report_path),
            subtasks=subtasks,
            output_path=str(output_path)
        )

        # Verify file was created
        assert output_path.exists()

        # Verify content was written correctly
        written_content = output_path.read_text()
        assert written_content == readme_content

        # Verify content structure
        assert "# Feature: Integration Test Feature" in written_content
        assert "TASK-001" in written_content
        assert "Testing the full README generation flow" in written_content

    def test_generate_readme_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if they don't exist."""
        report_path = tmp_path / "report.md"
        report_path.write_text("# Review")

        # Output path in non-existent nested directories
        output_path = tmp_path / "deep" / "nested" / "path" / "README.md"

        generate_feature_readme(
            feature_name="Test",
            feature_slug="test",
            review_task_id="TASK-001",
            review_report_path=str(report_path),
            subtasks=[],
            output_path=str(output_path)
        )

        # Verify all parent directories were created
        assert output_path.exists()
        assert output_path.parent.exists()
        assert (tmp_path / "deep" / "nested" / "path").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
