"""Multi-stack BDD reachability tests (TASK-BDDW-002).

Verifies that ``guardkitfactory.bdd.discover`` routes .NET projects to
``ReqnrollPlugin`` and JS/TS projects to ``CucumberJSPlugin`` through the
same discovery seam, and that unsupported stacks yield ``None`` (absent
signal).

Coach validation:

.. code-block:: bash

    pytest tests/ -k "bdd and (reqnroll or cucumber or stack_profile)" -v
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

# Skip the entire module unless the real cross-repo stack is installed
# (TASK-FIX-BDDROUTETEST01). In a bare guardkit dev venv or an autobuild
# worktree venv this skips cleanly instead of breaking collection for the
# whole quality_gates directory; in the seam-tests CI job it runs.
pytest.importorskip(
    "guardkitfactory.bdd",
    reason=(
        "guardkitfactory not installed; this seam test runs in the seam-tests "
        "CI job (pip install -e ../guardkitfactory)."
    ),
)

from guardkitfactory.bdd import StackProfile, discover
from guardkitfactory.bdd.plugins import CucumberJSPlugin, PytestBDDPlugin, ReqnrollPlugin

pytestmark = pytest.mark.seam


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_stack(
    language: str,
    test_framework: str = "pytest",
    package_manager: str = "pip",
    extras: dict | None = None,
) -> StackProfile:
    """Build a minimal ``StackProfile`` pointing at a temporary directory."""
    return StackProfile(
        language=language,
        test_framework=test_framework,
        package_manager=package_manager,
        project_root=Path("."),
        extras=extras or {},
    )


# Shared mock for subprocess.run that returns success for any command
_SUCCESS = mock.MagicMock(returncode=0)


def _patch_subprocess_for(plugin_module_name: str):
    """Return a context manager that patches subprocess.run on the given plugin module."""
    import guardkitfactory.bdd.plugins.reqnroll_plugin as reqnroll_mod
    import guardkitfactory.bdd.plugins.cucumber_js_plugin as cucumber_mod
    import guardkitfactory.bdd.plugins.pytest_bdd_plugin as pytest_bdd_mod

    modules = {
        "guardkitfactory.bdd.plugins.reqnroll_plugin": reqnroll_mod,
        "guardkitfactory.bdd.plugins.cucumber_js_plugin": cucumber_mod,
        "guardkitfactory.bdd.plugins.pytest_bdd_plugin": pytest_bdd_mod,
    }
    mod = modules.get(plugin_module_name)
    if mod is None:
        raise ValueError(f"Unknown plugin module: {plugin_module_name}")
    return mock.patch.object(mod.subprocess, "run")


# ---------------------------------------------------------------------------
# AC-2: multi-stack reachability — plugin selection per stack profile
# ---------------------------------------------------------------------------


class TestMultiStackRouting:
    """Plugin selection must match the detected stack profile."""

    def test_python_routes_to_pytest_bdd(self, tmp_path: Path) -> None:
        """A Python project with pytest discovers ``PytestBDDPlugin``."""
        stack = _make_stack(language="python", test_framework="pytest")
        with _patch_subprocess_for("guardkitfactory.bdd.plugins.pytest_bdd_plugin") as m:
            m.return_value = _SUCCESS
            result = PytestBDDPlugin.discover(stack, tmp_path)
        assert result is not None
        assert isinstance(result, PytestBDDPlugin)

    def test_dotnet_routes_to_reqnroll(self, tmp_path: Path) -> None:
        """A .NET project with a .sln file discovers ``ReqnrollPlugin``."""
        (tmp_path / "test.sln").write_text("Microsoft Visual Studio Solution File\n")
        stack = _make_stack(
            language="dotnet",
            test_framework="dotnet-test",
            package_manager="nuget",
        )
        with _patch_subprocess_for("guardkitfactory.bdd.plugins.reqnroll_plugin") as m:
            m.return_value = _SUCCESS
            result = ReqnrollPlugin.discover(stack, tmp_path)
        assert result is not None
        assert isinstance(result, ReqnrollPlugin)

    def test_csharp_routes_to_reqnroll(self, tmp_path: Path) -> None:
        """A C# project with a .csproj file discovers ``ReqnrollPlugin``."""
        (tmp_path / "test.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk"></Project>\n')
        stack = _make_stack(
            language="csharp",
            test_framework="dotnet-test",
            package_manager="nuget",
        )
        with _patch_subprocess_for("guardkitfactory.bdd.plugins.reqnroll_plugin") as m:
            m.return_value = _SUCCESS
            result = ReqnrollPlugin.discover(stack, tmp_path)
        assert result is not None
        assert isinstance(result, ReqnrollPlugin)

    def test_javascript_routes_to_cucumberjs(self, tmp_path: Path) -> None:
        """A JavaScript project with cucumber dependency discovers ``CucumberJSPlugin``."""
        (tmp_path / "package.json").write_text('{"dependencies": {"cucumber": "^9.0.0"}}\n')
        stack = _make_stack(
            language="javascript",
            test_framework="cucumber-js",
            package_manager="npm",
        )
        with _patch_subprocess_for("guardkitfactory.bdd.plugins.cucumber_js_plugin") as m:
            m.return_value = _SUCCESS
            result = CucumberJSPlugin.discover(stack, tmp_path)
        assert result is not None
        assert isinstance(result, CucumberJSPlugin)

    def test_typescript_routes_to_cucumberjs(self, tmp_path: Path) -> None:
        """A TypeScript project with cucumber dependency discovers ``CucumberJSPlugin``."""
        (tmp_path / "package.json").write_text('{"dependencies": {"@cucumber/cucumber": "^9.0.0"}}\n')
        stack = _make_stack(
            language="typescript",
            test_framework="cucumber-js",
            package_manager="npm",
        )
        with _patch_subprocess_for("guardkitfactory.bdd.plugins.cucumber_js_plugin") as m:
            m.return_value = _SUCCESS
            result = CucumberJSPlugin.discover(stack, tmp_path)
        assert result is not None
        assert isinstance(result, CucumberJSPlugin)

    def test_factory_discover_returns_matching_plugin(self, tmp_path: Path) -> None:
        """Factory ``discover`` returns the first matching plugin for the stack."""
        (tmp_path / "test.sln").write_text("Solution\n")
        stack = _make_stack(
            language="dotnet",
            test_framework="dotnet-test",
            package_manager="nuget",
        )
        with _patch_subprocess_for("guardkitfactory.bdd.plugins.reqnroll_plugin") as m:
            m.return_value = _SUCCESS
            result = discover(stack, tmp_path)
        assert result is not None
        assert isinstance(result, ReqnrollPlugin)

    # -----------------------------------------------------------------------
    # AC-2b: unsupported stack → absent signal (None)
    # -----------------------------------------------------------------------

    def test_unknown_language_returns_none(self, tmp_path: Path) -> None:
        """An unknown language returns ``None`` from all plugins."""
        stack = _make_stack(language="rust", test_framework="cargo-test")
        assert PytestBDDPlugin.discover(stack, tmp_path) is None
        assert ReqnrollPlugin.discover(stack, tmp_path) is None
        assert CucumberJSPlugin.discover(stack, tmp_path) is None

    def test_python_without_pytest_bdd_returns_none(self, tmp_path: Path) -> None:
        """Python project without pytest_bdd package returns ``None``."""
        stack = _make_stack(language="python", test_framework="pytest")
        import guardkitfactory.bdd.plugins.pytest_bdd_plugin as mod
        with mock.patch.object(mod.subprocess, "run") as m:
            m.side_effect = FileNotFoundError("pytest_bdd")
            result = PytestBDDPlugin.discover(stack, tmp_path)
        assert result is None

    def test_dotnet_without_project_files_returns_none(self, tmp_path: Path) -> None:
        """A .NET project without .sln or .csproj returns ``None``."""
        stack = _make_stack(
            language="dotnet",
            test_framework="dotnet-test",
            package_manager="nuget",
        )
        with _patch_subprocess_for("guardkitfactory.bdd.plugins.reqnroll_plugin") as m:
            m.return_value = _SUCCESS
            result = ReqnrollPlugin.discover(stack, tmp_path)
        assert result is None

    def test_js_without_cucumber_dependency_returns_none(self, tmp_path: Path) -> None:
        """A JS project without cucumber dependency returns ``None``."""
        (tmp_path / "package.json").write_text('{"dependencies": {"express": "^4.0.0"}}\n')
        stack = _make_stack(
            language="javascript",
            test_framework="cucumber-js",
            package_manager="npm",
        )
        with _patch_subprocess_for("guardkitfactory.bdd.plugins.cucumber_js_plugin") as m:
            m.return_value = _SUCCESS
            result = CucumberJSPlugin.discover(stack, tmp_path)
        assert result is None

    def test_dotnet_without_dotnet_cli_returns_none(self, tmp_path: Path) -> None:
        """A .NET project without the dotnet CLI returns ``None``."""
        (tmp_path / "test.sln").write_text("Solution\n")
        stack = _make_stack(
            language="dotnet",
            test_framework="dotnet-test",
            package_manager="nuget",
        )
        import guardkitfactory.bdd.plugins.reqnroll_plugin as mod
        with mock.patch.object(mod.subprocess, "run") as m:
            m.side_effect = FileNotFoundError("dotnet")
            result = ReqnrollPlugin.discover(stack, tmp_path)
        assert result is None
