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

27 October 2026 cull: the reviewer's verdict is advice, the plan audit is no
longer written into the task's results, a repair round whose record cannot be
read no longer refuses the turn, and the legacy Coach is gone. What still
sends a repair-round turn back is a protected file it made, changed or
deleted. The tests of the deleted parts went with them.
"""

from __future__ import annotations

import asyncio
import json
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
from guardkit.orchestrator.task_work_scope import checkout_lease, current_lease
from guardkit.worktrees import Worktree
from tests.task_scope_fixtures import register_clean_fresh_checkout

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
    register: bool = True,
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
    if register:
        register_clean_fresh_checkout(repo)
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
    retained = current_lease(repo)
    assert retained is not None and retained.scope is not None
    orch.task_work_scope = retained.scope
    invoker.task_work_scope = retained.scope
    invoker._baseline_commit = retained.scope.baseline_commit
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
    _retained: bool = False,
) -> Dict[str, Any]:
    if not _retained:
        with checkout_lease(repo) as lease:
            lease.admit(TASK_ID, FEATURE_ID)
            return run_round(
                repo,
                files,
                seed_feedback=seed_feedback,
                repair_round=repair_round,
                model_verdict=model_verdict,
                requirements=requirements,
                shell_step=shell_step,
                _retained=True,
            )
    prompts: List[str] = []
    orch = make_orchestrator(repo, seed_feedback, repair_round, prompts)
    seen: List[Optional[str]] = []
    orch._invoke_player_safely = player_writing(  # type: ignore[method-assign]
        repo, files, seen, orch._agent_invoker, shell_step
    )
    worktree = SimpleNamespace(
        task_id=FEATURE_ID, path=repo, branch_name=BRANCH, base_branch="main"
    )
    # The pre-turn-1 pin ``orchestrate`` makes before the loop: the task's
    # changed parts' tests run the declared ``bash scripts/check.sh``.
    from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain

    snapshot_task_toolchain(TASK_ID, repo, repo)
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

    with patch.object(fo, "_execute_task_owned", side_effect=_execute_task), \
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


def _protected_issues(history: List[Any]) -> List[Dict[str, Any]]:
    """Step 1 (24 October 2026): the plan audit is advice (GKT-141), so a
    repair round's protected file is refused by the repair-round guard."""
    report = history[-1].coach_result.report or {}
    return [
        i for i in report.get("issues", [])
        if i.get("category") == "repair_round_protected"
    ]


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

    def test_the_same_files_on_an_ordinary_turn_are_audited_as_ordinary(
        self, approved_round_one: Path
    ) -> None:
        """Control: without the re-open the turn is an ordinary one, and a
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
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report
        assert not _protected_issues(outcome["history"])
        assert all("## This is a repair round" not in p for p in outcome["prompts"])


class TestARepairRoundThatWanders:
    def test_the_reviewer_sees_unrelated_product_code_and_its_verdict_is_advice(
        self, approved_round_one: Path
    ) -> None:
        repo = approved_round_one
        outcome = reopen_and_repair(
            repo,
            {**REPAIR_THAT_WANDERS, "tests/e2e/shelf.spec.ts": "test('x', () => {});\n"},
            model_verdict=REFUSE_UNRELATED,
        )

        section = _repair_section(outcome["prompts"])
        for path in REPAIR_THAT_WANDERS:
            assert f"- `{path}`" in section
        # The reviewer's refusal is kept as advice; it no longer sends the
        # turn back (nothing protected was touched).
        assert outcome["decision"] == "approved"
        report = outcome["history"][-1].coach_result.report
        assert report["decision"] == "approve"

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
        issues = _protected_issues(outcome["history"])
        assert issues and issues[0]["severity"] == "must_fix"
        assert "db/migrations/0003_seed_books.sql" in issues[0]["description"]


class TestTheReviewerSeesEveryChange:
    def test_an_unplanned_edit_reaches_the_reviewer_without_a_modify_section(
        self, tmp_path: Path
    ) -> None:
        """The task declares only files to create; the unrelated edit still
        reaches the reviewer (whose refusal is advice)."""
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
        assert outcome["decision"] == "approved"


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


class TestTheReviewSectionReachesTheModel:
    """A long gate output is cut so the review section fits; every file the
    round changed is still listed."""

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
        issues = _protected_issues(outcome["history"])
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
        issues = _protected_issues(outcome["history"])
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

        # Task B's planned change lands through its own real admitted scope;
        # an out-of-band clean commit is intentionally not resumable.
        with checkout_lease(repo) as lease:
            lease.admit("TASK-B", FEATURE_ID)
            _write(repo, "deploy/Dockerfile", "FROM scratch\nEXPOSE 8080\n")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-q", "-m", "task B: planned Dockerfile change")
            lease.checkpoint_completed()

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
        issues = _protected_issues(second["history"])
        assert issues and "deploy/Dockerfile" in issues[0]["description"]

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
        issues = _protected_issues(outcome["history"])
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
            tmp_path,
            declare_create=False,
            declare_modify=False,
            direct_mode=direct_mode,
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


class TestTheCheckpointRecordIsDiagnosticOnly:
    """Live scope is authority. ``checkpoints.json`` is diagnostic only:
    deleting or corrupting it cannot erase the retained in-memory checkpoints
    or hide a protected change.
    """

    def _approved_round_one(self, tmp_path: Path, direct_mode: bool) -> Path:
        repo = make_project(
            tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
        )
        first = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
        assert first["decision"] == "approved", first["history"][-1].coach_result.report
        return repo

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
        # The deleted diagnostic file cannot hide the protected migration.
        assert outcome["decision"] != "approved"
        issues = outcome["history"][-1].coach_result.report.get("issues", [])
        protected = [i for i in issues if i.get("category") == "repair_round_protected"]
        assert protected and "db/migrations/0003_seed_books.sql" in protected[0]["description"]
        assert outcome["fo"]._repair_approvals.get(TASK_ID) is None

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
        # A Player-writable diagnostic file is not a credential and does not
        # override the retained scope/checkpoint lineage.
        assert outcome["decision"] == "approved"
        assert outcome["fo"]._repair_approvals[TASK_ID] == {"tests/e2e/sign-in.ts"}

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

class TestAReadableProtectedFile:
    """A readable, unchanged protected file leaves the reviewer's approval."""

    def _round_one(self, tmp_path: Path, direct_mode: bool, env: Optional[str]) -> Path:
        repo = make_project(
            tmp_path, declare_create=False, declare_modify=False, direct_mode=direct_mode
        )
        if env is not None:
            _write(repo, ".env", env)
        first = run_round(repo, {"apps/web/src/App.tsx": "export const App = () => 1;\n"})
        assert first["decision"] == "approved", first["history"][-1].coach_result.report
        return repo

    HELPER = {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"}

    @pytest.mark.parametrize("direct_mode", [False, True], ids=["no-declarations", "direct-mode"])
    def test_a_readable_unchanged_protected_file_approves(
        self, tmp_path: Path, direct_mode: bool
    ) -> None:
        repo = self._round_one(tmp_path, direct_mode, env="A=1\n")
        outcome = reopen_and_repair(repo, self.HELPER, model_verdict=APPROVE)
        assert outcome["repair_round"].unavailable is None
        assert outcome["decision"] == "approved", outcome["history"][-1].coach_result.report


class TestASymlinkedProtectedFile:
    """A protected ignored file that is a symlink is fingerprinted by its link
    text, the path the chain resolves to and the target's contents, so a
    write through it or a retarget is seen."""

    HELPER = {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"}

    def _round_one(self, tmp_path: Path, direct_mode: bool) -> Path:
        repo = make_project(
            tmp_path,
            declare_create=False,
            declare_modify=False,
            direct_mode=direct_mode,
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

class TestATrackedProtectedSymlink:
    """Every protected path is fingerprinted whatever git thinks of it: a
    committed protected symlink to an ignored target is followed too."""

    HELPER = {"tests/e2e/sign-in.ts": "export const signIn = 1;\n"}

    def _round_one(self, tmp_path: Path, direct_mode: bool) -> Path:
        repo = make_project(
            tmp_path,
            declare_create=False,
            declare_modify=False,
            direct_mode=direct_mode,
            register=False,
        )
        _write(repo, "build/out.txt", "FROM scratch\n")  # ignored, not protected
        (repo / "deploy" / "Dockerfile").unlink()
        (repo / "deploy" / "Dockerfile").symlink_to("../build/out.txt")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "the container file is a link to the build output")
        register_clean_fresh_checkout(repo)
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

    def test_a_folder_symlink_loop_is_not_followed(self, tmp_path: Path) -> None:
        from guardkit.orchestrator.repair_round import protected_fingerprints

        repo = make_project(tmp_path)
        (repo / "build").mkdir(exist_ok=True)
        (repo / "build" / "loop").symlink_to("..")
        assert set(protected_fingerprints(repo)) == {".gitignore", "deploy/Dockerfile"}
