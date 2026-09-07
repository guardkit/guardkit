"""``guardkit qa classify-scenarios`` (2026-09-07, Part K of the
rewrite-on-refusal lane, rule 43): the routing law's dry run over one
``.feature`` file, for a spec that has no plan yet.

forge runs it on the committed draft before the spec card opens. It reads the
file and the repo's manifests, classifies every scenario by rule alone (R1-R10,
the same order and the same HTTP-surface detection as ``normalize-stamps``),
prints exactly one JSON object on stdout with ``--json``, and exits 0 whether
or not anything is refused (the JSON says which). It writes nothing anywhere
and never asks the model fallback. Exit 2 only when it cannot run (the file is
missing or cannot be read), as ``{"error": "..."}``.

The contract with forge's half (fixed so both could be built at once):

    {"feature_file": "<path as given>",
     "repo_has_http_surface": true|false,
     "http_surface_evidence": "<text>",
     "scenarios": [{"title": "<verbatim>", "home": "<verifier word or null>",
                    "rule": "<R1..R10 or null>", "refused": true|false}, ...],
     "refused_titles": ["<title>", ...]}

Every in-process test runs with the model trapped (an endpoint is configured
and reaching for it fails the test); the subprocess test points the endpoint at
a socket this test owns and counts the connections it is offered (none). Every
invocation hashes the whole temporary tree before and after, so a write
anywhere under it fails the test.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Dict, List

import pytest
from click.testing import CliRunner

from guardkit.cli.main import cli
from guardkit.orchestrator import stamp_normalizer
from guardkit.orchestrator.stamp_model_fallback import (
    MODEL_TIMEOUT_ENV,
    MODEL_URL_ENV,
    MODEL_URL_FALLBACK_ENV,
)

# ---------------------------------------------------------------------------
# The fixture: one endpoint example (hurl by R9 when the surface is on), one
# schema example in the idiom this weekend's refusals had (no rule decides
# it), and one fresh-start example (probe:process by R2, which runs before R9
# and so wins even though "I request the users count" is R9's own idiom).
# ---------------------------------------------------------------------------

ENDPOINT = "Creating a user answers 201 with the new user"
SCHEMA = "The users table has a deleted_at column after the migration"
FRESH = "A freshly started service serves the user count"

FEATURE_TEXT = f"""Feature: Users on a fresh deployment

  Scenario: {ENDPOINT}
    Given the service is running
    When I send a POST request to /users with a valid email
    Then the response status code should be 201
    And the response body contains the new user's id

  Scenario: {SCHEMA}
    Given the migration has been applied
    When the users table's columns are listed
    Then there is a nullable deleted_at column

  Scenario: {FRESH}
    Given the service has just started
    When I request the users count
    Then the count is zero
