"""Unit tests for ``guardkit.orchestrator.coach_output_parser`` (TASK-FIX-COACHOUT01).

Implements **Shape A** of TASK-FIX-COACHOUT01 — orchestrator-side parser
that extracts the Coach verdict from a harness event stream and writes
``coach_turn_N.json``.

Test coverage maps to the edge-case matrix in
``docs/state/TASK-FIX-COACHOUT01/implementation_plan.md`` §2.2 and the
Phase 2.5B architectural-review constraints
(``docs/state/TASK-FIX-COACHOUT01/architectural_review.md`` Gaps 2 + 3):

* No JSON block → ``CoachDecisionNotFoundError`` (COACHSF01 trigger)
* No assistant text at all → ``CoachDecisionNotFoundError`` (LangGraph tool-call-only branch)
* Single valid block → atomic write, parsed dict returned
* Multiple blocks → last one wins (handles exploratory-then-corrected pattern)
* Block split across multiple ``AssistantMessageEvent`` (SDK streaming) → still found
* Malformed JSON in last block → ``CoachDecisionInvalidError``
* Top-level array / scalar → ``CoachDecisionInvalidError``
* Missing required fields (``task_id`` / ``turn`` / ``decision``) → ``CoachDecisionInvalidError``
* ``decision`` value outside ``{"approve","feedback"}`` → ``CoachDecisionInvalidError``
* COACHSF01 coupling — every raised exception string contains the
  ``"Coach decision not found"`` / ``"Coach decision invalid"`` substring
  that ``autobuild.py:5676-5678`` greps for.
* Atomic write semantics — partial ``.tmp`` is not left behind on success.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import pytest

from guardkit.orchestrator.coach_output_parser import extract_and_write
from guardkit.orchestrator.exceptions import (
    CoachDecisionInvalidError,
    CoachDecisionNotFoundError,
)
from guardkit.orchestrator.harness.adapter import (
    AssistantMessageEvent,
    HarnessEvent,
    ResultMessageEvent,
    ToolUseEvent,
)


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


def _make_approve_payload(task_id: str = "TASK-FIX-COACHOUT01", turn: int = 1) -> dict:
    """A minimal-but-valid Coach approval verdict."""
    return {
        "task_id": task_id,
        "turn": turn,
        "decision": "approve",
        "validation_results": {
            "requirements_met": ["AC-001"],
            "tests_run": True,
            "tests_passed": True,
            "test_command": "pytest tests/",
            "test_output_summary": "all green",
            "code_quality": "ok",
            "edge_cases_covered": ["empty input"],
        },
        "rationale": "Looks good.",
    }


def _make_feedback_payload(task_id: str = "TASK-FIX-COACHOUT01", turn: int = 1) -> dict:
    """A minimal-but-valid Coach feedback verdict."""
    return {
        "task_id": task_id,
        "turn": turn,
        "decision": "feedback",
        "issues": [
            {
                "type": "test_failure",
                "severity": "critical",
                "description": "tests/foo.py:12 assertion failed",
                "requirement": "AC-001",
                "suggestion": "Fix the regex",
            }
        ],
        "rationale": "One test is red.",
    }


def _fence(payload: dict) -> str:
    """Wrap a payload in a fenced ``json`` block exactly as Coach is told to."""
    return f"```json\n{json.dumps(payload, indent=2)}\n```"


def _assistant_event(text: str) -> AssistantMessageEvent:
    return AssistantMessageEvent(text=text)


def _result_event() -> ResultMessageEvent:
    return ResultMessageEvent(session_id="session-test")


def _tool_use_event(name: str = "Bash") -> ToolUseEvent:
    return ToolUseEvent(tool_use_id="tu-1", name=name, input={"command": "ls"})


def _output_path(tmp_path: Path, task_id: str = "TASK-FIX-COACHOUT01", turn: int = 1) -> Path:
    return tmp_path / ".guardkit" / "autobuild" / task_id / f"coach_turn_{turn}.json"


# --------------------------------------------------------------------------- #
# Happy paths
# --------------------------------------------------------------------------- #


class TestSingleValidBlock:
    """One AssistantMessageEvent ending in a single fenced JSON block."""

    def test_single_approval_block_writes_file_and_returns_dict(self, tmp_path):
        payload = _make_approve_payload()
        events: List[HarnessEvent] = [
            _assistant_event(
                "I verified all acceptance criteria.\n\n" + _fence(payload)
            ),
            _result_event(),
        ]
        out = _output_path(tmp_path)

        result = extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)

        assert result == payload
        assert out.exists()
        assert json.loads(out.read_text()) == payload

    def test_single_feedback_block_writes_file_and_returns_dict(self, tmp_path):
        payload = _make_feedback_payload()
        events: List[HarnessEvent] = [
            _assistant_event(
                "Found one issue while running tests.\n\n" + _fence(payload)
            ),
        ]
        out = _output_path(tmp_path)

        result = extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)

        assert result["decision"] == "feedback"
        assert json.loads(out.read_text()) == payload


class TestSubstrateParity:
    """LangGraph emits one AssistantMessageEvent; SDK may emit several.

    The parser must extract the same verdict from both shapes.
    """

    def test_langgraph_style_single_event_with_full_response(self, tmp_path):
        """LangGraph (qwen36-workhorse): one event carries the whole turn."""
        payload = _make_approve_payload()
        single_event = _assistant_event(
            "Reasoning through the AC list...\n\nAll good.\n\n" + _fence(payload)
        )
        out = _output_path(tmp_path)

        result = extract_and_write([single_event], "TASK-FIX-COACHOUT01", 1, out)

        assert result == payload

    def test_sdk_style_multiple_events_with_block_split_across_streamed_chunks(
        self, tmp_path
    ):
        """SDK (Sonnet): multiple AssistantMessageEvents per turn.

        The parser concatenates them with newlines before regexing. Splitting
        the fence mid-block must still resolve.
        """
        payload = _make_feedback_payload()
        rendered = _fence(payload)
        # Split the fenced block roughly in half across two events to exercise
        # the join path.
        half = len(rendered) // 2
        events: List[HarnessEvent] = [
            _assistant_event("Starting verification.\n```json\n"),
            _assistant_event(json.dumps(payload, indent=2) + "\n```"),
        ]
        out = _output_path(tmp_path)

        # The above split actually puts ```json on event 1 and {…}``` on
        # event 2. Joined with newline → a parseable fenced block.
        result = extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert result == payload

    def test_non_assistant_events_are_ignored(self, tmp_path):
        """Tool-use and result events do not contribute to verdict text."""
        payload = _make_approve_payload()
        events: List[HarnessEvent] = [
            _tool_use_event(),
            _assistant_event("Quick check.\n\n" + _fence(payload)),
            _tool_use_event("Read"),
            _result_event(),
        ]
        out = _output_path(tmp_path)

        result = extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert result == payload


class TestMultipleBlocks:
    """When Coach emits several fenced blocks, the LAST wins.

    Handles the real qwen36-workhorse pattern of "draft a block, reason,
    then emit a corrected final block".
    """

    def test_two_blocks_last_one_wins(self, tmp_path):
        first = _make_feedback_payload()
        first["rationale"] = "Initial impression — wrong."
        final = _make_approve_payload()

        events: List[HarnessEvent] = [
            _assistant_event(
                "First pass:\n" + _fence(first) +
                "\n\nWait, on re-check:\n" + _fence(final)
            ),
        ]
        out = _output_path(tmp_path)

        result = extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)

        assert result["decision"] == "approve"
        assert result["rationale"] == "Looks good."

    def test_three_blocks_last_one_wins(self, tmp_path):
        a = _make_feedback_payload(turn=1)
        b = _make_feedback_payload(turn=1)
        b["rationale"] = "Middle draft"
        c = _make_approve_payload(turn=1)
        events: List[HarnessEvent] = [
            _assistant_event(_fence(a) + "\n\n" + _fence(b) + "\n\n" + _fence(c)),
        ]
        out = _output_path(tmp_path)

        result = extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert result["decision"] == "approve"


# --------------------------------------------------------------------------- #
# Error paths — must raise typed exceptions whose str() is COACHSF01-friendly
# --------------------------------------------------------------------------- #


class TestNoBlockFound:
    """No fenced JSON → ``CoachDecisionNotFoundError``."""

    def test_no_block_at_all_raises_not_found(self, tmp_path):
        events: List[HarnessEvent] = [
            _assistant_event(
                "I looked at the tests and they all pass. Approving."
            ),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionNotFoundError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert "Coach decision not found" in str(exc_info.value)
        assert not out.exists()

    def test_no_assistant_events_at_all_raises_not_found(self, tmp_path):
        """LangGraph edge case: tool-call-only AIMessage → empty text."""
        events: List[HarnessEvent] = [
            _tool_use_event(),
            _result_event(),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionNotFoundError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert "Coach decision not found" in str(exc_info.value)

    def test_assistant_event_with_empty_text_raises_not_found(self, tmp_path):
        events: List[HarnessEvent] = [_assistant_event("")]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionNotFoundError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert "Coach decision not found" in str(exc_info.value)

    def test_non_json_fenced_block_does_not_match(self, tmp_path):
        """A ``\`\`\`python ... \`\`\`` block isn't a Coach verdict."""
        events: List[HarnessEvent] = [
            _assistant_event(
                "Here's some code:\n\n```python\nprint('hi')\n```\n\n"
                "Approving."
            ),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionNotFoundError):
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)


