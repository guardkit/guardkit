"""``guardkit qa normalize-stamps --no-model`` (2026-09-07, rule 1a of the
rewrite-on-refusal lane).

On a run's first stamping forge wants the routing law applied by rule only: a
refusal is the signal its rewrite round needs, and the model fallback (which
cannot see the schema) must not decide the refused titles away. ``--no-model``
switches the fallback off for that one stamping. Everything else about the
command is unchanged: the refused titles are named on stderr and in the JSON,
the JSON is the same shape, exit 3 is still "partial" and exit 0 still "all
decided"; the only new thing is ``model_outcome.status == "switched_off"``
with the reason in plain words, and one INFO line on stderr saying the same.

Network-free by construction: the in-process tests replace ``urlopen`` with a
call that fails the test; the subprocess tests point the endpoint at a socket
this test owns and count the connections it is offered — none with the flag,
one without it.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import List

from click.testing import CliRunner

from guardkit.cli.main import cli
from guardkit.orchestrator.stamp_model_fallback import (
    MODEL_TIMEOUT_ENV,
    MODEL_URL_ENV,
    MODEL_URL_FALLBACK_ENV,
    SWITCHED_OFF_DETAIL,
)

LOGGER = "guardkit.orchestrator.stamp_model_fallback"

#: Two of the real refusals from the week the lane was set, verbatim.
TITLES = [
    "Concurrent requests return the same 7-day data",
    "Concurrent deactivation requests are handled idempotently",
]
STEPS = (
    "Given the service is running\n"
    "    When several clients act at the same moment\n"
    "    Then the answers agree\n"
)
DECIDED_BY_A_RULE = "The count degrades honestly when the database is unavailable"
DECIDED_STEPS = (
    "Given the database is unavailable\n"
    "    When the count is asked for\n"
    "    Then it degrades honestly\n"
)

#: The flag's help, word for word.
HELP_TEXT = (
    "Classify by rule only; never ask the model fallback about refused titles. "
    "forge passes this on a run's first stamping so a refusal reaches the "
    "machine's rewrite round; the model is asked on the second stamping."
)

#: What the JSON carries under ``model_outcome`` — the contract with forge.
SWITCHED_OFF_OUTCOME = {
    "status": "switched_off",
    "detail": (
        "the caller switched the model fallback off for this stamping (the first "
        "stamping of a run runs by rule only so a refusal can go back to the spec writer)"
    ),
    "endpoint": "",
    "model": "",
}
#: The one line on stderr (behind the logger prefix ``INFO:<logger>:``).
SWITCHED_OFF_LINE = (
    "STAMP NORMALIZER: feature FEAT-CONC — the model fallback was not asked about "
    "2 title(s) no rule could decide: switched off for this stamping by the caller "
    "(the first stamping of a run runs by rule only so a refusal can go back to the "
    "spec writer). The titles stay refused and nothing was stamped."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo(tmp_path: Path, titles: List[str], *, include_rule_decided: bool = False) -> Path:
    """A repo with one feature file and no HTTP surface, so every title in
    ``titles`` is refused by rule and would reach the fallback."""
    repo = tmp_path / "repo"
    (repo / ".guardkit" / "features").mkdir(parents=True)
    (repo / "features" / "concurrency").mkdir(parents=True)
    body = "Feature: Concurrency\n"
    if include_rule_decided:
        body += f"  Scenario: {DECIDED_BY_A_RULE}\n    {DECIDED_STEPS}\n"
    for title in titles:
        body += f"  Scenario: {title}\n    {STEPS}\n"
    (repo / "features" / "concurrency" / "concurrency.feature").write_text(body)
    (repo / ".guardkit" / "features" / "FEAT-CONC.yaml").write_text(
        "id: FEAT-CONC\n"
        "name: Concurrency scenarios\n"
        "status: planned\n"
        "feature_files:\n"
        "  - features/concurrency/concurrency.feature\n"
    )
    return repo


def _payload(text: str) -> dict:
    return json.loads(text[text.index('{\n  "feature_id"') :])


def _never(*_args, **_kwargs):
    raise AssertionError("the network was touched with --no-model")


def _invoke(repo: Path, *extra: str):
    return CliRunner().invoke(
        cli,
        ["qa", "normalize-stamps", "--feature", "FEAT-CONC", "--repo", str(repo), "--dry-run", *extra],
    )


class _Listener:
    """A socket this test owns at the address the CLI is told is the model. It
    counts every connection it is offered and closes each at once, so a caller
    that does reach it fails fast instead of waiting on a timeout."""

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.sock.settimeout(0.1)
        self.port: int = self.sock.getsockname()[1]
        self.connections = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def __enter__(self) -> "_Listener":
        self._thread.start()
        return self

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self.connections += 1
            conn.close()

    def __exit__(self, *_exc) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        self.sock.close()


def _run_real_cli(repo: Path, env: dict, *extra: str) -> subprocess.CompletedProcess:
    worktree = Path(__file__).resolve().parents[2]  # this checkout's guardkit, not another's
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from guardkit.cli.main import cli; cli()",
            "qa",
            "normalize-stamps",
            "--feature",
            "FEAT-CONC",
            "--repo",
            str(repo),
            "--dry-run",
            *extra,
        ],
        cwd=str(worktree),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


# ---------------------------------------------------------------------------
# 1. The flag, and what the command says with it
# ---------------------------------------------------------------------------


def test_the_pinned_words_are_the_modules_words():
    """The literal above is the contract; the module must say the same thing."""
    assert SWITCHED_OFF_OUTCOME["detail"] == SWITCHED_OFF_DETAIL


def test_no_model_is_offered_with_its_words():
    out = CliRunner().invoke(cli, ["qa", "normalize-stamps", "--help"])
    assert out.exit_code == 0, out.output
    flat = " ".join(out.output.split())
    assert "--no-model" in flat
    assert HELP_TEXT in flat


def test_no_model_names_the_refused_titles_and_says_switched_off(tmp_path: Path, monkeypatch, caplog):
    """An endpoint is configured and the network is a trap; with the flag the
    command never goes near it. The refusal path is otherwise as today: the
    PARTIAL echo names the titles, the JSON lists them, exit 3."""
    monkeypatch.setenv(MODEL_URL_ENV, "http://127.0.0.1:9/v1")
    monkeypatch.setattr(urllib.request, "urlopen", _never)
    repo = _repo(tmp_path, TITLES)

    with caplog.at_level(logging.INFO, logger=LOGGER):
        out = _invoke(repo, "--no-model")

    assert out.exit_code == 3, out.output
    payload = _payload(out.output)
    assert payload["refused"] == TITLES
    assert payload["stamped"] == {} and payload["model_stamped"] == []
    assert payload["model_outcome"] == SWITCHED_OFF_OUTCOME
    assert "normalize-stamps PARTIAL: 2 scenario(s)" in out.output
    for title in TITLES:
        assert f"  - {title}" in out.output
    records = [(r.levelno, r.getMessage()) for r in caplog.records if r.name == LOGGER]
    assert records == [(logging.INFO, SWITCHED_OFF_LINE)]


def test_without_no_model_the_same_run_asks_the_endpoint(tmp_path: Path, monkeypatch):
    """The flag is the whole difference: the same command without it reaches
    for the configured endpoint (and, here, is refused by it)."""
    monkeypatch.setenv(MODEL_URL_ENV, "http://127.0.0.1:9/v1")
    monkeypatch.setenv(MODEL_TIMEOUT_ENV, "1")
    calls: List[str] = []

    def _refuse(req, *args, **kwargs):
        calls.append(getattr(req, "full_url", str(req)))
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", _refuse)
    repo = _repo(tmp_path, TITLES)

    out = _invoke(repo)

    assert out.exit_code == 3, out.output
    assert calls == ["http://127.0.0.1:9/v1/chat/completions"]
    payload = _payload(out.output)
    assert payload["refused"] == TITLES
    assert payload["model_outcome"]["status"] == "asked_and_failed"


def test_no_model_with_nothing_refused_exits_zero_with_no_outcome(tmp_path: Path, monkeypatch):
    """Every title decided by rule: the flag changes nothing — no outcome, exit 0."""
    monkeypatch.setattr(urllib.request, "urlopen", _never)
    repo = _repo(tmp_path, [], include_rule_decided=True)

    out = _invoke(repo, "--no-model")

    assert out.exit_code == 0, out.output
    payload = _payload(out.output)
    assert payload["refused"] == []
    assert payload["model_outcome"] is None
    assert DECIDED_BY_A_RULE in payload["stamped"]


# ---------------------------------------------------------------------------
# 2. The real CLI as forge runs it: a subprocess, with a socket that counts
# ---------------------------------------------------------------------------


def test_the_real_cli_with_no_model_makes_no_network_attempt_and_prints_the_line(tmp_path: Path):
    """The endpoint is a socket this test owns. With ``--no-model`` it is never
    connected to; the INFO line lands on stderr behind the logger prefix, the
    JSON on stdout carries ``switched_off``, and the refused titles are named
    both places, exit 3 — the same partial as today."""
    repo = _repo(tmp_path, TITLES)
    with _Listener() as model:
        env = dict(os.environ)
        env[MODEL_URL_ENV] = model.url
        env.pop(MODEL_URL_FALLBACK_ENV, None)
        env[MODEL_TIMEOUT_ENV] = "1"
        proc = _run_real_cli(repo, env, "--no-model")
        connections = model.connections

    assert proc.returncode == 3, proc.stderr
    assert connections == 0

    stderr_lines = proc.stderr.splitlines()
    assert "INFO:guardkit.orchestrator.stamp_model_fallback:" + SWITCHED_OFF_LINE in stderr_lines
    about_the_model = [line for line in stderr_lines if "STAMP NORMALIZER:" in line and "model fallback" in line]
    assert len(about_the_model) == 1
    assert "could not answer" not in proc.stderr
    assert "no model endpoint is configured" not in proc.stderr
    assert "normalize-stamps PARTIAL: 2 scenario(s)" in proc.stderr

    payload = json.loads(proc.stdout[proc.stdout.index("{") :])
    assert payload["model_outcome"] == SWITCHED_OFF_OUTCOME
    assert payload["refused"] == TITLES
    assert payload["model_stamped"] == [] and payload["stamped"] == {}


def test_the_real_cli_without_no_model_does_connect(tmp_path: Path):
    """The control: the same command without the flag connects to the socket
    (which hangs up on it), so the outcome is a failed call, not a switch."""
    repo = _repo(tmp_path, TITLES)
    with _Listener() as model:
        env = dict(os.environ)
        env[MODEL_URL_ENV] = model.url
        env.pop(MODEL_URL_FALLBACK_ENV, None)
        env[MODEL_TIMEOUT_ENV] = "1"
        proc = _run_real_cli(repo, env)
        connections = model.connections

    assert proc.returncode == 3, proc.stderr
    assert connections >= 1
    payload = json.loads(proc.stdout[proc.stdout.index("{") :])
    assert payload["model_outcome"]["status"] == "asked_and_failed"
    assert payload["model_outcome"]["endpoint"] == f"127.0.0.1:{model.port}"
    assert payload["refused"] == TITLES
    assert "switched off" not in proc.stderr
