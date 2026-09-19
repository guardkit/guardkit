"""Proof that the whole feature is checked before anyone is offered a merge.

Plain words: a build can finish with every task green and still not do what
the person asked for. These tests prove that when a project declares one
command for its finished features, GuardKit

1. runs it once after the last wave, in the build's own worktree, with the
   feature id, the feature record, the worktree and the candidate sha in its
   environment;
2. treats exit 0 as the only pass — a non-zero exit, a timeout and a command
   that does not exist are all failures;
3. on a failure, re-enters the LAST wave with the command's own output, the
   words of the request and the promised scenarios as the Player's feedback,
   a bounded number of times;
4. when that budget is spent, fails the feature — so the runner's terminal is
   a failed one and Forge's merge card is never offered;
5. writes a receipt naming every attempt; and
6. changes nothing at all for a project that declares no such command.

THE FIXTURE IS NOT PYTHON, ON PURPOSE. The project under test is a Makefile
project whose check is a shell script. Nothing in this seam may assume a
Python repository: the declaration is the project's, and the verdict is an
exit code.

``_execute_wave`` is stubbed throughout, so no model is ever called.

WHERE THIS FILE LIVES, AND WHY: see the note in ``test_boot_smoke_wiring.py``.
``tests/orchestrator/`` is collected by the command CI actually runs; a proof
under ``tests/integration/`` would be silently skipped.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator import feature_check
from guardkit.orchestrator.feature_check import (
    RECEIPT_RELATIVE_PATH,
    FeatureCheckAttempt,
    build_feature_check_feedback,
    claimed_machine_criteria,
    completion_verdict,
    load_feature_check_declaration,
    parse_scenarios_covered,
)
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
    WaveExecutionResult,
)
from guardkit.orchestrator.toolchain_declaration import parse_toolchain_block
from guardkit.worktrees import Worktree


REQUEST_WORDS = "Show me how many users were created per day"
SCENARIO_TITLE = "Seeing the daily count of new users"

#: The project's own check: a shell script, in a Makefile project. It proves
#: the four promised environment variables reach the command, prints the
#: optional coverage line when the feature is fixed, and otherwise fails the
#: way a real endpoint check fails — loudly, on stderr.
CHECK_SCRIPT = f"""#!/bin/sh
echo "feature=$GUARDKIT_FEATURE_ID worktree=$GUARDKIT_WORKTREE"
echo "record=$GUARDKIT_FEATURE_RECORD sha=$GUARDKIT_CANDIDATE_SHA"
if [ -f THE_FEATURE_IS_FIXED ]; then
  echo '{{"guardkit_feature_check": {{"scenarios_covered": ["{SCENARIO_TITLE}"]}}}}'
  exit 0
fi
echo "GET /users/created-per-day answered 404, so the feature does not work" >&2
exit 1
"""

MAKEFILE = "check:\n\tsh qa/feature-check.sh\n"

TASK_DOCUMENT = f"""# TASK-001 — the daily count endpoint

## The words of the request this task serves

{REQUEST_WORDS}

## Acceptance criteria

