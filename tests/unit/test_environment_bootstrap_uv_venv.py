"""
Tests for TASK-FIX-AB60: worktree-local venv arrangement for the
``[tool.uv.sources]`` install matrix row.

Covers the gap left by TASK-FIX-F09A2: F09A2 selected
``uv pip install -e .`` for projects declaring ``[tool.uv.sources]`` with
uv on PATH, but did not arrange a venv. uv refuses to install without an
active venv (or ``--system``), so the bootstrap hard-failed on any project
in this row that had no preexisting ``.venv``. AB60 detects uv's stderr
sentinel ("No virtual environment found"), creates ``<cwd>/.venv`` via
``uv venv``, and retries with ``VIRTUAL_ENV`` / ``PATH`` exported.

Coverage Target: >=85%

Test cases (matching AC):
1. uv-sources + no uv.lock + no preexisting venv → first invocation emits
   no-venv error, retry creates ``.venv/``, retry succeeds.
2. uv-sources + no uv.lock + preexisting ``.venv/`` → first invocation
   succeeds (uv discovers the venv), no retry path entered.
3. uv-sources + uv.lock present → still routes to ``uv sync --frozen``
   (FD32 path), retry block does NOT fire (regression guard for FD32).
4. No uv-sources + no uv.lock → still routes to ``pip install -e .``,
   retry block does NOT fire (PEP 668 fallback unaffected).
5. uv-sources branch + uv emits some unrelated error → no retry,
   escalates to the bootstrap-failure-mode gate (regression guard for
   the gate added by TASK-FIX-7A04).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    UV_NO_VENV_SENTINEL,
    DetectedManifest,
    EnvironmentBootstrapper,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_uv_pip_manifest(directory: Path) -> DetectedManifest:
    """Build a manifest matching the ``[tool.uv.sources]`` matrix row."""
    pyproject = directory / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            "[project]\nname = \"x\"\nversion = \"0.1.0\"\n"
            "[tool.uv.sources]\nfoo = { path = \"../foo\" }\n",
            encoding="utf-8",
        )
    return DetectedManifest(
        path=pyproject,
        stack="python",
        is_lock_file=False,
        install_command=["uv", "pip", "install", "-e", "."],
    )


def _make_uv_sync_manifest(directory: Path) -> DetectedManifest:
    """Build a manifest matching the ``uv sync --frozen`` matrix row."""
    pyproject = directory / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            "[project]\nname = \"x\"\nversion = \"0.1.0\"\n",
            encoding="utf-8",
        )
    return DetectedManifest(
        path=pyproject,
        stack="python",
        is_lock_file=False,
        install_command=["uv", "sync", "--frozen"],
    )


def _make_pip_editable_manifest(directory: Path) -> DetectedManifest:
    """Build a manifest matching the plain ``pip install -e .`` matrix row."""
    pyproject = directory / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            "[project]\nname = \"x\"\nversion = \"0.1.0\"\n",
            encoding="utf-8",
        )
    return DetectedManifest(
        path=pyproject,
        stack="python",
        is_lock_file=False,
        install_command=[sys.executable, "-m", "pip", "install", "-e", "."],
    )


def _no_venv_stderr() -> str:
    """Return a realistic stderr fragment containing the uv no-venv sentinel."""
    return (
        "error: " + UV_NO_VENV_SENTINEL + "; run `uv venv` to create an "
        "environment, or pass `--system` to install into a non-virtual "
        "environment\n"
    )


# ---------------------------------------------------------------------------
# TestUvSourcesVenvArrangement
# ---------------------------------------------------------------------------


class TestUvSourcesVenvArrangement:
    """Behavioural tests for the AB60 retry path."""

    # AC test 1
    def test_no_venv_error_triggers_retry_that_creates_venv_and_succeeds(
        self, tmp_path: Path
    ) -> None:
        """First invocation hits no-venv stderr; retry creates .venv and succeeds."""
        m = _make_uv_pip_manifest(tmp_path)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        first_call_stderr = _no_venv_stderr()
        first_proc = MagicMock(returncode=2, stdout="", stderr=first_call_stderr)
        venv_create_proc = MagicMock(returncode=0, stdout="", stderr="")
        retry_proc = MagicMock(returncode=0, stdout="installed\n", stderr="")

        # Sequence of subprocess.run calls:
        #   1. uv pip install -e . (fails with no-venv stderr)
        #   2. uv venv <cwd>/.venv (succeeds — _ensure_uv_venv)
        #   3. uv pip install -e . retry with VIRTUAL_ENV (succeeds)
        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            side_effect=[first_proc, venv_create_proc, retry_proc],
        ) as mock_run:
            assert bootstrapper._run_install(m) is True

        assert mock_run.call_count == 3

        # Call 2 was uv venv with worktree-local target.
        venv_call = mock_run.call_args_list[1]
        assert venv_call.args[0][:2] == ["uv", "venv"]
        assert venv_call.args[0][2] == str(tmp_path / ".venv")

        # Call 3 was the retry with VIRTUAL_ENV / PATH propagated.
        retry_call = mock_run.call_args_list[2]
        assert retry_call.args[0] == ["uv", "pip", "install", "-e", "."]
        retry_env = retry_call.kwargs["env"]
        assert retry_env["VIRTUAL_ENV"] == str(tmp_path / ".venv")
        assert retry_env["PATH"].startswith(str(tmp_path / ".venv" / "bin") + os.pathsep)

        # Cache populated so a second call inside the same bootstrap pass
        # does not re-create.
        assert bootstrapper._uv_venv_python == tmp_path / ".venv" / "bin" / "python"

    # AC test 2
    def test_preexisting_venv_succeeds_without_retry(self, tmp_path: Path) -> None:
        """First invocation succeeds when uv already discovers .venv; no retry path."""
        m = _make_uv_pip_manifest(tmp_path)
        # Simulate a preexisting venv (uv discovers it, exit code 0).
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python").write_text("#!/usr/bin/env python\n")
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        first_proc = MagicMock(returncode=0, stdout="installed\n", stderr="")

        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=first_proc,
        ) as mock_run:
            assert bootstrapper._run_install(m) is True

        # Only the original call — no uv venv invocation, no retry.
        assert mock_run.call_count == 1
        # Cache untouched.
        assert bootstrapper._uv_venv_python is None

    # AC test 3 (FD32 regression guard)
    def test_uv_sync_lockfile_path_does_not_enter_retry(self, tmp_path: Path) -> None:
        """uv sync --frozen failures must NOT trigger the AB60 retry block."""
        m = _make_uv_sync_manifest(tmp_path)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        # Even if uv sync's stderr accidentally contained the sentinel
        # substring, AB60's gate must reject it because cmd[1:3] != ["pip",
        # "install"].
        sync_stderr = "error: " + UV_NO_VENV_SENTINEL + " (FD32 row)\n"
        sync_proc = MagicMock(returncode=2, stdout="", stderr=sync_stderr)

        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=sync_proc,
        ) as mock_run:
            assert bootstrapper._run_install(m) is False

        assert mock_run.call_count == 1  # no retry
        assert bootstrapper._uv_venv_python is None

    # AC test 4 (PEP 668 fallback regression guard)
    def test_pip_editable_path_unaffected(self, tmp_path: Path) -> None:
        """Plain pip install -e . path must NOT enter AB60 retry, only PEP 668."""
        m = _make_pip_editable_manifest(tmp_path)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        # pip emits the PEP 668 sentinel; the no-venv sentinel is not
        # present. AB60's gate must not fire even by accident.
        pep668_stderr = "error: externally-managed-environment\n"
        pip_proc = MagicMock(returncode=1, stdout="", stderr=pep668_stderr)
        venv_create_proc = MagicMock(returncode=0, stdout="", stderr="")
        retry_proc = MagicMock(returncode=0, stdout="installed\n", stderr="")

        # Sequence: pip → python -m venv → pip retry. (PEP 668 path uses
        # ``sys.executable -m venv``, not ``uv venv``.)
        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            side_effect=[pip_proc, venv_create_proc, retry_proc],
        ) as mock_run:
            assert bootstrapper._run_install(m) is True

        # PEP 668 path engaged — _venv_python set, _uv_venv_python untouched.
        assert bootstrapper._venv_python is not None
        assert bootstrapper._uv_venv_python is None
        # Venv created at <root>/.guardkit/venv/, NOT <cwd>/.venv.
        venv_call = mock_run.call_args_list[1]
        assert venv_call.args[0] == [
            sys.executable,
            "-m",
            "venv",
            str(tmp_path / ".guardkit" / "venv"),
        ]

    # AC test 5 (7A04 hard-fail gate regression guard)
    def test_unrelated_uv_error_does_not_retry(self, tmp_path: Path) -> None:
        """Unrelated uv errors must NOT trigger retry; failure surfaces normally."""
        m = _make_uv_pip_manifest(tmp_path)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        # An unrelated uv error: missing wheel in lockfile, network error,
        # parse failure, etc. The sentinel must not appear in stderr.
        unrelated_stderr = (
            "error: distribution `foo @ git+ssh://git@example/foo` cannot be "
            "resolved (network error)\n"
        )
        proc = MagicMock(returncode=2, stdout="", stderr=unrelated_stderr)

        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=proc,
        ) as mock_run:
            assert bootstrapper._run_install(m) is False

        # No retry — only the original failed call.
        assert mock_run.call_count == 1
        # Failure detail captured for the hard-fail gate to surface.
        assert "network error" in bootstrapper._last_failure_stderr
        assert bootstrapper._uv_venv_python is None
        # Not a PEP 668 failure either.
        assert bootstrapper._last_failure_is_pep668 is False


# ---------------------------------------------------------------------------
# TestUvVenvHelpers — direct coverage of _ensure_uv_venv / _is_uv_no_venv_error
# ---------------------------------------------------------------------------


class TestUvVenvHelpers:
    """Direct unit tests for the AB60 helpers."""

    def test_is_uv_no_venv_error_matches_sentinel(self, tmp_path: Path) -> None:
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        assert bootstrapper._is_uv_no_venv_error(_no_venv_stderr()) is True
        assert bootstrapper._is_uv_no_venv_error("") is False
        assert bootstrapper._is_uv_no_venv_error("some other error\n") is False

    def test_ensure_uv_venv_idempotent_when_python_exists(
        self, tmp_path: Path
    ) -> None:
        """If <cwd>/.venv/bin/python exists, no uv venv subprocess fires."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python").write_text("#!/usr/bin/env python\n")

        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run"
        ) as mock_run:
            result = bootstrapper._ensure_uv_venv(tmp_path)

        mock_run.assert_not_called()
        assert result == tmp_path / ".venv"
        assert bootstrapper._uv_venv_python == tmp_path / ".venv" / "bin" / "python"

    def test_ensure_uv_venv_caches_result(self, tmp_path: Path) -> None:
        """Second call returns cached path without invoking uv venv again."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        # First call — venv does not exist; uv venv would be invoked.
        venv_create = MagicMock(returncode=0, stdout="", stderr="")
        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=venv_create,
        ) as mock_run:
            first = bootstrapper._ensure_uv_venv(tmp_path)
        assert mock_run.call_count == 1
        assert first == tmp_path / ".venv"

        # Second call — cached, no subprocess.
        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run"
        ) as mock_run:
            second = bootstrapper._ensure_uv_venv(tmp_path)
        mock_run.assert_not_called()
        assert second == tmp_path / ".venv"

    def test_uv_venv_creation_failure_is_caught_and_surfaces_failure_detail(
        self, tmp_path: Path
    ) -> None:
        """If uv venv itself fails, _run_install records it and returns False."""
        m = _make_uv_pip_manifest(tmp_path)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        first_proc = MagicMock(returncode=2, stdout="", stderr=_no_venv_stderr())
        # uv venv fails (e.g., no permission to create .venv).
        venv_failure = subprocess.CalledProcessError(
            returncode=1, cmd=["uv", "venv"], stderr="permission denied\n"
        )

        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            side_effect=[first_proc, venv_failure],
        ) as mock_run:
            assert bootstrapper._run_install(m) is False

        assert mock_run.call_count == 2
        # Failure detail mentions the venv-creation failure specifically,
        # not just the original uv stderr — distinguishes this hard-fail
        # from the bootstrap_failure_mode escape hatch case.
        assert "uv venv creation failed" in bootstrapper._last_failure_stderr
        assert bootstrapper._uv_venv_python is None
