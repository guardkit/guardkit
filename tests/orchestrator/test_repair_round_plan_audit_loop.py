"""A repair round can do its job; the reviewer refuses one that wanders.

What happened (19-20 October 2026)
----------------------------------
A feature's two tasks were approved; then the project's whole-feature check
failed and GuardKit re-opened the page task with the check's output as the
Player's feedback. To make the check pass the Player had to make files the
task document never named. The plan audit compared the whole task with the
task document, called every repair turn high, and the task stalled.

What this file drives, with no model called
-------------------------------------------
Round 1 runs through the real loop (``AutoBuildOrchestrator._loop_phase``)
and is approved, leaving real checkpoint commits. Then the REAL gate-driven
re-open in ``FeatureOrchestrator._execute_wave_parallel`` runs, with only
``_execute_task`` standing in: it hands the repair round it was given IN MEMORY
to a second real loop. On every turn the Player is a stand-in that writes
files and reports through the real ``AgentInvoker._write_task_work_results``
(so the real plan audit runs), and the Coach is the real primary path and the
real ``invoke_coach`` guards; only the model's answer is a stand-in. The prompt
the model would have read is captured. Every file name and content is invented.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult, AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.repair_round import RepairRound
from guardkit.worktrees import Worktree

TASK_ID = "TASK-RPR-001"
FEATURE_ID = "FEAT-RPR"
BRANCH = "autobuild/FEAT-RPR"
CRITERIA = ["The shelf page lists the reader's books."]

PLANNED_CREATE = ["apps/web/src/ShelfPage.tsx", "apps/web/src/ShelfCard.tsx"]
PLANNED_MODIFY = ["apps/web/src/App.tsx"]

GATE_OUTPUT = (
    "THE WHOLE-FEATURE CHECK FAILED.\n\n"
    "Check command:\nbash scripts/check-feature.sh\n\n"
    "Result: exit=1, expected=0\n\n"
    "stdout (last 40 lines):\n"
    "  Error: expect(list).not.toContainText('Seeded sample book')\n"
    "    at /some/other/checkout/tests/e2e/shelf.spec.ts:41:7\n"
    "  1 failed\n"
    "    [chromium] › tests/e2e/shelf.spec.ts:30:1 › sign in and see the shelf\n"
    "check-feature: FAIL exit=1\n"
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write(repo: Path, rel: str, text: str = "// invented\n") -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def make_project(
    tmp_path: Path,
    declare_modify: bool = True,
    declare_create: bool = True,
    direct_mode: bool = False,
) -> Path:
    """A small invented web project on its feature branch."""
    repo = tmp_path / "main" / ".guardkit" / "worktrees" / FEATURE_ID
    repo.mkdir(parents=True)
    _write(repo, "apps/web/src/App.tsx", "export const App = () => null;\n")
    _write(repo, "apps/api/src/server.ts", "export const serve = () => 1;\n")
    _write(repo, "scripts/check.sh", "#!/bin/sh\nexit 0\n")
    _write(repo, "scripts/check-feature.sh", "#!/bin/sh\nbash scripts/seed.sh\n")
    _write(repo, "scripts/seed.sh", "#!/bin/sh\necho seeded\n")
    _write(repo, "tests/e2e/shelf.spec.ts", "test('shelf', () => {});\n")
    _write(repo, "deploy/Dockerfile", "FROM scratch\n")
    _write(repo, ".gitignore", "node_modules/\n.env\n.env.*\nbuild/\n")
    _write(
        repo,
        ".guardkit/config.yaml",
        "toolchain:\n"
        '  test: "bash scripts/check.sh"\n'
        '  feature_check: "bash scripts/check-feature.sh"\n',
    )
    _write(
        repo,
        f"tasks/in_progress/{TASK_ID}.md",
        "---\n"
        f"id: {TASK_ID}\n"
        "title: Build the shelf page\n"
        "status: in_progress\n"
        "task_type: scaffolding\n"
        + ("implementation_mode: direct\n" if direct_mode else "")
        + "---\n\n# Build the shelf page\n\n"
        + (
            "## Files to Create\n\n" + "".join(f"- `{p}`\n" for p in PLANNED_CREATE)
            if declare_create
            else ""
        )
        + (
            "\n## Files to Modify\n\n" + "".join(f"- `{p}`\n" for p in PLANNED_MODIFY)
            if declare_modify
            else ""
        )
        + "\n## Acceptance Criteria\n\n"
        + "".join(f"- [ ] {c}\n" for c in CRITERIA),
    )
    _git(repo, "init", "-q", "-b", BRANCH)
    _git(repo, "config", "user.email", "factory@example.invalid")
    _git(repo, "config", "user.name", "Factory Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


REFUSE_UNRELATED = {
    "decision": "feedback",
    "rationale": "The billing files have nothing to do with the failing check.",
    "issues": [{
        "severity": "must_fix",
        "category": "scope",
        "description": (
            "apps/api/src/billing/invoice.ts is unrelated product work, not "
            "needed to make the failing check pass"
        ),
    }],
    "criteria_verification": [
        {"criterion_id": "AC-001", "result": "verified", "notes": "seen"}
    ],
}

APPROVE = {
    "decision": "approve",
    "rationale": "The page lists the books.",
    "validation_results": {"requirements_met": ["AC-001 verified"]},
    "criteria_verification": [
        {"criterion_id": "AC-001", "result": "verified", "notes": "seen"}
    ],
}


def make_orchestrator(
    repo: Path,
    seed_feedback: Optional[str],
    repair_round: Optional[RepairRound],
    prompts: List[str],
) -> AutoBuildOrchestrator:
    """A real task orchestrator and a real ``AgentInvoker.invoke_coach``.

    Only the model call is absent: ``_invoke_with_role`` records the prompt it
    was given and returns no events, and the verdict parser writes the
    model's answer. Every guard ``invoke_coach`` applies after the model,
    including the one that puts the deterministic gates' feedback in place of
    an approval over failed gates, runs for real.
    """
    invoker = AgentInvoker(worktree_path=repo)

    async def _model(**kwargs: Any) -> Any:
        prompts.append(kwargs.get("prompt") or "")
        return (None, [])

    invoker._invoke_with_role = AsyncMock(side_effect=_model)  # type: ignore[method-assign]
    orch = AutoBuildOrchestrator(
        repo_root=repo,
        max_turns=1,
        enable_pre_loop=False,
        enable_context=False,
        agent_invoker=invoker,
        worktree_manager=SimpleNamespace(worktrees_dir=repo.parent),
        seed_feedback=seed_feedback,
        repair_round=repair_round,
    )
    orch._progress_display = MagicMock()
    return orch


def _model_answers(verdict: Dict[str, Any]) -> Callable[..., None]:
    """Stands in for the verdict parser: the model's answer was ``verdict``."""

    def _write(*, harness_events: Any, task_id: str, turn: int, output_path: Path, **_: Any) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(
            json.dumps(dict(deepcopy(verdict), task_id=task_id, turn=turn), indent=2)
        )

    return _write


