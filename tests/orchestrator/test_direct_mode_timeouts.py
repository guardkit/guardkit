"""Direct-mode turns that run out of time (build FEAT-2C42, 8 October 2026).

What the build showed, and what each test below pins:

- Direct-mode coder turns were given 1.0x the base time where task-work got
  1.5x. 31% of direct turns ran out of time before writing their report.
  -> ``TestDirectModeTimeBudget``
- On a timeout the factory writes a placeholder ``player_turn_N.json``
  (``success: false``, an ``error``, empty file lists). State recovery read
  that placeholder as the coder's report and ignored git, logging "0 files"
  while git showed changed files.
  -> ``TestPlaceholderIsNotThePlayersReport``
- The evidence gate's feedback never said the turn ran out of time, and its
  must-fix item reached the coder with an empty suggestion.
  -> ``TestTimeoutReachesMustFix``
- The final summary blamed "player_report" and suggested sign-in and SDK
  checks, which do not apply to a local model.
  -> ``TestTimeoutSummaryHasNoSignInHint``
- Tasks in one wave share a working copy, so a report rebuilt from git
  credited one task with its neighbour's files.
  -> ``TestSharedWorkingCopyIsNotEvidence``

The fixtures are trimmed copies of that build's records with neutral names.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

import guardkit.orchestrator.agent_invoker as agent_invoker_module
from guardkit.orchestrator.agent_invoker import AgentInvocationResult, AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, TurnRecord
from guardkit.orchestrator.exceptions import SDKTimeoutError
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.state_detection import GitChangesSummary
from guardkit.orchestrator.state_tracker import MultiLayeredStateTracker, WorkState
from guardkit.orchestrator.synthetic_report import (
    PLAYER_NO_OWN_REPORT_CATEGORY,
    PLAYER_TIMED_OUT_CATEGORY,
    SHARED_WORKING_COPY_CONCERN,
    SHARED_WORKING_COPY_FIELD,
    is_failure_placeholder,
)

TASK_A = "TASK-DMT-002"
TASK_B = "TASK-DMT-003"

# Acceptance criteria shaped like the build's documentation task.
CRITERIA = [
    "AC-001: docs/widgets.md describes the remove-widget endpoint.",
    "AC-002: docs/widgets.md lists the 204 and 404 responses.",
]


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """A git working copy with one commit, as a feature worktree has."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "builder@example.invalid")
    _git(tmp_path, "config", "user.name", "builder")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "widgets.md").write_text("# Widgets\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("app = None\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _create_task_file(worktree: Path, task_id: str, complexity: int) -> None:
    tasks_dir = worktree / "tasks" / "backlog"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / f"{task_id}-document-remove-widget.md").write_text(
        "---\n"
        f"id: {task_id}\n"
        "title: Document the remove-widget endpoint\n"
        "status: backlog\n"
        f"complexity: {complexity}\n"
        "implementation_mode: direct\n"
        "task_type: documentation\n"
        "---\n\n# Document the remove-widget endpoint\n\n"
        "## Acceptance Criteria\n\n"
        + "".join(f"- [ ] {c}\n" for c in CRITERIA)
    )


def _invoker(worktree: Path, **kwargs: Any) -> AgentInvoker:
    """An invoker configured as the live factory runs: base 1800 s, scaled."""
    return AgentInvoker(
        worktree_path=worktree,
        sdk_timeout_seconds=1800,
        sdk_timeout_is_override=False,
        timeout_multiplier=1.0,
        **kwargs,
    )


def _placeholder(task_id: str, turn: int, seconds: int) -> Dict[str, Any]:
    """The placeholder report exactly as build FEAT-2C42 left it."""
    return {
        "task_id": task_id,
        "turn": turn,
        "files_modified": [],
        "files_created": [],
        "tests_written": [],
        "tests_run": False,
        "tests_passed": False,
        "test_output_summary": "",
        "implementation_notes": "Direct mode implementation via SDK",
        "concerns": [],
        "requirements_addressed": [],
        "requirements_remaining": [],
        "implementation_mode": "direct",
        "error": f"SDK timeout: Agent invocation exceeded {seconds}s timeout",
        "success": False,
    }


def _write_player_report(worktree: Path, task_id: str, turn: int, report: Dict) -> None:
    report_dir = worktree / ".guardkit" / "autobuild" / task_id
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"player_turn_{turn}.json").write_text(json.dumps(report))


def _orchestrator(
    repo_root: Path, wave_size: int = 1, shares_working_copy: bool = False
) -> AutoBuildOrchestrator:
    return AutoBuildOrchestrator(
        repo_root=repo_root, enable_pre_loop=False, wave_size=wave_size,
        shares_working_copy=shares_working_copy,
    )


class _FakeWorktree:
    def __init__(self, path: Path) -> None:
        self.path = path


# ---------------------------------------------------------------------------
# 1. Direct mode gets the same time as task-work, within the task's budget
# ---------------------------------------------------------------------------


class TestDirectModeTimeBudget:
    @pytest.fixture(autouse=True)
    def _live_caps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The live configuration: base 1800 s, so the finite cap is 5400 s.
        monkeypatch.setattr(agent_invoker_module, "DEFAULT_SDK_TIMEOUT", 1800)
        monkeypatch.setattr(agent_invoker_module, "MAX_SDK_TIMEOUT", 5400)

    def test_direct_mode_gets_one_and_a_half_times(self, worktree: Path) -> None:
        # The build's tasks: complexity 3 was allowed 2340 s, complexity 2
        # 2160 s. Both are now scaled like task-work.
        _create_task_file(worktree, TASK_A, complexity=3)
        _create_task_file(worktree, TASK_B, complexity=2)
        invoker = _invoker(worktree)

        assert invoker._calculate_sdk_timeout(TASK_A, remaining_budget=10799) == 3510
        assert invoker._calculate_sdk_timeout(TASK_B, remaining_budget=10799) == 3240

    def test_matches_task_work_for_the_same_complexity(self, worktree: Path) -> None:
        _create_task_file(worktree, TASK_A, complexity=5)
        direct = _invoker(worktree)._calculate_sdk_timeout(TASK_A)
        assert direct == 4050  # 1800 * 1.5 * 1.5, as task-work gets

    def test_never_exceeds_the_cap_or_the_task_budget(self, worktree: Path) -> None:
        _create_task_file(worktree, TASK_A, complexity=10)
        invoker = _invoker(worktree)

        # 1800 * 1.5 * 2.0 = 5400: at the finite cap, under the 10800 s task budget.
        assert invoker._calculate_sdk_timeout(TASK_A, remaining_budget=10800) == 5400
        assert invoker._calculate_sdk_timeout(TASK_A) <= 10800
        # What is left of the task's budget still caps the turn.
        assert invoker._calculate_sdk_timeout(TASK_A, remaining_budget=2000) == 2000


