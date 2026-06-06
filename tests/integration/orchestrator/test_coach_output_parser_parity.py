"""Substrate-parity + COACHSF01 coupling tests for the Coach output parser.

TASK-FIX-COACHOUT01 Shape A — integration tests called out in
``docs/state/TASK-FIX-COACHOUT01/implementation_plan.md`` §8 Phase 3:

> "Phase 3 — Parity + integration tests (45 minutes)
>  Write or extend ``tests/integration/test_coach_parity.py``. The test
>  must:
>  1. Instantiate a synthetic AssistantMessageEvent stream with a valid
>     fenced JSON block.
>  2. Run through the new code path.
>  3. Assert coach_turn_N.json is written correctly.
>  4. Repeat with an SDK-harness fake and a LangGraph-harness fake."

The parser is structurally substrate-agnostic — it operates on the
``List[HarnessEvent]`` ABC at ``guardkit/orchestrator/harness/adapter.py``,
which both harnesses populate identically (``AssistantMessageEvent`` with
``text``). The architectural review at
``docs/state/TASK-FIX-COACHOUT01/architectural_review.md`` §"Substrate
Parity Assessment" verified this empirically against ``sdk_harness.py:340``
and ``langgraph_harness.py:370``.

These tests pin that contract:

* **Single-event LangGraph shape** (qwen36-workhorse via DeepAgents emits
  exactly one ``AssistantMessageEvent`` per turn).
* **Multi-event SDK shape** (Sonnet streams may produce multiple
  ``AssistantMessageEvent`` per turn — the parser concatenates them).
* **Identical disk output** from both shapes given equivalent verdicts.
* **Gap 2 COACHSF01 coupling** — ``CoachDecisionNotFoundError`` raised by
  the parser carries the exact substring ``autobuild.py:5676-5678``
  greps for to fire the synthetic-feedback safety net. This is the
  Phase 2.5B architectural review's explicit "add ONE unit test" ask.
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
# Substrate-shape simulators
# --------------------------------------------------------------------------- #


def _fenced(payload: dict) -> str:
    return f"```json\n{json.dumps(payload, indent=2)}\n```"


def _langgraph_style_events(payload: dict) -> List[HarnessEvent]:
    """One ``AssistantMessageEvent`` carrying the full Coach response.

    Mirrors ``LangGraphHarness.invoke()`` at
    ``guardkitfactory/.../langgraph_harness.py:357-370``: it calls
    ``extract_last_ai_message(result)`` which returns a single content
    string, then yields exactly one ``AssistantMessageEvent``. The Coach
    prose and the fenced JSON block both live in that one event.
    """
    full_text = (
        "I ran the tests and inspected each acceptance criterion.\n\n"
        "All acceptance criteria are satisfied.\n\n"
        + _fenced(payload)
    )
    return [
        AssistantMessageEvent(text=full_text),
        ResultMessageEvent(session_id="lg-session-001"),
    ]


def _sdk_style_events(payload: dict) -> List[HarnessEvent]:
    """Several ``AssistantMessageEvent``s carrying chunks of one response.

    Mirrors ``ClaudeSDKHarness.invoke()`` at
    ``guardkit/orchestrator/harness/sdk_harness.py:319-340``: it iterates
    the SDK message stream and yields one ``AssistantMessageEvent`` per
    ``AssistantMessage``. Sonnet may stream the prose in one event and
    the final fenced JSON block in another, interleaved with
    ``ToolUseEvent``s for any Bash/Read commands Coach ran during
    verification.
    """
    return [
        AssistantMessageEvent(
            text="I ran the tests and inspected each acceptance criterion.\n"
        ),
        # Coach actually ran a tool — this event must NOT contribute to
        # the verdict text. The parser skips non-AssistantMessageEvent.
        ToolUseEvent(
            tool_use_id="tu-bash-1",
            name="Bash",
            input={"command": "pytest tests/ -v"},
        ),
        AssistantMessageEvent(
            text="\nAll acceptance criteria are satisfied.\n\n"
            + _fenced(payload)
        ),
        ResultMessageEvent(session_id="sdk-session-001"),
    ]


# --------------------------------------------------------------------------- #
# Substrate parity
# --------------------------------------------------------------------------- #


class TestSubstrateParity:
    """Both harness shapes yield the same ``coach_turn_N.json`` on disk."""

    @pytest.fixture
    def approve_payload(self) -> dict:
        return {
            "task_id": "TASK-FIX-COACHOUT01",
            "turn": 1,
            "decision": "approve",
            "validation_results": {
                "requirements_met": ["AC-001", "AC-002"],
                "tests_run": True,
                "tests_passed": True,
                "test_command": "pytest tests/",
                "test_output_summary": "all green",
                "code_quality": "ok",
                "edge_cases_covered": ["empty input"],
            },
            "rationale": "All ACs verified.",
        }

    @pytest.fixture
    def feedback_payload(self) -> dict:
        return {
            "task_id": "TASK-FIX-COACHOUT01",
            "turn": 2,
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

    def test_langgraph_and_sdk_yield_identical_files_on_approve(
        self, tmp_path, approve_payload
    ):
        lg_out = tmp_path / "lg" / "coach_turn_1.json"
        sdk_out = tmp_path / "sdk" / "coach_turn_1.json"

        extract_and_write(
            _langgraph_style_events(approve_payload),
            "TASK-FIX-COACHOUT01",
            1,
            lg_out,
        )
        extract_and_write(
            _sdk_style_events(approve_payload),
            "TASK-FIX-COACHOUT01",
            1,
            sdk_out,
        )

        # Identical bytes on disk modulo the file system — parser is
        # substrate-agnostic by construction.
        assert json.loads(lg_out.read_text()) == approve_payload
        assert json.loads(sdk_out.read_text()) == approve_payload
        assert lg_out.read_text() == sdk_out.read_text()

    def test_langgraph_and_sdk_yield_identical_files_on_feedback(
        self, tmp_path, feedback_payload
    ):
        lg_out = tmp_path / "lg" / "coach_turn_2.json"
        sdk_out = tmp_path / "sdk" / "coach_turn_2.json"

        extract_and_write(
            _langgraph_style_events(feedback_payload),
            "TASK-FIX-COACHOUT01",
            2,
            lg_out,
        )
        extract_and_write(
            _sdk_style_events(feedback_payload),
            "TASK-FIX-COACHOUT01",
            2,
            sdk_out,
        )

        assert json.loads(lg_out.read_text()) == feedback_payload
        assert json.loads(sdk_out.read_text()) == feedback_payload


# --------------------------------------------------------------------------- #
# Gap 2 (Phase 2.5B architectural review) — COACHSF01 error-string coupling
# --------------------------------------------------------------------------- #


class TestCoachSF01Coupling:
    """The Phase 2.5B review's "add ONE unit test" ask, expanded.

    ``autobuild.py:5676-5678`` matches on the literal substrings
    ``"Coach decision not found"`` and ``"Coach decision invalid"`` to fire
    its synthetic-feedback fallback when ``invoke_coach`` returns
    ``success=False``. If the parser's raise sites stop using those
    substrings, the safety net silently misses every verdict-emission
    failure and the wave loop hard-fails the turn.

    These tests pin the contract end-to-end against the actual COACHSF01
    grep predicate (extracted verbatim from
    ``guardkit/orchestrator/autobuild.py``).
    """

    # Extracted verbatim from autobuild.py:5676-5678 — the canonical
    # source of truth for what strings the safety net catches. If this
    # tuple ever drifts from the autobuild.py source, COACHSF01 will
    # silently miss the failure class.
    COACHSF01_SUBSTRINGS = ("Coach decision not found", "Coach decision invalid")

    @staticmethod
    def _would_coachsf01_fire(error: str) -> bool:
        """Mirror exactly the predicate at autobuild.py:5672-5678."""
        return any(
            s in error for s in TestCoachSF01Coupling.COACHSF01_SUBSTRINGS
        )

    def test_no_block_raises_with_coachsf01_substring(self, tmp_path):
        # qwen36-workhorse F2-at-Coach-level: Coach completes the turn
        # but emits no fenced JSON block at all.
        events: List[HarnessEvent] = [
            AssistantMessageEvent(
                text="I verified the tests. All looks good — approving."
            ),
        ]
        out = tmp_path / "coach_turn_1.json"

        with pytest.raises(CoachDecisionNotFoundError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)

        assert self._would_coachsf01_fire(str(exc_info.value)), (
            "Parser exception text must contain a COACHSF01 substring so "
            "the synthetic-feedback safety net at autobuild.py:5672-5698 "
            "fires when invoke_coach returns success=False, error=str(e)."
        )

    def test_no_assistant_events_raises_with_coachsf01_substring(self, tmp_path):
        # LangGraph edge case: tool-call-only AIMessage → empty text.
        events: List[HarnessEvent] = [
            ToolUseEvent(tool_use_id="tu-1", name="Bash", input={"command": "ls"}),
        ]
        out = tmp_path / "coach_turn_1.json"

        with pytest.raises(CoachDecisionNotFoundError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)

        assert self._would_coachsf01_fire(str(exc_info.value))

    def test_malformed_json_raises_with_coachsf01_substring(self, tmp_path):
        events: List[HarnessEvent] = [
            AssistantMessageEvent(
                text='Final answer:\n\n```json\n{"task_id": "TASK-X", '
                     '"turn": 1, "decision": "approve",}\n```'
            ),
        ]
        out = tmp_path / "coach_turn_1.json"

        with pytest.raises(CoachDecisionInvalidError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)

        assert self._would_coachsf01_fire(str(exc_info.value))

    def test_invalid_decision_value_raises_with_coachsf01_substring(self, tmp_path):
        events: List[HarnessEvent] = [
            AssistantMessageEvent(
                text='```json\n{"task_id": "TASK-X", "turn": 1, '
                     '"decision": "maybe"}\n```'
            ),
        ]
        out = tmp_path / "coach_turn_1.json"

        with pytest.raises(CoachDecisionInvalidError) as exc_info:
            extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)

        assert self._would_coachsf01_fire(str(exc_info.value))


# --------------------------------------------------------------------------- #
# Documented qwen36-workhorse failure pattern: exploratory-then-corrected
# --------------------------------------------------------------------------- #


class TestExploratoryThenCorrected:
    """When Coach drafts a block, reasons further, then emits a corrected
    block, the parser MUST take the last block.

    This is a real qwen36-workhorse pattern observed in run-5 of FEAT-AOF
    (see ``docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-5.md``):
    the model emits a tentative decision, then reconsiders mid-response.
    """

    def test_two_decision_blocks_last_one_wins(self, tmp_path):
        first = {
            "task_id": "TASK-FIX-COACHOUT01",
            "turn": 1,
            "decision": "feedback",
            "issues": [],
            "rationale": "First pass — wrong.",
        }
        second = {
            "task_id": "TASK-FIX-COACHOUT01",
            "turn": 1,
            "decision": "approve",
            "validation_results": {
                "requirements_met": ["AC-001"],
                "tests_run": True,
                "tests_passed": True,
                "test_command": "pytest",
                "test_output_summary": "ok",
                "code_quality": "ok",
                "edge_cases_covered": [],
            },
            "rationale": "Re-checked, all ACs satisfied.",
        }

        events: List[HarnessEvent] = [
            AssistantMessageEvent(
                text="Initial impression:\n" + _fenced(first)
                + "\n\nOn re-check after reading the test output more carefully:\n"
                + _fenced(second)
            ),
        ]
        out = tmp_path / "coach_turn_1.json"

        result = extract_and_write(events, "TASK-FIX-COACHOUT01", 1, out)
        on_disk = json.loads(out.read_text())

        assert result["decision"] == "approve"
        assert on_disk["decision"] == "approve"
        assert on_disk["rationale"] == "Re-checked, all ACs satisfied."