- The endpoint answers with one entry per day.
"""


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(root), check=True, capture_output=True)


def _make_project(
    tmp_path: Path,
    *,
    declaration: Optional[str],
    enforce_twins: bool = False,
) -> tuple[Path, Path]:
    """A Makefile project: a main checkout and the build's worktree.

    ``declaration`` is the ``.guardkit/config.yaml`` body for the MAIN
    checkout — the only copy the check is ever read from. ``None`` declares
    nothing at all.
    """
    repo_root = tmp_path / "main"
    worktree = tmp_path / "worktree"
    for root in (repo_root, worktree):
        _write(root, "Makefile", MAKEFILE)
        _write(root, "qa/feature-check.sh", CHECK_SCRIPT)
    if declaration is not None:
        body = declaration
        if enforce_twins:
            body += "\nqa:\n  enforce_twin_coverage: true\n"
        _write(repo_root, ".guardkit/config.yaml", body)
    _write(worktree, "tasks/TASK-001.md", TASK_DOCUMENT)

    _git(worktree, "init", "-b", "main")
    _git(worktree, "config", "user.email", "test@example.com")
    _git(worktree, "config", "user.name", "Test")
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", "the build's candidate")
    return repo_root, worktree


def _declaration(command: str, *, timeout: Optional[int] = None) -> str:
    body = f'toolchain:\n  test: "make test"\n  feature_check: "{command}"\n'
    if timeout is not None:
        body += f"  feature_check_timeout: {timeout}\n"
    return body


def _make_orchestrator(repo_root: Path) -> FeatureOrchestrator:
    return FeatureOrchestrator(
        repo_root=repo_root,
        max_turns=1,
        worktree_manager=MagicMock(),
        quiet=True,
    )


def _make_worktree(path: Path) -> Worktree:
    return Worktree(
        task_id="FEAT-TEST",
        branch_name="autobuild/FEAT-TEST",
        path=path,
        base_branch="main",
    )


def _make_feature(worktree: Path, *, hurl_scenario: bool = False):
    feature = MagicMock()
    feature.id = "FEAT-TEST"
    feature.name = "Daily count of new users"
    feature.description = REQUEST_WORDS
    feature.status = "in_progress"
    feature.smoke_gates = None
    feature.estimated_minutes = None
    feature.file_path = str(worktree / ".guardkit/features/FEAT-TEST.yaml")
    feature.scenarios = (
        {SCENARIO_TITLE: {"verifier": "hurl"}} if hurl_scenario else {}
    )

    task = MagicMock()
    task.id = "TASK-001"
    task.dependencies = []
    task.status = "pending"
    task.file_path = str(worktree / "tasks/TASK-001.md")
    feature.tasks = [task]
    feature.orchestration.parallel_groups = [["TASK-001"]]
    feature.execution.current_wave = 0
    feature.execution.completed_waves = []
    return feature


def _succeeding_wave(wave_number: int, task_ids: List[str]) -> WaveExecutionResult:
    return WaveExecutionResult(
        wave_number=wave_number,
        task_ids=task_ids,
        results=[
            TaskExecutionResult(
                task_id=tid, success=True, total_turns=1, final_decision="approved"
            )
            for tid in task_ids
        ],
        all_succeeded=True,
    )


def _pass_the_wiring_gate(wave_number, task_ids, feature, worktree, wave_result):
    return MagicMock(final_wave_result=wave_result, terminate=False)


def _common_patches(orchestrator: FeatureOrchestrator):
    return (
        patch.object(orchestrator, "_preflight_check"),
        patch.object(orchestrator, "_bootstrap_environment"),
        patch.object(
            orchestrator,
            "_run_post_wave_wiring_gate",
            autospec=True,
            side_effect=_pass_the_wiring_gate,
        ),
        patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.find_task",
            side_effect=lambda f, tid: f,
        ),
        patch(
            "guardkit.orchestrator.feature_orchestrator.FeatureLoader.save_feature",
        ),
    )


class _WaveRecorder:
    """Stands in for the Player: records the feedback each wave was given.

    ``on_reentry`` is the Player's "fix": the test decides whether the
    re-entered wave actually repairs the feature (it writes the marker file
    the project's check looks for) or leaves it broken.
    """

    def __init__(
        self, worktree: Path, on_reentry: Optional[Callable[[int], None]] = None
    ) -> None:
        self.worktree = worktree
        self.on_reentry = on_reentry
        self.feedback: List[Optional[str]] = []

    def __call__(
        self,
        wave_number,
        task_ids,
        feature,
        worktree,
        seed_feedback=None,
        attempt=0,
    ) -> WaveExecutionResult:
        self.feedback.append(seed_feedback)
        if seed_feedback is not None and self.on_reentry is not None:
            self.on_reentry(len(self.feedback) - 1)
        return _succeeding_wave(wave_number, list(task_ids))


def _run_build(
    repo_root: Path,
    worktree_path: Path,
    feature,
    recorder: _WaveRecorder,
    *,
    finalize: bool = True,
):
    """Run the wave phase (and the finaliser) with no model in the loop."""
    orchestrator = _make_orchestrator(repo_root)
    worktree = _make_worktree(worktree_path)
    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        stack.enter_context(
            patch.object(orchestrator, "_run_final_wave_boot_smoke", return_value=None)
        )
        stack.enter_context(patch.object(orchestrator, "_execute_wave", side_effect=recorder))
        wave_results = orchestrator._wave_phase(feature, worktree)
        if not finalize:
            return orchestrator, wave_results, None
        stack.enter_context(patch.object(orchestrator, "_display_summary"))
        result = orchestrator._finalize_phase(feature, wave_results, worktree)
    return orchestrator, wave_results, result


def _receipt(worktree_path: Path) -> dict:
    return json.loads((worktree_path / RECEIPT_RELATIVE_PATH).read_text())


@pytest.fixture(autouse=True)
def _no_ambient_flags(monkeypatch: pytest.MonkeyPatch):
    """The estate's own env must not decide what these tests prove."""
    monkeypatch.delenv("GUARDKIT_FEATURE_CHECK_MAX_RETRIES", raising=False)
    monkeypatch.delenv("GUARDKIT_QA_ENFORCE_TWIN_COVERAGE", raising=False)


# ---------------------------------------------------------------------------
# 1. The declaration
# ---------------------------------------------------------------------------


def test_a_declared_check_is_read_from_the_main_checkout(tmp_path: Path) -> None:
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh", timeout=120)
    )
    declared = load_feature_check_declaration(repo_root)
    assert declared is not None
    assert declared.command == "sh qa/feature-check.sh"
    assert declared.timeout == 120

    # The build's own copy of the config is never the one that is read: a
    # build that could rewrite its own final check would not be checked.
    _write(worktree, ".guardkit/config.yaml", _declaration("true"))
    assert load_feature_check_declaration(repo_root).command == "sh qa/feature-check.sh"


