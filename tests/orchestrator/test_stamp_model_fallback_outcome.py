"""THE MODEL FALLBACK REPORTS ITS OWN OUTCOME (2026-09-06).

Why this exists. On 2026-09-06 two of Rich's sentences stopped at the plan
stage and the plan-stop card said nothing about the model fallback: every
failure had been logged with the same words, "the model could not be asked",
so a router answering 500, a timed-out call and a box with no endpoint set all
read the same. Now every call ends in ONE outcome with exactly four statuses
(``not_configured`` / ``asked_and_failed`` / ``answer_rejected`` /
``decided``), the normalizer's result and its JSON carry it under
``model_outcome``, and one plain line beginning ``STAMP NORMALIZER:`` says the
same thing so forge can read it from the CLI's stderr when only that survived.

The line shapes pinned below are a contract with forge's parser: change them
here and there together.

Network-free: every asker below is a fake. The one test of the real CLI runs
it as a subprocess with no endpoint configured, which is the path where the
model is never called at all.
"""

from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import sys
import urllib.error
from pathlib import Path
from typing import List, Optional

import pytest
import yaml
from click.testing import CliRunner

import guardkit.orchestrator.stamp_model_fallback as smf
from guardkit.lib.client_env import API_KEY_ENV
from guardkit.orchestrator.stamp_model_fallback import (
    DEFAULT_MODEL_NAME,
    EXAMPLE_ENDPOINT,
    MAX_DETAIL_CHARS,
    MODEL_NAME_ENV,
    MODEL_URL_ENV,
    MODEL_URL_FALLBACK_ENV,
    OUTCOME_ANSWER_REJECTED,
    OUTCOME_ASKED_AND_FAILED,
    OUTCOME_DECIDED,
    OUTCOME_NOT_CONFIGURED,
    OUTCOME_REFUSED_TAIL,
    OUTCOME_STATUSES,
    ModelAnswerRejected,
    ModelOutcome,
    build_default_asker,
    decide_refused_titles,
    decide_refused_titles_with_outcome,
    endpoint_label,
    failure_detail,
    outcome_line,
    parse_answer,
)
from guardkit.orchestrator.stamp_normalizer import normalize_feature

LOGGER = "guardkit.orchestrator.stamp_model_fallback"

#: Two of this week's real refusals, verbatim.
TITLES = [
    "Concurrent requests return the same 7-day data",
    "Concurrent deactivation requests are handled idempotently",
]

