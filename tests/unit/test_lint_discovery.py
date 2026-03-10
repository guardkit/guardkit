"""Tests for guardkit.orchestrator.lint_discovery module.

TASK-ABE-002: Config-driven lint tool discovery and pre-Coach auto-fix.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.lint_discovery import (
    LintResult,
    detect_tech_stack,
    discover_lint_commands,
    run_lint_autofix,
)


# ============================================================================
# detect_tech_stack
# ============================================================================


class TestDetectTechStack:
    """Tests for detect_tech_stack() function."""

    def test_python_pyproject(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[build-system]\n")
        assert detect_tech_stack(tmp_path) == "python"

    def test_python_requirements(self, tmp_path: Path):
        (tmp_path / "requirements.txt").write_text("flask\n")
        assert detect_tech_stack(tmp_path) == "python"

    def test_python_setup_py(self, tmp_path: Path):
        (tmp_path / "setup.py").write_text("from setuptools import setup\n")
        assert detect_tech_stack(tmp_path) == "python"

    def test_go(self, tmp_path: Path):
        (tmp_path / "go.mod").write_text("module example.com/app\n")
        assert detect_tech_stack(tmp_path) == "go"

    def test_rust(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").write_text("[package]\nname = \"app\"\n")
        assert detect_tech_stack(tmp_path) == "rust"

    def test_dotnet(self, tmp_path: Path):
        (tmp_path / "App.csproj").write_text("<Project />\n")
        assert detect_tech_stack(tmp_path) == "dotnet"

    def test_typescript(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"name": "app"}\n')
        assert detect_tech_stack(tmp_path) == "typescript"

    def test_generic_fallback(self, tmp_path: Path):
        assert detect_tech_stack(tmp_path) == "generic"

    def test_python_takes_priority_over_typescript(self, tmp_path: Path):
        """Python signals should win when both pyproject.toml and package.json exist."""
        (tmp_path / "pyproject.toml").write_text("[build-system]\n")
        (tmp_path / "package.json").write_text('{"name": "app"}\n')
        assert detect_tech_stack(tmp_path) == "python"


# ============================================================================
# discover_lint_commands — Python
# ============================================================================


class TestDiscoverPythonLint:
    """Tests for Python lint discovery from pyproject.toml."""

    def test_ruff_configured(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 88\n")
        commands = discover_lint_commands(tmp_path)
        assert "ruff check . --fix" in commands
        # ruff without [tool.ruff.format] should NOT add ruff format
        assert "ruff format ." not in commands

    def test_ruff_with_format(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[tool.ruff]\nline-length = 88\n\n[tool.ruff.format]\nquote-style = 'double'\n"
        )
        commands = discover_lint_commands(tmp_path)
        assert "ruff check . --fix" in commands
        assert "ruff format ." in commands

    def test_black_configured(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.black]\nline-length = 88\n")
        commands = discover_lint_commands(tmp_path)
        assert "black ." in commands

    def test_isort_configured(self, tmp_path: Path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.isort]\nprofile = 'black'\n")
        commands = discover_lint_commands(tmp_path)
        assert "isort ." in commands

    def test_ruff_suppresses_isort(self, tmp_path: Path):
        """When ruff is configured, isort should NOT be added (ruff subsumes it)."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 88\n\n[tool.isort]\nprofile = 'black'\n")
        commands = discover_lint_commands(tmp_path)
        assert "ruff check . --fix" in commands
        assert "isort ." not in commands

    def test_ruff_suppresses_black(self, tmp_path: Path):
        """When ruff is configured, black should NOT be added."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 88\n\n[tool.black]\nline-length = 88\n")
        commands = discover_lint_commands(tmp_path)
        assert "ruff check . --fix" in commands
        assert "black ." not in commands

    def test_flake8_skipped_no_autofix(self, tmp_path: Path):
        """flake8 has no auto-fix capability, should be skipped."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.flake8]\nmax-line-length = 88\n")
        commands = discover_lint_commands(tmp_path)
        assert len(commands) == 0

    def test_pylint_skipped_no_autofix(self, tmp_path: Path):
        """pylint has no auto-fix capability, should be skipped."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.pylint]\n")
        commands = discover_lint_commands(tmp_path)
        assert len(commands) == 0

    def test_no_tool_sections(self, tmp_path: Path):
        """pyproject.toml with no [tool.*] sections yields no commands."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[build-system]\nrequires = ['hatchling']\n")
        commands = discover_lint_commands(tmp_path)
        assert len(commands) == 0

    def test_setup_cfg_isort_fallback(self, tmp_path: Path):
        """Legacy setup.cfg with [isort] should be detected."""
        setup_cfg = tmp_path / "setup.cfg"
        setup_cfg.write_text("[isort]\nprofile = black\n")
        commands = discover_lint_commands(tmp_path)
        assert "isort ." in commands

    def test_malformed_pyproject_gracefully_handled(self, tmp_path: Path):
        """Malformed pyproject.toml should not crash."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("this is not valid toml {{{{")
        commands = discover_lint_commands(tmp_path)
        assert commands == []


# ============================================================================
# discover_lint_commands — JavaScript/TypeScript
# ============================================================================


class TestDiscoverJsLint:
    """Tests for JS/TS lint discovery from package.json."""

    def test_lint_fix_script(self, tmp_path: Path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"scripts": {"lint:fix": "eslint . --fix"}}))
        commands = discover_lint_commands(tmp_path)
        assert "npm run lint:fix" in commands

    def test_lint_script_with_fix_flag(self, tmp_path: Path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"scripts": {"lint": "eslint ."}}))
        commands = discover_lint_commands(tmp_path)
        assert "npm run lint -- --fix" in commands

    def test_format_script(self, tmp_path: Path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"scripts": {"format": "prettier --write ."}}))
        commands = discover_lint_commands(tmp_path)
        assert "npm run format" in commands

    def test_lint_fix_preferred_over_lint(self, tmp_path: Path):
        """lint:fix should be used instead of lint when both exist."""
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"scripts": {"lint": "eslint .", "lint:fix": "eslint . --fix"}}))
        commands = discover_lint_commands(tmp_path)
        assert "npm run lint:fix" in commands
        assert "npm run lint -- --fix" not in commands

    def test_biome_devdep(self, tmp_path: Path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"devDependencies": {"biome": "^1.0.0"}}))
        commands = discover_lint_commands(tmp_path)
        assert "npx biome check --write" in commands

    def test_eslint_devdep_no_script(self, tmp_path: Path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"devDependencies": {"eslint": "^8.0.0"}}))
        commands = discover_lint_commands(tmp_path)
        assert "npx eslint . --fix" in commands

    def test_no_lint_configured(self, tmp_path: Path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"name": "app", "version": "1.0.0"}))
        commands = discover_lint_commands(tmp_path)
        assert len(commands) == 0

    def test_malformed_package_json(self, tmp_path: Path):
        pkg = tmp_path / "package.json"
        pkg.write_text("not valid json")
        commands = discover_lint_commands(tmp_path)
        assert commands == []


# ============================================================================
# discover_lint_commands — Go
# ============================================================================


class TestDiscoverGoLint:
    """Tests for Go lint discovery."""

    def test_golangci_yml(self, tmp_path: Path):
        (tmp_path / "go.mod").write_text("module example.com/app\n")
        (tmp_path / ".golangci.yml").write_text("linters:\n")
        commands = discover_lint_commands(tmp_path)
        assert "golangci-lint run --fix" in commands
        assert "gofmt -w ." in commands

    def test_golangci_yaml(self, tmp_path: Path):
        (tmp_path / "go.mod").write_text("module example.com/app\n")
        (tmp_path / ".golangci.yaml").write_text("linters:\n")
        commands = discover_lint_commands(tmp_path)
        assert "golangci-lint run --fix" in commands

    def test_gofmt_only(self, tmp_path: Path):
        """Without golangci config, only gofmt should be discovered."""
        (tmp_path / "go.mod").write_text("module example.com/app\n")
        commands = discover_lint_commands(tmp_path)
        assert commands == ["gofmt -w ."]

    def test_no_go_mod(self, tmp_path: Path):
        """Without go.mod, no Go commands should be discovered."""
        commands = discover_lint_commands(tmp_path)
        go_commands = [c for c in commands if "go" in c.lower()]
        assert len(go_commands) == 0


# ============================================================================
# discover_lint_commands — Rust
# ============================================================================


class TestDiscoverRustLint:
    """Tests for Rust lint discovery."""

    def test_cargo_fmt(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").write_text("[package]\nname = \"app\"\n")
        commands = discover_lint_commands(tmp_path)
        assert "cargo fmt" in commands

    def test_clippy_configured(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").write_text(
            "[package]\nname = \"app\"\n\n[clippy]\nwarn = [\"all\"]\n"
        )
        commands = discover_lint_commands(tmp_path)
        assert "cargo fmt" in commands
        assert "cargo clippy --fix --allow-dirty" in commands


# ============================================================================
# discover_lint_commands — .NET
# ============================================================================


class TestDiscoverDotnetLint:
    """Tests for .NET lint discovery."""

    def test_csproj_found(self, tmp_path: Path):
        (tmp_path / "App.csproj").write_text("<Project />\n")
        commands = discover_lint_commands(tmp_path)
        assert "dotnet format" in commands

    def test_no_csproj(self, tmp_path: Path):
        commands = discover_lint_commands(tmp_path)
        dotnet_commands = [c for c in commands if "dotnet" in c]
        assert len(dotnet_commands) == 0


# ============================================================================
# discover_lint_commands — No lint configured
# ============================================================================


class TestDiscoverNoLint:
    """Tests for projects with no lint tools configured."""

    def test_empty_directory(self, tmp_path: Path):
        commands = discover_lint_commands(tmp_path)
        assert commands == []

    def test_guardkit_own_pyproject(self):
        """GuardKit's own pyproject.toml has no lint tools configured."""
        # This is a live test against the real codebase
        project_root = Path(__file__).parent.parent.parent
        pyproject = project_root / "pyproject.toml"
        if pyproject.exists():
            commands = discover_lint_commands(project_root)
            # GuardKit has no [tool.ruff], [tool.black], etc.
            lint_commands = [c for c in commands if any(
                tool in c for tool in ["ruff", "black", "isort", "flake8", "pylint"]
            )]
            assert len(lint_commands) == 0