# ---------------------------------------------------------------------------
# 2. The timeout placeholder is not the Player's report; git is used instead
# ---------------------------------------------------------------------------


class TestPlaceholderIsNotThePlayersReport:
    def test_timeout_writes_a_placeholder_with_its_timings(self, worktree: Path) -> None:
        """The real timeout branch writes the placeholder, now with timings."""
        _create_task_file(worktree, TASK_A, complexity=3)
        invoker = _invoker(worktree)
        invoker.sdk_timeout_seconds = 3510

        with patch.object(
            invoker, "_invoke_with_role",
            new=AsyncMock(side_effect=SDKTimeoutError(
                "Agent invocation exceeded 3510s timeout"
            )),
        ), patch.object(invoker, "_build_player_prompt", return_value="prompt"):
            result = asyncio.run(
                invoker._invoke_player_direct(TASK_A, 1, "requirements")
            )

        assert result.success is False
        assert result.report["timed_out"] is True
        assert result.report["timeout_seconds"] == 3510

        written = json.loads(
            (worktree / ".guardkit/autobuild" / TASK_A / "player_turn_1.json").read_text()
        )
        assert is_failure_placeholder(written)
        assert written["timed_out"] is True
        assert written["timeout_seconds"] == 3510
        assert "elapsed_seconds" in written

    def test_placeholder_is_ignored_in_favour_of_git(self, worktree: Path) -> None:
        # The coder changed files, then ran out of time before its report.
        (worktree / "docs" / "widgets.md").write_text("# Widgets\n\nRemove a widget.\n")
        (worktree / "src" / "app.py").write_text("app = 'changed'\n")
        (worktree / "docs" / "remove-widget.md").write_text("# Remove\n")
        _write_player_report(worktree, TASK_A, 1, _placeholder(TASK_A, 1, 2340))

        tracker = MultiLayeredStateTracker(task_id=TASK_A, worktree_path=worktree)
        with patch(
            "guardkit.orchestrator.state_tracker.detect_test_results",
            return_value=None,
        ):
            state = tracker.capture_state(turn=1)

        assert state is not None
        assert state.detection_method != "player_report"
        assert state.player_report_loaded is False
        assert set(state.files_modified) >= {"docs/widgets.md", "src/app.py"}
        assert "docs/remove-widget.md" in state.files_created
        assert state.has_work

    def test_a_real_report_is_still_trusted(self, worktree: Path) -> None:
        (worktree / "docs" / "widgets.md").write_text("# Widgets\n\nRemove.\n")
        report = _placeholder(TASK_A, 1, 2340)
        report.pop("error")
        report["success"] = True
        report["files_modified"] = ["docs/widgets.md"]
        _write_player_report(worktree, TASK_A, 1, report)

        tracker = MultiLayeredStateTracker(task_id=TASK_A, worktree_path=worktree)
        with patch(
            "guardkit.orchestrator.state_tracker.detect_test_results",
            return_value=None,
        ):
            state = tracker.capture_state(turn=1)

        assert state.detection_method == "player_report"
        assert state.files_modified == ["docs/widgets.md"]


# ---------------------------------------------------------------------------
# 3. The gate says the turn ran out of time, as a must-fix with a suggestion
# ---------------------------------------------------------------------------


def _direct_results(task_id: str) -> Dict[str, Any]:
    """The task_work_results the recovery wrote: relaxed gates, no promises."""
    return {
        "task_id": task_id,
        "implementation_mode": "direct",
        "completed": True,
        "success": True,
        "quality_gates": {"all_passed": True, "quality_gates_relaxed": True},
        "files_created": [],
        "files_modified": [],
        "tests_written": [],
        "completion_promises": [],
        "requirements_addressed": [],
    }


def _recovered_timeout_report(task_id: str, seconds: int) -> Dict[str, Any]:
    """The report recovery handed the Coach after a timeout."""
    return {
        "task_id": task_id,
        "_synthetic": True,
        "files_modified": [],
        "files_created": [],
        "_recovery_metadata": {
            "detection_method": "git_test_detection",
            "original_error": (
                f"SDK timeout after {seconds}s: Agent invocation exceeded "
                f"{seconds}s timeout"
            ),
            "timed_out": True,
            "timeout_seconds": seconds,
            "elapsed_seconds": seconds + 1,
        },
    }


class TestTimeoutReachesMustFix:
    def _gate_feedback(self, worktree: Path, player_report: Dict) -> Any:
        results_dir = worktree / ".guardkit" / "autobuild" / TASK_A
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "task_work_results.json").write_text(
            json.dumps(_direct_results(TASK_A))
        )
        orch = _orchestrator(worktree)
        validator = CoachValidator(str(worktree), task_id=TASK_A)
        return orch._direct_mode_evidence_gate(
            validator, TASK_A, 1, _FakeWorktree(worktree), 0.0,
            acceptance_criteria=CRITERIA, task_type="documentation",
            player_report=player_report,
        ), orch

    def test_timeout_is_the_first_must_fix_with_a_suggestion(
        self, worktree: Path
    ) -> None:
        result, orch = self._gate_feedback(
            worktree, _recovered_timeout_report(TASK_A, 2340)
        )
        assert result is not None and result.report["decision"] == "feedback"
        first = result.report["issues"][0]
        assert first["category"] == PLAYER_TIMED_OUT_CATEGORY
        assert first["severity"] == "must_fix"
        assert "ran out of time after 2340 s" in first["description"]
        assert "player_turn_1.json" in first["description"]
        assert first["suggestion"]

        # Through the text the Player is given, into the feedback file.
        text = orch._extract_feedback(result.report)
        structured = _invoker(worktree)._parse_coach_feedback(text, 2)
        must_fix = structured["must_fix"]
        assert must_fix, "the timeout must reach must_fix"
        assert "ran out of time after 2340 s" in must_fix[0]["issue"]
        assert "player_turn_1.json" in must_fix[0]["issue"]
        assert must_fix[0]["suggestion"] == (
            "Write the report as soon as the work is done, before any long "
            "test run."
        )
        # The criteria block still follows it.
        assert any("Direct-mode evidence gate" in m["issue"] for m in must_fix)

    def test_no_timeout_issue_when_the_coder_wrote_its_report(
        self, worktree: Path
    ) -> None:
        result, _ = self._gate_feedback(worktree, {"task_id": TASK_A})
        assert result is not None
        categories = [i.get("category") for i in result.report["issues"]]
        assert PLAYER_TIMED_OUT_CATEGORY not in categories
        assert len(result.report["issues"]) == 1

    def test_shared_copy_without_report_is_explained(self, worktree: Path) -> None:
        report = {"task_id": TASK_A, "_synthetic": True, SHARED_WORKING_COPY_FIELD: True}
        result, _ = self._gate_feedback(worktree, report)
        first = result.report["issues"][0]
        assert first["category"] == PLAYER_NO_OWN_REPORT_CATEGORY
        assert first["suggestion"]