NOT_CONFIGURED_DETAIL = (
    "no model endpoint is configured (set GUARDKIT_STAMP_MODEL_URL, or "
    "OPENAI_BASE_URL, to something like http://localhost:4000/v1)"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeAsker:
    """A model call that answers from a script or raises; it names its endpoint
    and model only when told to, like the real one does and a bare callable
    does not."""

    def __init__(
        self,
        answer: object = "",
        *,
        raises: Optional[BaseException] = None,
        endpoint: str = "",
        model: str = "",
    ):
        self.answer = answer
        self.raises = raises
        self.prompts: List[str] = []
        if endpoint:
            self.endpoint = endpoint
        if model:
            self.model = model

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.raises is not None:
            raise self.raises
        return self.answer  # type: ignore[return-value]

    @property
    def calls(self) -> int:
        return len(self.prompts)


def _http_error(
    code: int,
    reason: str,
    body: Optional[bytes] = None,
    url: str = "http://127.0.0.1:4000/v1/chat/completions",
) -> urllib.error.HTTPError:
    fp = io.BytesIO(body) if body is not None else None
    return urllib.error.HTTPError(url, code, reason, {}, fp)  # type: ignore[arg-type]


def _lines(caplog) -> List[str]:
    """Every line the fallback's own logger wrote, verbatim."""
    return [r.getMessage() for r in caplog.records if r.name == LOGGER]


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


def _repo(tmp_path: Path, titles: List[str], *, include_rule_decided: bool = False) -> Path:
    """A repo with one feature file and no HTTP surface, so every title in
    ``titles`` is refused by rule and reaches the fallback."""
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


def _yaml_path(repo: Path) -> Path:
    return repo / ".guardkit" / "features" / "FEAT-CONC.yaml"


# ---------------------------------------------------------------------------
# 1. The four statuses, and each one's shape from a fake asker
# ---------------------------------------------------------------------------


def test_the_four_statuses_are_exactly_these_words():
    """forge's card and parser match on these words; nothing else is ever
    reported."""
    assert OUTCOME_STATUSES == ("not_configured", "asked_and_failed", "answer_rejected", "decided")
    assert OUTCOME_REFUSED_TAIL == "The titles stay refused and nothing was stamped."


def test_no_endpoint_is_not_configured_and_the_line_says_what_to_set(caplog, monkeypatch):
    monkeypatch.delenv(MODEL_URL_ENV, raising=False)
    monkeypatch.delenv(MODEL_URL_FALLBACK_ENV, raising=False)
    assert build_default_asker() is None

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        decided, outcome = decide_refused_titles_with_outcome(TITLES, feature_id="FEAT-X")

    assert decided == {}
    assert outcome == ModelOutcome(OUTCOME_NOT_CONFIGURED, NOT_CONFIGURED_DETAIL, "", "")
    assert outcome.to_dict() == {
        "status": "not_configured",
        "detail": NOT_CONFIGURED_DETAIL,
        "endpoint": "",
        "model": "",
    }
    assert _lines(caplog) == [
        "STAMP NORMALIZER: feature FEAT-X — the model fallback was not asked about "
        "2 title(s) no rule could decide: " + NOT_CONFIGURED_DETAIL + ". "
        "The titles stay refused and nothing was stamped."
    ]
    assert "the model could not be asked" not in caplog.text
    assert "localhost:9000" not in caplog.text  # the example is the router now


def test_an_http_error_reports_the_status_the_host_and_port_and_the_upstreams_message(caplog):
    """The shape from the spec's example: the status code, where it came from
    (the error's own address, host and port only) and the body's message."""
    boom = _http_error(
        500,
        "Internal Server Error",
        b'{"error": {"message": "upstream command exited prematurely", "type": "server_error"}}',
    )
    fake = FakeAsker(raises=boom, endpoint="localhost:4000", model="workhorse")

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        decided, outcome = decide_refused_titles_with_outcome(
            TITLES, ask_model=fake, feature_id="FEAT-X"
        )

    assert decided == {}
    assert fake.calls == 1
    assert outcome.status == OUTCOME_ASKED_AND_FAILED
    assert outcome.detail == "HTTPError 500 from 127.0.0.1:4000 (upstream command exited prematurely)"
    assert outcome.endpoint == "localhost:4000"
    assert outcome.model == "workhorse"
    assert _lines(caplog) == [
        "STAMP NORMALIZER: feature FEAT-X — the model fallback was asked about 2 title(s) "
        "and could not answer: HTTPError 500 from 127.0.0.1:4000 (upstream command exited "
        "prematurely). The titles stay refused and nothing was stamped."
    ]


@pytest.mark.parametrize(
    "body,expected_message",
    [
        (None, "Service Unavailable"),
        (b"", "Service Unavailable"),
        (b"upstream command exited prematurely", "upstream command exited prematurely"),
        (b'{"error": "no model loaded"}', "no model loaded"),
        (b'{"message": "rate limited"}', "rate limited"),
        (b'{"error": {"message": "  bad gateway  "}}', "bad gateway"),
        (b"not json {", "not json {"),
    ],
    ids=["no-body", "empty-body", "plain-text", "json-error-string", "json-message", "json-envelope", "broken-json"],
)
def test_an_http_error_uses_the_body_when_it_has_one_else_the_reason(body, expected_message):
    detail = failure_detail(_http_error(503, "Service Unavailable", body))
    assert detail == f"HTTPError 503 from 127.0.0.1:4000 ({expected_message})"


def test_a_timeout_names_the_type_the_message_and_the_askers_endpoint(caplog):
    fake = FakeAsker(raises=TimeoutError("timed out"), endpoint="localhost:4000", model="workhorse")
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        decided, outcome = decide_refused_titles_with_outcome(TITLES, ask_model=fake)
    assert decided == {}
    assert outcome.status == OUTCOME_ASKED_AND_FAILED
    assert outcome.detail == "TimeoutError from localhost:4000 (timed out)"
    # Without a feature id the "feature X — " part is simply absent.
    assert _lines(caplog) == [
        "STAMP NORMALIZER: the model fallback was asked about 2 title(s) and could not "
        "answer: TimeoutError from localhost:4000 (timed out). The titles stay refused and "
        "nothing was stamped."
    ]


def test_a_bare_callable_that_does_not_name_its_endpoint_gets_a_detail_without_one():
    _, outcome = decide_refused_titles_with_outcome(TITLES, ask_model=FakeAsker(raises=TimeoutError("timed out")))
    assert outcome.detail == "TimeoutError (timed out)"
    assert outcome.endpoint == "" and outcome.model == ""


def test_an_unreachable_endpoint_reports_the_reason_not_urllibs_wrapper():
    boom = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))
    assert str(boom).startswith("<urlopen error")  # what str() would have said
    detail = failure_detail(boom, "localhost:4000")
    assert detail == "URLError from localhost:4000 ([Errno 111] Connection refused)"


