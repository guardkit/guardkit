"""The frontier-model fence applies to factory launches only (19 October 2026).

Rich's decision: the factory's own launches never reach a hosted model, and a
person's own run of GuardKit is not fenced (he builds some of his own projects
on the ``sdk`` harness with Claude on purpose). Design note:
``docs/design/m0-fence-factory-launches-only-2026-10-19.md``.

The one signal is ``GUARDKIT_FACTORY_LAUNCH``, set by Forge's
``build_launch_env`` on every launch it makes. Every test in this suite runs as
a factory launch unless it is marked ``personal_run`` (``tests/conftest.py``),
and no test can reach a network or start ``claude``.

Nothing here makes a model call: the passing ``sdk`` case builds a
``ClaudeSDKHarness`` object and never invokes it.
"""

from __future__ import annotations

import logging

import pytest

from guardkit.orchestrator import m0_fence
from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness.selector import select_harness
from guardkit.orchestrator.m0_fence import (
    FACTORY_LAUNCH_ENV,
    FRONTIER_ESCAPE_ENV,
    LANGGRAPH_DEFAULT_SEAT,
    VERDICT_ALLOWED_BY_ESCAPE,
    VERDICT_NOT_JUDGED,
    VERDICT_PASS,
    VERDICT_PERSONAL_RUN,
    VERDICT_REFUSED,
    cli_m0_violation,
    enforce_effective_seat,
    is_factory_launch,
    judge_effective_seat,
    receipt_line_when_chokepoint_did_not_run,
    resolve_m0_violation,
)

