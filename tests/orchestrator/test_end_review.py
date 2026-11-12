"""The end review of the finished feature, in place of a model review of each task
(Rich, 12 November 2026: "yes agreed please proceed").

What is checked here, with no model called anywhere:

- the request is found in the build's own history (the ``planning: feature plan`` commit and
  ``feature_spec_inputs/<correlation id>.md``), or else from the feature file and its
  ``.feature`` files, and the record says which;
- by default the per-task reviewer makes no model call, and ``GUARDKIT_PER_TASK_REVIEW=1``
  brings it back (and turns the end review off);
- the end review is skipped when a task did not complete, and a single ``--task`` run never
  starts it;
- at most two repair rounds, stopping at ``NO FAULTS``; the record is written after every step
  and a resumed build carries on from it with the same budget;
- the whole-feature check runs after the end review's repairs, so a repair that breaks it
  fails the build;
- the fault parser.

Async calls use ``asyncio.run`` to stay free of a pytest-asyncio dependency.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator import end_review
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.feature_orchestrator import WaveExecutionResult
from guardkit.orchestrator.harness import AssistantMessageEvent, ResultMessageEvent

FEATURE_ID = "FEAT-ER1"
#: The real one review, kept before the suite's fence replaces it for every test.
_REAL_REVIEW_ONCE = end_review._review_once
CORRELATION = "511b7cf1-7110-432b-a28a-eb085d51003f"


@pytest.fixture(autouse=True)
def _default_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """The estate's own environment must not decide what these tests prove."""
    monkeypatch.delenv(end_review.PER_TASK_REVIEW_ENV, raising=False)
    monkeypatch.delenv("GUARDKIT_FEATURE_CHECK_MAX_RETRIES", raising=False)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(root), check=True, capture_output=True,
                          text=True).stdout.strip()


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    _write(path, "README.md", "a project\n")
    _commit(path, "start")
    return path


def _feature(tasks: int = 2, statuses: Optional[List[str]] = None, feature_files: Optional[List[str]] = None):
    task_list = [
        SimpleNamespace(id=f"TASK-ER-00{n}", name=f"task {n}", file_path=f"tasks/TASK-ER-00{n}.md",
                        status=(statuses or ["completed"] * tasks)[n - 1])
        for n in range(1, tasks + 1)
    ]
    return SimpleNamespace(
        id=FEATURE_ID,
        name="Daily count of new users",
        description="Show me how many users were created per day.",
        feature_files=feature_files or [],
        file_path=".guardkit/features/FEAT-ER1.yaml",
        tasks=task_list,
        orchestration=SimpleNamespace(parallel_groups=[[t.id for t in task_list]]),
    )


# ---------------------------------------------------------------------------
# The request
# ---------------------------------------------------------------------------


def test_the_request_is_found_by_the_planning_commit(tmp_path: Path) -> None:
    worktree = _repo(tmp_path / "wt")
    _write(worktree, f"feature_spec_inputs/{CORRELATION}.md", "# The request\n\nCount users per day.\n")
    _commit(worktree, f"planning: add feature_spec_inputs/{CORRELATION}.md (Mode P planned handoff)")
    _write(worktree, ".guardkit/features/FEAT-ER1.yaml", "id: FEAT-ER1\n")
    plan = _commit(worktree, f"planning: feature plan {FEATURE_ID} for {CORRELATION} (Lane B 008)")
    _write(worktree, "src/app.py", "print('built')\n")
    _commit(worktree, "a task's checkpoint")

    text, source = end_review.find_request(_feature(), worktree)

    assert text == "# The request\n\nCount users per day.\n"
    assert source == {"source": "planning commit", "commit": plan, "correlation_id": CORRELATION,
                      "path": f"feature_spec_inputs/{CORRELATION}.md"}


def test_another_feature_s_planning_commit_is_not_taken(tmp_path: Path) -> None:
    worktree = _repo(tmp_path / "wt")
    _write(worktree, f"feature_spec_inputs/{CORRELATION}.md", "someone else's request\n")
    _commit(worktree, f"planning: feature plan FEAT-OTHER for {CORRELATION} (Lane B 008)")

    _, source = end_review.find_request(_feature(), worktree)

    assert source["source"] == "feature file"


