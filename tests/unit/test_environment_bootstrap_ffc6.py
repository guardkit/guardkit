"""
Tests for TASK-FIX-FF61 (FEAT-FFC6): worktree-venv isolation across all
three Python install paths.

Regression coverage for the leak whereby autobuild's
``environment_bootstrap`` step writes the worktree's editable
``_editable_impl_*.pth`` line into the *parent* project's ``.venv``,
because every install subprocess inherits ``os.environ`` (including
``$VIRTUAL_ENV``) and, on the pip path, uses ``sys.executable`` (which
may itself be the parent venv's python).

Three independent leak vectors covered here:

1. ``["uv", "pip", "install", "-e", "."]`` — leaks via inherited
   ``$VIRTUAL_ENV`` (covered by AC-009).
2. ``["uv", "sync", "--frozen"]`` — leaks via inherited ``$VIRTUAL_ENV``
   in project mode (covered by AC-011).
3. ``[sys.executable, "-m", "pip", "install", "-e", "."]`` — leaks via
   ``sys.executable``'s ``sys.prefix``, **independent of**
   ``$VIRTUAL_ENV`` (covered by AC-010).

Plus AC-012: the ``BootstrapEnvironmentLeakError`` invariant — bootstrap
must refuse to claim success when the captured interpreter lies outside
the worktree root.

See:
    - .claude/reviews/TASK-REV-FFC6-review-report.md
    - .claude/rules/absence-of-failure-is-not-success.md
    - .claude/rules/namespace-hygiene.md

Coverage Target: >=85%
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    BootstrapEnvironmentLeakError,
    DetectedManifest,
    EnvironmentBootstrapper,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_worktree_venv_on_disk(worktree: Path) -> Path:
    """Create a stub <worktree>/.venv/bin/python on disk so the eager
    venv-creation helper takes the idempotent fast path (no subprocess.run
    call to mock-out for the venv-creation step)."""
    venv_bin = worktree / ".venv" / "bin"
    venv_bin.mkdir(parents=True, exist_ok=True)
    venv_python = venv_bin / "python"
    venv_python.write_text("#!/usr/bin/env python\n")
    venv_python.chmod(0o755)
    return venv_python


def _ensure_project_source_dir(worktree: Path) -> None:
    """Create ``<worktree>/x/`` so ``is_project_complete()`` returns True
    for a pyproject.toml that declares ``name = "x"``."""
    (worktree / "x").mkdir(exist_ok=True)


def _make_uv_pip_manifest(worktree: Path) -> DetectedManifest:
    pyproject = worktree / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n'
            '[tool.uv.sources]\nfoo = { path = "../foo" }\n',
            encoding="utf-8",
        )
    _ensure_project_source_dir(worktree)
    return DetectedManifest(
        path=pyproject,
        stack="python",
        is_lock_file=False,
        install_command=["uv", "pip", "install", "-e", "."],
    )


def _make_pip_editable_manifest(worktree: Path) -> DetectedManifest:
    pyproject = worktree / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )
    _ensure_project_source_dir(worktree)
    return DetectedManifest(
        path=pyproject,
        stack="python",
        is_lock_file=False,
        install_command=[sys.executable, "-m", "pip", "install", "-e", "."],
    )


def _make_uv_sync_manifest(worktree: Path) -> DetectedManifest:
    pyproject = worktree / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )
    _ensure_project_source_dir(worktree)
    # Drop a uv.lock so the FD32 row's sentinel (uv.lock present) is hit.
    (worktree / "uv.lock").write_text("", encoding="utf-8")
    return DetectedManifest(
        path=pyproject,
        stack="python",
        is_lock_file=False,
        install_command=["uv", "sync", "--frozen"],
    )


def _make_extras_manifest(worktree: Path) -> DetectedManifest:
    """Simulate TASK-FIX-A7B6's `pip install -e .[dev]` extras shape."""
    pyproject = worktree / "pyproject.toml"
    if not pyproject.exists():
        pyproject.write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )
    _ensure_project_source_dir(worktree)
    return DetectedManifest(
        path=pyproject,
        stack="python",
        is_lock_file=False,
        install_command=[sys.executable, "-m", "pip", "install", "-e", ".[dev]"],
    )


def _python_install_calls(mock_run: MagicMock) -> List[MagicMock]:
    """Return the subprocess.run calls that look like Python installs.

    Excludes venv-creation calls (``uv venv ...`` / ``python -m venv ...``)
    so callers can assert on the install subprocess shape only.
    """
    calls = []
    for call_obj in mock_run.call_args_list:
        cmd = call_obj.args[0] if call_obj.args else call_obj.kwargs.get("args", [])
        if not cmd:
            continue
        # Skip venv-creation calls.
        if cmd[:2] == ["uv", "venv"]:
            continue
        if len(cmd) >= 3 and cmd[1] == "-m" and cmd[2] == "venv":
            continue
        # Heuristic: pip / uv pip / uv sync are install calls; npm/dotnet/etc. aren't.
        if cmd[0] == "uv" or (
            len(cmd) >= 3 and cmd[1] == "-m" and cmd[2] == "pip"
        ):
            calls.append(call_obj)
    return calls


