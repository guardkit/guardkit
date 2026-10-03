"""Integration tests for the claim_audit gate on the deterministic Coach path.

Proves TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT acceptance criteria
AC-003 / AC-005 / AC-006 / AC-007 are wired through CoachValidator,
plus the TASK-FIX-IGNR severity reclassification:

- AC-003: dropped paths produce a Coach ``claim_audit``-category issue.
  Genuine fabrication remains ``must_fix``; the gitignored-but-present
  subset (``claim_audit_gitignored``) is now ``should_fix`` and rides
  along to feedback without short-circuiting.
- AC-005: synthetic Player report claims a ``.gitignore``-d path →
  ``should_fix`` advisory (TASK-FIX-IGNR), not a turn-rejecting
  ``must_fix`` (which was the pre-IGNR behaviour).
- AC-006: zero claimed files → no claim_audit issue (gate stays out of
  the way of legitimately documentation-only turns).
- AC-007: every claimed file is stage-able → no claim_audit issue.

These tests use a real git repo to exercise actual gitignore filtering —
the FEAT-39E1 silent-loss class is by definition a Player-vs-git-config
disagreement, and a mock would hide rule drift.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import CoachValidator


# ---------------------------------------------------------------------------
# Selective subprocess mock
# ---------------------------------------------------------------------------
#
# CoachValidator runs both ``run_independent_tests`` (pytest) and
# ``_verify_claims_were_staged`` (``git status --porcelain=v1``). The
# existing test pattern in ``test_coach_honesty_restoration.py`` mocks
# subprocess.run uniformly — that would also intercept the git call and
# force every claimed path into the dropped set, masking real behaviour.
#
# Instead we capture the real ``subprocess.run`` before patching and
# delegate ``git`` invocations to the real binary while continuing to
# stub pytest.

_REAL_RUN = subprocess.run


def _selective_run(*args: Any, **kwargs: Any) -> Any:
    """side_effect that lets git through and mocks everything else."""
    if args:
        cmd = args[0]
    else:
        cmd = kwargs.get("args") or []
    if cmd and isinstance(cmd, (list, tuple)) and cmd[0] == "git":
        return _REAL_RUN(*args, **kwargs)
    # Stub pytest / coverage / anything else as a clean pass.
    return MagicMock(returncode=0, stdout="5 passed in 0.1s", stderr="")


# ---------------------------------------------------------------------------
# Real git worktree fixture
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return _REAL_RUN(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture
def git_worktree(tmp_path: Path) -> Path:
    """A real git repo with one base commit."""
    repo = tmp_path / "worktree"
    repo.mkdir()
    _git("init", "--initial-branch=main", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "README.md").write_text("base\n")
    _git("add", "README.md", cwd=repo)
    _git("commit", "-m", "base", cwd=repo)
    return repo


@pytest.fixture
def task_work_results_dir(git_worktree: Path) -> Path:
    results_dir = git_worktree / ".guardkit" / "autobuild" / "TASK-001"
    results_dir.mkdir(parents=True)
    return results_dir


def _passing_baseline(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """A task_work_results that would otherwise approve."""
    base: Dict[str, Any] = {
        "quality_gates": {
            "tests_passing": True,
            "tests_passed": 5,
            "tests_failed": 0,
            "coverage": 85,
            "coverage_met": True,
            "all_passed": True,
        },
        "code_review": {"score": 82, "solid": 85, "dry": 80, "yagni": 82},
        "plan_audit": {"status": "skipped", "violations": 0},
        "files_created": [],
        "files_modified": [],
        "tests_written": [],
        "tests_run": False,
        "test_output_summary": "",
        "completion_promises": [],
        "requirements_addressed": [],
        "requirements_met": ["AC-001"],
    }
    if extra:
        base.update(extra)
    return base


def _write_results(results_dir: Path, results: Dict[str, Any]) -> Path:
    results_path = results_dir / "task_work_results.json"
    results_path.write_text(json.dumps(results, indent=2))
    return results_path


def _task() -> Dict[str, Any]:
    return {"acceptance_criteria": ["AC-001"]}


# ---------------------------------------------------------------------------
# AC-003 / AC-005: gitignored Player file surfaces as a should_fix advisory
# (TASK-FIX-IGNR demoted this from must_fix to should_fix; the file IS
# on disk, the .gitignore is the bug, and turn-rejecting on the wrong
# turn produces the FEAT-39E1 adversarial blow-up. Coach now approves
# the turn while surfacing the gitignored claim as actionable feedback.)
# ---------------------------------------------------------------------------


def test_ac005_gitignored_file_triggers_claim_audit_feedback(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """The FEAT-39E1 reproducer end-to-end: file on disk, gitignored,
    Coach must surface a ``should_fix`` claim_audit advisory rather
    than a turn-rejecting ``must_fix`` (TASK-FIX-IGNR AC-1/AC-3)."""
    # Unanchored .gitignore rule (the same shape that bit study-tutor).
    (git_worktree / ".gitignore").write_text("adapters/\n")
    # Player creates the source module in the worktree.
    src = git_worktree / "src" / "study_tutor" / "adapters"
    src.mkdir(parents=True)
    (src / "manifest.py").write_text("class Manifest: pass\n")

    results = _passing_baseline({
        "files_created": ["src/study_tutor/adapters/manifest.py"],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    audit_issues = [
        i for i in result.issues if i.get("category") == "claim_audit"
    ]
    assert len(audit_issues) == 1, (
        f"Expected exactly one claim_audit issue, got: {result.issues}"
    )
    issue = audit_issues[0]
    # TASK-FIX-IGNR: gitignored-but-present is should_fix (advisory).
    assert issue["severity"] == "should_fix"
    assert issue["details"]["claim_type"] == "claim_audit_gitignored"
    assert "src/study_tutor/adapters/manifest.py" in issue["description"]
    # Matched rule is exposed in details for downstream surfacing.
    assert ".gitignore" in issue["details"]["ignore_rule"]
    assert "adapters/" in issue["details"]["ignore_rule"]
    # AC-6: project-root .gitignore match → rebase hint appears.
    assert "rebase the worktree onto main" in issue["description"]


# ---------------------------------------------------------------------------
# AC-006: zero-cardinality permissive
# ---------------------------------------------------------------------------


def test_ac006_zero_claimed_files_does_not_trigger_claim_audit(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """Documentation-only turn: zero file claims must not emit claim_audit
    feedback. (Other gates may still produce decisions; what matters here
    is that the claim_audit category is absent.)"""
    results = _passing_baseline()  # all file lists empty
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    audit_issues = [
        i for i in result.issues if i.get("category") == "claim_audit"
    ]
    assert audit_issues == [], (
        f"Zero-cardinality turn yielded spurious claim_audit issues: "
        f"{audit_issues}"
    )


# ---------------------------------------------------------------------------
# AC-007: all claimed files staged → no claim_audit issue
# ---------------------------------------------------------------------------


def test_ac007_all_files_stageable_does_not_trigger_claim_audit(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """Player creates real source + test files, no gitignore filter →
    claim_audit must remain silent."""
    (git_worktree / "src").mkdir()
    (git_worktree / "src" / "real.py").write_text("def real(): pass\n")
    (git_worktree / "tests").mkdir()
    (git_worktree / "tests" / "test_real.py").write_text(
        "def test_real(): assert True\n"
    )

    results = _passing_baseline({
        "files_created": ["src/real.py", "tests/test_real.py"],
        "completion_promises": [
            {
                "criterion_id": "AC-001",
                "status": "complete",
                "implementation_files": ["src/real.py"],
                "test_file": "tests/test_real.py",
            }
        ],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    audit_issues = [
        i for i in result.issues if i.get("category") == "claim_audit"
    ]
    assert audit_issues == [], (
        f"All-staged turn yielded spurious claim_audit issues: "
        f"{audit_issues}"
    )


# ---------------------------------------------------------------------------
# Critical claim_audit (genuine fabrication) short-circuits gate evaluation
# ---------------------------------------------------------------------------
# (TASK-FIX-IGNR: the gitignored subset no longer short-circuits — this
# test now covers the path-not-on-disk fabrication case which keeps the
# pre-IGNR contract.)


def test_claim_audit_short_circuits_gate_evaluation(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """A critical claim_audit issue (path absent from disk = genuine
    Player fabrication) must short-circuit before the independent-test
    gate runs. Signal: ``quality_gates`` and ``independent_tests`` are
    both None when claim_audit fires alone."""
    # Pure fabrication: path is NOT on disk. No .gitignore involved.
    results = _passing_baseline({
        "files_created": ["src/fabricated/missing.py"],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    assert result.decision == "feedback"
    assert result.quality_gates is None
    assert result.independent_tests is None
    audit_issues = [
        i for i in result.issues if i.get("category") == "claim_audit"
    ]
    assert len(audit_issues) == 1
    assert audit_issues[0]["severity"] == "must_fix"
    assert audit_issues[0]["details"]["claim_type"] == "claim_audit"


# ---------------------------------------------------------------------------
# TASK-FIX-IGNR AC-3: gitignored claim_audit does NOT short-circuit
# ---------------------------------------------------------------------------


def test_gitignored_claim_audit_does_not_short_circuit(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """The gitignored subset rides along to feedback as ``should_fix``
    rather than short-circuiting. With a passing-baseline task_work
    result the rest of the gates evaluate normally and ``quality_gates``
    / ``independent_tests`` are populated, not None."""
    (git_worktree / ".gitignore").write_text("adapters/\n")
    src = git_worktree / "src" / "adapters"
    src.mkdir(parents=True)
    (src / "manifest.py").write_text("class Manifest: pass\n")

    results = _passing_baseline({
        "files_created": ["src/adapters/manifest.py"],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    # AC-3: short-circuit did NOT fire — downstream gates ran.
    assert result.quality_gates is not None
    assert result.independent_tests is not None
    # The advisory still surfaces in the issue list as should_fix.
    audit_issues = [
        i for i in result.issues if i.get("category") == "claim_audit"
    ]
    assert len(audit_issues) == 1
    assert audit_issues[0]["severity"] == "should_fix"
    assert audit_issues[0]["details"]["claim_type"] == "claim_audit_gitignored"


# ---------------------------------------------------------------------------
# Critical claim_audit retains must_fix even when only one discrepancy fires
# (i.e. the FEAT-FFC3 single-discrepancy demotion does NOT apply to a
# genuinely-fabricated claim_audit; TASK-FIX-IGNR's gitignored demotion is
# a separate, narrower carve-out keyed on claim_type, not count.)
# ---------------------------------------------------------------------------


def test_single_claim_audit_not_demoted_to_should_fix(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """The FEAT-FFC3 demotion (single ``file_existence`` → should_fix)
    must not apply to genuinely-fabricated ``claim_audit`` (path absent
    from disk): even one dropped path is enough signal to reject the
    turn. TASK-FIX-IGNR's demotion is keyed on
    ``claim_type == "claim_audit_gitignored"``, not on the count, so
    fabrication remains must_fix regardless of cardinality."""
    # Pure fabrication: no file on disk, no .gitignore.
    results = _passing_baseline({
        "files_created": ["src/fabricated/missing.py"],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    audit_issues = [
        i for i in result.issues if i.get("category") == "claim_audit"
    ]
    assert len(audit_issues) == 1
    assert audit_issues[0]["severity"] == "must_fix"
    assert audit_issues[0]["details"]["claim_type"] == "claim_audit"


# ---------------------------------------------------------------------------
# TASK-FIX-CAUD-J6F1 AC-006: FEAT-JARVIS-006 fail-run-1 replay
#
# The Player report on the failed run carried the same staged file under
# both absolute and relative form, plus the harness-owned per-turn
# artefact under its absolute path. Pre-fix Coach raised three critical
# claim_audit discrepancies (one per absolute claim) and short-circuited
# the gate. Post-fix:
#   * The duplicated source/test files dedupe (AC-001 normalisation).
#   * The harness-owned per-turn JSON is allowlisted (AC-003b).
#   * Decision is approve, no must_fix claim_audit issue.
# ---------------------------------------------------------------------------


def test_j6f1_player_turn1_replay_no_claim_audit_issue(
    git_worktree: Path, task_work_results_dir: Path
) -> None:
    """Replay the J6F1 player_turn_1 shape end-to-end against the
    deterministic Coach path. Asserts the FEAT-JARVIS-006 fail-run-1
    incident no longer fires a critical claim_audit discrepancy.
    """
    # Stage the chat handler + tests under the same paths the Player
    # reported. These exist on disk AND will be in ``git status
    # --porcelain`` (untracked-not-ignored), so the audit MUST classify
    # them as staged.
    src = git_worktree / "src" / "jarvis" / "infrastructure"
    src.mkdir(parents=True)
    (src / "chat_handler.py").write_text("class ChatHandler: ...\n")
    tests = git_worktree / "tests" / "unit" / "infrastructure"
    tests.mkdir(parents=True)
    (tests / "test_chat_handler.py").write_text(
        "def test_handler(): assert True\n"
    )

    # Also stage the harness-owned per-turn artefact under its absolute
    # path — the J6F1 incident's third flagged path. The orchestrator
    # writes this file at an absolute path which round-trips into the
    # Player's files_created. AC-003b's allowlist must drop it.
    autobuild_dir = git_worktree / ".guardkit" / "autobuild" / "TASK-001"
    autobuild_dir.mkdir(parents=True, exist_ok=True)
    abs_player_turn = autobuild_dir / "player_turn_1.json"
    abs_player_turn.write_text("{}\n")

    # The implementation plan that task-work writes per the J6F1 fail-run-1
    # report (F4 bucket A: yes-on-disk / yes-staged / no-flagged). Created
    # so the replay matches the actual fixture shape.
    plan_dir = git_worktree / ".claude" / "task-plans"
    plan_dir.mkdir(parents=True)
    (plan_dir / "TASK-001-implementation-plan.md").write_text("# plan\n")

    abs_chat_handler = str(src / "chat_handler.py")
    abs_test = str(tests / "test_chat_handler.py")

    # The exact J6F1 shape: each file claimed under both absolute and
    # relative form. Pre-fix this raised 3× critical claim_audit (one
    # per absolute entry); post-fix all three are normalised away.
    results = _passing_baseline({
        "files_created": [
            ".claude/task-plans/TASK-001-implementation-plan.md",
            abs_chat_handler,
            abs_test,
            str(abs_player_turn),
            "src/jarvis/infrastructure/chat_handler.py",
            "tests/unit/infrastructure/test_chat_handler.py",
        ],
    })
    _write_results(task_work_results_dir, results)

    with patch("subprocess.run", side_effect=_selective_run):
        validator = CoachValidator(str(git_worktree))
        result = validator.validate("TASK-001", 1, _task())

    # Either no claim_audit issue at all, or any that surface are
    # advisory should_fix — never the J6F1-shape critical must_fix
    # that drove the unrecoverable_stall.
    audit_issues = [
        i for i in result.issues if i.get("category") == "claim_audit"
    ]
    must_fix_audit = [
        i for i in audit_issues if i.get("severity") == "must_fix"
    ]
    assert must_fix_audit == [], (
        f"J6F1 reproducer regressed: post-fix replay must NOT produce "
        f"a must_fix claim_audit issue. Got: {must_fix_audit}"
    )
    # The .claude/task-plans/... entry isn't on disk so it's a genuine
    # file_existence concern — but the J6F1 reproducer only requires
    # that the absolute-path/harness paths stop firing, not that every
    # ancillary path becomes clean. Pin only the regression we fixed.
    audit_paths_must_fix = [
        i["details"]["player_claim"] for i in must_fix_audit
    ]
    j6f1_paths = [
        abs_chat_handler,
        abs_test,
        str(abs_player_turn),
    ]
    for p in j6f1_paths:
        assert p not in " ".join(audit_paths_must_fix), (
            f"J6F1 path {p} produced a must_fix audit issue; expected "
            f"normalisation/allowlist to suppress it."
        )


# ---------------------------------------------------------------------------
# 3 October 2026: throwaway scripts (FEAT-E592, FEAT-D586)
#
# Through the real path: the builder's tool events are processed by the
# stream loop, the turn report is built from both the results file and the
# returned result, and the Coach runs its honesty check and evidence step.
# The events are the local builder's delivery order: every tool use, then
# every tool result; a write the factory refused (outside the worktree)
# comes back with ``is_error=True``. File changes happen before the events
# arrive, as they do there. In E592 the builder's /tmp script was refused,
# it wrote the script inside the worktree instead, ran it and deleted it,
# and the attempt was thrown away. Now it has a scratch folder outside the
# project and the refused write never reaches the list.
# ---------------------------------------------------------------------------


def _tool_use(call_id: str, name: str, path: Any) -> Any:
    from guardkit.orchestrator.harness.adapter import ToolUseEvent

    return ToolUseEvent(
        tool_use_id=call_id,
        name=name,
        input={"file_path": str(path), "content": "x = 1\n"},
    )


def _tool_result(call_id: str, is_error: bool = False) -> Any:
    from guardkit.orchestrator.harness.adapter import ToolResultEvent

    return ToolResultEvent(
        tool_use_id=call_id,
        content="Error: refusing to write" if is_error else "Updated file",
        is_error=is_error,
    )


_TURN_TEXT = "5 tests passed, 0 tests failed\nAll quality gates passed"


def _run_builder_turn(
    worktree: Path,
    task_id: str,
    steps: list,
    final_text: str = _TURN_TEXT,
    provides_scratch: Any = True,
) -> Any:
    """Stream processing and report construction, as one builder turn.

    ``provides_scratch`` stands in for the factory backend having accepted
    the prepared scratch folder (``backend.default.scratch_root``); a path
    makes the stand-in report that path instead.
    """
    import asyncio
    from types import SimpleNamespace

    from guardkit.orchestrator.agent_invoker import AgentInvoker
    from guardkit.orchestrator.harness.adapter import (
        AssistantMessageEvent,
        ResultMessageEvent,
    )
    from guardkit.orchestrator.paths import prepare_builder_scratch_dir

    class LocalReplay:
        supports_resume = False

        def __init__(self) -> None:
            scratch = (
                provides_scratch
                if isinstance(provides_scratch, Path)
                else prepare_builder_scratch_dir(worktree)
            )
            if provides_scratch and scratch is not None:
                self.backend = SimpleNamespace(
                    default=SimpleNamespace(scratch_root=scratch)
                )

        async def invoke(self, prompt, role, tools, cwd, *, timeout_seconds):
            for step in steps:
                if callable(step):
                    step()
                    continue
                yield step
            yield AssistantMessageEvent(text=final_text, raw=None)
            yield ResultMessageEvent(session_id=None, raw=None)

        async def cancel(self) -> None:
            return None

    invoker = AgentInvoker(
        worktree_path=worktree, max_turns_per_agent=30, sdk_timeout_seconds=60
    )
    with patch(
        "guardkit.orchestrator.agent_invoker.select_harness",
        return_value=LocalReplay(),
    ):
        result = asyncio.run(
            invoker._invoke_task_work_implement(task_id=task_id, mode="standard")
        )
    assert result.success is True
    invoker._create_player_report_from_task_work(task_id, 1, result)
    return result


def _make(path: Path) -> Any:
    def run() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x = 1\n")

    return run


def _remove(path: Path) -> Any:
    return lambda: path.unlink()


def _e592_steps(worktree: Path, task: str) -> list:
    """A refused /tmp script, the same script in the scratch folder, run and
    deleted there, and the real product files."""
    from guardkit.orchestrator.paths import builder_scratch_dir

    script = builder_scratch_dir(worktree) / f"verify_{task}.py"
    product = worktree / "src" / "users" / "routes.py"
    test = worktree / "tests" / "test_routes.py"
    return [
        _make(script),
        _make(product),
        _make(test),
        _remove(script),
        _tool_use("c45", "write_file", f"/tmp/verify_{task}.py"),
        _tool_use("c46", "write_file", script),
        _tool_use("c47", "write_file", product),
        _tool_use("c48", "write_file", test),
        _tool_result("c45", is_error=True),
        _tool_result("c46"),
        _tool_result("c47"),
        _tool_result("c48"),
    ]


def _coach(worktree: Path, task_id: str) -> tuple:
    with patch("subprocess.run", side_effect=_selective_run):
        result = CoachValidator(str(worktree)).validate(task_id, 1, _task())
        bundle = CoachValidator(str(worktree)).gather_evidence(task_id, 1, _task())
    return result, bundle


def _records(worktree: Path, task_id: str) -> list:
    base = worktree / ".guardkit" / "autobuild" / task_id
    return [
        json.loads((base / "task_work_results.json").read_text()),
        json.loads((base / "player_turn_1.json").read_text()),
    ]


def _honesty_must_fix(result: Any) -> list:
    return [
        i for i in result.issues
        if i.get("severity") == "must_fix"
        and i.get("category") in ("honesty", "claim_audit")
    ]


@pytest.mark.parametrize("task", ["e592_002", "e592_003"])
def test_e592_shape_with_scratch_folder_passes_honesty(
    git_worktree: Path, task: str
) -> None:
    task_id = f"TASK-{task.upper()}"
    result = _run_builder_turn(git_worktree, task_id, _e592_steps(git_worktree, task))

    # The returned result, the results file and the turn report all agree.
    for files in [result.output["files_created"]] + [
        r["files_created"] + r["files_modified"]
        for r in _records(git_worktree, task_id)
    ]:
        assert not any("verify_" in path for path in files), files
        assert "src/users/routes.py" in files

    coach_result, bundle = _coach(git_worktree, task_id)
    assert _honesty_must_fix(coach_result) == [], coach_result.issues
    assert coach_result.quality_gates is not None
    assert bundle.gathering_status != "partial_honesty_abort"


def test_fabricated_src_claim_still_aborts(git_worktree: Path) -> None:
    """A product file claimed in the builder's own words and in a criterion,
    never written: still caught, scratch folder or not."""
    task_id = "TASK-E592-003"
    report = git_worktree / ".guardkit" / "autobuild" / task_id / "player_turn_1.json"

    def builder_writes_its_report() -> None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            json.dumps(
                {
                    "completion_promises": [
                        {
                            "criterion_id": "AC-001",
                            "status": "complete",
                            "implementation_files": ["src/users/not_written.py"],
                        }
                    ]
                }
            )
        )

    _run_builder_turn(
        git_worktree,
        task_id,
        [builder_writes_its_report] + _e592_steps(git_worktree, "e592_003"),
        final_text="Created: src/users/not_written.py\n" + _TURN_TEXT,
    )

    coach_result, bundle = _coach(git_worktree, task_id)
    assert coach_result.quality_gates is None
    assert "src/users/not_written.py" in json.dumps(_honesty_must_fix(coach_result))
    assert bundle.gathering_status == "partial_honesty_abort"


def test_deleted_project_file_still_trips_the_checks_unchanged(
    git_worktree: Path,
) -> None:
    """Unchanged on purpose: a throwaway script written INSIDE the project
    and deleted stays listed, and so does a tracked file the builder
    deleted; the existence and claim checks still report them."""
    task_id = "TASK-E592-OLD-SHAPE"
    script = git_worktree / ".tmp" / "verify.py"
    (git_worktree / "a.md").write_text("a\n")
    subprocess.run(["git", "add", "a.md"], cwd=git_worktree, check=True)
    subprocess.run(["git", "commit", "-m", "a"], cwd=git_worktree, check=True,
                   capture_output=True)
    steps = [
        _make(script),
        _remove(script),
        _remove(git_worktree / "a.md"),
        _tool_use("c1", "write_file", script),
        _tool_use("c2", "edit_file", git_worktree / "a.md"),
        _tool_result("c1"),
        _tool_result("c2"),
    ]
    _run_builder_turn(git_worktree, task_id, steps)

    results, report = _records(git_worktree, task_id)
    assert ".tmp/verify.py" in results["files_created"]
    assert "a.md" in results["files_modified"]
    coach_result, bundle = _coach(git_worktree, task_id)
    assert coach_result.quality_gates is None
    assert bundle.gathering_status == "partial_honesty_abort"


def test_symlinked_scratch_folder_cannot_hide_a_fabricated_src_claim(
    git_worktree: Path,
) -> None:
    """If the scratch folder is a symlink into the project, it is not used
    at all, and an unwritten src file claimed in the builder's own words is
    still a critical finding, even with a harness claiming to allow it."""
    from guardkit.orchestrator.paths import builder_scratch_dir

    task_id = "TASK-SYMLINKED-SCRATCH"
    (git_worktree / "src").mkdir()
    builder_scratch_dir(git_worktree).symlink_to(git_worktree / "src")

    _run_builder_turn(
        git_worktree,
        task_id,
        [],
        final_text="Created: src/not_written.py\n" + _TURN_TEXT,
        provides_scratch=builder_scratch_dir(git_worktree),
    )

    results, report = _records(git_worktree, task_id)
    assert "src/not_written.py" in results["files_created"]
    coach_result, bundle = _coach(git_worktree, task_id)
    assert coach_result.quality_gates is None
    assert "src/not_written.py" in json.dumps(_honesty_must_fix(coach_result))
    assert bundle.gathering_status == "partial_honesty_abort"


def test_claim_through_a_link_inside_the_scratch_folder_still_aborts(
    git_worktree: Path,
) -> None:
    """``<scratch>/project`` pointing at ``src``: an unwritten file claimed
    through it in the builder's own words reaches the Coach and is caught."""
    from guardkit.orchestrator.paths import prepare_builder_scratch_dir

    task_id = "TASK-SCRATCH-LINK"
    (git_worktree / "src").mkdir()
    scratch = prepare_builder_scratch_dir(git_worktree)
    (scratch / "project").symlink_to(git_worktree / "src")
    claimed = scratch / "project" / "not_written.py"

    _run_builder_turn(
        git_worktree,
        task_id,
        [],
        final_text=f"Created: {claimed}\n" + _TURN_TEXT,
    )

    results, report = _records(git_worktree, task_id)
    assert any("not_written.py" in path for path in results["files_created"])
    coach_result, bundle = _coach(git_worktree, task_id)
    assert coach_result.quality_gates is None
    assert "not_written.py" in json.dumps(_honesty_must_fix(coach_result))
    assert bundle.gathering_status == "partial_honesty_abort"


