"""The plan audit in a gate-driven repair round (20 October 2026).

A gate that runs after a wave can re-open an approved task with the gate's
output as feedback. To make the gate pass the Player may have to make files
the task document never named, and no rule about how many files, or which
folder, can tell those from unrelated work. So in a repair round, and only
there, handed to the audit IN MEMORY by the orchestrator that re-opened the
task:

* a non-protected extra file the round made does not count towards "three is
  high"; it is named for the reviewer, whose prompt says it is a repair round
  and asks it to refuse any file not needed to make the failing check pass;
* a protected extra file the round made is high, always;
* extra files an earlier, approved round made count as they did then.

Ordinary turns are unchanged. The Coach's "Coverage is UNKNOWN" issue, when it
only waits on another gate, is ordered after that gate, and the stall summary
quotes the gate that refused the last turn.

The audit cases drive the normal caller (``AgentInvoker._compute_plan_audit_verdict``)
over real git repositories, and the gate (``CoachValidator.verify_quality_gates``).
Every file name and content is invented.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from guardkit.models.task_types import TaskType, get_profile
from guardkit.orchestrator.agent_invoker import AgentInvocationResult, AgentInvoker
from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    TurnRecord,
    _coach_headline_issue,
    _feedback_issue_is_must_fix,
    _stall_refusal_line,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    QualityGateStatus,
)
from guardkit.orchestrator.repair_round import (
    RepairRound,
    begin_repair_round,
    implicated_paths,
)
from installer.core.commands.lib.plan_audit import _repair_round_split

TASK_ID = "TASK-SHELF-001"
PLANNED_CREATE = ["web/src/ShelfPage.tsx", "web/src/ShelfCard.tsx"]
PLANNED_MODIFY = ["web/src/App.tsx"]

GATE_OUTPUT = (
    "Check command:\nbash scripts/check-feature.sh\n\n"
    "stdout (last 40 lines):\n"
    "  Error: expected the list not to contain 'Seeded sample book'\n"
    "    at /elsewhere/checkout/tests/e2e/shelf.spec.ts:41:7\n"
    "  [chromium] › tests/e2e/shelf.spec.ts:30:1 › sign in\n"
    "  attachment: .runs/abc/test-failed-1.png\n"
)


# ---------------------------------------------------------------------------
# 1. Which files the gate's output names
# ---------------------------------------------------------------------------

TRACKED = [
    "scripts/check-feature.sh",
    "tests/e2e/shelf.spec.ts",
    "tests/e2e/login.spec.ts",
    "web/src/App.tsx",
    "README.md",
    "docs/README.md",
]


class TestImplicatedPaths:
    def test_an_absolute_path_from_another_checkout_with_line_numbers(self) -> None:
        text = "    at /some/where/else/FEAT-X/tests/e2e/shelf.spec.ts:124:26"
        assert implicated_paths(text, TRACKED) == ["tests/e2e/shelf.spec.ts"]

    def test_the_longest_tracked_suffix_wins(self) -> None:
        tracked = ["web/src/util/format.ts", "src/util/format.ts", "util/format.ts"]
        text = "    at /checkout/elsewhere/web/src/util/format.ts:3:9"
        assert implicated_paths(text, tracked) == ["web/src/util/format.ts"]

    def test_a_runner_line_and_the_check_command(self) -> None:
        assert implicated_paths(GATE_OUTPUT, TRACKED) == [
            "scripts/check-feature.sh",
            "tests/e2e/shelf.spec.ts",
        ]

    def test_a_bare_name_counts_only_when_it_means_one_file(self) -> None:
        assert implicated_paths("see login.spec.ts", TRACKED) == [
            "tests/e2e/login.spec.ts"
        ]
        assert implicated_paths("see README.md.", TRACKED) == []

    def test_untracked_or_generated_paths_and_plain_words_name_nothing(self) -> None:
        text = ".runs/abc/test-failed-1.png Error: exit=1 expected=0 v1.2"
        assert implicated_paths(text, TRACKED) == []
        assert implicated_paths("", TRACKED) == []


# ---------------------------------------------------------------------------
# 2. The decision itself
# ---------------------------------------------------------------------------

class TestTheSplit:
    def test_each_kind_of_file(self) -> None:
        counted, approved, protected, for_reviewer = _repair_round_split(
            {
                "web/src/format.ts",          # made by the ordinary approved round
                "db/migrations/0001_x.sql",   # made by the approved round, protected
                "tests/e2e/helpers.ts",       # made by an earlier, approved repair round
                "scripts/seed-owner.sh",      # made by this round
                "api/billing/invoice.ts",     # made by this round
                "scripts/Dockerfile",         # made by this round, protected
                "tests/e2e/.env.test",        # made by this round, protected
            },
            existed_at_round_start={
                "web/src/format.ts", "db/migrations/0001_x.sql", "tests/e2e/helpers.ts",
            },
            approved_by_repairs={"tests/e2e/helpers.ts", "db/migrations/0001_x.sql"},
        )
        # The ordinary round's files count as they did when it was approved.
        assert counted == {"web/src/format.ts", "db/migrations/0001_x.sql"}
        assert approved == {"tests/e2e/helpers.ts"}
        assert protected == {"scripts/Dockerfile", "tests/e2e/.env.test"}
        assert for_reviewer == {"scripts/seed-owner.sh", "api/billing/invoice.ts"}


# ---------------------------------------------------------------------------
# 3. The audit, through its normal caller, on real repositories
# ---------------------------------------------------------------------------


def _git(root: Path, *args: str) -> str:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True, env=env
    ).stdout.strip()


def _write(root: Path, rel: str, text: str = "// invented\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _checkpoint(root: Path, *commits: str) -> None:
    path = root / ".guardkit" / "autobuild" / TASK_ID / "checkpoints.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "task_id": TASK_ID,
        "checkpoints": [
            {"turn": n, "commit_hash": c} for n, c in enumerate(commits, start=1)
        ],
    }))


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _make_repo(tmp_path)


def _make_repo(tmp_path: Path, declare_modify: bool = True) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "autobuild/FEAT-SHELF")
    _git(root, "config", "user.email", "factory@example.invalid")
    _git(root, "config", "user.name", "Factory Test")
    _git(root, "config", "commit.gpgsign", "false")
    _write(root, ".gitignore", ".guardkit/autobuild-private/\n")
    _write(root, "web/src/App.tsx", "export const App = () => null;\n")
    _write(root, "api/src/server.ts", "export const serve = 1;\n")
    _write(root, "scripts/check-feature.sh", "#!/bin/sh\nexit 0\n")
    _write(root, "scripts/seed.sh", "#!/bin/sh\necho seed\n")
    _write(root, "tests/e2e/shelf.spec.ts", "test('shelf', () => {});\n")
    _write(
        root,
        f"tasks/in_progress/{TASK_ID}.md",
        "---\n"
        f"id: {TASK_ID}\ntitle: Build the shelf page\nstatus: in_progress\n"
        "---\n\n## Files to Create\n\n"
        + "".join(f"- `{p}`\n" for p in PLANNED_CREATE)
        + (
            "\n## Files to Modify\n\n" + "".join(f"- `{p}`\n" for p in PLANNED_MODIFY)
            if declare_modify
            else ""
        )
        + "\n## Acceptance Criteria\n\n- [ ] The shelf page lists books.\n",
    )
    _commit(root, "base")
    return root


def _approve_round_one(root: Path, extra: Optional[Dict[str, str]] = None) -> str:
    """Round 1's work, committed as its checkpoint; returns that commit."""
    for path in PLANNED_CREATE:
        _write(root, path)
    _write(root, "web/src/App.tsx", "export const App = () => 'shelf';\n")
    for path, text in (extra or {}).items():
        _write(root, path, text)
    commit = _commit(root, "turn 1 checkpoint")
    _checkpoint(root, commit)
    return commit