def test_no_declaration_means_no_check(tmp_path: Path) -> None:
    repo_root, _ = _make_project(tmp_path, declaration=None)
    assert load_feature_check_declaration(repo_root) is None


def test_the_timeout_defaults_to_ten_minutes_and_is_bounded() -> None:
    assert parse_toolchain_block({"feature_check": "make check"}).feature_check_timeout == 600
    with pytest.raises(ValueError):
        parse_toolchain_block({"feature_check": "make check", "feature_check_timeout": 0})
    with pytest.raises(ValueError):
        parse_toolchain_block({"feature_check": "make check", "feature_check_timeout": 99999})
    # A block that declares ONLY the feature check is not an empty block.
    assert parse_toolchain_block({"feature_check": "make check"}).is_empty is False


# ---------------------------------------------------------------------------
# 2. Exit 0 is the only pass
# ---------------------------------------------------------------------------


def test_a_passing_check_completes_the_feature_with_one_attempt(tmp_path: Path) -> None:
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    _write(worktree, "THE_FEATURE_IS_FIXED", "")
    feature = _make_feature(worktree)
    recorder = _WaveRecorder(worktree)

    _, _, result = _run_build(repo_root, worktree, feature, recorder)

    assert result.status == "completed"
    assert result.success is True
    assert recorder.feedback == [None], "a passing check must not re-enter the wave"
    receipt = _receipt(worktree)
    assert receipt["status"] == "passed"
    assert len(receipt["attempts"]) == 1
    assert receipt["attempts"][0]["exit_code"] == 0
    assert receipt["scenarios_covered"] == [SCENARIO_TITLE]


def test_the_check_is_given_the_feature_id_record_worktree_and_sha(
    tmp_path: Path,
) -> None:
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    _write(worktree, "THE_FEATURE_IS_FIXED", "")
    feature = _make_feature(worktree)
    _run_build(repo_root, worktree, feature, _WaveRecorder(worktree))

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(worktree), capture_output=True, text=True
    ).stdout.strip()
    stdout_tail = _receipt(worktree)["attempts"][0]["stdout_tail"]
    assert "feature=FEAT-TEST" in stdout_tail
    assert f"worktree={worktree}" in stdout_tail
    assert "FEAT-TEST.yaml" in stdout_tail
    assert head in stdout_tail


