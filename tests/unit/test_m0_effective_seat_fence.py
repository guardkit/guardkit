"""The M0 effective-seat fence — leg-invocation stage-2 design §3 (GA1).

Stage 1 shipped a fence that judged a *supplied* ``--model`` alias. The pipeline
never supplies one (zero ``--model`` hits in ``forge/src``), so on the live path
the seat rode ``model=None`` into DeepAgents, which constructs
``ChatAnthropic(model_name="claude-sonnet-4-6")`` (``deepagents/graph.py:145-153``).
Only a missing ``ANTHROPIC_API_KEY`` stopped the crossing. Stage 2 moves the rule
to the one chokepoint every real model call passes through — ``select_harness``.

What this suite drives for real (no mock of the thing under test): the real
:func:`guardkit.orchestrator.harness.selector.select_harness`, the real
:class:`~guardkit.orchestrator.harness.sdk_harness.ClaudeSDKHarness`
construction on the passing path, the real process environment via
``monkeypatch``, and the real receipt builder in
:mod:`guardkit.orchestrator.review_runner`.

Covered:

* rule part (a) — ``model=None`` is ITSELF the violation, and the refusal names
  the concrete default per branch (langgraph AND sdk);
* rule part (b) — a frontier provider prefix refuses;
* rule part (c) — a bare alias / ``openai:`` prefix needs ``OPENAI_BASE_URL``
  set to a host on the LOCAL-SEAT ALLOWLIST (corrected 2026-08-02: the shipped
  rule was a one-vendor ``openai.com`` denylist, which five real vendor hosts
  walked straight through and a scheme-less URL defeated entirely);
* the verdict record is WORST-WINS, so a late local PASS cannot bury an earlier
  frontier construction on the receipt line;
* the escape hatch proceeds, and is LOUD on stderr;
* the branch inventory — the fence sits before every construction branch, and
  the "no real model call" exemption seam has no members today;
* the verdict record, and the receipt REPORTING it instead of NOT-EVALUATED;
* the stage-1 names still import from ``guardkit.cli.task_review`` unchanged.
"""

from __future__ import annotations

import pytest

from guardkit.orchestrator import m0_fence
from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness.selector import select_harness
from guardkit.orchestrator.m0_fence import (
    FRONTIER_ESCAPE_ENV,
    LANGGRAPH_DEFAULT_SEAT,
    LOCAL_SEAT_HOSTS_ENV,
    VERDICT_ALLOWED_BY_ESCAPE,
    VERDICT_NOT_JUDGED,
    VERDICT_PASS,
    VERDICT_REFUSED,
    default_seat_for,
    judge_effective_seat,
)

FLEET_BASE_URL = "http://127.0.0.1:9/v1"
FLEET_SEAT = "qwen36-workhorse"

#: Isolated env-var names so these tests never read the operator's real
#: ``GUARDKIT_HARNESS``.
SDK_ENV = "GUARDKIT_HARNESS_M0FENCE_SDK"
LG_ENV = "GUARDKIT_HARNESS_M0FENCE_LG"


