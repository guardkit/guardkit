"""Tests for the third outcome: a task the tree already satisfies is CLOSED.

The build of 2026-09-11 (``build-FEAT-3EF3-20260911171802``) is the reason
this exists. Its plan split one job into three tasks. Task one did the whole
job in a single turn — the route, the query, the schema and a test file, 826
tests green. Tasks two and three, "add the statistics schema" and "implement
the statistics query", then had nothing left to do: you cannot make an
endpoint return seven ordered entries without the query that produces them and
the schema that shapes them.

The loop had no way to say "already done". It saw no file changes, read that
as no progress, and spent five turns on each of those two tasks. On the fifth
turn one of them deleted ``count_users_today`` and ``count_users_by_domain``
from a module its task never mentioned — 79 tests of shipped behaviour. "The
work is already there" and "no progress is being made" look identical from
outside, and only one of them is a failure.

What is covered here
--------------------
1. A task whose acceptance criteria the tree already satisfies — claimed by
   the builder with citations, verified by the reviewer — closes on turn ONE
   as ``already_satisfied`` and counts as a COMPLETE task.
2. A claim that cites nothing is refused, in a sentence a person can read.
3. A claim the reviewer cannot verify is refused, and the turn carries on
   exactly as it does today.
4. A task with real work outstanding is untouched, stall rule included.
5. The outcome reads correctly everywhere it surfaces: the run summary, the
   final status, and the completed count.
6. None of it knows what language the repository is written in.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

from guardkit.orchestrator.agent_invoker import (
    ALREADY_SATISFIED_FIELD,
    ALREADY_SATISFIED_PROMPT_SECTION,
    AgentInvocationResult,
    AgentInvoker,
)
from guardkit.orchestrator.autobuild import (
    DECISION_ALREADY_SATISFIED,
    STALL_CLASSIFICATION_THRESHOLD,
    TASK_COMPLETE_DECISIONS,
    AutoBuildOrchestrator,
    OrchestrationResult,
    TurnRecord,
    _already_satisfied_citations,
    _already_satisfied_claim,
    _already_satisfied_refusal,
    finalize_autobuild,
)
from guardkit.orchestrator.exceptions import TaskWorkResult

AUTOBUILD_LOGGER = "guardkit.orchestrator.autobuild"

#: The three acceptance criteria of the task this lane is named after.
STATS_CRITERIA = [
    "AC-001: the statistics schema shapes the response",
    "AC-002: the statistics query returns seven ordered entries",
    "AC-003: the endpoint answers with the shaped result",
]


# ---------------------------------------------------------------------------
# Builders: the builder's report, the reviewer's report, a turn
# ---------------------------------------------------------------------------


def _citation(criterion: str, file: str, location: str) -> Dict[str, str]:
    return {
        "criterion_id": criterion,
        "file": file,
        "location": location,
        "evidence": f"{file} already satisfies {criterion}.",
    }


#: The citations a builder would write in a Python repository...
PYTHON_CITATIONS = [
    _citation("AC-001", "src/users/schemas.py", "UsersPerDay, lines 41-48"),
    _citation("AC-002", "src/users/crud.py", "count_users_per_day, lines 88-112"),
    _citation("AC-003", "src/users/router.py", "the /stats route, lines 210-236"),
]

#: ...and the same claim in a TypeScript repository...
TYPESCRIPT_CITATIONS = [
    _citation("AC-001", "src/users/schemas.ts", "the UsersPerDay interface"),
    _citation("AC-002", "src/users/repository.ts", "countUsersPerDay"),
    _citation("AC-003", "src/users/router.ts", "the GET /stats handler"),
]

#: ...and in a Go one. Nothing in this lane can tell them apart.
GO_CITATIONS = [
    _citation("AC-001", "internal/users/schema.go", "type UsersPerDay"),
    _citation("AC-002", "internal/users/store.go", "func CountUsersPerDay"),
    _citation("AC-003", "internal/users/router.go", "the /stats handler"),
]


def _builder_claiming_already_done(
    turn: int = 1,
    citations: Optional[List[Dict[str, str]]] = None,
    task_id: str = "TASK-STAT-002",
    files_modified: Optional[List[str]] = None,
) -> AgentInvocationResult:
    """A builder report that says "this is already here", and cites where."""
    claim: Dict[str, Any] = {"claimed": True}
    if citations is not None:
        claim["citations"] = citations
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=True,
        report={
            "files_modified": files_modified or [],
            "files_created": [],
            "tests_passed": True,
            "test_count": 826,
            "implementation_notes": (
                "Task one already wrote the schema and the query; nothing "
                "was left to do here."
            ),
            ALREADY_SATISFIED_FIELD: claim,
        },
        duration_seconds=22.0,
        error=None,
    )


def _builder_with_no_claim(
    turn: int = 1, task_id: str = "TASK-STAT-002"
) -> AgentInvocationResult:
    """Today's builder report: no claim of any kind."""
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="player",
        success=True,
        report={
            "files_modified": [],
            "files_created": [],
            "tests_passed": True,
            "test_count": 826,
        },
        duration_seconds=22.0,
        error=None,
    )


