"""Tests for TASK-FIX-7A05: Coach pytest interpreter selection.

Covers the AC branches from the task:
  1. Explicit ``venv_python`` param → Coach invokes pytest through it.
  2. No explicit param but a filesystem venv at
     ``<worktree>/.guardkit/venv/bin/python`` → Coach discovers and uses it.
  3. No venv (explicit or filesystem) → Coach preserves the prior PATH
     ``pytest`` behavior (non-Python projects).
  4. Explicit venv path that does not exist → filesystem discovery is
     consulted; when that also fails, fall through to PATH pytest.
  5. Argv-shape integration test asserting the exact command passed to
     ``subprocess.run`` for the bootstrap-venv case.

The changes under test also extend the ``FileNotFoundError`` fallback:
when the resolved venv interpreter disappears mid-run, Coach will NOT
silently fall through to whichever ``python3`` happens to be on PATH —
it retries the resolved venv interpreter only.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.coach_verification import (
    CoachVerifier,
    _resolve_venv_python,
)


# --------------------------------------------------------------------------
# _resolve_venv_python: resolution-order primitive
# --------------------------------------------------------------------------


class TestResolveVenvPython:
    """Tests for the interpreter-resolution helper."""

    def test_explicit_path_when_exists(self, tmp_path: Path) -> None:
        """Explicit param wins when the file exists on disk."""
        fake_python = tmp_path / "my-venv" / "bin" / "python"
        fake_python.parent.mkdir(parents=True)
        fake_python.touch()

        resolved = _resolve_venv_python(tmp_path, explicit=fake_python)

        assert resolved == fake_python

    def test_explicit_path_accepts_string(self, tmp_path: Path) -> None:
        """Explicit param also accepts ``str`` (typical BootstrapResult form)."""
        fake_python = tmp_path / "venv" / "bin" / "python"
        fake_python.parent.mkdir(parents=True)
        fake_python.touch()

        resolved = _resolve_venv_python(tmp_path, explicit=str(fake_python))

        assert resolved == fake_python

    def test_explicit_missing_falls_through_to_filesystem(
        self, tmp_path: Path
    ) -> None:
        """When the explicit path is stale, filesystem discovery runs next."""
        stale_explicit = tmp_path / "stale" / "bin" / "python"  # never created
        fs_python = tmp_path / ".guardkit" / "venv" / "bin" / "python"
        fs_python.parent.mkdir(parents=True)
        fs_python.touch()

        resolved = _resolve_venv_python(tmp_path, explicit=stale_explicit)

        assert resolved == fs_python

    def test_filesystem_fallback_discovered(self, tmp_path: Path) -> None:
        """No explicit param → ``<worktree>/.guardkit/venv/bin/python`` wins."""
        fs_python = tmp_path / ".guardkit" / "venv" / "bin" / "python"
        fs_python.parent.mkdir(parents=True)
        fs_python.touch()

        resolved = _resolve_venv_python(tmp_path, explicit=None)

        assert resolved == fs_python

    def test_no_venv_returns_none(self, tmp_path: Path) -> None:
        """No explicit and no filesystem venv → ``None`` (non-Python project)."""
        resolved = _resolve_venv_python(tmp_path, explicit=None)

        assert resolved is None


# --------------------------------------------------------------------------
# CoachVerifier: end-to-end pytest argv shape
# --------------------------------------------------------------------------


class TestCoachInterpreterSelection:
    """Tests for :class:`CoachVerifier` interpreter-selection behavior."""

    @patch("guardkit.orchestrator.coach_verification.subprocess.run")
    def test_explicit_venv_python_used_in_argv(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """AC: bootstrap venv → Coach uses ``[venv_python, -m, pytest, ...]``."""
        fake_venv = tmp_path / "venv" / "bin" / "python"
        fake_venv.parent.mkdir(parents=True)
        fake_venv.touch()

        mock_run.return_value = MagicMock(returncode=0, stdout="5 passed in 0.1s")

        verifier = CoachVerifier(tmp_path, venv_python=fake_venv)
        verifier._run_tests()

        mock_run.assert_called_once()
        argv = mock_run.call_args[0][0]
        # AC: argv[0] is the bootstrap venv interpreter, and pytest is
        # invoked via ``-m`` (never as a PATH-resolved command).
        assert argv[0] == str(fake_venv)
        assert argv[1] == "-m"
        assert argv[2] == "pytest"
        assert "--tb=no" in argv
        assert "-q" in argv

    @patch("guardkit.orchestrator.coach_verification.subprocess.run")
    def test_filesystem_venv_used_when_no_explicit(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """AC: ``<worktree>/.guardkit/venv/bin/python`` is auto-discovered."""
        fs_python = tmp_path / ".guardkit" / "venv" / "bin" / "python"
        fs_python.parent.mkdir(parents=True)
        fs_python.touch()

        mock_run.return_value = MagicMock(returncode=0, stdout="3 passed")

        verifier = CoachVerifier(tmp_path)  # no explicit venv_python
        verifier._run_tests()

        mock_run.assert_called_once()
        argv = mock_run.call_args[0][0]
        assert argv[0] == str(fs_python)
        assert argv[1:4] == ["-m", "pytest", "--tb=no"]

    @patch("guardkit.orchestrator.coach_verification.subprocess.run")
    def test_no_venv_preserves_path_pytest_behavior(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """AC: non-Python project → argv[0] is still PATH ``pytest``."""
        mock_run.return_value = MagicMock(returncode=0, stdout="5 passed")

        verifier = CoachVerifier(tmp_path)  # no venv anywhere
        verifier._run_tests()

        mock_run.assert_called_once()
        argv = mock_run.call_args[0][0]
        # Prior behavior is preserved: PATH pytest as argv[0].
        assert argv[0] == "pytest"
        assert "--tb=no" in argv
        assert "-q" in argv

    @patch("guardkit.orchestrator.coach_verification.subprocess.run")
    def test_stale_explicit_path_falls_through_to_path_pytest(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Explicit venv that doesn't exist and no filesystem venv →
        preserves PATH ``pytest`` (non-Python project recovery path)."""
        stale = tmp_path / "missing" / "bin" / "python"  # never created
        mock_run.return_value = MagicMock(returncode=0, stdout="5 passed")

        verifier = CoachVerifier(tmp_path, venv_python=stale)
        verifier._run_tests()

        mock_run.assert_called_once()
        argv = mock_run.call_args[0][0]
        assert argv[0] == "pytest"

    @patch("guardkit.orchestrator.coach_verification.subprocess.run")
    def test_argv_shape_with_scoped_paths_bootstrap_venv(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Integration-shaped: bootstrap venv + scoped test paths."""
        fake_venv = tmp_path / "venv" / "bin" / "python"
        fake_venv.parent.mkdir(parents=True)
        fake_venv.touch()

        mock_run.return_value = MagicMock(returncode=0, stdout="2 passed")

        verifier = CoachVerifier(tmp_path, venv_python=fake_venv)
        verifier._run_tests(test_paths=["tests/unit/"])

        mock_run.assert_called_once()
        argv = mock_run.call_args[0][0]
        assert argv == [
            str(fake_venv),
            "-m",
            "pytest",
            "--tb=no",
            "-q",
            "tests/unit/",
        ]

    @patch("guardkit.orchestrator.coach_verification.subprocess.run")
    def test_no_venv_fallback_does_not_silently_use_wrong_interpreter(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """When PATH ``pytest`` is missing, fallback prefers ``sys.executable``.

        Regression lock (TASK-FIX-7A05 F7 root cause): in the no-venv
        branch Coach previously fell through to whichever ``python3`` /
        ``python`` was on PATH, which could silently be a different
        interpreter than the Player's. The new fallback list starts with
        ``sys.executable`` so Coach at least uses the same interpreter
        that's running the orchestrator process.
        """
        # First call simulates PATH pytest being unavailable, second call
        # simulates sys.executable -m pytest succeeding.
        mock_run.side_effect = [
            FileNotFoundError("pytest"),
            MagicMock(returncode=0, stdout="5 passed"),
        ]

        verifier = CoachVerifier(tmp_path)  # no venv
        verifier._run_tests()

        assert mock_run.call_count == 2
        fallback_argv = mock_run.call_args_list[1][0][0]
        assert fallback_argv[0] == sys.executable
        assert fallback_argv[1:4] == ["-m", "pytest", "--tb=no"]


# --------------------------------------------------------------------------
# AgentInvoker → CoachVerifier plumbing
# --------------------------------------------------------------------------


class TestAgentInvokerPlumbing:
    """Verify :class:`AgentInvoker` threads ``venv_python`` into Coach."""

    def test_agent_invoker_passes_venv_python_to_coach(
        self, tmp_path: Path
    ) -> None:
        """AgentInvoker stores ``venv_python`` and passes it into CoachVerifier."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        fake_venv = tmp_path / "venv" / "bin" / "python"
        fake_venv.parent.mkdir(parents=True)
        fake_venv.touch()

        invoker = AgentInvoker(
            worktree_path=tmp_path,
            venv_python=str(fake_venv),
        )

        # Private attribute — the guarantee we're locking in is that the
        # value is threaded into the CoachVerifier constructor at call
        # time. We assert that indirectly below.
        assert invoker._venv_python == str(fake_venv)

        with patch(
            "guardkit.orchestrator.agent_invoker.CoachVerifier"
        ) as mock_verifier_cls:
            mock_verifier_cls.return_value.verify_player_report.return_value = (
                MagicMock(verified=True, discrepancies=[], honesty_score=1.0)
            )

            invoker._verify_player_claims({"tests_run": False})

            mock_verifier_cls.assert_called_once_with(
                tmp_path, venv_python=str(fake_venv)
            )

    def test_agent_invoker_defaults_venv_python_to_none(
        self, tmp_path: Path
    ) -> None:
        """Default ``venv_python=None`` preserves backward compat."""
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        invoker = AgentInvoker(worktree_path=tmp_path)

        assert invoker._venv_python is None


# --------------------------------------------------------------------------
# AutoBuildOrchestrator plumbing
# --------------------------------------------------------------------------


class TestAutoBuildPlumbing:
    """Verify :class:`AutoBuildOrchestrator` stores and surfaces ``venv_python``."""

    def test_autobuild_stores_venv_python(self, tmp_path: Path) -> None:
        """AutoBuildOrchestrator stashes the threaded ``venv_python``."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            enable_context=False,
            worktree_manager=MagicMock(),
            venv_python="/path/to/venv/bin/python",
        )

        assert orchestrator._venv_python == "/path/to/venv/bin/python"

    def test_autobuild_defaults_venv_python_to_none(self, tmp_path: Path) -> None:
        """Default ``venv_python=None`` preserves backward compat."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            enable_context=False,
            worktree_manager=MagicMock(),
        )

        assert orchestrator._venv_python is None
