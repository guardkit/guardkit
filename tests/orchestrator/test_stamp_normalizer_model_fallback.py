"""THE MODEL FALLBACK for the routing law's refused titles (RULED 2026-08-31).

What is being proved here, in plain terms. Rules R1-R10 decide almost every
scenario's proving ground. When no rule matches, the law refuses loudly and
names the title. Since Rich's 2026-08-31 ruling (repair item 11) those refused
titles — and ONLY those — are handed to a model with the closed list and the
rules' own summary; it answers one word per title, the word is checked against
the closed list, and anything else leaves the titles refused exactly as before.

The fixture is this week's real refusals, pinned verbatim (two live planning
runs died on them):

    Concurrent requests return the same 7-day data
    Concurrent deactivation requests are handled idempotently
    Concurrent requests return consistent domain lists
    Concurrent deactivation requests are handled gracefully

Clause (h) was hand-widened on 2026-08-28 for exactly this idiom and still
refuses the first two ("the same", not "identical"; "idempotently", not
"gracefully") — the argument for this lane, and pinned as a test below.

Network-free by construction: every test injects a fake model call, and the
one test of the real HTTP shape fakes ``urlopen``. Nothing here reaches a
model, an endpoint, or a broker.
"""

from __future__ import annotations

import json
import logging
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional

import pytest
import yaml
from click.testing import CliRunner

from guardkit.orchestrator.stamp_model_fallback import (
    OFFERABLE_HOMES,
    DEFAULT_MODEL_NAME,
    DEFAULT_TIMEOUT_S,
    MAX_TIMEOUT_S,
    MODEL_NAME_ENV,
    MODEL_RULE,
    MODEL_TIMEOUT_ENV,
    MODEL_URL_ENV,
    MODEL_URL_FALLBACK_ENV,
    ModelAnswerRejected,
    build_default_asker,
    build_prompt,
    completions_url,
    decide_refused_titles,
    parse_answer,
    rule_table,
)
from guardkit.orchestrator.stamp_normalizer import (
    NormalizeContext,
    classify_scenario,
    normalize_feature,
)
from guardkit.orchestrator.verifier_stamp import VERIFIER_HOMES

# ---------------------------------------------------------------------------
# This week's real refusals, verbatim
# ---------------------------------------------------------------------------

