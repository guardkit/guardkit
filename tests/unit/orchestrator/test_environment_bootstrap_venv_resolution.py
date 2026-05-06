"""Bootstrap venv-resolution contract (TASK-SGER-002).

Pins the contract that ``EnvironmentBootstrapper.bootstrap()`` returns a
non-None ``venv_python`` after any successful Python install path:

  * worktree-local venv at ``<root>/.guardkit/venv/bin/python`` when the
    PEP 668 fallback fired (existing behaviour, regression guard);
  * orchestrator's ``sys.executable`` when the install ran first-try against
    the parent shell venv (new behaviour, the macOS uv happy path that bit
    FEAT-61F1).

When bootstrap was skipped (hash match, or non-Python project), existing
behaviour is preserved — ``venv_python`` may still be None.

Coverage Target: >=85%
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    PEP668_SENTINEL,
    BootstrapResult,
    DetectedManifest,
    EnvironmentBootstrapper,
)


def _python_manifest(
    path: Path,
    install_command: List[str] | None = None,
) -> DetectedManifest:
    """Make a Python ``DetectedManifest`` for test use."""
    if install_command is None:
        install_command = [sys.executable, "-m", "pip", "install", "-e", "."]
    return DetectedManifest(
        path=path,
        stack="python",
        is_lock_file=False,
        install_command=install_command,
    )


def _node_manifest(path: Path) -> DetectedManifest:
    """Make a Node ``DetectedManifest`` for test use."""
    return DetectedManifest(
        path=path,
        stack="node",
        is_lock_file=False,
        install_command=["npm", "install"],
    )


# ============================================================================
# Parent-venv happy path (the FEAT-61F1 fix)
# ============================================================================


class TestParentVenvFallback:
    """Tests for the macOS happy path: ``uv pip install`` succeeds first
    try against the orchestrator's parent shell venv. Pre-fix,
    ``self._venv_python`` stayed None and the smoke gate inherited
    unchanged PATH. Post-fix, ``result.venv_python == sys.executable``.
    """

    def test_parent_venv_install_sets_sys_executable(self, tmp_path: Path) -> None:
        """A first-try Python install success records sys.executable."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = _python_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result = bootstrapper.bootstrap([m])

        assert result.success is True
        assert result.skipped is False
        assert result.venv_python == sys.executable, (
            "After a successful first-try Python install (parent-venv path), "
            "result.venv_python must equal sys.executable so the smoke gate "
            "PATH-prepend fires against the same interpreter that ran the "
            "install."
        )

    def test_parent_venv_install_persists_to_state_file(
        self, tmp_path: Path
    ) -> None:
        """The captured sys.executable is persisted to bootstrap_state.json
        so a subsequent ``--resume`` (hash match) returns the same venv."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = _python_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            bootstrapper.bootstrap([m])

        state_file = tmp_path / ".guardkit" / "bootstrap_state.json"
        assert state_file.exists()
        state = json.loads(state_file.read_text())
        assert state.get("venv_python") == sys.executable

    def test_parent_venv_install_uv_command_also_sets_sys_executable(
        self, tmp_path: Path
    ) -> None:
        """``uv pip install`` (cmd[0] != sys.executable) also records the
        orchestrator's interpreter on first-try success — the package is
        installed against $VIRTUAL_ENV which is the orchestrator's venv."""
        f = tmp_path / "pyproject.toml"
        f.write_text("[project]\nname = 'pkg'\n")
        m = _python_manifest(f, install_command=["uv", "pip", "install", "-e", "."])
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result = bootstrapper.bootstrap([m])

        assert result.success is True
        assert result.venv_python == sys.executable


# ============================================================================
# PEP 668 path (existing behaviour, regression guard)
# ============================================================================