def _reopen(root: Path) -> RepairRound:
    """What the re-open hands the task's orchestrator: the round, in memory."""
    round_ = begin_repair_round(root, 2, GATE_OUTPUT)
    assert round_ is not None
    return round_


def _verdict(root: Path, repair_round: Optional[RepairRound] = None) -> Dict[str, Any]:
    invoker = AgentInvoker(worktree_path=root, max_turns_per_agent=1, sdk_timeout_seconds=10)
    invoker.repair_round = repair_round
    return invoker._compute_plan_audit_verdict(TASK_ID)


def _gate_passes(root: Path, plan_audit: Dict[str, Any]) -> bool:
    validator = CoachValidator(str(root), task_id=TASK_ID)
    gates = validator.verify_quality_gates(
        {
            "task_id": TASK_ID,
            "quality_gates": {"all_passed": True, "tests_failed": 0, "coverage_met": True},
            "code_review": {"score": 95},
            "plan_audit": plan_audit,
        },
        profile=get_profile(TaskType.FEATURE),
    )
    return bool(gates.plan_audit_passed)


NEAR_THE_FAILURE = {
    "tests/e2e/shelf.spec.ts": "test('only my books', () => {});\n",
    "tests/e2e/sign-in.ts": "export const signIn = 1;\n",
    "scripts/seed-owner.sh": "#!/bin/sh\necho owner\n",
    "scripts/seed-sample-book.sh": "#!/bin/sh\necho book\n",
    "scripts/seed.sh": "#!/bin/sh\nbash scripts/seed-owner.sh\n",
    "web/src/test-render.tsx": "export const render = 1;\n",
}


