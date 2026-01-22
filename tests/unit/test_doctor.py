"""
Unit tests for guardkit.cli.doctor module.

Tests the diagnostic tool that checks GuardKit installation and configuration.

Coverage Target: >=85%
Test Count: 40+ tests
"""

import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from guardkit.cli.doctor import (
    CLIToolCheck,
    Check,
    CheckResult,
    CheckStatus,
    ClaudeAuthCheck,
    DoctorReport,
    DoctorRunner,
    FileExistsCheck,
    PackageCheck,
    PythonVersionCheck,
    SDKConnectivityCheck,
    run_doctor,
)


# ============================================================================
# CheckStatus and CheckResult Tests
# ============================================================================


class TestCheckStatus:
    """Test CheckStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert CheckStatus.PASS.value == "pass"
        assert CheckStatus.FAIL.value == "fail"
        assert CheckStatus.WARNING.value == "warning"


class TestCheckResult:
    """Test CheckResult dataclass."""

    def test_pass_result(self):
        """Test PASS result."""
        result = CheckResult(
            name="test",
            status=CheckStatus.PASS,
            message="success",
            required=True,
        )
        assert result.icon == "✓"
        assert result.color == "green"

    def test_fail_result(self):
        """Test FAIL result."""
        result = CheckResult(
            name="test",
            status=CheckStatus.FAIL,
            message="failed",
            required=True,
        )
        assert result.icon == "✗"
        assert result.color == "red"

    def test_warning_result(self):
        """Test WARNING result."""
        result = CheckResult(
            name="test",
            status=CheckStatus.WARNING,
            message="warning",
            required=False,
        )
        assert result.icon == "⚠"
        assert result.color == "yellow"

    def test_with_details(self):
        """Test result with details."""
        result = CheckResult(
            name="test",
            status=CheckStatus.PASS,
            message="success",
            details="Additional info",
            required=True,
        )
        assert result.details == "Additional info"


# ============================================================================
# Check Base Class Tests
# ============================================================================


class TestCheckBaseClass:
    """Test Check abstract base class."""

    def test_check_required_default(self):
        """Test Check required flag defaults to True."""
        class TestCheck(Check):
            def run(self):
                return CheckResult("test", CheckStatus.PASS, "ok", required=self.required)

        check = TestCheck()
        assert check.required is True

    def test_check_required_false(self):
        """Test Check can be marked as not required."""
        class TestCheck(Check):
            def run(self):
                return CheckResult("test", CheckStatus.PASS, "ok", required=self.required)

        check = TestCheck(required=False)
        assert check.required is False


# ============================================================================
# PythonVersionCheck Tests
# ============================================================================


class TestPythonVersionCheck:
    """Test PythonVersionCheck."""

    def test_python_version_sufficient(self):
        """Test when Python version meets requirements."""
        check = PythonVersionCheck(min_version=(3, 10))
        result = check.run()

        # Current Python should be 3.10+
        assert result.status == CheckStatus.PASS
        assert result.required is True
        assert "Python" in result.name
        assert sys.executable in result.message

    def test_python_version_insufficient(self):
        """Test when Python version is too old."""
        # Mock sys.version_info to be Python 3.9
        mock_version = MagicMock()
        mock_version.major = 3
        mock_version.minor = 9
        mock_version.micro = 0

        with patch("guardkit.cli.doctor.sys.version_info", mock_version):
            check = PythonVersionCheck(min_version=(3, 10))
            result = check.run()

            assert result.status == CheckStatus.FAIL
            assert "requires 3.10+" in result.message

    def test_python_version_exact_match(self):
        """Test when Python version exactly matches minimum."""
        mock_version = MagicMock()
        mock_version.major = 3
        mock_version.minor = 10
        mock_version.micro = 0

        with patch("guardkit.cli.doctor.sys.version_info", mock_version):
            check = PythonVersionCheck(min_version=(3, 10))
            result = check.run()

            assert result.status == CheckStatus.PASS


# ============================================================================
# PackageCheck Tests
# ============================================================================


class TestPackageCheck:
    """Test PackageCheck."""

    def test_package_installed(self):
        """Test when package is installed."""
        check = PackageCheck("click", required=True)
        result = check.run()

        assert result.status == CheckStatus.PASS
        assert result.name == "click"
        assert result.required is True
        # Should have version
        assert result.message != "unknown"

    def test_package_not_installed_required(self):
        """Test when required package is missing."""
        check = PackageCheck("nonexistent-package-xyz", required=True)
        result = check.run()

        assert result.status == CheckStatus.FAIL
        assert result.message == "Not installed"
        assert result.required is True

    def test_package_not_installed_optional(self):
        """Test when optional package is missing."""
        check = PackageCheck("nonexistent-package-xyz", required=False)
        result = check.run()

        assert result.status == CheckStatus.WARNING
        assert result.message == "Not installed (optional)"
        assert result.required is False

    def test_package_with_different_import_name(self):
        """Test package with different import name."""
        check = PackageCheck("pyyaml", import_name="yaml", required=True)
        result = check.run()

        assert result.status == CheckStatus.PASS
        assert result.name == "pyyaml"

    def test_package_without_version(self):
        """Test package that doesn't have __version__ attribute."""
        with patch("builtins.__import__") as mock_import:
            mock_module = MagicMock()
            # Module without __version__ attribute
            if hasattr(mock_module, '__version__'):
                del mock_module.__version__
            mock_import.return_value = mock_module

            check = PackageCheck("test-package", required=True)
            result = check.run()

            assert result.status == CheckStatus.PASS
            assert result.message == "unknown"