# ---------------------------------------------------------------------------
# AC-009: VIRTUAL_ENV inherited via uv pip install path
# ---------------------------------------------------------------------------


class TestNoLeakWhenVirtualEnvInherited:
    """AC-009 — uv pip install path with inherited parent VIRTUAL_ENV."""

    def test_no_leak_when_VIRTUAL_ENV_inherited(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Inherited ``$VIRTUAL_ENV`` must NOT leak through to the install
        subprocess.

        Setup:
          - Parent venv at ``<tmp>/parent/.venv``.
          - ``$VIRTUAL_ENV`` exported pointing at the parent venv.
          - Worktree at ``<tmp>/worktree`` with pre-created ``.venv``.

        Expected: every captured ``subprocess.run(env=...)`` for a Python
        install command has ``VIRTUAL_ENV`` pointing at
        ``<worktree>/.venv`` — NOT the parent path.
        """
        parent_venv = tmp_path / "parent" / ".venv"
        parent_venv.mkdir(parents=True)
        monkeypatch.setenv("VIRTUAL_ENV", str(parent_venv))

        worktree = tmp_path / "worktree"
        worktree.mkdir()
        _make_worktree_venv_on_disk(worktree)
        manifest = _make_uv_pip_manifest(worktree)

        bootstrapper = EnvironmentBootstrapper(root=worktree)

        install_proc = MagicMock(returncode=0, stdout="installed\n", stderr="")

        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=install_proc,
        ) as mock_run:
            result = bootstrapper.bootstrap([manifest])

        assert result.success is True

        install_calls = _python_install_calls(mock_run)
        assert install_calls, "expected at least one Python install subprocess call"
        for call_obj in install_calls:
            env = call_obj.kwargs.get("env")
            assert env is not None, (
                "Python install subprocess.run call missing env= kwarg "
                "(would inherit parent VIRTUAL_ENV)"
            )
            assert env["VIRTUAL_ENV"] == str(worktree / ".venv"), (
                f"VIRTUAL_ENV leaked: expected {worktree / '.venv'}, "
                f"got {env['VIRTUAL_ENV']}"
            )
            assert env["VIRTUAL_ENV"] != str(parent_venv)


# ---------------------------------------------------------------------------
# AC-010: sys.executable leak via pip-path install command
# ---------------------------------------------------------------------------


class TestNoLeakWhenSysExecutableIsParentVenv:
    """AC-010 — pip-path install must remap ``cmd[0]`` to worktree venv."""

    def test_no_leak_when_sys_executable_is_parent_venv(
        self, tmp_path: Path
    ) -> None:
        """When ``install_command`` starts with ``sys.executable`` (which may
        BE the parent venv's python), bootstrap must remap ``cmd[0]`` to the
        worktree venv's python BEFORE subprocess.run.

        This leak path is independent of ``$VIRTUAL_ENV`` — even with no
        env override, ``sys.executable``'s ``sys.prefix`` decides where the
        editable ``.pth`` lands.
        """
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        _make_worktree_venv_on_disk(worktree)
        manifest = _make_pip_editable_manifest(worktree)

        bootstrapper = EnvironmentBootstrapper(root=worktree)

        install_proc = MagicMock(returncode=0, stdout="installed\n", stderr="")

        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=install_proc,
        ) as mock_run:
            result = bootstrapper.bootstrap([manifest])

        assert result.success is True

        install_calls = _python_install_calls(mock_run)
        assert install_calls, "expected at least one Python install subprocess call"
        worktree_python = str(worktree / ".venv" / "bin" / "python")
        for call_obj in install_calls:
            cmd = call_obj.args[0]
            assert cmd[0] == worktree_python, (
                f"sys.executable leaked: expected {worktree_python}, got {cmd[0]}"
            )
            assert cmd[0] != sys.executable


# ---------------------------------------------------------------------------
# AC-011: VIRTUAL_ENV inherited via uv sync --frozen path
# ---------------------------------------------------------------------------


class TestNoLeakWhenUvSyncPath:
    """AC-011 — uv sync path must override inherited VIRTUAL_ENV."""

    def test_no_leak_when_uv_sync_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``uv sync --frozen`` discovers the venv via ``$VIRTUAL_ENV`` —
        if the parent venv leaks through, ``uv sync`` syncs the parent
        venv and writes the ``.pth`` line there.
        """
        parent_venv = tmp_path / "parent" / ".venv"
        parent_venv.mkdir(parents=True)
        monkeypatch.setenv("VIRTUAL_ENV", str(parent_venv))

        worktree = tmp_path / "worktree"
        worktree.mkdir()
        _make_worktree_venv_on_disk(worktree)
        manifest = _make_uv_sync_manifest(worktree)

        bootstrapper = EnvironmentBootstrapper(root=worktree)

        sync_proc = MagicMock(returncode=0, stdout="synced\n", stderr="")

        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=sync_proc,
        ) as mock_run:
            result = bootstrapper.bootstrap([manifest])

        assert result.success is True

        install_calls = _python_install_calls(mock_run)
        assert install_calls, "expected at least one uv sync subprocess call"
        for call_obj in install_calls:
            env = call_obj.kwargs.get("env")
            assert env is not None, (
                "uv sync subprocess.run call missing env= kwarg "
                "(would inherit parent VIRTUAL_ENV)"
            )
            assert env["VIRTUAL_ENV"] == str(worktree / ".venv"), (
                f"VIRTUAL_ENV leaked: expected {worktree / '.venv'}, "
                f"got {env['VIRTUAL_ENV']}"
            )
            assert env["VIRTUAL_ENV"] != str(parent_venv)
            # PATH should have <worktree>/.venv/bin prepended.
            assert env["PATH"].startswith(
                str(worktree / ".venv" / "bin") + os.pathsep
            )


# ---------------------------------------------------------------------------
# AC-012: invariant raise when install lands outside worktree
# ---------------------------------------------------------------------------


class TestInvariantFailsWhenInstallLandsOutsideWorktree:
    """AC-012 — bootstrap must refuse to claim success when the captured
    interpreter lies outside the worktree root."""

    def test_invariant_fails_when_install_lands_outside_worktree(
        self, tmp_path: Path
    ) -> None:
        """Replaces the false-success block at environment_bootstrap.py:1239-1249.

        Setup the bootstrapper to leave ``self._venv_python`` pointing at a
        path OUTSIDE ``self._root`` after install. Expect
        ``BootstrapEnvironmentLeakError``.
        """
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        _make_worktree_venv_on_disk(worktree)
        manifest = _make_pip_editable_manifest(worktree)

        # Simulate a fictional parent venv outside the worktree.
        parent_venv_python = tmp_path / "parent" / ".venv" / "bin" / "python"
        parent_venv_python.parent.mkdir(parents=True)
        parent_venv_python.write_text("#!/usr/bin/env python\n")
        parent_venv_python.chmod(0o755)

        bootstrapper = EnvironmentBootstrapper(root=worktree)

        install_proc = MagicMock(returncode=0, stdout="installed\n", stderr="")

        # Patch _ensure_worktree_venv to mis-route into the parent venv
        # (simulates an arbitrary post-install code path that overrides
        # self._venv_python with a parent-rooted interpreter — the
        # historical false-success block did exactly this with
        # sys.executable).
        original_run_install = bootstrapper._run_install

        def leaky_run_install(manifest):  # type: ignore[no-untyped-def]
            ok = original_run_install(manifest)
            bootstrapper._venv_python = parent_venv_python
            return ok

        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=install_proc,
        ):
            with patch.object(
                bootstrapper, "_run_install", side_effect=leaky_run_install
            ):
                with pytest.raises(BootstrapEnvironmentLeakError) as exc_info:
                    bootstrapper.bootstrap([manifest])

        assert "outside worktree" in str(exc_info.value)
        assert str(parent_venv_python) in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-020: TASK-FIX-A7B6 sequencing — extras config preserves isolation
# ---------------------------------------------------------------------------


class TestExtrasConfigPreservesIsolation:
    """AC-020 — when A7B6 adds extras to the install command, isolation
    holds (extras land in worktree venv, not parent)."""

    def test_extras_install_uses_worktree_venv(self, tmp_path: Path) -> None:
        """Simulates A7B6's ``pip install -e .[dev]`` shape and asserts
        the worktree-venv remap fires."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        _make_worktree_venv_on_disk(worktree)
        manifest = _make_extras_manifest(worktree)

        bootstrapper = EnvironmentBootstrapper(root=worktree)
        install_proc = MagicMock(returncode=0, stdout="installed\n", stderr="")

        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=install_proc,
        ) as mock_run:
            result = bootstrapper.bootstrap([manifest])

        assert result.success is True

        install_calls = _python_install_calls(mock_run)
        assert install_calls, "expected pip install -e .[dev] to be called"
        worktree_python = str(worktree / ".venv" / "bin" / "python")
        for call_obj in install_calls:
            cmd = call_obj.args[0]
            assert cmd[0] == worktree_python
            # The .[dev] extras suffix is preserved verbatim.
            assert ".[dev]" in cmd
