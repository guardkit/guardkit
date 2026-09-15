"""End-to-end: plan-audit gate on producer → Coach path.

TASK-FIX-RWOP1.3.2 wires ``execute_phase_5_5_plan_audit`` (non-interactive
mode) into ``AgentInvoker._write_task_work_results``. Without this wire
the ``plan_audit`` block in task_work_results.json is the Player LLM's
self-report — the Player can emit ``"violations": []`` regardless of
whether the worktree matches the approved plan. The producer fold makes
the deterministic auditor's verdict the authoritative source, overriding
any Player-supplied block.

This test pins both sides of that wire:

1. Producer: a saved plan + extra files in the worktree → the on-disk
   ``task_work_results.json plan_audit`` block carries
   ``status == "violation"``, ``severity == "high"``, and the extra file
   paths. A Player-supplied ``plan_audit`` block with ``violations == 0``
   is overridden by the deterministic output.
2. Coach: a violation block → ``CoachValidator`` returns a feedback
   decision whose issues name the extras and escalate ``severity`` to
   ``must_fix``.

See ``docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md``
Finding #5 and the TASK-FIX-3C9D producer-runs-gate reference.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


TASK_ID = "TASK-RWOP132-TEST"


def _init_git_repo(root: Path) -> None:
    """Make ``root`` a real repository with an identity of its own.

    The audit asks git which files this task made and changed, so a fixture
    without a repository is not a fixture of anything. The identity is set
    here so the test does not depend on the host's git configuration.
    """
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    def run(*args: str) -> None:
        subprocess.run(args, cwd=root, check=True, capture_output=True, env=env)

    run("git", "init", "-q")
    run("git", "config", "user.email", "test@example.com")
    run("git", "config", "user.name", "Test")
    run("git", "config", "commit.gpgsign", "false")


def _commit_everything(root: Path, message: str) -> str:
    """Commit the whole worktree and return the commit it made."""
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", message], cwd=root, check=True,
        capture_output=True,
    )
    done = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True,
    )
    return done.stdout.strip()


def _write_checkpoint(root: Path, task_id: str, commit: str) -> None:
    """Write the end-of-turn checkpoint record the build loop writes."""
    path = root / ".guardkit" / "autobuild" / task_id / "checkpoints.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "checkpoints": [{"turn": 1, "commit_hash": commit}],
                "last_updated": "2026-09-15T00:00:00Z",
            }
        )
    )


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Isolated worktree root, a real repository with one commit behind it."""
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("the repository before this task\n")
    _commit_everything(tmp_path, "before this task")
    return tmp_path


@pytest.fixture
def invoker(worktree: Path) -> AgentInvoker:
    return AgentInvoker(worktree_path=worktree)


def _seed_plan(worktree: Path, planned_files: list[str]) -> Path:
    """Write a minimal legacy-JSON plan into the worktree's docs/state.

    The JSON path is preferred over markdown here because the auditor's
    workspace-root-aware ``_load_plan`` (TASK-FIX-RWOP1.3.2) reads JSON
    directly when a markdown plan isn't present, and building a full
    frontmatter-parsed markdown plan is overkill for a fixture.
    """
    state_dir = worktree / "docs" / "state" / TASK_ID
    state_dir.mkdir(parents=True, exist_ok=True)
    plan_path = state_dir / "implementation_plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "task_id": TASK_ID,
                "saved_at": "2026-04-23T00:00:00Z",
                "version": 1,
                "plan": {
                    "files_to_create": planned_files,
                    "files_to_modify": [],
                    "external_dependencies": [],
                    "estimated_loc": 100,
                    "estimated_duration": "4 hours",
                },
            },
            indent=2,
        )
    )
    return plan_path


def _create_src_files(worktree: Path, rel_paths: list[str]) -> None:
    """Create real files under the worktree so the auditor's scan finds them.

    The auditor scans patterns including ``src/**/*.py`` — fixtures need
    real files on disk because the audit reads the filesystem, not the
    Player report.
    """
    for rel in rel_paths:
        p = worktree / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {rel}\npass\n")


