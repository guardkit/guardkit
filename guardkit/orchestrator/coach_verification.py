"""The worktree interpreter, and a plain test run under it.

``_resolve_venv_python`` finds the interpreter the project's tests run under;
``CoachVerifier._run_tests`` runs them for state recovery. (27 October 2026: the
checks of the Player's claims that lived here were removed.)
"""

import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import (
    List,
    Optional,
    Union,
)

from guardkit.orchestrator.environment_bootstrap import probe_worktree_venv
from guardkit.orchestrator import process_group

logger = logging.getLogger(__name__)


# Manifest names that mark a worktree as a Python project for the loud
# no-venv fallback WARNING (TASK-AB-RESUMEVENV01 AC-003). Deliberately the
# same root-level names ProjectEnvironmentDetector treats as Python stack
# manifests — a match means "pytest against sys.executable will almost
# certainly miss the project's deps".
_PYTHON_PROJECT_MARKERS = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
)


class InterpreterResolutionError(RuntimeError):
    """No worktree venv interpreter resolved for a Python-project worktree
    *inside an autobuild run*.

    Q1 SPLIT posture (WS3-S1, decided by Rich 2026-07-09 — see WS3 §7): the
    shipped behaviour logged one WARNING and fell back to ``sys.executable``,
    which kept runs alive but is exactly the soft-fail shape that hid DD4F's
    TypeError. A wrong interpreter poisons **every** downstream Coach verdict
    (pytest collects 0 tests -> an absent signal that reads like a quality
    rejection, FEAT-ABL-005 run 4). So resolution failure is now a HARD-ABORT
    when ``in_autobuild_context=True`` — the run fails loud and the operator
    fixes the environment rather than the orchestrator silently mis-verdicting.

    The split is EXPLICIT (the ``in_autobuild_context`` flag), not a heuristic:
    interactive CLI use (the default, ``False``) keeps the WARNING +
    ``sys.executable`` fallback so a developer's ad-hoc invocation is not
    aborted.
    """