def test_scratch_folder_swapped_for_a_symlink_mid_run_still_aborts(
    git_worktree: Path,
) -> None:
    """The checked folder replaced by a symlink to ``src`` during the run: an
    unwritten file claimed in it in the builder's own words reaches the
    Coach and is caught."""
    import shutil

    from guardkit.orchestrator.paths import prepare_builder_scratch_dir

    task_id = "TASK-SCRATCH-SWAP"
    (git_worktree / "src").mkdir()
    scratch = prepare_builder_scratch_dir(git_worktree)
    claimed = scratch / "not_written.py"

    def swap() -> None:
        shutil.rmtree(scratch)
        scratch.symlink_to(git_worktree / "src")

    _run_builder_turn(
        git_worktree,
        task_id,
        [swap],
        final_text=f"Created: {claimed}\n" + _TURN_TEXT,
        provides_scratch=scratch,
    )

    results, report = _records(git_worktree, task_id)
    assert any("not_written.py" in path for path in results["files_created"])
    coach_result, bundle = _coach(git_worktree, task_id)
    assert coach_result.quality_gates is None
    assert "not_written.py" in json.dumps(_honesty_must_fix(coach_result))
    assert bundle.gathering_status == "partial_honesty_abort"


def test_scratch_folder_removed_by_the_builder_still_passes_honesty(
    git_worktree: Path,
) -> None:
    """The builder writes a script in the scratch folder and a product file,
    then removes the whole scratch folder: the script stays off the list and
    the product file stays on it."""
    import shutil

    from guardkit.orchestrator.paths import prepare_builder_scratch_dir

    task_id = "TASK-SCRATCH-REMOVED"
    scratch = prepare_builder_scratch_dir(git_worktree)
    script = scratch / "verify.py"
    product = git_worktree / "src" / "app.py"
    steps = [
        _make(script),
        _make(product),
        lambda: shutil.rmtree(scratch),
        _tool_use("c1", "write_file", script),
        _tool_use("c2", "write_file", product),
        _tool_result("c1"),
        _tool_result("c2"),
    ]

    result = _run_builder_turn(
        git_worktree, task_id, steps, provides_scratch=scratch
    )

    for files in [result.output["files_created"]] + [
        r["files_created"] + r["files_modified"]
        for r in _records(git_worktree, task_id)
    ]:
        assert not any("verify.py" in path for path in files), files
        assert "src/app.py" in files
    coach_result, bundle = _coach(git_worktree, task_id)
    assert _honesty_must_fix(coach_result) == [], coach_result.issues
    assert coach_result.quality_gates is not None
    assert bundle.gathering_status != "partial_honesty_abort"