class TestMalformedJson:
    """Block found but JSON is broken → ``CoachDecisionInvalidError``."""

    def test_trailing_comma_raises_invalid(self, tmp_path):
        events: List[HarnessEvent] = [
            _assistant_event(
                'Final answer:\n\n```json\n{"task_id": "TASK-X", "turn": 1, '
                '"decision": "approve",}\n```'
            ),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionInvalidError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert "Coach decision invalid" in str(exc_info.value)

    def test_unclosed_string_raises_invalid(self, tmp_path):
        events: List[HarnessEvent] = [
            _assistant_event(
                '```json\n{"task_id": "TASK-X", "turn": 1, "decision": "approve\n```'
            ),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionInvalidError):
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)


class TestNonObjectJson:
    """JSON parses but is not a top-level object."""

    def test_top_level_array_raises_invalid(self, tmp_path):
        events: List[HarnessEvent] = [
            _assistant_event('```json\n[1, 2, 3]\n```'),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionInvalidError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert "Coach decision invalid" in str(exc_info.value)
        assert "object" in str(exc_info.value).lower()

    def test_top_level_string_raises_invalid(self, tmp_path):
        events: List[HarnessEvent] = [
            _assistant_event('```json\n"just a string"\n```'),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionInvalidError):
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)