def player_writing(
    repo: Path,
    files: Dict[str, str],
    seen_feedback: List[Optional[str]],
    invoker: AgentInvoker,
    shell_step: Optional[Callable[[Path], None]] = None,
) -> Callable[..., AgentInvocationResult]:
    """The Player: writes ``files`` on disk and reports through the real writer
    of the task's own invoker (the one the orchestrator handed the round to)."""

    def _invoke_player_safely(*, task_id: str, turn: int, **kwargs: Any) -> AgentInvocationResult:
        seen_feedback.append(kwargs.get("feedback"))
        if shell_step is not None:
            shell_step(repo)  # what a shell command in the turn would do
        for rel, text in files.items():
            _write(repo, rel, text)
        report = {
            "task_id": task_id,
            "turn": turn,
            "files_created": sorted(files),
            "files_modified": [],
            "tests_run": True,
            "tests_passed": True,
            "implementation_notes": "invented",
            "completion_promises": [
                {
                    "criterion_id": "AC-001",
                    "criterion_text": CRITERIA[0],
                    "status": "complete",
                    "evidence": "the page renders the list",
                }
            ],
        }
        folder = repo / ".guardkit" / "autobuild" / task_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"player_turn_{turn}.json").write_text(json.dumps(report, indent=2))
        if invoker._get_implementation_mode(task_id) == "direct":
            invoker._write_direct_mode_results(task_id, report, success=True)
            return AgentInvocationResult(
                task_id=task_id, turn=turn, agent_type="player", success=True,
                report=report, duration_seconds=60.0,
            )
        invoker._write_task_work_results(
            task_id,
            {
                "phases": {
                    "phase_3": {"detected": True, "completed": True, "text": "Phase 3"},
                    "phase_4": {"detected": True, "completed": True, "text": "Phase 4"},
                    "phase_5": {"detected": True, "completed": True, "text": "Phase 5"},
                },
                "tests_passed": 1,
                "tests_failed": 0,
                "quality_gates_passed": True,
                "files_created": report["files_created"],
                "files_modified": [],
            },
        )
        return AgentInvocationResult(
            task_id=task_id,
            turn=turn,
            agent_type="player",
            success=True,
            report=report,
            duration_seconds=60.0,
        )

    return _invoke_player_safely


def run_round(
    repo: Path,
    files: Dict[str, str],
    seed_feedback: Optional[str] = None,
    repair_round: Optional[RepairRound] = None,
    model_verdict: Optional[Dict[str, Any]] = None,
    requirements: str = "Show the reader's books on a shelf page.",
    shell_step: Optional[Callable[[Path], None]] = None,
) -> Dict[str, Any]:
    prompts: List[str] = []
    orch = make_orchestrator(repo, seed_feedback, repair_round, prompts)
    seen: List[Optional[str]] = []
    orch._invoke_player_safely = player_writing(  # type: ignore[method-assign]
        repo, files, seen, orch._agent_invoker, shell_step
    )
    worktree = SimpleNamespace(
        task_id=FEATURE_ID, path=repo, branch_name=BRANCH, base_branch="main"
    )
    with patch(
        "guardkit.orchestrator.coach_output_parser.extract_and_write",
        side_effect=_model_answers(model_verdict or APPROVE),
    ):
        history, decision = orch._loop_phase(
            task_id=TASK_ID,
            requirements=requirements,
            acceptance_criteria=CRITERIA,
            worktree=worktree,
            task_type="scaffolding",
        )
    return {
        "history": history, "decision": decision, "seen": seen, "prompts": prompts,
        "orchestrator": orch,
    }


ROUND_ONE = {
    "apps/web/src/ShelfPage.tsx": "export const ShelfPage = () => null;\n",
    "apps/web/src/ShelfCard.tsx": "export const ShelfCard = () => null;\n",
    "apps/web/src/App.tsx": "export const App = () => 'shelf';\n",
}

# What the check needed: the failing spec and a helper beside it, the seed
# scripts beside the check's own script, and one shared test helper.
REPAIR_NEAR_THE_FAILURE = {
    "tests/e2e/shelf.spec.ts": "test('shelf shows only my books', () => {});\n",
    "tests/e2e/sign-in.ts": "export const signIn = () => 1;\n",
    "scripts/seed-sample-book.sh": "#!/bin/sh\necho one book\n",
    "scripts/seed-owner.sh": "#!/bin/sh\necho owner\n",
    "scripts/seed.sh": "#!/bin/sh\nbash scripts/seed-owner.sh\n",
    "apps/web/src/test-render.tsx": "export const render = () => 1;\n",
}

# A repair round that wanders: new product code nothing in the output names.
REPAIR_THAT_WANDERS = {
    "apps/api/src/billing/invoice.ts": "export const invoice = 1;\n",
    "apps/api/src/billing/tax.ts": "export const tax = 1;\n",
    "apps/api/src/billing/ledger.ts": "export const ledger = 1;\n",
}


def reopen_and_repair(
    repo: Path,
    files: Dict[str, str],
    model_verdict: Optional[Dict[str, Any]] = None,
    *,
    fo: Optional[FeatureOrchestrator] = None,
    gate_output: str = GATE_OUTPUT,
    requirements: str = "Show the reader's books on a shelf page.",
    shell_step: Optional[Callable[[Path], None]] = None,
) -> Dict[str, Any]:
    """The real gate-driven re-open; the repair round runs through the loop.

    Pass the same ``fo`` to re-open the task again, as a later gate does."""
    fo = fo or FeatureOrchestrator(
        repo_root=repo.parents[2], worktree_manager=MagicMock(), quiet=True
    )
    worktree = Worktree(
        task_id=FEATURE_ID, branch_name=BRANCH, path=repo, base_branch="main"
    )
    feature = MagicMock()
    feature.id = FEATURE_ID
    task = MagicMock()
    task.id = TASK_ID
    task.status = "completed"
    task.dependencies = []
    task.turns_completed = 1
    task.estimated_minutes = None
    feature.tasks = [task]
    outcome: Dict[str, Any] = {"head_at_re_open": _git(repo, "rev-parse", "HEAD")}

    def _execute_task(task_, feature_, worktree_, **kwargs: Any) -> TaskExecutionResult:
        outcome["repair_round"] = kwargs.get("repair_round")
        outcome.update(run_round(
            Path(worktree_.path),
            files,
            seed_feedback=kwargs.get("seed_feedback"),
            repair_round=kwargs.get("repair_round"),
            model_verdict=model_verdict,
            requirements=requirements,
            shell_step=shell_step,
        ))
        # What the real _execute_task does after orchestrate().
        fo._remember_repair_approvals(task_.id, outcome["orchestrator"])
        return TaskExecutionResult(
            task_id=task_.id,
            success=outcome["decision"] == "approved",
            total_turns=len(outcome["history"]),
            final_decision=outcome["decision"],
        )

    with patch.object(fo, "_execute_task", side_effect=_execute_task), \
            patch("guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
                  side_effect=lambda f, tid: f.tasks[0]), \
            patch("guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature"), \
            patch("guardkit.orchestrator.feature_orchestrator.TaskLoader.load_task",
                  side_effect=Exception("no task file")), \
            patch.object(fo, "_update_task_started"), \
            patch.object(fo, "_update_feature"):
        asyncio.run(
            fo._execute_wave_parallel(
                2, [TASK_ID], feature, worktree, seed_feedback=gate_output
            )
        )
    outcome["fo"] = fo
    return outcome


