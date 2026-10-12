"""Tests for the L3 runtime coverage gate (TASK-QAV-003).

Unit tests for report-parsing + symbol mapping; the AC-7 integration test
exercising the real runner.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from guardkit.orchestrator.quality_gates.coverage_gate import (
    CoverageFinding,
    CoverageResult,
    _extract_public_symbols,
    _map_executed_lines_to_symbols,
    _parse_coverage_json,
    _run_coverage,
    _is_python_stack,
    run_coverage_gate,
    run_coverage_gate_for_bundle,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_worktree(tmp_path: Path) -> Path:
    """Create a temporary worktree directory."""
    return tmp_path


@pytest.fixture()
def fixture_with_zero_execution(tmp_worktree: Path) -> Path:
    """Create a worktree with a public function that is never executed.

    Returns the worktree path.
    """
    # Source file with an unused public function
    src = tmp_worktree / "mymodule.py"
    src.write_text(
        'def public_func():\n    return 42\n\ndef unused_func():\n    return "never called"\n',
        encoding="utf-8",
    )

    # Test file that only calls public_func
    test = tmp_worktree / "test_mymodule.py"
    test.write_text(
        "from mymodule import public_func\n\ndef test_public():\n"
        "    assert public_func() == 42\n",
        encoding="utf-8",
    )

    # pytest.ini to enable coverage
    ini = tmp_worktree / "pytest.ini"
    ini.write_text(
        "[pytest]\ntestpaths = .\naddopts = --cov=mymodule --cov-report=json --cov-branch -p no:cacheprovider\n",
        encoding="utf-8",
    )

    return tmp_worktree


@pytest.fixture()
def fixture_fully_covered(tmp_worktree: Path) -> Path:
    """Create a worktree where all public functions are executed.

    Returns the worktree path.
    """
    src = tmp_worktree / "mymodule.py"
    src.write_text(
        'def public_func():\n    return 42\n\ndef unused_func():\n    return "never called"\n',
        encoding="utf-8",
    )

    # Test file that calls BOTH functions
    test = tmp_worktree / "test_mymodule.py"
    test.write_text(
        "from mymodule import public_func, unused_func\n\n"
        "def test_public():\n    assert public_func() == 42\n\n"
        "def test_unused():\n    assert unused_func() == 'never called'\n",
        encoding="utf-8",
    )

    ini = tmp_worktree / "pytest.ini"
    ini.write_text(
        "[pytest]\ntestpaths = .\naddopts = --cov=mymodule --cov-report=json --cov-branch -p no:cacheprovider\n",
        encoding="utf-8",
    )

    return tmp_worktree


# ---------------------------------------------------------------------------
# Symbol extraction tests
# ---------------------------------------------------------------------------


class TestExtractPublicSymbols:
    """Tests for _extract_public_symbols."""

    def test_extract_functions(self, tmp_worktree: Path) -> None:
        """AC-1: Extract public function symbols from source file."""
        src = tmp_worktree / "mod.py"
        src.write_text(
            "def public_func():\n    pass\n\n"
            "def _private_func():\n    pass\n\n"
            "class PublicClass:\n    pass\n\n"
            "class _PrivateClass:\n    pass\n",
            encoding="utf-8",
        )

        symbols = _extract_public_symbols(src)

        names = [s["name"] for s in symbols]
        assert "public_func" in names
        assert "_private_func" not in names
        assert "PublicClass" in names
        assert "_PrivateClass" not in names

    def test_extract_no_public_symbols(self, tmp_worktree: Path) -> None:
        """Symbols list is empty when no public symbols exist."""
        src = tmp_worktree / "mod.py"
        src.write_text(
            "def _private():\n    pass\n",
            encoding="utf-8",
        )

        symbols = _extract_public_symbols(src)
        assert symbols == []

    def test_extract_async_functions(self, tmp_worktree: Path) -> None:
        """AC-1: Async public functions are also extracted."""
        src = tmp_worktree / "mod.py"
        src.write_text(
            "async def async_public():\n    pass\n",
            encoding="utf-8",
        )

        symbols = _extract_public_symbols(src)
        assert len(symbols) == 1
        assert symbols[0]["name"] == "async_public"


class TestMapExecutedLines:
    """Tests for _map_executed_lines_to_symbols."""

    def test_map_executed_lines(self) -> None:
        """AC-1: Executed lines are correctly mapped to symbols."""
        symbols = [
            {"name": "func_a", "lineno": 1, "end_lineno": 3, "executed_lines": []},
            {"name": "func_b", "lineno": 5, "end_lineno": 7, "executed_lines": []},
        ]
        executed = [2, 6]  # Line 2 in func_a, line 6 in func_b

        result = _map_executed_lines_to_symbols(symbols, executed)

        assert result[0]["executed_lines"] == [2]
        assert result[1]["executed_lines"] == [6]

    def test_map_no_executed_lines(self) -> None:
        """AC-3: Symbols with no executed lines remain empty."""
        symbols = [
            {"name": "func_a", "lineno": 1, "end_lineno": 3, "executed_lines": []},
        ]
        executed: list[int] = []

        result = _map_executed_lines_to_symbols(symbols, executed)

        assert result[0]["executed_lines"] == []


# ---------------------------------------------------------------------------
# Coverage report parsing tests
# ---------------------------------------------------------------------------


class TestParseCoverageJson:
    """Tests for _parse_coverage_json."""

    def test_parse_zero_execution_finding(
        self, tmp_worktree: Path
    ) -> None:
        """AC-1: Zero-execution symbol produces a finding.

        A fixture worktree whose tests pass but never execute an authored
        public function yields one coverage finding with
        {file, symbol, lineno, executed_lines: 0, severity:"warning",
        pattern:"ZERO_EXECUTION"} and a positive run status.
        """
        # Create coverage JSON that mirrors the fixture_with_zero_execution
        json_file = tmp_worktree / "coverage.json"
        json_file.write_text(
            json.dumps({
                "files": {
                    "mymodule.py": {
                        "executed_lines": [1, 2, 4],  # public_func lines
                        "functions": {
                            "public_func": {
                                "start_line": 1,
                                "executed_lines": [2],
                            },
                            "unused_func": {
                                "start_line": 4,
                                "executed_lines": [],  # zero execution!
                            },
                        },
                    },
                },
                "totals": {
                    "percent_covered": 75.0,
                },
            }),
            encoding="utf-8",
        )

        result = _parse_coverage_json(
            json_file,
            ["mymodule.py"],
            tmp_worktree,
        )

        assert result["status"] == "positive"
        assert len(result["findings"]) >= 1
        # Find the unused_func finding
        unused_findings = [
            f for f in result["findings"] if f["symbol"] == "unused_func"
        ]
        assert len(unused_findings) == 1
        finding = unused_findings[0]
        assert finding["file"] == "mymodule.py"
        assert finding["symbol"] == "unused_func"
        assert finding["executed_lines"] == 0
        assert finding["severity"] == "warning"
        assert finding["pattern"] == "ZERO_EXECUTION"

    def test_parse_clean_no_findings(
        self, tmp_worktree: Path
    ) -> None:
        """AC-2: Fully-covered fixture yields findings:[] with clean status.

        An authored public function executed at least once yields no finding;
        a fully-covered fixture yields findings:[] with a positive status
        (real clean verdict).
        """
        json_file = tmp_worktree / "coverage.json"
        json_file.write_text(
            json.dumps({
                "files": {
                    "mymodule.py": {
                        "executed_lines": [1, 2, 4, 5],  # all lines executed
                        "functions": {
                            "public_func": {
                                "start_line": 1,
                                "executed_lines": [2],
                            },
                            "unused_func": {
                                "start_line": 4,
                                "executed_lines": [5],
                            },
                        },
                    },
                },
                "totals": {
                    "percent_covered": 100.0,
                },
            }),
            encoding="utf-8",
        )

        result = _parse_coverage_json(
            json_file,
            ["mymodule.py"],
            tmp_worktree,
        )

        assert result["status"] == "clean"
        assert result["findings"] == []

    def test_parse_absent_on_missing_json(self, tmp_worktree: Path) -> None:
        """AC-4: Missing coverage JSON returns absent status."""
        json_file = tmp_worktree / "coverage.json"
        # Don't create the file

        result = _parse_coverage_json(
            json_file,
            ["mymodule.py"],
            tmp_worktree,
        )

        assert result["status"] == "absent"
        assert result["findings"] == []
        assert result["coverage_percentage"] == 0.0

    def test_parse_absent_on_invalid_json(self, tmp_worktree: Path) -> None:
        """AC-4: Invalid JSON returns absent status."""
        json_file = tmp_worktree / "coverage.json"
        json_file.write_text("not valid json", encoding="utf-8")

        result = _parse_coverage_json(
            json_file,
            ["mymodule.py"],
            tmp_worktree,
        )

        assert result["status"] == "absent"

    def test_parse_zero_exec_only(self, tmp_worktree: Path) -> None:
        """AC-3: Zero-execution only — no percentage threshold.

        A symbol with any executed line is not flagged (v0 policy).
        """
        json_file = tmp_worktree / "coverage.json"
        json_file.write_text(
            json.dumps({
                "files": {
                    "mymodule.py": {
                        "executed_lines": [2],  # only line 2 executed
                        "functions": {
                            "partial_func": {
                                "start_line": 1,
                                "executed_lines": [2],  # has execution
                            },
                            "zero_func": {
                                "start_line": 5,
                                "executed_lines": [],  # zero execution
                            },
                        },
                    },
                },
                "totals": {
                    "percent_covered": 25.0,
                },
            }),
            encoding="utf-8",
        )

        result = _parse_coverage_json(
            json_file,
            ["mymodule.py"],
            tmp_worktree,
        )

        # partial_func should NOT be flagged (has executed lines)
        partial_findings = [
            f for f in result["findings"] if f["symbol"] == "partial_func"
        ]
        assert len(partial_findings) == 0
        # zero_func SHOULD be flagged
        zero_findings = [
            f for f in result["findings"] if f["symbol"] == "zero_func"
        ]
        assert len(zero_findings) == 1


# ---------------------------------------------------------------------------
# Scope gate tests
# ---------------------------------------------------------------------------


class TestScopeGate:
    """Tests for task-type scoping (AC-5)."""

    def test_feature_runs_gate(self, tmp_worktree: Path) -> None:
        """AC-5: FEATURE task type runs the gate."""
        result = run_coverage_gate(
            tmp_worktree,
            [],
            task_type="FEATURE",
        )
        # Returns None for no authored files, but doesn't gate out
        assert result is None  # absent due to no authored files

    def test_refactor_runs_gate(self, tmp_worktree: Path) -> None:
        """AC-5: REFACTOR task type runs the gate."""
        result = run_coverage_gate(
            tmp_worktree,
            [],
            task_type="REFACTOR",
        )
        assert result is None

    def test_integration_runs_gate(self, tmp_worktree: Path) -> None:
        """AC-5: INTEGRATION task type runs the gate."""
        result = run_coverage_gate(
            tmp_worktree,
            [],
            task_type="INTEGRATION",
        )
        assert result is None

    def test_scaffolding_gates_out(self, tmp_worktree: Path) -> None:
        """AC-5: SCAFFOLDING task type gates out (returns None)."""
        result = run_coverage_gate(
            tmp_worktree,
            ["some_file.py"],
            task_type="SCAFFOLDING",
        )
        assert result is None

    def test_documentation_gates_out(self, tmp_worktree: Path) -> None:
        """AC-5: DOCUMENTATION task type gates out."""
        result = run_coverage_gate(
            tmp_worktree,
            ["some_file.py"],
            task_type="DOCUMENTATION",
        )
        assert result is None


# ---------------------------------------------------------------------------
# Absent-signal safety tests (AC-4)
# ---------------------------------------------------------------------------


class TestAbsentSignalSafety:
    """Tests for absent-signal safety (AC-4)."""

    def test_tool_missing(self, tmp_worktree: Path) -> None:
        """AC-4: Coverage tool missing → absent signal."""
        # Create a non-Python stack (no .py files)
        src = tmp_worktree / "main.go"
        src.write_text("package main\n", encoding="utf-8")

        result = run_coverage_gate(
            tmp_worktree,
            ["main.go"],
            task_type="FEATURE",
        )
        assert result is None  # absent signal, not a pass

    def test_non_python_stack(self, tmp_worktree: Path) -> None:
        """AC-4: Non-Python stack → absent signal."""
        result = _is_python_stack(tmp_worktree)
        assert result is False

    def test_run_error_absent(self, tmp_worktree: Path) -> None:
        """AC-4: Runner error → absent signal, never a pass."""
        # Create a worktree with no pytest and no Python config
        src = tmp_worktree / "app.py"
        src.write_text("print('hello')\n", encoding="utf-8")

        result = _run_coverage(
            tmp_worktree,
            ["app.py"],
        )
        # Should return None (absent) because no pytest config
        assert result is None


# ---------------------------------------------------------------------------
# Integration test: real pytest-under-coverage path (AC-7)
# ---------------------------------------------------------------------------


class TestIntegrationRealRunner:
    """AC-7: Integration test exercising the real pytest-under-coverage path.

    Runs the real pytest-under-coverage path over a fixture worktree
    (no mocked coverage report) and asserts the finding appears.
    """

    def test_ac7_zero_execution_finding_real_runner(
        self, fixture_with_zero_execution: Path
    ) -> None:
        """AC-7: Real pytest run produces zero-execution finding.

        An integration test runs the real pytest-under-coverage path over a
        fixture worktree (no mocked coverage report) and asserts the finding
        appears in the rendered evidence bundle.
        """
        result = run_coverage_gate(
            fixture_with_zero_execution,
            ["mymodule.py"],
            task_type="FEATURE",
            timeout=60,
        )

        # The gate should have run and produced findings
        assert result is not None, (
            "Coverage gate should not return absent for a Python worktree "
            "with authored files and pytest config"
        )
        assert result["status"] == "positive"
        assert len(result["findings"]) >= 1

        # Verify the finding structure
        finding = result["findings"][0]
        assert finding["file"] == "mymodule.py"
        assert finding["symbol"] == "unused_func"
        assert finding["lineno"] == 4
        assert finding["executed_lines"] == 0
        assert finding["severity"] == "warning"
        assert finding["pattern"] == "ZERO_EXECUTION"

    def test_ac7_fully_covered_clean(
        self, fixture_fully_covered: Path
    ) -> None:
        """AC-7: Real pytest run with full coverage yields clean result.

        An authored public function executed at least once yields no finding;
        a fully-covered fixture yields findings:[] with a positive status.
        """
        result = run_coverage_gate(
            fixture_fully_covered,
            ["mymodule.py"],
            task_type="FEATURE",
            timeout=60,
        )

        assert result is not None
        assert result["status"] == "clean"
        assert result["findings"] == []


# ---------------------------------------------------------------------------
# Advisory-only tests (AC-6)
# ---------------------------------------------------------------------------


class TestAdvisoryOnly:
    """Tests for advisory-only nature (AC-6).

    Coverage findings surface as should_fix Coach feedback; they never
    deterministically override an approve in v0.
    """

    def test_finding_structure_advisory(self, tmp_worktree: Path) -> None:
        """AC-6: Findings have advisory severity."""
        json_file = tmp_worktree / "coverage.json"
        json_file.write_text(
            json.dumps({
                "files": {
                    "mod.py": {
                        "executed_lines": [],
                        "functions": {
                            "unused": {
                                "start_line": 1,
                                "executed_lines": [],
                            },
                        },
                    },
                },
                "totals": {"percent_covered": 0.0},
            }),
            encoding="utf-8",
        )

        result = _parse_coverage_json(
            json_file,
            ["mod.py"],
            tmp_worktree,
        )

        assert result["status"] == "positive"
        for finding in result["findings"]:
            assert finding["severity"] == "warning"
            assert finding["pattern"] == "ZERO_EXECUTION"


# ---------------------------------------------------------------------------
# CoverageResult dataclass tests
# ---------------------------------------------------------------------------


class TestCoverageResult:
    """Tests for the CoverageResult dataclass."""

    def test_default_values(self) -> None:
        """CoverageResult has sensible defaults."""
        result = CoverageResult()
        assert result.status == "absent"
        assert result.findings == []
        assert result.coverage_percentage == 0.0
        assert result.files_below_threshold == 0

    def test_positive_status(self) -> None:
        """CoverageResult can represent positive findings."""
        finding = CoverageFinding(
            file="mod.py",
            symbol="unused",
            lineno=1,
        )
        result = CoverageResult(
            status="positive",
            findings=[finding],
            coverage_percentage=50.0,
            files_below_threshold=1,
        )
        assert result.status == "positive"
        assert len(result.findings) == 1
        assert result.findings[0].symbol == "unused"

    def test_clean_status(self) -> None:
        """CoverageResult can represent clean state."""
        result = CoverageResult(
            status="clean",
            findings=[],
            coverage_percentage=100.0,
            files_below_threshold=0,
        )
        assert result.status == "clean"
        assert result.findings == []


# ---------------------------------------------------------------------------
# CoverageFinding dataclass tests
# ---------------------------------------------------------------------------


class TestCoverageFinding:
    """Tests for the CoverageFinding dataclass."""

    def test_default_severity_and_pattern(self) -> None:
        """CoverageFinding has correct default values."""
        finding = CoverageFinding(
            file="mod.py",
            symbol="func",
            lineno=1,
        )
        assert finding.severity == "warning"
        assert finding.pattern == "ZERO_EXECUTION"
        assert finding.executed_lines == 0


# ---------------------------------------------------------------------------
# Declared components and honest absence (12 October 2026, web readiness W3)
# ---------------------------------------------------------------------------


class TestDeclaredComponentAndHonestAbsence:
    """A non-Python project is never given a root pytest run, and a run that
    measured none of the task's files is never ``clean``."""

    def test_typescript_worktree_with_a_stray_py_helper_runs_no_pytest(
        self, tmp_worktree: Path
    ) -> None:
        (tmp_worktree / "package.json").write_text("{}", encoding="utf-8")
        (tmp_worktree / "src").mkdir()
        (tmp_worktree / "src" / "app.ts").write_text(
            "export const x = 1;\n", encoding="utf-8"
        )
        (tmp_worktree / "scripts").mkdir()
        (tmp_worktree / "scripts" / "helper.py").write_text(
            "print('x')\n", encoding="utf-8"
        )

        with patch(
            "guardkit.orchestrator.quality_gates.coverage_gate.subprocess.run"
        ) as run:
            result = run_coverage_gate_for_bundle(
                tmp_worktree,
                ["src/app.ts", "scripts/helper.py"],
                task_type="FEATURE",
            )

        run.assert_not_called()
        assert result is None  # the existing absent signal, never a pass
        assert _is_python_stack(tmp_worktree) is False

    def test_declared_non_python_component_is_unsupported_not_root_pytest(
        self, tmp_worktree: Path
    ) -> None:
        # The repository root carries Python tooling; the task's component
        # is the TypeScript web app.
        (tmp_worktree / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        web = tmp_worktree / "web"
        web.mkdir()
        (web / "package.json").write_text("{}", encoding="utf-8")
        (web / "tool.py").write_text("def f():\n    return 1\n", encoding="utf-8")

        with patch(
            "guardkit.orchestrator.quality_gates.coverage_gate.subprocess.run"
        ) as run:
            result = run_coverage_gate_for_bundle(
                tmp_worktree,
                ["web/src/App.tsx", "web/tool.py"],
                task_type="FEATURE",
                component="web",
                component_cwd="web",
            )

        run.assert_not_called()
        assert result["status"] == "unsupported_stack"
        assert result["ran"] is False
        assert result["findings"] is None
        assert "web" in result["reason"]

    def test_named_but_undeclared_component_runs_nothing(
        self, tmp_worktree: Path
    ) -> None:
        (tmp_worktree / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        with patch(
            "guardkit.orchestrator.quality_gates.coverage_gate.subprocess.run"
        ) as run:
            result = run_coverage_gate_for_bundle(
                tmp_worktree,
                ["mod.py"],
                task_type="FEATURE",
                component="api",
                component_cwd=None,
            )
        run.assert_not_called()
        assert result["status"] == "absent"
        assert result["findings"] is None

    def test_python_component_is_measured_in_its_own_directory(
        self, tmp_worktree: Path
    ) -> None:
        api = tmp_worktree / "api"
        api.mkdir()
        (api / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        (api / "svc.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        seen: Dict[str, Any] = {}

        def fake_run(cmd, cwd, **kwargs):
            seen["cwd"] = cwd
            report = Path(cwd) / ".cov_output" / "coverage.json"
            report.write_text(
                json.dumps({
                    "files": {"svc.py": {
                        "executed_lines": [],
                        "functions": {"f": {"start_line": 1, "executed_lines": []}},
                    }},
                    "totals": {"percent_covered": 0.0},
                }),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with patch(
            "guardkit.orchestrator.quality_gates.coverage_gate.subprocess.run",
            side_effect=fake_run,
        ):
            result = run_coverage_gate_for_bundle(
                tmp_worktree,
                ["api/svc.py", "web/App.tsx"],
                task_type="FEATURE",
                component="api",
                component_cwd="api",
            )

        assert seen["cwd"] == str(api)
        assert result["status"] == "positive"
        # Findings still name the file from the repository root.
        assert result["findings"][0]["file"] == "api/svc.py"

    def test_a_run_that_measured_no_authored_file_is_never_clean(
        self, tmp_worktree: Path
    ) -> None:
        json_file = tmp_worktree / "coverage.json"
        json_file.write_text(
            json.dumps({
                "files": {"other_pkg/unrelated.py": {"executed_lines": [1]}},
                "totals": {"percent_covered": 100.0},
            }),
            encoding="utf-8",
        )

        result = _parse_coverage_json(json_file, ["mymodule.py"], tmp_worktree)

        assert result["status"] != "clean"
        assert result["status"] == "absent"
        assert result["findings"] is None

    def test_no_tests_collected_is_absent(self, tmp_worktree: Path) -> None:
        """pytest exit 5 is absent even when a coverage report was written."""
        (tmp_worktree / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        (tmp_worktree / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")

        def fake_run(cmd, cwd, **kwargs):
            (Path(cwd) / ".cov_output" / "coverage.json").write_text(
                json.dumps({
                    "files": {"mod.py": {
                        "executed_lines": [],
                        "functions": {"f": {"start_line": 1, "executed_lines": []}},
                    }},
                    "totals": {"percent_covered": 0.0},
                }),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(cmd, 5, "", "")

        with patch(
            "guardkit.orchestrator.quality_gates.coverage_gate.subprocess.run",
            side_effect=fake_run,
        ):
            result = run_coverage_gate(tmp_worktree, ["mod.py"], task_type="FEATURE")

        assert result is None
