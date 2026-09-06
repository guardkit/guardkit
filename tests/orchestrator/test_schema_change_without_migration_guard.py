"""2026-09-06 — a model change without a migration fails the coach.

The case, in plain words. On 6 September 2026 the build ``build-FEAT-8388``
ran on api_test, a repository whose database schema lives in Alembic
migrations. On ``TASK-8388-001`` turn 1 the Player added a ``domain`` column
to ``src/users/models.py`` and no migration. The coach sent that turn back
for an unrelated reason (the independent test run could not collect any
tests), the turn was checkpointed anyway, and every verdict after it
approved a tree with no changes in it — ``TASK-8388-001`` turn 2 and
``TASK-8388-002`` turn 1. The unit tests passed (they build the schema from
the model), and the behavioural oracle passed (it was testing a Docker image
from July). The deploy into the Docker Sandbox, which builds the schema by
running the migrations on a fresh database, found the users table had no
``domain`` column — 44 checks passed, 6 failed, the candidate was refused.

``AgentInvoker._apply_schema_change_without_migration_guard`` now catches
this at the coach, on the turn that makes the change. It reads the
worktree's difference from ``HEAD`` (a changed model is a diff; a new
migration is an untracked file) and flips an ``approve`` to ``feedback``
when a Python file outside ``tests/`` and outside the migrations tree gains
a column or table line and nothing was added or changed under the
migrations' ``versions/``. Because the build checkpoints every completed
turn, a change committed by an earlier turn's checkpoint is not in that
difference; the guard's docstring records this as a known limit awaiting
the spec author's decision.

The two files in ``tests/fixtures/schema-change-2026-09-06/`` are
byte-for-byte copies of ``TASK-8388-002``'s real turn-1 records (see the
PROVENANCE.txt beside them): a real approval from the build that got
through, and its evidence bundle. The worktree shape — an uncommitted model
change, no migration — is built by the tests, because on the real build the
change was already committed by the time that approval was given.

Every test builds a real temporary git repository with an Alembic tree and a
model file, so the guard's three git commands run for real. The real
``invoke_coach`` synthesis path is driven once each way (a mocked harness
emits the verdict; the parser, loader, validator and every deterministic
guard run for real), matching ``test_coach_contradicted_absent_test_claim_guard.py``.
Async tests use ``asyncio.run`` to stay free of a pytest-asyncio dependency.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.harness import (
    AssistantMessageEvent,
    ResultMessageEvent,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    IndependentTestResult,
)


FIXTURE_DIR = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "schema-change-2026-09-06"
)

CATEGORY = "schema_change_without_migration"

# Rule 12 of the 2026-09-06 spec, verbatim, for the fixture's file and tree.
RULE_12_SENTENCE = (
    "`src/users/models.py` adds or changes a database column, but no Alembic "
    "migration was added under `alembic/versions/`. A freshly created "
    "database would not have this column, so the deployed app would fail on "
    "it. Add the migration in this task."
)


# ---------------------------------------------------------------------------
# fixture loading — the real build-FEAT-8388 / TASK-8388-002 turn-1 records
# ---------------------------------------------------------------------------


def _load_receipt(name: str) -> Dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text())


def _real_evidence() -> Dict[str, Any]:
    return _load_receipt("coach_evidence_turn_1.json")


def _real_verdict() -> Dict[str, Any]:
    return _load_receipt("coach_turn_1.json")


def _bundle_from_receipt() -> CoachEvidenceBundle:
    """Rebuild the evidence bundle from the saved record.

    Only the legs the override chain reads are rehydrated
    (``independent_tests`` as the real dataclass, ``behavioural_oracle`` /
    ``tests`` / ``task_type`` / ``profile_name`` as saved). ``honesty`` is
    rebuilt from the saved values: not verified, four should_fix notes about
    files the Player listed but had not touched — not a rejection trigger on
    its own, and the real build approved over it.
    """
    evidence = _real_evidence()
    ind = evidence["independent_tests"]
    honesty = evidence["honesty"]
    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=honesty["verified"],
            discrepancies=[],
            honesty_score=honesty["honesty_score"],
            resolved_paths=[],
            should_fix_count=honesty.get("should_fix_count", 0),
        ),
        gathering_status=evidence["gathering_status"],
        tests=evidence["tests"],
        behavioural_oracle=evidence["behavioural_oracle"],
        independent_tests=IndependentTestResult(
            tests_passed=ind["tests_passed"],
            test_command=ind["test_command"],
            test_output_summary=ind["test_output_summary"],
            duration_seconds=ind["duration_seconds"],
            raw_output=ind["raw_output"],
            signal_absent=ind["signal_absent"],
            tests_skipped=ind["tests_skipped"],
            resolved_interpreter=ind["resolved_interpreter"],
        ),
        task_type=evidence["task_type"],
        profile_name=evidence["profile_name"],
    )


# ---------------------------------------------------------------------------
# a temporary git repository shaped like api_test
# ---------------------------------------------------------------------------

MODEL_FILE = "src/users/models.py"

MODEL_SOURCE = '''"""User model."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
'''

DOMAIN_COLUMN_LINE = (
    "    domain: Mapped[str | None] = mapped_column(String(255), index=True)\n"
)

MIGRATION_SOURCE = '''"""add the domain column"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.add_column("users", sa.Column("domain", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "domain")
'''


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        [
            "git",
            "-c", "user.name=guardkit-test",
            "-c", "user.email=guardkit-test@example.invalid",
            "-c", "commit.gpgsign=false",
            *args,
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _write(repo: Path, rel: str, text: str) -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _make_repo(
    tmp_path: Path,
    *,
    alembic_tree: str = "alembic/env.py",
    with_first_migration: bool = True,
) -> Path:
    """A committed repository: a SQLAlchemy model, a test file, and an
    Alembic tree of the requested shape (``alembic/env.py``,
    ``migrations/env.py``, ``alembic.ini`` alone, or ``""`` for none)."""
    repo = tmp_path / "worktree"
    repo.mkdir()
    _git(repo, "init", "-q")
    _write(repo, MODEL_FILE, MODEL_SOURCE)
    _write(repo, "src/db.py", "from sqlalchemy.orm import DeclarativeBase\n\nclass Base(DeclarativeBase):\n    pass\n")
    _write(repo, "tests/users/test_models.py", "def test_nothing():\n    assert True\n")
    _write(repo, "README.md", "# api_test twin\n")
    if alembic_tree == "alembic/env.py":
        _write(repo, "alembic/env.py", "# alembic env\n")
        if with_first_migration:
            _write(repo, "alembic/versions/0001_initial.py", '"""initial"""\nrevision = "0001"\n')
    elif alembic_tree == "migrations/env.py":
        _write(repo, "migrations/env.py", "# alembic env\n")
        if with_first_migration:
            _write(repo, "migrations/versions/0001_initial.py", '"""initial"""\nrevision = "0001"\n')
    elif alembic_tree.startswith("alembic.ini"):
        # "alembic.ini" or "alembic.ini:<script_location>"
        location = alembic_tree.partition(":")[2] or "alembic"
        _write(repo, "alembic.ini", f"[alembic]\nscript_location = {location}\n")
        if with_first_migration:
            plain = location.replace("%(here)s/", "")
            _write(repo, f"{plain}/versions/0001_initial.py", '"""initial"""\nrevision = "0001"\n')
    elif alembic_tree:
        raise ValueError(alembic_tree)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def _add_domain_column(repo: Path, rel: str = MODEL_FILE) -> None:
    path = repo / rel
    path.write_text(path.read_text() + DOMAIN_COLUMN_LINE)


# ---------------------------------------------------------------------------
# harness helpers
# ---------------------------------------------------------------------------


def _make_invoker(worktree: Path) -> AgentInvoker:
    """A minimal AgentInvoker able to run the full ``invoke_coach`` synthesis
    path (mirrors ``_make_invoker`` in
    test_coach_contradicted_absent_test_claim_guard.py)."""
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._venv_python = None
    return invoker


def _approve() -> Dict[str, Any]:
    return {
        "task_id": "TASK-TEST-001",
        "turn": 1,
        "decision": "approve",
        "rationale": "All acceptance criteria met.",
        "issues": [],
    }


def _feedback(text: str = "AC-001 not delivered") -> Dict[str, Any]:
    return {
        "task_id": "TASK-TEST-001",
        "turn": 1,
        "decision": "feedback",
        "rationale": text,
        "issues": [{"severity": "must_fix", "category": "acceptance", "description": text}],
    }


def _run_guard(
    repo: Path,
    decision: Dict[str, Any],
    *,
    task_id: str = "TASK-TEST-001",
    turn: int = 1,
    bundle: Optional[CoachEvidenceBundle] = None,
) -> Path:
    """Call the guard directly on a decision already on disk, the way the
    override chain does; returns the on-disk path so tests can check the
    re-persist."""
    invoker = _make_invoker(repo)
    output_path = invoker._get_report_path(task_id, turn, "coach")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(decision, indent=2))
    invoker._apply_schema_change_without_migration_guard(
        decision=decision,
        evidence_bundle=bundle,
        task_id=task_id,
        turn=turn,
        coach_output_path=output_path,
    )
    return output_path


def _v4_approve_events() -> list:
    """Harness events carrying the Coach v4 wire shape the real build used
    for its approval: ``{"verdict": "approve", "findings": []}``."""
    wire = {"verdict": "approve", "findings": []}
    return [
        AssistantMessageEvent(text=json.dumps(wire)),
        ResultMessageEvent(session_id=None),
    ]


def _run_real_coach_path(invoker: AgentInvoker, *, task_id: str, turn: int):
    """Invoke the Coach with ``_invoke_with_role`` mocked to return an
    approval. Everything else — the parser, the loader, the validator and the
    whole deterministic override chain — runs for real."""
    iwr = AsyncMock(return_value=(None, _v4_approve_events()))
    with patch.object(invoker, "_invoke_with_role", iwr):
        return asyncio.run(
            invoker.invoke_coach(
                task_id=task_id,
                turn=turn,
                requirements="Add a domain column to the users model.",
                player_report={"files_modified": [MODEL_FILE], "tests_passed": True},
                evidence_bundle=_bundle_from_receipt(),
            )
        )


@pytest.fixture(autouse=True)
def _coach_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Synthesis path on (default), gather off, v4 contract — the shape the
    real build ran under."""
    monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
    monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
    monkeypatch.setenv("GUARDKIT_COACH_CONTRACT", "v4")