def test_a_failing_check_re_enters_the_last_wave_once_then_fails_the_feature(
    tmp_path: Path,
) -> None:
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    feature = _make_feature(worktree)
    recorder = _WaveRecorder(worktree)  # the Player never fixes it

    _, wave_results, result = _run_build(repo_root, worktree, feature, recorder)

    assert result.status == "failed"
    assert result.success is False
    assert len(recorder.feedback) == 2, "exactly one re-entry, the default budget"
    feedback = recorder.feedback[1]
    assert "GET /users/created-per-day answered 404" in feedback, "the output tail"
    assert REQUEST_WORDS in feedback, "the words of the request"
    assert "exit=1, expected=0" in feedback
    receipt = _receipt(worktree)
    assert receipt["status"] == "failed"
    assert [a["attempt"] for a in receipt["attempts"]] == [1, 2]
    # The wave is no longer recorded complete, so a resume re-runs it.
    assert 1 not in feature.execution.completed_waves
    gate = wave_results[-1].smoke_gate_result
    assert gate is not None and gate.passed is False
    assert "whole-feature check" in gate.command
    assert "whole-feature check failed" in (result.error or "")


def test_a_repair_round_that_fixes_the_feature_completes_it(tmp_path: Path) -> None:
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    feature = _make_feature(worktree)
    recorder = _WaveRecorder(
        worktree,
        on_reentry=lambda _n: _write(worktree, "THE_FEATURE_IS_FIXED", ""),
    )

    _, _, result = _run_build(repo_root, worktree, feature, recorder)

    assert result.status == "completed"
    receipt = _receipt(worktree)
    assert receipt["status"] == "passed"
    assert len(receipt["attempts"]) == 2
    assert receipt["attempts"][0]["passed"] is False
    assert receipt["attempts"][1]["passed"] is True


def test_a_timeout_is_a_failure(tmp_path: Path) -> None:
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sleep 30", timeout=1)
    )
    feature = _make_feature(worktree)
    recorder = _WaveRecorder(worktree)

    _, _, result = _run_build(repo_root, worktree, feature, recorder)

    assert result.status == "failed"
    receipt = _receipt(worktree)
    assert receipt["attempts"][0]["timed_out"] is True
    assert "timed out after 1s" in receipt["reason"]
    assert "timed out" in recorder.feedback[1]


def test_a_command_that_does_not_exist_is_a_failure(tmp_path: Path) -> None:
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/there-is-no-such-check.sh")
    )
    feature = _make_feature(worktree)

    _, _, result = _run_build(repo_root, worktree, feature, _WaveRecorder(worktree))

    assert result.status == "failed"
    receipt = _receipt(worktree)
    assert receipt["attempts"][0]["passed"] is False
    assert receipt["attempts"][0]["exit_code"] != 0