def test_an_exception_without_a_message_is_just_its_type():
    assert failure_detail(RuntimeError(), "localhost:4000") == "RuntimeError from localhost:4000"
    assert failure_detail(RuntimeError()) == "RuntimeError"


def test_a_detail_is_one_line_and_bounded():
    long = "a\nb\t\tc " + "x" * (3 * MAX_DETAIL_CHARS)
    detail = failure_detail(RuntimeError(long))
    assert "\n" not in detail and "\t" not in detail
    assert detail.startswith("RuntimeError (a b c xxx")
    assert len(detail) <= MAX_DETAIL_CHARS + len("RuntimeError ()") + 1


def test_a_detail_never_carries_the_key_or_a_url_with_one(monkeypatch, caplog):
    """The key goes into the request and nowhere else — not into a detail that
    lands on Rich's card and in the receipts, however an error phrases itself."""
    key = "dummy-secret-for-this-test-only"
    monkeypatch.setenv(API_KEY_ENV, key)

    loud = RuntimeError(f"POST http://svc:{key}@router:4000/v1 rejected key {key}")
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        _, outcome = decide_refused_titles_with_outcome(TITLES, ask_model=FakeAsker(raises=loud))
    assert outcome.detail == "RuntimeError (POST http://router:4000/v1 rejected key [key])"
    assert key not in json.dumps(outcome.to_dict())
    assert key not in caplog.text

    # An HTTP error raised for a URL with a user-info part names host:port only.
    with_userinfo = _http_error(401, "Unauthorized", url=f"http://svc:{key}@router:4000/v1/chat/completions")
    assert failure_detail(with_userinfo) == "HTTPError 401 from router:4000 (Unauthorized)"


def test_garbage_is_answer_rejected_with_the_parsers_reason(caplog):
    fake = FakeAsker("banana\nbanana\n", endpoint="localhost:4000", model="workhorse")
    with pytest.raises(ModelAnswerRejected) as caught:
        parse_answer("banana\nbanana\n", TITLES)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        decided, outcome = decide_refused_titles_with_outcome(
            TITLES, ask_model=fake, feature_id="FEAT-X"
        )

    assert decided == {}
    assert outcome.status == OUTCOME_ANSWER_REJECTED
    assert outcome.detail == str(caught.value)
    assert "not one of the allowed words" in outcome.detail
    assert outcome.endpoint == "localhost:4000" and outcome.model == "workhorse"
    assert _lines(caplog) == [
        "STAMP NORMALIZER: feature FEAT-X — the model fallback was asked about 2 title(s) "
        f"and its answer was rejected: {outcome.detail}. "
        "The titles stay refused and nothing was stamped."
    ]


