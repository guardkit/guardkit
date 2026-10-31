"""The smoke gate passes only on its declared ``expected_exit``.

TASK-FIX-SG05 read pytest's exit 5 ("no tests collected") from any smoke
command as a soft "gate not wired" pass. Since 31 October 2026 no exit code
means anything special: a command that exits 5 when 0 is expected failed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.feature_loader import SmokeGates
from guardkit.orchestrator.smoke_gates import run_smoke_gate


def _patch_subprocess_returncode(
    monkeypatch: pytest.MonkeyPatch, returncode: int
) -> None:
    """Replace subprocess.run with a stub that returns ``returncode``."""

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout, env=None):
        return subprocess.CompletedProcess(
            args=cmd, returncode=returncode, stdout="", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)


@pytest.mark.parametrize("returncode,passed", [(0, True), (1, False), (5, False)])
def test_only_the_expected_exit_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, returncode: int, passed: bool
) -> None:
    _patch_subprocess_returncode(monkeypatch, returncode)
    config = SmokeGates(after_wave=1, command="bash scripts/smoke.sh", expected_exit=0)

    result = run_smoke_gate(config, cwd=tmp_path, wave_number=1)

    assert result.passed is passed
    assert result.exit_code == returncode
    assert result.timed_out is False


def test_a_declared_expected_exit_of_five_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_subprocess_returncode(monkeypatch, 5)
    config = SmokeGates(after_wave=1, command="bash scripts/smoke.sh", expected_exit=5)

    assert run_smoke_gate(config, cwd=tmp_path, wave_number=1).passed is True


def test_an_old_feature_file_that_sets_the_removed_knob_still_loads() -> None:
    config = SmokeGates.model_validate(
        {"after_wave": 1, "command": "x", "exit5_is_hard_fail": True}
    )
    assert not hasattr(config, "exit5_is_hard_fail")
