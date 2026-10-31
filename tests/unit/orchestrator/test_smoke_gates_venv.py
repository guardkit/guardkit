"""The smoke command runs as declared, with nothing put in front of PATH.

TASK-FIX-A7B1 and TASK-SGER-002 put the bootstrap venv's interpreter first on
PATH so a bare ``python`` in a smoke command meant the project's venv. That
hidden Python default was removed on 31 October 2026 (Rich: "I don't want any
more hidden surprises"), with its tests; a project whose smoke command needs
an interpreter names it.
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
    """Nothing is put in front of PATH.

    AC-006, as changed on 13 October 2026: the command no longer inherits the
    parent environment (``env=None``). It gets one built from nothing
    (``project_command_env``), whose PATH is this process's own, unchanged.
    """
    captured: dict = {}

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout, env=None):
        captured["env"] = env
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("OPENAI_API_KEY", "factory-credential")
    config = SmokeGates(after_wave=1, command="pytest", expected_exit=0)

    result = run_smoke_gate(config, cwd=tmp_path, wave_number=1)

    assert result.passed is True
    assert captured["env"] is not None
    assert captured["env"]["PATH"] == os.environ["PATH"]
    assert "OPENAI_API_KEY" not in captured["env"]