def _plan_audit(repo: Path) -> Dict[str, Any]:
    path = repo / ".guardkit" / "autobuild" / TASK_ID / "task_work_results.json"
    return json.loads(path.read_text())["plan_audit"]


def _plan_audit_issues(history: List[Any]) -> List[Dict[str, Any]]:
    report = history[-1].coach_result.report or {}
    return [i for i in report.get("issues", []) if i.get("category") == "plan_audit"]


@pytest.fixture(autouse=True)
def _no_model_can_be_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    """The orchestrator's own specialists must never reach a model here: the
    M0 fence refuses any seat without a named local model unless this is set."""
    monkeypatch.delenv("GUARDKIT_ALLOW_FRONTIER", raising=False)


@pytest.fixture
def approved_round_one(tmp_path: Path) -> Path:
    repo = make_project(tmp_path)
    outcome = run_round(repo, ROUND_ONE)
    assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
    return repo


def _repair_section(prompts: List[str]) -> str:
    assert prompts, "the model was never asked"
    prompt = prompts[-1]
    start = prompt.index("## This is a repair round")
    return prompt[start:prompt.index("## Player's Report", start)]


class TestARepairRoundCanDoItsJob:
    def test_the_files_the_check_needed_reach_the_reviewer_and_are_approved(
        self, approved_round_one: Path
    ) -> None:
        repo = approved_round_one
        outcome = reopen_and_repair(repo, REPAIR_NEAR_THE_FAILURE)

        # The re-open handed the round over in memory, and wrote nothing.
        assert outcome["repair_round"] == RepairRound(
            round_number=2,
            start_commit=outcome["head_at_re_open"],
            gate_output=GATE_OUTPUT,
            protected_fingerprints=outcome["repair_round"].protected_fingerprints,
        )
        # Fingerprints only, of every protected path: tracked ones here.
        # (.guardkit/ and the factory's git lock are the factory's own.)
        assert [path for path, _ in outcome["repair_round"].protected_fingerprints] == [
            ".gitignore", "deploy/Dockerfile"
        ]
        private = TaskArtifactPaths.task_private_dir(TASK_ID, repo)
        assert not list(private.glob("repair_round*"))
        assert outcome["seen"][0] == GATE_OUTPUT

        # The reviewer was shown every extra file and the failing output.
        section = _repair_section(outcome["prompts"])
        for path in ("scripts/seed-owner.sh", "scripts/seed-sample-book.sh",
                     "tests/e2e/sign-in.ts", "apps/web/src/test-render.tsx"):
            assert f"- `{path}`" in section
        assert "- `tests/e2e/shelf.spec.ts` (the failing check's output names it)" in section
        assert "check-feature: FAIL exit=1" in section

        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
        block = _plan_audit(repo)
        assert block["status"] == "passed", block
        assert block["severity"] == "low"
        assert block["repair_round"]["start_commit"] == outcome["head_at_re_open"]

    def test_the_same_files_on_an_ordinary_turn_are_still_refused(
        self, approved_round_one: Path
    ) -> None:
        """Control: without the re-open the rule is exactly today's, and a
        repair-round file on disk (the old design's record) changes nothing."""
        repo = approved_round_one
        private = TaskArtifactPaths.task_private_dir(TASK_ID, repo)
        (private / "round-1").mkdir(parents=True, exist_ok=True)
        (private / "repair_round.json").write_text(json.dumps({
            "task_id": TASK_ID, "round": 1,
            "start_commit": _git(repo, "rev-parse", "HEAD"),
            "implicated_paths": ["tests/e2e/shelf.spec.ts"],
        }))
        outcome = run_round(repo, REPAIR_NEAR_THE_FAILURE)
        assert outcome["decision"] != "approved"
        block = _plan_audit(repo)
        assert block["status"] == "violation"
        assert block["severity"] == "high"
        assert "repair_round" not in block
        assert _plan_audit_issues(outcome["history"])
        assert all("## This is a repair round" not in p for p in outcome["prompts"])


class TestARepairRoundThatWandersIsRefused:
    def test_the_reviewer_refuses_unrelated_product_code(self, approved_round_one: Path) -> None:
        repo = approved_round_one
        outcome = reopen_and_repair(
            repo,
            {**REPAIR_THAT_WANDERS, "tests/e2e/shelf.spec.ts": "test('x', () => {});\n"},
            model_verdict=REFUSE_UNRELATED,
        )

        section = _repair_section(outcome["prompts"])
        for path in REPAIR_THAT_WANDERS:
            assert f"- `{path}`" in section
        assert outcome["decision"] != "approved"
        report = outcome["history"][-1].coach_result.report
        assert report["decision"] == "feedback"
        assert any(
            "apps/api/src/billing/invoice.ts" in issue.get("description", "")
            for issue in report.get("issues", [])
        )

    def test_a_protected_file_is_refused_whatever_the_reviewer_says(
        self, approved_round_one: Path
    ) -> None:
        repo = approved_round_one
        outcome = reopen_and_repair(
            repo,
            {
                "tests/e2e/sign-in.ts": "export const signIn = 1;\n",
                "db/migrations/0003_seed_books.sql": "insert into books values (1);\n",
            },
            model_verdict=APPROVE,
        )

        assert outcome["decision"] != "approved"
        block = _plan_audit(repo)
        assert block["severity"] == "high"
        issues = _plan_audit_issues(outcome["history"])
        assert issues and issues[0]["severity"] == "must_fix"
        assert "db/migrations/0003_seed_books.sql" in issues[0]["description"]