def _write_all(root: Path, files: Dict[str, str]) -> None:
    for path, text in files.items():
        _write(root, path, text)


class TestTheAuditInARepairRound:
    def test_the_round_starts_at_head_at_the_re_open(self, repo: Path) -> None:
        start = _approve_round_one(repo)
        round_ = _reopen(repo)
        assert round_ == RepairRound(round_number=2, start_commit=start, gate_output=GATE_OUTPUT)

    def test_extra_files_are_left_to_the_reviewer_and_all_named(self, repo: Path) -> None:
        _approve_round_one(repo)
        round_ = _reopen(repo)
        _write_all(repo, NEAR_THE_FAILURE)

        verdict = _verdict(repo, round_)

        assert verdict["status"] == "passed", verdict
        assert verdict["severity"] == "low"
        assert verdict["violations"] == 0
        made = [
            "scripts/seed-owner.sh",
            "scripts/seed-sample-book.sh",
            "tests/e2e/sign-in.ts",
            "web/src/test-render.tsx",
        ]
        assert verdict["extra_files"] == made
        assert verdict["extra_files_for_the_reviewer"] == made
        assert verdict["extra_modifications"] == ["scripts/seed.sh", "tests/e2e/shelf.spec.ts"]
        assert verdict["repair_round"] == {
            "round_number": 2,
            "start_commit": round_.start_commit,
            "files_the_gate_names": ["scripts/check-feature.sh", "tests/e2e/shelf.spec.ts"],
            "files_made_this_round": made,
            "files_changed_this_round": ["scripts/seed.sh", "tests/e2e/shelf.spec.ts"],
        }
        assert _gate_passes(repo, verdict)

    def test_the_same_tree_on_an_ordinary_turn_is_high(self, repo: Path) -> None:
        _approve_round_one(repo)
        _write_all(repo, NEAR_THE_FAILURE)

        verdict = _verdict(repo)

        assert verdict["status"] == "violation"
        assert verdict["severity"] == "high"
        assert verdict["extra_files_for_the_reviewer"] == []
        assert "repair_round" not in verdict
        assert not _gate_passes(repo, verdict)

    def test_a_protected_file_the_round_made_is_refused(self, repo: Path) -> None:
        _approve_round_one(repo)
        round_ = _reopen(repo)
        _write(repo, "tests/e2e/sign-in.ts", "export const s = 1;\n")
        _write(repo, "db/migrations/0003_seed.sql", "insert into items values (1);\n")

        verdict = _verdict(repo, round_)

        assert verdict["status"] == "violation"
        assert verdict["severity"] == "high"
        assert verdict["extra_files_for_the_reviewer"] == ["tests/e2e/sign-in.ts"]
        assert "db/migrations/0003_seed.sql" in verdict["extra_files"]
        assert not _gate_passes(repo, verdict)

    def test_files_an_earlier_round_made_count_as_they_did(self, repo: Path) -> None:
        # Round 1 was approved with two extra files, one protected (medium).
        _approve_round_one(
            repo,
            extra={
                "db/migrations/0002_items.sql": "create table items (id int);\n",
                "web/src/extra.ts": "export const extra = 1;\n",
            },
        )
        round_ = _reopen(repo)
        _write(repo, "api/src/a.ts", "export const a = 1;\n")

        verdict = _verdict(repo, round_)

        assert verdict["severity"] == "medium"  # as round 1 was approved
        assert verdict["extra_files_for_the_reviewer"] == ["api/src/a.ts"]
        assert _gate_passes(repo, verdict)

    def test_a_round_whose_start_was_rolled_back_is_audited_as_ordinary(self, repo: Path) -> None:
        first = _approve_round_one(repo)
        _write(repo, "web/src/ShelfCard.tsx", "export const ShelfCard = () => 1;\n")
        second = _commit(repo, "turn 2 checkpoint")
        _checkpoint(repo, first, second)
        round_ = _reopen(repo)
        assert round_.start_commit == second
        _git(repo, "reset", "-q", "--hard", first)
        _checkpoint(repo, first)
        _write_all(repo, NEAR_THE_FAILURE)

        verdict = _verdict(repo, round_)

        assert verdict["severity"] == "high"
        assert "repair_round" not in verdict

    def test_a_round_from_before_the_task_is_audited_as_ordinary(self, repo: Path) -> None:
        round_ = _reopen(repo)  # HEAD before this task's first checkpoint
        _approve_round_one(repo)
        _write_all(repo, NEAR_THE_FAILURE)
        assert _verdict(repo, round_)["severity"] == "high"

    def test_a_file_on_disk_never_makes_a_turn_a_repair_round(self, repo: Path) -> None:
        """Nothing is read from disk: a forged record in the private folder,
        where the old design kept one, has no effect."""
        _approve_round_one(repo)
        private = TaskArtifactPaths.task_private_dir(TASK_ID, repo)
        (private / "round-1").mkdir(parents=True)
        (private / "repair_round.json").write_text(json.dumps({
            "task_id": TASK_ID, "round": 1,
            "start_commit": _git(repo, "rev-parse", "HEAD"),
            "implicated_paths": ["tests/e2e/shelf.spec.ts"],
        }))
        _write_all(repo, NEAR_THE_FAILURE)

        verdict = _verdict(repo)

        assert verdict["severity"] == "high"
        assert "repair_round" not in verdict

    def test_an_edit_the_task_document_does_not_name_reaches_the_inventory(
        self, tmp_path: Path
    ) -> None:
        """A task that declares only files to create says nothing about edits,
        so the ordinary audit lists none; the reviewer's inventory still has
        every file git says the round changed."""
        repo = _make_repo(tmp_path, declare_modify=False)
        for path in PLANNED_CREATE:
            _write(repo, path)
        _checkpoint(repo, _commit(repo, "turn 1 checkpoint"))
        round_ = _reopen(repo)
        _write(repo, "tests/e2e/sign-in.ts", "export const s = 1;\n")
        _write(repo, "api/src/server.ts", "export const serve = 2; // billing tweak\n")
        # A file the task document names is the task's own work: not listed.
        _write(repo, "web/src/ShelfPage.tsx", "export const ShelfPage = () => 2;\n")

        verdict = _verdict(repo, round_)

        assert verdict["extra_modifications"] == []  # the ordinary audit is silent
        assert verdict["repair_round"]["files_changed_this_round"] == ["api/src/server.ts"]
        assert verdict["repair_round"]["files_made_this_round"] == ["tests/e2e/sign-in.ts"]

    def test_a_later_re_entry_does_not_recount_what_a_repair_approved(
        self, repo: Path
    ) -> None:
        """Ordinary approval, a repair round approved with four new files, then
        another gate's re-entry: the four are not counted again."""
        _approve_round_one(repo)
        first_repair = _reopen(repo)
        _write_all(repo, NEAR_THE_FAILURE)
        assert _verdict(repo, first_repair)["status"] == "passed"
        _commit(repo, "repair round approved")

        second_repair = begin_repair_round(repo, 3, "Smoke check failed: tests/e2e/shelf.spec.ts", previous=first_repair)
        assert second_repair is not None
        assert {
            "scripts/seed-owner.sh", "scripts/seed-sample-book.sh",
            "tests/e2e/sign-in.ts", "web/src/test-render.tsx",
        } <= second_repair.approved_by_earlier_repairs
        _write(repo, "tests/e2e/shelf.spec.ts", "test('again', () => {});\n")

        verdict = _verdict(repo, second_repair)

        assert verdict["status"] == "passed", verdict
        assert verdict["extra_files_approved_by_a_repair"] == [
            "scripts/seed-owner.sh", "scripts/seed-sample-book.sh",
            "tests/e2e/sign-in.ts", "web/src/test-render.tsx",
        ]
        # Without the carried approvals the same re-entry would be high.
        assert _verdict(repo, begin_repair_round(repo, 3, "x"))["severity"] == "high"

    def test_starting_a_round_without_git_never_raises(self, tmp_path: Path) -> None:
        assert begin_repair_round(tmp_path / "no-repo", 2, GATE_OUTPUT) is None