# ---------------------------------------------------------------------------
# 4. The final summary says it ran out of time, with no sign-in or SDK hint
# ---------------------------------------------------------------------------


def _turn(turn: int, player_result: AgentInvocationResult) -> TurnRecord:
    return TurnRecord(
        turn=turn,
        player_result=player_result,
        coach_result=None,
        decision="feedback",
        feedback=None,
        timestamp="2026-10-08T08:40:00Z",
    )


class TestTimeoutSummaryHasNoSignInHint:
    def test_recovered_timeouts_are_named_with_timings(self, worktree: Path) -> None:
        # As in the build: every turn ran out of time and was rebuilt from git.
        history = [
            _turn(n, AgentInvocationResult(
                task_id=TASK_A, turn=n, agent_type="player", success=True,
                report=_recovered_timeout_report(TASK_A, 2340),
                duration_seconds=0.0,
            ))
            for n in (1, 2, 3)
        ]
        text = _orchestrator(worktree)._build_summary_details(
            history, "player_invocation_stall"
        )

        assert "ran out of time" in text
        assert "allowed 2340 s" in text and "ran 2341 s" in text
        assert "turns: 1, 2, 3" in text
        lowered = text.lower()
        assert "login" not in lowered and "auth" not in lowered
        assert "claude-agent-sdk" not in lowered
        assert "'player_report'" not in text

    def test_unrecovered_timeout_is_named_too(self, worktree: Path) -> None:
        history = [
            _turn(n, AgentInvocationResult(
                task_id=TASK_A, turn=n, agent_type="player", success=False,
                report={"timed_out": True, "timeout_seconds": 2160,
                        "elapsed_seconds": 2160},
                duration_seconds=2160.0,
                error="SDK timeout after 2160s: Agent invocation exceeded 2160s timeout",
            ))
            for n in (1, 2, 3)
        ]
        text = _orchestrator(worktree)._build_summary_details(
            history, "player_invocation_stall"
        )
        assert "allowed 2160 s" in text
        assert "login" not in text.lower()

    def test_other_failures_keep_their_existing_checks(self, worktree: Path) -> None:
        history = [
            _turn(n, AgentInvocationResult(
                task_id=TASK_A, turn=n, agent_type="player", success=False,
                report={}, duration_seconds=1.0,
                error="SDK API error in stream: unknown",
            ))
            for n in (1, 2, 3)
        ]
        text = _orchestrator(worktree)._build_summary_details(
            history, "player_invocation_stall"
        )
        assert "SDK API error in stream" in text
        assert "ran out of time" not in text


# ---------------------------------------------------------------------------
# 5. A report rebuilt from a shared working copy is not this task's evidence
# ---------------------------------------------------------------------------


def _work_state(files_modified: List[str], files_created: List[str]) -> WorkState:
    """Git's view after two tasks in one wave both changed the working copy."""
    return WorkState(
        turn_number=1,
        files_modified=files_modified,
        files_created=files_created,
        test_count=12,
        git_changes=GitChangesSummary(
            files_modified=files_modified, files_added=files_created,
            files_deleted=[], diff_stats="", insertions=40, deletions=2,
        ),
        detection_method="git_test_detection",
    )