def test_a_good_answer_is_decided_with_the_count_and_the_words(caplog):
    fake = FakeAsker("hurl\nexam\n", endpoint="localhost:4000", model="workhorse")
    with caplog.at_level(logging.INFO, logger=LOGGER):
        decided, outcome = decide_refused_titles_with_outcome(
            TITLES, ask_model=fake, feature_id="FEAT-X"
        )

    assert decided == {TITLES[0]: "hurl", TITLES[1]: "exam"}
    assert outcome.status == OUTCOME_DECIDED
    assert outcome.detail == (
        "decided all 2 of them: 'Concurrent requests return the same 7-day data' -> hurl; "
        "'Concurrent deactivation requests are handled idempotently' -> exam"
    )
    assert outcome.endpoint == "localhost:4000" and outcome.model == "workhorse"
    assert _lines(caplog) == [
        "STAMP NORMALIZER: feature FEAT-X — the model fallback was asked about 2 title(s) "
        "and " + outcome.detail + "."
    ]
    assert OUTCOME_REFUSED_TAIL not in caplog.text


def test_nothing_refused_means_no_call_and_no_line(caplog):
    fake = FakeAsker("hurl\n")
    with caplog.at_level(logging.INFO, logger=LOGGER):
        decided, outcome = decide_refused_titles_with_outcome([], ask_model=fake)
    assert decided == {}
    assert fake.calls == 0
    assert outcome.status == OUTCOME_DECIDED
    assert outcome.detail == "nothing to decide: no title was refused"
    assert _lines(caplog) == []


def test_every_outcome_line_begins_with_the_marker_and_is_one_line():
    for status, detail in (
        (OUTCOME_NOT_CONFIGURED, NOT_CONFIGURED_DETAIL),
        (OUTCOME_ASKED_AND_FAILED, "HTTPError 500 from 127.0.0.1:4000 (upstream command exited prematurely)"),
        (OUTCOME_ANSWER_REJECTED, "expected 2 answer(s), one word per title, but the model gave 1: ['hurl']"),
        (OUTCOME_DECIDED, "decided all 2 of them: 'a' -> hurl; 'b' -> exam"),
    ):
        line = outcome_line(ModelOutcome(status, detail), 2, "FEAT-X")
        assert line.startswith("STAMP NORMALIZER: feature FEAT-X — the model fallback ")
        assert "\n" not in line
        assert detail in line
        assert (OUTCOME_REFUSED_TAIL in line) == (status != OUTCOME_DECIDED)
        assert line.count("STAMP NORMALIZER:") == 1


# ---------------------------------------------------------------------------
# 2. The old contract is untouched; the pair never raises
# ---------------------------------------------------------------------------


def test_decide_refused_titles_keeps_its_old_contract():
    good = FakeAsker("hurl\nexam\n")
    assert decide_refused_titles(TITLES, ask_model=good) == {TITLES[0]: "hurl", TITLES[1]: "exam"}
    for bad in (FakeAsker(raises=RuntimeError("x")), FakeAsker("banana\nbanana\n")):
        assert decide_refused_titles(TITLES, ask_model=bad) == {}
        assert decide_refused_titles_with_outcome(TITLES, ask_model=bad)[0] == {}


def test_the_pair_never_raises_whatever_the_call_does():
    for boom in (TimeoutError("t"), RuntimeError("r"), KeyError("k"), _http_error(500, "boom")):
        decided, outcome = decide_refused_titles_with_outcome(["a title"], ask_model=FakeAsker(raises=boom))
        assert decided == {}
        assert outcome.status == OUTCOME_ASKED_AND_FAILED
        assert outcome.detail.startswith(type(boom).__name__)


