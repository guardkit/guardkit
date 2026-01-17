"""
GuardKit Doctor - Environment Diagnostic Tool.

This module provides comprehensive environment checks for GuardKit installation,
dependencies, and configuration.

Architecture:
- CheckStatus: Enum for check results (PASS, FAIL, WARNING)
- CheckResult: Dataclass for check output
- Check: Base class using Strategy pattern
- Specific checks: PythonVersionCheck, PackageCheck, etc.
- DoctorRunner: Orchestrates check execution
- DoctorReport: Formats results with Rich

Example:
    $ guardkit doctor
    GuardKit Environment Check
    ===========================

    Core Dependencies:
      Python:           3.14.0 (/Library/Frameworks/...) ✓
      guardkit-py:      0.1.0 ✓
      ...

    All checks passed!
"""

import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

console = Console()


# ============================================================================
# Check Status and Results
# ============================================================================


class CheckStatus(Enum):
    """Status of a diagnostic check."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass
class CheckResult:
    """Result of a diagnostic check."""

    name: str
    status: CheckStatus
    message: str
    details: Optional[str] = None
    required: bool = True

    @property
    def icon(self) -> str:
        """Get status icon."""
        return {
            CheckStatus.PASS: "✓",
            CheckStatus.FAIL: "✗",
            CheckStatus.WARNING: "⚠",
        }[self.status]

    @property
    def color(self) -> str:
        """Get status color."""
        return {
            CheckStatus.PASS: "green",
            CheckStatus.FAIL: "red",
            CheckStatus.WARNING: "yellow",
        }[self.status]


# ============================================================================
# Check Base Class (Strategy Pattern)
# ============================================================================


class Check(ABC):
    """Base class for environment checks."""

    def __init__(self, required: bool = True):
        """Initialize check.

        Args:
            required: Whether this check is required for GuardKit to function
        """
        self.required = required

    @abstractmethod
    def run(self) -> CheckResult:
        """Execute the check.

        Returns:
            CheckResult with status, message, and optional details
        """
        pass


# ============================================================================
# Specific Check Implementations
# ============================================================================


class PythonVersionCheck(Check):
    """Check Python version meets minimum requirements."""

    def __init__(self, min_version: tuple = (3, 10)):
        """Initialize Python version check.

        Args:
            min_version: Minimum required Python version tuple (major, minor)
        """
        super().__init__(required=True)
        self.min_version = min_version

    def run(self) -> CheckResult:
        """Check Python version."""
        current = sys.version_info
        current_str = f"{current.major}.{current.minor}.{current.micro}"
        python_path = sys.executable

        if (current.major, current.minor) >= self.min_version:
            return CheckResult(
                name="Python",
                status=CheckStatus.PASS,
                message=f"{current_str} ({python_path})",
                required=self.required,
            )
        else:
            min_str = f"{self.min_version[0]}.{self.min_version[1]}"
            return CheckResult(
                name="Python",
                status=CheckStatus.FAIL,
                message=f"{current_str} (requires {min_str}+)",
                details=f"Python path: {python_path}",
                required=self.required,
            )


class PackageCheck(Check):
    """Check if a Python package is installed."""

    def __init__(self, package_name: str, import_name: Optional[str] = None, required: bool = True):
        """Initialize package check.

        Args:
            package_name: Name of the package (for display)
            import_name: Import name if different from package_name
            required: Whether this package is required
        """
        super().__init__(required=required)
        self.package_name = package_name
        self.import_name = import_name or package_name

    def run(self) -> CheckResult:
        """Check if package is installed."""
        try:
            module = __import__(self.import_name)
            version = getattr(module, "__version__", "unknown")
            return CheckResult(
                name=self.package_name,
                status=CheckStatus.PASS,
                message=version,
                required=self.required,
            )
        except ImportError:
            status = CheckStatus.FAIL if self.required else CheckStatus.WARNING
            message = "Not installed" if self.required else "Not installed (optional)"
            return CheckResult(
                name=self.package_name,
                status=status,
                message=message,
                required=self.required,
            )


class CLIToolCheck(Check):
    """Check if a CLI tool is available."""

    def __init__(
        self,
        tool_name: str,
        version_args: Optional[List[str]] = None,
        required: bool = True,
    ):
        """Initialize CLI tool check.

        Args:
            tool_name: Name of the CLI tool
            version_args: Arguments to get version (defaults to ['--version'])
            required: Whether this tool is required
        """
        super().__init__(required=required)
        self.tool_name = tool_name
        self.version_args = version_args or ["--version"]

    def run(self) -> CheckResult:
        """Check if CLI tool is available."""
        # Find tool path
        tool_path = shutil.which(self.tool_name)

        if not tool_path:
            status = CheckStatus.FAIL if self.required else CheckStatus.WARNING
            message = "Not found" if self.required else "Not found (optional)"
            return CheckResult(
                name=self.tool_name,
                status=status,
                message=message,
                required=self.required,
            )

        # Try to get version
        try:
            result = subprocess.run(
                [tool_path] + self.version_args,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )

            # Parse version from output
            output = (result.stdout + result.stderr).strip()
            version_line = output.split("\n")[0] if output else "unknown"

            # Extract just the version number if possible
            import re

            version_match = re.search(r"\d+\.\d+\.\d+", version_line)
            version = version_match.group(0) if version_match else version_line

            return CheckResult(
                name=self.tool_name,
                status=CheckStatus.PASS,
                message=f"{version} ({tool_path})",
                required=self.required,
            )
        except (subprocess.TimeoutExpired, Exception) as e:
            # Tool exists but version check failed
            return CheckResult(
                name=self.tool_name,
                status=CheckStatus.PASS,
                message=f"Found ({tool_path})",
                details=f"Version check failed: {e}",
                required=self.required,
            )


class FileExistsCheck(Check):
    """Check if a file or directory exists."""

    def __init__(
        self,
        path: Path,
        name: str,
        required: bool = False,
        is_dir: bool = False,
    ):
        """Initialize file existence check.

        Args:
            path: Path to check
            name: Display name for the check
            required: Whether this file/dir is required
            is_dir: Whether checking for a directory
        """
        super().__init__(required=required)
        self.path = path
        self.name = name
        self.is_dir = is_dir

    def run(self) -> CheckResult:
        """Check if file/directory exists."""
        if self.path.exists():
            if self.is_dir:
                # Count items in directory if applicable
                try:
                    if self.name.lower() == "tasks/":
                        # Count task files
                        task_files = list(self.path.rglob("TASK-*.md"))
                        count = len(task_files)
                        message = f"Found ({count} tasks)"
                    else:
                        message = "Found"
                except Exception:
                    message = "Found"
            else:
                message = "Found"

            return CheckResult(
                name=self.name,
                status=CheckStatus.PASS,
                message=message,
                required=self.required,
            )
        else:
            status = CheckStatus.FAIL if self.required else CheckStatus.WARNING
            message = "Not found" if self.required else "Not found (optional)"
            return CheckResult(
                name=self.name,
                status=status,
                message=message,
                required=self.required,
            )


# ============================================================================
# Doctor Runner (Orchestration)
# ============================================================================


class DoctorRunner:
    """Orchestrates execution of all diagnostic checks."""

    def __init__(self, checks: Optional[List[Check]] = None):
        """Initialize doctor runner.

        Args:
            checks: List of checks to run. If None, uses default checks.
        """
        self.checks = checks or self._default_checks()

    def _default_checks(self) -> List[Check]:
        """Create default set of checks.

        Returns:
            List of Check instances
        """
        return [
            # Core Dependencies
            PythonVersionCheck(min_version=(3, 10)),
            PackageCheck("guardkit-py", import_name="guardkit", required=True),
            PackageCheck("click", required=True),
            PackageCheck("rich", required=True),
            PackageCheck("pyyaml", import_name="yaml", required=True),
            PackageCheck("frontmatter", required=True),
            # AutoBuild Dependencies
            PackageCheck("claude-agent-sdk", import_name="claude_agent_sdk", required=False),
            CLIToolCheck("claude", required=False),
            # Optional Tools
            CLIToolCheck("git", required=True),
            CLIToolCheck("conductor", required=False),
            # Configuration
            FileExistsCheck(Path.cwd() / "CLAUDE.md", "CLAUDE.md", required=False),
            FileExistsCheck(Path.cwd() / "tasks", "tasks/", required=False, is_dir=True),
        ]

    def run(self) -> List[CheckResult]:
        """Run all checks.

        Returns:
            List of CheckResult instances
        """
        results = []
        for check in self.checks:
            try:
                result = check.run()
                results.append(result)
            except Exception as e:
                # If a check crashes, record it as a failure
                results.append(
                    CheckResult(
                        name=getattr(check, "name", check.__class__.__name__),
                        status=CheckStatus.FAIL,
                        message=f"Check failed: {e}",
                        required=check.required,
                    )
                )
        return results


# ============================================================================
# Doctor Report (Formatting)
# ============================================================================


class DoctorReport:
    """Formats diagnostic results for display."""

    def __init__(self, results: List[CheckResult]):
        """Initialize report.

        Args:
            results: List of CheckResult instances
        """
        self.results = results

    def format_rich(self) -> None:
        """Format and display report using Rich."""
        console.print("\n[bold]GuardKit Environment Check[/bold]")
        console.print("=" * 50 + "\n")

        # Group results by category
        core_deps = []
        autobuild_deps = []
        optional_tools = []
        config = []

        for result in self.results:
            if result.name in ["Python", "guardkit-py", "click", "rich", "pyyaml", "frontmatter"]:
                core_deps.append(result)
            elif result.name in ["claude-agent-sdk", "claude"]:
                autobuild_deps.append(result)
            elif result.name in ["git", "conductor"]:
                optional_tools.append(result)
            else:
                config.append(result)

        # Display each category
        self._display_category("Core Dependencies", core_deps)
        self._display_category("AutoBuild Dependencies", autobuild_deps)
        self._display_category("Optional Tools", optional_tools)
        self._display_category("Configuration", config)

        # Summary
        console.print()
        failed = [r for r in self.results if r.status == CheckStatus.FAIL and r.required]
        warnings = [r for r in self.results if r.status == CheckStatus.WARNING]

        if failed:
            console.print(f"[red]✗ {len(failed)} required checks failed[/red]")
            for result in failed:
                console.print(f"  - {result.name}: {result.message}")
        elif warnings:
            console.print(f"[yellow]⚠ {len(warnings)} optional checks have warnings[/yellow]")
            console.print("[green]All required checks passed![/green]")
        else:
            console.print("[green]✓ All checks passed![/green]")

    def _display_category(self, title: str, results: List[CheckResult]) -> None:
        """Display a category of results.

        Args:
            title: Category title
            results: List of CheckResult instances in this category
        """
        if not results:
            return

        console.print(f"[bold]{title}:[/bold]")
        for result in results:
            # Format with proper alignment
            name_width = 18
            icon = f"[{result.color}]{result.icon}[/{result.color}]"
            console.print(f"  {result.name:<{name_width}} {result.message} {icon}")

            if result.details:
                console.print(f"  {' ' * name_width} {result.details}")

        console.print()

    def has_failures(self) -> bool:
        """Check if any required checks failed.

        Returns:
            True if any required check failed
        """
        return any(r.status == CheckStatus.FAIL and r.required for r in self.results)


# ============================================================================
# Main Entry Point
# ============================================================================


def run_doctor() -> int:
    """Run GuardKit doctor diagnostic.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    runner = DoctorRunner()
    results = runner.run()

    report = DoctorReport(results)
    report.format_rich()

    return 1 if report.has_failures() else 0