REFUSED_THIS_WEEK = [
    "Concurrent requests return the same 7-day data",
    "Concurrent deactivation requests are handled idempotently",
    "Concurrent requests return consistent domain lists",
    "Concurrent deactivation requests are handled gracefully",
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

BASE_YAML = (
    "id: FEAT-CONC\n"
    "name: Concurrency scenarios\n"
    "# a comment the writer must keep\n"
    "description: the four titles two runs died on\n"
    "status: planned\n"
    "feature_files:\n"
    "  - features/concurrency/concurrency.feature\n"
)


def _feature_text(titles: List[str], *, include_rule_decided: bool = False) -> str:
    body = "Feature: Concurrency\n"
    if include_rule_decided:
        body += f"  Scenario: {DECIDED_BY_A_RULE}\n    {DECIDED_STEPS}\n"
    for title in titles:
        body += f"  Scenario: {title}\n    {STEPS}\n"
    return body


def _repo(
    tmp_path: Path,
    titles: List[str],
    *,
    http: bool = False,
    include_rule_decided: bool = False,
) -> Path:
    """A repo with one feature file. ``http=False`` by default: R9 (hurl) is
    gated on an HTTP surface, and without one every title below refuses."""
    repo = tmp_path / "repo"
    (repo / ".guardkit" / "features").mkdir(parents=True)
    (repo / "features" / "concurrency").mkdir(parents=True)
    (repo / "features" / "concurrency" / "concurrency.feature").write_text(
        _feature_text(titles, include_rule_decided=include_rule_decided)
    )
    (repo / ".guardkit" / "features" / "FEAT-CONC.yaml").write_text(BASE_YAML)
    if http:
        (repo / "qa" / "gates").mkdir(parents=True)
        (repo / "qa" / "gates" / "registry.yaml").write_text(
            "format_version: '1.0'\ngates:\n  - id: hurl-twins\n"
            "    path: qa/gates/hurl_twin_gate.py\n"
        )
    return repo


def _yaml_path(repo: Path) -> Path:
    return repo / ".guardkit" / "features" / "FEAT-CONC.yaml"


class FakeModel:
    """A model call that records every prompt and answers from a script."""

    def __init__(self, answer: object = "", *, raises: Optional[Exception] = None):
        self.answer = answer
        self.raises = raises
        self.prompts: List[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.raises is not None:
            raise self.raises
        return self.answer  # type: ignore[return-value]

    @property
    def calls(self) -> int:
        return len(self.prompts)


def _answers(*words: str) -> str:
    return "\n".join(words) + "\n"


# ---------------------------------------------------------------------------
# The datum: why a hand-maintained synonym list cannot do this job
# ---------------------------------------------------------------------------


def test_the_datum_clause_h_was_widened_and_still_refuses_two_of_the_four():
    """Pinned, because it is the whole argument for this lane: on a repo WITH
    an HTTP surface clause (h) decides the two phrasings it was written for
    and still refuses "the same" and "idempotently"."""
    ctx = NormalizeContext(repo_has_http_surface=True, http_surface_evidence="test")
    decided = {
        title: classify_scenario(title, STEPS, ctx) for title in REFUSED_THIS_WEEK
    }
    assert decided["Concurrent requests return consistent domain lists"].verifier == "hurl"
    assert decided["Concurrent deactivation requests are handled gracefully"].verifier == "hurl"
    assert decided["Concurrent requests return the same 7-day data"] is None
    assert decided["Concurrent deactivation requests are handled idempotently"] is None


# ---------------------------------------------------------------------------
# 1. Only the refused titles are asked about; a rule's title never goes near it
# ---------------------------------------------------------------------------


def test_the_four_refused_titles_become_hurl_and_are_marked_model_decided(tmp_path: Path):
    fake = FakeModel(_answers("hurl", "hurl", "hurl", "hurl"))
    repo = _repo(tmp_path, REFUSED_THIS_WEEK)
    result = normalize_feature(_yaml_path(repo), None, repo, ask_model=fake)

    assert fake.calls == 1
    assert result.refused == []
    assert result.model_stamped == REFUSED_THIS_WEEK
    for title in REFUSED_THIS_WEEK:
        assert result.stamped[title] == "hurl"
        assert result.rules[title] == MODEL_RULE  # never an R-number
        assert "the model decided it" in result.reasons[title]
    assert result.to_dict()["model_stamped"] == REFUSED_THIS_WEEK
    assert result.written is True

    data = yaml.safe_load(_yaml_path(repo).read_text())
    for title in REFUSED_THIS_WEEK:
        assert data["scenarios"][title] == {"verifier": "hurl"}


def test_a_title_a_rule_decided_never_goes_near_the_model(tmp_path: Path):
    """The rule-decided title is stamped by its rule and does not appear in the
    prompt; only the refused titles do."""
    fake = FakeModel(_answers("hurl", "hurl", "hurl", "hurl"))
    repo = _repo(tmp_path, REFUSED_THIS_WEEK, include_rule_decided=True)
    result = normalize_feature(_yaml_path(repo), None, repo, ask_model=fake)

    assert result.stamped[DECIDED_BY_A_RULE] == "probe:process"
    assert result.rules[DECIDED_BY_A_RULE] == "R1"
    assert DECIDED_BY_A_RULE not in result.model_stamped
    assert fake.calls == 1
    assert DECIDED_BY_A_RULE not in fake.prompts[0]
    for title in REFUSED_THIS_WEEK:
        assert title in fake.prompts[0]


def test_with_an_http_surface_only_the_two_clause_h_misses_reach_the_model(tmp_path: Path):
    """The strongest form of the same law: the two titles clause (h) DOES
    decide are stamped by R9 and never sent; the two it misses are."""
    fake = FakeModel(_answers("hurl", "hurl"))
    repo = _repo(tmp_path, REFUSED_THIS_WEEK, http=True)
    result = normalize_feature(_yaml_path(repo), None, repo, ask_model=fake)

    assert result.model_stamped == [
        "Concurrent requests return the same 7-day data",
        "Concurrent deactivation requests are handled idempotently",
    ]
    assert result.rules["Concurrent requests return consistent domain lists"] == "R9"
    assert fake.calls == 1
    assert "Concurrent requests return consistent domain lists" not in fake.prompts[0]
    assert "Concurrent deactivation requests are handled gracefully" not in fake.prompts[0]


def test_nothing_refused_means_the_model_is_not_asked_at_all(tmp_path: Path):
    fake = FakeModel(_answers("hurl"))
    repo = _repo(tmp_path, [], include_rule_decided=True)
    result = normalize_feature(_yaml_path(repo), None, repo, ask_model=fake)
    assert result.stamped == {DECIDED_BY_A_RULE: "probe:process"}
    assert fake.calls == 0
    assert result.model_stamped == []


# ---------------------------------------------------------------------------
# 2. The prompt
# ---------------------------------------------------------------------------


def test_the_prompt_carries_the_closed_list_the_rules_and_the_titles():
    prompt = build_prompt(REFUSED_THIS_WEEK)
    # The offered list, not the whole closed list: toolchain is deliberately
    # withheld because the model has no test node to name (2026-08-31).
    assert ", ".join(OFFERABLE_HOMES) in prompt
    for entry in rule_table():
        assert f"{entry.rule} -> {entry.home}:" in prompt
    for number, title in enumerate(REFUSED_THIS_WEEK, 1):
        assert f"  {number}. {title}" in prompt
    assert "Answer with exactly 4 line(s), one line per title, in the same order." in prompt
    assert "ONE word from the closed list" in prompt
    assert "operator only for work a person has to do by hand" in prompt


def test_the_rule_summary_is_read_from_the_rules_module_and_cannot_drift():
    """The summary the model is given is derived from the rules module's own
    docstring — and every row's home is what the rule really returns."""
    table = rule_table()
    assert [entry.rule for entry in table] == [
        "R1", "R2", "R3", "R7", "R4", "R5", "R6", "R8", "R9", "R10",
    ]
    homes = {entry.rule: entry.home for entry in table}
    assert set(homes.values()) <= set(VERIFIER_HOMES)

    http = NormalizeContext(repo_has_http_surface=True, http_surface_evidence="test")
    real_examples = {
        "R1": ("The count degrades honestly", "Given the database is unavailable\nThen it degrades"),
        "R2": ("A freshly started process answers", "Given the service was just started\nThen it answers"),
        "R3": ("The smoke run leaves no trace", "Given a throwaway sandbox\nThen no trace should remain"),
        "R7": ("The Coach explains its verdict", "When the Coach runs\nThen the coach should explain the miss"),
        "R4": ("A heartbeat is published", "When the agent runs\nThen a heartbeat is published to the fleet subject"),
        "R5": ("The app shows the home screen", "When I tap the button\nThen the home screen appears"),
        "R6": ("The page loads in the browser", "When the page is opened in the browser\nThen it renders"),
        "R9": ("Write methods are rejected", "When I send a POST request to \"/time\"\nThen the status code should be 405"),
        "R10": ("The runbook is walked", "Given an operator follows the runbook\nThen the evidence is filed"),
    }
    for rule, (title, steps) in real_examples.items():
        home = classify_scenario(title, steps, http)
        assert home is not None, f"{rule} example no longer classifies"
        assert home.rule == rule, f"{rule} example now matches {home.rule}"
        assert home.verifier == homes[rule], (
            f"the summary says {rule} -> {homes[rule]} but the rule returns "
            f"{home.verifier}: the model would be told something untrue"
        )

    # R8 is the plan-driven rule: its home is proved through the plan context.
    r8 = classify_scenario(
        "The count starts empty",
        "Given no users\nThen the count is zero",
        NormalizeContext(plan_test_refs={"The count starts empty": "test_count_empty"}),
    )
    assert r8 is not None and r8.rule == "R8" and r8.verifier == homes["R8"]


# ---------------------------------------------------------------------------
# 3. A bogus answer is the same loud refusal — never a guess
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "answer,why",
    [
        ("probably hurl\nhurl\nhurl\nhurl\n", "a sentence, not a word"),
        ("", "an empty answer"),
        ("banana\nbanana\nbanana\nbanana\n", "a made-up word"),
        ("hurl\nhurl\n", "two answers for four titles"),
        ("hurl\nhurl\nhurl\nhurl\nhurl\n", "five answers for four titles"),
        ("hurl, hurl, hurl, hurl\n", "one line for four titles"),
        ("1. hurl\n2. hurl\n3. hurl\n4. hurl\n", "numbered lines"),
        ("hurl\nexam\nbanana\nhurl\n", "one bad word poisons the whole answer"),
    ],
)
def test_a_bogus_answer_leaves_every_title_refused(tmp_path: Path, caplog, answer, why):
    fake = FakeModel(answer)
    repo = _repo(tmp_path, REFUSED_THIS_WEEK)
    with caplog.at_level(logging.WARNING):
        result = normalize_feature(_yaml_path(repo), None, repo, ask_model=fake)

    assert result.refused == REFUSED_THIS_WEEK, why
    assert result.stamped == {} and result.model_stamped == []
    assert result.written is False
    assert "the model's answer was rejected" in caplog.text
    assert "UNDECIDABLE" in caplog.text  # the law's own loud refusal, unchanged
    assert "scenarios" not in (yaml.safe_load(_yaml_path(repo).read_text()) or {})


def test_a_word_outside_the_closed_list_can_never_become_a_stamp():
    with pytest.raises(ModelAnswerRejected, match="not one of the allowed words"):
        parse_answer("banana\n", ["a title"])


def test_the_answer_may_be_spaced_or_capitalised_but_not_decorated():
    assert parse_answer("  HURL \n", ["t"]) == {"t": "hurl"}
    assert parse_answer("probe:bus\n", ["t"]) == {"t": "probe:bus"}
    with pytest.raises(ModelAnswerRejected):
        parse_answer("`hurl`\n", ["t"])
    with pytest.raises(ModelAnswerRejected):
        parse_answer("hurl.\n", ["t"])


def test_a_thinking_model_may_wrap_its_answer_but_the_answer_still_has_to_be_words():
    assert parse_answer("<think>weighing it up</think>\nhurl\nexam\n", ["a", "b"]) == {
        "a": "hurl",
        "b": "exam",
    }
    with pytest.raises(ModelAnswerRejected):
        parse_answer("<think>hurl</think>\nI think it is hurl\n", ["a"])


def test_an_answer_that_is_not_text_is_rejected():
    with pytest.raises(ModelAnswerRejected, match="was not text"):
        parse_answer(None, ["a title"])


# ---------------------------------------------------------------------------
# 4. Every way the call can fail is the old behaviour, plus one plain line
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "boom",
    [
        TimeoutError("timed out"),
        urllib.error.URLError("connection refused"),
        urllib.error.HTTPError("http://localhost:9000/v1", 500, "server error", {}, None),
        ValueError("the reply carried no answer"),
        RuntimeError("something else entirely"),
    ],
    ids=["timeout", "unreachable", "http-error", "malformed-reply", "unknown"],
)
def test_a_model_that_cannot_answer_leaves_the_refusal_exactly_as_it_was(
    tmp_path: Path, caplog, boom
):
    fake = FakeModel(raises=boom)
    repo = _repo(tmp_path, REFUSED_THIS_WEEK)
    with caplog.at_level(logging.WARNING):
        result = normalize_feature(_yaml_path(repo), None, repo, ask_model=fake)

    assert result.refused == REFUSED_THIS_WEEK
    assert result.stamped == {} and result.model_stamped == []
    assert result.written is False
    assert "the model could not be asked" in caplog.text
    assert "nothing was stamped" in caplog.text
    for title in REFUSED_THIS_WEEK:
        assert title in caplog.text  # the law still names every refused title