class TestProducerWritesPlanAuditBlock:
    """Producer fold: plan vs actual comparison → deterministic verdict on disk."""

    def test_extras_in_worktree_mark_violation_and_name_files(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Plan expects 2 files; worktree actually has 5 (3 extras beyond
        # the planned pair). 3 extras trips the auditor's files-extras
        # high-severity threshold (>2 extras), which drives overall
        # severity to "high" and the producer block to status="violation".
        planned = [
            "src/feature.py",
            "src/helper.py",
        ]
        actual_extras = [
            "src/unexpected_one.py",
            "src/unexpected_two.py",
            "src/unexpected_three.py",
        ]
        _seed_plan(worktree, planned)
        _create_src_files(worktree, planned + actual_extras)

        # Player's self-report claims no violations — this is the exact
        # scenario the task is guarding against. The producer wire must
        # override this block with the deterministic auditor's output.
        result_data = {
            "phases": {
                "phase_3": {"detected": True, "completed": True, "text": "Phase 3"},
                "phase_4": {"detected": True, "completed": True, "text": "Phase 4"},
                "phase_5": {"detected": True, "completed": True, "text": "Phase 5"},
            },
            "tests_passed": 5,
            "tests_failed": 0,
            "coverage": 85.0,
            "quality_gates_passed": True,
            "files_modified": [],
            "files_created": planned,  # Player lies: reports only 2 files
            "plan_audit": {"violations": 0, "file_count_match": True},
        }

        results_path = invoker._write_task_work_results(
            TASK_ID, result_data, documentation_level="standard"
        )

        assert results_path.exists()
        on_disk = json.loads(results_path.read_text())

        plan_audit = on_disk.get("plan_audit")
        assert plan_audit is not None, "plan_audit block must be persisted"
        assert plan_audit["status"] == "violation", (
            "3 extras → files-extras severity=high → overall severity=high "
            "→ status=violation (Coach-blocking)"
        )
        assert plan_audit["severity"] == "high"
        assert plan_audit["violations"] >= 1

        extras = set(plan_audit["extra_files"])
        # All three planted extras must be named so the Player's next
        # turn has actionable feedback, not just a count.
        for extra in actual_extras:
            assert extra in extras, (
                f"extra file {extra} must appear in plan_audit.extra_files"
            )

    def test_player_supplied_plan_audit_is_overridden(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Same scenario as above but asserting specifically that the
        # Player-supplied {violations: 0, file_count_match: True} block
        # is thrown away. The producer fold owns the plan_audit key.
        _seed_plan(worktree, ["src/a.py"])
        _create_src_files(
            worktree,
            [
                "src/a.py",
                "src/scope_creep_1.py",
                "src/scope_creep_2.py",
                "src/scope_creep_3.py",
            ],
        )

        result_data = {
            "phases": {
                "phase_3": {"detected": True, "completed": True, "text": "Phase 3"},
                "phase_4": {"detected": True, "completed": True, "text": "Phase 4"},
                "phase_5": {"detected": True, "completed": True, "text": "Phase 5"},
            },
            "plan_audit": {
                "violations": 0,
                "file_count_match": True,
                "player_claim": "no scope creep here, officer",
            },
        }

        results_path = invoker._write_task_work_results(
            TASK_ID, result_data, documentation_level="standard"
        )

        plan_audit = json.loads(results_path.read_text())["plan_audit"]
        # The Player's custom key must not leak through.
        assert "player_claim" not in plan_audit
        assert plan_audit["status"] == "violation"
        assert plan_audit["severity"] == "high"

    def test_no_plan_on_disk_marks_skipped(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # Autobuild with pre-loop disabled (no --design-only run) won't
        # write a plan. The auditor must not fail the gate on absent
        # data — `skipped` is the informational escape hatch.
        result_data = {
            "phases": {
                "phase_3": {"detected": True, "completed": True, "text": "Phase 3"},
                "phase_4": {"detected": True, "completed": True, "text": "Phase 4"},
                "phase_5": {"detected": True, "completed": True, "text": "Phase 5"},
            },
            "tests_passed": 5,
            "tests_failed": 0,
        }

        results_path = invoker._write_task_work_results(
            TASK_ID, result_data, documentation_level="standard"
        )

        plan_audit = json.loads(results_path.read_text())["plan_audit"]
        assert plan_audit["status"] == "skipped"
        assert plan_audit["severity"] is None
        assert plan_audit["violations"] == 0
        assert plan_audit["extra_files"] == []

    def test_auditor_crash_records_auditor_error(
        self, invoker: AgentInvoker, worktree: Path, monkeypatch
    ):
        # The gate must never block artefact emission — if the auditor
        # itself raises, the producer records auditor_error and writes
        # the file anyway, matching the validator_error invariant on
        # the agent_invocations gate.
        def _boom(*_args, **_kwargs):
            raise RuntimeError("simulated auditor crash")

        monkeypatch.setattr(
            "guardkit.orchestrator.agent_invoker.execute_phase_5_5_plan_audit",
            _boom,
        )

        _seed_plan(worktree, ["src/feature.py"])

        result_data = {
            "phases": {
                "phase_3": {"detected": True, "completed": True, "text": "Phase 3"},
                "phase_4": {"detected": True, "completed": True, "text": "Phase 4"},
                "phase_5": {"detected": True, "completed": True, "text": "Phase 5"},
            }
        }
        results_path = invoker._write_task_work_results(
            TASK_ID, result_data, documentation_level="standard"
        )

        plan_audit = json.loads(results_path.read_text())["plan_audit"]
        assert plan_audit["status"] == "auditor_error"
        assert "simulated auditor crash" in plan_audit["message"]


DECLARING_TASK_ID = "TASK-DECLARES-FILES"


def _write_task_document(
    worktree: Path,
    task_id: str,
    creates: list[str],
    modifies: list[str],
) -> Path:
    """Write a task document that declares the files it will touch."""
    def _section(paths: list[str]) -> str:
        if not paths:
            return "- _none_\n"
        return "".join(f"- `{path}`\n" for path in paths)

    task_dir = worktree / "tasks" / "in_progress"
    task_dir.mkdir(parents=True, exist_ok=True)
    task_file = task_dir / f"{task_id}.md"
    task_file.write_text(
        "---\n"
        f"id: {task_id}\n"
        "title: Add the daily counts endpoint\n"
        "status: in_progress\n"
        "task_type: feature\n"
        "---\n\n"
        "Add the endpoint the request asks for.\n\n"
        "## Files to Create\n\n"
        f"{_section(creates)}\n"
        "## Files to Modify\n\n"
        f"{_section(modifies)}\n"
        "## Acceptance Criteria\n\n"
        "- [ ] AC-1: the endpoint answers.\n"
    )
    return task_file


def _minimal_result_data() -> dict:
    """The player's own report, with its plan-audit claim of innocence."""
    return {
        "phases": {
            "phase_3": {"detected": True, "completed": True, "text": "Phase 3"},
            "phase_4": {"detected": True, "completed": True, "text": "Phase 4"},
            "phase_5": {"detected": True, "completed": True, "text": "Phase 5"},
        },
        "tests_passed": 5,
        "tests_failed": 0,
        "coverage": 85.0,
        "quality_gates_passed": True,
        "plan_audit": {"violations": 0, "file_count_match": True},
    }


class TestAuditComparesAgainstTheTaskDocument:
    """The plan of record is the task document, on every path.

    Before this, the audit compared the build against the player's own note of
    what it meant to touch - which is a build marking its own homework - and
    it consulted the task document only when no note existed at all.
    """

    def test_the_task_document_grades_even_when_the_player_wrote_a_note(
        self, invoker: AgentInvoker, worktree: Path
    ):
        # The task document declares two files.
        _write_task_document(
            worktree,
            DECLARING_TASK_ID,
            creates=["src/users/router.py"],
            modifies=["src/users/crud.py"],
        )
        # The player's own note says all five were the plan all along.
        sprawl = [
            "src/analytics/service.py",
            "tests/test_analytics.py",
            "migrations/0001_add_users_index.py",
        ]
        state_dir = worktree / "docs" / "state" / DECLARING_TASK_ID
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "implementation_plan.json").write_text(
            json.dumps(
                {
                    "task_id": DECLARING_TASK_ID,
                    "plan": {
                        "files_to_create": ["src/users/router.py"] + sprawl,
                        "files_to_modify": ["src/users/crud.py"],
                        "external_dependencies": [],
                        "estimated_loc": 100,
                        "estimated_duration": "1 hour",
                    },
                },
                indent=2,
            )
        )
        # A pre-existing file the task legitimately changes.
        _create_src_files(worktree, ["src/users/crud.py"])
        _commit_everything(worktree, "the file this task will change")

        # The build: the declared file, the declared change, and three files
        # nobody declared - one of them a test, one of them a migration.
        _create_src_files(worktree, ["src/users/router.py"] + sprawl)
        (worktree / "src" / "users" / "crud.py").write_text("# changed\npass\n")

        results_path = invoker._write_task_work_results(
            DECLARING_TASK_ID, _minimal_result_data(), documentation_level="standard"
        )
        block = json.loads(results_path.read_text())["plan_audit"]

        assert block["planned_files_source"] == "the task document"
        assert block["status"] == "violation"
        assert block["severity"] == "high"
        assert sorted(block["extra_files"]) == sorted(sprawl), (
            "the three files the task document never named are the sprawl, "
            "whatever the player's own note claims"
        )
        assert "tests/test_analytics.py" in block["extra_files"], (
            "a file under tests/ used to be dropped before anything was "
            "compared"
        )
        assert "migrations/0001_add_users_index.py" in block["extra_files"], (
            "a migration used to be dropped before anything was compared"
        )
        # The note is still read and reported - it just does not grade.
        assert block["player_note_files"]["present"] is True
        assert "src/analytics/service.py" in (
            block["player_note_files"]["files_to_create"]
        )
        assert "player_claim" not in block
        # And the Coach acts on it.
        validator = CoachValidator(worktree_path=str(worktree))
        result = validator.validate(
            task_id=DECLARING_TASK_ID,
            turn=1,
            task={"id": DECLARING_TASK_ID, "acceptance_criteria": ["trivial AC"]},
        )
        assert result.decision == "feedback"
        plan_audit_issues = [
            i for i in (result.issues or []) if i.get("category") == "plan_audit"
        ]
        assert plan_audit_issues
        assert plan_audit_issues[0]["severity"] == "must_fix"

    def test_a_checkpoint_commit_no_longer_hides_the_blast_radius(
        self, invoker: AgentInvoker, worktree: Path
    ):
        """Turn two must still see the sprawl turn one committed."""
        _write_task_document(
            worktree,
            DECLARING_TASK_ID,
            creates=["src/users/router.py"],
            modifies=[],
        )
        _commit_everything(worktree, "the task document")

        # Turn one writes the declared file and three nobody declared, and
        # the loop commits its checkpoint.
        turn_one_sprawl = [
            "src/analytics/one.py",
            "src/analytics/two.py",
            "src/analytics/three.py",
        ]
        _create_src_files(worktree, ["src/users/router.py"] + turn_one_sprawl)
        first_checkpoint = _commit_everything(worktree, "turn one checkpoint")
        _write_checkpoint(worktree, DECLARING_TASK_ID, first_checkpoint)

        results_path = invoker._write_task_work_results(
            DECLARING_TASK_ID, _minimal_result_data(), documentation_level="standard"
        )
        block = json.loads(results_path.read_text())["plan_audit"]

        assert sorted(block["extra_files"]) == sorted(turn_one_sprawl), (
            "turn one's files are committed, and they are still this task's "
            "work - asking what differs from the newest commit answered "
            "nothing from turn two onward"
        )
        assert block["status"] == "violation"

    def test_a_clean_build_says_so_plainly(
        self, invoker: AgentInvoker, worktree: Path
    ):
        _write_task_document(
            worktree,
            DECLARING_TASK_ID,
            creates=["src/users/router.py"],
            modifies=["src/users/crud.py"],
        )
        _create_src_files(worktree, ["src/users/crud.py"])
        _commit_everything(worktree, "the file this task will change")

        _create_src_files(worktree, ["src/users/router.py"])
        (worktree / "src" / "users" / "crud.py").write_text("# changed\npass\n")

        results_path = invoker._write_task_work_results(
            DECLARING_TASK_ID, _minimal_result_data(), documentation_level="standard"
        )
        block = json.loads(results_path.read_text())["plan_audit"]

        assert block["status"] == "passed"
        assert block["extra_files"] == []
        assert block["missing_files"] == []
        assert block["message"] == (
            "every file this build changed was named in the task document, "
            "and all 2 declared file(s) are on disk"
        )

    def test_a_declared_file_that_was_never_written_is_still_caught(
        self, invoker: AgentInvoker, worktree: Path
    ):
        _write_task_document(
            worktree,
            DECLARING_TASK_ID,
            creates=["src/users/router.py", "src/users/schemas.py"],
            modifies=[],
        )
        _create_src_files(worktree, ["src/users/router.py"])

        results_path = invoker._write_task_work_results(
            DECLARING_TASK_ID, _minimal_result_data(), documentation_level="standard"
        )
        block = json.loads(results_path.read_text())["plan_audit"]

        assert block["status"] == "violation"
        assert block["severity"] == "high"
        assert block["missing_files"] == ["src/users/schemas.py"]
        assert block["violations"] == 1

    def test_a_section_that_says_none_is_a_claim(
        self, invoker: AgentInvoker, worktree: Path
    ):
        """"Creates nothing" is something a task must be able to say."""
        _write_task_document(
            worktree,
            DECLARING_TASK_ID,
            creates=[],
            modifies=["src/users/crud.py"],
        )
        _create_src_files(worktree, ["src/users/crud.py"])
        _commit_everything(worktree, "the file this task will change")

        (worktree / "src" / "users" / "crud.py").write_text("# changed\npass\n")
        _create_src_files(worktree, ["src/users/brand_new.py"])

        results_path = invoker._write_task_work_results(
            DECLARING_TASK_ID, _minimal_result_data(), documentation_level="standard"
        )
        block = json.loads(results_path.read_text())["plan_audit"]

        assert block["extra_files"] == ["src/users/brand_new.py"]
        assert block["message"] == (
            "this build touched 1 file(s) the task document did not name: "
            "src/users/brand_new.py"
        )


class TestCoachRejectsOnPlanAuditViolation:
    """Coach gate: violation block → feedback decision naming the extras."""

    def _seed_results(self, worktree: Path, plan_audit_block: dict) -> Path:
        """Put a canned task_work_results.json at the autobuild path."""
        TaskArtifactPaths.ensure_autobuild_dir(TASK_ID, worktree)
        results_path = TaskArtifactPaths.task_work_results_path(TASK_ID, worktree)
        results_path.write_text(
            json.dumps({
                "task_id": TASK_ID,
                "completed": True,
                "quality_gates": {
                    "tests_passing": True,
                    "tests_passed": 10,
                    "tests_failed": 0,
                    "coverage": 85.0,
                    "coverage_met": True,
                    "all_passed": True,
                },
                "code_review": {"score": 85},
                "files_modified": [],
                "files_created": [],
                "tests_written": [],
                "summary": "",
                "plan_audit": plan_audit_block,
                # Don't trip the sibling gate; only plan_audit is under
                # test here.
                "agent_invocations_validation": {
                    "status": "passed",
                    "expected_phases": 3,
                    "actual_invocations": 3,
                    "missing_phases": [],
                    "violation_message": None,
                },
            })
        )
        return results_path

    def test_coach_rejects_high_severity_and_names_extras(
        self, worktree: Path
    ):
        # The scenario called out in the task AC: saved plan exists and
        # the actual implementation adds extra files → Coach must reject
        # with feedback citing the extras so the Player's next turn can
        # correct course.
        violation_block = {
            "status": "violation",
            "severity": "high",
            "violations": 1,
            "extra_files": [
                "src/scope_creep_1.py",
                "src/scope_creep_2.py",
                "src/scope_creep_3.py",
            ],
            "missing_files": [],
            "extra_dependencies": [],
            "missing_dependencies": [],
            "loc_variance_pct": None,
            "discrepancies_count": 1,
            "message": "severity=high, 1 discrepanc(ies), 3 extra file(s)",
        }
        self._seed_results(worktree, violation_block)

        validator = CoachValidator(worktree_path=str(worktree))
        result = validator.validate(
            task_id=TASK_ID,
            turn=1,
            task={"id": TASK_ID, "acceptance_criteria": ["trivial AC"]},
        )

        assert result.decision == "feedback"
        assert result.issues, "feedback decision must carry issues"

        plan_audit_issues = [
            i for i in result.issues if i.get("category") == "plan_audit"
        ]
        assert plan_audit_issues, "plan_audit must appear in feedback issues"

        # High severity → must_fix (escalated from legacy should_fix).
        assert plan_audit_issues[0]["severity"] == "must_fix"

        # Feedback description must name the extras so the Player has
        # actionable information for the next turn.
        description = plan_audit_issues[0]["description"]
        assert "scope_creep_1.py" in description
        assert "scope_creep_2.py" in description

        # Details must carry the structured extras for downstream
        # tooling (the producer-written deterministic fields).
        details = plan_audit_issues[0]["details"]
        assert details["severity"] == "high"
        assert len(details["extra_files"]) == 3

    def test_coach_does_not_reject_on_skipped_plan(self, worktree: Path):
        # No plan on disk → producer writes skipped → Coach must not
        # reject on plan_audit. (Other gates may still pass/fail — we
        # only care that the plan_audit category isn't the rejection
        # reason.)
        skipped_block = {
            "status": "skipped",
            "severity": None,
            "violations": 0,
            "extra_files": [],
            "missing_files": [],
            "extra_dependencies": [],
            "missing_dependencies": [],
            "loc_variance_pct": None,
            "discrepancies_count": 0,
            "message": "no implementation plan on disk",
        }
        self._seed_results(worktree, skipped_block)

        validator = CoachValidator(worktree_path=str(worktree))
        result = validator.validate(
            task_id=TASK_ID,
            turn=1,
            task={"id": TASK_ID, "acceptance_criteria": ["trivial AC"]},
        )

        if result.decision == "feedback":
            categories = {i.get("category") for i in (result.issues or [])}
            assert "plan_audit" not in categories, (
                "skipped plan_audit must be treated as pass, not rejection"
            )

    def test_coach_does_not_reject_on_auditor_error(self, worktree: Path):
        # auditor_error is NOT a blocker — the auditor's own failure
        # shouldn't stop Coach from evaluating the rest of the task.
        error_block = {
            "status": "auditor_error",
            "severity": None,
            "violations": 0,
            "extra_files": [],
            "missing_files": [],
            "extra_dependencies": [],
            "missing_dependencies": [],
            "loc_variance_pct": None,
            "discrepancies_count": 0,
            "message": "RuntimeError: simulated crash",
        }
        self._seed_results(worktree, error_block)

        validator = CoachValidator(worktree_path=str(worktree))
        result = validator.validate(
            task_id=TASK_ID,
            turn=1,
            task={"id": TASK_ID, "acceptance_criteria": ["trivial AC"]},
        )

        if result.decision == "feedback":
            categories = {i.get("category") for i in (result.issues or [])}
            assert "plan_audit" not in categories

    def test_coach_does_not_reject_on_passed_block(self, worktree: Path):
        passed_block = {
            "status": "passed",
            "severity": "low",
            "violations": 0,
            "extra_files": [],
            "missing_files": [],
            "extra_dependencies": [],
            "missing_dependencies": [],
            "loc_variance_pct": None,
            "discrepancies_count": 0,
            "message": "severity=low, 0 discrepanc(ies)",
        }
        self._seed_results(worktree, passed_block)

        validator = CoachValidator(worktree_path=str(worktree))
        result = validator.validate(
            task_id=TASK_ID,
            turn=1,
            task={"id": TASK_ID, "acceptance_criteria": ["trivial AC"]},
        )

        if result.decision == "feedback":
            categories = {i.get("category") for i in (result.issues or [])}
            assert "plan_audit" not in categories