class TestMissingRequiredFields:
    """Object but missing one of task_id / turn / decision."""

    def test_missing_decision_raises_invalid(self, tmp_path):
        events: List[HarnessEvent] = [
            _assistant_event(
                '```json\n{"task_id": "TASK-X", "turn": 1}\n```'
            ),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionInvalidError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert "Coach decision invalid" in str(exc_info.value)
        assert "decision" in str(exc_info.value)

    def test_missing_task_id_raises_invalid(self, tmp_path):
        events: List[HarnessEvent] = [
            _assistant_event(
                '```json\n{"turn": 1, "decision": "approve"}\n```'
            ),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionInvalidError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert "task_id" in str(exc_info.value)

    def test_missing_turn_raises_invalid(self, tmp_path):
        events: List[HarnessEvent] = [
            _assistant_event(
                '```json\n{"task_id": "TASK-X", "decision": "approve"}\n```'
            ),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionInvalidError):
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)


class TestInvalidDecisionValue:
    """``decision`` must be exactly ``"approve"`` or ``"feedback"``."""

    def test_decision_is_pending_raises_invalid(self, tmp_path):
        events: List[HarnessEvent] = [
            _assistant_event(
                '```json\n{"task_id": "TASK-X", "turn": 1, "decision": "pending"}\n```'
            ),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionInvalidError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert "approve" in str(exc_info.value)
        assert "feedback" in str(exc_info.value)


# --------------------------------------------------------------------------- #
# COACHSF01 coupling — Gap 2 from Phase 2.5B architectural review
# --------------------------------------------------------------------------- #


class TestCoachSf01ErrorStringCoupling:
    """Every parser exception must carry COACHSF01's grep substrings.

    ``autobuild.py:5676-5678`` matches on the literal strings
    ``"Coach decision not found"`` and ``"Coach decision invalid"`` to fire
    the synthetic-feedback safety net. If a future raise site forgets the
    prefix, COACHSF01 silently misses and the wave loop hard-fails.

    This test pins the contract for every error class the parser raises.
    """

    NOT_FOUND_SUBSTRING = "Coach decision not found"
    INVALID_SUBSTRING = "Coach decision invalid"

    @pytest.mark.parametrize(
        "events,task_id,turn,expected_substring",
        [
            # No JSON block at all
            (
                [AssistantMessageEvent(text="no fences here")],
                "TASK-FIX-COACHOUT01",
                1,
                NOT_FOUND_SUBSTRING,
            ),
            # No assistant text
            (
                [ToolUseEvent(tool_use_id="x", name="Bash", input={})],
                "TASK-FIX-COACHOUT01",
                1,
                NOT_FOUND_SUBSTRING,
            ),
            # Malformed JSON in last block
            (
                [AssistantMessageEvent(text='```json\n{not json}\n```')],
                "TASK-FIX-COACHOUT01",
                1,
                INVALID_SUBSTRING,
            ),
            # Non-object JSON
            (
                [AssistantMessageEvent(text='```json\n[1,2]\n```')],
                "TASK-FIX-COACHOUT01",
                1,
                INVALID_SUBSTRING,
            ),
            # Missing required field
            (
                [
                    AssistantMessageEvent(
                        text='```json\n{"task_id": "X", "turn": 1}\n```'
                    )
                ],
                "TASK-FIX-COACHOUT01",
                1,
                INVALID_SUBSTRING,
            ),
            # Invalid decision value
            (
                [
                    AssistantMessageEvent(
                        text='```json\n{"task_id": "X", "turn": 1, '
                             '"decision": "maybe"}\n```'
                    )
                ],
                "TASK-FIX-COACHOUT01",
                1,
                INVALID_SUBSTRING,
            ),
        ],
    )
    def test_every_error_path_contains_coachsf01_substring(
        self, tmp_path, events, task_id, turn, expected_substring
    ):
        out = _output_path(tmp_path, task_id, turn)
        with pytest.raises(
            (CoachDecisionNotFoundError, CoachDecisionInvalidError)
        ) as exc_info:
            extract_and_write(events, task_id, turn, out)

        # The COACHSF01 safety net does ``in result.error``, where
        # ``result.error == str(e)``. Mirror that check exactly.
        assert expected_substring in str(exc_info.value)


# --------------------------------------------------------------------------- #
# Atomic write semantics
# --------------------------------------------------------------------------- #


class TestAtomicWrite:
    """The parser writes via ``.tmp`` + ``os.replace``."""

    def test_no_tmp_leftover_on_success(self, tmp_path):
        payload = _make_approve_payload()
        events: List[HarnessEvent] = [_assistant_event(_fence(payload))]
        out = _output_path(tmp_path)

        extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)

        tmp_leftover = out.with_suffix(out.suffix + ".tmp")
        assert not tmp_leftover.exists()
        assert out.exists()

    def test_parent_directory_created_on_demand(self, tmp_path):
        """``output_path`` parent may not exist yet — parser mkdir's it."""
        payload = _make_feedback_payload()
        events: List[HarnessEvent] = [_assistant_event(_fence(payload))]
        out = tmp_path / "fresh" / "dir" / "coach_turn_5.json"

        assert not out.parent.exists()
        extract_and_write(events, "TASK-FIX-COACHOUT01", 5, out)
        assert out.exists()

    def test_overwrites_existing_file(self, tmp_path):
        """Re-running for the same turn must replace any previous file."""
        out = _output_path(tmp_path)
        out.parent.mkdir(parents=True)
        out.write_text(json.dumps({"stale": True}))

        payload = _make_approve_payload()
        events: List[HarnessEvent] = [_assistant_event(_fence(payload))]
        extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)

        assert json.loads(out.read_text()) == payload