# ---------------------------------------------------------------------------
# 4. What the Coach tells the Player, and what the reviewer is shown
# ---------------------------------------------------------------------------


def _feedback_issue(plan_audit: Dict[str, Any]) -> Dict[str, Any]:
    validator = CoachValidator("/nonexistent", task_id=TASK_ID)
    gates = QualityGateStatus(
        tests_passed=True,
        coverage_met=True,
        arch_review_passed=True,
        plan_audit_passed=False,
    )
    result = validator._feedback_from_gates(TASK_ID, 1, gates, {"plan_audit": plan_audit})
    return next(i for i in result.issues if i["category"] == "plan_audit")


class TestTheCoachMessage:
    def test_a_repair_round_names_only_the_protected_files(self) -> None:
        issue = _feedback_issue({
            "status": "violation",
            "severity": "high",
            "violations": 1,
            "extra_files": ["db/migrations/0003_seed.sql", "tests/e2e/sign-in.ts"],
            "extra_files_for_the_reviewer": ["tests/e2e/sign-in.ts"],
            "extra_files_beside_the_plan": [],
            "repair_round": {"round_number": 2, "start_commit": "abc"},
        })
        text = issue["description"]
        assert issue["severity"] == "must_fix"
        assert "1 extra file(s): db/migrations/0003_seed.sql" in text
        assert "sign-in.ts" not in text
        assert "this is a repair round" in text

    def test_an_ordinary_turn_reads_as_before(self) -> None:
        issue = _feedback_issue({
            "status": "violation",
            "severity": "high",
            "violations": 1,
            "extra_files": ["a/one.ts", "a/two.ts", "a/three.ts"],
            "extra_files_beside_the_plan": [],
        })
        assert issue["description"] == (
            "Plan audit detected high-severity discrepancies — 3 extra file(s): "
            "a/one.ts, a/two.ts, a/three.ts"
        )