def _verified(*criteria: str) -> List[Dict[str, str]]:
    return [
        {
            "criterion_id": criterion.split(":")[0],
            "criterion_text": criterion,
            "result": "verified",
            "status": "verified",
            "evidence": "read the file named in the citation",
        }
        for criterion in criteria
    ]


def _reviewer(
    turn: int = 1,
    decision: str = "approve",
    criteria_verification: Optional[List[Dict[str, str]]] = None,
    issues: Optional[List[Dict[str, Any]]] = None,
    task_id: str = "TASK-STAT-002",
) -> AgentInvocationResult:
    report: Dict[str, Any] = {
        "decision": decision,
        "feedback": "" if decision == "approve" else "Not yet.",
        "issues": issues or [],
    }
    if criteria_verification is not None:
        report["criteria_verification"] = criteria_verification
    return AgentInvocationResult(
        task_id=task_id,
        turn=turn,
        agent_type="coach",
        success=True,
        report=report,
        duration_seconds=31.0,
        error=None,
    )


def _turn(
    turn: int = 1,
    player: Optional[AgentInvocationResult] = None,
    coach: Optional[AgentInvocationResult] = None,
    decision: str = "approve",
    files_changed: Optional[int] = 0,
) -> TurnRecord:
    coach = coach if coach is not None else _reviewer(
        turn, decision, _verified(*STATS_CRITERIA)
    )
    return TurnRecord(
        turn=turn,
        player_result=player if player is not None
        else _builder_claiming_already_done(turn, PYTHON_CITATIONS),
        coach_result=coach,
        decision=decision,
        feedback=coach.report.get("feedback") or None,
        timestamp=f"2026-09-11T17:0{turn}:00Z",
        files_changed_this_turn=files_changed,
    )


class _FakeWorktreeManager:
    """Just enough of the manager for the loop and the finalize phase."""

    def __init__(self, worktrees_dir: Path) -> None:
        self.worktrees_dir = worktrees_dir
        self.preserved: List[Any] = []

    def preserve_on_failure(self, worktree: Any) -> None:
        self.preserved.append(worktree)


def _orchestrator(tmp_path: Path, max_turns: int = 5) -> AutoBuildOrchestrator:
    worktrees_dir = tmp_path / ".guardkit" / "worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    return AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=max_turns,
        worktree_manager=_FakeWorktreeManager(worktrees_dir),
        enable_pre_loop=False,
        enable_context=False,
        enable_checkpoints=False,
    )


