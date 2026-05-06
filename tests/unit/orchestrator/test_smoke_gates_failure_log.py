"""Smoke-gate failure-path log surfaces captured output (TASK-SGER-001).

Pins the contract that ``run_smoke_gate`` includes captured stderr and stdout
in the WARNING log on every failure path — exit-mismatch and timeout — so
operators see the actual diagnostic in a single line of log output rather
than re-running the gate by hand.

The data is captured at the subprocess call site; the change is log-only.
This module guards against silently dropping that data on either path,
which has bitten FEAT-61F1 and FEAT-D40B in production.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.feature_loader import SmokeGates
from guardkit.orchestrator.smoke_gates import run_smoke_gate


def _patch_subprocess_run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    returncode: int,
    stdout: str = "",
    stderr: str = "",
) -> None:
    """Replace subprocess.run with a stub that returns the given output."""

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout, env=None):
        return subprocess.CompletedProcess(
            args=cmd, returncode=returncode, stdout=stdout, stderr=stderr
        )

    monkeypatch.setattr(subprocess, "run", fake_run)


def test_failure_path_log_contains_captured_stderr_and_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC: the exit-mismatch failure WARNING must include captured output.

    Without this, operators see only ``exit=X, expected=Y`` and have to
    re-run the gate by hand to learn what actually failed. Closes the
    diagnostic gap that bit FEAT-61F1 and FEAT-D40B.
    """
    captured_stderr = (
        "ImportError: No module named 'specialist_agent.workflows'\n"
        "  File \"smoke.py\", line 3, in <module>"
    )
    captured_stdout = "running smoke check..."
    _patch_subprocess_run(
        monkeypatch, returncode=2, stdout=captured_stdout, stderr=captured_stderr
    )
    config = SmokeGates(after_wave=1, command="python smoke.py", expected_exit=0)

    with caplog.at_level(
        logging.WARNING, logger="guardkit.orchestrator.smoke_gates"
    ):
        result = run_smoke_gate(config, cwd=tmp_path, wave_number=1)

    assert result.passed is False, "exit=2 with expected=0 must fail"

    log_text = caplog.text
    # Preserve the machine-parseable prefix (downstream log scrapers depend
    # on the "Smoke gate failed after wave N (exit=X, expected=Y)" shape).
    assert "Smoke gate failed after wave 1 (exit=2, expected=0)" in log_text
    # The whole point of this task: stderr lands in the log.
    assert "ImportError: No module named 'specialist_agent.workflows'" in log_text
    # stdout too — sometimes the diagnostic is on stdout (pytest -q etc.).
    assert "running smoke check..." in log_text
    # Labels matter: an operator scanning the log must be able to tell which
    # stream is which without re-running the gate.
    assert "stderr:" in log_text
    assert "stdout:" in log_text


def test_failure_path_log_handles_empty_streams_gracefully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When the failed subprocess wrote nothing to stderr/stdout, the log
    must still emit a placeholder rather than silently rendering blank lines.

    The ``(empty)`` placeholder makes "process produced no output" visually
    distinct from "log was truncated" in post-mortem reading.
    """
    _patch_subprocess_run(monkeypatch, returncode=1, stdout="", stderr="")
    config = SmokeGates(after_wave=2, command="false", expected_exit=0)

    with caplog.at_level(
        logging.WARNING, logger="guardkit.orchestrator.smoke_gates"
    ):
        result = run_smoke_gate(config, cwd=tmp_path, wave_number=2)

    assert result.passed is False
    log_text = caplog.text
    assert "Smoke gate failed after wave 2 (exit=1, expected=0)" in log_text
    # Both streams empty — placeholder must appear under each label.
    # We assert on the rendered substring rather than the format string so
    # log-scraper-style text inspection works the same way an operator
    # would scan it.
    assert "stderr:\n(empty)" in log_text
    assert "stdout:\n(empty)" in log_text


def test_timeout_path_log_contains_partial_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC: the timeout path WARNING must surface whatever the subprocess
    produced before being killed.

    ``subprocess.TimeoutExpired`` carries partial ``stdout`` / ``stderr``;
    the runner already decodes both onto the result, but pre-fix the log
    line dropped them. This guards against re-introducing that drop.
    """
    partial_stderr = b"about to import broken module..."
    partial_stdout = b"setup phase done\n"

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout, env=None):
        # subprocess.TimeoutExpired carries partial output as bytes when
        # text=True wasn't fully effective at decode time — the runner's
        # ``_decode`` helper handles both bytes and str. Use bytes here to
        # exercise that branch.
        raise subprocess.TimeoutExpired(
            cmd=cmd, timeout=timeout, output=partial_stdout, stderr=partial_stderr
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = SmokeGates(
        after_wave=3, command="python long_smoke.py", expected_exit=0, timeout=2
    )

    with caplog.at_level(
        logging.WARNING, logger="guardkit.orchestrator.smoke_gates"
    ):
        result = run_smoke_gate(config, cwd=tmp_path, wave_number=3)

    assert result.timed_out is True
    assert result.passed is False
    assert result.exit_code == -1, (
        "Timeout path uses sentinel exit_code=-1; the log surfaces the"
        " partial output instead of a real return code."
    )

    log_text = caplog.text
    # The original timeout prefix must remain so existing log scrapers and
    # operators searching for "timed out after" still match.
    assert "Smoke gate timed out after 2s: python long_smoke.py" in log_text
    # And the partial output must now be surfaced under labelled sections,
    # so a stuck-on-import gate is self-diagnosing without rerunning.
    assert "about to import broken module..." in log_text
    assert "setup phase done" in log_text
    assert "stderr (partial):" in log_text
    assert "stdout (partial):" in log_text


def test_timeout_path_log_handles_missing_partial_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When ``TimeoutExpired`` carries no captured partial output, the log
    must still emit ``(empty)`` placeholders so the format is uniform with
    the populated case — and so an operator can tell "timed out before
    writing anything" from "log truncated by buffering"."""

    def fake_run(cmd, *, shell, cwd, capture_output, text, timeout, env=None):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = SmokeGates(
        after_wave=1, command="hang.sh", expected_exit=0, timeout=1
    )

    with caplog.at_level(
        logging.WARNING, logger="guardkit.orchestrator.smoke_gates"
    ):
        result = run_smoke_gate(config, cwd=tmp_path, wave_number=1)

    assert result.timed_out is True
    log_text = caplog.text
    assert "Smoke gate timed out after 1s: hang.sh" in log_text
    assert "stderr (partial):\n(empty)" in log_text
    assert "stdout (partial):\n(empty)" in log_text


def test_passing_path_log_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC constraint: the passing-path log must NOT change.

    Only failure paths are extended. A success log dump on every gate
    would be noise, and downstream log scrapers may pin against the exact
    "Smoke gate passed after wave N (exit=N)" shape.
    """
    _patch_subprocess_run(
        monkeypatch, returncode=0, stdout="some output", stderr=""
    )
    config = SmokeGates(after_wave=1, command="pytest", expected_exit=0)

    with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.smoke_gates"):
        result = run_smoke_gate(config, cwd=tmp_path, wave_number=1)

    assert result.passed is True
    log_text = caplog.text
    assert "Smoke gate passed after wave 1 (exit=0)" in log_text
    # The success log must NOT echo captured stdout — the passing-path
    # output is an intentional silence, not a regression.
    assert "stderr:" not in log_text
    assert "stdout:" not in log_text