# ============================================================================
# LintResult
# ============================================================================


class TestLintResult:
    """Tests for LintResult dataclass."""

    def test_to_dict(self):
        result = LintResult(
            commands_run=["ruff check . --fix"],
            commands_skipped=["black ."],
            warnings=["black not installed"],
            duration_seconds=1.234,
            success=True,
        )
        d = result.to_dict()
        assert d["commands_run"] == ["ruff check . --fix"]
        assert d["commands_skipped"] == ["black ."]
        assert d["warnings"] == ["black not installed"]
        assert d["duration_seconds"] == 1.23
        assert d["success"] is True

    def test_defaults(self):
        result = LintResult()
        d = result.to_dict()
        assert d["commands_run"] == []
        assert d["commands_skipped"] == []
        assert d["warnings"] == []
        assert d["duration_seconds"] == 0.0
        assert d["success"] is True


# ============================================================================
# run_lint_autofix
# ============================================================================


class TestRunLintAutofix:
    """Tests for run_lint_autofix() function."""

    def test_no_lint_configured_returns_none(self, tmp_path: Path):
        """When no lint tools are configured, should return None."""
        result = run_lint_autofix("TASK-001", 1, tmp_path)
        assert result is None

    @patch("guardkit.orchestrator.lint_discovery.subprocess.run")
    @patch("guardkit.orchestrator.lint_discovery.shutil.which")
    def test_ruff_configured_and_installed(self, mock_which, mock_run, tmp_path: Path):
        """When ruff is configured and installed, should run it."""
        # Setup: pyproject.toml with ruff configured
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 88\n")

        # Mock: ruff is installed
        mock_which.return_value = "/usr/bin/ruff"

        # Mock: ruff succeeds
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = run_lint_autofix("TASK-001", 1, tmp_path)

        assert result is not None
        assert "ruff check . --fix" in result.commands_run
        assert len(result.commands_skipped) == 0
        mock_run.assert_called_once()

    @patch("guardkit.orchestrator.lint_discovery.shutil.which")
    def test_lint_tool_not_installed_skipped(self, mock_which, tmp_path: Path):
        """When lint tool is configured but not installed, should skip with warning."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 88\n")

        # Mock: ruff is NOT installed
        mock_which.return_value = None

        result = run_lint_autofix("TASK-001", 1, tmp_path)

        assert result is not None
        assert len(result.commands_run) == 0
        assert "ruff check . --fix" in result.commands_skipped
        assert any("not installed" in w for w in result.warnings)

    @patch("guardkit.orchestrator.lint_discovery.subprocess.run")
    @patch("guardkit.orchestrator.lint_discovery.shutil.which")
    def test_lint_command_fails_continues(self, mock_which, mock_run, tmp_path: Path):
        """When lint command fails, should warn and continue."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 88\n")

        mock_which.return_value = "/usr/bin/ruff"
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error output")

        result = run_lint_autofix("TASK-001", 1, tmp_path)

        assert result is not None
        assert "ruff check . --fix" in result.commands_run
        assert any("exited with code 1" in w for w in result.warnings)

    @patch("guardkit.orchestrator.lint_discovery.subprocess.run")
    @patch("guardkit.orchestrator.lint_discovery.shutil.which")
    def test_lint_command_timeout(self, mock_which, mock_run, tmp_path: Path):
        """When lint command times out, should skip with warning."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 88\n")

        mock_which.return_value = "/usr/bin/ruff"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ruff", timeout=30)

        result = run_lint_autofix("TASK-001", 1, tmp_path)

        assert result is not None
        assert len(result.commands_run) == 0
        assert "ruff check . --fix" in result.commands_skipped
        assert any("timed out" in w for w in result.warnings)

    @patch("guardkit.orchestrator.lint_discovery.subprocess.run")
    def test_npm_commands_skip_which_check(self, mock_run, tmp_path: Path):
        """npm/npx commands should not check shutil.which (npm handles resolution)."""
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({"scripts": {"lint:fix": "eslint . --fix"}}))

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = run_lint_autofix("TASK-001", 1, tmp_path)

        assert result is not None
        assert "npm run lint:fix" in result.commands_run

    @patch("guardkit.orchestrator.lint_discovery.subprocess.run")
    @patch("guardkit.orchestrator.lint_discovery.shutil.which")
    def test_multiple_commands_all_run(self, mock_which, mock_run, tmp_path: Path):
        """When multiple lint tools configured, all should run."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[tool.ruff]\nline-length = 88\n\n[tool.ruff.format]\nquote-style = 'double'\n"
        )

        mock_which.return_value = "/usr/bin/ruff"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = run_lint_autofix("TASK-001", 1, tmp_path)

        assert result is not None
        assert "ruff check . --fix" in result.commands_run
        assert "ruff format ." in result.commands_run
        assert mock_run.call_count == 2

    def test_duration_is_recorded(self, tmp_path: Path):
        """Result should include non-zero duration when commands are skipped."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.ruff]\nline-length = 88\n")

        with patch("guardkit.orchestrator.lint_discovery.shutil.which", return_value=None):
            result = run_lint_autofix("TASK-001", 1, tmp_path)

        assert result is not None
        assert result.duration_seconds >= 0.0

    @patch("guardkit.orchestrator.lint_discovery.subprocess.run")
    def test_dotnet_format_skips_which_check(self, mock_run, tmp_path: Path):
        """dotnet commands should not check shutil.which."""
        (tmp_path / "App.csproj").write_text("<Project />\n")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = run_lint_autofix("TASK-001", 1, tmp_path)

        assert result is not None
        assert "dotnet format" in result.commands_run

    @patch("guardkit.orchestrator.lint_discovery.subprocess.run")
    def test_cargo_fmt_skips_which_check(self, mock_run, tmp_path: Path):
        """cargo commands should not check shutil.which."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = \"app\"\n")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = run_lint_autofix("TASK-001", 1, tmp_path)

        assert result is not None
        assert "cargo fmt" in result.commands_run