def _drive(
    orchestrator: AutoBuildOrchestrator,
    turns: List[TurnRecord],
    task_id: str = "TASK-STAT-002",
    acceptance_criteria: Optional[List[str]] = None,
) -> OrchestrationResult:
    """Run the REAL loop and finalize phases over a scripted set of turns.

    Only the two things this lane is not about are stood in for: creating a
    git worktree, and calling out to the two agents. Everything the lane
    changed — the turn decision, the stall rule, the final decision, the
    summary and the completed flag — is the real code.
    """
    worktree = SimpleNamespace(
        task_id=task_id,
        path=orchestrator.repo_root / "worktree",
        branch=f"autobuild/{task_id}",
    )
    calls: List[int] = []

    def _fake_turn(*_args: Any, **kwargs: Any) -> TurnRecord:
        index = len(calls)
        calls.append(kwargs.get("turn", index + 1))
        if index < len(turns):
            return turns[index]
        return turns[-1]

    with patch.object(orchestrator, "_setup_phase", return_value=worktree), \
         patch.object(orchestrator, "_execute_turn", side_effect=_fake_turn):
        result = orchestrator.orchestrate(
            task_id=task_id,
            requirements="Implement the statistics query",
            acceptance_criteria=(
                STATS_CRITERIA if acceptance_criteria is None
                else acceptance_criteria
            ),
        )
    result.turns_attempted = len(calls)  # type: ignore[attr-defined]
    return result


# ---------------------------------------------------------------------------
# 1. The task the tree already satisfies closes on turn one
# ---------------------------------------------------------------------------


class TestItClosesOnTurnOne:
    def test_a_claimed_and_verified_task_closes_as_already_satisfied(
        self, tmp_path
    ):
        orchestrator = _orchestrator(tmp_path)
        result = _drive(orchestrator, [_turn(1)])

        assert result.final_decision == DECISION_ALREADY_SATISFIED
        assert result.total_turns == 1

    def test_it_costs_one_turn_not_five(self, tmp_path):
        """The whole point: today's five wasted turns become one."""
        orchestrator = _orchestrator(tmp_path, max_turns=5)
        result = _drive(
            orchestrator, [_turn(t) for t in (1, 2, 3, 4, 5)]
        )

        assert result.final_decision == DECISION_ALREADY_SATISFIED
        assert result.turns_attempted == 1

    def test_it_counts_as_a_completed_task(self, tmp_path):
        """``success`` is what the feature run counts. It must be True."""
        orchestrator = _orchestrator(tmp_path)
        result = _drive(orchestrator, [_turn(1)])

        assert result.success is True
        assert result.error is None

    def test_a_feature_of_approved_and_satisfied_tasks_is_complete(
        self, tmp_path
    ):
        """The count behind "status=failed, completed=1/5".

        The feature run counts ``sum(1 for r in results if r.success)`` and
        fails the feature when any task is not successful. An already-satisfied
        task has to be on the completed side of that line.
        """
        orchestrator = _orchestrator(tmp_path)
        satisfied = _drive(orchestrator, [_turn(1)])
        approved = _drive(
            _orchestrator(tmp_path / "second"),
            [_turn(1, player=_builder_with_no_claim(1), files_changed=4)],
            task_id="TASK-STAT-001",
        )

        results = [approved, satisfied]
        assert approved.final_decision == "approved"
        assert sum(1 for r in results if r.success) == 2
        assert sum(1 for r in results if not r.success) == 0

    def test_both_complete_outcomes_are_named_in_one_place(self):
        assert TASK_COMPLETE_DECISIONS == frozenset(
            {"approved", DECISION_ALREADY_SATISFIED}
        )

    def test_the_claim_is_read_from_the_builders_own_report(self):
        record = _turn(1)
        assert _already_satisfied_claim(record) is not None
        assert _already_satisfied_claim(
            _turn(1, player=_builder_with_no_claim(1))
        ) is None

    def test_a_withdrawn_claim_is_no_claim(self):
        player = _builder_claiming_already_done(1, PYTHON_CITATIONS)
        player.report[ALREADY_SATISFIED_FIELD]["claimed"] = False
        assert _already_satisfied_claim(_turn(1, player=player)) is None


# ---------------------------------------------------------------------------
# 2. A claim has to cite, and a claim nobody verified is worth nothing
# ---------------------------------------------------------------------------