def test_without_a_planning_commit_the_feature_file_is_the_request(tmp_path: Path) -> None:
    worktree = _repo(tmp_path / "wt")
    spec = "features/daily-count/daily-count.feature"
    _write(worktree, spec, "Feature: Daily count\n  Scenario: Seeing the daily count\n")
    _commit(worktree, "plan without Forge")

    text, source = end_review.find_request(_feature(feature_files=[spec, "features/gone.feature"]), worktree)

    assert source == {"source": "feature file", "feature_files": [spec],
                      "feature_files_missing": ["features/gone.feature"]}
    assert text.startswith("# Daily count of new users\n\nShow me how many users were created per day.")
    assert "Scenario: Seeing the daily count" in text


def test_a_planning_commit_whose_request_is_not_at_head_falls_back(tmp_path: Path) -> None:
    worktree = _repo(tmp_path / "wt")
    _git(worktree, "commit", "-q", "--allow-empty", "-m",
         f"planning: feature plan {FEATURE_ID} for {CORRELATION} (Lane B 008)")

    _, source = end_review.find_request(_feature(), worktree)

    assert source["source"] == "feature file"


def test_not_a_git_checkout_still_gives_the_feature_file(tmp_path: Path) -> None:
    text, source = end_review.find_request(_feature(), tmp_path)

    assert source["source"] == "feature file"
    assert "Daily count of new users" in text


# ---------------------------------------------------------------------------
# The fault parser
# ---------------------------------------------------------------------------


def test_the_fault_parser_keeps_only_located_triggerable_faults() -> None:
    answer = "\n".join([
        "I ran the service and tried a closed port.",
        "FAULT src/app.py:42 :: the error is swallowed :: GET /count with the database stopped",
        "- FAULT src/app.py:42 :: The error is swallowed :: again, a duplicate",
        "FAULT src/b.py :: no line :: something",
        "FAULT src/c.py:7 :: no trigger",
        "* fault pkg/x.go:3 :: wrong status :: send an empty body",
        "1. FAULT numbered/x.go:3 :: a numbered line is not read :: as measured",
    ])

    assert end_review.parse_faults(answer) == [
        {"file": "src/app.py", "line": 42, "what": "the error is swallowed",
         "trigger": "GET /count with the database stopped"},
        {"file": "pkg/x.go", "line": 3, "what": "wrong status", "trigger": "send an empty body"},
    ]
    assert end_review.parse_faults("NO FAULTS") == []
    assert end_review.parse_faults(None) == []


def test_the_switch() -> None:
    assert end_review.per_task_review_on({}) is False
    assert end_review.enabled({}) is True
    for word in ("1", "true", "Yes", " on "):
        assert end_review.per_task_review_on({end_review.PER_TASK_REVIEW_ENV: word}) is True
        assert end_review.enabled({end_review.PER_TASK_REVIEW_ENV: word}) is False
    assert end_review.per_task_review_on({end_review.PER_TASK_REVIEW_ENV: "0"}) is False


# ---------------------------------------------------------------------------
# The per-task reviewer: no model call by default, back with the setting
# ---------------------------------------------------------------------------


def _bundle():
    from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle

    return CoachEvidenceBundle(gathering_status="complete")


def _coach(tmp_path: Path):
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = tmp_path
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    calls: List[Dict[str, Any]] = []

    async def _iwr(**kwargs):
        calls.append(kwargs)
        if not kwargs.get("synthesis"):
            return (None, [AssistantMessageEvent(text="1. STUB src/foo.py:10: fixed answer"),
                           ResultMessageEvent(session_id=None)])
        verdict = ('```json\n{"task_id": "TASK-ER-001", "turn": 1, "decision": "approve", '
                   '"rationale": "looked", "issues": []}\n```')
        return (None, [AssistantMessageEvent(text=verdict), ResultMessageEvent(session_id=None)])

    invoker._invoke_with_role = _iwr  # type: ignore[method-assign]
    result = asyncio.run(invoker.invoke_coach(
        task_id="TASK-ER-001", turn=1, requirements="reqs",
        player_report={"files_modified": ["src/foo.py"]}, evidence_bundle=_bundle(),
    ))
    return result, calls


