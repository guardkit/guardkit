"""Smoke-gate venv interpreter resolution (TASK-FIX-A7B1, TASK-SGER-002).

Pins the contract that ``run_smoke_gate`` honours the bootstrap venv
interpreter when one is supplied. Without this, on Ubuntu 24+ a smoke
command containing a bare ``python`` (e.g. ``python -m pytest …``) dies
with exit 127 because only ``python3`` exists in system PATH — even
when ``environment_bootstrap`` has already created a venv at
``<worktree>/.guardkit/venv/bin/python``.

TASK-SGER-002 extends the ``venv_python`` contract: when the bootstrap
install ran first-try against the orchestrator's parent shell venv
(macOS uv happy path), the bootstrapper records ``sys.executable`` as
the active interpreter. The smoke gate must PATH-prepend that
interpreter's directory so a bare ``python`` resolves to the same
binary that ran the install — closing the FEAT-61F1 failure shape.

The companion fix to ``build_venv_env`` (consult ``.guardkit/venv/bin``
in addition to ``.venv/bin``) is covered in
``tests/unit/test_coach_command_verification.py``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    DetectedManifest,
    EnvironmentBootstrapper,
)
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


# ============================================================================
# TASK-SGER-002: parent-venv fallback (sys.executable)
# ============================================================================


def test_run_smoke_gate_with_sys_executable_prepends_interpreter_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TASK-SGER-002: ``venv_python = sys.executable`` produces a PATH-prepended
    env whose first entry is ``Path(sys.executable).parent``.

    This is the macOS happy-path shape post-fix: the bootstrap install ran
    against the orchestrator's parent shell venv, no worktree-local venv
    was created, and the bootstrapper records ``sys.executable``. The
    smoke gate must treat that interpreter's bin/ identically to a
    worktree-local venv — prepending it to PATH so a bare ``python`` in
    the smoke command resolves to the same interpreter that ran the
    install (closing the FEAT-61F1 failure shape).
    """
    captured: dict = {}

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout, env=None):
        captured["env"] = env
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = SmokeGates(after_wave=1, command="python -c 'pass'", expected_exit=0)

    result = run_smoke_gate(
        config,
        cwd=tmp_path,
        wave_number=1,
        venv_python=sys.executable,
    )

    assert result.passed is True
    env = captured["env"]
    assert env is not None, (
        "When venv_python=sys.executable is supplied (TASK-SGER-002 path), "
        "env must be a non-None dict with PATH prepended — same contract "
        "as the worktree-local venv path."
    )
    expected_bin = str(Path(sys.executable).parent)
    first_path_entry = env["PATH"].split(os.pathsep, 1)[0]
    assert first_path_entry == expected_bin, (
        f"sys.executable's parent dir must be the first PATH entry so the "
        f"smoke gate's bare ``python`` resolves to the orchestrator's "
        f"interpreter. Got first entry: {first_path_entry!r}, expected: "
        f"{expected_bin!r}"
    )


# ============================================================================
# TASK-SGER-002: end-to-end regression guard for FEAT-61F1's failure shape
# ============================================================================


def test_bootstrap_then_smoke_gate_resolves_python_against_parent_venv(
    tmp_path: Path,
) -> None:
    """End-to-end regression guard for the FEAT-61F1 failure shape.

    Builds a tmp-path worktree with a minimal pyproject.toml, runs
    ``EnvironmentBootstrapper.bootstrap()`` against a stubbed install
    (mocked to succeed first try, simulating the macOS uv-against-parent-venv
    happy path), and then invokes ``run_smoke_gate`` with the bootstrapper's
    reported ``venv_python``. Asserts the gate resolves ``python`` to a real
    on-disk interpreter — the same one that "ran" the install.

    This locks in the contract that closes FEAT-61F1's failure: bootstrap →
    venv_python populated → smoke gate sees that interpreter via PATH.
    Pre-fix, ``venv_python`` was None and the gate inherited unchanged
    PATH; on systems where another ``python`` precedes the orchestrator's
    own, the gate fired against the wrong interpreter and the worktree's
    package was missing.
    """
    # Set up a minimal worktree: pyproject.toml declaring a 'pkg' project.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "pkg"\n'
        'version = "0.0.1"\n'
        'requires-python = ">=3.8"\n'
    )
    # Materialise the package src-dir so is_project_complete() returns True.
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")

    manifest = DetectedManifest(
        path=pyproject.resolve(),
        stack="python",
        is_lock_file=False,
        install_command=["uv", "pip", "install", "-e", "."],
    )

    bootstrapper = EnvironmentBootstrapper(root=tmp_path)
    # Mock subprocess.run for the install so the test doesn't shell out.
    install_proc = Mock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=install_proc):
        bootstrap_result = bootstrapper.bootstrap([manifest])

    assert bootstrap_result.success is True
    assert bootstrap_result.venv_python == sys.executable, (
        "macOS happy path: bootstrap must record sys.executable as the "
        "active interpreter."
    )

    # Now run the smoke gate with the bootstrap's reported venv_python.
    # Mock subprocess.run again so we observe the env constructed for the
    # gate without actually shelling out.
    captured: dict = {}

    def fake_smoke_run(cmd, *, shell, cwd, capture_output, text, timeout, env=None):
        captured["env"] = env
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="ok", stderr=""
        )

    config = SmokeGates(
        after_wave=1, command="python -c 'import sys; print(sys.executable)'",
        expected_exit=0,
    )
    with patch("subprocess.run", side_effect=fake_smoke_run):
        smoke_result = run_smoke_gate(
            config,
            cwd=tmp_path,
            wave_number=1,
            venv_python=bootstrap_result.venv_python,
        )

    assert smoke_result.passed is True
    env = captured["env"]
    assert env is not None, (
        "Bootstrap's venv_python must produce a PATH-prepended env for "
        "the smoke gate — the regression guard for FEAT-61F1."
    )
    expected_bin = str(Path(sys.executable).parent)
    assert env["PATH"].startswith(expected_bin + os.pathsep), (
        f"Smoke gate PATH must lead with the bootstrap interpreter's bin "
        f"directory. Got: {env['PATH'][:160]!r}"
    )