class TestAClaimMustCite:
    def test_a_claim_that_cites_nothing_is_refused(self, tmp_path, caplog):
        orchestrator = _orchestrator(tmp_path, max_turns=3)
        turns = [
            _turn(
                t,
                player=_builder_claiming_already_done(t, citations=None),
                coach=_reviewer(t, "feedback", _verified(*STATS_CRITERIA)),
                decision="feedback",
            )
            for t in (1, 2, 3)
        ]
        with caplog.at_level(logging.WARNING, logger=AUTOBUILD_LOGGER):
            result = _drive(orchestrator, turns)

        assert result.final_decision != DECISION_ALREADY_SATISFIED
        assert result.success is False
        messages = " ".join(r.getMessage() for r in caplog.records)
        assert "cited nothing" in messages
        assert "the file and the place" in messages

    def test_a_citation_without_a_file_is_not_a_citation(self):
        claim = {"claimed": True, "citations": [
            {"criterion_id": "AC-001", "location": "lines 41-48"},
        ]}
        assert _already_satisfied_citations(claim) == []

    def test_a_citation_without_a_place_is_not_a_citation(self):
        claim = {"claimed": True, "citations": [
            {"criterion_id": "AC-001", "file": "src/users/schemas.py"},
        ]}
        assert _already_satisfied_citations(claim) == []

    def test_a_citation_without_a_criterion_is_not_a_citation(self):
        claim = {"claimed": True, "citations": [
            {"file": "src/users/schemas.py", "location": "lines 41-48"},
        ]}
        assert _already_satisfied_citations(claim) == []

    def test_citing_some_criteria_is_not_citing_every_one(self):
        record = _turn(
            1,
            player=_builder_claiming_already_done(1, PYTHON_CITATIONS[:2]),
        )
        refusal = _already_satisfied_refusal(record, STATS_CRITERIA)
        assert refusal is not None
        assert "2 of its 3 acceptance criteria" in refusal
        assert "every one" in refusal

    def test_empty_citations_list_is_refused_like_no_citations(self):
        record = _turn(1, player=_builder_claiming_already_done(1, []))
        refusal = _already_satisfied_refusal(record, STATS_CRITERIA)
        assert refusal is not None
        assert "cited nothing" in refusal