def test_the_retry_budget_is_the_operator_s(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GUARDKIT_FEATURE_CHECK_MAX_RETRIES", "0")
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    feature = _make_feature(worktree)
    recorder = _WaveRecorder(worktree)

    _, _, result = _run_build(repo_root, worktree, feature, recorder)

    assert result.status == "failed"
    assert len(recorder.feedback) == 1, "budget 0 means the first failure is final"
    assert len(_receipt(worktree)["attempts"]) == 1


# ---------------------------------------------------------------------------
# 3. Twin coverage runs first
# ---------------------------------------------------------------------------


def test_missing_twins_under_enforcement_re_enter_the_wave_with_the_titles(
    tmp_path: Path,
) -> None:
    repo_root, worktree = _make_project(
        tmp_path,
        declaration=_declaration("sh qa/feature-check.sh"),
        enforce_twins=True,
    )
    _write(worktree, "THE_FEATURE_IS_FIXED", "")  # the command itself would pass
    feature = _make_feature(worktree, hurl_scenario=True)
    recorder = _WaveRecorder(worktree)

    _, _, result = _run_build(repo_root, worktree, feature, recorder)

    assert result.status == "failed"
    assert len(recorder.feedback) == 2
    assert SCENARIO_TITLE in recorder.feedback[1]
    assert "no twin file exists" in recorder.feedback[1]
    receipt = _receipt(worktree)
    assert receipt["attempts"][0]["missing_twins"] == [SCENARIO_TITLE]
    # The command never ran: a promise with no artifact is answered before a
    # command gets the chance to say the feature is fine.
    assert receipt["attempts"][0]["exit_code"] is None


def test_a_twin_that_exists_lets_the_check_run(tmp_path: Path) -> None:
    repo_root, worktree = _make_project(
        tmp_path,
        declaration=_declaration("sh qa/feature-check.sh"),
        enforce_twins=True,
    )
    _write(worktree, "THE_FEATURE_IS_FIXED", "")
    _write(worktree, "qa/twins/daily-count.hurl", f"# Scenario: {SCENARIO_TITLE}\nGET /x\n")
    feature = _make_feature(worktree, hurl_scenario=True)

    _, _, result = _run_build(repo_root, worktree, feature, _WaveRecorder(worktree))

    assert result.status == "completed"
    assert _receipt(worktree)["attempts"][0]["exit_code"] == 0


# ---------------------------------------------------------------------------
# 4. The positive control: a project that declared nothing is unchanged
# ---------------------------------------------------------------------------


def test_a_project_with_no_declaration_is_unchanged(tmp_path: Path) -> None:
    repo_root, worktree = _make_project(tmp_path, declaration=None)
    feature = _make_feature(worktree)
    recorder = _WaveRecorder(worktree)

    _, wave_results, result = _run_build(repo_root, worktree, feature, recorder)

    assert result.status == "completed"
    assert result.success is True
    assert recorder.feedback == [None], "no check, no re-entry"
    assert wave_results[-1].smoke_gate_result is None
    receipt = _receipt(worktree)
    assert receipt["status"] == "not_declared"
    assert receipt["attempts"] == []


def test_a_build_that_did_not_finish_does_not_run_the_check(tmp_path: Path) -> None:
    """A build that already failed explains its own red; no extra noise."""
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    feature = _make_feature(worktree)
    feature.orchestration.parallel_groups = [["TASK-001"], ["TASK-002"]]
    orchestrator = _make_orchestrator(repo_root)

    def _stop_after_one(wave_number, task_ids, feature_, worktree_, **kwargs):
        return WaveExecutionResult(
            wave_number=wave_number,
            task_ids=list(task_ids),
            results=[
                TaskExecutionResult(
                    task_id="TASK-001",
                    success=False,
                    total_turns=1,
                    final_decision="rejected",
                )
            ],
            all_succeeded=False,
        )

    with ExitStack() as stack:
        for _cm in _common_patches(orchestrator):
            stack.enter_context(_cm)
        stack.enter_context(
            patch.object(orchestrator, "_run_final_wave_boot_smoke", return_value=None)
        )
        stack.enter_context(
            patch.object(orchestrator, "_execute_wave", side_effect=_stop_after_one)
        )
        orchestrator._wave_phase(feature, _make_worktree(worktree))

    assert not (worktree / RECEIPT_RELATIVE_PATH).exists()


# ---------------------------------------------------------------------------
# 5. The completion rule
# ---------------------------------------------------------------------------


def _stub_receipt(worktree: Path, **overrides: Any) -> None:
    payload = {
        "feature": "FEAT-TEST",
        "status": "passed",
        "declared": True,
        "command": "sh qa/feature-check.sh",
        "scenarios_covered": [],
        "attempts": [
            {
                "attempt": 1,
                "passed": True,
                "candidate_sha": feature_check.candidate_sha(worktree),
            }
        ],
    }
    payload.update(overrides)
    path = worktree / RECEIPT_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_claimed_criterion(worktree: Path, name: str) -> None:
    """What the Coach writes when a promise was never independently proved."""
    path = worktree / ".guardkit/autobuild-private/TASK-001/coach_turn_1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "task_id": "TASK-001",
                "requirements": {
                    "criteria_results": [
                        {
                            "criterion": name,
                            "status": "claimed",
                            "pass_bar_class": "machine",
                        },
                        {
                            "criterion": "a helper returns a list",
                            "status": "verified",
                            "pass_bar_class": "machine",
                        },
                    ]
                },
            }
        ),
        encoding="utf-8",
    )


