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
