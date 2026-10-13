"""L3 runtime coverage gate — zero-execution authored public surface.

TASK-QAV-003. Runs the worktree test suite under coverage measurement and
flags every authored public symbol with zero real execution — tests green
over code no test ever entered.

Design:
    * Coverage source of truth: coverage.py JSON report (``--cov-report=json``)
      keyed by file + executed line numbers, intersected with the authored
      symbol extents.
    * Symbol extraction: Python AST (``ast`` module) for authored Python files;
      non-Python stacks degrade to absent-signal (``None``).
    * Zero-execution only: a symbol with any executed line is not flagged
      (v0 policy).
    * Advisory only: findings surface as ``should_fix`` feedback; they never
      deterministically override an approve in v0.
    * Scope gate: only FEATURE / REFACTOR / INTEGRATION task types run the
      gate.

Acceptance criteria:
    AC-1: Positive finding for zero-execution symbol.
    AC-2: No finding when executed; fully-covered yields empty findings.
    AC-3: Zero-execution only — no percentage threshold.
    AC-4: Absent-signal safety (tool missing / run error / non-Python stack).
    AC-5: Scope gate (only FEATURE / REFACTOR / INTEGRATION).
    AC-6: Advisory only (should_fix, never blocking).
    AC-7: Integration test exercising real pytest-under-coverage path.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from guardkit.orchestrator import process_group

logger = logging.getLogger(__name__)

# Task-type gate: only these types run the coverage gate.
_GATE_TASK_TYPES = frozenset({"FEATURE", "REFACTOR", "INTEGRATION"})


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoverageFinding:
    """A single zero-execution finding for an authored public symbol.

    Attributes
    ----------
    file : str
        Relative file path of the authored source file.
    symbol : str
        Name of the public symbol (function or class).
    lineno : int
        Line number where the symbol is defined.
    executed_lines : int
        Number of executed lines in the symbol body (always 0 for findings).
    severity : str
        Always ``"warning"`` for zero-execution findings.
    pattern : str
        Always ``"ZERO_EXECUTION"``.
    """

    file: str
    symbol: str
    lineno: int
    executed_lines: int = 0
    severity: str = "warning"
    pattern: str = "ZERO_EXECUTION"


@dataclass
class CoverageResult:
    """Result of the L3 coverage gate analysis.

    Attributes
    ----------
    status : str
        ``"positive"`` when findings exist, ``"clean"`` when no findings,
        ``"absent"`` when the gate could not run or measured none of the
        authored files, ``"unsupported_stack"`` when the task's declared
        component is not a Python project.
    findings : list[CoverageFinding]
        Zero-execution findings (empty when clean or absent).
    coverage_percentage : float
        Overall line coverage percentage (0.0 when absent).
    files_below_threshold : int
        Number of files with below-threshold coverage (0 when absent).
    """

    status: str = "absent"
    findings: List[CoverageFinding] = field(default_factory=list)
    coverage_percentage: float = 0.0
    files_below_threshold: int = 0


# ---------------------------------------------------------------------------
# Symbol extraction via Python AST
# ---------------------------------------------------------------------------


def _extract_public_symbols(file_path: Path) -> List[Dict[str, Any]]:
    """Extract public function and class symbols from a Python source file.

    A symbol is "public" if its name does not start with an underscore
    (following Python convention). Only top-level functions and classes
    are extracted (nested functions/classes are ignored).

    Parameters
    ----------
    file_path : Path
        Path to the Python source file.

    Returns
    -------
    List[Dict[str, Any]]
        List of dicts with ``name``, ``lineno``, ``end_lineno``,
        ``executed_lines`` keys.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Cannot read %s for symbol extraction: %s", file_path, exc)
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        logger.warning("Cannot parse %s for symbol extraction: %s", file_path, exc)
        return []

    symbols: List[Dict[str, Any]] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                symbols.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "end_lineno": node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
                    "executed_lines": [],
                })
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                symbols.append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "end_lineno": node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
                    "executed_lines": [],
                })

    return symbols