def test_a_claimed_promise_the_check_did_not_cover_blocks_completion(
    tmp_path: Path,
) -> None:
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    _stub_receipt(worktree)
    _write_claimed_criterion(worktree, SCENARIO_TITLE)
    feature = _make_feature(worktree)

    verdict = completion_verdict(
        repo_root=repo_root, worktree_root=worktree, feature=feature
    )

    assert verdict.blocks is True
    assert SCENARIO_TITLE in verdict.reason


def test_a_claimed_promise_the_check_covered_does_not_block(tmp_path: Path) -> None:
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    _stub_receipt(worktree, scenarios_covered=[SCENARIO_TITLE])
    _write_claimed_criterion(worktree, SCENARIO_TITLE)
    feature = _make_feature(worktree)

    verdict = completion_verdict(
        repo_root=repo_root, worktree_root=worktree, feature=feature
    )

    assert verdict.blocks is False, verdict.reason


def test_a_pass_recorded_against_different_code_does_not_count(tmp_path: Path) -> None:
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    _stub_receipt(
        worktree,
        attempts=[{"attempt": 1, "passed": True, "candidate_sha": "0" * 40}],
    )
    feature = _make_feature(worktree)

    verdict = completion_verdict(
        repo_root=repo_root, worktree_root=worktree, feature=feature
    )

    assert verdict.blocks is True
    assert "different code" in verdict.reason


def test_a_declared_check_with_no_receipt_cannot_be_completed(tmp_path: Path) -> None:
    repo_root, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    feature = _make_feature(worktree)

    verdict = completion_verdict(
        repo_root=repo_root, worktree_root=worktree, feature=feature
    )

    assert verdict.blocks is True
    assert "no receipt" in verdict.reason


def test_no_declaration_never_blocks_completion(tmp_path: Path) -> None:
    repo_root, worktree = _make_project(tmp_path, declaration=None)
    _write_claimed_criterion(worktree, SCENARIO_TITLE)
    feature = _make_feature(worktree)

    verdict = completion_verdict(
        repo_root=repo_root, worktree_root=worktree, feature=feature
    )

    assert verdict.blocks is False


def test_the_claimed_reader_survives_a_factory_that_never_writes_the_word(
    tmp_path: Path,
) -> None:
    """Absent evidence is not evidence of a claim — and never an exception."""
    worktree = tmp_path / "worktree"
    (worktree / ".guardkit/autobuild-private/TASK-001").mkdir(parents=True)
    (worktree / ".guardkit/autobuild-private/TASK-001/coach_turn_1.json").write_text(
        "{not json at all", encoding="utf-8"
    )
    assert claimed_machine_criteria(worktree, ["TASK-001"]) == []
    assert claimed_machine_criteria(worktree, ["TASK-404"]) == []
    assert claimed_machine_criteria(tmp_path / "nothing-here", ["TASK-001"]) == []


def test_a_claimed_criterion_that_is_not_machine_class_is_not_consumed(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "worktree"
    path = worktree / ".guardkit/autobuild-private/TASK-001/coach_turn_1.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {"criteria": [{"criterion": "the docs read well", "status": "claimed",
                           "pass_bar_class": "human"}]}
        ),
        encoding="utf-8",
    )
    assert claimed_machine_criteria(worktree, ["TASK-001"]) == []


# ---------------------------------------------------------------------------
# 6. The optional coverage line, and the feedback's own words
# ---------------------------------------------------------------------------