def test_no_endpoint_configured_means_the_model_is_never_asked(tmp_path: Path, caplog, monkeypatch):
    monkeypatch.delenv(MODEL_URL_ENV, raising=False)
    monkeypatch.delenv(MODEL_URL_FALLBACK_ENV, raising=False)
    assert build_default_asker() is None

    repo = _repo(tmp_path, REFUSED_THIS_WEEK)
    with caplog.at_level(logging.WARNING):
        result = normalize_feature(_yaml_path(repo), None, repo)  # no fake: the real path

    assert result.refused == REFUSED_THIS_WEEK
    assert result.stamped == {} and result.model_stamped == []
    assert "no model endpoint is configured" in caplog.text
    assert "The titles stay refused and nothing was stamped." in caplog.text


def test_an_endpoint_set_to_an_empty_value_is_not_configured(monkeypatch):
    monkeypatch.setenv(MODEL_URL_ENV, "")
    monkeypatch.setenv(MODEL_URL_FALLBACK_ENV, "http://localhost:9000/v1")
    assert build_default_asker() is None


def test_decide_refused_titles_never_raises_whatever_the_call_does():
    for boom in (TimeoutError("t"), RuntimeError("r"), KeyError("k")):
        assert decide_refused_titles(["a title"], ask_model=FakeModel(raises=boom)) == {}