def _map_executed_lines_to_symbols(
    symbols: List[Dict[str, Any]],
    executed_lines: List[int],
) -> List[Dict[str, Any]]:
    """Map executed line numbers to their containing symbols.

    Parameters
    ----------
    symbols : List[Dict[str, Any]]
        Symbol dicts from ``_extract_public_symbols``.
    executed_lines : List[int]
        Line numbers that were executed (from coverage report).

    Returns
    -------
    List[Dict[str, Any]]
        Same symbol dicts, updated with ``executed_lines`` populated.
    """
    for sym in symbols:
        sym_lineno = sym["lineno"]
        sym_end = sym["end_lineno"]
        sym_executed = [
            ln for ln in executed_lines
            if sym_lineno <= ln <= sym_end
        ]
        sym["executed_lines"] = sym_executed

    return symbols


# ---------------------------------------------------------------------------
# Coverage report parsing
# ---------------------------------------------------------------------------


def _parse_coverage_json(
    json_path: Path,
    authored_files: List[str],
    worktree_path: Path,
) -> Dict[str, Any]:
    """Parse a coverage.py JSON report and identify zero-execution symbols.

    Parameters
    ----------
    json_path : Path
        Path to the coverage.json file.
    authored_files : List[str]
        Relative paths of authored source files to examine.
    worktree_path : Path
        Root of the worktree (for resolving relative paths).

    Returns
    -------
    Dict[str, Any]
        Dict with ``status``, ``findings``, ``coverage_percentage``,
        ``files_below_threshold`` keys.
    """
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Cannot parse coverage JSON %s: %s", json_path, exc)
        return {
            "status": "absent",
            "findings": [],
            "coverage_percentage": 0.0,
            "files_below_threshold": 0,
        }

    files_data = raw.get("files", {})
    totals = raw.get("totals", {})
    coverage_pct = totals.get("percent_covered", 0.0)

    findings: List[CoverageFinding] = []
    files_below = 0
    files_measured = 0

    for authored_rel in authored_files:
        # Try multiple path formats to match coverage report keys
        rel_key = Path(authored_rel).name
        abs_key = str(Path(worktree_path) / authored_rel)
        normalized_key = str(Path(authored_rel).as_posix())

        file_info = None
        for key in (abs_key, normalized_key, rel_key):
            if key in files_data:
                file_info = files_data[key]
                break

        if file_info is None:
            # File not in coverage report — could be a test file or not covered.
            logger.debug(
                "Authored file %s not found in coverage report; skipping.",
                authored_rel,
            )
            continue

        files_measured += 1
        executed_lines = file_info.get("executed_lines", [])
        functions = file_info.get("functions", {})
        classes = file_info.get("classes", {})

        # Extract public symbols from the file
        file_path = worktree_path / authored_rel
        symbols = _extract_public_symbols(file_path)

        # Map executed lines to symbols
        symbols = _map_executed_lines_to_symbols(symbols, executed_lines)

        # Also check function-level data from coverage report.
        # Coverage.py's function-level executed_lines only includes body lines
        # (not the def/class header line), which is the correct signal for
        # zero-execution detection. Use this data to update or supplement AST
        # symbols.
        for func_name, func_info in functions.items():
            if not func_name or func_name.startswith("_"):
                continue
            start_line = func_info.get("start_line", 0)
            if start_line > 0:
                sym_executed = func_info.get("executed_lines", [])
                # Check if this is a new symbol not already in AST results
                existing = {s["name"]: s for s in symbols}
                if func_name not in existing:
                    symbols.append({
                        "name": func_name,
                        "lineno": start_line,
                        "end_lineno": start_line,
                        "executed_lines": sym_executed,
                    })
                else:
                    # Update existing AST symbol with coverage report data.
                    # The coverage report's function-level executed_lines is
                    # the authoritative signal (body lines only).
                    existing[func_name]["executed_lines"] = sym_executed

        # Check for zero-execution symbols
        for sym in symbols:
            if not sym["executed_lines"]:
                findings.append(CoverageFinding(
                    file=authored_rel,
                    symbol=sym["name"],
                    lineno=sym["lineno"],
                ))

        # Count files below coverage threshold (using line-level)
        file_summary = file_info.get("summary", {})
        file_pct = file_summary.get("percent_covered", 0.0)
        if file_pct < 100.0 and file_pct >= 0.0:
            files_below += 1

    if files_measured == 0:
        # 12 October 2026. The run measured none of the files this task wrote,
        # so there is nothing for "clean" to be about. It used to say "clean"
        # here, which read as a checked result on a run that checked nothing.
        return _unavailable(
            "absent",
            "coverage ran but measured none of the files this task wrote",
            coverage_percentage=coverage_pct,
        )

    if findings:
        status = "positive"
    else:
        status = "clean"

    return {
        "status": status,
        "findings": [
            {
                "file": f.file,
                "symbol": f.symbol,
                "lineno": f.lineno,
                "executed_lines": f.executed_lines,
                "severity": f.severity,
                "pattern": f.pattern,
            }
            for f in findings
        ],
        "coverage_percentage": coverage_pct,
        "files_below_threshold": files_below,
    }