FLEET_BASE_URL = "http://127.0.0.1:9/v1"
FLEET_SEAT = "qwen36-workhorse"
CLAUDE_SEAT = "claude-sonnet-4-5-20250929"
SDK_ENV = "GUARDKIT_HARNESS_FACTORY_ONLY_SDK"


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv(FRONTIER_ESCAPE_ENV, raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("GUARDKIT_LOCAL_SEAT_HOSTS", raising=False)
    monkeypatch.delenv("GUARDKIT_RUN_OWNER", raising=False)
    monkeypatch.delenv(SDK_ENV, raising=False)
    m0_fence.reset_verdict()
    yield
    m0_fence.reset_verdict()


def _sdk_kwargs(model):
    return {
        "sdk_timeout_seconds": 60,
        "allowed_tools": ["Read"],
        "permission_mode": "acceptEdits",
        "max_turns": 5,
        "model": model,
    }


# ===========================================================================
# 1. The signal
# ===========================================================================


class TestTheSignal:
    def test_the_suite_runs_as_a_factory_launch_by_default(self):
        assert is_factory_launch()

    @pytest.mark.personal_run
    def test_a_personal_run_test_has_no_signal(self):
        assert not is_factory_launch()

    @pytest.mark.parametrize(
        "value", ["1", "yes", "anything", "0", "false", "False", "no", "off", " 0 ", " "]
    )
    def test_any_non_empty_value_is_a_factory_launch(self, value):
        """Fails safe: ``0``, ``false``, ``no`` and ``off`` are factory launches
        too. Only unset, empty or whitespace is a person's own run, so a later
        change that reads "0" as off cannot quietly unfence the factory."""
        assert is_factory_launch({FACTORY_LAUNCH_ENV: value})

    @pytest.mark.parametrize("value", ["1", "0", "false", "no", "off"])
    def test_the_memory_rule_reads_any_non_empty_value_the_same_way(
        self, value, tmp_path
    ):
        """The memory rule ignores the folder's declaration on a factory launch;
        it must agree with the fence about what a factory launch is."""
        from guardkit.knowledge.memory_project import resolve_memory_project

        (tmp_path / ".guardkit").mkdir()
        (tmp_path / ".guardkit" / "config.yaml").write_text(
            "memory:\n  project: declared_here\n", encoding="utf-8"
        )
        factory = resolve_memory_project(tmp_path, env={FACTORY_LAUNCH_ENV: value})
        by_hand = resolve_memory_project(tmp_path, env={})
        assert factory.project is None
        assert by_hand.project == "declared_here"

    def test_only_unset_or_exactly_empty_is_a_persons_run(self):
        assert not is_factory_launch({})
        assert not is_factory_launch({FACTORY_LAUNCH_ENV: ""})

    @pytest.mark.parametrize("value", [" ", "   ", "\t", "\n", " \r\n "])
    def test_a_whitespace_value_is_a_factory_launch(self, value):
        """Codex review round 3: a stripped whitespace value used to switch
        the fence off. Any value at all keeps it on."""
        assert is_factory_launch({FACTORY_LAUNCH_ENV: value})

    @pytest.mark.parametrize("value", [" ", "\t"])
    def test_a_whitespace_value_keeps_every_refusal(self, value, monkeypatch):
        monkeypatch.setenv(FACTORY_LAUNCH_ENV, value)
        sdk = judge_effective_seat(CLAUDE_SEAT, harness="sdk")
        assert sdk.status == VERDICT_REFUSED and sdk.escapable is False
        langgraph = judge_effective_seat(None, harness="langgraph")
        assert langgraph.status == VERDICT_REFUSED
        assert cli_m0_violation("anthropic:claude-opus-4") is not None
        with pytest.raises(AgentInvocationError):
            enforce_effective_seat(CLAUDE_SEAT, harness="sdk")

    @pytest.mark.parametrize("value", [" ", "\t"])
    def test_a_whitespace_value_keeps_the_selectors_own_sdk_refusal(
        self, value, monkeypatch
    ):
        from guardkit.orchestrator.harness import selector

        monkeypatch.setenv(FACTORY_LAUNCH_ENV, value)
        assert selector.is_factory_launch is is_factory_launch
        monkeypatch.setenv(SDK_ENV, "sdk")
        monkeypatch.setattr(selector, "enforce_effective_seat", lambda *a, **k: None)
        with pytest.raises(AgentInvocationError, match="factory build does not use it"):
            select_harness(env_var=SDK_ENV, **_sdk_kwargs(CLAUDE_SEAT))

    def test_the_memory_rule_treats_whitespace_as_a_factory_launch(self, tmp_path):
        from guardkit.knowledge.memory_project import resolve_memory_project

        (tmp_path / ".guardkit").mkdir()
        (tmp_path / ".guardkit" / "config.yaml").write_text(
            "memory:\n  project: declared_here\n", encoding="utf-8"
        )
        assert resolve_memory_project(tmp_path, env={FACTORY_LAUNCH_ENV: " "}).project is None
        assert resolve_memory_project(tmp_path, env={FACTORY_LAUNCH_ENV: ""}).project == "declared_here"

    def test_the_build_id_alone_is_not_a_factory_signal(self):
        """GUARDKIT_RUN_OWNER is set only on the build launch, not on every
        factory launch, so it is not used as a second signal (gap recorded for
        a Forge follow-up: set GUARDKIT_FACTORY_LAUNCH in the factory images)."""
        assert not is_factory_launch({"GUARDKIT_RUN_OWNER": "build-1"})

    def test_the_memory_rule_reads_the_same_setting(self):
        from guardkit.knowledge.memory_project import FACTORY_LAUNCH_ENV as memory_env

        assert memory_env == FACTORY_LAUNCH_ENV


# ===========================================================================
# 2. A factory launch: today's strict rule, plus sdk refused outright
# ===========================================================================


class TestFactoryLaunch:
    @pytest.mark.parametrize(
        "model", [CLAUDE_SEAT, FLEET_SEAT, "anthropic:claude-opus-4", None, ""]
    )
    def test_sdk_is_refused_whatever_the_model(self, model, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        verdict = judge_effective_seat(model, harness="sdk")
        assert verdict.status == VERDICT_REFUSED
        assert verdict.escapable is False

    def test_the_sdk_refusal_names_the_claude_program_not_openai(self):
        verdict = judge_effective_seat(CLAUDE_SEAT, harness="sdk")
        assert "Claude program" in verdict.detail
        assert CLAUDE_SEAT in verdict.detail
        assert "OPENAI" not in verdict.detail
        assert "langgraph" not in verdict.detail

    def test_select_harness_refuses_sdk_and_records_it(self, monkeypatch):
        monkeypatch.setenv(SDK_ENV, "sdk")
        with pytest.raises(AgentInvocationError) as exc:
            select_harness(env_var=SDK_ENV, **_sdk_kwargs(CLAUDE_SEAT))
        assert "Claude program" in str(exc.value)
        assert m0_fence.last_verdict().status == VERDICT_REFUSED
        assert m0_fence.last_verdict().harness == "sdk"

    def test_the_escape_hatch_does_not_lift_the_sdk_refusal(self, monkeypatch, capsys):
        monkeypatch.setenv(FRONTIER_ESCAPE_ENV, "1")
        with pytest.raises(AgentInvocationError) as exc:
            enforce_effective_seat(CLAUDE_SEAT, harness="sdk")
        assert f"{FRONTIER_ESCAPE_ENV} does not override this" in str(exc.value)
        assert m0_fence.last_verdict().status == VERDICT_REFUSED
        assert capsys.readouterr().err == ""

    def test_a_bare_alias_with_no_local_base_url_is_refused(self):
        verdict = judge_effective_seat(FLEET_SEAT, harness="langgraph")
        assert verdict.status == VERDICT_REFUSED
        assert "OPENAI_BASE_URL" in verdict.detail

    def test_langgraph_with_no_model_is_refused(self):
        verdict = judge_effective_seat(None, harness="langgraph")
        assert verdict.status == VERDICT_REFUSED
        assert verdict.effective_model == LANGGRAPH_DEFAULT_SEAT

    def test_a_local_seat_passes(self, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        assert judge_effective_seat(FLEET_SEAT, harness="langgraph").status == VERDICT_PASS

    def test_the_escape_hatch_still_opens_the_other_refusals(self, monkeypatch, capsys):
        monkeypatch.setenv(FRONTIER_ESCAPE_ENV, "1")
        verdict = enforce_effective_seat("anthropic:claude-opus-4", harness="langgraph")
        assert verdict.status == VERDICT_ALLOWED_BY_ESCAPE
        assert "Proceeding because" in capsys.readouterr().err

    def test_the_cli_fence_is_the_full_rule(self):
        assert cli_m0_violation("anthropic:claude-opus-4") is not None
        assert cli_m0_violation("anthropic:claude-opus-4") == resolve_m0_violation(
            "anthropic:claude-opus-4"
        )

    def test_the_no_chokepoint_receipt_line_is_unchanged(self):
        assert receipt_line_when_chokepoint_did_not_run(None).startswith("NOT-EVALUATED")
        assert receipt_line_when_chokepoint_did_not_run(FLEET_SEAT).startswith(
            "PARTIALLY-EVALUATED"
        )


# ===========================================================================
# 3. A person's own run: judged and recorded, never refused
# ===========================================================================


@pytest.mark.personal_run
class TestPersonalRun:
    def test_sdk_with_a_claude_model_builds_and_says_personal_run(
        self, monkeypatch, capsys
    ):
        from guardkit.orchestrator.harness.sdk_harness import ClaudeSDKHarness

        monkeypatch.setenv(SDK_ENV, "sdk")
        harness = select_harness(env_var=SDK_ENV, **_sdk_kwargs(CLAUDE_SEAT))

        assert isinstance(harness, ClaudeSDKHarness)
        verdict = m0_fence.last_verdict()
        assert verdict.status == VERDICT_PERSONAL_RUN
        assert verdict.harness == "sdk"
        assert verdict.effective_model == CLAUDE_SEAT
        assert "not a factory launch" in verdict.detail
        assert "Claude program" in verdict.detail  # what the factory would say
        assert capsys.readouterr().err == ""  # no stderr noise

    def test_sdk_with_no_model_is_not_refused(self):
        verdict = enforce_effective_seat(None, harness="sdk")
        assert verdict.status == VERDICT_PERSONAL_RUN
        assert "bundled claude-agent-sdk CLI default" in verdict.effective_model

    def test_langgraph_with_no_model_is_allowed_too(self):
        verdict = enforce_effective_seat(None, harness="langgraph")
        assert verdict.status == VERDICT_PERSONAL_RUN
        assert verdict.effective_model == LANGGRAPH_DEFAULT_SEAT

    def test_a_frontier_prefix_is_not_refused(self):
        verdict = enforce_effective_seat("anthropic:claude-opus-4", harness="langgraph")
        assert verdict.status == VERDICT_PERSONAL_RUN

    def test_a_seat_the_factory_rule_passes_is_still_a_pass(self, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        verdict = enforce_effective_seat(FLEET_SEAT, harness="langgraph")
        assert verdict.status == VERDICT_PASS

    def test_a_model_object_stays_not_judged(self):
        verdict = judge_effective_seat(object(), harness="langgraph")
        assert verdict.status == VERDICT_NOT_JUDGED

    def test_the_escape_hatch_changes_nothing_and_echoes_nothing(
        self, monkeypatch, capsys
    ):
        monkeypatch.setenv(FRONTIER_ESCAPE_ENV, "1")
        verdict = enforce_effective_seat(CLAUDE_SEAT, harness="sdk")
        assert verdict.status == VERDICT_PERSONAL_RUN
        assert capsys.readouterr().err == ""

    def test_it_is_logged_once_at_info(self, caplog):
        with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.m0_fence"):
            enforce_effective_seat(CLAUDE_SEAT, harness="sdk")
            enforce_effective_seat(CLAUDE_SEAT, harness="sdk")
        lines = [r for r in caplog.records if VERDICT_PERSONAL_RUN in r.getMessage()]
        assert len(lines) == 1
        assert lines[0].levelno == logging.INFO

    def test_the_cli_fence_does_not_apply(self):
        assert resolve_m0_violation("anthropic:claude-opus-4") is not None
        assert cli_m0_violation("anthropic:claude-opus-4") is None

    def test_the_no_chokepoint_receipt_line_says_not_fenced(self):
        for model in (None, "anthropic:claude-opus-4"):
            line = receipt_line_when_chokepoint_did_not_run(model)
            assert line.startswith("NOT-FENCED")
            assert "passed the CLI fence" not in line


# ===========================================================================
# 4. The record ranks a personal run between PASS and NOT-JUDGED
# ===========================================================================


@pytest.mark.personal_run
class TestRanking:
    def test_a_personal_run_outranks_a_pass(self, monkeypatch):
        monkeypatch.setenv("OPENAI_BASE_URL", FLEET_BASE_URL)
        enforce_effective_seat(FLEET_SEAT, harness="langgraph")
        enforce_effective_seat(CLAUDE_SEAT, harness="sdk")
        enforce_effective_seat(FLEET_SEAT, harness="langgraph")
        assert m0_fence.last_verdict().status == VERDICT_PERSONAL_RUN

    def test_a_later_unjudged_seat_cannot_hide_a_personal_run(self):
        """A hosted seat in a person's run stays on the record (coach F3)."""
        enforce_effective_seat(CLAUDE_SEAT, harness="sdk")
        enforce_effective_seat(object(), harness="langgraph")
        assert m0_fence.last_verdict().status == VERDICT_PERSONAL_RUN
        assert m0_fence.last_verdict().effective_model == CLAUDE_SEAT

    def test_a_personal_run_outranks_an_earlier_unjudged_seat(self):
        enforce_effective_seat(object(), harness="langgraph")
        enforce_effective_seat(CLAUDE_SEAT, harness="sdk")
        assert m0_fence.last_verdict().status == VERDICT_PERSONAL_RUN

    def test_an_escape_on_a_factory_launch_still_outranks_it(self, monkeypatch):
        enforce_effective_seat(CLAUDE_SEAT, harness="sdk")
        monkeypatch.setenv(FACTORY_LAUNCH_ENV, "1")
        monkeypatch.setenv(FRONTIER_ESCAPE_ENV, "1")
        enforce_effective_seat("anthropic:claude-opus-4", harness="langgraph")
        assert m0_fence.last_verdict().status == VERDICT_ALLOWED_BY_ESCAPE