# ---------------------------------------------------------------------------
# 5. `operator` from the model is surfaced, never silent
# ---------------------------------------------------------------------------


def _cli_with(fake: "FakeModel", monkeypatch):
    """Run the CLI with the fake model wired into the one call that asks."""
    from guardkit.orchestrator import stamp_normalizer

    real = stamp_normalizer.normalize_feature

    def _with_fake(*args, **kwargs):
        kwargs["ask_model"] = fake
        return real(*args, **kwargs)

    monkeypatch.setattr(stamp_normalizer, "normalize_feature", _with_fake)


def test_an_operator_answer_is_stamped_and_named_everywhere(tmp_path: Path, caplog, monkeypatch):
    title = REFUSED_THIS_WEEK[0]
    fake = FakeModel(_answers("operator"))
    repo = _repo(tmp_path, [title])
    with caplog.at_level(logging.WARNING):
        # dry-run: the CLI below re-runs the same feature, and a written stamp
        # is never asked about twice.
        result = normalize_feature(_yaml_path(repo), None, repo, dry_run=True, ask_model=fake)

    assert result.stamped[title] == "operator"
    assert result.operator_stamped == [title]
    assert result.model_stamped == [title]
    assert "attended human work" in caplog.text
    assert "decided by the model" in caplog.text

    from guardkit.cli.main import cli

    _cli_with(FakeModel(_answers("operator")), monkeypatch)
    out = CliRunner().invoke(
        cli, ["qa", "normalize-stamps", "--feature", "FEAT-CONC", "--repo", str(repo), "--dry-run"]
    )
    assert out.exit_code == 0, out.output
    assert "minted `operator`" in out.output
    assert "decided by the model" in out.output
    assert title in out.output