def _resolve_venv_python(
    worktree_path: Path,
    explicit: Optional[Union[str, Path]],
    *,
    in_autobuild_context: bool = False,
) -> Optional[Path]:
    """Resolve the Python interpreter Coach should use for pytest.

    Resolution order (AC-TASK-FIX-7A05, extended by TASK-AB-RESUMEVENV01):
      1. Explicit path passed by the orchestrator (typically from
         BootstrapResult.venv_python).
      2. ``<worktree>/.venv/bin/python`` when it exists on disk — the
         current bootstrap layout (FFC6 eager worktree venv; recovery path
         when the explicit param wasn't threaded through, e.g. the
         ``--resume`` hash-match skip).
      3. ``<worktree>/.guardkit/venv/bin/python`` when it exists on disk —
         the legacy PEP 668 fallback layout (old worktrees exist).
      4. For a PYTHON project worktree that resolved nothing, the split
         posture (Q1, WS3-S1) applies:
           * ``in_autobuild_context=True`` -> raise
             :class:`InterpreterResolutionError` (HARD-ABORT — a wrong
             interpreter poisons every downstream Coach verdict; the
             DD4F-shaped soft-fail closes).
           * ``in_autobuild_context=False`` (interactive CLI, the default) ->
             log ONE WARNING naming the probed locations and the interpreter
             the caller will fall back to, then return None (warn-and-fallback
             preserved).
      5. For a non-Python project, return None either way (the caller's
         PATH ``pytest`` / ``sys.executable`` behaviour is correct — there is
         no project venv to miss).

    Args:
        worktree_path: The worktree whose venv is being resolved.
        explicit: An explicit interpreter path (typically
            ``BootstrapResult.venv_python``); wins when it exists on disk.
        in_autobuild_context: When True, a Python-project resolution failure
            is a HARD-ABORT (raises :class:`InterpreterResolutionError`)
            instead of warn-and-fallback. Set True ONLY by autobuild
            orchestrator call sites (Coach verdict paths). The interactive
            default (False) keeps the shipped warn-and-fallback behaviour.

    Raises:
        InterpreterResolutionError: Python-project worktree, no interpreter
            resolved, and ``in_autobuild_context=True``.
    """
    if explicit:
        candidate = Path(explicit)
        if candidate.exists():
            return candidate
        logger.debug(
            "CoachVerifier: explicit venv_python %s does not exist — "
            "falling through to filesystem discovery",
            candidate,
        )

    filesystem = probe_worktree_venv(worktree_path)
    if filesystem is not None:
        return filesystem

    # TASK-AB-RESUMEVENV01 (AC-003): no silent sys.executable fallback for a
    # Python project. The caller will run pytest under the ORCHESTRATOR'S own
    # interpreter, which almost certainly lacks the target project's deps —
    # pytest then collects 0 tests and every turn records an absent signal
    # that looks exactly like a quality rejection (FEAT-ABL-005 run 4).
    is_python_project = any(
        (worktree_path / marker).exists() for marker in _PYTHON_PROJECT_MARKERS
    )
    if is_python_project:
        probed_venv = worktree_path / ".venv" / "bin" / "python"
        probed_legacy = worktree_path / ".guardkit" / "venv" / "bin" / "python"
        if in_autobuild_context:
            # Q1 SPLIT (WS3-S1, Rich 2026-07-09): HARD-ABORT inside autobuild.
            # The remediation is named so the operator fixes the environment,
            # not the (poisoned) verdict.
            raise InterpreterResolutionError(
                "Autobuild interpreter-resolution FAILED for Python project at "
                f"{worktree_path}: no worktree venv interpreter resolved "
                f"(explicit={explicit}; probed {probed_venv} and "
                f"{probed_legacy}). Inside an autobuild run this is a "
                "HARD-ABORT (Q1 SPLIT, WS3-S1) — falling back to the "
                "orchestrator's own interpreter would poison every downstream "
                "Coach verdict (pytest collects 0 tests, the DD4F-shaped "
                "soft-fail). Remediation: re-run environment bootstrap so the "
                f"worktree venv exists (verify {probed_venv} was created, or "
                "delete the worktree and re-run the autobuild), or thread an "
                "explicit venv_python through. Interactive CLI use keeps the "
                "warn-and-fallback behaviour."
            )
        logger.warning(
            "TASK-AB-RESUMEVENV01: no worktree venv interpreter resolved for "
            "Python project at %s — probed %s and %s (explicit=%s). Callers "
            "will fall back to %s (the orchestrator's own interpreter), which "
            "likely lacks the project's deps; check the worktree venv or "
            "re-run environment bootstrap.",
            worktree_path,
            probed_venv,
            probed_legacy,
            explicit,
            sys.executable,
        )

    return None


@dataclass
class TestResult:
    """Result of running tests.

    Attributes:
        passed: Whether all tests passed
        test_count: Number of tests that passed
        output: Raw test output
    """

    passed: bool
    test_count: int
    output: str