class TestPep668PathRegressionGuard:
    """The PEP 668 fallback path was the only path that previously set
    ``self._venv_python``. After TASK-SGER-002, that path must continue to
    point ``result.venv_python`` at the worktree-local venv (NOT clobbered
    by a later ``sys.executable`` assignment)."""

    def test_pep668_fallback_uses_worktree_local_venv(self, tmp_path: Path) -> None:
        """A PEP 668 fallback creates ``<root>/.guardkit/venv/`` and the
        bootstrapper records that interpreter on the result, not
        sys.executable."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = _python_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        # First subprocess.run call: install fails with PEP 668 sentinel.
        # Second call: ``python -m venv``. Third call: pip retry succeeds.
        first_proc = Mock(
            returncode=1,
            stdout="",
            stderr=f"error: {PEP668_SENTINEL}\n",
        )
        venv_create_proc = Mock(returncode=0, stdout="", stderr="")
        retry_proc = Mock(returncode=0, stdout="", stderr="")

        # Materialise the venv python so _ensure_venv's path semantics work.
        venv_python = tmp_path / ".guardkit" / "venv" / "bin" / "python"

        def _fake_run(*args, **kwargs):
            # First call: install attempt (returns PEP 668 error).
            # Subsequent calls don't matter for this assertion path.
            cmd = args[0] if args else kwargs.get("args")
            if cmd and "venv" in cmd:
                # python -m venv — materialise the dir + python so
                # _ensure_venv's existence check sees it next time.
                venv_python.parent.mkdir(parents=True, exist_ok=True)
                venv_python.touch()
                return venv_create_proc
            # First install: PEP 668 fail. Retry install: success.
            if not _fake_run.first_install_done:
                _fake_run.first_install_done = True
                return first_proc
            return retry_proc

        _fake_run.first_install_done = False  # type: ignore[attr-defined]

        with patch("subprocess.run", side_effect=_fake_run):
            result = bootstrapper.bootstrap([m])

        assert result.success is True
        assert result.venv_python is not None
        assert result.venv_python.endswith(".guardkit/venv/bin/python"), (
            f"PEP 668 path must point venv_python at <root>/.guardkit/venv/"
            f"bin/python, not sys.executable. Got: {result.venv_python}"
        )
        # Defence-in-depth: it MUST NOT have been overwritten with
        # sys.executable by the new TASK-SGER-002 fallback block.
        assert result.venv_python != sys.executable


# ============================================================================
# Skipped paths (preserve existing behaviour per AC #2)
# ============================================================================


class TestSkippedBootstrap:
    """When ``bootstrap()`` skips because content hash matched saved state,
    or because the project has no Python manifests, ``result.venv_python``
    must reflect existing behaviour (not be coerced to sys.executable)."""

    def test_hash_match_preserves_saved_venv_python(self, tmp_path: Path) -> None:
        """Hash-match-skip returns whatever was saved — including sys.executable
        from a previous successful run."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = _python_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        # First run records sys.executable.
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            first = bootstrapper.bootstrap([m])
        assert first.venv_python == sys.executable

        # Second run hits hash match → returns saved venv_python unchanged.
        bootstrapper2 = EnvironmentBootstrapper(root=tmp_path)
        with patch("subprocess.run") as mock_run:
            second = bootstrapper2.bootstrap([m])
        mock_run.assert_not_called()
        assert second.skipped is True
        assert second.venv_python == sys.executable

    def test_hash_match_with_no_saved_venv_returns_none(
        self, tmp_path: Path
    ) -> None:
        """Old state files (pre-TASK-SGER-002) without a venv_python field
        must continue to skip-with-None — preserve existing behaviour per
        AC #2. (Users with stale state can re-bootstrap by deleting
        ``.guardkit/bootstrap_state.json``.)"""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = _python_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        h = bootstrapper._compute_hash([m])
        # Save state in the pre-fix shape (no venv_python field).
        state_file = tmp_path / ".guardkit" / "bootstrap_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(
            json.dumps(
                {
                    "content_hash": h,
                    "success": True,
                    "timestamp": "2026-05-06T00:00:00",
                    # NOTE: no venv_python — pre-TASK-SGER-002 shape.
                }
            )
        )

        with patch("subprocess.run") as mock_run:
            result = bootstrapper.bootstrap([m])
        mock_run.assert_not_called()
        assert result.skipped is True
        assert result.venv_python is None

    def test_non_python_project_returns_none(self, tmp_path: Path) -> None:
        """Pure-node bootstrap leaves venv_python as None — no Python
        install ran, so claiming an interpreter would be meaningless."""
        pkg = tmp_path / "package.json"
        pkg.write_text('{"name": "x", "version": "0.0.1"}')
        m = _node_manifest(pkg)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result = bootstrapper.bootstrap([m])

        assert result.success is True
        assert result.venv_python is None

    def test_empty_manifests_returns_none(self, tmp_path: Path) -> None:
        """No manifests → no install ran → venv_python is None."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        result = bootstrapper.bootstrap([])
        assert result.success is True
        assert result.venv_python is None

    def test_failed_python_install_does_not_set_venv_python(
        self, tmp_path: Path
    ) -> None:
        """A failed Python install must NOT set venv_python — claiming an
        interpreter when no install succeeded would mislead downstream
        smoke gates into running against a broken env."""
        f = tmp_path / "requirements.txt"
        f.write_text("flask\n")
        m = _python_manifest(f)
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)

        mock_result = Mock(returncode=1, stdout="", stderr="generic install error")
        with patch("subprocess.run", return_value=mock_result):
            result = bootstrapper.bootstrap([m])

        assert result.success is False
        assert result.venv_python is None


# ============================================================================
# Mixed-stack scenarios
# ============================================================================


class TestMixedStacks:
    """When manifests span multiple stacks, ``venv_python`` should reflect
    the Python interpreter only when a Python install actually succeeded."""

    def test_python_plus_node_success_sets_sys_executable(
        self, tmp_path: Path
    ) -> None:
        """Python + Node both succeed → venv_python = sys.executable."""
        py = tmp_path / "requirements.txt"
        py.write_text("flask\n")
        node = tmp_path / "package.json"
        node.write_text('{"name": "x", "version": "0.0.1"}')

        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        mock_result = Mock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result = bootstrapper.bootstrap(
                [_python_manifest(py), _node_manifest(node)]
            )

        assert result.success is True
        assert result.venv_python == sys.executable
