"""A file this task deleted, in an earlier turn already committed, is not a fabrication.

Build FEAT-D31F (19 October 2026): the task's first turn deleted a page file,
and the loop's checkpoint committed the deletion. On every later turn the
orchestrator's own git enrichment (``git diff --name-only <task base>``) listed
the deleted path under ``files_modified``. The claim audit found it neither in
``git status --porcelain`` (the deletion was committed) nor on disk, called it
fabricated, and the critical record stopped all other evidence gathering
(``partial_honesty_abort``) on turns 2 to 5. The builder never wrote that
claim and could not take it back.

A modified-file claim for a path that existed where the task started and is
gone now is a deletion this task made - a true report. The honesty rule stays
strict: a path that never existed is still fabricated and still critical, and
so is a cited file or a "created" file that is missing.

Real git repositories under ``tmp_path``; invented names; no network, no model.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.coach_verification import CoachVerifier
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.state_detection import detect_git_changes


TASK_ID = "TASK-SHELF-002"


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


def _write(root: Path, rel: str, text: str = "invented\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Task base: a page, its form and an app. Turn 1 deletes the form."""
    root = tmp_path / "worktree"
    root.mkdir()
    _git("init", "--initial-branch=main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    _git("config", "commit.gpgsign", "false", cwd=root)
    _write(root, ".gitignore", ".guardkit/\n")
    _write(root, "apps/shelf/src/Main.tsx", "export const Main = () => null;\n")
    _write(root, "apps/shelf/src/pages/ShelfForm.tsx", "export const F = () => null;\n")
    _write(root, "apps/shelf/src/pages/ShelfPage.tsx", "export const P = () => null;\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-m", "task base", cwd=root)

    # Turn 1: delete the form, change the app; the loop checkpoints it.
    (root / "apps/shelf/src/pages/ShelfForm.tsx").unlink()
    _write(root, "apps/shelf/src/Main.tsx", "export const Main = () => 1;\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-m", "[guardkit-checkpoint] Turn 1 complete", cwd=root)
    turn_1 = _git("rev-parse", "HEAD", cwd=root).stdout.strip()

    checkpoints = root / ".guardkit" / "autobuild" / TASK_ID / "checkpoints.json"
    checkpoints.parent.mkdir(parents=True)
    checkpoints.write_text(
        json.dumps(
            {"task_id": TASK_ID, "checkpoints": [{"turn": 1, "commit_hash": turn_1}]}
        )
    )
    # Turn 2 edits the page and has not been checkpointed yet.
    _write(root, "apps/shelf/src/pages/ShelfPage.tsx", "export const P = () => 2;\n")
    return root


# The shape of task_work_results on turn 2: the git enrichment lists every path
# that differs from the task base, the deleted form included.
TURN_2_RESULTS = {
    "task_id": TASK_ID,
    "files_modified": [
        "apps/shelf/src/Main.tsx",
        "apps/shelf/src/pages/ShelfForm.tsx",
        "apps/shelf/src/pages/ShelfPage.tsx",
    ],
    "files_created": [],
}


class TestTheLiveShape:
    def test_claim_audit_has_no_record_for_the_committed_deletion(
        self, repo: Path
    ) -> None:
        verifier = CoachVerifier(repo, task_id=TASK_ID)

        assert verifier._verify_claims_were_staged(TURN_2_RESULTS) == []

    def test_existence_check_has_no_record_for_the_committed_deletion(
        self, repo: Path
    ) -> None:
        verifier = CoachVerifier(repo, task_id=TASK_ID)

        assert verifier._verify_files_exist(TURN_2_RESULTS) == []

    def test_the_coach_honesty_check_raises_no_must_fix(self, repo: Path) -> None:
        """The caller that set partial_honesty_abort on turns 2 to 5."""
        validator = CoachValidator(str(repo), task_id=TASK_ID)

        honesty = validator._verify_honesty(TURN_2_RESULTS)
        must_fix = [
            issue
            for issue in validator._honesty_issues_from(honesty)
            if issue["severity"] == "must_fix"
        ]

        assert honesty.verified, honesty.discrepancies
        assert must_fix == []


class TestTheHonestyRuleStaysStrict:
    def test_a_file_that_never_existed_is_still_fabricated(self, repo: Path) -> None:
        verifier = CoachVerifier(repo, task_id=TASK_ID)
        results = {
            **TURN_2_RESULTS,
            "files_modified": TURN_2_RESULTS["files_modified"]
            + ["apps/shelf/src/pages/Ghost.tsx"],
        }

        records = verifier._verify_claims_were_staged(results)

        assert [(r.claim_type, r.severity) for r in records] == [
            ("claim_audit", "critical")
        ]
        assert "Ghost.tsx" in records[0].player_claim
        assert "To clear this record" in records[0].actual_value

        validator = CoachValidator(str(repo), task_id=TASK_ID)
        honesty = validator._verify_honesty(results)
        assert not honesty.verified
        assert any(
            issue["severity"] == "must_fix"
            for issue in validator._honesty_issues_from(honesty)
        )

    def test_a_deleted_file_reported_as_created_is_still_fabricated(
        self, repo: Path
    ) -> None:
        verifier = CoachVerifier(repo, task_id=TASK_ID)

        records = verifier._verify_claims_were_staged(
            {"files_created": ["apps/shelf/src/pages/ShelfForm.tsx"]}
        )

        assert [(r.claim_type, r.severity) for r in records] == [
            ("claim_audit", "critical")
        ]

    def test_a_deleted_file_cited_as_evidence_is_still_fabricated(
        self, repo: Path
    ) -> None:
        verifier = CoachVerifier(repo, task_id=TASK_ID)

        records = verifier._verify_claims_were_staged(
            {
                "completion_promises": [
                    {
                        "criterion_id": "AC-001",
                        "implementation_files": [
                            "apps/shelf/src/pages/ShelfForm.tsx"
                        ],
                    }
                ]
            }
        )

        assert [(r.claim_type, r.severity) for r in records] == [
            ("claim_audit", "critical")
        ]

    def test_without_a_task_base_on_record_the_deletion_is_still_flagged(
        self, repo: Path
    ) -> None:
        """Fail closed: no checkpoints file, no exemption."""
        verifier = CoachVerifier(repo, task_id="TASK-NO-CHECKPOINTS")

        records = verifier._verify_claims_were_staged(TURN_2_RESULTS)
        critical = [r for r in records if r.severity == "critical"]

        assert [r.player_claim for r in critical] == [
            "Player claimed file apps/shelf/src/pages/ShelfForm.tsx"
        ]


DELETED = "apps/shelf/src/pages/ShelfForm.tsx"

# Each second claim of the deleted file, made beside the files_modified entry
# the git step always adds. None of them is made true by the deletion.
SECOND_CLAIMS = {
    "reported as created": {"files_created": [DELETED]},
    "reported as a test written": {"tests_written": [DELETED]},
    "cited as a completed check's test file": {
        "completion_promises": [
            {"criterion_id": "AC-002", "status": "complete", "test_file": DELETED}
        ]
    },
    "cited as a completed check's implementation file": {
        "completion_promises": [
            {
                "criterion_id": "AC-002",
                "status": "complete",
                "implementation_files": [DELETED],
            }
        ]
    },
}


class TestASecondClaimOfTheDeletedFileIsRefused:
    """Coach 1, finding 1: the deletion skip must not cover a second claim.

    The git step lists the deleted path under files_modified on every turn
    after the deletion was committed, so each case below includes that entry,
    exactly as a real report would.
    """

    @pytest.mark.parametrize("label", sorted(SECOND_CLAIMS))
    def test_the_coach_honesty_check_raises_must_fix(
        self, repo: Path, label: str
    ) -> None:
        results = {**TURN_2_RESULTS, **SECOND_CLAIMS[label]}
        assert DELETED in results["files_modified"]
        validator = CoachValidator(str(repo), task_id=TASK_ID)

        honesty = validator._verify_honesty(results)
        must_fix = [
            issue
            for issue in validator._honesty_issues_from(honesty)
            if issue["severity"] == "must_fix"
        ]

        assert not honesty.verified, label
        assert must_fix, (label, honesty.discrepancies)

    @pytest.mark.parametrize(
        "label",
        [
            "reported as created",
            "reported as a test written",
            "cited as a completed check's test file",
        ],
    )
    def test_the_claim_check_itself_records_it(self, repo: Path, label: str) -> None:
        verifier = CoachVerifier(repo, task_id=TASK_ID)

        records = verifier._verify_claims_were_staged(
            {**TURN_2_RESULTS, **SECOND_CLAIMS[label]}
        )

        assert [(r.claim_type, r.severity, r.player_claim) for r in records] == [
            ("claim_audit", "critical", f"Player claimed file {DELETED}")
        ]


class TestTheExistenceCheckSkipsOnlyModifiedDeletions:
    """Coach 1, mutation M5: only files_modified earns the deletion skip."""

    @pytest.mark.parametrize("key", ["files_created", "tests_written"])
    def test_a_deleted_file_in_another_list_is_still_missing(
        self, repo: Path, key: str
    ) -> None:
        verifier = CoachVerifier(repo, task_id=TASK_ID)

        records = verifier._verify_files_exist({key: [DELETED]})

        assert [(r.claim_type, r.severity, r.player_claim) for r in records] == [
            ("file_existence", "critical", f"{key}: {DELETED}")
        ]

    def test_beside_the_modified_entry_only_the_other_list_is_recorded(
        self, repo: Path
    ) -> None:
        verifier = CoachVerifier(repo, task_id=TASK_ID)

        records = verifier._verify_files_exist(
            {"files_modified": [DELETED], "files_created": [DELETED]}
        )

        assert [r.player_claim for r in records] == [f"files_created: {DELETED}"]


class TestRecoveredStateNamesFilesNotFolders:
    def test_a_new_folder_is_listed_file_by_file(self, tmp_path: Path) -> None:
        """Turn 2 of the same build was refused over folder "claims".

        The recovery path listed ``.claude/task-plans/`` and ``.local/`` as
        created files because git folds a new folder into one line.
        """
        root = tmp_path / "repo"
        root.mkdir()
        _git("init", "--initial-branch=main", cwd=root)
        _git("config", "user.email", "test@example.com", cwd=root)
        _git("config", "user.name", "Test", cwd=root)
        _write(root, "README.md", "base\n")
        _git("add", "-A", cwd=root)
        _git("commit", "-m", "base", cwd=root)
        _write(root, "drafts/plans/plan-1.md", "plan\n")
        _write(root, "drafts/plans/plan-2.md", "plan\n")

        changes = detect_git_changes(root)

        assert changes is not None
        assert sorted(changes.files_added) == [
            "drafts/plans/plan-1.md",
            "drafts/plans/plan-2.md",
        ]