def test_by_default_the_per_task_reviewer_makes_no_model_call(tmp_path: Path) -> None:
    result, calls = _coach(tmp_path)

    assert calls == []
    assert result.success is True
    assert result.report["decision"] == "approve"
    assert result.report["issues"] == []
    assert "end review" in result.report["rationale"]


def test_the_setting_brings_the_per_task_reviewer_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(end_review.PER_TASK_REVIEW_ENV, "1")

    result, calls = _coach(tmp_path)

    assert [bool(c.get("synthesis")) for c in calls] == [False, True]
    assert result.report["rationale"] == "looked"


def test_with_no_reviewer_a_failing_project_check_still_sends_the_turn_back(tmp_path: Path) -> None:
    """The guards after the verdict still run: the experiment's empty-approval path."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = tmp_path
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._invoke_with_role = MagicMock(side_effect=AssertionError("no model call"))  # type: ignore[method-assign]
    seen: List[str] = []

    def _guard(*, decision, **_kwargs):
        seen.append(decision["decision"])
        decision["decision"] = "feedback"
        decision["issues"] = [{"description": "the project's tests failed"}]

    invoker._apply_independent_test_code_failure_guard = _guard  # type: ignore[method-assign]
    result = asyncio.run(invoker.invoke_coach(
        task_id="TASK-ER-001", turn=1, requirements="reqs", player_report={}, evidence_bundle=_bundle(),
    ))

    assert seen == ["approve"]
    assert result.report["decision"] == "feedback"


def test_with_no_reviewer_the_last_look_has_no_notes_and_makes_no_call(tmp_path: Path) -> None:
    from guardkit.orchestrator import build_review

    last_look = MagicMock(side_effect=AssertionError("no model call"))
    # The no-reviewer verdict leaves nothing on the task's record for the card.
    _, _ = _coach(tmp_path)
    path = build_review.write_feature_notes(FEATURE_ID, ["TASK-ER-001"], tmp_path, last_look=last_look)

    assert json.loads(path.read_text())["notes"] == []
    last_look.assert_not_called()


# ---------------------------------------------------------------------------
# The review's copy of the code
# ---------------------------------------------------------------------------


def test_the_review_s_copy_is_a_separate_repository_at_the_same_commit(tmp_path: Path) -> None:
    worktree = _repo(tmp_path / "wt")
    base = _git(worktree, "rev-parse", "HEAD")
    _git(worktree, "checkout", "-q", "-b", "autobuild/FEAT-ER1")
    _write(worktree, "src/app.py", "print('built')\n")
    head = _commit(worktree, "a task's checkpoint")
    _write(worktree, "uncommitted.txt", "not part of the copy\n")
    (tmp_path / "copy").mkdir()

    code = end_review._copy_of(worktree, tmp_path / "copy")

    assert _git(code, "rev-parse", "HEAD") == head
    assert _git(code, "rev-parse", "--abbrev-ref", "HEAD") == "autobuild/FEAT-ER1"
    assert _git(code, "merge-base", "--is-ancestor", base, "HEAD") == ""
    assert (code / "src/app.py").read_text() == "print('built')\n"
    assert not (code / "uncommitted.txt").exists()
    assert (code / ".git").is_dir(), "its own repository, not a worktree linked to the build's"
    assert _git(code, "status", "--porcelain") == ""
    assert not (tmp_path / "copy" / "history.bundle").exists()


def test_one_review_runs_in_the_copy_with_the_request_and_the_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = _repo(tmp_path / "wt")
    base = _git(worktree, "rev-parse", "HEAD")
    _write(worktree, "src/app.py", "print('built')\n")
    _commit(worktree, "a task's checkpoint")
    seen: Dict[str, Any] = {}

    async def _session(self, feature_id, round_number, prompt, seconds, grace_seconds):
        seen.update(cwd=Path(self.worktree_path), prompt=prompt, seconds=seconds, grace=grace_seconds,
                    files=(Path(self.worktree_path) / "src/app.py").exists())
        return "NO FAULTS"

    monkeypatch.setattr(AgentInvoker, "invoke_end_review", _session)
    orchestrator = SimpleNamespace(sdk_timeout=None, timeout_multiplier=1.0, model=None, coach_model=None,
                                   _emitter=None)

    reviewed = _REAL_REVIEW_ONCE(orchestrator, _feature(), SimpleNamespace(path=worktree), base,
                                 "Count users per day.", 1, 3600)

    assert reviewed["answer"] == "NO FAULTS"
    assert seen["files"] and seen["cwd"] != worktree
    assert not seen["cwd"].exists(), "the copy is removed afterwards"
    assert (seen["seconds"], seen["grace"]) == (3600, end_review.ANSWER_GRACE_SECONDS)
    assert "## The whole request\n\nCount users per day." in seen["prompt"]
    assert "+print('built')" in seen["prompt"]
    assert "FAULT path/to/file.ext:LINE :: what goes wrong :: how to trigger it" in seen["prompt"]


# ---------------------------------------------------------------------------
# The rounds
# ---------------------------------------------------------------------------


class _Builder:
    """Stands in for the builder's repair turn: commits a change, says whether it succeeded."""

    def __init__(self, worktree: Path, succeed: bool = True) -> None:
        self.worktree = worktree
        self.succeed = succeed
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, wave, task_ids, feature, worktree, seed_feedback=None, attempt=0):
        self.calls.append({"wave": wave, "tasks": list(task_ids), "feedback": seed_feedback, "attempt": attempt})
        _write(self.worktree, f"repair-{len(self.calls)}.txt", "fixed\n")
        _commit(self.worktree, f"repair {len(self.calls)}")
        for task in feature.tasks:
            if task.id in task_ids:
                task.status = "completed" if self.succeed else "failed"
        return WaveExecutionResult(wave_number=wave, task_ids=list(task_ids), results=[],
                                   all_succeeded=self.succeed)