class TestSharedWorkingCopyIsNotEvidence:
    # Task A documents the endpoint; task B (same wave) wrote the docs files.
    # Git cannot tell them apart.
    FILES_MODIFIED = ["docs/widgets.md"]
    FILES_CREATED = ["docs/remove-widget.md", "tests/test_widget_docs.py"]

    def test_rebuilt_report_in_a_concurrent_wave_carries_no_evidence(
        self, worktree: Path
    ) -> None:
        orch = _orchestrator(worktree, wave_size=2, shares_working_copy=True)
        report = orch._build_synthetic_report(
            _work_state(self.FILES_MODIFIED, self.FILES_CREATED),
            "SDK timeout after 2160s: Agent invocation exceeded 2160s timeout",
            acceptance_criteria=CRITERIA,
            task_type="documentation",
            worktree_path=worktree,
        )

        assert report[SHARED_WORKING_COPY_FIELD] is True
        assert not report.get("completion_promises")
        assert report["requirements_addressed"] == []
        assert SHARED_WORKING_COPY_CONCERN in report["concerns"]
        # What git saw is still listed, for whoever reads the report.
        assert report["files_created"] == self.FILES_CREATED

    def test_single_task_wave_still_uses_git_evidence(self, worktree: Path) -> None:
        orch = _orchestrator(worktree, wave_size=1)
        report = orch._build_synthetic_report(
            _work_state(self.FILES_MODIFIED, self.FILES_CREATED),
            "SDK timeout after 2160s: Agent invocation exceeded 2160s timeout",
            acceptance_criteria=CRITERIA,
            task_type="documentation",
            worktree_path=worktree,
        )
        assert SHARED_WORKING_COPY_FIELD not in report
        assert report.get("completion_promises")

    def test_recovery_keeps_the_timeout_in_the_rebuilt_report(
        self, worktree: Path
    ) -> None:
        (worktree / "docs" / "widgets.md").write_text("# Widgets\n\nRemove.\n")
        _write_player_report(worktree, TASK_B, 1, _placeholder(TASK_B, 1, 2160))
        orch = _orchestrator(worktree, wave_size=2, shares_working_copy=True)
        with patch(
            "guardkit.orchestrator.state_tracker.detect_test_results",
            return_value=None,
        ):
            recovered = orch._attempt_state_recovery(
                task_id=TASK_B, turn=1, worktree=_FakeWorktree(worktree),
                original_error=(
                    "SDK timeout after 2160s: Agent invocation exceeded 2160s timeout"
                ),
                acceptance_criteria=CRITERIA, task_type="documentation",
                player_report={"timed_out": True, "timeout_seconds": 2160,
                               "elapsed_seconds": 2161},
            )

        assert recovered is not None
        report = recovered.report
        assert report["files_modified"] == ["docs/widgets.md"]
        assert report[SHARED_WORKING_COPY_FIELD] is True
        metadata = report["_recovery_metadata"]
        assert metadata["timed_out"] is True
        assert metadata["timeout_seconds"] == 2160

    def test_invoker_rebuilt_report_in_a_wave_is_marked(self, worktree: Path) -> None:
        """The coder finished but wrote no report; the invoker built one."""
        _create_task_file(worktree, TASK_A, complexity=3)
        (worktree / "docs" / "widgets.md").write_text("# Widgets\n\nRemove a widget.\n")
        (worktree / "docs" / "remove-widget.md").write_text("# Remove a widget\n204 404\n")

        invoker = _invoker(worktree)
        invoker.shared_working_copy = True
        report = invoker._create_synthetic_direct_mode_report(
            TASK_A, 2, acceptance_criteria=CRITERIA, task_type="documentation"
        )
        assert report[SHARED_WORKING_COPY_FIELD] is True
        assert report["requirements_addressed"] == []
        assert not report.get("completion_promises")

        # The marker survives into player_turn_N.json, where the gate reads it.
        path = invoker._write_player_report_for_direct_mode(TASK_A, 2, report)
        assert json.loads(path.read_text())[SHARED_WORKING_COPY_FIELD] is True

    @pytest.mark.parametrize("shares", [True, False])
    def test_orchestrator_tells_the_invoker_about_the_wave(
        self, worktree: Path, shares: bool
    ) -> None:
        orch = AutoBuildOrchestrator(
            repo_root=worktree, enable_pre_loop=False, wave_size=2,
            shares_working_copy=shares,
            existing_worktree=_FakeWorktree(worktree),
        )
        orch._setup_phase(TASK_A, "main")
        assert orch._agent_invoker.shared_working_copy is shares


class TestWaveRunOneAtATimeKeepsItsCredit:
    """Coach finding, 8 October 2026: a wave of two run one task at a time
    (max_parallel 1, or tasks on the same area) is not a shared working copy.
    Each task measures git from its own starting commit, so its rebuilt
    report keeps its promises and requirements (as build FEAT-DB3D's wave 2
    did: 2 promises and 3 requirements on a turn with no coder report)."""

    def test_recovery_rebuilt_report_keeps_promises(self, worktree: Path) -> None:
        orch = _orchestrator(worktree, wave_size=2, shares_working_copy=False)
        report = orch._build_synthetic_report(
            _work_state(["docs/widgets.md"], ["docs/remove-widget.md"]),
            "SDK timeout after 2160s: Agent invocation exceeded 2160s timeout",
            acceptance_criteria=CRITERIA,
            task_type="documentation",
            worktree_path=worktree,
        )
        assert SHARED_WORKING_COPY_FIELD not in report
        assert report.get("completion_promises")

    def test_invoker_rebuilt_report_keeps_requirements(self, worktree: Path) -> None:
        _create_task_file(worktree, TASK_A, complexity=3)
        (worktree / "docs" / "widgets.md").write_text(
            "# Widgets\n\nThis page describes the remove-widget endpoint.\n"
            "It lists the 204 and 404 responses.\n"
        )

        def build(shared: bool) -> Dict[str, Any]:
            invoker = _invoker(worktree)
            invoker.shared_working_copy = shared
            return invoker._create_synthetic_direct_mode_report(
                TASK_A, 5, acceptance_criteria=CRITERIA, task_type="documentation"
            )

        alone = build(False)
        assert SHARED_WORKING_COPY_FIELD not in alone
        # The text-matching fallback's list is kept.
        assert alone["requirements_addressed"]
        # The same tree, really shared, carries none.
        assert build(True)["requirements_addressed"] == []

    @pytest.mark.parametrize(
        "tasks_to_run, max_parallel, expected",
        [
            (2, 1, False),     # one at a time
            (2, None, True),   # unlimited
            (2, 0, True),      # zero means unlimited
            (3, 2, True),
            (1, None, False),  # only one task actually runs
        ],
    )
    def test_concurrency_rule(self, tasks_to_run, max_parallel, expected) -> None:
        from guardkit.orchestrator.parallel_strategy import tasks_run_at_the_same_time

        assert tasks_run_at_the_same_time(tasks_to_run, max_parallel) is expected


class TestTimeoutWordsAreNarrow:
    def test_only_the_factorys_timeout_words_count(self) -> None:
        from guardkit.orchestrator.synthetic_report import player_timeout_from_error

        assert player_timeout_from_error(
            "SDK timeout after 2340s: Agent invocation exceeded 2340s timeout"
        ) == {"timed_out": True, "timeout_seconds": 2340}
        assert player_timeout_from_error(
            "task-work execution exceeded 4050s timeout"
        )["timeout_seconds"] == 4050
        assert player_timeout_from_error("ReadTimeout: model server read timeout") is None
        assert player_timeout_from_error("SDK API error in stream: unknown") is None
        assert player_timeout_from_error(None) is None


# ---------------------------------------------------------------------------
# Second round (coordinator review, 8 October 2026): the same family of gaps
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, Mock  # noqa: E402

from guardkit.orchestrator.synthetic_report import (  # noqa: E402
    PLAYER_NO_REPORT_NO_CHANGES_CATEGORY,
)