class TestTheReviewerHasToVerifyIt:
    def test_a_claim_the_reviewer_did_not_verify_is_refused(self, tmp_path):
        """The reviewer says one criterion is not met. The claim falls."""
        orchestrator = _orchestrator(tmp_path, max_turns=3)
        partly = _verified(*STATS_CRITERIA[:2]) + [
            {
                "criterion_id": "AC-003",
                "criterion_text": STATS_CRITERIA[2],
                "result": "rejected",
                "status": "rejected",
            }
        ]
        turns = [
            _turn(
                t,
                coach=_reviewer(t, "feedback", partly),
                decision="feedback",
            )
            for t in (1, 2, 3)
        ]
        result = _drive(orchestrator, turns)

        assert result.final_decision != DECISION_ALREADY_SATISFIED
        assert result.success is False

    def test_a_reviewer_that_said_nothing_about_the_criteria_is_not_a_pass(
        self,
    ):
        """Unknown is not a pass — the rule "tests: pass, count: 0" broke."""
        record = _turn(1, coach=_reviewer(1, "approve", None))
        refusal = _already_satisfied_refusal(record, STATS_CRITERIA)
        assert refusal is not None
        assert "did not confirm every acceptance criterion" in refusal

    def test_a_must_fix_objection_outranks_the_claim(self):
        record = _turn(
            1,
            coach=_reviewer(
                1,
                "feedback",
                _verified(*STATS_CRITERIA),
                issues=[{
                    "severity": "must_fix",
                    "category": "test_verification",
                    "description": "independent tests did not run at all",
                }],
            ),
            decision="feedback",
        )
        refusal = _already_satisfied_refusal(record, STATS_CRITERIA)
        assert refusal is not None
        assert "must be fixed" in refusal
        assert "independent tests did not run" in refusal

    def test_the_honesty_record_outranks_the_claim(self):
        """The builder named files git says it never touched."""
        record = _turn(
            1,
            coach=_reviewer(
                1,
                "feedback",
                _verified(*STATS_CRITERIA),
                issues=[{
                    "severity": "should_fix",
                    "category": "claim_audit",
                    "claim_type": "claim_audit_unmodified",
                    "description": "Player claimed src/users/crud.py.",
                }],
            ),
            decision="feedback",
        )
        refusal = _already_satisfied_refusal(record, STATS_CRITERIA)
        assert refusal is not None
        assert "did not actually change" in refusal

    def test_a_builder_that_wrote_files_is_doing_work_not_claiming(self):
        record = _turn(1, files_changed=3)
        refusal = _already_satisfied_refusal(record, STATS_CRITERIA)
        assert refusal is not None
        assert "changed 3 file(s)" in refusal

    def test_an_unmeasured_turn_cannot_close_a_task(self):
        record = _turn(1, files_changed=None)
        refusal = _already_satisfied_refusal(record, STATS_CRITERIA)
        assert refusal is not None
        assert "could not measure" in refusal

    def test_a_refused_claim_does_not_stop_the_loop(self, tmp_path):
        """"Refused" means the turn continues, exactly as it does today."""
        orchestrator = _orchestrator(tmp_path, max_turns=3)
        turns = [
            _turn(
                t,
                player=_builder_claiming_already_done(t, citations=None),
                coach=_reviewer(t, "feedback", _verified(*STATS_CRITERIA)),
                decision="feedback",
            )
            for t in (1, 2, 3)
        ]
        result = _drive(orchestrator, turns)

        assert result.turns_attempted == STALL_CLASSIFICATION_THRESHOLD
        assert result.final_decision == "unrecoverable_stall"

    def test_the_refusal_is_told_back_to_the_builder(self, tmp_path):
        """The next turn is given the plain sentence, so it can stop."""
        orchestrator = _orchestrator(tmp_path, max_turns=3)
        turns = [
            _turn(
                t,
                player=_builder_claiming_already_done(t, citations=None),
                coach=_reviewer(t, "feedback", _verified(*STATS_CRITERIA)),
                decision="feedback",
            )
            for t in (1, 2)
        ]
        seen: List[Optional[str]] = []

        worktree = SimpleNamespace(
            task_id="TASK-STAT-002",
            path=orchestrator.repo_root / "worktree",
            branch="autobuild/TASK-STAT-002",
        )

        def _fake_turn(*_args: Any, **kwargs: Any) -> TurnRecord:
            seen.append(kwargs.get("previous_feedback"))
            return turns[min(len(seen) - 1, len(turns) - 1)]

        with patch.object(orchestrator, "_setup_phase", return_value=worktree), \
             patch.object(orchestrator, "_execute_turn", side_effect=_fake_turn):
            orchestrator.orchestrate(
                task_id="TASK-STAT-002",
                requirements="Implement the statistics query",
                acceptance_criteria=STATS_CRITERIA,
            )

        assert seen[0] is None
        assert seen[1] is not None
        assert "cited nothing" in seen[1]


# ---------------------------------------------------------------------------
# 3. A task with real work outstanding behaves exactly as it does today
# ---------------------------------------------------------------------------


class TestRealWorkIsUntouched:
    def test_no_claim_and_no_progress_still_stalls_after_the_usual_turns(
        self, tmp_path
    ):
        orchestrator = _orchestrator(tmp_path, max_turns=8)
        turns = [
            _turn(
                t,
                player=_builder_with_no_claim(t),
                coach=_reviewer(t, "feedback", None, issues=[{
                    "severity": "must_fix",
                    "category": "missing_requirement",
                    "description": "AC-002 is not met: add the query.",
                }]),
                decision="feedback",
            )
            for t in range(1, 9)
        ]
        result = _drive(orchestrator, turns)

        assert result.final_decision == "unrecoverable_stall"
        assert result.success is False
        assert result.turns_attempted == STALL_CLASSIFICATION_THRESHOLD

    def test_a_normal_build_that_writes_code_still_ends_approved(
        self, tmp_path
    ):
        orchestrator = _orchestrator(tmp_path, max_turns=5)
        turns = [
            _turn(
                1,
                player=_builder_with_no_claim(1),
                coach=_reviewer(1, "feedback", None, issues=[{
                    "severity": "must_fix",
                    "category": "missing_requirement",
                    "description": "AC-002 is not met.",
                }]),
                decision="feedback",
                files_changed=6,
            ),
            _turn(
                2,
                player=_builder_with_no_claim(2),
                coach=_reviewer(2, "approve", _verified(*STATS_CRITERIA)),
                decision="approve",
                files_changed=2,
            ),
        ]
        result = _drive(orchestrator, turns)

        assert result.final_decision == "approved"
        assert result.success is True


