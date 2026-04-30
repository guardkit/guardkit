"""Smoke-gate venv interpreter resolution (TASK-FIX-A7B1).

Pins the contract that ``run_smoke_gate`` honours the bootstrap venv
interpreter when one is supplied. Without this, on Ubuntu 24+ a smoke
command containing a bare ``python`` (e.g. ``python -m pytest …``) dies
with exit 127 because only ``python3`` exists in system PATH — even
when ``environment_bootstrap`` has already created a venv at
``<worktree>/.guardkit/venv/bin/python``.

The companion fix to ``build_venv_env`` (consult ``.guardkit/venv/bin``
in addition to ``.venv/bin``) is covered in
``tests/unit/test_coach_command_verification.py``.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.feature_loader import SmokeGates
from guardkit.orchestrator.smoke_gates import run_smoke_gate


def test_run_smoke_gate_default_no_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When ``venv_python`` is None, subprocess.run is called with env=None.

    AC-006: existing behaviour preserved when no venv is bootstrapped.
    Passing ``env=None`` is identical to omitting it — subprocess inherits
    the parent environment.
    """
    captured: dict = {}

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout, env=None):
        captured["env"] = env
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = SmokeGates(after_wave=1, command="pytest", expected_exit=0)

    result = run_smoke_gate(config, cwd=tmp_path, wave_number=1)

    assert result.passed is True
    assert captured["env"] is None, (
        "When no venv is bootstrapped, env must remain None so subprocess "
        "inherits the parent environment unchanged."
    )


def test_run_smoke_gate_path_prepends_venv_bin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-001 + AC-002: venv_python triggers PATH-prepended env construction.

    The bootstrap venv interpreter directory must appear at the *front*
    of PATH so a bare ``python`` in the smoke command resolves to the
    venv interpreter, not the system PATH.
    """
    venv_python = tmp_path / ".guardkit" / "venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.touch()

    captured: dict = {}

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout, env=None):
        captured["env"] = env
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = SmokeGates(after_wave=1, command="python -m pytest", expected_exit=0)

    result = run_smoke_gate(
        config,
        cwd=tmp_path,
        wave_number=1,
        venv_python=str(venv_python),
    )

    assert result.passed is True
    env = captured["env"]
    assert env is not None, "venv_python must produce a non-None env dict"

    expected_bin = str(venv_python.parent)
    assert env["PATH"].startswith(expected_bin + os.pathsep), (
        f"venv bin must be prepended to PATH (got: {env['PATH'][:120]!r})"
    )


def test_run_smoke_gate_resolves_bare_python_to_venv_on_ubuntu_24(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-005: regression test — Ubuntu-24-only-``python3`` system PATH.

    Simulates the production failure mode: a system PATH where only
    ``python3`` exists, and the smoke command contains a bare ``python``.
    With the bootstrap venv prepended, ``python`` MUST resolve to the
    venv interpreter; without it (the pre-fix bug), the subprocess would
    die with exit 127.
    """
    # Build a "system" PATH that only has python3 — mimic Ubuntu 24+.
    system_bin = tmp_path / "system_bin"
    system_bin.mkdir()
    (system_bin / "python3").touch()
    monkeypatch.setenv("PATH", str(system_bin))

    # Bootstrap venv with a real ``python`` symlink target.
    venv_bin = tmp_path / ".guardkit" / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    venv_python_path = venv_bin / "python"
    venv_python_path.touch()

    captured: dict = {}

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout, env=None):
        captured["env"] = env
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = SmokeGates(
        after_wave=1, command="python -m pytest -q", expected_exit=0
    )

    run_smoke_gate(
        config,
        cwd=tmp_path,
        wave_number=1,
        venv_python=str(venv_python_path),
    )

    env = captured["env"]
    assert env is not None
    # The first PATH entry resolves ``python`` — it must be the venv bin,
    # not the system bin (which only carries python3).
    first_path_entry = env["PATH"].split(os.pathsep, 1)[0]
    assert first_path_entry == str(venv_bin), (
        "Bootstrap venv bin must precede system PATH; otherwise a bare "
        "``python`` in the smoke command would resolve to nothing on "
        "Ubuntu 24+."
    )
