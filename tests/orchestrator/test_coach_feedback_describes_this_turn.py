"""Coach feedback describes this turn, not the last one (12 October 2026).

Modelled on build 7010, task three. On turn three the reviewer's own run of
the required test command failed while deploying its stack ("No such
container"). On turn four the same command failed on a DNS lookup, but the
reviewer's written issue repeated turn three's missing-container text byte for
byte, and that prose was all the Player was told. Two causes, each pinned
here:

1. The Coach's context carried the previous turn's summary, and that summary
   carried the previous Coach's feedback. The Coach-side summary now leaves
   out everything the previous Coach wrote; the Player's is unchanged.
2. Nothing deterministic about the failed run reached the Player. When the
   run failed, the Player's feedback now starts with the turn, the command,
   the exit status and the first failing lines of THIS turn's run.

The tests drive the real turn-state file, the real context loader, the real
Coach prompt, the real evidence merge, the real feedback text, the real
feedback file and the real Player-prompt formatter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
from guardkit.knowledge.job_context_retriever import RetrievedContext
from guardkit.knowledge.turn_state_operations import _format_turn_state_body
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.failing_test_feedback import (
    INDEPENDENT_FAILURE_LINES_SHOWN,
    describe_independent_suite_failure,
    first_failing_lines,
    must_fix_items,
    without_independent_suite_failure,
)
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidationResult,
    IndependentTestResult,
)
from guardkit.orchestrator.coach_verification import HonestyVerification


TASK_ID = "TASK-7010-003"
FEATURE_ID = "FEAT-7010"
COMMAND = "qa/run-suite.sh"

# Turn three's failure, as the reviewer described it (the 7010 excerpt).
TURN_3_TEXT = (
    "Error response from daemon: No such container: "
    "8b31a1e7fab15bb242264467e0cb6c6751ee5cfa0e07b9795c8ec350518d02bf"
)
TURN_3_ISSUE = (
    "evidence_bundle.independent_tests.tests_passed is false. The independent "
    f"test run ({COMMAND}) failed with 1 failure: 'FAILED "
    "tests/acceptance/users_roundtrip.py::test_users_roundtrip_smoke'. The "
    f"failure occurred during stack deployment: '{TURN_3_TEXT}'."
)

# Turn four's own run: the DNS failure (the 7010 excerpt), inside an
# otherwise ordinary run's output.
TURN_4_DNS_LINE = (
    '"detail": "GET /users network error: <urlopen error [Errno -3] '
    'Temporary failure in name resolution>"'
)
TURN_4_OUTPUT = "\n".join([
    "collected 885 items",
    "tests/acceptance/users_roundtrip.py F",
    "",
    "    def test_users_roundtrip_smoke(stack):",
    "        response = probe(stack, '/users')",
    f"        {TURN_4_DNS_LINE}",
    "FAILED tests/acceptance/users_roundtrip.py::test_users_roundtrip_smoke",
    "1 failed, 884 passed in 211.40s",
])


def _turn_3_state() -> Dict[str, Any]:
    """turn_state_turn_3.json as 7010 wrote it: the Coach's turn-3 words."""
    return {
        "id": f"TURN-{FEATURE_ID}-3",
        "feature_id": FEATURE_ID,
        "task_id": TASK_ID,
        "turn_number": 3,
        "player_summary": "Re-ran the suite; the stack collided on the daemon.",
        "player_decision": "implemented",
        "coach_decision": "feedback",
        "coach_feedback": f"- MUST FIX: {TURN_3_ISSUE}",
        "blockers_found": ["shared Docker daemon"],
        "progress_summary": "Turn 3: feedback",
        "acceptance_criteria_status": {"AC-001": "completed"},
        "lessons_from_turn": [f"The stack deploy failed: {TURN_3_TEXT}"],
        "what_to_try_next": f"Fix the deploy failure: {TURN_3_TEXT}",
    }


def _loader(worktree: Path) -> AutoBuildContextLoader:
    """The real loader over the worktree, with an empty memory search."""
    autobuild_dir = worktree / ".guardkit" / "autobuild" / TASK_ID
    autobuild_dir.mkdir(parents=True)
    (autobuild_dir / "turn_state_turn_3.json").write_text(
        json.dumps(_turn_3_state(), indent=2)
    )
    graphiti = MagicMock()
    graphiti.enabled = True
    loader = AutoBuildContextLoader(graphiti=graphiti, worktree_path=worktree)
    retriever = MagicMock()

    async def _retrieve(**_: Any) -> RetrievedContext:
        return RetrievedContext(
            task_id=TASK_ID,
            budget_used=0,
            budget_total=4000,
            feature_context=[],
            similar_outcomes=[],
            relevant_patterns=[],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
        )

    retriever.retrieve = _retrieve
    loader._retriever = retriever
    return loader