"""

FEATURE_REL = "features/users/users.feature"

#: The structural door the test repo opens, and the evidence sentence the
#: detector says for it — and for a repo with no door at all.
SURFACE_EVIDENCE = ".guardkit/config.yaml declares surface: http"
NO_SURFACE_EVIDENCE = (
    "no hurl gate in qa/gates/registry.yaml, no `surface: http` in "
    ".guardkit/config.yaml, and no web framework in pyproject/package.json dependencies"
)
OVERRIDE_ON_EVIDENCE = "overridden by the caller (--http-surface)"
OVERRIDE_OFF_EVIDENCE = "overridden by the caller (--no-http-surface)"


def _row(title: str, home: str | None, rule: str | None) -> dict:
    return {"title": title, "home": home, "rule": rule, "refused": home is None}


#: The whole JSON for the fixture on a repo with an HTTP surface — the
#: object forge's half was built against.
EXPECTED_WITH_SURFACE = {
    "feature_file": FEATURE_REL,
    "repo_has_http_surface": True,
    "http_surface_evidence": SURFACE_EVIDENCE,
    "scenarios": [
        _row(ENDPOINT, "hurl", "R9"),
        _row(SCHEMA, None, None),
        _row(FRESH, "probe:process", "R2"),
    ],
    "refused_titles": [SCHEMA],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo(tmp_path: Path, *, surface: bool, feature_text: str = FEATURE_TEXT) -> Path:
    """A repo with the fixture .feature and, when asked, the `surface: http`
    door. No `.guardkit/features/` directory: the verb must not need one."""
    repo = tmp_path / "repo"
    (repo / "features" / "users").mkdir(parents=True)
    (repo / "features" / "users" / "users.feature").write_text(feature_text, encoding="utf-8")
    (repo / ".guardkit").mkdir()
    if surface:
        (repo / ".guardkit" / "config.yaml").write_text("surface: http\n", encoding="utf-8")
    (repo / "README.md").write_text("a bystander file; must be untouched\n", encoding="utf-8")
    return repo


def _tree(root: Path) -> Dict[str, str]:
    """Every path under ``root`` with a hash of its bytes (directories are
    listed too, so a new empty directory is caught)."""
    out: Dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root))
        out[rel] = "<dir>" if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _invoke(tmp_path: Path, args: List[str]):
    """Run the verb in-process, asserting nothing under ``tmp_path`` changed."""
    before = _tree(tmp_path)
    result = CliRunner().invoke(cli, ["qa", "classify-scenarios", *args])
    assert _tree(tmp_path) == before, "the verb wrote or created something"
    return result


def _never(*_args, **_kwargs):
    raise AssertionError("the model fallback was reached by classify-scenarios")


@pytest.fixture(autouse=True)
def _model_is_a_trap(monkeypatch):
    """An endpoint is configured and every road to it fails the test."""
    monkeypatch.setenv(MODEL_URL_ENV, "http://127.0.0.1:9/v1")
    monkeypatch.setattr(urllib.request, "urlopen", _never)
    monkeypatch.setattr(stamp_normalizer, "decide_refused_titles", _never)
    monkeypatch.setattr(stamp_normalizer, "decide_refused_titles_with_outcome", _never)


# ---------------------------------------------------------------------------
# 1. The verb and its options
# ---------------------------------------------------------------------------


def test_the_verb_is_offered_beside_normalize_stamps():
    out = CliRunner().invoke(cli, ["qa", "--help"])
    assert out.exit_code == 0, out.output
    assert "classify-scenarios" in out.output
    assert "normalize-stamps" in out.output


def test_the_verb_offers_the_contracts_options():
    out = CliRunner().invoke(cli, ["qa", "classify-scenarios", "--help"])
    assert out.exit_code == 0, out.output
    flat = " ".join(out.output.split())
    for option in ("--feature-file", "--repo", "--http-surface / --no-http-surface", "--json"):
        assert option in flat, option
    assert "writes nothing" in flat
    assert "never asked" in flat


# ---------------------------------------------------------------------------
# 2. The JSON shape, rules only, refused against homed, exit 0 either way
# ---------------------------------------------------------------------------


def test_the_json_for_the_fixture_on_a_repo_with_an_http_surface(tmp_path: Path):
    """The whole object, key for key: the endpoint example is hurl by R9, the
    schema example is refused, the fresh-start example is probe:process by
    R2; one title refused; exit 0 all the same; stdout is that one object."""
    repo = _repo(tmp_path, surface=True)

    out = _invoke(tmp_path, ["--feature-file", FEATURE_REL, "--repo", str(repo), "--json"])

    assert out.exit_code == 0, out.output
    payload = json.loads(out.stdout)  # the WHOLE of stdout parses: one object, nothing else
    assert payload == EXPECTED_WITH_SURFACE
    assert list(payload) == [
        "feature_file",
        "repo_has_http_surface",
        "http_surface_evidence",
        "scenarios",
        "refused_titles",
    ]
    assert "cannot be proven by rule" in out.stderr
    assert SCHEMA in out.stderr
    assert "model" not in out.stderr.lower()


def test_without_an_http_surface_the_endpoint_example_is_refused_too(tmp_path: Path):
    """The wire rule is gated on the repo's surface, exactly as in
    normalize-stamps: with no surface the endpoint example has no home
    either. R2 does not depend on the surface. Still exit 0."""
    repo = _repo(tmp_path, surface=False)

    out = _invoke(tmp_path, ["--feature-file", FEATURE_REL, "--repo", str(repo), "--json"])

    assert out.exit_code == 0, out.output
    payload = json.loads(out.stdout)
    assert payload["repo_has_http_surface"] is False
    assert payload["http_surface_evidence"] == NO_SURFACE_EVIDENCE
    assert payload["scenarios"] == [
        _row(ENDPOINT, None, None),
        _row(SCHEMA, None, None),
        _row(FRESH, "probe:process", "R2"),
    ]
    assert payload["refused_titles"] == [ENDPOINT, SCHEMA]


def test_nothing_refused_is_the_same_shape_with_an_empty_list(tmp_path: Path):
    """A clean file: every row homed, ``refused_titles`` empty, no stderr line."""
    text = (
        "Feature: Users\n\n"
        f"  Scenario: {ENDPOINT}\n"
        "    When I send a POST request to /users with a valid email\n"
        "    Then the response status code should be 201\n\n"
        f"  Scenario: {FRESH}\n"
        "    Given the service has just started\n"
        "    Then the count is zero\n"
    )
    repo = _repo(tmp_path, surface=True, feature_text=text)

    out = _invoke(tmp_path, ["--feature-file", FEATURE_REL, "--repo", str(repo), "--json"])

    assert out.exit_code == 0, out.output
    payload = json.loads(out.stdout)
    assert payload["scenarios"] == [_row(ENDPOINT, "hurl", "R9"), _row(FRESH, "probe:process", "R2")]
    assert payload["refused_titles"] == []
    assert out.stderr == ""


def test_a_file_with_no_scenarios_is_not_an_error(tmp_path: Path):
    repo = _repo(tmp_path, surface=True, feature_text="Feature: Nothing yet\n")

    out = _invoke(tmp_path, ["--feature-file", FEATURE_REL, "--repo", str(repo), "--json"])

    assert out.exit_code == 0, out.output
    payload = json.loads(out.stdout)
    assert payload["scenarios"] == [] and payload["refused_titles"] == []


def test_a_duplicate_title_is_listed_per_scenario_but_refused_once(tmp_path: Path):
    """Every scenario in the file gets a row; the refused list names a title
    once, since that list is what the machine's note reads out."""
    text = FEATURE_TEXT + (
        f"\n  Scenario: {SCHEMA}\n"
        "    Given the migration has been applied\n"
        "    Then there is a nullable deleted_at column\n"
    )
    repo = _repo(tmp_path, surface=True, feature_text=text)

    out = _invoke(tmp_path, ["--feature-file", FEATURE_REL, "--repo", str(repo), "--json"])

    assert out.exit_code == 0, out.output
    payload = json.loads(out.stdout)
    assert [r["title"] for r in payload["scenarios"]] == [ENDPOINT, SCHEMA, FRESH, SCHEMA]
    assert payload["refused_titles"] == [SCHEMA]