def _orchestrator(repo_root: Path, worktree: Path, builder: Optional[_Builder] = None, resume: bool = False):
    return SimpleNamespace(repo_root=repo_root, resume=resume, fresh=False,
                           _execute_wave=builder or _Builder(worktree))


def _answers(monkeypatch: pytest.MonkeyPatch, answers: List[Any]) -> List[Dict[str, Any]]:
    seen: List[Dict[str, Any]] = []

    def _fake(orchestrator, feature, worktree, base, request, round_number, seconds):
        seen.append({"round": round_number, "request": request, "seconds": seconds})
        answer = answers.pop(0)
        if isinstance(answer, BaseException):
            raise answer
        return {"answer": answer, "seconds": 1.0, "prompt_chars": 10}

    monkeypatch.setattr(end_review, "_review_once", _fake)
    return seen


FAULT = "FAULT src/app.py:3 :: the count is off by one :: GET /count after adding a user"


def _record(repo_root: Path) -> Dict[str, Any]:
    return json.loads((end_review.record_dir(repo_root, FEATURE_ID) / "end_review.json").read_text())


def test_no_faults_ends_after_one_review_with_no_repair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worktree = _repo(tmp_path / "wt")
    builder = _Builder(worktree)
    seen = _answers(monkeypatch, ["NO FAULTS"])

    end_review.run_end_review(_orchestrator(tmp_path / "main", worktree, builder), _feature(),
                              SimpleNamespace(path=worktree), [])

    assert len(seen) == 1 and seen[0]["seconds"] == end_review.DEFAULT_REVIEW_SECONDS
    assert builder.calls == []
    out = end_review.record_dir(tmp_path / "main", FEATURE_ID)
    record = _record(tmp_path / "main")
    assert record["status"] == "finished"
    assert record["request"]["source"] == "feature file"
    assert record["pre_commit"] == (out / "pre_commit.txt").read_text().strip() == _git(worktree, "rev-parse", "HEAD")
    assert [r["faults"] for r in record["rounds"]] == [[]]
    assert (out / "review-1-answer.txt").read_text() == "NO FAULTS"