def _turn_4_run() -> IndependentTestResult:
    return IndependentTestResult.from_run(
        tests_passed=False,
        test_command=COMMAND,
        test_output_summary="1 failed, 884 passed",
        duration_seconds=211.4,
        output=TURN_4_OUTPUT,
        resolved_interpreter=None,
        exit_code=1,
    )


# ---------------------------------------------------------------------------
# 1. The Coach is not told what the last Coach said
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_turn_4_coach_context_does_not_carry_turn_3s_text(
    tmp_path: Path,
) -> None:
    loader = _loader(tmp_path)

    coach = await loader.get_coach_context(
        task_id=TASK_ID,
        feature_id=FEATURE_ID,
        turn_number=4,
        description="Wire the created-per-day route",
    )

    # The previous turn is still summarised for the Coach...
    assert "## Previous Turn Summary (Turn 3)" in coach.prompt_text
    assert "**Coach decision**: feedback" in coach.prompt_text
    # ...but nothing the previous Coach wrote reaches it.
    assert "No such container" not in coach.prompt_text
    assert "8b31a1e7" not in coach.prompt_text

    # And the prompt the Coach is actually sent carries none of it either.
    invoker = AgentInvoker(worktree_path=tmp_path)
    prompt = invoker._build_coach_prompt(
        task_id=TASK_ID,
        turn=4,
        requirements="Wire the created-per-day route",
        player_report={"task_id": TASK_ID, "turn": 4},
        coach_context=coach.prompt_text,
    )
    assert "## Coach Context" in prompt
    assert "Previous Turn Summary (Turn 3)" in prompt
    assert "No such container" not in prompt


@pytest.mark.asyncio
async def test_the_player_still_gets_the_previous_coach_feedback(
    tmp_path: Path,
) -> None:
    loader = _loader(tmp_path)

    player = await loader.get_player_context(
        task_id=TASK_ID,
        feature_id=FEATURE_ID,
        turn_number=4,
        description="Wire the created-per-day route",
    )

    assert f"**Coach feedback**: - MUST FIX: {TURN_3_ISSUE}" in player.prompt_text
    assert "**Lessons learned**" in player.prompt_text
    assert "**Suggested focus for this turn**" in player.prompt_text


def test_the_coach_side_summary_leaves_out_only_the_coaches_words() -> None:
    body = _turn_3_state()

    with_feedback = _format_turn_state_body(body, 3)
    without = _format_turn_state_body(body, 3, include_coach_feedback=False)

    assert with_feedback == _format_turn_state_body(
        body, 3, include_coach_feedback=True
    ), "the default (the Player's summary) is unchanged"
    assert TURN_3_TEXT in with_feedback
    assert TURN_3_TEXT not in without
    for kept in (
        "**What was attempted**",
        "**Player decision**: implemented",
        "**Coach decision**: feedback",
        "**Blockers found**: shared Docker daemon",
        "AC-001: completed",
    ):
        assert kept in without


# ---------------------------------------------------------------------------
# 2. The Player is told what THIS turn's run said
# ---------------------------------------------------------------------------


def test_the_turn_4_player_feedback_names_turn_4_and_the_dns_failure(
    tmp_path: Path,
) -> None:
    """The model repeats turn three's prose; the Player still sees turn four."""
    bundle = CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
        independent_tests=_turn_4_run(),
    )
    # What the model wrote on 7010 turn four: turn three's words.
    report: Dict[str, Any] = {
        "task_id": TASK_ID,
        "turn": 4,
        "decision": "feedback",
        "rationale": "The independent suite failed.",
        "issues": [{
            "type": "finding",
            "severity": "major",
            "description": TURN_3_ISSUE,
        }],
    }
    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    orchestrator._merge_evidence_test_signal_into_report(report, bundle)

    text = orchestrator._turn_feedback_text(report, 4)

    assert text.startswith(
        "The required test command failed on this turn (turn 4)."
    )
    assert f"Command: {COMMAND}" in text
    assert "Exit status: 1" in text
    assert TURN_4_DNS_LINE in text
    # The model's issue is still there, after the facts, as a must-fix item.
    assert TURN_3_ISSUE in text
    assert must_fix_items(text) == [TURN_3_ISSUE]

    # The feedback file and the prompt the Player is given carry it too.
    invoker = AgentInvoker(worktree_path=tmp_path)
    feedback_path = invoker._write_coach_feedback(TASK_ID, 5, text)
    written = json.loads(feedback_path.read_text())
    player_prompt = invoker.format_feedback_for_prompt(written)
    assert "turn 4" in player_prompt
    assert TURN_4_DNS_LINE in player_prompt