# ---------------------------------------------------------------------------
# 3. The surface override, both ways
# ---------------------------------------------------------------------------


def test_http_surface_arms_the_wire_rule_on_a_repo_with_no_surface(tmp_path: Path):
    repo = _repo(tmp_path, surface=False)

    out = _invoke(
        tmp_path, ["--feature-file", FEATURE_REL, "--repo", str(repo), "--http-surface", "--json"]
    )

    assert out.exit_code == 0, out.output
    payload = json.loads(out.stdout)
    assert payload["repo_has_http_surface"] is True
    assert payload["http_surface_evidence"] == OVERRIDE_ON_EVIDENCE
    assert payload["scenarios"][0] == _row(ENDPOINT, "hurl", "R9")
    assert payload["refused_titles"] == [SCHEMA]


def test_no_http_surface_disarms_the_wire_rule_on_a_repo_with_a_surface(tmp_path: Path):
    repo = _repo(tmp_path, surface=True)

    out = _invoke(
        tmp_path, ["--feature-file", FEATURE_REL, "--repo", str(repo), "--no-http-surface", "--json"]
    )

    assert out.exit_code == 0, out.output
    payload = json.loads(out.stdout)
    assert payload["repo_has_http_surface"] is False
    assert payload["http_surface_evidence"] == OVERRIDE_OFF_EVIDENCE
    assert payload["scenarios"][0] == _row(ENDPOINT, None, None)
    assert payload["scenarios"][2] == _row(FRESH, "probe:process", "R2")
    assert payload["refused_titles"] == [ENDPOINT, SCHEMA]


# ---------------------------------------------------------------------------
# 4. Where the file is looked for; what "as given" means
# ---------------------------------------------------------------------------