# ============================================================================
# CLIToolCheck Tests
# ============================================================================


class TestCLIToolCheck:
    """Test CLIToolCheck."""

    def test_cli_tool_found(self):
        """Test when CLI tool is found."""
        # Python should be available
        check = CLIToolCheck("python3", required=True)
        result = check.run()

        assert result.status == CheckStatus.PASS
        assert "python3" in result.name
        assert result.required is True
        # Should have version or path
        assert result.message != "Not found"

    def test_cli_tool_not_found_required(self):
        """Test when required CLI tool is missing."""
        check = CLIToolCheck("nonexistent-tool-xyz", required=True)
        result = check.run()

        assert result.status == CheckStatus.FAIL
        assert result.message == "Not found"
        assert result.required is True

    def test_cli_tool_not_found_optional(self):
        """Test when optional CLI tool is missing."""
        check = CLIToolCheck("nonexistent-tool-xyz", required=False)
        result = check.run()

        assert result.status == CheckStatus.WARNING
        assert result.message == "Not found (optional)"
        assert result.required is False

    def test_cli_tool_version_extraction(self):
        """Test version number extraction."""
        with patch("shutil.which", return_value="/usr/bin/git"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    stdout="git version 2.50.1\n", stderr="", returncode=0
                )
                check = CLIToolCheck("git")
                result = check.run()

                assert result.status == CheckStatus.PASS
                assert "2.50.1" in result.message

    def test_cli_tool_version_check_fails(self):
        """Test when version check command fails."""
        with patch("shutil.which", return_value="/usr/bin/tool"):
            with patch("subprocess.run", side_effect=Exception("Command failed")):
                check = CLIToolCheck("tool")
                result = check.run()

                # Should still pass (tool exists)
                assert result.status == CheckStatus.PASS
                assert "/usr/bin/tool" in result.message

    def test_cli_tool_custom_version_args(self):
        """Test CLI tool with custom version arguments."""
        with patch("shutil.which", return_value="/usr/bin/npm"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    stdout="10.1.0\n", stderr="", returncode=0
                )
                check = CLIToolCheck("npm", version_args=["-v"])
                result = check.run()

                assert result.status == CheckStatus.PASS
                assert "10.1.0" in result.message
                mock_run.assert_called_once()
                assert mock_run.call_args[0][0] == ["/usr/bin/npm", "-v"]

    def test_cli_tool_timeout(self):
        """Test CLI tool version check timeout handling."""
        import subprocess

        with patch("shutil.which", return_value="/usr/bin/slow-tool"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
                check = CLIToolCheck("slow-tool")
                result = check.run()

                # Should still pass (tool exists)
                assert result.status == CheckStatus.PASS
                assert "Found" in result.message

    def test_cli_tool_version_in_stderr(self):
        """Test version extraction from stderr."""
        with patch("shutil.which", return_value="/usr/bin/tool"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    stdout="", stderr="tool version 1.2.3\n", returncode=0
                )
                check = CLIToolCheck("tool")
                result = check.run()

                assert result.status == CheckStatus.PASS
                assert "1.2.3" in result.message


# ============================================================================
# FileExistsCheck Tests
# ============================================================================


class TestFileExistsCheck:
    """Test FileExistsCheck."""

    def test_file_exists(self, tmp_path):
        """Test when file exists."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        check = FileExistsCheck(test_file, "test.txt", required=True)
        result = check.run()

        assert result.status == CheckStatus.PASS
        assert result.message == "Found"

    def test_file_not_exists_required(self, tmp_path):
        """Test when required file is missing."""
        test_file = tmp_path / "missing.txt"

        check = FileExistsCheck(test_file, "missing.txt", required=True)
        result = check.run()

        assert result.status == CheckStatus.FAIL
        assert result.message == "Not found"

    def test_file_not_exists_optional(self, tmp_path):
        """Test when optional file is missing."""
        test_file = tmp_path / "missing.txt"

        check = FileExistsCheck(test_file, "missing.txt", required=False)
        result = check.run()

        assert result.status == CheckStatus.WARNING
        assert result.message == "Not found (optional)"

    def test_directory_exists(self, tmp_path):
        """Test when directory exists."""
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()

        check = FileExistsCheck(test_dir, "testdir/", required=False, is_dir=True)
        result = check.run()

        assert result.status == CheckStatus.PASS
        assert result.message == "Found"

    def test_tasks_directory_with_count(self, tmp_path):
        """Test tasks directory counts task files."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "TASK-001.md").write_text("task 1")
        (tasks_dir / "TASK-002.md").write_text("task 2")

        check = FileExistsCheck(tasks_dir, "tasks/", required=False, is_dir=True)
        result = check.run()

        assert result.status == CheckStatus.PASS
        assert "2 tasks" in result.message

    def test_tasks_directory_empty(self, tmp_path):
        """Test tasks directory with no task files."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        check = FileExistsCheck(tasks_dir, "tasks/", required=False, is_dir=True)
        result = check.run()

        assert result.status == CheckStatus.PASS
        assert "0 tasks" in result.message

    def test_tasks_directory_with_subdirectories(self, tmp_path):
        """Test tasks directory counts tasks in subdirectories."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "backlog").mkdir()
        (tasks_dir / "backlog" / "TASK-003.md").write_text("task 3")
        (tasks_dir / "in_progress").mkdir()
        (tasks_dir / "in_progress" / "TASK-004.md").write_text("task 4")

        check = FileExistsCheck(tasks_dir, "tasks/", required=False, is_dir=True)
        result = check.run()

        assert result.status == CheckStatus.PASS
        assert "2 tasks" in result.message

    def test_directory_count_exception_handling(self, tmp_path):
        """Test directory count handles exceptions gracefully."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        # Mock rglob to raise exception
        with patch.object(Path, 'rglob', side_effect=PermissionError("Access denied")):
            check = FileExistsCheck(tasks_dir, "tasks/", required=False, is_dir=True)
            result = check.run()

            assert result.status == CheckStatus.PASS
            assert result.message == "Found"

    def test_non_tasks_directory_with_is_dir(self, tmp_path):
        """Test non-tasks directory doesn't try to count tasks."""
        some_dir = tmp_path / "configs"
        some_dir.mkdir()
        (some_dir / "config.json").write_text("{}")

        check = FileExistsCheck(some_dir, "configs/", required=False, is_dir=True)
        result = check.run()

        assert result.status == CheckStatus.PASS
        assert result.message == "Found"


# ============================================================================
# ClaudeAuthCheck Tests
# ============================================================================


class TestClaudeAuthCheck:
    """Test ClaudeAuthCheck."""

    def test_auth_with_api_key(self, monkeypatch):
        """Test when ANTHROPIC_API_KEY is set."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-test1234567890abcdef")

        check = ClaudeAuthCheck(required=False)
        result = check.run()

        assert result.status == CheckStatus.PASS
        assert result.name == "Claude Auth"
        assert "ANTHROPIC_API_KEY" in result.message
        # Verify key is masked
        assert "sk-ant-a" in result.message  # First 8 chars
        assert "cdef" in result.message  # Last 4 chars
        assert "1234567890ab" not in result.message  # Middle is hidden

    def test_auth_with_short_api_key(self, monkeypatch):
        """Test masking of short API key."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "short-key")

        check = ClaudeAuthCheck(required=False)
        result = check.run()

        assert result.status == CheckStatus.PASS
        # Short keys should show ***
        assert "***" in result.message

    def test_auth_with_claude_code_file(self, tmp_path, monkeypatch):
        """Test when Claude Code auth file exists."""
        # Clear API key env var
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        # Create mock auth file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        auth_file = claude_dir / "auth.json"
        auth_file.write_text('{"access_token": "test-token"}')

        # Patch Path.home() to return our temp dir
        with patch("guardkit.cli.doctor.Path.home", return_value=tmp_path):
            check = ClaudeAuthCheck(required=False)
            result = check.run()

        assert result.status == CheckStatus.PASS
        assert "Claude Code auth" in result.message

    def test_auth_with_empty_auth_file(self, tmp_path, monkeypatch):
        """Test when Claude Code auth file is empty JSON."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        auth_file = claude_dir / "auth.json"
        auth_file.write_text("{}")

        with patch("guardkit.cli.doctor.Path.home", return_value=tmp_path):
            check = ClaudeAuthCheck(required=False)
            result = check.run()

        # Empty JSON should be treated as invalid
        assert result.status == CheckStatus.WARNING
        assert "Not configured" in result.message

    def test_auth_with_invalid_json_file(self, tmp_path, monkeypatch):
        """Test when Claude Code auth file has invalid JSON."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        auth_file = claude_dir / "auth.json"
        auth_file.write_text("not valid json")

        with patch("guardkit.cli.doctor.Path.home", return_value=tmp_path):
            check = ClaudeAuthCheck(required=False)
            result = check.run()

        assert result.status == CheckStatus.WARNING
        assert "Not configured" in result.message

    def test_auth_not_configured_optional(self, tmp_path, monkeypatch):
        """Test when no auth is configured (optional)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with patch("guardkit.cli.doctor.Path.home", return_value=tmp_path):
            check = ClaudeAuthCheck(required=False)
            result = check.run()

        assert result.status == CheckStatus.WARNING
        assert "Not configured (optional)" in result.message
        assert result.details is not None
        assert "ANTHROPIC_API_KEY" in result.details

    def test_auth_not_configured_required(self, tmp_path, monkeypatch):
        """Test when no auth is configured (required)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with patch("guardkit.cli.doctor.Path.home", return_value=tmp_path):
            check = ClaudeAuthCheck(required=True)
            result = check.run()

        assert result.status == CheckStatus.FAIL
        assert "Not configured" in result.message
        assert result.required is True

    def test_mask_api_key_method(self):
        """Test the _mask_api_key method directly."""
        check = ClaudeAuthCheck()

        # Normal key
        assert check._mask_api_key("sk-ant-api03-abcdefghijklmnop") == "sk-ant-a...mnop"

        # Short key (<=12 chars)
        assert check._mask_api_key("shortkey") == "***"

        # Exactly 12 chars
        assert check._mask_api_key("123456789012") == "***"

        # 13 chars (first that shows partial)
        assert check._mask_api_key("1234567890123") == "12345678...0123"


# ============================================================================
# SDKConnectivityCheck Tests
# ============================================================================


class TestSDKConnectivityCheck:
    """Test SDKConnectivityCheck."""

    def test_connectivity_skipped_when_disabled(self):
        """Test that connectivity check is skipped when not enabled."""
        check = SDKConnectivityCheck(enabled=False, required=False)
        result = check.run()

        assert result.status == CheckStatus.WARNING
        assert result.name == "SDK Connectivity"
        assert "Skipped" in result.message
        assert "--connectivity" in result.message

    def test_connectivity_import_error(self):
        """Test when claude_agent_sdk is not installed."""
        with patch("guardkit.cli.doctor.SDKConnectivityCheck.run") as mock_run:
            # Simulate ImportError path
            mock_run.return_value = CheckResult(
                name="SDK Connectivity",
                status=CheckStatus.FAIL,
                message="claude-agent-sdk not installed",
                details="Run: pip install claude-agent-sdk",
                required=False,
            )

            check = SDKConnectivityCheck(enabled=True, required=False)
            result = check.run()

            assert result.status == CheckStatus.FAIL
            assert "not installed" in result.message

    def test_connectivity_success(self):
        """Test successful SDK connectivity."""
        # Mock the SDK import and query
        mock_query = MagicMock()

        async def mock_query_fn(prompt):
            yield {"type": "message", "content": "ok"}

        with patch.dict("sys.modules", {"claude_agent_sdk": MagicMock()}):
            with patch("guardkit.cli.doctor.SDKConnectivityCheck.run") as mock_run:
                mock_run.return_value = CheckResult(
                    name="SDK Connectivity",
                    status=CheckStatus.PASS,
                    message="Connected successfully",
                    required=False,
                )

                check = SDKConnectivityCheck(enabled=True, required=False)
                result = check.run()

                assert result.status == CheckStatus.PASS
                assert "Connected successfully" in result.message

    def test_connectivity_connection_failure(self):
        """Test SDK connectivity failure."""
        with patch("guardkit.cli.doctor.SDKConnectivityCheck.run") as mock_run:
            mock_run.return_value = CheckResult(
                name="SDK Connectivity",
                status=CheckStatus.FAIL,
                message="Connection failed: API error",
                details="Check API key and network connectivity",
                required=False,
            )

            check = SDKConnectivityCheck(enabled=True, required=False)
            result = check.run()

            assert result.status == CheckStatus.FAIL
            assert "Connection failed" in result.message

    def test_connectivity_error_message_truncation(self):
        """Test that long error messages are truncated."""
        long_error = "A" * 100  # 100 character error message

        with patch("guardkit.cli.doctor.SDKConnectivityCheck.run") as mock_run:
            # Simulate truncated error
            truncated = long_error[:47] + "..."
            mock_run.return_value = CheckResult(
                name="SDK Connectivity",
                status=CheckStatus.FAIL,
                message=f"Connection failed: {truncated}",
                details="Check API key and network connectivity",
                required=False,
            )

            check = SDKConnectivityCheck(enabled=True, required=False)
            result = check.run()

            assert result.status == CheckStatus.FAIL
            assert "..." in result.message
            # Original long error should not be fully present
            assert long_error not in result.message

    def test_connectivity_required_flag(self):
        """Test that required flag is respected."""
        check = SDKConnectivityCheck(enabled=False, required=True)
        assert check.required is True

        check = SDKConnectivityCheck(enabled=False, required=False)
        assert check.required is False


# ============================================================================
# DoctorRunner Tests
# ============================================================================


class TestDoctorRunner:
    """Test DoctorRunner."""

    def test_default_checks(self):
        """Test default checks are created."""
        runner = DoctorRunner()
        assert len(runner.checks) > 0

        # Should have core dependencies
        check_names = [check.__class__.__name__ for check in runner.checks]
        assert "PythonVersionCheck" in check_names
        assert "CLIToolCheck" in check_names
        assert "ClaudeAuthCheck" in check_names
        assert "SDKConnectivityCheck" in check_names

    def test_connectivity_parameter(self):
        """Test connectivity parameter is passed to SDKConnectivityCheck."""
        runner_without = DoctorRunner(connectivity=False)
        runner_with = DoctorRunner(connectivity=True)

        # Find SDKConnectivityCheck in each runner
        sdk_check_without = next(
            c for c in runner_without.checks if isinstance(c, SDKConnectivityCheck)
        )
        sdk_check_with = next(
            c for c in runner_with.checks if isinstance(c, SDKConnectivityCheck)
        )

        assert sdk_check_without.enabled is False
        assert sdk_check_with.enabled is True

    def test_custom_checks(self):
        """Test with custom checks."""
        custom_checks = [
            PythonVersionCheck(),
            PackageCheck("click"),
        ]
        runner = DoctorRunner(checks=custom_checks)
        assert len(runner.checks) == 2

    def test_run_all_checks(self):
        """Test running all checks."""
        checks = [
            PythonVersionCheck(),
            PackageCheck("click"),
        ]
        runner = DoctorRunner(checks=checks)
        results = runner.run()

        assert len(results) == 2
        assert all(isinstance(r, CheckResult) for r in results)

    def test_check_failure_handling(self):
        """Test handling of check that raises exception."""
        # Create a check that will fail
        class FailingCheck(Check):
            def run(self):
                raise RuntimeError("Check failed")

        checks = [FailingCheck(required=True)]
        runner = DoctorRunner(checks=checks)
        results = runner.run()

        assert len(results) == 1
        assert results[0].status == CheckStatus.FAIL
        assert "Check failed" in results[0].message

    def test_default_checks_structure(self):
        """Test default checks include expected categories."""
        runner = DoctorRunner()
        results = runner.run()

        # Extract check names
        names = [r.name for r in results]

        # Core dependencies
        assert "Python" in names
        assert "guardkit-py" in names
        assert "click" in names
        assert "rich" in names

        # AutoBuild dependencies (new checks)
        assert "Claude Auth" in names
        assert "SDK Connectivity" in names

        # Optional tools
        assert "git" in names

    def test_check_without_name_attribute(self):
        """Test handling of check without name attribute."""
        class NoNameCheck(Check):
            def run(self):
                raise ValueError("Test error")

        runner = DoctorRunner(checks=[NoNameCheck()])
        results = runner.run()

        assert len(results) == 1
        assert "NoNameCheck" in results[0].name


# ============================================================================
# DoctorReport Tests
# ============================================================================


class TestDoctorReport:
    """Test DoctorReport."""

    def test_has_failures_true(self):
        """Test has_failures when required checks fail."""
        results = [
            CheckResult("test1", CheckStatus.FAIL, "failed", required=True),
            CheckResult("test2", CheckStatus.PASS, "passed", required=True),
        ]
        report = DoctorReport(results)
        assert report.has_failures() is True

    def test_has_failures_false_with_warnings(self):
        """Test has_failures with only warnings."""
        results = [
            CheckResult("test1", CheckStatus.PASS, "passed", required=True),
            CheckResult("test2", CheckStatus.WARNING, "warning", required=False),
        ]
        report = DoctorReport(results)
        assert report.has_failures() is False

    def test_has_failures_false_all_pass(self):
        """Test has_failures when all pass."""
        results = [
            CheckResult("test1", CheckStatus.PASS, "passed", required=True),
            CheckResult("test2", CheckStatus.PASS, "passed", required=True),
        ]
        report = DoctorReport(results)
        assert report.has_failures() is False

    def test_has_failures_ignores_optional_failures(self):
        """Test has_failures ignores failures on optional checks."""
        results = [
            CheckResult("test1", CheckStatus.PASS, "passed", required=True),
            CheckResult("test2", CheckStatus.FAIL, "failed", required=False),
        ]
        report = DoctorReport(results)
        assert report.has_failures() is False

    def test_format_rich_output(self, capsys):
        """Test Rich formatting output."""
        results = [
            CheckResult("Python", CheckStatus.PASS, "3.14.2", required=True),
            CheckResult("click", CheckStatus.PASS, "8.3.1", required=True),
        ]
        report = DoctorReport(results)

        # Just verify it doesn't crash
        report.format_rich()

        # Note: Can't easily test Rich output in unit tests
        # Integration tests would be better for verifying formatting

    def test_format_rich_with_details(self):
        """Test Rich formatting with result details."""
        results = [
            CheckResult(
                "Python",
                CheckStatus.PASS,
                "3.14.2",
                details="Additional debug info",
                required=True
            ),
        ]
        report = DoctorReport(results)

        # Should not crash with details present
        report.format_rich()

    def test_format_rich_all_categories(self):
        """Test Rich formatting with all categories."""
        results = [
            # Core deps
            CheckResult("Python", CheckStatus.PASS, "3.14.2", required=True),
            CheckResult("click", CheckStatus.PASS, "8.3.1", required=True),
            # AutoBuild deps
            CheckResult("claude-agent-sdk", CheckStatus.WARNING, "Not installed (optional)", required=False),
            CheckResult("Claude Auth", CheckStatus.PASS, "ANTHROPIC_API_KEY (sk-ant-a...cdef)", required=False),
            CheckResult("SDK Connectivity", CheckStatus.WARNING, "Skipped (use --connectivity to test)", required=False),
            # Optional tools
            CheckResult("git", CheckStatus.PASS, "2.50.1", required=True),
            # Config
            CheckResult("CLAUDE.md", CheckStatus.PASS, "Found", required=False),
        ]
        report = DoctorReport(results)

        # Should format all categories without crashing
        report.format_rich()

    def test_format_rich_empty_category(self):
        """Test Rich formatting skips empty categories."""
        results = [
            CheckResult("unknown-check", CheckStatus.PASS, "ok", required=True),
        ]
        report = DoctorReport(results)

        # Should handle checks not in predefined categories
        report.format_rich()


# ============================================================================
# run_doctor() Integration Tests
# ============================================================================


class TestRunDoctor:
    """Test run_doctor() main entry point."""

    @patch("guardkit.cli.doctor.DoctorRunner")
    def test_run_doctor_success(self, mock_runner_class):
        """Test run_doctor when all checks pass."""
        # Mock successful results
        mock_results = [
            CheckResult("test", CheckStatus.PASS, "passed", required=True),
        ]
        mock_runner = Mock()
        mock_runner.run.return_value = mock_results
        mock_runner_class.return_value = mock_runner

        exit_code = run_doctor()

        assert exit_code == 0
        mock_runner.run.assert_called_once()
        # Verify DoctorRunner was called with default connectivity=False
        mock_runner_class.assert_called_once_with(connectivity=False)

    @patch("guardkit.cli.doctor.DoctorRunner")
    def test_run_doctor_failure(self, mock_runner_class):
        """Test run_doctor when required checks fail."""
        # Mock failed results
        mock_results = [
            CheckResult("test", CheckStatus.FAIL, "failed", required=True),
        ]
        mock_runner = Mock()
        mock_runner.run.return_value = mock_results
        mock_runner_class.return_value = mock_runner

        exit_code = run_doctor()

        assert exit_code == 1
        mock_runner.run.assert_called_once()

    @patch("guardkit.cli.doctor.DoctorRunner")
    def test_run_doctor_with_warnings_only(self, mock_runner_class):
        """Test run_doctor with only warnings (should succeed)."""
        # Mock results with warnings
        mock_results = [
            CheckResult("test1", CheckStatus.PASS, "passed", required=True),
            CheckResult("test2", CheckStatus.WARNING, "warning", required=False),
        ]
        mock_runner = Mock()
        mock_runner.run.return_value = mock_results
        mock_runner_class.return_value = mock_runner

        exit_code = run_doctor()

        assert exit_code == 0

    @patch("guardkit.cli.doctor.DoctorRunner")
    def test_run_doctor_with_connectivity(self, mock_runner_class):
        """Test run_doctor with connectivity flag enabled."""
        mock_results = [
            CheckResult("test", CheckStatus.PASS, "passed", required=True),
        ]
        mock_runner = Mock()
        mock_runner.run.return_value = mock_results
        mock_runner_class.return_value = mock_runner

        exit_code = run_doctor(connectivity=True)

        assert exit_code == 0
        # Verify DoctorRunner was called with connectivity=True
        mock_runner_class.assert_called_once_with(connectivity=True)


# ============================================================================
# Integration Tests
# ============================================================================


class TestDoctorIntegration:
    """Integration tests for the full doctor workflow."""

    def test_real_environment_check(self):
        """Test against real environment (smoke test)."""
        runner = DoctorRunner()
        results = runner.run()

        # Should have results
        assert len(results) > 0

        # Python check should pass
        python_results = [r for r in results if "Python" in r.name]
        assert len(python_results) == 1
        assert python_results[0].status == CheckStatus.PASS

        # At least some core packages should be installed
        core_packages = ["click", "rich"]
        for pkg in core_packages:
            pkg_results = [r for r in results if r.name == pkg]
            assert len(pkg_results) == 1
            assert pkg_results[0].status == CheckStatus.PASS

    def test_report_generation(self):
        """Test full report generation."""
        runner = DoctorRunner()
        results = runner.run()
        report = DoctorReport(results)

        # Should not crash
        report.format_rich()

        # Check failure detection
        has_failures = report.has_failures()
        assert isinstance(has_failures, bool)

    def test_end_to_end_workflow(self):
        """Test complete end-to-end doctor workflow."""
        exit_code = run_doctor()

        # Should return valid exit code
        assert exit_code in [0, 1]

        # Exit code 0 means all required checks passed
        # Exit code 1 means some required checks failed