class TestTheReviewersPrompt:
    def _section(self, repair_round: Optional[RepairRound]) -> str:
        invoker = AgentInvoker(worktree_path=Path("/nonexistent"))
        invoker.repair_round = repair_round
        bundle = SimpleNamespace(plan_audit={
            "repair_round": {
                "files_the_gate_names": ["tests/e2e/shelf.spec.ts"],
                "files_made_this_round": ["scripts/seed-owner.sh", "api/billing/invoice.ts"],
                "files_changed_this_round": ["tests/e2e/shelf.spec.ts"],
            },
        })
        return invoker._render_repair_round_section(bundle)

    def test_a_repair_round_asks_the_reviewer_to_judge_every_file(self) -> None:
        text = self._section(RepairRound(2, "abc", GATE_OUTPUT))
        assert "## This is a repair round (round 2)" in text
        assert "refuse the turn (feedback, must_fix) and name the file" in text
        assert "- `scripts/seed-owner.sh`" in text
        assert "- `api/billing/invoice.ts`" in text
        assert "- `tests/e2e/shelf.spec.ts` (the failing check's output names it)" in text
        assert "bash scripts/check-feature.sh" in text  # the gate's own words

    def test_an_ordinary_turn_has_no_such_section(self) -> None:
        assert self._section(None) == ""


# ---------------------------------------------------------------------------
# 5. The gate that refused the turn is the one quoted
# ---------------------------------------------------------------------------