TIMEOUT_ERROR = "SDK timeout after 2340s: Agent invocation exceeded 2340s timeout"
TIMEOUT_SUGGESTION = (
    "Write the report as soon as the work is done, before any long test run."
)


def _mocked_orchestrator(worktree: Path) -> tuple:
    """An orchestrator whose coder and reviewer are stand-ins."""
    invoker = Mock()
    invoker.invoke_player = AsyncMock()
    invoker.invoke_coach = AsyncMock()
    invoker._get_implementation_mode.return_value = "direct"
    display = MagicMock()
    manager = Mock()
    manager.worktrees_dir = worktree
    orch = AutoBuildOrchestrator(
        repo_root=worktree,
        max_turns=5,
        worktree_manager=manager,
        agent_invoker=invoker,
        progress_display=display,
        enable_pre_loop=False,
        enable_checkpoints=False,
    )
    return orch, invoker


def _reviewer_feedback() -> AgentInvocationResult:
    """The model reviewer's feedback: it knows nothing about the timeout."""
    return AgentInvocationResult(
        task_id=TASK_A, turn=1, agent_type="coach", success=True,
        report={
            "decision": "feedback",
            "issues": [{
                "severity": "major",
                "category": "missing_requirement",
                "description": "docs/widgets.md does not list the 404 response",
                "suggestion": "Add the 404 response to docs/widgets.md",
            }],
            "rationale": "One criterion is not met.",
        },
        duration_seconds=1.0,
    )


def _timed_out_player() -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=TASK_A, turn=1, agent_type="player", success=False,
        report={"timed_out": True, "timeout_seconds": 2340, "elapsed_seconds": 2341},
        duration_seconds=2341.0, error=TIMEOUT_ERROR,
    )


def _run_turn(orch, worktree: Path, *, recovered, coach=None):
    patches = [patch.object(orch, "_attempt_state_recovery", return_value=recovered)]
    if coach is not None:
        patches.append(patch.object(orch, "_invoke_coach_safely", return_value=coach))
    for p in patches:
        p.start()
    try:
        return orch._execute_turn(
            turn=1, task_id=TASK_A, requirements="Document the endpoint",
            worktree=_FakeWorktree(worktree), previous_feedback=None,
        )
    finally:
        for p in patches:
            p.stop()


class TestTimeoutNoteOnEveryPath:
    def test_reviewer_feedback_gets_the_timeout_must_fix(self, worktree: Path) -> None:
        orch, invoker = _mocked_orchestrator(worktree)
        invoker.invoke_player.return_value = _timed_out_player()
        recovered = AgentInvocationResult(
            task_id=TASK_A, turn=1, agent_type="player", success=True,
            report=_recovered_timeout_report(TASK_A, 2340), duration_seconds=0.0,
        )

        record = _run_turn(orch, worktree, recovered=recovered, coach=_reviewer_feedback())

        assert record.decision == "feedback"
        assert record.feedback.startswith(
            "- MUST FIX: Your last turn ran out of time after 2340 s"
        )
        must_fix = _invoker(worktree)._parse_coach_feedback(record.feedback, 2)["must_fix"]
        assert "ran out of time after 2340 s" in must_fix[0]["issue"]
        assert "player_turn_1.json" in must_fix[0]["issue"]
        assert must_fix[0]["suggestion"] == TIMEOUT_SUGGESTION
        # The reviewer's own issue still follows, with its suggestion.
        assert must_fix[1]["issue"] == "docs/widgets.md does not list the 404 response"
        assert must_fix[1]["suggestion"] == "Add the 404 response to docs/widgets.md"

    def test_said_once_when_the_gate_already_said_it(self, worktree: Path) -> None:
        orch, invoker = _mocked_orchestrator(worktree)
        invoker.invoke_player.return_value = _timed_out_player()
        recovered = AgentInvocationResult(
            task_id=TASK_A, turn=1, agent_type="player", success=True,
            report=_recovered_timeout_report(TASK_A, 2340), duration_seconds=0.0,
        )
        coach = _reviewer_feedback()
        coach.report["issues"].insert(
            0, player_timed_out_issue_for_test(TASK_A, 1, 2340)
        )

        record = _run_turn(orch, worktree, recovered=recovered, coach=coach)
        assert record.feedback.count("ran out of time") == 1

    def test_no_note_when_the_turn_did_not_time_out(self, worktree: Path) -> None:
        orch, invoker = _mocked_orchestrator(worktree)
        invoker.invoke_player.return_value = AgentInvocationResult(
            task_id=TASK_A, turn=1, agent_type="player", success=True,
            report={"task_id": TASK_A, "files_modified": ["docs/widgets.md"],
                    "files_created": [], "tests_written": []},
            duration_seconds=900.0,
        )
        record = _run_turn(orch, worktree, recovered=None, coach=_reviewer_feedback())
        assert "ran out of time" not in record.feedback


def player_timed_out_issue_for_test(task_id: str, turn: int, seconds: int) -> Dict:
    from guardkit.orchestrator.synthetic_report import player_timed_out_issue

    return player_timed_out_issue(
        task_id, turn, {"timed_out": True, "timeout_seconds": seconds}
    )


class TestNothingRecoveredStillSaysWhatHappened:
    def test_timeout_with_nothing_found_gives_timings(self, worktree: Path) -> None:
        orch, invoker = _mocked_orchestrator(worktree)
        invoker.invoke_player.return_value = _timed_out_player()

        record = _run_turn(orch, worktree, recovered=None)

        assert record.decision == "error"
        must_fix = _invoker(worktree)._parse_coach_feedback(record.feedback, 2)["must_fix"]
        assert len(must_fix) == 1
        assert "ran out of time (allowed 2340 s, ran 2341 s)" in must_fix[0]["issue"]
        assert "found no changes" in must_fix[0]["issue"]
        assert must_fix[0]["suggestion"] == TIMEOUT_SUGGESTION

    def test_other_failure_with_nothing_found(self, worktree: Path) -> None:
        orch, invoker = _mocked_orchestrator(worktree)
        invoker.invoke_player.return_value = AgentInvocationResult(
            task_id=TASK_A, turn=1, agent_type="player", success=False,
            report={}, duration_seconds=12.0,
            error="Player report not found at the expected path",
        )

        record = _run_turn(orch, worktree, recovered=None)

        assert record.decision == "error"
        must_fix = _invoker(worktree)._parse_coach_feedback(record.feedback, 2)["must_fix"]
        assert len(must_fix) == 1
        assert "ended without writing its report (player_turn_1.json)" in must_fix[0]["issue"]
        assert "found no changes" in must_fix[0]["issue"]
        assert "Player report not found" in must_fix[0]["issue"]
        assert must_fix[0]["suggestion"]
        assert "ran out of time" not in record.feedback

    def test_the_next_turn_starts_from_it(self, worktree: Path) -> None:
        """A resumed run takes its first feedback from the saved last turn."""
        orch, invoker = _mocked_orchestrator(worktree)
        invoker.invoke_player.return_value = _timed_out_player()
        record = _run_turn(orch, worktree, recovered=None)

        orch._turn_history = [record]
        resumed, _ = _mocked_orchestrator(worktree)
        resumed._turn_history = resumed._deserialize_turn_history(
            orch._serialize_turn_history()
        )
        assert resumed._get_last_feedback() == record.feedback
        assert "ran out of time" in resumed._get_last_feedback()


