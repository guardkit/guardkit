"""Integration: whole-feature .feature can be run as a smoke gate (TASK-SMK-F703A).

Completes the R2 ↔ R3 scoping boundary: task-level BDD (TASK-BDD-E8954)
uses ``@task:<TASK-ID>`` tags; whole-feature ``.feature`` files have no
such tags and belong to feature-level smoke. Operators write
``smoke_gates.command: "pytest features/FEAT-X.feature"`` to run those
scenarios between waves.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from guardkit.orchestrator.feature_loader import SmokeGates
from guardkit.orchestrator.smoke_gates import run_smoke_gate


def test_whole_feature_bdd_runs_as_smoke_gate(
    tmp_path: Path, monkeypatch
) -> None:
    """``smoke_gates.command: "pytest features/FEAT-X.feature"`` is a valid smoke config.

    The smoke-gate runner is agnostic to what the command does — it only
    cares about exit code, timeout, and working directory. This test
    verifies the runner:
      - executes the exact command configured
      - runs inside the worktree (not the main repo)
      - reports exit-code mismatch as a failure with structured context
    """
    worktree = tmp_path / "worktree"
    (worktree / "features").mkdir(parents=True)
    (worktree / "features" / "FEAT-X.feature").write_text(
        "Feature: Whole-feature smoke\n"
        "  Scenario: sanity\n"
        "    Given the worktree has a feature file\n"
        "    Then the smoke gate can run pytest against it\n",
        encoding="utf-8",
    )

    recorded: dict = {}

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout):
        recorded["cmd"] = cmd
        recorded["shell"] = shell
        recorded["cwd"] = cwd
        recorded["timeout"] = timeout
        # Simulate pytest exit=0 (scenarios pass)
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="1 passed", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    config = SmokeGates(
        after_wave=1,
        command="pytest features/FEAT-X.feature",
        expected_exit=0,
        timeout=30,
    )

    result = run_smoke_gate(config, cwd=worktree, wave_number=1)

    # Command is passed through verbatim — the runner does not rewrite it.
    assert recorded["cmd"] == "pytest features/FEAT-X.feature"
    # cwd is the worktree, not the main repo (AC: subprocess cwd must be
    # the feature-mode shared worktree, not the main repo).
    assert Path(recorded["cwd"]) == worktree
    assert recorded["shell"] is True
    assert recorded["timeout"] == 30

    assert result.passed is True
    assert result.exit_code == 0
    assert result.after_wave == 1


def test_whole_feature_bdd_failure_propagates_exit_code(
    tmp_path: Path, monkeypatch
) -> None:
    """When pytest exits non-zero, the smoke gate reports it as failure."""
    worktree = tmp_path / "worktree"
    (worktree / "features").mkdir(parents=True)

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout):
        return subprocess.CompletedProcess(
            args=cmd, returncode=1, stdout="", stderr="1 failed"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    config = SmokeGates(
        after_wave=1,
        command="pytest features/FEAT-X.feature",
    )

    result = run_smoke_gate(config, cwd=worktree, wave_number=1)

    assert result.passed is False
    assert result.exit_code == 1
    assert result.timed_out is False
    assert "1 failed" in result.stderr