# ---------------------------------------------------------------------------
# Coverage runner
# ---------------------------------------------------------------------------


#: Files at a project root that say "this is a Python project". Used only for
#: a project that declares its toolchain: there a stray ``*.py`` helper
#: somewhere in the tree does not make it Python (12 October 2026: a
#: TypeScript worktree with one script in it used to get a root pytest run).
_PYTHON_PROJECT_MARKERS = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "pytest.ini",
    "tox.ini",
    "conftest.py",
    "Pipfile",
)
_PYTHON_PROJECT_MARKER_GLOBS = ("requirements*.txt",)


def _is_python_stack(worktree_path: Path, declared: bool = False) -> bool:
    """Check if the worktree (or component directory) is a Python project.

    Parameters
    ----------
    worktree_path : Path
        Root of the worktree, or of the selected component.
    declared : bool, optional
        True when the project declares its toolchain. Only then is a Python
        project marker file at this root required. A project that declares
        nothing keeps the original rule: any ``*.py`` file in the tree.

    Returns
    -------
    bool
        Whether this gate should run pytest here.
    """
    if not declared:
        return any(worktree_path.rglob("*.py"))
    if any((worktree_path / name).is_file() for name in _PYTHON_PROJECT_MARKERS):
        return True
    return any(
        path.is_file()
        for pattern in _PYTHON_PROJECT_MARKER_GLOBS
        for path in worktree_path.glob(pattern)
    )


def _unavailable(
    status: str, reason: str, coverage_percentage: Optional[float] = None
) -> Dict[str, Any]:
    """The block this gate returns when it did not measure the task's code.

    ``findings`` is ``None``, not ``[]``: an empty list is what a run that
    looked and found nothing returns. ``status`` is one of the existing words:
    ``"unsupported_stack"`` when this Python-only gate does not cover the
    task's stack, ``"absent"`` when it could not produce a measurement.
    """
    return {
        "status": status,
        "ran": False,
        "findings": None,
        "reason": reason,
        "coverage_percentage": coverage_percentage,
        "files_below_threshold": None,
    }