@pytest.fixture(autouse=True)
def _fence_armed(monkeypatch):
    """Every test starts with the fence armed and no recorded verdict."""
    monkeypatch.delenv(FRONTIER_ESCAPE_ENV, raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv(LOCAL_SEAT_HOSTS_ENV, raising=False)
    monkeypatch.delenv(SDK_ENV, raising=False)
    monkeypatch.delenv(LG_ENV, raising=False)
    m0_fence.reset_verdict()
    yield
    m0_fence.reset_verdict()


def _sdk_kwargs(**overrides):
    """The SDK harness's required constructor kwargs (real construction)."""
    base = {
        "sdk_timeout_seconds": 60,
        "allowed_tools": ["Read"],
        "permission_mode": "acceptEdits",
        "max_turns": 5,
        "model": FLEET_SEAT,
    }
    base.update(overrides)
    return base


# ===========================================================================
# 1. Rule part (a) — model=None is itself the violation
# ===========================================================================


class TestPartAModelNoneIsTheViolation:
    def test_langgraph_none_names_the_concrete_deepagents_default(self):
        verdict = judge_effective_seat(None, harness="langgraph")
        assert verdict.status == VERDICT_REFUSED
        # The point of part (a): say what would ACTUALLY have been called.
        assert "claude-sonnet-4-6" in verdict.effective_model
        assert "claude-sonnet-4-6" in verdict.detail

    def test_sdk_none_names_the_bundled_cli_default(self):
        verdict = judge_effective_seat(None, harness="sdk")
        assert verdict.status == VERDICT_REFUSED
        assert "bundled claude-agent-sdk CLI default" in verdict.effective_model

    def test_langgraph_and_sdk_defaults_are_not_the_same_string(self):
        """A single generic 'harness default' phrase would hide the difference."""
        assert default_seat_for("langgraph") != default_seat_for("sdk")

    def test_empty_string_model_is_the_same_absence_as_none(self):
        verdict = judge_effective_seat("   ", harness="langgraph")
        assert verdict.status == VERDICT_REFUSED
        assert LANGGRAPH_DEFAULT_SEAT in verdict.effective_model

    def test_select_harness_refuses_a_nameless_langgraph_seat(self, tmp_path):
        """The live crossing shape: no --model, langgraph branch, real selector."""
        with pytest.raises(AgentInvocationError) as exc:
            select_harness(env_var=LG_ENV, cwd=tmp_path)  # env unset -> langgraph
        assert "M0 fence" in str(exc.value)
        assert "claude-sonnet-4-6" in str(exc.value)

    def test_the_fence_fires_before_the_langgraph_cwd_check(self):
        """Ordering proof: the fence is inserted BEFORE either harness branch.

        Without ``cwd=`` the langgraph branch raises its own
        AgentInvocationError. If the fence ran after the branch we would see
        that message instead of the M0 one.
        """
        with pytest.raises(AgentInvocationError) as exc:
            select_harness(env_var=LG_ENV)
        assert "M0 fence" in str(exc.value)
        assert "requires a `cwd=` kwarg" not in str(exc.value)

    def test_select_harness_refuses_a_nameless_sdk_seat(self, monkeypatch):
        monkeypatch.setenv(SDK_ENV, "sdk")
        with pytest.raises(AgentInvocationError) as exc:
            select_harness(env_var=SDK_ENV, **_sdk_kwargs(model=None))
        assert "M0 fence" in str(exc.value)
        assert "bundled claude-agent-sdk CLI default" in str(exc.value)

    def test_a_nameless_seat_is_refused_even_with_a_local_base_url(
        self, monkeypatch
    ):
        """OPENAI_BASE_URL does not rescue part (a) — None never routes there.

        ``model=None`` reaches DeepAgents' *Anthropic* default, which ignores
        ``OPENAI_BASE_URL`` entirely. A fence that let a local base URL excuse a
        missing model would be exactly the silent breach stage 2 exists to stop.
        """
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        assert judge_effective_seat(None, harness="langgraph").status == VERDICT_REFUSED


# ===========================================================================
# 2. Rule part (b) — a frontier provider prefix refuses
# ===========================================================================


class TestPartBFrontierPrefix:
    @pytest.mark.parametrize(
        "model",
        [
            "anthropic:claude-opus-4",
            "anthropic/claude-sonnet-4-5",
            "google_genai:gemini-2.5-pro",
            "bedrock:anthropic.claude-v2",
            "xai:grok-4",
            "mistralai:mistral-large",
        ],
    )
    def test_frontier_prefix_refuses_on_both_branches(self, model):
        for harness in ("langgraph", "sdk"):
            verdict = judge_effective_seat(model, harness=harness)
            assert verdict.status == VERDICT_REFUSED, (harness, model)
            assert model in verdict.detail
            assert verdict.effective_model == model

    def test_frontier_prefix_refuses_even_with_a_local_base_url(self, monkeypatch):
        """A local OPENAI_BASE_URL says nothing about an ``anthropic:`` call."""
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        verdict = judge_effective_seat("anthropic:claude-opus-4", harness="sdk")
        assert verdict.status == VERDICT_REFUSED

    def test_select_harness_refuses_a_frontier_prefix(self, monkeypatch):
        monkeypatch.setenv(SDK_ENV, "sdk")
        with pytest.raises(AgentInvocationError) as exc:
            select_harness(env_var=SDK_ENV, **_sdk_kwargs(model="anthropic:claude-opus-4"))
        assert "anthropic:claude-opus-4" in str(exc.value)


# ===========================================================================
# 3. Rule part (c) — the base URL is the load-bearing half
# ===========================================================================


class TestPartCBaseUrlIsLoadBearing:
    def test_bare_alias_without_a_base_url_refuses(self):
        """The stage-1 named hole, closed.

        A bare alias is auto-prefixed to ``openai:`` by the langgraph translator
        (``selector.py:162-176``), so with no OPENAI_BASE_URL it is an
        OpenAI-vendor call wearing a local-sounding name.
        """
        verdict = judge_effective_seat(FLEET_SEAT, harness="langgraph")
        assert verdict.status == VERDICT_REFUSED
        assert "OPENAI_BASE_URL" in verdict.detail

    def test_bare_alias_with_a_fleet_base_url_passes(self, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        verdict = judge_effective_seat(FLEET_SEAT, harness="langgraph")
        assert verdict.status == VERDICT_PASS
        assert verdict.effective_model == FLEET_SEAT

    def test_bare_alias_against_the_vendor_host_refuses(self, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        assert judge_effective_seat(FLEET_SEAT, harness="sdk").status == VERDICT_REFUSED

    def test_openai_prefix_without_a_base_url_refuses(self):
        verdict = judge_effective_seat("openai:gpt-5", harness="langgraph")
        assert verdict.status == VERDICT_REFUSED

    def test_openai_prefix_against_the_vendor_host_refuses(self, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        assert judge_effective_seat("openai:gpt-5", harness="sdk").status == VERDICT_REFUSED

    def test_openai_prefix_against_a_fleet_seat_passes(self, monkeypatch):
        """The fleet's own route IS ``openai:<alias>`` against a local base URL."""
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        verdict = judge_effective_seat(f"openai:{FLEET_SEAT}", harness="langgraph")
        assert verdict.status == VERDICT_PASS

    def test_select_harness_refuses_a_bare_alias_with_no_base_url(self, monkeypatch):
        monkeypatch.setenv(SDK_ENV, "sdk")
        with pytest.raises(AgentInvocationError) as exc:
            select_harness(env_var=SDK_ENV, **_sdk_kwargs())
        assert FLEET_SEAT in str(exc.value)
        assert "OPENAI_BASE_URL" in str(exc.value)


# ===========================================================================
# 3b. Rule part (c) is an ALLOWLIST, not a one-vendor denylist
#     (design §3c as corrected 2026-08-02 — the GA1 coach's finding, ratified)
# ===========================================================================


#: Real inference vendors that the shipped ``openai.com`` denylist waved through.
#: Every one of them is a frontier API and an M0 breach on the routine path.
VENDOR_BASE_URLS = [
    "https://openrouter.ai/api/v1",
    "https://api.deepseek.com/v1",
    "https://api.groq.com/openai/v1",
    "https://api.together.xyz/v1",
    "https://generativelanguage.googleapis.com/v1beta/openai",
]

#: The shapes the fleet actually runs: loopback by name and by number, the
#: workhorse's single-label LAN hostname, and a LAN address.
FLEET_BASE_URLS = [
    "http://localhost:9000/v1",
    "http://127.0.0.1:9000/v1",
    "http://promaxgb10-41b1:9000/v1",
    "http://192.168.1.41:9000/v1",
    "http://10.0.0.7:9000/v1",
    "http://[::1]:9000/v1",
]


class TestPartCIsAnAllowlist:
    @pytest.mark.parametrize("base_url", VENDOR_BASE_URLS)
    def test_every_non_openai_vendor_now_refuses(self, monkeypatch, base_url):
        """The mutation the correction exists for.

        Under the one-vendor denylist each of these returned ``None`` from the
        route test — i.e. PASS — because the host simply was not ``openai.com``.
        """
        monkeypatch.setenv("OPENAI_BASE_URL", base_url)
        verdict = judge_effective_seat(FLEET_SEAT, harness="langgraph")
        assert verdict.status == VERDICT_REFUSED, base_url
        host = base_url.split("/")[2]
        assert host in verdict.detail  # the refusal NAMES the host

    @pytest.mark.parametrize("base_url", FLEET_BASE_URLS)
    def test_the_real_fleet_shapes_still_pass(self, monkeypatch, base_url):
        monkeypatch.setenv("OPENAI_BASE_URL", base_url)
        verdict = judge_effective_seat(FLEET_SEAT, harness="langgraph")
        assert verdict.status == VERDICT_PASS, base_url

    def test_a_scheme_less_base_url_refuses_instead_of_passing(self, monkeypatch):
        """``urlparse`` yields hostname ``None`` here — the second hole.

        ``api.openai.com/v1`` with no scheme is a path, not a netloc, so the old
        host test compared ``""`` against ``openai.com``, found no match, and
        PASSED the OpenAI vendor API itself.
        """
        monkeypatch.setenv("OPENAI_BASE_URL", "api.openai.com/v1")
        verdict = judge_effective_seat(FLEET_SEAT, harness="langgraph")
        assert verdict.status == VERDICT_REFUSED
        assert "names no host" in verdict.detail

    @pytest.mark.parametrize(
        "base_url", ["://nonsense", "http:///v1", "not a url at all"]
    )
    def test_an_unparseable_base_url_fails_closed(self, monkeypatch, base_url):
        monkeypatch.setenv("OPENAI_BASE_URL", base_url)
        assert (
            judge_effective_seat(FLEET_SEAT, harness="sdk").status == VERDICT_REFUSED
        )

    def test_a_dotted_internal_name_is_admitted_by_the_env_allowlist(
        self, monkeypatch
    ):
        monkeypatch.setenv("OPENAI_BASE_URL", "http://gb10.appmilla.internal:9000/v1")
        assert (
            judge_effective_seat(FLEET_SEAT, harness="langgraph").status
            == VERDICT_REFUSED
        )

        monkeypatch.setenv(
            LOCAL_SEAT_HOSTS_ENV, "spark.lan, gb10.appmilla.internal ,other.lan"
        )
        assert (
            judge_effective_seat(FLEET_SEAT, harness="langgraph").status == VERDICT_PASS
        )

    def test_the_env_allowlist_is_an_exact_match_never_a_suffix(self, monkeypatch):
        """A suffix rule would re-open the hole: ``evil-gb10.appmilla.internal``."""
        monkeypatch.setenv(LOCAL_SEAT_HOSTS_ENV, "gb10.appmilla.internal")
        monkeypatch.setenv(
            "OPENAI_BASE_URL", "http://evil.gb10.appmilla.internal/v1"
        )
        assert (
            judge_effective_seat(FLEET_SEAT, harness="sdk").status == VERDICT_REFUSED
        )

    def test_a_public_ip_literal_refuses(self, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", "http://8.8.8.8:9000/v1")
        assert (
            judge_effective_seat(FLEET_SEAT, harness="sdk").status == VERDICT_REFUSED
        )

    def test_the_openai_prefix_obeys_the_same_one_rule(self, monkeypatch):
        """Part (c)'s two halves share ONE predicate — prove it on both."""
        monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        assert (
            judge_effective_seat(f"openai:{FLEET_SEAT}", harness="langgraph").status
            == VERDICT_REFUSED
        )
        monkeypatch.setenv("OPENAI_BASE_URL", "http://promaxgb10-41b1:9000/v1")
        assert (
            judge_effective_seat(f"openai:{FLEET_SEAT}", harness="langgraph").status
            == VERDICT_PASS
        )

    def test_the_allowlist_predicate_is_stated_once(self):
        """No second copy of the host rule anywhere in the builder."""
        import inspect

        from guardkit.orchestrator import m0_fence as fence_module

        source = inspect.getsource(fence_module)
        assert source.count("def is_local_seat_host") == 1
        assert source.count("LOCAL_SEAT_NETWORKS: Tuple") == 1


# ===========================================================================
# 4. The sdk branch builds for real once the seat is legitimate
# ===========================================================================


class TestSdkBranchDrive:
    def test_sdk_branch_constructs_when_the_seat_is_a_fleet_route(
        self, monkeypatch
    ):
        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        monkeypatch.setenv(SDK_ENV, "sdk")
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)

        harness = select_harness(env_var=SDK_ENV, **_sdk_kwargs())

        assert isinstance(harness, ClaudeSDKHarness)
        verdict = m0_fence.last_verdict()
        assert verdict is not None
        assert verdict.status == VERDICT_PASS
        assert verdict.harness == "sdk"
        assert verdict.effective_model == FLEET_SEAT

    def test_an_unknown_harness_name_is_not_fenced_but_still_refused(self, monkeypatch):
        """Branch inventory: the third branch constructs nothing.

        ``select_harness`` has exactly two construction branches (sdk,
        langgraph) — both fenced — and one error branch. The error branch makes
        no model call, so the fence records NOT-JUDGED and the selector's own
        unknown-value refusal still fires.
        """
        monkeypatch.setenv(SDK_ENV, "not-a-harness")
        with pytest.raises(AgentInvocationError) as exc:
            select_harness(env_var=SDK_ENV, **_sdk_kwargs(model=None))
        assert "Unknown GUARDKIT_HARNESS value" in str(exc.value)
        assert m0_fence.last_verdict().status == VERDICT_NOT_JUDGED

    def test_a_model_instance_is_recorded_not_judged_never_a_silent_pass(self):
        """The named hole says so out loud rather than reporting PASS."""

        class _PreBuiltModel:
            pass

        verdict = judge_effective_seat(_PreBuiltModel(), harness="langgraph")
        assert verdict.status == VERDICT_NOT_JUDGED
        assert "_PreBuiltModel" in verdict.effective_model


# ===========================================================================
# 5. The escape hatch — allowed, but never silent
# ===========================================================================


class TestEscapeHatch:
    def test_escape_lets_a_frontier_seat_through_with_a_loud_stderr_echo(
        self, monkeypatch, capsys
    ):
        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        monkeypatch.setenv(SDK_ENV, "sdk")
        monkeypatch.setenv(FRONTIER_ESCAPE_ENV, "1")

        harness = select_harness(
            env_var=SDK_ENV, **_sdk_kwargs(model="anthropic:claude-opus-4")
        )

        assert isinstance(harness, ClaudeSDKHarness)
        captured = capsys.readouterr()
        assert "anthropic:claude-opus-4" in captured.err
        assert FRONTIER_ESCAPE_ENV in captured.err
        assert captured.out == ""  # stdout is the pipeline's marker scrape

    def test_escape_covers_the_nameless_seat_too(self, monkeypatch, capsys):
        monkeypatch.setenv(SDK_ENV, "sdk")
        monkeypatch.setenv(FRONTIER_ESCAPE_ENV, "1")

        select_harness(env_var=SDK_ENV, **_sdk_kwargs(model=None))

        assert "bundled claude-agent-sdk CLI default" in capsys.readouterr().err

    def test_the_escape_verdict_is_recorded_as_escaped_not_as_a_pass(
        self, monkeypatch
    ):
        monkeypatch.setenv(SDK_ENV, "sdk")
        monkeypatch.setenv(FRONTIER_ESCAPE_ENV, "1")
        select_harness(env_var=SDK_ENV, **_sdk_kwargs(model="anthropic:claude-opus-4"))
        assert m0_fence.last_verdict().status == VERDICT_ALLOWED_BY_ESCAPE

    @pytest.mark.parametrize("value", ["0", "true", "yes", "", "TRUE"])
    def test_only_the_literal_1_opens_the_escape(self, monkeypatch, value):
        monkeypatch.setenv(SDK_ENV, "sdk")
        monkeypatch.setenv(FRONTIER_ESCAPE_ENV, value)
        with pytest.raises(AgentInvocationError):
            select_harness(env_var=SDK_ENV, **_sdk_kwargs(model="anthropic:claude-opus-4"))


# ===========================================================================
# 6. Receipt truth (§3.3) — REPORT the chokepoint verdict, never re-derive it
# ===========================================================================


def _outcome(model=None):
    from guardkit.orchestrator.review_runner import ReviewLegOutcome

    return ReviewLegOutcome(
        task_id="TASK-M0F-0001",
        status="clean",
        exit_code=0,
        duration_seconds=1.0,
        model=model,
        seat=None,
    )


class TestReceiptTruth:
    def test_no_verdict_and_no_model_keeps_the_honest_not_evaluated_wording(self):
        from guardkit.orchestrator.review_runner import build_receipt

        receipt = build_receipt(_outcome(), build_id=None, correlation_id=None)
        assert receipt["m0_fence"].startswith("NOT-EVALUATED")

    def test_a_recorded_pass_replaces_not_evaluated(self, monkeypatch):
        from guardkit.orchestrator.review_runner import build_receipt

        monkeypatch.setenv(SDK_ENV, "sdk")
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        select_harness(env_var=SDK_ENV, **_sdk_kwargs())

        receipt = build_receipt(_outcome(), build_id=None, correlation_id=None)
        assert receipt["m0_fence"].startswith(VERDICT_PASS)
        assert "NOT-EVALUATED" not in receipt["m0_fence"]
        assert FLEET_SEAT in receipt["m0_fence"]
        assert "select_harness/sdk" in receipt["m0_fence"]

    def test_a_recorded_escape_is_reported_as_escaped(self, monkeypatch):
        from guardkit.orchestrator.review_runner import build_receipt

        monkeypatch.setenv(SDK_ENV, "sdk")
        monkeypatch.setenv(FRONTIER_ESCAPE_ENV, "1")
        select_harness(env_var=SDK_ENV, **_sdk_kwargs(model="anthropic:claude-opus-4"))

        receipt = build_receipt(_outcome(), build_id=None, correlation_id=None)
        assert receipt["m0_fence"].startswith(VERDICT_ALLOWED_BY_ESCAPE)
        assert "anthropic:claude-opus-4" in receipt["m0_fence"]

    def test_a_late_local_pass_cannot_bury_an_earlier_escaped_frontier(
        self, monkeypatch
    ):
        """WORST-WINS — the GA1 coach's exact sequence.

        A leg builds more than one harness. Under last-write-wins the receipt
        line said PASS about a process that had ALREADY constructed a frontier
        seat under the escape hatch: the second, local construction simply
        overwrote the record. The receipt must report the escape.
        """
        from guardkit.orchestrator.review_runner import build_receipt

        monkeypatch.setenv(SDK_ENV, "sdk")

        # 1. a frontier seat, allowed only because the operator opened the hatch
        monkeypatch.setenv(FRONTIER_ESCAPE_ENV, "1")
        select_harness(env_var=SDK_ENV, **_sdk_kwargs(model="anthropic:claude-opus-4"))
        assert m0_fence.last_verdict().status == VERDICT_ALLOWED_BY_ESCAPE

        # 2. a perfectly legitimate local seat, later in the same process
        monkeypatch.delenv(FRONTIER_ESCAPE_ENV)
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        select_harness(env_var=SDK_ENV, **_sdk_kwargs())

        assert m0_fence.last_verdict().status == VERDICT_ALLOWED_BY_ESCAPE
        receipt = build_receipt(_outcome(), build_id=None, correlation_id=None)
        assert receipt["m0_fence"].startswith(VERDICT_ALLOWED_BY_ESCAPE)
        assert "anthropic:claude-opus-4" in receipt["m0_fence"]
        assert not receipt["m0_fence"].startswith(VERDICT_PASS)

    def test_a_refusal_outranks_everything_recorded_after_it(self, monkeypatch):
        monkeypatch.setenv(SDK_ENV, "sdk")
        with pytest.raises(AgentInvocationError):
            select_harness(env_var=SDK_ENV, **_sdk_kwargs(model=None))
        assert m0_fence.last_verdict().status == VERDICT_REFUSED

        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        select_harness(env_var=SDK_ENV, **_sdk_kwargs())
        assert m0_fence.last_verdict().status == VERDICT_REFUSED

    def test_a_pass_is_not_buried_by_a_later_not_judged(self, monkeypatch):
        """NOT-JUDGED outranks PASS: an unjudged seat is worse news than a
        judged-and-clean one, and the ranking says so in one place."""
        monkeypatch.setenv(SDK_ENV, "sdk")
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        select_harness(env_var=SDK_ENV, **_sdk_kwargs())
        assert m0_fence.last_verdict().status == VERDICT_PASS

        m0_fence.record_verdict(
            judge_effective_seat(object(), harness="langgraph")
        )
        assert m0_fence.last_verdict().status == VERDICT_NOT_JUDGED

    def test_an_equal_severity_verdict_replaces_the_earlier_one(self, monkeypatch):
        monkeypatch.setenv(SDK_ENV, "sdk")
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        select_harness(env_var=SDK_ENV, **_sdk_kwargs())
        select_harness(env_var=SDK_ENV, **_sdk_kwargs(model="other-seat"))
        assert m0_fence.last_verdict().effective_model == "other-seat"

    def test_reset_clears_the_sticky_record(self, monkeypatch):
        monkeypatch.setenv(SDK_ENV, "sdk")
        with pytest.raises(AgentInvocationError):
            select_harness(env_var=SDK_ENV, **_sdk_kwargs(model=None))
        m0_fence.reset_verdict()
        assert m0_fence.last_verdict() is None

    def test_a_supplied_model_with_no_chokepoint_run_says_cli_fence_only(self):
        from guardkit.orchestrator.review_runner import build_receipt

        receipt = build_receipt(
            _outcome(model=FLEET_SEAT), build_id=None, correlation_id=None
        )
        assert "CLI fence only" in receipt["m0_fence"]
        assert "NOT-EVALUATED" not in receipt["m0_fence"]

    def test_the_middle_case_never_claims_a_bare_alias_was_route_judged(self):
        """Softened 2026-08-02: ``evaluated`` over-claimed.

        The CLI fence judges a provider PREFIX. A bare alias carries none, so
        ``resolve_m0_violation`` returns ``None`` without ever reading
        OPENAI_BASE_URL — nothing about the ROUTE was judged. The old wording
        ("evaluated (--model supplied; CLI fence only …)") read as a check that
        had happened.
        """
        from guardkit.orchestrator.review_runner import build_receipt

        line = build_receipt(
            _outcome(model=FLEET_SEAT), build_id=None, correlation_id=None
        )["m0_fence"]
        assert line.startswith("PARTIALLY-EVALUATED")
        assert "BARE alias" in line
        assert "does not route-judge" in line
        assert not line.startswith("evaluated")

    def test_a_prefixed_alias_says_the_prefix_is_what_was_judged(self):
        from guardkit.orchestrator.review_runner import build_receipt

        line = build_receipt(
            _outcome(model="openai:qwen36-workhorse"),
            build_id=None,
            correlation_id=None,
        )["m0_fence"]
        assert line.startswith("PARTIALLY-EVALUATED")
        assert "provider prefix was judged" in line

    def test_both_legs_share_ONE_no_chokepoint_sentence(self):
        """A second copy of this sentence is a future lie."""
        import inspect

        from guardkit.orchestrator import review_runner, work_runner

        for module in (review_runner, work_runner):
            source = inspect.getsource(module)
            assert "PARTIALLY-EVALUATED (" not in source
            assert "NOT-EVALUATED (no --model supplied" not in source
            assert "receipt_line_when_chokepoint_did_not_run(outcome.model)" in source


# ===========================================================================
# 7. The extraction kept every stage-1 import working
# ===========================================================================


class TestExtractionCompatibility:
    def test_stage_one_names_still_import_from_the_cli_module(self):
        from guardkit.cli import task_review as cli_module

        assert cli_module.FRONTIER_ESCAPE_ENV is m0_fence.FRONTIER_ESCAPE_ENV
        assert cli_module.resolve_m0_violation is m0_fence.resolve_m0_violation
        assert (
            cli_module.FRONTIER_PROVIDER_PREFIXES is m0_fence.FRONTIER_PROVIDER_PREFIXES
        )

    def test_review_runner_still_exports_the_prefix_tuple(self):
        from guardkit.orchestrator import review_runner

        assert (
            review_runner.FRONTIER_PROVIDER_PREFIXES
            is m0_fence.FRONTIER_PROVIDER_PREFIXES
        )
        assert "FRONTIER_PROVIDER_PREFIXES" in review_runner.__all__

    def test_the_rule_is_stated_once(self):
        """The predicate lives in exactly one module.

        A second copy of the frontier-prefix list or the base-URL test is a
        future lie (the binding one-rule lesson): the chokepoint's part (b) must
        BE ``resolve_m0_violation``, not a paraphrase of it.
        """
        import inspect

        from guardkit.cli import task_review as cli_module
        from guardkit.orchestrator import review_runner

        for module in (cli_module, review_runner):
            source = inspect.getsource(module)
            assert "def resolve_m0_violation" not in source
            assert "openai.com" not in source