def test_at_most_two_repair_rounds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worktree = _repo(tmp_path / "wt")
    builder = _Builder(worktree)
    seen = _answers(monkeypatch, [FAULT, FAULT, FAULT])
    wave_results: List[Any] = []
    feature = _feature()

    end_review.run_end_review(_orchestrator(tmp_path / "main", worktree, builder), feature,
                              SimpleNamespace(path=worktree), wave_results)

    assert [s["round"] for s in seen] == [1, 2]
    assert [(c["wave"], c["tasks"], c["attempt"]) for c in builder.calls] == [
        (1, ["TASK-ER-002"], end_review.REPAIR_ATTEMPT + 1),
        (1, ["TASK-ER-002"], end_review.REPAIR_ATTEMPT + 2),
    ]
    assert "src/app.py:3: the count is off by one" in builder.calls[0]["feedback"]
    assert len(wave_results) == 2
    record = _record(tmp_path / "main")
    assert record["status"] == "finished"
    assert [r["repair"]["succeeded"] for r in record["rounds"]] == [True, True]
    assert record["last_commit"] == _git(worktree, "rev-parse", "HEAD")
    out = end_review.record_dir(tmp_path / "main", FEATURE_ID)
    assert sorted(p.name for p in out.iterdir()) == [
        "end_review.json", "pre_commit.txt", "repair-1-feedback.txt", "repair-2-feedback.txt",
        "review-1-answer.txt", "review-2-answer.txt",
    ]


class _Builder2(_Builder):
    """A builder whose repair turns succeed or fail in the order given."""

    def __init__(self, worktree: Path, outcomes: List[bool]) -> None:
        super().__init__(worktree)
        self.outcomes = outcomes

    def __call__(self, *args, **kwargs):
        self.succeed = self.outcomes.pop(0)
        return super().__call__(*args, **kwargs)


def test_a_failed_repair_repaired_again_leaves_only_the_latest_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = _repo(tmp_path / "wt")
    builder = _Builder2(worktree, [False, True])
    _answers(monkeypatch, [FAULT, FAULT])
    earlier = WaveExecutionResult(wave_number=1, task_ids=["TASK-ER-001", "TASK-ER-002"], results=[],
                                  all_succeeded=True)
    wave_results: List[Any] = [earlier]

    end_review.run_end_review(_orchestrator(tmp_path / "main", worktree, builder), _feature(),
                              SimpleNamespace(path=worktree), wave_results)

    assert len(wave_results) == 2 and wave_results[0] is earlier
    assert wave_results[1].all_succeeded is True
    assert [r["repair"]["succeeded"] for r in _record(tmp_path / "main")["rounds"]] == [False, True]