def _stall_history() -> List[TurnRecord]:
    return [
        _turn(n, AgentInvocationResult(
            task_id=TASK_A, turn=n, agent_type="player", success=False,
            report={}, duration_seconds=1.0,
            error="SDK API error in stream: unknown",
        ))
        for n in (1, 2, 3)
    ]


class TestSignInHintOnlyForAnthropicSdkRuns:
    @pytest.mark.parametrize(
        "harness, base_url, expect_hint",
        [
            ("langgraph", None, False),                       # the factory's local default
            ("langgraph", "https://api.anthropic.com", False),  # harness decides
            ("sdk", "http://localhost:8000", False),           # SDK on a local server
            ("sdk", "http://10.0.0.5:4000/v1", False),         # SDK on a LAN server
            ("sdk", None, True),                               # Anthropic through the SDK
            ("sdk", "https://api.anthropic.com", True),
        ],
    )
    def test_hint_follows_the_configured_provider(
        self, worktree: Path, monkeypatch: pytest.MonkeyPatch,
        harness: str, base_url: Optional[str], expect_hint: bool,
    ) -> None:
        monkeypatch.setenv("GUARDKIT_HARNESS", harness)
        if base_url is None:
            monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        else:
            monkeypatch.setenv("ANTHROPIC_BASE_URL", base_url)

        text = _orchestrator(worktree)._build_summary_details(
            _stall_history(), "player_invocation_stall"
        )
        has_hint = "claude login" in text or "claude-agent-sdk" in text
        assert has_hint is expect_hint
        assert "SDK API error in stream" in text

    def test_timeout_stall_never_has_it_even_on_anthropic(
        self, worktree: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        history = [
            _turn(n, AgentInvocationResult(
                task_id=TASK_A, turn=n, agent_type="player", success=True,
                report=_recovered_timeout_report(TASK_A, 2340), duration_seconds=0.0,
            ))
            for n in (1, 2, 3)
        ]
        text = _orchestrator(worktree)._build_summary_details(
            history, "player_invocation_stall"
        )
        assert "claude login" not in text and "claude-agent-sdk" not in text


class TestGateItemKeepsItsDetails:
    def _gate(self, worktree: Path, criteria: List[str]) -> Any:
        results_dir = worktree / ".guardkit" / "autobuild" / TASK_A
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "task_work_results.json").write_text(
            json.dumps(_direct_results(TASK_A))
        )
        orch = _orchestrator(worktree)
        validator = CoachValidator(str(worktree), task_id=TASK_A)
        result = orch._direct_mode_evidence_gate(
            validator, TASK_A, 2, _FakeWorktree(worktree), 0.0,
            acceptance_criteria=criteria, task_type="documentation",
            player_report={"task_id": TASK_A},
        )
        return orch, result

    def test_unmet_criteria_and_suggestion_reach_the_coder(self, worktree: Path) -> None:
        orch, result = self._gate(worktree, CRITERIA)
        text = orch._extract_feedback(result.report)
        must_fix = _invoker(worktree)._parse_coach_feedback(text, 3)["must_fix"]

        assert len(must_fix) == 1
        item = must_fix[0]
        assert "Direct-mode evidence gate blocked the turn" in item["issue"]
        # The detail line survives: which criteria are unmet.
        assert "[direct_mode_ac_unverified]" in item["issue"]
        assert "AC-001" in item["issue"] and "AC-002" in item["issue"]
        assert item["suggestion"] == (
            "List a completion promise for each acceptance criterion "
            "(criterion_id, status, evidence) in player_turn_3.json."
        )

    def test_the_unmet_list_is_bounded(self, worktree: Path) -> None:
        many = [f"AC-{n:03d}: section {n} of docs/widgets.md is written." for n in range(1, 31)]
        orch, result = self._gate(worktree, many)
        text = orch._extract_feedback(result.report)
        item = _invoker(worktree)._parse_coach_feedback(text, 3)["must_fix"][0]
        assert "AC-010" in item["issue"]
        assert "AC-011" not in item["issue"]
        assert "and 20 more" in item["issue"]
        assert item["suggestion"]


# ---------------------------------------------------------------------------
# Coach finding 2: task-work turns get task-work wording, said once
# ---------------------------------------------------------------------------

TASK_WORK_TIMEOUT = "task-work execution exceeded 4050s timeout"


def _task_work_orchestrator(worktree: Path) -> tuple:
    orch, invoker = _mocked_orchestrator(worktree)
    invoker._get_implementation_mode.return_value = "task-work"
    invoker.invoke_player.return_value = AgentInvocationResult(
        task_id=TASK_A, turn=2, agent_type="player", success=False,
        report={}, duration_seconds=4050.0, error=TASK_WORK_TIMEOUT,
    )
    return orch, invoker