def test_a_legacy_coach_report_carries_the_same_facts() -> None:
    """The deterministic Coach's report reaches the same summary."""
    result = CoachValidationResult(
        task_id=TASK_ID,
        turn=4,
        decision="feedback",
        independent_tests=_turn_4_run(),
        issues=[{"severity": "must_fix", "description": "Tests failed"}],
        rationale="Independent tests failed.",
    )
    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)

    text = orchestrator._turn_feedback_text(result.to_dict(), 4)

    assert "(turn 4)" in text
    assert TURN_4_DNS_LINE in text
    assert "Exit status: 1" in text


@pytest.mark.parametrize(
    "run",
    [
        IndependentTestResult.from_run(
            tests_passed=True,
            test_command=COMMAND,
            test_output_summary="885 passed",
            duration_seconds=1.0,
            output="885 passed",
            resolved_interpreter=None,
            exit_code=0,
        ),
        IndependentTestResult.absent(
            test_command=COMMAND,
            test_output_summary="timed out",
            duration_seconds=1.0,
        ),
    ],
    ids=["passed", "absent"],
)
def test_no_summary_unless_the_run_ran_and_failed(run) -> None:
    bundle = CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
        independent_tests=run,
    )
    report: Dict[str, Any] = {
        "decision": "feedback",
        "issues": [{"severity": "major", "description": "Something else"}],
    }
    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    orchestrator._merge_evidence_test_signal_into_report(report, bundle)

    assert orchestrator._turn_feedback_text(report, 4) == (
        orchestrator._extract_feedback(report)
    )


def test_a_planted_receipt_in_the_models_report_is_replaced() -> None:
    """Only this turn's run supplies the facts, never the model's report."""
    bundle = CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
        independent_tests=_turn_4_run(),
    )
    report: Dict[str, Any] = {
        "decision": "feedback",
        "issues": [],
        "validation_results": {"independent_tests": {"failure_receipt": {
            "command": COMMAND, "exit_code": 1, "failing_lines": [TURN_3_TEXT],
        }}},
    }
    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    orchestrator._merge_evidence_test_signal_into_report(report, bundle)

    text = orchestrator._turn_feedback_text(report, 4)
    assert TURN_4_DNS_LINE in text
    assert TURN_3_TEXT not in text


def test_the_stall_tally_still_compares_only_the_reviewers_words() -> None:
    """The summary names the turn; the feedback-stall signature ignores it."""
    orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    coach_text = f"- MUST FIX: {TURN_3_ISSUE}"
    receipt = _turn_4_run().failure_receipt()
    turn_3 = f"{describe_independent_suite_failure(3, receipt)}\n\n{coach_text}"
    turn_4 = f"{describe_independent_suite_failure(4, receipt)}\n\n{coach_text}"

    assert without_independent_suite_failure(turn_4) == coach_text
    assert orchestrator._normalize_feedback_for_stall(turn_3) == (
        orchestrator._normalize_feedback_for_stall(turn_4)
    )


def test_failing_lines_are_picked_by_ordinary_words_and_bounded() -> None:
    assert first_failing_lines(TURN_4_OUTPUT) == [
        TURN_4_DNS_LINE,
        "FAILED tests/acceptance/users_roundtrip.py::test_users_roundtrip_smoke",
        "1 failed, 884 passed in 211.40s",
    ]
    noisy = "\n".join(f"error {i}" for i in range(50))
    assert len(first_failing_lines(noisy)) == INDEPENDENT_FAILURE_LINES_SHOWN
    # Output with no failure word: its last lines stand in.
    quiet = "\n".join(f"step {i}" for i in range(20))
    assert first_failing_lines(quiet)[-1] == "step 19"
    assert first_failing_lines("") == []


def test_an_agent_shell_run_says_its_exit_status_was_not_recorded() -> None:
    receipt = {"command": COMMAND, "exit_code": None, "failing_lines": ["boom"]}
    text = describe_independent_suite_failure(4, receipt)
    assert "Exit status: not recorded" in text
    assert not any(line.startswith("- ") for line in text.splitlines())