def test_the_coverage_line_is_read_and_everything_else_on_stdout_is_not() -> None:
    stdout = (
        "running the project's own check\n"
        '{"guardkit_feature_check": {"scenarios_covered": ["A", "B"]}}\n'
        "all good\n"
    )
    assert parse_scenarios_covered(stdout) == ["A", "B"]
    assert parse_scenarios_covered("scenarios_covered: A, B") == []
    assert parse_scenarios_covered('{"guardkit_feature_check": "not a mapping"}') == []
    assert parse_scenarios_covered("{broken json guardkit_feature_check}") == []
    assert parse_scenarios_covered("") == []


def test_the_feedback_says_what_failed_and_what_was_asked_for() -> None:
    attempt = FeatureCheckAttempt(
        attempt=1,
        command="sh qa/feature-check.sh",
        candidate_sha="abc123",
        passed=False,
        exit_code=1,
        stderr_tail="404 on /users/created-per-day",
        failure_reason="exit=1, expected=0",
    )
    text = build_feature_check_feedback(
        attempt, request_words=REQUEST_WORDS, titles=[SCENARIO_TITLE]
    )
    assert "sh qa/feature-check.sh" in text
    assert "404 on /users/created-per-day" in text
    assert REQUEST_WORDS in text
    assert SCENARIO_TITLE in text
    assert "must not edit it" in text


def test_the_request_words_come_from_the_task_document_too(tmp_path: Path) -> None:
    _, worktree = _make_project(
        tmp_path, declaration=_declaration("sh qa/feature-check.sh")
    )
    feature = _make_feature(worktree)
    feature.description = ""
    words = feature_check.feature_request_words(feature, worktree)
    assert REQUEST_WORDS in words
    assert "Acceptance criteria" not in words, "the block ends at the next heading"


# ---------------------------------------------------------------------------
# 7. The other end of the rail: Forge refuses the card for a failed build
# ---------------------------------------------------------------------------

try:  # pragma: no cover - import availability is the thing under test
    from forge.pipeline.merge_offer import MergeOfferService
    from nats_core.events import BuildCompletePayload

    _FORGE_IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # noqa: BLE001
    MergeOfferService = None  # type: ignore[assignment]
    BuildCompletePayload = None  # type: ignore[assignment]
    _FORGE_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


def _build_complete(tasks_failed: int):
    return BuildCompletePayload(
        feature_id="FEAT-TEST",
        build_id="build-1",
        tasks_completed=5 - tasks_failed,
        tasks_failed=tasks_failed,
        tasks_total=5,
        duration_seconds=12,
        summary="a build",
    )


def _merge_offer_service(offers: List[dict]):
    async def _fake_offer(**kwargs: Any) -> bool:
        offers.append(kwargs)
        return True

    async def _raw_publish(subject: str, body: bytes) -> None:
        raise AssertionError("no test here may put anything on a broker")

    service = MergeOfferService(
        config=SimpleNamespace(merge_executor=SimpleNamespace(enabled=True)),
        pool=MagicMock(),
        pipeline_publisher=MagicMock(),
        raw_publish=_raw_publish,
        scope_pass=lambda **kwargs: None,
    )
    service.offer = _fake_offer  # the card itself is not what this proves
    return service


@pytest.mark.skipif(
    _FORGE_IMPORT_ERROR is not None,
    reason=f"forge/nats_core not importable here ({_FORGE_IMPORT_ERROR})",
)
def test_forge_refuses_the_merge_card_for_a_failed_build() -> None:
    """The real ``MergeOfferService._maybe_offer``, no broker anywhere near it."""
    offers: List[dict] = []
    service = _merge_offer_service(offers)

    asyncio.run(service._maybe_offer(_build_complete(tasks_failed=1)))
    assert offers == [], "a build that is not clean is never offered a merge card"

    asyncio.run(service._maybe_offer(_build_complete(tasks_failed=0)))
    assert len(offers) == 1
    assert offers[0]["feature_id"] == "FEAT-TEST"