# ---------------------------------------------------------------------------
# (a) fires on the fixture shape: Alembic tree, model line added, no versions file
# ---------------------------------------------------------------------------


class TestFiresOnTheFixtureShape:
    def test_added_mapped_column_with_no_migration_flips_approve_to_feedback(
        self, tmp_path: Path
    ) -> None:
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "feedback"
        issue = decision["issues"][0]
        assert issue["severity"] == "must_fix"
        assert issue["category"] == CATEGORY
        assert issue["description"] == RULE_12_SENTENCE
        assert decision["rationale"] == RULE_12_SENTENCE

    def test_details_carry_the_file_the_lines_and_the_directory_looked_in(
        self, tmp_path: Path
    ) -> None:
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        decision = _approve()

        _run_guard(repo, decision)

        details = decision["issues"][0]["details"]
        assert details["file"] == MODEL_FILE
        assert details["files"] == [MODEL_FILE]
        assert details["matching_lines"][MODEL_FILE] == [DOMAIN_COLUMN_LINE.rstrip("\n")]
        assert details["migrations_dir"] == "alembic"
        assert details["versions_dir"] == "alembic/versions"
        assert details["overridden_decision"] == "approve"

    def test_override_rewrites_coach_turn_file_on_disk(self, tmp_path: Path) -> None:
        """The on-disk ``coach_turn_N.json`` must carry the flipped verdict —
        the late-approval reader reads ``decision`` straight off disk."""
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        decision = _approve()

        output_path = _run_guard(repo, decision, turn=2)

        on_disk = json.loads(output_path.read_text())
        assert on_disk["decision"] == "feedback"
        assert on_disk["issues"][0]["category"] == CATEGORY
        assert on_disk["issues"][0]["description"] == RULE_12_SENTENCE

    def test_a_classic_column_call_fires(self, tmp_path: Path) -> None:
        """``Column(`` — the declarative-classic spelling — is a schema line too."""
        repo = _make_repo(tmp_path)
        path = repo / MODEL_FILE
        path.write_text(
            path.read_text().replace("from sqlalchemy import String", "from sqlalchemy import Column, String")
            + "    nickname = Column(String(64), nullable=True)\n"
        )
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "feedback"
        assert decision["issues"][0]["category"] == CATEGORY
        assert "Column(String(64)" in decision["issues"][0]["details"]["matching_lines"][MODEL_FILE][0]

    def test_a_new_untracked_model_file_with_a_table_fires(self, tmp_path: Path) -> None:
        """A brand-new model file is untracked until the checkpoint; it is
        read whole as added lines, and ``__tablename__`` is a table."""
        repo = _make_repo(tmp_path)
        _write(
            repo,
            "src/orders/models.py",
            'from src.db import Base\n\n\nclass Order(Base):\n    __tablename__ = "orders"\n',
        )
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "feedback"
        issue = decision["issues"][0]
        assert issue["details"]["file"] == "src/orders/models.py"
        assert issue["details"]["matching_lines"]["src/orders/models.py"] == ['    __tablename__ = "orders"']

    def test_the_issue_text_names_the_real_file(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        _write(repo, "src/billing/tables.py", MODEL_SOURCE.replace('"users"', '"invoices"'))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "invoices")
        _add_domain_column(repo, "src/billing/tables.py")
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["issues"][0]["description"].startswith(
            "`src/billing/tables.py` adds or changes a database column, but no "
            "Alembic migration was added under `alembic/versions/`."
        )

    def test_the_sentence_names_the_first_file_and_details_name_them_all(
        self, tmp_path: Path
    ) -> None:
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        _write(repo, "src/orders/models.py", 'class Order:\n    __tablename__ = "orders"\n')
        decision = _approve()

        _run_guard(repo, decision)

        issue = decision["issues"][0]
        assert issue["details"]["files"] == ["src/orders/models.py", MODEL_FILE]
        assert issue["description"].startswith("`src/orders/models.py` adds or changes")

    def test_fixture_approval_is_flipped_with_the_rule_12_sentence(
        self, tmp_path: Path
    ) -> None:
        """The real turn-1 verdict from build-FEAT-8388 / TASK-8388-002 (an
        approval carrying four should_fix honesty notes), over a worktree
        shaped like the defect that build shipped: ``src/users/models.py``
        gained ``domain``, uncommitted, nothing under ``alembic/versions/``.
        (On the real build that change had been committed by an earlier
        turn's checkpoint; see the fixture's PROVENANCE.txt.) The guard
        flips it to feedback with the spec's sentence in front, and the
        coach's own notes survive behind it."""
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        decision = _real_verdict()
        assert decision["decision"] == "approve"
        original_issues = list(decision["issues"])
        assert len(original_issues) == 4

        _run_guard(repo, decision, task_id="TASK-8388-002", bundle=_bundle_from_receipt())

        assert decision["decision"] == "feedback"
        assert decision["issues"][0]["severity"] == "must_fix"
        assert decision["issues"][0]["category"] == CATEGORY
        assert decision["issues"][0]["description"] == RULE_12_SENTENCE
        assert decision["issues"][1:] == original_issues

    def test_the_real_coach_path_flips_the_approval(self, tmp_path: Path) -> None:
        """Through ``invoke_coach`` itself with the fixture's evidence bundle:
        the harness emits the approval the real seat gave, and the override
        chain ends in feedback. Pins that the guard is wired into the chain,
        not just defined."""
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        invoker = _make_invoker(repo)

        result = _run_real_coach_path(invoker, task_id="TASK-8388-002", turn=1)

        assert result.success is True
        assert result.report["decision"] == "feedback"
        assert result.report["issues"][0]["category"] == CATEGORY
        assert result.report["issues"][0]["description"] == RULE_12_SENTENCE
        on_disk = json.loads(
            invoker._get_report_path("TASK-8388-002", 1, "coach").read_text()
        )
        assert on_disk["decision"] == "feedback"

    def test_a_warning_is_logged(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker"):
            _run_guard(repo, _approve(), task_id="TASK-TEST-009", turn=3)
        messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert any(
            "schema change without migration" in m
            and "TASK-TEST-009 turn 3" in m
            and MODEL_FILE in m
            for m in messages
        )


# ---------------------------------------------------------------------------
# (b) no-ops: a migration was added or changed
# ---------------------------------------------------------------------------


class TestMigrationPresentIsANoOp:
    def test_an_untracked_migration_file_satisfies_the_guard(self, tmp_path: Path) -> None:
        """The real shape of a correct turn: the model changed AND a new
        migration sits untracked under versions/."""
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        _write(repo, "alembic/versions/0002_add_domain.py", MIGRATION_SOURCE)
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"
        assert decision["issues"] == []

    def test_a_changed_tracked_migration_file_satisfies_the_guard(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        path = repo / "alembic/versions/0001_initial.py"
        path.write_text(path.read_text() + "\n# also adds the domain column\n")
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"

    def test_a_first_migration_in_a_brand_new_versions_directory_counts(
        self, tmp_path: Path
    ) -> None:
        """``versions/`` did not exist at HEAD. Plain ``git status --porcelain``
        would fold the new file into ``?? alembic/versions/``; the guard asks
        for every untracked file so the migration is seen."""
        repo = _make_repo(tmp_path, with_first_migration=False)
        assert not (repo / "alembic/versions").exists()
        _add_domain_column(repo)
        _write(repo, "alembic/versions/0001_add_domain.py", MIGRATION_SOURCE)
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"

    def test_the_real_coach_path_approves_when_the_migration_is_there(
        self, tmp_path: Path
    ) -> None:
        """The control for the real-path flip above: same bundle, same
        harness, a migration added — the chain ends in approve, so the flip
        is this guard's doing and nothing else's."""
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        _write(repo, "alembic/versions/0002_add_domain.py", MIGRATION_SOURCE)
        invoker = _make_invoker(repo)

        result = _run_real_coach_path(invoker, task_id="TASK-8388-002", turn=1)

        assert result.success is True
        assert result.report["decision"] == "approve"
        assert CATEGORY not in [i.get("category") for i in result.report["issues"]]


# ---------------------------------------------------------------------------
# (c) no-ops: not this guard's case
# ---------------------------------------------------------------------------


class TestOutOfScopeIsANoOp:
    def test_no_alembic_tree_is_a_no_op(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, alembic_tree="")
        _add_domain_column(repo)
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"
        assert decision["issues"] == []

    def test_a_schema_line_under_tests_is_a_no_op(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        _write(
            repo,
            "tests/users/test_models.py",
            'from sqlalchemy import Column\n\nclass Fake:\n    __tablename__ = "fake"\n    x = Column()\n',
        )
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"

    def test_a_schema_line_under_a_nested_tests_directory_is_a_no_op(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        _write(repo, "src/users/tests/factories.py", 'class F:\n    __tablename__ = "f"\n')
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"

    def test_a_schema_line_inside_the_migrations_tree_is_a_no_op(self, tmp_path: Path) -> None:
        """``alembic/env.py`` (or anything under the tree that is not a
        versions file) gaining a ``Column(`` is not a model change."""
        repo = _make_repo(tmp_path)
        path = repo / "alembic/env.py"
        path.write_text(path.read_text() + "from sqlalchemy import Column\nx = Column()\n")
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"

    def test_a_schema_word_in_a_non_python_file_is_a_no_op(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        path = repo / "README.md"
        path.write_text(path.read_text() + "\nUse mapped_column( for every column.\n")
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"

    def test_a_removed_column_line_is_a_no_op(self, tmp_path: Path) -> None:
        """Only ADDED lines count. Dropping a column is a schema change too,
        but the spec's rule reads added lines; a removal is not read as one."""
        repo = _make_repo(tmp_path)
        path = repo / MODEL_FILE
        path.write_text(path.read_text().replace(
            "    full_name: Mapped[str | None] = mapped_column(String, nullable=True)\n", ""
        ))
        assert "full_name" not in path.read_text()
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"

    def test_a_python_change_without_a_schema_line_is_a_no_op(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        path = repo / MODEL_FILE
        path.write_text(path.read_text() + "\n    def display(self) -> str:\n        return self.email\n")
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"

    def test_a_clean_worktree_is_a_no_op(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"


# ---------------------------------------------------------------------------
# (d) git cannot run: no-op, and the reason is logged
# ---------------------------------------------------------------------------


class TestGitCannotRunIsANoOp:
    def test_worktree_that_is_not_a_git_repository(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An Alembic tree and a model change, but no ``.git``: ``git diff
        HEAD`` fails, the guard stays out of the verdict and says why."""
        repo = tmp_path / "plain"
        _write(repo, "alembic/env.py", "# env\n")
        _write(repo, MODEL_FILE, MODEL_SOURCE + DOMAIN_COLUMN_LINE)
        decision = _approve()

        with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker"):
            _run_guard(repo, decision)

        assert decision["decision"] == "approve"
        assert decision["issues"] == []
        assert any(
            "schema change without migration" in r.getMessage()
            and "judged without this guard" in r.getMessage()
            for r in caplog.records
        )

    def test_git_binary_missing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        decision = _approve()

        with patch("subprocess.run", side_effect=FileNotFoundError("git")):
            with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker"):
                _run_guard(repo, decision)

        assert decision["decision"] == "approve"
        assert any(
            "git could not run" in r.getMessage() and "FileNotFoundError" in r.getMessage()
            for r in caplog.records
        )

    def test_git_timeout(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        decision = _approve()

        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=30),
        ):
            with caplog.at_level(logging.WARNING, logger="guardkit.orchestrator.agent_invoker"):
                _run_guard(repo, decision)

        assert decision["decision"] == "approve"
        assert any("git timed out" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# (e) a feedback verdict is never touched
# ---------------------------------------------------------------------------


class TestFeedbackIsNeverTouched:
    def test_feedback_over_the_firing_shape_is_left_exactly_as_it_was(
        self, tmp_path: Path
    ) -> None:
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        decision = _feedback()
        before = json.loads(json.dumps(decision))

        output_path = _run_guard(repo, decision)

        assert decision == before
        assert json.loads(output_path.read_text()) == before

    def test_no_worktree_on_the_invoker_is_a_no_op(self, tmp_path: Path) -> None:
        invoker = _make_invoker(tmp_path)
        invoker.worktree_path = None  # type: ignore[assignment]
        decision = _approve()

        invoker._apply_schema_change_without_migration_guard(
            decision=decision,
            evidence_bundle=None,
            task_id="TASK-TEST-001",
            turn=1,
            coach_output_path=tmp_path / "coach_turn_1.json",
        )

        assert decision["decision"] == "approve"


# ---------------------------------------------------------------------------
# (f) where the Alembic tree is, and so where the migration must be
# ---------------------------------------------------------------------------


class TestAlembicTreeDetection:
    def test_migrations_env_py_names_migrations_versions(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, alembic_tree="migrations/env.py")
        _add_domain_column(repo)
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "feedback"
        assert "under `migrations/versions/`" in decision["issues"][0]["description"]
        assert decision["issues"][0]["details"]["migrations_dir"] == "migrations"

    def test_migrations_env_py_with_a_new_migration_is_satisfied(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, alembic_tree="migrations/env.py")
        _add_domain_column(repo)
        _write(repo, "migrations/versions/0002_add_domain.py", MIGRATION_SOURCE)
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "approve"

    def test_alembic_ini_alone_defaults_to_alembic(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, alembic_tree="alembic.ini")
        assert not (repo / "alembic/env.py").exists()
        _add_domain_column(repo)
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "feedback"
        assert "under `alembic/versions/`" in decision["issues"][0]["description"]

    def test_alembic_ini_script_location_is_honoured(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, alembic_tree="alembic.ini:db/migrations")
        _add_domain_column(repo)
        decision = _approve()

        _run_guard(repo, decision)

        assert decision["decision"] == "feedback"
        assert "under `db/migrations/versions/`" in decision["issues"][0]["description"]

        # ... and a migration there satisfies it
        _write(repo, "db/migrations/versions/0002_add_domain.py", MIGRATION_SOURCE)
        again = _approve()
        _run_guard(repo, again)
        assert again["decision"] == "approve"

    def test_alembic_ini_here_prefix_is_stripped(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path, alembic_tree="alembic.ini:%(here)s/alembic")
        assert AgentInvoker._alembic_migrations_dir(repo) == "alembic"

    def test_no_tree_is_none(self, tmp_path: Path) -> None:
        assert AgentInvoker._alembic_migrations_dir(tmp_path) is None


# ---------------------------------------------------------------------------
# (g) the helpers: what counts as a source file, and reading the diff
# ---------------------------------------------------------------------------


class TestHelpers:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("src/users/models.py", True),
            ("app.py", True),
            ("tests/test_models.py", False),
            ("src/pkg/tests/factories.py", False),
            ("alembic/env.py", False),
            ("alembic/versions/0002.py", False),
            ("alembic", False),
            ("alembic_helpers/x.py", True),
            ("src/users/models.txt", False),
            ("README.md", False),
        ],
    )
    def test_is_schema_source_file(self, path: str, expected: bool) -> None:
        assert AgentInvoker._is_schema_source_file(path, "alembic") is expected

    def test_added_lines_from_unified_diff(self) -> None:
        diff = (
            "diff --git a/src/users/models.py b/src/users/models.py\n"
            "index 1111111..2222222 100644\n"
            "--- a/src/users/models.py\n"
            "+++ b/src/users/models.py\n"
            "@@ -13,0 +14 @@ class User(Base):\n"
            "+    domain: Mapped[str | None] = mapped_column(String(255))\n"
            "@@ -20 +21 @@\n"
            "-    old = 1\n"
            "+    new = 2\n"
            "diff --git a/src/gone.py b/src/gone.py\n"
            "deleted file mode 100644\n"
            "--- a/src/gone.py\n"
            "+++ /dev/null\n"
            "@@ -1 +0,0 @@\n"
            "-x = Column()\n"
            "diff --git a/src/new.py b/src/new.py\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            "+++ b/src/new.py\n"
            "@@ -0,0 +1,2 @@\n"
            "+++ not a header, an added line starting with two pluses\n"
            "+y = 1\n"
        )

        added = AgentInvoker._added_lines_from_unified_diff(diff)

        assert added == {
            "src/users/models.py": [
                "    domain: Mapped[str | None] = mapped_column(String(255))",
                "    new = 2",
            ],
            "src/new.py": [
                "++ not a header, an added line starting with two pluses",
                "y = 1",
            ],
        }

    def test_a_second_call_changes_nothing(self, tmp_path: Path) -> None:
        """Idempotent: re-running the guard over an already-flipped decision
        (now ``feedback``) leaves it exactly as it was."""
        repo = _make_repo(tmp_path)
        _add_domain_column(repo)
        decision = _approve()
        output_path = _run_guard(repo, decision)
        before = json.loads(json.dumps(decision))

        _make_invoker(repo)._apply_schema_change_without_migration_guard(
            decision=decision,
            evidence_bundle=None,
            task_id="TASK-TEST-001",
            turn=1,
            coach_output_path=output_path,
        )

        assert decision == before