# ---------------------------------------------------------------------------
# 4. How it reads: the summary, the final status, the next steps
# ---------------------------------------------------------------------------


class TestHowItReads:
    def test_the_summary_says_what_happened_in_plain_words(self, tmp_path):
        orchestrator = _orchestrator(tmp_path)
        details = orchestrator._build_summary_details(
            [_turn(1)], DECISION_ALREADY_SATISFIED
        )

        assert "already satisfied" in details
        assert "nothing was written" in details.lower()
        assert "COMPLETE" in details

    def test_the_summary_names_where_the_work_already_is(self, tmp_path):
        orchestrator = _orchestrator(tmp_path)
        details = orchestrator._build_summary_details(
            [_turn(1)], DECISION_ALREADY_SATISFIED
        )

        assert "src/users/crud.py" in details
        assert "count_users_per_day, lines 88-112" in details

    def test_the_summary_survives_an_empty_history(self, tmp_path):
        orchestrator = _orchestrator(tmp_path)
        details = orchestrator._build_summary_details(
            [], DECISION_ALREADY_SATISFIED
        )
        assert "COMPLETE" in details

    def test_the_final_status_is_finished_not_blocked(self, tmp_path):
        result = OrchestrationResult(
            task_id="TASK-STAT-002",
            success=True,
            total_turns=1,
            final_decision=DECISION_ALREADY_SATISFIED,
            turn_history=[_turn(1)],
            worktree=SimpleNamespace(path=tmp_path),
        )
        finalized = finalize_autobuild(
            task_id="TASK-STAT-002",
            worktree_path=tmp_path,
            loop_result=result,
        )

        assert finalized["status"] == "in_review"
        joined = " ".join(finalized["next_steps"])
        assert "Nothing was written" in joined
        assert "nothing to merge" in joined

    def test_a_stalled_task_is_still_blocked(self, tmp_path):
        result = OrchestrationResult(
            task_id="TASK-STAT-002",
            success=False,
            total_turns=3,
            final_decision="unrecoverable_stall",
            turn_history=[],
            worktree=SimpleNamespace(path=tmp_path),
        )
        finalized = finalize_autobuild(
            task_id="TASK-STAT-002",
            worktree_path=tmp_path,
            loop_result=result,
        )
        assert finalized["status"] == "blocked"


# ---------------------------------------------------------------------------
# 5. Stack-agnostic: nothing here knows what language the repository is in
# ---------------------------------------------------------------------------


class TestItKnowsNoLanguage:
    @pytest.mark.parametrize(
        "citations",
        [PYTHON_CITATIONS, TYPESCRIPT_CITATIONS, GO_CITATIONS],
        ids=["python", "typescript", "go"],
    )
    def test_the_same_claim_closes_in_any_repository(
        self, tmp_path, citations
    ):
        orchestrator = _orchestrator(tmp_path)
        result = _drive(
            orchestrator,
            [_turn(1, player=_builder_claiming_already_done(1, citations))],
        )
        assert result.final_decision == DECISION_ALREADY_SATISFIED

    def test_a_place_can_be_a_name_rather_than_a_line_number(self):
        claim = {"claimed": True, "citations": [
            {
                "criterion_id": "AC-001",
                "file": "internal/users/store.go",
                "location": "func CountUsersPerDay",
            }
        ]}
        citations = _already_satisfied_citations(claim)
        assert citations == [{
            "criterion": "AC-001",
            "file": "internal/users/store.go",
            "place": "func CountUsersPerDay",
        }]

    def test_no_sentence_a_person_reads_names_a_language(self, tmp_path):
        """Refusals and the builder's instructions stay stack-agnostic."""
        forbidden = (
            "python", "pytest", "venv", "virtualenv", "pip", "npm",
            "node_modules", "yarn", "go.mod", "cargo", "gradle",
            "interpreter", ".py",
        )
        sentences = [ALREADY_SATISFIED_PROMPT_SECTION]
        for record, criteria in (
            (_turn(1, player=_builder_claiming_already_done(1, None)),
             STATS_CRITERIA),
            (_turn(1, player=_builder_claiming_already_done(
                1, PYTHON_CITATIONS[:1])), STATS_CRITERIA),
            (_turn(1, files_changed=3), STATS_CRITERIA),
            (_turn(1, files_changed=None), STATS_CRITERIA),
            (_turn(1, coach=_reviewer(1, "approve", None)), STATS_CRITERIA),
        ):
            refusal = _already_satisfied_refusal(record, criteria)
            assert refusal is not None
            sentences.append(refusal)

        for sentence in sentences:
            lowered = sentence.lower()
            for word in forbidden:
                assert word not in lowered, (word, sentence)