def _run_coverage(
    worktree_path: Path,
    authored_files: List[str],
    timeout: int = 300,
    declared: bool = False,
) -> Optional[Dict[str, Any]]:
    """Run pytest under coverage measurement and parse results.

    Parameters
    ----------
    worktree_path : Path
        Root of the worktree.
    authored_files : List[str]
        Authored source files to examine for zero-execution.
    timeout : int, optional
        Timeout in seconds for the coverage run. Default: 300.
    declared : bool, optional
        True when the project declares its toolchain (see
        :func:`_is_python_stack`); only then are authored files other than
        ``*.py`` left out before deciding whether to run.

    Returns
    -------
    Optional[Dict[str, Any]]
        Coverage result dict, or ``None`` when the run fails or the stack
        is not Python (absent signal).
    """
    # Gate: non-Python stack → absent signal
    if not _is_python_stack(worktree_path, declared=declared):
        logger.debug(
            "Coverage gate: non-Python stack detected for %s; "
            "returning absent signal.",
            worktree_path,
        )
        return None

    # Gate: no authored (Python) files → absent signal. In a declared project
    # this gate reads Python source only, so a change with none has nothing
    # here to measure.
    if declared:
        authored_files = [f for f in authored_files if f.endswith(".py")]
    if not authored_files:
        logger.debug(
            "Coverage gate: no authored files for %s; "
            "returning absent signal.",
            worktree_path,
        )
        return None

    # Determine the Python interpreter to use.
    # Prefer the venv Python if available, otherwise fall back to system Python.
    venv_python = None
    venv_path = worktree_path / ".venv" / "bin" / "python"
    if venv_path.exists():
        venv_python = str(venv_path)
    else:
        venv_python = sys.executable

    # Build the coverage command.
    cov_dir = worktree_path / ".cov_output"
    cov_dir.mkdir(exist_ok=True)
    json_report = cov_dir / "coverage.json"

    cmd = [
        venv_python, "-m", "pytest",
        "-v",
        "--tb=short",
        "--cov-report=json",
        f"--cov-report=json:{json_report}",
        "--cov-branch",
        "-p", "no:cacheprovider",
    ]

    # Add cov-source for authored Python files if they're under a known package.
    # We look for a Python package directory within the worktree.
    py_packages = [
        d for d in worktree_path.rglob("*")
        if d.is_dir() and (d / "__init__.py").exists()
    ]
    if py_packages:
        # Use the first top-level package as coverage source.
        src_pkg = py_packages[0].name
        cmd.extend(["--cov", src_pkg])

    logger.info(
        "Coverage gate: running pytest under coverage for %s (timeout=%ds)",
        worktree_path, timeout,
    )

    try:
        # Built from nothing (13 October 2026): the project's tests never
        # see the factory's credentials.
        from guardkit.orchestrator.project_command_env import (
            main_checkout_environment,
        )

        env = main_checkout_environment(Path(worktree_path))
        result = process_group.run_project_command(
            cmd,
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            "Coverage gate: pytest timed out after %ds for %s; "
            "returning absent signal.",
            timeout, worktree_path,
        )
        return None
    except OSError as exc:
        logger.warning(
            "Coverage gate: subprocess error for %s: %s; "
            "returning absent signal.",
            worktree_path, exc,
        )
        return None

    # Exit code 5 = no tests collected. The report, when one was written, is
    # still read: every authored symbol then shows zero execution, which is
    # the finding this gate exists to make.
    if result.returncode not in (0, 5):
        # Other failures: still parse coverage if available, but note the
        # failure. For the gate, a test failure doesn't negate coverage data.
        logger.warning(
            "Coverage gate: pytest exited %d for %s; "
            "still parsing coverage if available.",
            result.returncode, worktree_path,
        )

    # Parse the coverage JSON report.
    if not json_report.exists():
        logger.warning(
            "Coverage gate: coverage JSON report not found at %s; "
            "returning absent signal.",
            json_report,
        )
        return None

    return _parse_coverage_json(json_report, authored_files, worktree_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_coverage_gate(
    worktree_path: Path,
    authored_files: List[str],
    task_type: str,
    timeout: int = 300,
    component: Optional[str] = None,
    component_cwd: Optional[str] = None,
    toolchain_declared: bool = False,
) -> Dict[str, Any]:
    """Run the L3 coverage gate for authored files.

    This is the main entry point for the coverage gate. It runs the worktree
    test suite under coverage measurement and flags every authored public
    symbol with zero real execution.

    Parameters
    ----------
    worktree_path : Path
        Root of the worktree.
    authored_files : List[str]
        Relative paths of source files authored this turn.
    task_type : str
        Task type (e.g. ``"feature"``, ``"refactor"``, ``"scaffolding"``).
    timeout : int, optional
        Timeout in seconds for the coverage run. Default: 300.
    component : str, optional
        The component the task names in the repository's declaration.
    component_cwd : str, optional
        That component's declared, repo-relative directory; ``None`` when the
        task names no component or names one the declaration does not define.
    toolchain_declared : bool, optional
        True when the project declares its toolchain. A project that declares
        nothing keeps this gate's original Python detection, unchanged.

    Returns
    -------
    Dict[str, Any]
        Coverage result dict with keys:
        - ``status``: ``"positive"``, ``"clean"``, or ``"absent"``
        - ``findings``: list of zero-execution findings
        - ``coverage_percentage``: overall line coverage percentage
        - ``files_below_threshold``: number of files below threshold

        Returns ``None`` when the gate legitimately did not run
        (non-Python stack, no authored files).
    """
    # Scope gate: only FEATURE / REFACTOR / INTEGRATION task types.
    if task_type.upper() not in _GATE_TASK_TYPES:
        logger.debug(
            "Coverage gate: task_type=%s gates out; "
            "all fields left as None.",
            task_type,
        )
        return None

    # No authored files → absent signal.
    if not authored_files:
        logger.debug(
            "Coverage gate: no authored files; "
            "returning absent signal.",
        )
        return None

    if not component:
        return _run_coverage(
            worktree_path, authored_files, timeout, declared=toolchain_declared
        )

    # 12 October 2026. A task that names a component is measured in THAT
    # component's directory, never by a root pytest run over the whole
    # repository. A component that is not a Python project is outside what
    # this gate covers, and says so.
    if component_cwd is None:
        return _unavailable(
            "absent",
            f"the task names component {component!r}, which the project's "
            "declaration does not define, so there was nothing to measure",
        )
    prefix = component_cwd.strip("/")
    if prefix in ("", "."):
        prefix = ""
    root = Path(worktree_path) / prefix if prefix else Path(worktree_path)
    if not _is_python_stack(root, declared=True):
        return _unavailable(
            "unsupported_stack",
            f"this coverage check measures Python only, and component "
            f"{component!r} ({component_cwd}) is not a Python project",
        )
    if prefix:
        authored_files = [
            f[len(prefix) + 1:]
            for f in authored_files
            if f.startswith(prefix + "/")
        ]
    result = _run_coverage(root, authored_files, timeout, declared=True)
    if prefix and isinstance(result, dict):
        # Findings name files from the repository root, like every other check.
        for finding in result.get("findings") or []:
            if isinstance(finding, dict) and isinstance(finding.get("file"), str):
                finding["file"] = f"{prefix}/{finding['file']}"
    return result


def run_coverage_gate_for_bundle(
    worktree_path: Path,
    authored_files: List[str],
    task_type: str,
    timeout: int = 300,
    component: Optional[str] = None,
    component_cwd: Optional[str] = None,
    toolchain_declared: bool = False,
) -> Optional[Dict[str, Any]]:
    """Run the coverage gate and return a bundle-compatible dict.

    This is a wrapper around :func:`run_coverage_gate` that returns
    ``None`` (absent signal) when the gate did not run, matching the
    bundle field semantics.

    Parameters
    ----------
    worktree_path : Path
        Root of the worktree.
    authored_files : List[str]
        Relative paths of source files authored this turn.
    task_type : str
        Task type.
    timeout : int, optional
        Timeout in seconds.
    component, component_cwd : str, optional
        The task's declared component and its directory; see
        :func:`run_coverage_gate`.
    toolchain_declared : bool, optional
        Whether the project declares its toolchain; see
        :func:`run_coverage_gate`.

    Returns
    -------
    Optional[Dict[str, Any]]
        Coverage result dict, or ``None`` when absent.
    """
    result = run_coverage_gate(
        worktree_path,
        authored_files,
        task_type,
        timeout,
        component=component,
        component_cwd=component_cwd,
        toolchain_declared=toolchain_declared,
    )
    return result