class TestTheLegacyCoachHasNoReviewer:
    """With ``GUARDKIT_COACH_LEGACY=1`` no LLM reviewer judges the extra files,
    so a repair round is audited exactly as an ordinary turn, and the log says
    so."""

    def test_a_repair_round_is_refused_by_count_and_the_log_says_why(
        self,
        approved_round_one: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        repo = approved_round_one
        monkeypatch.setenv("GUARDKIT_COACH_LEGACY", "1")
        with caplog.at_level("WARNING", logger="guardkit.orchestrator.autobuild"):
            outcome = reopen_and_repair(repo, REPAIR_NEAR_THE_FAILURE)

        # The re-open still started the round; the loop did not use it.
        assert isinstance(outcome["repair_round"], RepairRound)
        assert outcome["decision"] != "approved"
        block = _plan_audit(repo)
        assert block["status"] == "violation"
        assert block["severity"] == "high"
        assert "repair_round" not in block
        assert block["extra_files_for_the_reviewer"] == []
        # No model Coach was asked, and nothing carried a repair section.
        assert not any(p.startswith("You are the Coach agent") for p in outcome["prompts"])
        assert all("## This is a repair round" not in p for p in outcome["prompts"])
        assert any(
            "audited as an ordinary turn" in record.getMessage()
            and "GUARDKIT_COACH_LEGACY=1" in record.getMessage()
            for record in caplog.records
        )


class TestTheReviewerSeesEveryChange:
    def test_an_unplanned_edit_reaches_the_reviewer_without_a_modify_section(
        self, tmp_path: Path
    ) -> None:
        """The task declares only files to create, so the ordinary audit says
        nothing about edits; the unrelated edit still reaches the reviewer,
        and its refusal blocks the approval."""
        repo = make_project(tmp_path, declare_modify=False)
        assert run_round(repo, ROUND_ONE)["decision"] == "approved"
        refuse = deepcopy(REFUSE_UNRELATED)
        refuse["issues"][0]["description"] = (
            "apps/api/src/server.ts was changed to add billing, which the "
            "failing check does not need"
        )
        outcome = reopen_and_repair(
            repo,
            {
                "tests/e2e/sign-in.ts": "export const signIn = 1;\n",
                "apps/api/src/server.ts": "export const serve = () => 2; // billing\n",
            },
            model_verdict=refuse,
        )

        section = _repair_section(outcome["prompts"])
        assert "- `apps/api/src/server.ts`" in section
        assert _plan_audit(repo)["extra_modifications"] == []  # ordinary audit silent
        assert outcome["decision"] != "approved"


class TestSequentialReEntries:
    def test_a_second_gate_does_not_recount_what_the_first_repair_approved(
        self, approved_round_one: Path
    ) -> None:
        repo = approved_round_one
        first = reopen_and_repair(repo, REPAIR_NEAR_THE_FAILURE)
        assert first["decision"] == "approved"
        # Another gate (say the wiring gate after the smoke gate) re-opens it.
        second = reopen_and_repair(
            repo,
            {"tests/e2e/shelf.spec.ts": "test('wired', () => {});\n"},
            fo=first["fo"],
            gate_output="The wiring check failed: tests/e2e/shelf.spec.ts:9:1",
        )

        assert second["repair_round"].round_number == 3
        assert {
            "scripts/seed-owner.sh", "scripts/seed-sample-book.sh",
            "tests/e2e/sign-in.ts", "apps/web/src/test-render.tsx",
        } <= second["repair_round"].approved_by_earlier_repairs
        assert second["decision"] == "approved", second["history"][-1].coach_result.report
        block = _plan_audit(repo)
        assert block["status"] == "passed"
        assert "apps/web/src/test-render.tsx" in block["extra_files_approved_by_a_repair"]


class TestTheReviewSectionMustReachTheModel:
    """In a repair round the audit leaves the extra files to the reviewer, so
    the Coach is not run unless the whole section reaches the model."""

    REFUSED = "review section could not be kept whole"

    def _coach_error(self, outcome: Dict[str, Any]) -> str:
        return str(getattr(outcome["history"][-1].coach_result, "error", "") or "")

    def test_an_oversized_section_refuses_the_turn(
        self, approved_round_one: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = approved_round_one
        monkeypatch.setattr(AgentInvoker, "_COACH_SYNTHESIS_MAX_CHARS", 5000)
        many = {
            f"tests/e2e/fixtures/generated-fixture-number-{n:04d}.json": "{}\n"
            for n in range(300)
        }
        outcome = reopen_and_repair(repo, many)

        assert outcome["decision"] != "approved"
        assert not any(p.startswith("You are the Coach agent") for p in outcome["prompts"])
        assert self.REFUSED in self._coach_error(outcome)

    def test_an_oversized_prefix_refuses_the_turn(
        self, approved_round_one: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = approved_round_one
        monkeypatch.setattr(AgentInvoker, "_COACH_SYNTHESIS_MAX_CHARS", 20000)
        outcome = reopen_and_repair(
            repo, REPAIR_NEAR_THE_FAILURE, requirements="Show the shelf. " * 3000
        )

        assert outcome["decision"] != "approved"
        assert not any(p.startswith("You are the Coach agent") for p in outcome["prompts"])
        assert self.REFUSED in self._coach_error(outcome)

    def test_a_long_gate_output_is_cut_and_every_file_is_still_listed(
        self, approved_round_one: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = approved_round_one
        monkeypatch.setattr(AgentInvoker, "_COACH_SYNTHESIS_MAX_CHARS", 6000)
        long_output = GATE_OUTPUT + "".join(
            f"  noise line {n} from the check runner\n" for n in range(400)
        )
        outcome = reopen_and_repair(repo, REPAIR_NEAR_THE_FAILURE, gate_output=long_output)

        section = _repair_section(outcome["prompts"])
        for path in ("scripts/seed-owner.sh", "scripts/seed-sample-book.sh",
                     "tests/e2e/sign-in.ts", "apps/web/src/test-render.tsx"):
            assert f"- `{path}`" in section
        assert "noise line 399" in section  # the end of the output is kept
        assert "noise line 100 " not in section  # the rest was cut
        assert outcome["decision"] == "approved"


class TestProtectedFilesWhateverTheTaskDeclares:
    """A task that declares only files to modify has no "files to create"
    section, so the ordinary audit lists no new files. In a repair round a
    protected file made or changed is still refused, even when the reviewer
    approves."""

    def _modify_only(self, tmp_path: Path) -> Path:
        repo = make_project(tmp_path, declare_create=False)
        outcome = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
        return repo

    def test_a_new_migration_is_refused(self, tmp_path: Path) -> None:
        repo = self._modify_only(tmp_path)
        outcome = reopen_and_repair(
            repo,
            {
                "tests/e2e/sign-in.ts": "export const signIn = 1;\n",
                "db/migrations/0003_seed_books.sql": "insert into books values (1);\n",
            },
            model_verdict=APPROVE,
        )
        assert outcome["decision"] != "approved"
        issues = _plan_audit_issues(outcome["history"])
        assert issues and issues[0]["severity"] == "must_fix"
        assert "db/migrations/0003_seed_books.sql" in issues[0]["description"]

    def test_an_edited_dockerfile_is_refused(self, tmp_path: Path) -> None:
        repo = self._modify_only(tmp_path)
        outcome = reopen_and_repair(
            repo,
            {"deploy/Dockerfile": "FROM scratch\nRUN echo seeded\n"},
            model_verdict=APPROVE,
        )
        assert outcome["decision"] != "approved"
        issues = _plan_audit_issues(outcome["history"])
        assert issues and issues[0]["severity"] == "must_fix"
        assert "deploy/Dockerfile" in issues[0]["description"]


class TestCarriedApprovalsAreThisTasksOwn:
    def test_another_tasks_planned_dockerfile_change_is_never_carried(
        self, approved_round_one: Path
    ) -> None:
        """Task B, sharing the worktree, makes its planned Dockerfile change;
        task A's later repair round edits the Dockerfile and is refused."""
        repo = approved_round_one
        first = reopen_and_repair(repo, REPAIR_NEAR_THE_FAILURE)
        assert first["decision"] == "approved"
        fo = first["fo"]
        carried = fo._repair_approvals[TASK_ID]
        assert "apps/web/src/test-render.tsx" in carried

        # Task B's planned change lands on the shared branch.
        _write(repo, "deploy/Dockerfile", "FROM scratch\nEXPOSE 8080\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "task B: planned Dockerfile change")

        second = reopen_and_repair(
            repo,
            {"deploy/Dockerfile": "FROM scratch\nEXPOSE 9090\n"},
            fo=fo,
            gate_output="The smoke check failed: deploy/Dockerfile",
            model_verdict=APPROVE,
        )

        assert "deploy/Dockerfile" not in second["repair_round"].approved_by_earlier_repairs
        assert second["repair_round"].approved_by_earlier_repairs == frozenset(carried)
        assert second["decision"] != "approved"
        issues = _plan_audit_issues(second["history"])
        assert issues and "deploy/Dockerfile" in issues[0]["description"]

    def test_an_unapproved_repair_round_carries_nothing(self, approved_round_one: Path) -> None:
        repo = approved_round_one
        outcome = reopen_and_repair(
            repo,
            {**REPAIR_THAT_WANDERS, "tests/e2e/shelf.spec.ts": "test('x', () => {});\n"},
            model_verdict=REFUSE_UNRELATED,
        )
        assert outcome["decision"] != "approved"
        assert outcome["fo"]._repair_approvals.get(TASK_ID) is None



class TestARenameIsSeen:
    def test_moving_the_dockerfile_away_is_refused_and_the_old_path_is_listed(
        self, tmp_path: Path
    ) -> None:
        """A modify-only task's repair turn renames the project's Dockerfile.
        git's rename detection would name only the new path; the repair
        round's audit sees the path it left."""
        repo = make_project(tmp_path, declare_create=False)
        assert run_round(
            repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"}
        )["decision"] == "approved"

        def _rename(root: Path) -> None:
            (root / "scripts").mkdir(exist_ok=True)
            _git(root, "mv", "deploy/Dockerfile", "scripts/image-build")

        outcome = reopen_and_repair(
            repo,
            {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"},
            model_verdict=APPROVE,
            shell_step=_rename,
        )

        assert outcome["decision"] != "approved"
        block = _plan_audit(repo)
        assert "deploy/Dockerfile" in block["repair_round"]["files_changed_this_round"]
        assert "scripts/image-build" in block["repair_round"]["files_made_this_round"]
        issues = _plan_audit_issues(outcome["history"])
        assert issues and "deploy/Dockerfile" in issues[0]["description"]
        # The reviewer was shown the path the file left, too.
        assert "- `deploy/Dockerfile`" in _repair_section(outcome["prompts"])


class TestEveryAuditPathGetsTheReview:
    """The repair review and the protected refusal run on every repair-round
    turn before the Coach, whatever audit path the task takes."""

    @pytest.mark.parametrize(
        "direct_mode", [False, True], ids=["no-declarations", "direct-mode"]
    )
    def test_a_migration_is_refused_and_an_unrelated_edit_is_listed(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        # No "files to create", no "files to modify", no saved plan, and no
        # path in the acceptance criteria: the plan audit has nothing to
        # compare and is skipped (or, in direct mode, not run at all).
        repo = make_project(
            tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
        )
        first = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
        assert first["decision"] == "approved", first["history"][-1].coach_result.report

        outcome = reopen_and_repair(
            repo,
            {
                "tests/e2e/sign-in.ts": "export const signIn = 1;\n",
                "apps/api/src/server.ts": "export const serve = () => 2; // billing\n",
                "db/migrations/0003_seed_books.sql": "insert into books values (1);\n",
            },
            model_verdict=APPROVE,
        )

        section = _repair_section(outcome["prompts"])
        assert "- `apps/api/src/server.ts`" in section
        assert "- `tests/e2e/sign-in.ts`" in section
        assert outcome["decision"] != "approved"
        report = outcome["history"][-1].coach_result.report
        assert report["decision"] == "feedback"
        protected = [
            i for i in report.get("issues", []) if i.get("category") == "repair_round_protected"
        ]
        assert protected and "db/migrations/0003_seed_books.sql" in protected[0]["description"]
        assert protected[0]["severity"] == "must_fix"
        # The turn record on disk says the same (the late-approval reader).
        private = TaskArtifactPaths.task_private_dir(TASK_ID, repo)
        assert json.loads((private / "coach_turn_1.json").read_text())["decision"] == "feedback"
        # Nothing was carried: the turn was not approved.
        assert outcome["fo"]._repair_approvals.get(TASK_ID) is None

    def test_without_a_protected_file_the_reviewers_approval_stands(self, tmp_path: Path) -> None:
        repo = make_project(tmp_path, declare_create=False, declare_modify=False)
        assert run_round(
            repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"}
        )["decision"] == "approved"
        outcome = reopen_and_repair(
            repo, {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"}, model_verdict=APPROVE
        )
        assert outcome["decision"] == "approved"
        assert outcome["fo"]._repair_approvals[TASK_ID] == {"tests/e2e/sign-in.ts"}


class TestAnUnreadableRecordIsNeverApproved:
    """In a repair round the audit leaves extra files to the reviewer, so a
    turn whose record of what changed cannot be read is refused, whatever the
    reviewer says. Ordinary turns are unchanged."""

    REFUSAL = (
        "The repair round's record of what changed could not be read, so this "
        "turn cannot be approved."
    )

    def _approved_round_one(self, tmp_path: Path, direct_mode: bool) -> Path:
        repo = make_project(
            tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
        )
        first = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
        assert first["decision"] == "approved", first["history"][-1].coach_result.report
        return repo

    def _assert_refused(self, repo: Path, outcome: Dict[str, Any]) -> None:
        assert outcome["decision"] != "approved"
        report = outcome["history"][-1].coach_result.report
        assert report["decision"] == "feedback"
        refusals = [
            i for i in report.get("issues", []) if i.get("category") == "repair_round_unreadable"
        ]
        assert refusals and refusals[0]["severity"] == "must_fix"
        assert refusals[0]["description"] == self.REFUSAL
        private = TaskArtifactPaths.task_private_dir(TASK_ID, repo)
        saved = json.loads((private / "coach_turn_1.json").read_text())
        assert saved["decision"] == "feedback"
        assert any(i.get("category") == "repair_round_unreadable" for i in saved["issues"])
        assert outcome["fo"]._repair_approvals.get(TASK_ID) is None

    @staticmethod
    def _checkpoints(repo: Path) -> Path:
        return repo / ".guardkit" / "autobuild" / TASK_ID / "checkpoints.json"

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_missing_checkpoint_record_refuses_the_turn(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._approved_round_one(tmp_path, direct_mode)
        outcome = reopen_and_repair(
            repo,
            {"db/migrations/0003_seed_books.sql": "insert into books values (1);\n"},
            model_verdict=APPROVE,
            shell_step=lambda root: self._checkpoints(root).unlink(),
        )
        self._assert_refused(repo, outcome)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_malformed_checkpoint_record_refuses_the_turn(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._approved_round_one(tmp_path, direct_mode)
        outcome = reopen_and_repair(
            repo,
            {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"},
            model_verdict=APPROVE,
            shell_step=lambda root: self._checkpoints(root).write_text("{not json"),
        )
        self._assert_refused(repo, outcome)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_read_that_raises_refuses_the_turn(
        self, tmp_path: Path, direct_mode: bool, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = self._approved_round_one(tmp_path, direct_mode)
        from installer.core.commands.lib.plan_audit import PlanAuditor

        def _raise(self: Any, task_id: Any) -> Any:
            raise OSError("invented read failure")

        monkeypatch.setattr(PlanAuditor, "_repair_round_facts", _raise)
        outcome = reopen_and_repair(
            repo,
            {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"},
            model_verdict=APPROVE,
        )
        self._assert_refused(repo, outcome)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_readable_record_still_approves(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._approved_round_one(tmp_path, direct_mode)
        outcome = reopen_and_repair(
            repo, {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"}, model_verdict=APPROVE
        )
        assert outcome["decision"] == "approved"
        assert outcome["fo"]._repair_approvals[TASK_ID] == {"tests/e2e/sign-in.ts"}

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_ordinary_turn_with_a_missing_record_is_unchanged(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._approved_round_one(tmp_path, direct_mode)
        outcome = run_round(
            repo,
            {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"},
            shell_step=lambda root: self._checkpoints(root).unlink(),
        )
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
        report = outcome["history"][-1].coach_result.report
        assert not any(
            i.get("category") == "repair_round_unreadable" for i in report.get("issues", [])
        )


SECRET = "INVENTED_SECRET_VALUE_31f7"


class TestIgnoredProtectedFiles:
    """git's view of changes leaves out ignored files, so an ignored ``.env``
    is compared, by path and hash only, with what the re-open recorded."""

    def _round_one(self, tmp_path: Path, direct_mode: bool, env: Optional[str]) -> Path:
        repo = make_project(
            tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
        )
        if env is not None:
            _write(repo, ".env", env)  # ignored: never committed
        _write(repo, "build/out.txt", "first build\n")  # ignored, not protected
        first = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
        assert first["decision"] == "approved", first["history"][-1].coach_result.report
        return repo

    def _refused_naming_env(self, outcome: Dict[str, Any]) -> None:
        assert outcome["decision"] != "approved"
        report = outcome["history"][-1].coach_result.report
        refusals = [
            i for i in report.get("issues", []) if i.get("category") == "repair_round_protected"
        ]
        assert refusals and ".env" in refusals[0]["details"]["protected"]
        assert outcome["fo"]._repair_approvals.get(TASK_ID) is None

    def _no_secret_anywhere(self, repo: Path, outcome: Dict[str, Any]) -> None:
        for prompt in outcome["prompts"]:
            assert SECRET not in prompt
        main = repo.parents[2]
        worktrees = main / ".guardkit" / "worktrees"
        # Every record the build keeps: the main checkout's .guardkit (its
        # private folder) and the worktree's .guardkit, not the project's own
        # files (the .env itself lives there).
        for folder in (main / ".guardkit", repo / ".guardkit"):
            for path in folder.rglob("*"):
                if path.is_file() and worktrees not in path.parents:
                    assert SECRET.encode() not in path.read_bytes(), path
        for path in (repo / ".guardkit").rglob("*"):
            if path.is_file():
                assert SECRET.encode() not in path.read_bytes(), path
        assert SECRET not in json.dumps(
            [tr.coach_result.report for tr in outcome["history"]], default=str
        )

    HELPER = {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"}

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_ignored_env_made_during_the_repair_is_refused(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env=None)
        outcome = reopen_and_repair(
            repo, {**self.HELPER, ".env": f"API_TOKEN={SECRET}\n"}, model_verdict=APPROVE
        )
        self._refused_naming_env(outcome)
        self._no_secret_anywhere(repo, outcome)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_ignored_env_edited_during_the_repair_is_refused(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env=f"API_TOKEN={SECRET}\n")
        outcome = reopen_and_repair(
            repo, {**self.HELPER, ".env": f"API_TOKEN={SECRET}x\n"}, model_verdict=APPROVE
        )
        self._refused_naming_env(outcome)
        self._no_secret_anywhere(repo, outcome)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_ignored_env_deleted_during_the_repair_is_refused(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env=f"API_TOKEN={SECRET}\n")
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: (root / ".env").unlink(),
        )
        self._refused_naming_env(outcome)
        self._no_secret_anywhere(repo, outcome)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_unchanged_ignored_env_still_approves(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env=f"API_TOKEN={SECRET}\n")
        outcome = reopen_and_repair(repo, self.HELPER, model_verdict=APPROVE)
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
        # Recorded by path and hash only.
        recorded = dict(outcome["repair_round"].protected_fingerprints)
        assert ".env" in recorded and SECRET not in recorded[".env"]
        self._no_secret_anywhere(repo, outcome)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_ignored_file_that_is_not_protected_is_not_refused_by_this_rule(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env=None)
        outcome = reopen_and_repair(
            repo, {**self.HELPER, "build/out.txt": "second build\n"}, model_verdict=APPROVE
        )
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_no_listing_refuses_the_turn(
        self, tmp_path: Path, direct_mode: bool, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env=None)
        from guardkit.orchestrator import repair_round as rr

        real = rr.protected_files
        calls = {"n": 0}

        def _second_listing_fails(worktree_path: Path) -> Any:
            calls["n"] += 1
            return real(worktree_path) if calls["n"] == 1 else None

        monkeypatch.setattr(rr, "protected_files", _second_listing_fails)
        outcome = reopen_and_repair(repo, self.HELPER, model_verdict=APPROVE)
        assert outcome["decision"] != "approved"
        report = outcome["history"][-1].coach_result.report
        assert any(
            i.get("category") == "repair_round_unreadable" for i in report.get("issues", [])
        )


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root reads unreadable files"
)
class TestEveryFailurePathFailsClosed:
    """A repair round whose facts cannot be established is still a repair
    round, and every one of its turns is refused (no stand-in value, no
    fallback to an ordinary turn)."""

    def _round_one(self, tmp_path: Path, direct_mode: bool, env: Optional[str]) -> Path:
        repo = make_project(
            tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
        )
        if env is not None:
            _write(repo, ".env", env)
        first = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
        assert first["decision"] == "approved", first["history"][-1].coach_result.report
        return repo

    def _refused_as_unreadable(self, repo: Path, outcome: Dict[str, Any]) -> None:
        assert outcome["decision"] != "approved"
        report = outcome["history"][-1].coach_result.report
        assert report["decision"] == "feedback"
        assert any(
            i.get("category") == "repair_round_unreadable" for i in report.get("issues", [])
        ), report.get("issues")
        private = TaskArtifactPaths.task_private_dir(TASK_ID, repo)
        assert json.loads((private / "coach_turn_1.json").read_text())["decision"] == "feedback"
        assert outcome["fo"]._repair_approvals.get(TASK_ID) is None

    HELPER = {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"}

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_one_shot_head_failure_at_the_re_open_is_refused(
        self, tmp_path: Path, direct_mode: bool, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env=None)
        from guardkit.orchestrator import repair_round as rr

        real = rr.git_head
        calls = {"n": 0}

        def _first_call_fails(worktree_path: Path) -> str:
            calls["n"] += 1
            if calls["n"] == 1:
                raise rr.RepairFactsUnavailable("HEAD could not be read")
            return real(worktree_path)

        monkeypatch.setattr(rr, "git_head", _first_call_fails)
        outcome = reopen_and_repair(repo, self.HELPER, model_verdict=APPROVE)

        assert outcome["repair_round"] is not None  # never dropped
        assert outcome["repair_round"].unavailable
        self._refused_as_unreadable(repo, outcome)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_protected_file_unreadable_at_the_baseline_only_is_refused(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env="A=1\n")
        os.chmod(repo / ".env", 0)
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: os.chmod(root / ".env", 0o600),
        )
        assert outcome["repair_round"].unavailable
        self._refused_as_unreadable(repo, outcome)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_protected_file_unreadable_at_the_current_read_only_is_refused(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env="A=1\n")
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: os.chmod(root / ".env", 0),
        )
        assert not outcome["repair_round"].unavailable
        os.chmod(repo / ".env", 0o600)
        self._refused_as_unreadable(repo, outcome)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_protected_file_unreadable_at_both_reads_and_changed_between_is_refused(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env="A=1\n")
        os.chmod(repo / ".env", 0)

        def _change_while_unreadable(root: Path) -> None:
            os.chmod(root / ".env", 0o600)
            (root / ".env").write_text("A=2\n")
            os.chmod(root / ".env", 0)

        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE, shell_step=_change_while_unreadable
        )
        os.chmod(repo / ".env", 0o600)
        self._refused_as_unreadable(repo, outcome)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_readable_unchanged_protected_file_approves(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env="A=1\n")
        outcome = reopen_and_repair(repo, self.HELPER, model_verdict=APPROVE)
        assert outcome["repair_round"].unavailable is None
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root reads unreadable files"
)
class TestASymlinkedProtectedFile:
    """A protected ignored file that is a symlink is fingerprinted by its link
    text, the path the chain resolves to and the target's contents, so a
    write through it or a retarget is seen; a target that cannot be read
    refuses the turn."""

    HELPER = {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"}

    def _round_one(self, tmp_path: Path, direct_mode: bool) -> Path:
        repo = make_project(
            tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
        )
        _write(repo, "build/out.txt", "A=1\n")  # ignored, not protected
        (repo / ".env").symlink_to("build/out.txt")  # ignored, protected
        first = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
        assert first["decision"] == "approved", first["history"][-1].coach_result.report
        return repo

    def _refused(self, repo: Path, outcome: Dict[str, Any], category: str) -> None:
        assert outcome["decision"] != "approved"
        report = outcome["history"][-1].coach_result.report
        assert any(i.get("category") == category for i in report.get("issues", [])), report
        private = TaskArtifactPaths.task_private_dir(TASK_ID, repo)
        assert json.loads((private / "coach_turn_1.json").read_text())["decision"] == "feedback"
        assert outcome["fo"]._repair_approvals.get(TASK_ID) is None

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_write_through_the_link_is_refused(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._round_one(tmp_path, direct_mode)
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: (root / ".env").write_text("A=2\n"),
        )
        assert (repo / ".env").is_symlink()
        self._refused(repo, outcome, "repair_round_protected")

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_unchanged_link_and_target_approve(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._round_one(tmp_path, direct_mode)
        outcome = reopen_and_repair(repo, self.HELPER, model_verdict=APPROVE)
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_retargeted_link_is_refused(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._round_one(tmp_path, direct_mode)

        def _retarget(root: Path) -> None:
            _write(root, "build/other.txt", "A=1\n")  # the same contents
            (root / ".env").unlink()
            (root / ".env").symlink_to("build/other.txt")

        outcome = reopen_and_repair(repo, self.HELPER, model_verdict=APPROVE, shell_step=_retarget)
        self._refused(repo, outcome, "repair_round_protected")

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_dangling_link_is_refused_as_unreadable(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._round_one(tmp_path, direct_mode)
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: (root / "build" / "out.txt").unlink(),
        )
        self._refused(repo, outcome, "repair_round_unreadable")

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_unreadable_target_is_refused_as_unreadable(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode)
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: os.chmod(root / "build" / "out.txt", 0),
        )
        os.chmod(repo / "build" / "out.txt", 0o600)
        self._refused(repo, outcome, "repair_round_unreadable")



@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root reads unreadable files"
)
class TestATrackedProtectedSymlink:
    """Every protected path is fingerprinted whatever git thinks of it: a
    committed protected symlink to an ignored target is followed too."""

    HELPER = {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"}

    def _round_one(self, tmp_path: Path, direct_mode: bool) -> Path:
        repo = make_project(
            tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
        )
        _write(repo, "build/out.txt", "FROM scratch\n")  # ignored, not protected
        (repo / "deploy" / "Dockerfile").unlink()
        (repo / "deploy" / "Dockerfile").symlink_to("../build/out.txt")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "the container file is a link to the build output")
        first = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
        assert first["decision"] == "approved", first["history"][-1].coach_result.report
        return repo

    def _refused(self, repo: Path, outcome: Dict[str, Any], category: str) -> None:
        assert outcome["decision"] != "approved"
        report = outcome["history"][-1].coach_result.report
        assert any(i.get("category") == category for i in report.get("issues", [])), report
        private = TaskArtifactPaths.task_private_dir(TASK_ID, repo)
        assert json.loads((private / "coach_turn_1.json").read_text())["decision"] == "feedback"
        assert outcome["fo"]._repair_approvals.get(TASK_ID) is None

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_write_through_a_tracked_link_is_refused(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode)
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: (root / "deploy" / "Dockerfile").write_text("FROM busybox\n"),
        )
        # git sees nothing: the link is unchanged and its target is ignored.
        assert _git(repo, "status", "--porcelain", "--", "deploy/Dockerfile") == ""
        self._refused(repo, outcome, "repair_round_protected")

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_unchanged_tracked_link_approves(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._round_one(tmp_path, direct_mode)
        outcome = reopen_and_repair(repo, self.HELPER, model_verdict=APPROVE)
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_tracked_link_with_an_unreadable_target_is_refused_as_unreadable(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode)
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: os.chmod(root / "build" / "out.txt", 0),
        )
        os.chmod(repo / "build" / "out.txt", 0o600)
        self._refused(repo, outcome, "repair_round_unreadable")

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_deleted_tracked_protected_file_is_a_protected_change(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        """A tracked path the worktree no longer has is absent from the
        fingerprints (a change), not an unreadable record."""
        repo = self._round_one(tmp_path, direct_mode)
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: (root / "deploy" / "Dockerfile").unlink(),
        )
        self._refused(repo, outcome, "repair_round_protected")
        report = outcome["history"][-1].coach_result.report
        assert not any(
            i.get("category") == "repair_round_unreadable" for i in report.get("issues", [])
        )


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root reads unreadable files"
)
class TestANestedRepository:
    """git lists an untracked nested repository as one entry; the walk of the
    filesystem goes inside it, so a protected file there is fingerprinted."""

    HELPER = {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"}
    ENV = "build/local/.env"

    def _round_one(self, tmp_path: Path, direct_mode: bool, env: Optional[str]) -> Path:
        repo = make_project(
            tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
        )
        nested = repo / "build" / "local"  # ignored (build/), with its own .git
        nested.mkdir(parents=True)
        _git(nested, "init", "-q")
        if env is not None:
            _write(repo, self.ENV, env)
        # git itself sees the nested repository only as one folder.
        assert self.ENV not in _git(repo, "ls-files", "--cached", "--others")
        first = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
        assert first["decision"] == "approved", first["history"][-1].coach_result.report
        return repo

    def _refused(self, repo: Path, outcome: Dict[str, Any], category: str) -> None:
        assert outcome["decision"] != "approved"
        report = outcome["history"][-1].coach_result.report
        issues = [i for i in report.get("issues", []) if i.get("category") == category]
        assert issues, report
        if category == "repair_round_protected":
            assert self.ENV in issues[0]["details"]["protected"]
        private = TaskArtifactPaths.task_private_dir(TASK_ID, repo)
        assert json.loads((private / "coach_turn_1.json").read_text())["decision"] == "feedback"
        assert outcome["fo"]._repair_approvals.get(TASK_ID) is None

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_created_env_inside_is_refused(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._round_one(tmp_path, direct_mode, env=None)
        outcome = reopen_and_repair(
            repo, {**self.HELPER, self.ENV: "A=1\n"}, model_verdict=APPROVE
        )
        self._refused(repo, outcome, "repair_round_protected")

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_modified_env_inside_is_refused(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._round_one(tmp_path, direct_mode, env="A=1\n")
        outcome = reopen_and_repair(
            repo, {**self.HELPER, self.ENV: "A=2\n"}, model_verdict=APPROVE
        )
        self._refused(repo, outcome, "repair_round_protected")

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_deleted_env_inside_is_refused(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._round_one(tmp_path, direct_mode, env="A=1\n")
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: (root / self.ENV).unlink(),
        )
        self._refused(repo, outcome, "repair_round_protected")

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_unchanged_env_inside_approves(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._round_one(tmp_path, direct_mode, env="A=1\n")
        outcome = reopen_and_repair(repo, self.HELPER, model_verdict=APPROVE)
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
        assert self.ENV in dict(outcome["repair_round"].protected_fingerprints)

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_unreadable_env_inside_is_refused(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._round_one(tmp_path, direct_mode, env="A=1\n")
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: os.chmod(root / self.ENV, 0),
        )
        os.chmod(repo / self.ENV, 0o600)
        self._refused(repo, outcome, "repair_round_unreadable")

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_an_unreadable_folder_is_refused(self, tmp_path: Path, direct_mode: bool) -> None:
        repo = self._round_one(tmp_path, direct_mode, env="A=1\n")
        outcome = reopen_and_repair(
            repo, self.HELPER, model_verdict=APPROVE,
            shell_step=lambda root: os.chmod(root / "build" / "local", 0),
        )
        os.chmod(repo / "build" / "local", 0o755)
        self._refused(repo, outcome, "repair_round_unreadable")

    def test_a_folder_symlink_loop_is_not_followed(self, tmp_path: Path) -> None:
        from guardkit.orchestrator.repair_round import protected_fingerprints

        repo = make_project(tmp_path)
        (repo / "build").mkdir(exist_ok=True)
        (repo / "build" / "loop").symlink_to("..")
        assert set(protected_fingerprints(repo)) == {".gitignore", "deploy/Dockerfile"}
