"""
Integration Tests for Task-Work Security Scan (Phase 4.3) - TASK-SEC-005.

Tests for the revised architecture where:
- Quick security scan runs in **task-work** (Phase 4.3) after tests pass
- SecurityChecker.run_quick_checks() is used for quick validation
- Critical findings block task progression
- Results are written to task_work_results.json

Test Categories:
- Quick scan runs after tests
- Critical finding blocks progression
- Results written to task_work_results
- Integration with phase 4.3 workflow
"""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from guardkit.orchestrator.security_config import SecurityConfig, SecurityLevel
from guardkit.orchestrator.quality_gates.security_checker import (
    SecurityChecker,
    SecurityFinding,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_worktree(tmp_path):
    """Create a temporary worktree structure for testing."""
    worktree = tmp_path / "test_worktree"
    worktree.mkdir()
    (worktree / "src").mkdir()
    (worktree / "tests").mkdir()
    (worktree / ".github" / "workflows").mkdir(parents=True)
    return worktree


@pytest.fixture
def vulnerable_worktree(temp_worktree):
    """Create a worktree with vulnerable code."""
    # Critical: Hardcoded secret
    config_file = temp_worktree / "src" / "config.py"
    config_file.write_text('API_KEY = "sk-secret-key-12345"\n')

    # High: Debug mode
    settings_file = temp_worktree / "src" / "settings.py"
    settings_file.write_text("DEBUG = True\n")

    return temp_worktree


@pytest.fixture
def clean_worktree(temp_worktree):
    """Create a worktree with clean code."""
    config_file = temp_worktree / "src" / "config.py"
    config_file.write_text('import os\nAPI_KEY = os.environ.get("API_KEY")\n')

    settings_file = temp_worktree / "src" / "settings.py"
    settings_file.write_text('import os\nDEBUG = os.environ.get("DEBUG", "false").lower() == "true"\n')

    return temp_worktree


# ============================================================================
# Quick Scan Execution Tests
# ============================================================================


class TestQuickScanExecution:
    """Test SecurityChecker quick scan execution."""

    def test_quick_scan_runs_on_worktree(self, temp_worktree):
        """Quick security scan should run on worktree."""
        checker = SecurityChecker(temp_worktree)

        findings = checker.run_quick_checks()

        assert isinstance(findings, list)

    def test_quick_scan_detects_vulnerabilities(self, vulnerable_worktree):
        """Quick scan should detect security vulnerabilities."""
        checker = SecurityChecker(vulnerable_worktree)

        findings = checker.run_quick_checks()

        assert len(findings) > 0

    def test_quick_scan_returns_finding_objects(self, vulnerable_worktree):
        """Quick scan should return SecurityFinding objects."""
        checker = SecurityChecker(vulnerable_worktree)

        findings = checker.run_quick_checks()

        assert all(isinstance(f, SecurityFinding) for f in findings)

    def test_quick_scan_returns_empty_for_clean_code(self, clean_worktree):
        """Quick scan should return empty list for clean code."""
        checker = SecurityChecker(clean_worktree)

        findings = checker.run_quick_checks()

        assert len(findings) == 0


# ============================================================================
# Critical Finding Detection Tests
# ============================================================================


class TestCriticalFindingDetection:
    """Test critical finding detection and blocking."""

    def test_detects_critical_hardcoded_secrets(self, vulnerable_worktree):
        """Quick scan should detect critical hardcoded secrets."""
        checker = SecurityChecker(vulnerable_worktree)

        findings = checker.run_quick_checks()

        critical = [f for f in findings if f.severity == "critical"]
        assert len(critical) >= 1

    def test_critical_findings_include_check_id(self, vulnerable_worktree):
        """Critical findings should include check_id."""
        checker = SecurityChecker(vulnerable_worktree)

        findings = checker.run_quick_checks()

        critical = [f for f in findings if f.severity == "critical"]
        for finding in critical:
            assert finding.check_id is not None
            assert len(finding.check_id) > 0

    def test_critical_findings_include_file_info(self, vulnerable_worktree):
        """Critical findings should include file path and line number."""
        checker = SecurityChecker(vulnerable_worktree)

        findings = checker.run_quick_checks()

        critical = [f for f in findings if f.severity == "critical"]
        for finding in critical:
            assert finding.file_path is not None
            assert finding.line_number > 0


# ============================================================================
# Task-Work Phase 4.3 Integration Tests
# ============================================================================


class TestTaskWorkPhase43:
    """Test Phase 4.3 security scan integration."""

    def test_security_scan_after_tests_pass(self, clean_worktree):
        """Security scan should run after tests pass."""
        # Simulate Phase 4.3: Run security scan after tests
        tests_passed = True

        if tests_passed:
            checker = SecurityChecker(clean_worktree)
            findings = checker.run_quick_checks()

        assert isinstance(findings, list)

    def test_critical_finding_blocks_task(self, vulnerable_worktree):
        """Critical finding should result in blocked status."""
        checker = SecurityChecker(vulnerable_worktree)

        findings = checker.run_quick_checks()
        critical_count = sum(1 for f in findings if f.severity == "critical")

        # Task should be blocked if critical findings exist
        should_block = critical_count > 0
        assert should_block is True

    def test_clean_code_allows_progression(self, clean_worktree):
        """Clean code should allow task progression."""
        checker = SecurityChecker(clean_worktree)

        findings = checker.run_quick_checks()
        critical_count = sum(1 for f in findings if f.severity == "critical")

        # Task should not be blocked with clean code
        should_block = critical_count > 0
        assert should_block is False


# ============================================================================
# Task Work Results Integration Tests
# ============================================================================


class TestTaskWorkResults:
    """Test security results written to task_work_results format."""

    def test_security_results_format(self, vulnerable_worktree):
        """Security results should be in correct format for task_work_results."""
        checker = SecurityChecker(vulnerable_worktree)

        findings = checker.run_quick_checks()

        # Format results as would be in task_work_results.json
        security_results = {
            "quick_check_passed": all(f.severity != "critical" for f in findings),
            "findings_count": len(findings),
            "critical_count": sum(1 for f in findings if f.severity == "critical"),
            "high_count": sum(1 for f in findings if f.severity == "high"),
            "findings": [
                {
                    "check_id": f.check_id,
                    "severity": f.severity,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                }
                for f in findings
            ],
        }

        assert "quick_check_passed" in security_results
        assert "findings_count" in security_results
        assert "critical_count" in security_results
        assert isinstance(security_results["findings"], list)

    def test_security_results_serializable(self, vulnerable_worktree):
        """Security results should be JSON serializable."""
        checker = SecurityChecker(vulnerable_worktree)

        findings = checker.run_quick_checks()

        security_results = {
            "quick_check_passed": all(f.severity != "critical" for f in findings),
            "findings_count": len(findings),
            "critical_count": sum(1 for f in findings if f.severity == "critical"),
        }

        # Should not raise
        json_str = json.dumps(security_results)
        assert isinstance(json_str, str)

    def test_task_work_results_integration(self, vulnerable_worktree):
        """Test integration with task_work_results.json structure."""
        checker = SecurityChecker(vulnerable_worktree)

        findings = checker.run_quick_checks()

        # Simulate task_work_results.json structure
        task_work_results = {
            "task_id": "TASK-001",
            "status": "IN_PROGRESS",
            "phases": {
                "phase_4_3": {
                    "name": "Security Quick Scan",
                    "status": "completed",
                    "security": {
                        "quick_check_passed": all(
                            f.severity != "critical" for f in findings
                        ),
                        "findings_count": len(findings),
                        "critical_count": sum(
                            1 for f in findings if f.severity == "critical"
                        ),
                    },
                }
            },
        }

        assert task_work_results["phases"]["phase_4_3"]["security"]["findings_count"] > 0


# ============================================================================
# Performance Tests
# ============================================================================


class TestQuickScanPerformance:
    """Test quick scan performance requirements."""

    def test_quick_scan_completes_under_30_seconds(self, vulnerable_worktree):
        """Quick scan should complete in under 30 seconds."""
        checker = SecurityChecker(vulnerable_worktree)

        start = time.time()
        findings = checker.run_quick_checks()
        elapsed = time.time() - start

        assert elapsed < 30.0, f"Quick scan took {elapsed:.2f}s, should be < 30s"

    def test_empty_worktree_completes_quickly(self, temp_worktree):
        """Empty worktree should complete very quickly."""
        checker = SecurityChecker(temp_worktree)

        start = time.time()
        findings = checker.run_quick_checks()
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Empty worktree check took {elapsed:.2f}s"


# ============================================================================
# Edge Cases
# ============================================================================


class TestTaskWorkSecurityEdgeCases:
    """Test edge cases in task-work security integration."""

    def test_handles_missing_src_directory(self, temp_worktree):
        """Should handle worktree without src directory."""
        # Remove src directory
        import shutil

        src_dir = temp_worktree / "src"
        if src_dir.exists():
            shutil.rmtree(src_dir)

        checker = SecurityChecker(temp_worktree)

        findings = checker.run_quick_checks()

        assert isinstance(findings, list)

    def test_handles_empty_files(self, temp_worktree):
        """Should handle empty source files."""
        empty_file = temp_worktree / "src" / "empty.py"
        empty_file.write_text("")

        checker = SecurityChecker(temp_worktree)

        findings = checker.run_quick_checks()

        assert isinstance(findings, list)

    def test_handles_large_files(self, temp_worktree):
        """Should handle large source files."""
        large_content = "x = 1\n" * 10000  # 10k lines
        large_file = temp_worktree / "src" / "large.py"
        large_file.write_text(large_content)

        checker = SecurityChecker(temp_worktree)

        start = time.time()
        findings = checker.run_quick_checks()
        elapsed = time.time() - start

        assert elapsed < 10.0, f"Large file check took {elapsed:.2f}s"