# ---------------------------------------------------------------------------
# 3. How an address is named, and the real asker names itself without the key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url,label",
    [
        ("http://localhost:4000/v1", "localhost:4000"),
        ("http://localhost:4000/v1/chat/completions", "localhost:4000"),
        ("https://router.example/v1", "router.example:443"),
        ("http://router.example/v1", "router.example:80"),
        ("http://user:secret@10.0.0.5:9000/v1", "10.0.0.5:9000"),
        ("  http://127.0.0.1:4000/v1  ", "127.0.0.1:4000"),
        ("", ""),
        ("not a url", ""),
        ("http://host:notaport/v1", ""),
    ],
)
def test_endpoint_label_is_host_and_port_only(url, label):
    assert endpoint_label(url) == label


def test_the_configured_asker_names_its_endpoint_and_model_and_never_the_key(monkeypatch):
    key = "dummy-secret-for-this-test-only"
    monkeypatch.setenv(API_KEY_ENV, key)
    monkeypatch.setenv(MODEL_URL_ENV, f"http://svc:{key}@localhost:4000/v1")
    monkeypatch.setenv(MODEL_NAME_ENV, "workhorse")

    asker = build_default_asker()
    assert asker is not None
    # The address it will call is the full URL (the request needs it); the two
    # things it REPORTS are the label and the model name, and neither may
    # carry the key however the URL was written.
    assert asker.endpoint == "localhost:4000"
    assert asker.model == "workhorse"
    assert key not in asker.endpoint and key not in asker.model
    assert key not in json.dumps(ModelOutcome(OUTCOME_ASKED_AND_FAILED, "x", asker.endpoint, asker.model).to_dict())


def test_the_configured_asker_defaults_the_model_name_when_the_variable_is_unset(monkeypatch):
    monkeypatch.setenv(MODEL_URL_ENV, "http://localhost:4000/v1")
    monkeypatch.delenv(MODEL_NAME_ENV, raising=False)
    asker = build_default_asker()
    assert asker is not None
    assert asker.model == DEFAULT_MODEL_NAME == "qwen36-workhorse"


def test_the_example_endpoint_and_the_docstrings_point_at_the_router():
    """Rule 17 of the 2026-09-06 spec: the example and the words move to the
    LiteLLM router; the built-in default model name stays, and the docstring
    says the live value is set by forge-prod's environment."""
    assert EXAMPLE_ENDPOINT == "http://localhost:4000/v1"
    assert DEFAULT_MODEL_NAME == "qwen36-workhorse"
    doc = smf.__doc__ or ""
    assert "http://localhost:4000/v1" in doc
    assert "GUARDKIT_STAMP_MODEL=workhorse" in doc
    assert "2026-09-06" in doc
    assert "http://localhost:9000/v1" not in doc  # only mentioned as history, by port


# ---------------------------------------------------------------------------
# 4. The normalizer's result and its JSON carry the outcome
# ---------------------------------------------------------------------------


def test_the_normalizer_result_and_its_json_carry_the_outcome(tmp_path: Path):
    repo = _repo(tmp_path, TITLES)
    fake = FakeAsker(
        raises=_http_error(500, "Internal Server Error", b"upstream command exited prematurely"),
        endpoint="localhost:4000",
        model="workhorse",
    )
    result = normalize_feature(_yaml_path(repo), None, repo, ask_model=fake)

    assert result.refused == TITLES
    assert result.written is False
    assert result.model_outcome == {
        "status": "asked_and_failed",
        "detail": "HTTPError 500 from 127.0.0.1:4000 (upstream command exited prematurely)",
        "endpoint": "localhost:4000",
        "model": "workhorse",
    }
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["model_outcome"] == result.model_outcome