# ---------------------------------------------------------------------------
# 6. Provenance: a model-decided stamp says so wherever stamps are recorded
# ---------------------------------------------------------------------------


def test_the_yaml_marks_a_model_decided_stamp_and_leaves_rule_stamps_as_they_are(tmp_path: Path):
    fake = FakeModel(_answers("hurl", "hurl", "hurl", "hurl"))
    repo = _repo(tmp_path, REFUSED_THIS_WEEK, include_rule_decided=True)
    normalize_feature(_yaml_path(repo), None, repo, ask_model=fake)

    text = _yaml_path(repo).read_text()
    assert "# a comment the writer must keep" in text  # nothing else moved
    for title in REFUSED_THIS_WEEK:
        marker = "# stamped by the model"
        entry = text.index(json.dumps(title))
        assert marker in text[:entry], f"no model-decided note above {title!r}"
    # The rule-decided stamp keeps exactly today's shape: no note above it.
    rule_entry = text.index(json.dumps(DECIDED_BY_A_RULE))
    line_before = text[:rule_entry].rstrip().rsplit("\n", 1)[-1].strip()
    assert not line_before.startswith("# stamped by the model")

    data = yaml.safe_load(text)  # a comment is not data — the map is unchanged
    assert data["scenarios"][DECIDED_BY_A_RULE] == {"verifier": "probe:process"}
    assert data["scenarios"][REFUSED_THIS_WEEK[0]] == {"verifier": "hurl"}


def test_the_cli_json_carries_the_model_decided_titles_and_the_stderr_echo(tmp_path: Path, monkeypatch):
    _cli_with(FakeModel(_answers("hurl", "hurl", "hurl", "hurl")), monkeypatch)
    repo = _repo(tmp_path, REFUSED_THIS_WEEK)

    from guardkit.cli.main import cli

    out = CliRunner().invoke(
        cli, ["qa", "normalize-stamps", "--feature", "FEAT-CONC", "--repo", str(repo), "--dry-run"]
    )
    assert out.exit_code == 0, out.output
    assert "the model decided 4 scenario(s) no rule could decide" in out.output
    payload = json.loads(out.output[out.output.index('{\n  "feature_id"'):])
    assert payload["model_stamped"] == REFUSED_THIS_WEEK
    assert payload["refused"] == []


# ---------------------------------------------------------------------------
# 7. Configuration and the real call's shape (faked at the socket)
# ---------------------------------------------------------------------------


def test_the_timeout_is_short_enough_that_a_hung_endpoint_cannot_stall_a_run():
    assert 10.0 <= DEFAULT_TIMEOUT_S <= 20.0