def test_a_failed_repair_not_repaired_again_stays(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worktree = _repo(tmp_path / "wt")
    builder = _Builder2(worktree, [False])
    _answers(monkeypatch, [FAULT, "NO FAULTS"])
    wave_results: List[Any] = []

    end_review.run_end_review(_orchestrator(tmp_path / "main", worktree, builder), _feature(),
                              SimpleNamespace(path=worktree), wave_results)

    assert [r.all_succeeded for r in wave_results] == [False]


def test_a_repair_then_no_faults_stops(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worktree = _repo(tmp_path / "wt")
    builder = _Builder(worktree)
    seen = _answers(monkeypatch, [FAULT, "NO FAULTS"])

    end_review.run_end_review(_orchestrator(tmp_path / "main", worktree, builder), _feature(),
                              SimpleNamespace(path=worktree), [])

    assert [s["round"] for s in seen] == [1, 2]
    assert len(builder.calls) == 1
    assert [bool(r.get("repair")) for r in _record(tmp_path / "main")["rounds"]] == [True, False]


def test_a_review_that_fails_repairs_nothing_and_never_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worktree = _repo(tmp_path / "wt")
    builder = _Builder(worktree)
    _answers(monkeypatch, [TimeoutError("the review ran out of time")])

    end_review.run_end_review(_orchestrator(tmp_path / "main", worktree, builder), _feature(),
                              SimpleNamespace(path=worktree), [])

    assert builder.calls == []
    record = _record(tmp_path / "main")
    assert record["rounds"][0]["error"].startswith("TimeoutError")
    assert record["status"] == "finished"


def test_skipped_when_a_task_did_not_complete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worktree = _repo(tmp_path / "wt")
    builder = _Builder(worktree)
    seen = _answers(monkeypatch, [FAULT])

    end_review.run_end_review(_orchestrator(tmp_path / "main", worktree, builder),
                              _feature(statuses=["completed", "failed"]), SimpleNamespace(path=worktree), [])

    assert seen == [] and builder.calls == []
    assert _record(tmp_path / "main")["status"].startswith("skipped: not every task completed")


def test_the_request_found_is_the_one_reviewed_and_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worktree = _repo(tmp_path / "wt")
    _write(worktree, f"feature_spec_inputs/{CORRELATION}.md", "Count users per day, please.\n")
    _commit(worktree, f"planning: feature plan {FEATURE_ID} for {CORRELATION} (Lane B 008)")
    seen = _answers(monkeypatch, ["NO FAULTS"])

    end_review.run_end_review(_orchestrator(tmp_path / "main", worktree), _feature(),
                              SimpleNamespace(path=worktree), [])

    assert seen[0]["request"] == "Count users per day, please.\n"
    assert _record(tmp_path / "main")["request"]["source"] == "planning commit"


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


def test_a_resumed_build_carries_on_with_the_same_two_round_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    worktree = _repo(tmp_path / "wt")
    main = tmp_path / "main"

    class _Interrupted(BaseException):
        """What a killed process looks like to the code after it: nothing more runs."""

    builder = _Builder(worktree)
    # First run: review 1 finds a fault, repair 1 completes, then the build is stopped during review 2.
    _answers(monkeypatch, [FAULT, _Interrupted()])
    with pytest.raises(_Interrupted):
        end_review.run_end_review(_orchestrator(main, worktree, builder), _feature(),
                                  SimpleNamespace(path=worktree), [])
    first = _record(main)
    pre_commit = first["pre_commit"]
    assert first["status"] == "running"
    assert len(first["rounds"]) == 2 and first["rounds"][0]["repair"]["succeeded"] is True
    assert not first["rounds"][1].get("reviewed")

    # Resumed: review 2 runs (not review 1 again), its repair is the last one.
    seen = _answers(monkeypatch, [FAULT, FAULT])
    end_review.run_end_review(_orchestrator(main, worktree, builder, resume=True), _feature(),
                              SimpleNamespace(path=worktree), [])

    assert [s["round"] for s in seen] == [2]
    assert len(builder.calls) == 2
    record = _record(main)
    assert record["status"] == "finished" and record["resumed"] == 1
    assert record["pre_commit"] == pre_commit
    assert (end_review.record_dir(main, FEATURE_ID) / "review-1-answer.txt").exists()

    # Resumed again after it finished: nothing more runs.
    seen = _answers(monkeypatch, [FAULT])
    end_review.run_end_review(_orchestrator(main, worktree, builder, resume=True), _feature(),
                              SimpleNamespace(path=worktree), [])
    assert seen == [] and len(builder.calls) == 2


def test_a_build_that_is_not_resumed_starts_a_new_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worktree = _repo(tmp_path / "wt")
    main = tmp_path / "main"
    _answers(monkeypatch, [FAULT, FAULT])
    end_review.run_end_review(_orchestrator(main, worktree), _feature(), SimpleNamespace(path=worktree), [])
    assert _record(main)["status"] == "finished"

    seen = _answers(monkeypatch, ["NO FAULTS"])
    end_review.run_end_review(_orchestrator(main, worktree), _feature(), SimpleNamespace(path=worktree), [])

    assert [s["round"] for s in seen] == [1]
    assert len(_record(main)["rounds"]) == 1
    out = end_review.record_dir(main, FEATURE_ID)
    assert not (out / "review-2-answer.txt").exists() and not (out / "repair-1-feedback.txt").exists()


def test_a_resume_onto_different_code_starts_a_new_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    worktree = _repo(tmp_path / "wt")
    main = tmp_path / "main"
    _answers(monkeypatch, [FAULT, FAULT])
    end_review.run_end_review(_orchestrator(main, worktree), _feature(), SimpleNamespace(path=worktree), [])

    other = _repo(tmp_path / "other")  # a new worktree: the earlier record's commits are not in it
    seen = _answers(monkeypatch, ["NO FAULTS"])
    end_review.run_end_review(_orchestrator(main, other, resume=True), _feature(), SimpleNamespace(path=other), [])

    assert [s["round"] for s in seen] == [1]
    assert _record(main)["pre_commit"] == _git(other, "rev-parse", "HEAD")


# ---------------------------------------------------------------------------
# Where the end review sits in the build
# ---------------------------------------------------------------------------


def _orchestrate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, specific_task: Optional[str] = None):
    from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

    orchestrator = FeatureOrchestrator.__new__(FeatureOrchestrator)
    feature, worktree = _feature(), SimpleNamespace(path=tmp_path)
    order: List[Any] = []
    orchestrator._setup_phase = lambda fid, base: (feature, worktree)  # type: ignore[method-assign]
    orchestrator._pinned_feature_branch = lambda wt: "autobuild/x"  # type: ignore[method-assign]
    orchestrator._wave_phase = lambda f, w, feature_check=True: order.append(("waves", feature_check)) or []  # type: ignore[method-assign]
    orchestrator._execute_single_task = lambda f, w, t: order.append(("one task", t)) or []  # type: ignore[method-assign]
    orchestrator._run_feature_check = lambda f, w, r: order.append("feature check")  # type: ignore[method-assign]
    orchestrator._finalize_phase = lambda f, r, w: order.append("finish") or SimpleNamespace(  # type: ignore[method-assign]
        status="completed", tasks_completed=2, total_tasks=2)
    monkeypatch.setattr(end_review, "run_end_review", lambda *a: order.append("end review"))
    orchestrator.orchestrate(FEATURE_ID, specific_task=specific_task)
    return order


def test_the_end_review_runs_after_the_waves_and_before_the_feature_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _orchestrate(tmp_path, monkeypatch) == [("waves", False), "end review", "feature check", "finish"]


def test_with_the_per_task_reviewer_back_the_build_is_as_before(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(end_review.PER_TASK_REVIEW_ENV, "1")

    assert _orchestrate(tmp_path, monkeypatch) == [("waves", True), "finish"]


def test_a_single_task_run_has_no_end_review(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert _orchestrate(tmp_path, monkeypatch, specific_task="TASK-ER-001") == [("one task", "TASK-ER-001"), "finish"]


def test_repair_1_fails_repair_2_succeeds_and_the_feature_check_still_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Codex, 12 November 2026: a superseded failed repair must not let the build finish
    without its whole-feature check. Repair 1 fails, repair 2 succeeds but leaves the
    feature broken: the check runs, fails, and the build does not complete."""
    from tests.orchestrator.test_feature_check import (
        _common_patches,
        _declaration,
        _make_feature,
        _make_orchestrator,
        _make_project,
        _make_worktree,
        _receipt,
        _WaveRecorder,
    )
    from guardkit.orchestrator.task_work_scope import register_fresh_checkout

    monkeypatch.setenv("GUARDKIT_FEATURE_CHECK_MAX_RETRIES", "0")
    repo_root, worktree_path = _make_project(tmp_path, declaration=_declaration("sh qa/feature-check.sh"))
    _write(worktree_path, "THE_FEATURE_IS_FIXED", "yes\n")
    _commit(worktree_path, "the finished feature")
    register_fresh_checkout(worktree_path, "HEAD")
    feature = _make_feature(worktree_path)
    feature.feature_files = []

    def _break(_index: int) -> None:
        (worktree_path / "THE_FEATURE_IS_FIXED").unlink(missing_ok=True)

    recorder = _WaveRecorder(worktree_path, on_reentry=_break)
    calls = {"n": 0}

    def _builder(wave_number, task_ids, feature_obj, worktree, seed_feedback=None, attempt=0):
        result = recorder(wave_number, task_ids, feature_obj, worktree, seed_feedback=seed_feedback,
                          attempt=attempt)
        calls["n"] += 1
        if calls["n"] == 2:  # the first repair turn fails
            for task in feature_obj.tasks:
                if task.id in task_ids:
                    task.status = "failed"
            return result.__class__(wave_number=wave_number, task_ids=list(task_ids),
                                    results=result.results, all_succeeded=False)
        return result

    _answers(monkeypatch, [FAULT, FAULT])
    orchestrator = _make_orchestrator(repo_root)
    worktree = _make_worktree(worktree_path)
    with ExitStack() as stack:
        for cm in _common_patches(orchestrator):
            stack.enter_context(cm)
        stack.enter_context(patch.object(orchestrator, "_execute_wave", side_effect=_builder))
        stack.enter_context(patch.object(orchestrator, "_display_summary"))
        stack.enter_context(patch.object(orchestrator, "_setup_phase", return_value=(feature, worktree)))
        result = orchestrator.orchestrate("FEAT-TEST")

    assert calls["n"] == 3, "the wave, then two repair turns"
    assert feature.tasks[0].status == "completed", "the second repair succeeded"
    assert _receipt(worktree_path)["status"] == "failed", "the whole-feature check ran on the repaired code"
    assert result.status == "failed"


def test_a_repair_that_breaks_the_feature_check_fails_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole-feature check runs on the repaired code, so a repair that breaks it is not merged."""
    from tests.orchestrator.test_feature_check import (
        _common_patches,
        _declaration,
        _make_feature,
        _make_orchestrator,
        _make_project,
        _make_worktree,
        _receipt,
        _WaveRecorder,
    )
    from guardkit.orchestrator.task_work_scope import register_fresh_checkout

    monkeypatch.setenv("GUARDKIT_FEATURE_CHECK_MAX_RETRIES", "0")
    repo_root, worktree_path = _make_project(tmp_path, declaration=_declaration("sh qa/feature-check.sh"))
    # The feature works when the tasks finish: the project's check passes on it.
    _write(worktree_path, "THE_FEATURE_IS_FIXED", "yes\n")
    _commit(worktree_path, "the finished feature")
    register_fresh_checkout(worktree_path, "HEAD")
    feature = _make_feature(worktree_path)
    feature.feature_files = []

    def _break(_index: int) -> None:
        (worktree_path / "THE_FEATURE_IS_FIXED").unlink(missing_ok=True)

    recorder = _WaveRecorder(worktree_path, on_reentry=_break)
    _answers(monkeypatch, [FAULT, "NO FAULTS"])
    orchestrator = _make_orchestrator(repo_root)
    worktree = _make_worktree(worktree_path)
    with ExitStack() as stack:
        for cm in _common_patches(orchestrator):
            stack.enter_context(cm)
        stack.enter_context(patch.object(orchestrator, "_execute_wave", side_effect=recorder))
        stack.enter_context(patch.object(orchestrator, "_display_summary"))
        stack.enter_context(patch.object(orchestrator, "_setup_phase", return_value=(feature, worktree)))
        result = orchestrator.orchestrate("FEAT-TEST")

    assert recorder.feedback[0] is None, "the wave ran as usual"
    assert recorder.feedback[1].startswith("The finished feature was reviewed as a whole")
    assert _receipt(worktree_path)["status"] == "failed"
    assert result.status == "failed"