# --------------------------------------------------------------------------- #
# TASK-FIX-COACHBUDG01 — hybrid reasoning models (reasoning_text fallback)
# --------------------------------------------------------------------------- #


class TestHybridReasoningFallback:
    """Coverage for AssistantMessageEvent.reasoning_text precedence.

    TASK-FIX-COACHBUDG01 (2026-06-06). Hybrid reasoning models (base Gemma 4
    IT under ``--reasoning auto``, Anthropic Claude with extended thinking,
    nemotron-3-super, deepseek-v4-flash) route chain-of-thought into a
    separate channel. The parser uses "prefer content, fall through to
    reasoning" precedence so:

    1. A model that mirrors the verdict to ``content`` is honoured there
       even when ``reasoning_text`` also contains a (possibly earlier /
       exploratory) fenced block.
    2. A model whose ``content`` channel is empty or has no fenced block
       still parses successfully when the verdict landed in
       ``reasoning_text`` — closes the empirical §9.13 failure mode where
       the F17 prose-before-JSON symptom would re-surface as
       reasoning-before-JSON.
    3. A model whose BOTH channels are empty still raises
       CoachDecisionNotFoundError so COACHSF01 fires.

    Empirical evidence: §9.14 of
    ``docs/research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md``
    (gemma4-coach with ``--reasoning auto`` + 16384 max_tokens —
    content 364 chars + reasoning_content 4450 chars, both fenced).
    """

    def test_block_in_content_only_parses_canonically(self, tmp_path):
        """Legacy case — verdict mirrored to content, no thinking blocks.

        Pre-COACHBUDG01 behavior must be preserved bit-for-bit when
        reasoning_text is empty.
        """
        payload = _make_approve_payload()
        events: List[HarnessEvent] = [
            AssistantMessageEvent(
                text="All ACs verified.\n\n" + _fence(payload),
                reasoning_text="",
            ),
            _result_event(),
        ]
        out = _output_path(tmp_path)

        result = extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert result == payload

    def test_block_in_reasoning_only_falls_through(self, tmp_path):
        """COACHBUDG01 core — empty content, verdict in reasoning_text.

        This is the gemma4-coach-with-reasoning-auto failure mode that
        TASK-FIX-COACHBUDG01 is meant to close. Without the fallback, the
        Coach turn would raise CoachDecisionNotFoundError and the
        COACHSF01 safety net would mask a real verdict.
        """
        payload = _make_feedback_payload()
        events: List[HarnessEvent] = [
            AssistantMessageEvent(
                text="",  # content stream empty — model emitted only to thinking
                reasoning_text=(
                    "Reasoning through AC list...\n"
                    "AC-001 is partial — tests are red.\n\n"
                    + _fence(payload)
                ),
            ),
        ]
        out = _output_path(tmp_path)

        result = extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert result == payload
        assert json.loads(out.read_text()) == payload

    def test_block_in_both_prefers_content(self, tmp_path):
        """AC-004 "prefer content" — if both channels have a block, content wins.

        Empirical pattern: gemma4-coach with ``--reasoning auto`` + 16384
        budget mirrors the verdict to BOTH content AND reasoning_content
        (see §9.14 probe — 364 chars content + 4450 chars reasoning,
        both fenced). Content is the authoritative version; reasoning is
        the exploratory draft. Parser must NOT pick the reasoning block.
        """
        # Distinguishable payloads so we can prove which channel won.
        canonical = _make_approve_payload(turn=1)
        exploratory = _make_feedback_payload(turn=1)
        events: List[HarnessEvent] = [
            AssistantMessageEvent(
                text="Final verdict:\n\n" + _fence(canonical),
                reasoning_text=(
                    "Initial thought: maybe feedback?\n"
                    + _fence(exploratory)
                    + "\nBut on reflection, all ACs are met. Approve."
                ),
            ),
        ]
        out = _output_path(tmp_path)

        result = extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        assert result["decision"] == "approve"
        assert result == canonical
        assert json.loads(out.read_text()) == canonical

    def test_neither_channel_has_block_raises_decision_not_found(self, tmp_path):
        """Both channels populated but neither has a fenced block.

        Must still raise CoachDecisionNotFoundError with the COACHSF01-
        coupled substring. The error message records both channel sizes
        so the operator can tell from the log whether reasoning was
        emitted (helps diagnose substrate behaviour without re-running).
        """
        events: List[HarnessEvent] = [
            AssistantMessageEvent(
                text="I think the implementation is fine but I won't emit JSON.",
                reasoning_text=(
                    "Pondering... no block here either, the model has "
                    "decided to ignore the structured-output instruction."
                ),
            ),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionNotFoundError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHBUDG01", 4, out)

        msg = str(exc_info.value)
        assert "Coach decision not found" in msg  # COACHSF01 coupling
        # Both lengths recorded — useful diagnostic for substrate review
        assert "content" in msg
        assert "reasoning_content" in msg

    def test_both_channels_empty_raises_decision_not_found(self, tmp_path):
        """Pre-COACHBUDG01 LangGraph edge case still raises.

        A final tool-call-only AIMessage with empty content AND no
        thinking blocks collapses to an empty AssistantMessageEvent in
        both channels. The "no assistant text at all" branch still
        fires — substrate parity with the legacy behaviour.
        """
        events: List[HarnessEvent] = [
            AssistantMessageEvent(text="", reasoning_text=""),
        ]
        out = _output_path(tmp_path)

        with pytest.raises(CoachDecisionNotFoundError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHBUDG01", 4, out)

        msg = str(exc_info.value)
        assert "Coach decision not found" in msg
        assert "0 AssistantMessageEvent" in msg

    def test_reasoning_text_field_defaults_to_empty_string(self):
        """AssistantMessageEvent backwards-compat — legacy callers don't break.

        Any code constructing AssistantMessageEvent(text=...) without the
        new reasoning_text kwarg should still work, with reasoning_text
        defaulting to "". This is the contract that keeps existing
        sdk_harness tests, langgraph_harness tests (in guardkitfactory),
        and the SubstrateParity test class above all unchanged.
        """
        event = AssistantMessageEvent(text="hello")
        assert event.text == "hello"
        assert event.reasoning_text == ""
        # The dataclass remains frozen — sanity-check immutability is preserved
        with pytest.raises((AttributeError, Exception)):
            event.reasoning_text = "mutated"  # type: ignore[misc]

    def test_multi_event_stream_concatenates_both_channels(self, tmp_path):
        """SDK-style multi-event streams: reasoning_text joined per-event.

        Mirrors :class:`TestSubstrateParity` for the legacy ``text`` field
        but applied to ``reasoning_text``. Each AssistantMessageEvent
        contributes its own reasoning chunk; the parser joins with
        newlines and treats the result as a single stream when scanning
        for the fenced block.
        """
        payload = _make_approve_payload()
        events: List[HarnessEvent] = [
            AssistantMessageEvent(
                text="",
                reasoning_text="Reading task plan...\n",
            ),
            AssistantMessageEvent(
                text="",
                reasoning_text="Confirming AC list ...\n\n" + _fence(payload),
            ),
            _result_event(),
        ]
        out = _output_path(tmp_path)

        result = extract_and_write(events, "TASK-FIX-COACHBUDG01", 1, out)
        assert result == payload


# --------------------------------------------------------------------------- #
# TASK-CMIR-001 — v4 contract parsing + wire-to-internal adapter
# --------------------------------------------------------------------------- #


def _make_v4_approve_payload(findings: list | None = None) -> dict:
    """A minimal v4 approval verdict (findings must be empty)."""
    return {
        "verdict": "approve",
        "findings": findings or [],
    }


def _make_v4_reject_payload() -> dict:
    """A minimal v4 reject verdict with a valid finding."""
    return {
        "verdict": "reject",
        "findings": [
            {
                "locus": "guardkit/orchestrator/coach_output_parser.py:150",
                "category": "major",
                "recommendation": "Fix the regex",
            }
        ],
    }


def _make_v4_reject_payload_empty_locus() -> dict:
    """A v4 reject verdict with an empty locus (invalid)."""
    return {
        "verdict": "reject",
        "findings": [
            {
                "locus": "",
                "category": "major",
            }
        ],
    }


class TestV4RawParsing:
    """contract=v4: raw v4 JSON parses via whole-text json.loads."""

    def test_v4_approve_raw_parses_and_adapts(self, tmp_path):
        v4_payload = _make_v4_approve_payload()
        events: List[HarnessEvent] = [_assistant_event(json.dumps(v4_payload))]
        out = _output_path(tmp_path, turn=1)

        result = extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")

        assert result["decision"] == "approve"
        assert result["task_id"] == "TASK-CMIR-001"
        assert result["turn"] == 1
        assert result["issues"] == []
        assert result["contract"] == "v4"
        assert result["findings_provenance"] == "coach-ft-v4"
        assert out.exists()
        written = json.loads(out.read_text())
        assert written["decision"] == "approve"

    def test_v4_reject_raw_parses_and_adapts(self, tmp_path):
        v4_payload = _make_v4_reject_payload()
        events: List[HarnessEvent] = [_assistant_event(json.dumps(v4_payload))]
        out = _output_path(tmp_path, turn=2)

        result = extract_and_write(events, "TASK-CMIR-001", 2, out, contract="v4")

        assert result["decision"] == "feedback"
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "finding"
        assert result["issues"][0]["severity"] == "major"
        assert result["issues"][0]["description"] == "guardkit/orchestrator/coach_output_parser.py:150"
        assert result["issues"][0]["suggestion"] == ""

    def test_v4_raw_with_stray_prefix_does_not_parse_raw(self, tmp_path):
        """Text with leading prose fails raw json.loads — falls to balanced."""
        v4_payload = _make_v4_approve_payload()
        text = "Some stray text\n\n" + json.dumps(v4_payload)
        events: List[HarnessEvent] = [_assistant_event(text)]
        out = _output_path(tmp_path, turn=1)

        result = extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")
        assert result["decision"] == "approve"


class TestV4BalancedObjectParsing:
    """contract=v4: v4 object embedded after stray text via last-balanced-object."""

    def test_balanced_object_containing_verdict_found(self, tmp_path):
        v4_payload = _make_v4_approve_payload()
        text = (
            "Here's some analysis:\n"
            '{"some": "other", "data": true}\n'
            + json.dumps(v4_payload)
        )
        events: List[HarnessEvent] = [_assistant_event(text)]
        out = _output_path(tmp_path, turn=1)

        result = extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")

        assert result["decision"] == "approve"

    def test_last_balanced_object_wins(self, tmp_path):
        """When multiple objects contain 'verdict', the last one wins."""
        first = {"verdict": "reject", "findings": [{"locus": "old"}]}
        second = _make_v4_approve_payload()
        text = json.dumps(first) + "\n\n" + json.dumps(second)
        events: List[HarnessEvent] = [_assistant_event(text)]
        out = _output_path(tmp_path, turn=1)

        result = extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")

        assert result["decision"] == "approve"

    def test_no_balanced_object_falls_to_legacy(self, tmp_path):
        """No v4 object found → legacy fenced-block fallback."""
        legacy_payload = _make_approve_payload()
        events: List[HarnessEvent] = [_assistant_event(_fence(legacy_payload))]
        out = _output_path(tmp_path, turn=1)

        result = extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")

        # Should get the legacy shape back
        assert result["decision"] == "approve"
        assert "task_id" in result

    def test_balanced_object_without_verdict_ignored(self, tmp_path):
        """A balanced object without 'verdict' is skipped."""
        text = json.dumps({"other": "data"})
        events: List[HarnessEvent] = [_assistant_event(text)]
        out = _output_path(tmp_path, turn=1)

        with pytest.raises(CoachDecisionNotFoundError):
            extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")


class TestV4Adaptation:
    """Verify the wire-to-internal adapter mapping."""

    def test_severity_is_constant_major_must_fix(self, tmp_path):
        """Spec §2: every v4 finding is a rejection reason — severity is
        CONSTANT "major" (the must_fix bucket boundary is critical|major),
        regardless of any extra keys the wire might carry."""
        v4_payload = {
            "verdict": "reject",
            "findings": [
                {"locus": "file.py:1", "category": "major"},
                {"locus": "file.py:2", "category": "minor"},
                {"locus": "file.py:3"},
            ],
        }
        events: List[HarnessEvent] = [_assistant_event(json.dumps(v4_payload))]
        out = _output_path(tmp_path, turn=1)

        result = extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")
        assert [i["severity"] for i in result["issues"]] == ["major"] * 3
        assert all(i["type"] == "finding" for i in result["issues"])


    def test_suggestion_is_empty_locus_is_description(self, tmp_path):
        """Spec §2: the wire carries only locus; suggestion/requirement are
        empty strings — extra wire keys are tolerated but never trusted."""
        v4_payload = {
            "verdict": "reject",
            "findings": [
                {
                    "locus": "test.py:42",
                    "category": "major",
                    "recommendation": "Update the assertion",
                }
            ],
        }
        events: List[HarnessEvent] = [_assistant_event(json.dumps(v4_payload))]
        out = _output_path(tmp_path, turn=1)

        result = extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")
        issue = result["issues"][0]
        assert issue["description"] == "test.py:42"
        assert issue["suggestion"] == ""
        assert issue["requirement"] == ""
        assert issue["severity"] == "major"

class TestV4Validation:
    """v4-specific validation: approve⇒empty findings, reject⇒non-empty locus."""

    def test_v4_approve_with_findings_raises_invalid(self, tmp_path):
        v4_payload = _make_v4_approve_payload(
            findings=[{"locus": "file.py:1"}]
        )
        events: List[HarnessEvent] = [_assistant_event(json.dumps(v4_payload))]
        out = _output_path(tmp_path, turn=1)

        with pytest.raises(CoachDecisionInvalidError) as exc_info:
            extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")
        assert "Coach decision invalid" in str(exc_info.value)
        assert "approve" in str(exc_info.value)
        assert "empty findings" in str(exc_info.value)

    def test_v4_reject_with_empty_locus_raises_invalid(self, tmp_path):
        v4_payload = _make_v4_reject_payload_empty_locus()
        events: List[HarnessEvent] = [_assistant_event(json.dumps(v4_payload))]
        out = _output_path(tmp_path, turn=1)

        with pytest.raises(CoachDecisionInvalidError) as exc_info:
            extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")
        assert "Coach decision invalid" in str(exc_info.value)
        assert "empty locus" in str(exc_info.value)

    def test_v4_reject_with_valid_locus_passes(self, tmp_path):
        v4_payload = _make_v4_reject_payload()
        events: List[HarnessEvent] = [_assistant_event(json.dumps(v4_payload))]
        out = _output_path(tmp_path, turn=1)

        result = extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")

        assert result["decision"] == "feedback"


class TestV4LegacyFallback:
    """contract=v4: fenced LEGACY reply falls back to unchanged parser."""

    def test_legacy_fenced_block_falls_through(self, tmp_path):
        legacy_payload = _make_feedback_payload()
        events: List[HarnessEvent] = [_assistant_event(_fence(legacy_payload))]
        out = _output_path(tmp_path, turn=1)

        result = extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")

        assert result["decision"] == "feedback"
        assert result["task_id"] == "TASK-FIX-COACHOUT01"

    def test_legacy_fallback_logs_marker(self, tmp_path, caplog):
        legacy_payload = _make_approve_payload()
        events: List[HarnessEvent] = [_assistant_event(_fence(legacy_payload))]
        out = _output_path(tmp_path, turn=1)

        with caplog.at_level(logging.WARNING):
            extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")

        assert any(
            "contract=v4" in record.message and "legacy-fallback" in record.message
            for record in caplog.records
        )


class TestContractCoachsplit:
    """contract=coachsplit (default): byte-identical to today."""

    def test_default_contract_is_coachsplit(self):
        from guardkit.orchestrator.coach_output_parser import _resolve_contract
        # Must run without GUARDKIT_COACH_CONTRACT set
        import os
        os.environ.pop("GUARDKIT_COACH_CONTRACT", None)
        assert _resolve_contract() == "coachsplit"

    def test_explicit_coachsplit_uses_legacy_path(self, tmp_path):
        payload = _make_approve_payload()
        events: List[HarnessEvent] = [_assistant_event(_fence(payload))]
        out = _output_path(tmp_path, turn=1)

        result = extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out, contract="coachsplit")

        assert result == payload

    def test_existing_error_paths_unchanged(self, tmp_path):
        """No block → CoachDecisionNotFoundError with COACHSF01 substring."""
        events: List[HarnessEvent] = [_assistant_event("no fences")]
        out = _output_path(tmp_path, turn=1)

        with pytest.raises(CoachDecisionNotFoundError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out, contract="coachsplit")
        assert "Coach decision not found" in str(exc_info.value)


class TestV4Logging:
    """AC-004: every successful parse logs which path fired."""

    def test_v4_raw_path_logged(self, tmp_path, caplog):
        v4_payload = _make_v4_approve_payload()
        events: List[HarnessEvent] = [_assistant_event(json.dumps(v4_payload))]
        out = _output_path(tmp_path, turn=1)

        with caplog.at_level(logging.DEBUG):
            extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")

        assert any(
            "contract=v4" in record.message and "path=raw" in record.message
            for record in caplog.records
        )

    def test_v4_balanced_path_logged(self, tmp_path, caplog):
        v4_payload = _make_v4_approve_payload()
        text = "stray text\n" + json.dumps(v4_payload)
        events: List[HarnessEvent] = [_assistant_event(text)]
        out = _output_path(tmp_path, turn=1)

        with caplog.at_level(logging.DEBUG):
            extract_and_write(events, "TASK-CMIR-001", 1, out, contract="v4")

        assert any(
            "contract=v4" in record.message and "path=balanced" in record.message
            for record in caplog.records
        )

    def test_legacy_path_logged(self, tmp_path, caplog):
        payload = _make_approve_payload()
        events: List[HarnessEvent] = [_assistant_event(_fence(payload))]
        out = _output_path(tmp_path, turn=1)

        with caplog.at_level(logging.DEBUG):
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)

        assert any(
            "fenced block" in record.message
            for record in caplog.records
        )