def test_a_relative_path_is_found_under_the_repo_and_echoed_as_given(tmp_path: Path, monkeypatch):
    """The current directory is somewhere else entirely; the relative path
    resolves under --repo and the JSON echoes the string as it was given."""
    repo = _repo(tmp_path, surface=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    out = _invoke(tmp_path, ["--feature-file", FEATURE_REL, "--repo", str(repo), "--json"])

    assert out.exit_code == 0, out.output
    assert json.loads(out.stdout)["feature_file"] == FEATURE_REL


def test_an_absolute_path_is_taken_as_it_is(tmp_path: Path):
    repo = _repo(tmp_path, surface=True)
    absolute = str(repo / FEATURE_REL)

    out = _invoke(tmp_path, ["--feature-file", absolute, "--repo", str(repo), "--json"])

    assert out.exit_code == 0, out.output
    payload = json.loads(out.stdout)
    assert payload["feature_file"] == absolute
    assert payload == {**EXPECTED_WITH_SURFACE, "feature_file": absolute}


# ---------------------------------------------------------------------------
# 5. Exit 2 only when it cannot run
# ---------------------------------------------------------------------------


def test_a_missing_file_exits_2_with_one_error_object(tmp_path: Path):
    repo = _repo(tmp_path, surface=True)

    out = _invoke(tmp_path, ["--feature-file", "features/nowhere.feature", "--repo", str(repo), "--json"])

    assert out.exit_code == 2, out.output
    payload = json.loads(out.stdout)
    assert list(payload) == ["error"]
    assert payload["error"].startswith("feature file not found: features/nowhere.feature")
    assert str(repo) in payload["error"]
    assert "classify-scenarios: feature file not found" in out.stderr


def test_a_file_that_cannot_be_read_exits_2_with_one_error_object(tmp_path: Path):
    """A directory where a file was expected: it exists but cannot be read."""
    repo = _repo(tmp_path, surface=True)

    out = _invoke(tmp_path, ["--feature-file", "features/users", "--repo", str(repo), "--json"])

    assert out.exit_code == 2, out.output
    payload = json.loads(out.stdout)
    assert list(payload) == ["error"]
    assert payload["error"].startswith("feature file cannot be read: ")
    assert "features/users" in payload["error"]


def test_without_json_a_missing_file_still_exits_2_and_stdout_is_empty(tmp_path: Path):
    repo = _repo(tmp_path, surface=True)

    out = _invoke(tmp_path, ["--feature-file", "features/nowhere.feature", "--repo", str(repo)])

    assert out.exit_code == 2, out.output
    assert out.stdout == ""
    assert "feature file not found" in out.stderr


# ---------------------------------------------------------------------------
# 6. Without --json: plain lines a person can read
# ---------------------------------------------------------------------------


def test_without_json_the_verb_prints_one_plain_line_per_scenario(tmp_path: Path):
    repo = _repo(tmp_path, surface=True)

    out = _invoke(tmp_path, ["--feature-file", FEATURE_REL, "--repo", str(repo)])

    assert out.exit_code == 0, out.output
    lines = out.stdout.splitlines()
    assert lines[0] == f"3 scenario(s) in {FEATURE_REL}; HTTP surface: yes ({SURFACE_EVIDENCE})"
    assert lines[1] == f"  - {ENDPOINT} -> hurl (R9: post request to ({SURFACE_EVIDENCE}))"
    assert lines[2] == f"  - {SCHEMA} -> refused: no rule decides it"
    assert lines[3] == f"  - {FRESH} -> probe:process (R2: freshly started)"
    assert len(lines) == 4
    assert f"1 of 3 scenario(s) cannot be proven by rule: {SCHEMA}" in out.stderr


# ---------------------------------------------------------------------------
# 7. The real CLI as forge runs it: a subprocess, a socket that counts
# ---------------------------------------------------------------------------


class _Listener:
    """A socket this test owns at the address the CLI is told is the model.
    It counts every connection it is offered and closes each at once."""

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


def _run_real_cli(args: List[str], env: dict) -> subprocess.CompletedProcess:
    worktree = Path(__file__).resolve().parents[2]  # this checkout's guardkit, not another's
    return subprocess.run(
        [sys.executable, "-c", "from guardkit.cli.main import cli; cli()", "qa", "classify-scenarios", *args],
        cwd=str(worktree),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_the_real_cli_prints_exactly_one_json_object_writes_nothing_and_never_connects(tmp_path: Path):
    """The subprocess's whole stdout is the one object; the tree is byte for
    byte what it was; the socket the CLI is told is the model is never
    connected to; exit 0 with a refusal in the list."""
    repo = _repo(tmp_path, surface=True)
    before = _tree(tmp_path)
    with _Listener() as model:
        env = dict(os.environ)
        env[MODEL_URL_ENV] = model.url
        env.pop(MODEL_URL_FALLBACK_ENV, None)
        env[MODEL_TIMEOUT_ENV] = "1"
        proc = _run_real_cli(["--feature-file", FEATURE_REL, "--repo", str(repo), "--json"], env)
        connections = model.connections

    assert proc.returncode == 0, proc.stderr
    assert connections == 0
    assert _tree(tmp_path) == before
    assert json.loads(proc.stdout) == EXPECTED_WITH_SURFACE
    assert proc.stderr.strip() == f"classify-scenarios: 1 of 3 scenario(s) cannot be proven by rule: {SCHEMA}"


def test_the_real_cli_exits_2_on_a_missing_file_with_one_error_object(tmp_path: Path):
    repo = _repo(tmp_path, surface=True)
    before = _tree(tmp_path)
    env = dict(os.environ)
    env.pop(MODEL_URL_ENV, None)
    env.pop(MODEL_URL_FALLBACK_ENV, None)

    proc = _run_real_cli(["--feature-file", "features/nowhere.feature", "--repo", str(repo), "--json"], env)

    assert proc.returncode == 2, proc.stderr
    assert _tree(tmp_path) == before
    payload = json.loads(proc.stdout)
    assert list(payload) == ["error"]
    assert payload["error"].startswith("feature file not found: features/nowhere.feature")