def test_the_endpoint_falls_back_to_openai_base_url_and_the_model_name_has_a_default(monkeypatch):
    monkeypatch.delenv(MODEL_URL_ENV, raising=False)
    monkeypatch.setenv(MODEL_URL_FALLBACK_ENV, "http://localhost:9000/v1")
    monkeypatch.delenv(MODEL_NAME_ENV, raising=False)
    assert build_default_asker() is not None
    assert DEFAULT_MODEL_NAME == "qwen36-workhorse"


def test_completions_url_is_built_once_and_is_not_doubled():
    assert completions_url("http://localhost:9000/v1") == "http://localhost:9000/v1/chat/completions"
    assert completions_url("http://localhost:9000/v1/") == "http://localhost:9000/v1/chat/completions"
    assert (
        completions_url("http://localhost:9000/v1/chat/completions")
        == "http://localhost:9000/v1/chat/completions"
    )


@pytest.mark.parametrize(
    "value,expected",
    [("", DEFAULT_TIMEOUT_S), ("not-a-number", DEFAULT_TIMEOUT_S), ("5", 5.0), ("9999", MAX_TIMEOUT_S)],
)
def test_the_timeout_is_read_from_the_environment_and_clamped(monkeypatch, value, expected):
    from guardkit.orchestrator.stamp_model_fallback import _timeout_seconds

    monkeypatch.setenv(MODEL_TIMEOUT_ENV, value)
    assert _timeout_seconds() == expected


def test_the_default_call_posts_the_prompt_to_the_endpoint_with_a_timeout(monkeypatch):
    """The wire shape, proved offline: ``urlopen`` is faked, nothing is sent."""
    from guardkit.orchestrator import stamp_model_fallback as fallback

    seen: Dict[str, object] = {}

    class _Response:
        def read(self):
            return json.dumps(
                {"choices": [{"message": {"role": "assistant", "content": "hurl\n"}}]}
            ).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return _Response()

    monkeypatch.setenv(MODEL_URL_ENV, "http://localhost:9000/v1")
    monkeypatch.setenv(MODEL_NAME_ENV, "qwen36-workhorse")
    monkeypatch.setenv(MODEL_TIMEOUT_ENV, "12")
    monkeypatch.setattr(fallback.urllib.request, "urlopen", _fake_urlopen)

    asker = build_default_asker()
    assert asker is not None
    assert asker("the prompt") == "hurl\n"
    assert seen["url"] == "http://localhost:9000/v1/chat/completions"
    assert seen["timeout"] == 12.0
    body = seen["body"]
    assert body["model"] == "qwen36-workhorse"
    assert body["temperature"] == 0.0
    assert body["messages"] == [{"role": "user", "content": "the prompt"}]


def test_a_reply_without_an_answer_is_a_malformed_reply_not_a_stamp(monkeypatch):
    from guardkit.orchestrator import stamp_model_fallback as fallback

    class _Response:
        def read(self):
            return json.dumps({"error": "no model loaded"}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setenv(MODEL_URL_ENV, "http://localhost:9000/v1")
    monkeypatch.setattr(fallback.urllib.request, "urlopen", lambda *a, **k: _Response())

    asker = build_default_asker()
    assert asker is not None
    assert decide_refused_titles(["a title"], ask_model=asker) == {}


# --- toolchain is offered to nobody (2026-08-31, the coach's finding) ---------
# A toolchain stamp must name the test that proves the scenario. The model has no
# test to name, so an accepted toolchain answer died later in the writer, taking
# the feature's correctly rule-decided stamps down with it. It is now absent from
# the words offered, said plainly in the prompt, and refused if answered anyway.

def test_toolchain_is_not_among_the_words_offered():
    from guardkit.orchestrator.stamp_model_fallback import OFFERABLE_HOMES
    assert "toolchain" not in OFFERABLE_HOMES
    assert "hurl" in OFFERABLE_HOMES and "operator" in OFFERABLE_HOMES


def test_the_prompt_tells_the_model_not_to_answer_toolchain():
    from guardkit.orchestrator.stamp_model_fallback import build_prompt
    prompt = build_prompt(["Concurrent requests are handled idempotently"])
    assert "Never answer toolchain." in prompt


def test_a_toolchain_answer_is_refused_and_says_why():
    from guardkit.orchestrator.stamp_model_fallback import (
        ModelAnswerRejected, parse_answer)
    import pytest
    with pytest.raises(ModelAnswerRejected) as caught:
        parse_answer("toolchain\n", ["Concurrent requests are handled idempotently"])
    assert "no test to name" in str(caught.value)
    assert "stays refused" in str(caught.value)