def test_no_refusal_means_no_outcome_in_the_result_or_the_json(tmp_path: Path):
    repo = _repo(tmp_path, [], include_rule_decided=True)
    fake = FakeAsker("hurl\n")
    result = normalize_feature(_yaml_path(repo), None, repo, ask_model=fake)
    assert fake.calls == 0
    assert result.model_outcome is None
    assert json.loads(json.dumps(result.to_dict()))["model_outcome"] is None


def test_a_decided_outcome_rides_the_result_beside_the_model_stamped_titles(tmp_path: Path):
    repo = _repo(tmp_path, TITLES)
    result = normalize_feature(_yaml_path(repo), None, repo, ask_model=FakeAsker("hurl\nhurl\n"))
    assert result.model_stamped == TITLES
    assert result.model_outcome is not None
    assert result.model_outcome["status"] == "decided"
    assert result.model_outcome["detail"].startswith("decided all 2 of them: ")
    assert yaml.safe_load(_yaml_path(repo).read_text())["scenarios"][TITLES[0]] == {"verifier": "hurl"}


def test_the_cli_json_carries_model_outcome(tmp_path: Path, monkeypatch):
    """Through the real command, with the fake wired into the one call that
    asks: the JSON forge parses carries the outcome, and PARTIAL still exits 3."""
    from guardkit.cli.main import cli
    from guardkit.orchestrator import stamp_normalizer

    real = stamp_normalizer.normalize_feature

    def _with_fake(*args, **kwargs):
        kwargs["ask_model"] = FakeAsker("banana\nbanana\n", endpoint="localhost:4000", model="workhorse")
        return real(*args, **kwargs)

    monkeypatch.setattr(stamp_normalizer, "normalize_feature", _with_fake)
    repo = _repo(tmp_path, TITLES)

    out = CliRunner().invoke(
        cli, ["qa", "normalize-stamps", "--feature", "FEAT-CONC", "--repo", str(repo), "--dry-run"]
    )
    assert out.exit_code == 3, out.output
    payload = json.loads(out.output[out.output.index('{\n  "feature_id"'):])
    assert payload["refused"] == TITLES
    assert payload["model_outcome"]["status"] == "answer_rejected"
    assert "not one of the allowed words" in payload["model_outcome"]["detail"]
    assert payload["model_outcome"]["endpoint"] == "localhost:4000"
    assert payload["model_outcome"]["model"] == "workhorse"


def test_the_real_cli_prints_the_outcome_line_on_stderr_and_the_json_on_stdout(tmp_path: Path):
    """The whole path as forge sees it: the CLI as a subprocess, no endpoint
    configured, so the model is never called. The line reaches stderr under
    the CLI's default logging (behind ``WARNING:<logger>:``), and the JSON on
    stdout carries the same outcome."""
    repo = _repo(tmp_path, TITLES)
    env = dict(os.environ)
    env[MODEL_URL_ENV] = ""
    env.pop(MODEL_URL_FALLBACK_ENV, None)
    env.pop(API_KEY_ENV, None)
    worktree = Path(__file__).resolve().parents[2]  # this checkout's guardkit, not another's
    proc = subprocess.run(
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
        ],
        cwd=str(worktree),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 3, proc.stderr

    expected = (
        "STAMP NORMALIZER: feature FEAT-CONC — the model fallback was not asked about "
        "2 title(s) no rule could decide: " + NOT_CONFIGURED_DETAIL + ". "
        "The titles stay refused and nothing was stamped."
    )
    stderr_lines = proc.stderr.splitlines()
    matching = [line for line in stderr_lines if expected in line]
    assert matching, proc.stderr
    assert matching[0] == "WARNING:guardkit.orchestrator.stamp_model_fallback:" + expected
    assert "the model could not be asked" not in proc.stderr

    payload = json.loads(proc.stdout[proc.stdout.index("{"):])
    assert payload["model_outcome"] == {
        "status": "not_configured",
        "detail": NOT_CONFIGURED_DETAIL,
        "endpoint": "",
        "model": "",
    }
    assert payload["refused"] == TITLES
