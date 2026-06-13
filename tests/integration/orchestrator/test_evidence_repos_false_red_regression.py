"""AC-005 regression: sibling-repo-only task must not false-red (TASK-AB-XREPOEV01).

Reproduces the FEAT-C332 run-1 defect: TASK-QAWE-001's deliverable landed in
``guardkitfactory`` (a declared sibling repo), but the orchestrator's evidence
loop was scoped to the guardkit worktree only, so the Player report showed
"0 files modified" and the Coach honestly rejected every turn as "No
implementation provided" while 2,100+ lines of on-spec work sat in the
factory repo.

With ``evidence_repos`` declared, the post-turn diff must merge the sibling
repo's writes into the Player report as repo-qualified paths, and the Coach
honesty verifier must resolve those claims against the right repo root
(no new ghost-path false-red, per path-string-mismatch-is-not-dishonesty).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_verification import CoachVerifier
from guardkit.orchestrator.evidence_repos import EvidenceRepo
from guardkit.orchestrator.exceptions import TaskWorkResult
from guardkit.orchestrator.paths import TaskArtifactPaths


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "t@t"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "t"],
        check=True,
        capture_output=True,
    )
    (path / "README.md").write_text("seed\n")
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-q", "-m", "init"],
        check=True,
        capture_output=True,
    )


@pytest.fixture
def worktree_and_factory(tmp_path):
    worktree = tmp_path / "worktree"
    factory = tmp_path / "guardkitfactory"
    _init_repo(worktree)
    _init_repo(factory)
    return worktree, factory


class TestSiblingRepoOnlyFalseRedRegression:
    def test_sibling_only_writes_reach_player_report(self, worktree_and_factory):
        worktree, factory = worktree_and_factory
        repo = EvidenceRepo(name="guardkitfactory", root=factory)
        invoker = AgentInvoker(
            worktree_path=worktree,
            evidence_repos=[repo],
            use_task_work_delegation=True,
        )

        # Baseline both repos BEFORE the Player writes anything.
        invoker._record_baseline()

        # Player writes its deliverable ONLY in the sibling repo (the
        # FEAT-C332 scenario). The guardkit worktree is untouched.
        (factory / "src").mkdir()
        (factory / "src" / "deliverable.py").write_text(
            "def reqnroll_discover():\n    return 'routing'\n"
        )

        task_id = "TASK-QAWE-001"
        result = TaskWorkResult(success=True, output={})
        invoker._create_player_report_from_task_work(task_id, 1, result)

        report_path = TaskArtifactPaths.player_report_path(task_id, 1, worktree)
        report = json.loads(report_path.read_text())

        all_claimed = report.get("files_created", []) + report.get(
            "files_modified", []
        )
        # The crux: the report is NOT empty -> Coach will not see "0 files".
        assert all_claimed, "sibling-repo-only task produced an empty report (false-red)"
        assert "guardkitfactory:src/deliverable.py" in report["files_created"]

    def test_coach_verifier_resolves_sibling_claim_no_false_red(
        self, worktree_and_factory
    ):
        worktree, factory = worktree_and_factory
        repo = EvidenceRepo(name="guardkitfactory", root=factory)

        # The deliverable exists in the sibling repo.
        (factory / "src").mkdir()
        (factory / "src" / "deliverable.py").write_text("x = 1\n")

        report = {
            "files_created": ["guardkitfactory:src/deliverable.py"],
            "files_modified": [],
            "tests_written": [],
        }

        verifier = CoachVerifier(worktree, evidence_repos=[repo])
        verification = verifier.verify_player_report(report)

        file_discs = [
            d for d in verification.discrepancies if d.claim_type == "file_existence"
        ]
        assert file_discs == [], "sibling-repo claim wrongly flagged as missing"

    def test_coach_verifier_flags_genuinely_missing_sibling_file(
        self, worktree_and_factory
    ):
        # Honesty still works: a claimed sibling file that does NOT exist is a
        # real critical discrepancy (the resolution is not a blanket pass).
        worktree, factory = worktree_and_factory
        repo = EvidenceRepo(name="guardkitfactory", root=factory)

        report = {
            "files_created": ["guardkitfactory:src/never_written.py"],
            "files_modified": [],
            "tests_written": [],
        }

        verifier = CoachVerifier(worktree, evidence_repos=[repo])
        verification = verifier.verify_player_report(report)

        file_discs = [
            d for d in verification.discrepancies if d.claim_type == "file_existence"
        ]
        assert len(file_discs) == 1
        assert file_discs[0].severity == "critical"

    def test_undeclared_sibling_claim_is_fail_open_not_false_red(
        self, worktree_and_factory
    ):
        # AC-003 + path-string-mismatch: a qualified claim naming an UNDECLARED
        # repo must not manufacture a false-red (fail-open skip).
        worktree, _ = worktree_and_factory
        report = {
            "files_created": ["someotherrepo:src/x.py"],
            "files_modified": [],
            "tests_written": [],
        }
        verifier = CoachVerifier(worktree, evidence_repos=[])  # none declared
        verification = verifier.verify_player_report(report)
        file_discs = [
            d for d in verification.discrepancies if d.claim_type == "file_existence"
        ]
        assert file_discs == []

    def test_undeclared_repo_writes_stay_invisible(self, worktree_and_factory):
        # AC-003: with NO evidence_repos declared, sibling-repo writes are not
        # swept into the report (no implicit scanning of parent dirs).
        worktree, factory = worktree_and_factory
        invoker = AgentInvoker(
            worktree_path=worktree,
            evidence_repos=[],  # nothing declared
            use_task_work_delegation=True,
        )
        invoker._record_baseline()
        (factory / "leak.py").write_text("secret = 1\n")

        task_id = "TASK-NODECL"
        invoker._create_player_report_from_task_work(
            task_id, 1, TaskWorkResult(success=True, output={})
        )
        report_path = TaskArtifactPaths.player_report_path(task_id, 1, worktree)
        report = json.loads(report_path.read_text())
        all_claimed = report.get("files_created", []) + report.get("files_modified", [])
        assert not any("leak.py" in p for p in all_claimed)
        assert not any("guardkitfactory" in p for p in all_claimed)