class CoachVerifier:
    """Runs a worktree's tests under the worktree's own interpreter.

    Used by state recovery (``state_detection``) to see whether a turn that left
    no report left passing tests.
    """

    def __init__(
        self,
        worktree_path: Path,
        venv_python: Optional[Union[str, Path]] = None,
        in_autobuild_context: bool = False,
    ):
        self.worktree_path = Path(worktree_path)
        self._cached_test_result: Optional[TestResult] = None
        self._venv_python: Optional[Path] = _resolve_venv_python(
            self.worktree_path,
            venv_python,
            in_autobuild_context=in_autobuild_context,
        )

    def _run_tests(self, test_paths: list[str] | None = None, timeout: int = 120) -> TestResult:
        """Run tests in worktree and return result.

        Uses caching to avoid running tests multiple times in the same
        verification session. Caching is only used for unscoped runs.

        Args:
            test_paths: Optional list of test file/directory paths to scope
                the test run. When provided, pytest runs only against these
                paths instead of the entire worktree.
            timeout: Timeout in seconds for test execution. Default 120.
                Use higher values (e.g. 300) for state recovery contexts
                where parallel load may cause slower execution.

        Returns:
            TestResult with execution results
        """
        # Return cached result if available (only for unscoped runs)
        if test_paths is None and self._cached_test_result is not None:
            return self._cached_test_result

        # Build base pytest command. When a venv interpreter is known
        # (explicit param or discovered via _resolve_venv_python), invoke
        # pytest through it so Coach verifies against the same interpreter
        # the bootstrap produced (AC-TASK-FIX-7A05).
        if self._venv_python is not None:
            cmd = [str(self._venv_python), "-m", "pytest", "--tb=no", "-q"]
        else:
            cmd = ["pytest", "--tb=no", "-q"]
        if test_paths:
            cmd.extend(test_paths)

        # Detect test framework and run appropriate command
        try:
            # Built from nothing (13 October 2026): the project's tests never
            # see the factory's credentials.
            from guardkit.orchestrator.project_command_env import (
                main_checkout_environment,
            )

            env = main_checkout_environment(Path(self.worktree_path))
            result = process_group.run_project_command(
                cmd,
                cwd=self.worktree_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            test_result = TestResult(
                passed=result.returncode == 0,
                test_count=self._parse_pytest_count(result.stdout),
                output=result.stdout,
            )
        except process_group.CleanupUnavailableError:
            raise
        except FileNotFoundError:
            logger.warning("pytest not found, trying python -m pytest")
            test_result = None
            # When a venv interpreter was resolved but missing at run time,
            # skip the PATH fallback — it would silently validate against
            # the wrong interpreter (the exact bug TASK-FIX-7A05 closes).
            fallback_interpreters: List[str] = (
                [str(self._venv_python)] if self._venv_python is not None
                else [sys.executable, "python3", "python"]
            )
            for python_cmd in fallback_interpreters:
                try:
                    fallback_cmd = [python_cmd, "-m", "pytest", "--tb=no", "-q"]
                    if test_paths:
                        fallback_cmd.extend(test_paths)
                    result = process_group.run_project_command(
                        fallback_cmd,
                        cwd=self.worktree_path,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        env=env,
                    )
                    test_result = TestResult(
                        passed=result.returncode == 0,
                        test_count=self._parse_pytest_count(result.stdout),
                        output=result.stdout,
                    )
                    break
                except process_group.CleanupUnavailableError:
                    raise
                except FileNotFoundError:
                    continue
            if test_result is None:
                logger.error(
                    "Failed to run tests: no usable Python interpreter found "
                    "(tried: %s)",
                    ", ".join(fallback_interpreters),
                )
                test_result = TestResult(passed=False, test_count=0, output="")
        except subprocess.TimeoutExpired:
            logger.error(f"Test execution timed out after {timeout}s")
            test_result = TestResult(
                passed=False, test_count=0, output="Test execution timed out"
            )
        except Exception as e:
            logger.error(f"Failed to run tests: {e}")
            test_result = TestResult(
                passed=False, test_count=0, output=str(e)
            )

        # Only cache unscoped runs
        if test_paths is None:
            self._cached_test_result = test_result

        return test_result

    def _extract_test_count(self, summary: str) -> Optional[int]:
        """Extract test count from summary string.

        Args:
            summary: Test output summary string (e.g., "5 passed in 0.23s")

        Returns:
            Number of passed tests, or None if not parseable
        """
        match = re.search(r"(\d+)\s+passed", summary)
        return int(match.group(1)) if match else None

    def _parse_pytest_count(self, output: str) -> int:
        """Parse test count from pytest output.

        Args:
            output: Raw pytest output

        Returns:
            Number of passed tests
        """
        match = re.search(r"(\d+)\s+passed", output)
        return int(match.group(1)) if match else 0

__all__ = [
    "CoachVerifier",
    "InterpreterResolutionError",
    "TestResult",
    "_resolve_venv_python",
]