COVERAGE_WAITING = {
    "severity": "must_fix",
    "category": "coverage_unknown",
    "description": (
        "Coverage is UNKNOWN, not met: coverage is required for feature tasks. "
        "The project declares a coverage command (toolchain.coverage: bash "
        "scripts/coverage.sh), but it was not run this turn because the plan "
        "audit gate(s) failed first."
    ),
    "details": {"waiting_on_gates": ["plan audit"]},
}
COVERAGE_UNMEASURED = {
    "severity": "must_fix",
    "category": "coverage_unknown",
    "description": "Coverage is UNKNOWN, not met: nothing measured coverage.",
    "details": {"waiting_on_gates": []},
}
PLAN_AUDIT = {
    "severity": "must_fix",
    "category": "plan_audit",
    "description": "Plan audit detected high-severity discrepancies — 3 extra file(s): a, b, c",
    "details": {"severity": "high"},
}
ADVISORY = {
    "severity": "warning",
    "category": "agent_invocations_advisory",
    "description": "Advisory (non-blocking): missing phases.",
}


def _turn(turn: int, issues: List[Dict[str, Any]]) -> TurnRecord:
    coach = AgentInvocationResult(
        task_id=TASK_ID, turn=turn, agent_type="coach", success=True,
        report={"decision": "feedback", "issues": issues}, duration_seconds=1.0,
    )
    player = AgentInvocationResult(
        task_id=TASK_ID, turn=turn, agent_type="player", success=True,
        report={"files_modified": ["a"], "files_created": []}, duration_seconds=1.0,
    )
    return TurnRecord(
        turn=turn, player_result=player, coach_result=coach, decision="feedback",
        feedback="same feedback", timestamp="2026-10-20T00:00:00Z",
        files_changed_this_turn=2,
    )


def _orchestrator(tmp_path: Path) -> AutoBuildOrchestrator:
    return AutoBuildOrchestrator(
        repo_root=tmp_path,
        max_turns=4,
        enable_pre_loop=False,
        enable_context=False,
        agent_invoker=MagicMock(),
        worktree_manager=SimpleNamespace(worktrees_dir=tmp_path),
    )


class TestTheBlockingGateIsQuoted:
    def test_the_plan_audit_is_the_headline_not_the_coverage_waiting_on_it(self) -> None:
        record = _turn(4, [ADVISORY, COVERAGE_WAITING, PLAN_AUDIT])
        assert _coach_headline_issue(record) == (PLAN_AUDIT["description"], True)

    def test_coverage_waiting_is_still_a_reason_the_turn_was_refused(self) -> None:
        assert _feedback_issue_is_must_fix(COVERAGE_WAITING)

    def test_unmeasured_coverage_keeps_its_place(self) -> None:
        record = _turn(4, [COVERAGE_UNMEASURED, PLAN_AUDIT])
        assert _coach_headline_issue(record)[0] == COVERAGE_UNMEASURED["description"]

    def test_the_turn_summary_and_the_players_feedback_lead_with_the_plan_audit(
        self, tmp_path: Path
    ) -> None:
        orch = _orchestrator(tmp_path)
        report = {"issues": [ADVISORY, COVERAGE_WAITING, PLAN_AUDIT]}
        assert orch._build_feedback_summary(report, "").startswith(
            "Feedback: Plan audit detected"
        )
        feedback = orch._extract_feedback(report)
        assert feedback.index("Plan audit detected") < feedback.index("Coverage is UNKNOWN")

    def test_the_stall_summary_and_error_quote_the_plan_audit(self, tmp_path: Path) -> None:
        orch = _orchestrator(tmp_path)
        history = [_turn(n, [ADVISORY, COVERAGE_WAITING, PLAN_AUDIT]) for n in (2, 3, 4)]
        summary = orch._build_summary_details(history, "unrecoverable_stall")
        error = orch._build_error_message("unrecoverable_stall", history)
        expected = f'The reviewer refused turn 4 for this: "{PLAN_AUDIT["description"]}"'
        assert expected in summary, summary
        assert expected in error, error
        assert "Coverage is UNKNOWN" not in summary

    def test_no_readable_issue_adds_nothing(self) -> None:
        assert _stall_refusal_line([]) == ""
        assert _stall_refusal_line([_turn(1, [])]) == ""
