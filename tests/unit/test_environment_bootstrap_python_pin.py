"""
Tests for TASK-AB-BOOTPY01: pin ``uv venv`` interpreter to ``requires-python``.

FEAT-MEM-01 Error 1 (Python 3.10 bootstrap trap): ``uv venv`` was invoked with
no ``--python`` flag, so on a host whose default uv-managed interpreter is
cpython-3.10 the worktree venv was built on 3.10, hard-failing a project that
declares ``requires-python >=3.12``. This suite covers the fix that threads the
manifest's ``requires-python`` into the ``uv venv`` interpreter selection for
both creation sites (``_ensure_worktree_venv`` eager path and ``_ensure_uv_venv``
AB60 retry path), plus the pure ``_uv_python_request`` mapping helper.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    DetectedManifest,
    EnvironmentBootstrapper,
    _uv_python_request,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_python_manifest(
    directory: Path, requires_python: str | None
) -> DetectedManifest:
    """Write a pyproject.toml (optionally declaring requires-python)."""
    pyproject = directory / "pyproject.toml"
    body = '[project]\nname = "x"\nversion = "0.1.0"\n'
    if requires_python is not None:
        body += f'requires-python = "{requires_python}"\n'
    body += '[tool.uv.sources]\nfoo = { path = "../foo" }\n'
    pyproject.write_text(body, encoding="utf-8")
    return DetectedManifest(
        path=pyproject,
        stack="python",
        is_lock_file=False,
        install_command=["uv", "pip", "install", "-e", "."],
    )


def _venv_cmd(mock_run: MagicMock) -> list:
    """Return the argv of the single subprocess.run (uv venv) call."""
    assert mock_run.call_count == 1
    return list(mock_run.call_args[0][0])


# ---------------------------------------------------------------------------
# _uv_python_request — pure mapping helper
# ---------------------------------------------------------------------------


class TestUvPythonRequest:
    @pytest.mark.parametrize(
        ("requires_python", "expected"),
        [
            (">=3.12", "3.12"),
            (">=3.12,<4.0", "3.12"),
            (">=3.9,<4.0", "3.9"),
            ("^3.11", "3.11"),
            ("~=3.10", "3.10"),
            (">=3.13", "3.13"),
            ("==3.12.*", "3.12"),
        ],
    )
    def test_maps_lower_bound(self, requires_python: str, expected: str) -> None:
        assert _uv_python_request(requires_python) == expected

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_absent_returns_none(self, value) -> None:
        assert _uv_python_request(value) is None

    def test_unparseable_returns_none(self) -> None:
        # No major.minor token anywhere → fall back to uv default.
        assert _uv_python_request(">=3") is None
        assert _uv_python_request("not-a-version") is None

    def test_excludes_310_for_modern_floor(self) -> None:
        """AC: a >=3.12 floor must never resolve to 3.10."""
        assert _uv_python_request(">=3.12") != "3.10"


# ---------------------------------------------------------------------------
# _ensure_worktree_venv — eager creation path
# ---------------------------------------------------------------------------


class TestEnsureWorktreeVenvPython:
    def test_pins_python_from_requires_python(self, tmp_path: Path) -> None:
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch(
            "guardkit.orchestrator.environment_bootstrap._uv_on_path",
            return_value=True,
        ), patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="", stderr=""),
        ) as mock_run:
            bootstrapper._ensure_worktree_venv(tmp_path, ">=3.12")

        cmd = _venv_cmd(mock_run)
        assert cmd[:2] == ["uv", "venv"]
        assert "--seed" in cmd
        assert "--python" in cmd
        assert cmd[cmd.index("--python") + 1] == "3.12"
        # AC: the call must exclude 3.10.
        assert "3.10" not in cmd

    def test_no_python_flag_when_constraint_absent(self, tmp_path: Path) -> None:
        """AC: requires-python absent → behaviour unchanged (no --python)."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch(
            "guardkit.orchestrator.environment_bootstrap._uv_on_path",
            return_value=True,
        ), patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="", stderr=""),
        ) as mock_run:
            bootstrapper._ensure_worktree_venv(tmp_path, None)

        cmd = _venv_cmd(mock_run)
        assert cmd == ["uv", "venv", "--seed", str(tmp_path / ".venv")]
        assert "--python" not in cmd

    def test_python_m_venv_fallback_ignores_constraint(
        self, tmp_path: Path
    ) -> None:
        """No uv on PATH → python -m venv, constraint cannot be honoured, no crash."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch(
            "guardkit.orchestrator.environment_bootstrap._uv_on_path",
            return_value=False,
        ), patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="", stderr=""),
        ) as mock_run:
            bootstrapper._ensure_worktree_venv(tmp_path, ">=3.12")

        cmd = _venv_cmd(mock_run)
        assert cmd[1:3] == ["-m", "venv"]
        assert "--python" not in cmd


# ---------------------------------------------------------------------------
# _ensure_uv_venv — AB60 retry path
# ---------------------------------------------------------------------------


class TestEnsureUvVenvPython:
    def test_pins_python_from_requires_python(self, tmp_path: Path) -> None:
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="", stderr=""),
        ) as mock_run:
            bootstrapper._ensure_uv_venv(tmp_path, ">=3.12")

        cmd = _venv_cmd(mock_run)
        assert cmd[:2] == ["uv", "venv"]
        assert cmd[cmd.index("--python") + 1] == "3.12"
        assert "3.10" not in cmd

    def test_no_python_flag_when_constraint_absent(self, tmp_path: Path) -> None:
        """Backward compat: default call shape unchanged."""
        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="", stderr=""),
        ) as mock_run:
            bootstrapper._ensure_uv_venv(tmp_path)

        cmd = _venv_cmd(mock_run)
        assert cmd == ["uv", "venv", str(tmp_path / ".venv")]


# ---------------------------------------------------------------------------
# End-to-end: manifest requires-python flows into the uv venv argv
# ---------------------------------------------------------------------------


class TestManifestRequiresPythonFlows:
    def test_manifest_requires_python_reaches_uv_venv(self, tmp_path: Path) -> None:
        """AC regression: a >=3.12 manifest yields a --python pin that excludes 3.10."""
        manifest = _make_python_manifest(tmp_path, ">=3.12")
        assert manifest.get_requires_python() == ">=3.12"

        bootstrapper = EnvironmentBootstrapper(root=tmp_path)
        with patch(
            "guardkit.orchestrator.environment_bootstrap.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="", stderr=""),
        ) as mock_run:
            bootstrapper._ensure_uv_venv(
                tmp_path, manifest.get_requires_python()
            )

        cmd = _venv_cmd(mock_run)
        assert "--python" in cmd
        assert cmd[cmd.index("--python") + 1] == "3.12"
        assert "3.10" not in cmd