class TestTaskWorkTimeoutWording:
    def test_partial_work_and_reviewer_feedback_say_it_once(
        self, worktree: Path
    ) -> None:
        orch, _ = _task_work_orchestrator(worktree)
        recovered = AgentInvocationResult(
            task_id=TASK_A, turn=2, agent_type="player", success=True,
            report={
                "task_id": TASK_A, "_synthetic": True,
                "files_modified": ["docs/widgets.md"], "files_created": [],
                "tests_written": [],
                "_recovery_metadata": {
                    "detection_method": "git_test_detection",
                    "original_error": TASK_WORK_TIMEOUT,
                    "timed_out": True, "timeout_seconds": 4050,
                },
            },
            duration_seconds=0.0,
        )
        with patch.object(orch, "_attempt_state_recovery", return_value=recovered), \
                patch.object(orch, "_invoke_coach_safely", return_value=_reviewer_feedback()):
            record = orch._execute_turn(
                turn=2, task_id=TASK_A, requirements="Document the endpoint",
                worktree=_FakeWorktree(worktree), previous_feedback=None,
            )

        assert record.decision == "feedback"
        assert record.feedback.count("timed out") + record.feedback.count(
            "ran out of time"
        ) == 1
        assert "The task-work Player attempt timed out" in record.feedback
        assert "player_turn_" not in record.feedback
        assert "before any long test run" not in record.feedback

    def test_nothing_recovered_gets_task_work_wording(self, worktree: Path) -> None:
        orch, _ = _task_work_orchestrator(worktree)
        with patch.object(orch, "_attempt_state_recovery", return_value=None):
            record = orch._execute_turn(
                turn=2, task_id=TASK_A, requirements="Document the endpoint",
                worktree=_FakeWorktree(worktree), previous_feedback=None,
            )

        assert record.decision == "error"
        must_fix = _invoker(worktree)._parse_coach_feedback(record.feedback, 3)["must_fix"]
        assert len(must_fix) == 1
        assert "task-work attempt ran out of time (allowed 4050 s)" in must_fix[0]["issue"]
        assert "found no changes" in must_fix[0]["issue"]
        assert must_fix[0]["suggestion"]
        assert "player_turn_" not in record.feedback
        assert "before any long test run" not in record.feedback

    def test_task_work_other_failure_with_nothing_recovered(self, worktree: Path) -> None:
        orch, invoker = _task_work_orchestrator(worktree)
        invoker.invoke_player.return_value = AgentInvocationResult(
            task_id=TASK_A, turn=2, agent_type="player", success=False,
            report={}, duration_seconds=30.0, error="task-work exited with code 1",
        )
        with patch.object(orch, "_attempt_state_recovery", return_value=None):
            record = orch._execute_turn(
                turn=2, task_id=TASK_A, requirements="Document the endpoint",
                worktree=_FakeWorktree(worktree), previous_feedback=None,
            )
        must_fix = _invoker(worktree)._parse_coach_feedback(record.feedback, 3)["must_fix"]
        assert "task-work attempt failed" in must_fix[0]["issue"]
        assert "task-work exited with code 1" in must_fix[0]["issue"]
        assert "player_turn_" not in record.feedback


# ---------------------------------------------------------------------------
# Independent review, round 1: the reviewer-failed path and the overridden
# approval
# ---------------------------------------------------------------------------


def _failed_reviewer() -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=TASK_A, turn=1, agent_type="coach", success=False,
        report={}, duration_seconds=600.0,
        error="Coach invocation exceeded 600s timeout",
    )


def _resumed_feedback(orch, record) -> Optional[str]:
    """What a resumed run's first turn is given, via the saved history."""
    orch._turn_history = [record]
    resumed, _ = _mocked_orchestrator(Path(orch.repo_root))
    resumed._turn_history = resumed._deserialize_turn_history(
        orch._serialize_turn_history()
    )
    return resumed._get_last_feedback()


class TestReviewerFailureKeepsTheTimeoutNote:
    def test_direct_mode(self, worktree: Path) -> None:
        orch, invoker = _mocked_orchestrator(worktree)
        invoker.invoke_player.return_value = _timed_out_player()
        recovered = AgentInvocationResult(
            task_id=TASK_A, turn=1, agent_type="player", success=True,
            report=_recovered_timeout_report(TASK_A, 2340), duration_seconds=0.0,
        )

        record = _run_turn(orch, worktree, recovered=recovered, coach=_failed_reviewer())

        assert record.decision == "error"
        resumed = _resumed_feedback(orch, record)
        must_fix = _invoker(worktree)._parse_coach_feedback(resumed, 2)["must_fix"]
        assert len(must_fix) == 1
        assert "ran out of time after 2340 s" in must_fix[0]["issue"]
        assert "player_turn_1.json" in must_fix[0]["issue"]
        assert must_fix[0]["suggestion"] == TIMEOUT_SUGGESTION

    def test_task_work_with_recovered_partial_work(self, worktree: Path) -> None:
        orch, invoker = _task_work_orchestrator(worktree)
        recovered = AgentInvocationResult(
            task_id=TASK_A, turn=2, agent_type="player", success=True,
            report={"task_id": TASK_A, "_synthetic": True,
                    "files_modified": ["docs/widgets.md"], "files_created": [],
                    "tests_written": []},
            duration_seconds=0.0,
        )
        with patch.object(orch, "_attempt_state_recovery", return_value=recovered), \
                patch.object(orch, "_invoke_coach_safely", return_value=_failed_reviewer()):
            record = orch._execute_turn(
                turn=2, task_id=TASK_A, requirements="Document the endpoint",
                worktree=_FakeWorktree(worktree), previous_feedback=None,
            )

        assert record.decision == "error"
        must_fix = _invoker(worktree)._parse_coach_feedback(
            _resumed_feedback(orch, record), 3
        )["must_fix"]
        assert len(must_fix) == 1
        assert "task-work Player attempt timed out" in must_fix[0]["issue"]
        assert TASK_WORK_TIMEOUT in must_fix[0]["issue"]
        assert must_fix[0]["suggestion"]
        assert "player_turn_" not in must_fix[0]["issue"]

    def test_no_timeout_keeps_no_feedback(self, worktree: Path) -> None:
        orch, invoker = _mocked_orchestrator(worktree)
        invoker.invoke_player.return_value = AgentInvocationResult(
            task_id=TASK_A, turn=1, agent_type="player", success=True,
            report={"task_id": TASK_A, "files_modified": ["docs/widgets.md"],
                    "files_created": [], "tests_written": []},
            duration_seconds=900.0,
        )
        record = _run_turn(orch, worktree, recovered=None, coach=_failed_reviewer())
        assert record.decision == "error"
        assert record.feedback is None