# ---------------------------------------------------------------------------
# 6. The builder is asked, on turn one, before it writes anything
# ---------------------------------------------------------------------------


class TestTheBuilderIsAskedFirst:
    def _invoker(self, tmp_path: Path) -> AgentInvoker:
        worktree = tmp_path / "worktree"
        worktree.mkdir(parents=True, exist_ok=True)
        return AgentInvoker(worktree_path=worktree)

    def test_turn_one_is_offered_the_third_outcome(self, tmp_path):
        invoker = self._invoker(tmp_path)
        prompt = invoker._build_player_prompt(
            task_id="TASK-STAT-002",
            turn=1,
            requirements="Implement the statistics query",
            feedback=None,
        )
        assert "Before you write anything" in prompt
        assert '"already_satisfied"' in prompt
        assert "Cite EVERY acceptance criterion" in prompt

    def test_later_turns_are_not(self, tmp_path):
        invoker = self._invoker(tmp_path)
        prompt = invoker._build_player_prompt(
            task_id="TASK-STAT-002",
            turn=2,
            requirements="Implement the statistics query",
            feedback="Not yet.",
        )
        assert "Before you write anything" not in prompt

    def test_the_delegated_path_asks_on_turn_one_too(self, tmp_path):
        invoker = self._invoker(tmp_path)
        first = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-STAT-002",
            turn=1,
            requirements="Implement the statistics query",
            max_turns=5,
        )
        later = invoker._build_autobuild_implementation_prompt(
            task_id="TASK-STAT-002",
            turn=2,
            requirements="Implement the statistics query",
            feedback="Not yet.",
            max_turns=5,
        )
        assert "Before you write anything" in first
        assert "Before you write anything" not in later


# ---------------------------------------------------------------------------
# 7. The claim survives the journey from the builder to the orchestrator
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(repo),
        },
    )


class TestTheClaimIsCarried:
    def test_the_delegated_report_keeps_the_builders_claim(self, tmp_path):
        """A real worktree, a real report file, the real report builder.

        The delegated path assembles the builder's report from the fields it
        knows about, so without this the claim would be written by the builder
        and thrown away before the orchestrator ever saw it.
        """
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        _git(worktree, "init", "-q")
        (worktree / "README.md").write_text("hello\n")
        _git(worktree, "add", "README.md")
        _git(worktree, "commit", "-qm", "first")

        report_dir = worktree / ".guardkit" / "autobuild" / "TASK-STAT-002"
        report_dir.mkdir(parents=True)
        (report_dir / "player_turn_1.json").write_text(json.dumps({
            "task_id": "TASK-STAT-002",
            "turn": 1,
            "files_modified": [],
            "files_created": [],
            "tests_written": [],
            "tests_run": False,
            "tests_passed": True,
            "test_output_summary": "",
            "implementation_notes": "already there",
            "concerns": [],
            "requirements_addressed": [],
            "requirements_remaining": [],
            ALREADY_SATISFIED_FIELD: {
                "claimed": True,
                "citations": PYTHON_CITATIONS,
            },
        }))

        invoker = AgentInvoker(worktree_path=worktree)
        invoker._create_player_report_from_task_work(
            "TASK-STAT-002",
            1,
            TaskWorkResult(success=True, output={}),
        )

        written = json.loads(
            (report_dir / "player_turn_1.json").read_text()
        )
        assert ALREADY_SATISFIED_FIELD in written
        assert written[ALREADY_SATISFIED_FIELD]["citations"] == (
            PYTHON_CITATIONS
        )