class TestOverriddenApprovalSaysItOnce:
    def test_task_work_timeout_explained_once(self, worktree: Path) -> None:
        """The reviewer approved recovered partial work from a timed-out
        task-work attempt; the approval is overridden to feedback."""
        orch, _ = _task_work_orchestrator(worktree)
        recovered = AgentInvocationResult(
            task_id=TASK_A, turn=2, agent_type="player", success=True,
            report={"task_id": TASK_A, "_synthetic": True,
                    "files_modified": ["docs/widgets.md"], "files_created": [],
                    "tests_written": []},
            duration_seconds=0.0,
        )
        approval = AgentInvocationResult(
            task_id=TASK_A, turn=2, agent_type="coach", success=True,
            report={"decision": "approve", "issues": [],
                    "rationale": "The criteria are met."},
            duration_seconds=1.0,
        )
        with patch.object(orch, "_attempt_state_recovery", return_value=recovered), \
                patch.object(orch, "_invoke_coach_safely", return_value=approval):
            record = orch._execute_turn(
                turn=2, task_id=TASK_A, requirements="Document the endpoint",
                worktree=_FakeWorktree(worktree), previous_feedback=None,
            )

        assert record.decision == "feedback"
        assert record.feedback.count("timed out") == 1
        assert record.feedback.count(TASK_WORK_TIMEOUT) == 1
        must_fix = _invoker(worktree)._parse_coach_feedback(record.feedback, 3)["must_fix"]
        assert len(must_fix) == 1
        assert "task-work Player attempt timed out" in must_fix[0]["issue"]
        assert must_fix[0]["suggestion"]


# ---------------------------------------------------------------------------
# Independent review, round 2 (R3): the early returns before the reviewer
# ---------------------------------------------------------------------------

import threading  # noqa: E402

REINSTALL_TEXT = (
    "Dependency reinstall failed after this turn modified pyproject.toml. "
    "Fix the dependency declaration so the install succeeds."
)


def _recovered_task_work() -> AgentInvocationResult:
    return AgentInvocationResult(
        task_id=TASK_A, turn=2, agent_type="player", success=True,
        report={"task_id": TASK_A, "_synthetic": True,
                "files_modified": ["pyproject.toml"], "files_created": [],
                "tests_written": []},
        duration_seconds=0.0,
    )


def _one_timeout_must_fix(orch, record, worktree: Path) -> Dict[str, str]:
    """Exactly one timeout must-fix, with a suggestion, in the saved
    feedback a resumed run starts from. Returns it."""
    resumed = _resumed_feedback(orch, record)
    assert resumed == record.feedback
    must_fix = _invoker(worktree)._parse_coach_feedback(resumed, 3)["must_fix"]
    timeouts = [
        m for m in must_fix
        if "ran out of time" in m["issue"] or "timed out" in m["issue"]
    ]
    assert len(timeouts) == 1, must_fix
    assert timeouts[0]["suggestion"]
    assert resumed.count("ran out of time") + resumed.count("timed out") == 1
    return timeouts[0]


class TestEarlyReturnsKeepTheTimeoutNote:
    def test_direct_timeout_then_reinstall_failure(self, worktree: Path) -> None:
        orch, invoker = _mocked_orchestrator(worktree)
        invoker.invoke_player.return_value = _timed_out_player()
        recovered = AgentInvocationResult(
            task_id=TASK_A, turn=1, agent_type="player", success=True,
            report=_recovered_timeout_report(TASK_A, 2340), duration_seconds=0.0,
        )
        with patch.object(
            orch, "_maybe_refresh_venv_for_manifest_change", return_value=REINSTALL_TEXT
        ):
            record = _run_turn(orch, worktree, recovered=recovered)

        assert record.decision == "feedback"
        assert record.feedback.endswith(REINSTALL_TEXT)
        item = _one_timeout_must_fix(orch, record, worktree)
        assert "ran out of time after 2340 s" in item["issue"]
        assert item["suggestion"] == TIMEOUT_SUGGESTION

    def test_task_work_timeout_then_reinstall_failure(self, worktree: Path) -> None:
        orch, _ = _task_work_orchestrator(worktree)
        with patch.object(orch, "_attempt_state_recovery", return_value=_recovered_task_work()), \
                patch.object(
                    orch, "_maybe_refresh_venv_for_manifest_change",
                    return_value=REINSTALL_TEXT,
                ):
            record = orch._execute_turn(
                turn=2, task_id=TASK_A, requirements="Document the endpoint",
                worktree=_FakeWorktree(worktree), previous_feedback=None,
            )

        assert record.decision == "feedback"
        assert record.feedback.endswith(REINSTALL_TEXT)
        item = _one_timeout_must_fix(orch, record, worktree)
        assert "task-work Player attempt timed out" in item["issue"]
        assert "player_turn_" not in record.feedback

    def test_cancelled_task_work_timeout(self, worktree: Path) -> None:
        orch, _ = _task_work_orchestrator(worktree)
        orch._cancellation_event = threading.Event()
        orch._cancellation_event.set()
        with patch.object(orch, "_attempt_state_recovery", return_value=_recovered_task_work()):
            record = orch._execute_turn(
                turn=2, task_id=TASK_A, requirements="Document the endpoint",
                worktree=_FakeWorktree(worktree), previous_feedback=None,
            )

        assert record.decision == "error"
        assert record.coach_result is None
        item = _one_timeout_must_fix(orch, record, worktree)
        assert "task-work Player attempt timed out" in item["issue"]

    def test_no_timeout_leaves_the_reinstall_text_alone(self, worktree: Path) -> None:
        orch, invoker = _mocked_orchestrator(worktree)
        invoker.invoke_player.return_value = AgentInvocationResult(
            task_id=TASK_A, turn=1, agent_type="player", success=True,
            report={"task_id": TASK_A, "files_modified": ["pyproject.toml"],
                    "files_created": [], "tests_written": []},
            duration_seconds=900.0,
        )
        with patch.object(
            orch, "_maybe_refresh_venv_for_manifest_change", return_value=REINSTALL_TEXT
        ):
            record = _run_turn(orch, worktree, recovered=None)
        assert record.feedback == REINSTALL_TEXT
