"""CoachValidator sibling-repo independent tests (TASK-AB-XREPOEV01 AC-002).

The Coach must be able to run a declared sibling repo's tests independently
and have the results land in the evidence bundle. Since 31 October 2026 a
sibling the task changed is one more part of the task's check.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import pytest

from guardkit.orchestrator.evidence_repos import EvidenceRepo
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.toolchain_declaration import ToolchainDeclaration

# The running interpreter, not a bare ``python`` that may not be on PATH.
_PYTHON = shlex.quote(sys.executable)


def _bundle(**kw) -> CoachEvidenceBundle:
    """Build a minimal bundle (every field has a default)."""
    return CoachEvidenceBundle(**kw)


class TestRunEvidenceRepoTests:
    # ``run_evidence_repo_tests`` (every declared sibling, every turn, into a
    # separate result type) was removed on 31 October 2026: a sibling the
    # task changed is a part of ``run_changed_parts``, run by
    # ``_run_sibling_tests``. These keep their cases on that path.

    def test_no_evidence_repos_runs_no_sibling(self, tmp_path):
        validator = CoachValidator(str(tmp_path))
        assert validator._changed_siblings() == []

    def test_runs_declared_passing_suite(self, tmp_path):
        factory = tmp_path / "guardkitfactory"
        factory.mkdir()
        repo = EvidenceRepo(
            name="guardkitfactory",
            root=factory,
            test_command=f"{_PYTHON} -c 'import sys; sys.exit(0)'",
        )
        validator = CoachValidator(str(tmp_path), evidence_repos=[repo])
        result = validator._run_sibling_tests(repo)
        assert result.check_could_not_run is False
        assert result.tests_passed is True

    def test_runs_declared_failing_suite(self, tmp_path):
        factory = tmp_path / "guardkitfactory"
        factory.mkdir()
        repo = EvidenceRepo(
            name="guardkitfactory",
            root=factory,
            test_command=f"{_PYTHON} -c 'import sys; sys.exit(1)'",
        )
        validator = CoachValidator(str(tmp_path), evidence_repos=[repo])
        result = validator._run_sibling_tests(repo)
        assert result.check_could_not_run is False
        assert result.tests_passed is False

    def test_the_sibling_runs_the_interpreter_its_command_names(self, tmp_path):
        """A sibling's tests never run under the worktree's venv. Since 31
        October 2026 nothing is put first either: the sibling's own ``.venv``
        is no longer found and swapped in for a bare ``pytest`` (that test
        kept the implicit choice, removed as a hidden Python default), so the
        declaration names the interpreter and that one runs."""

        def _fake_interpreter(path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('#!/bin/sh\necho "$0" > ran_by.txt\nexit 0\n')
            path.chmod(0o755)
            return path

        worktree = tmp_path / "worktree"
        worktree.mkdir()
        worktree_python = _fake_interpreter(
            worktree / ".venv" / "bin" / "python"
        )
        sibling = tmp_path / "guardkitfactory"
        sibling.mkdir()
        sibling_python = _fake_interpreter(
            sibling / ".venv" / "bin" / "python"
        )

        repo = EvidenceRepo(
            name="guardkitfactory",
            root=sibling,
            test_command=".venv/bin/python -m pytest -q",
        )
        validator = CoachValidator(
            str(worktree),
            evidence_repos=[repo],
        )
        result = validator._run_sibling_tests(repo)
        assert result.check_could_not_run is False
        assert result.tests_passed is True

        ran_by = (sibling / "ran_by.txt").read_text()
        assert ran_by.strip() == ".venv/bin/python"
        assert str(worktree_python) not in ran_by
        assert sibling_python.exists()


class TestEvidenceBundleLandingField:
    def test_bundle_carries_evidence_repo_tests(self):
        bundle = _bundle(
            evidence_repo_tests=[
                {"repo_name": "guardkitfactory", "ran": True, "passed": True}
            ]
        )
        # The field survives serialisation (reaches coach_turn_N.json).
        as_dict = bundle.to_dict()
        assert as_dict["evidence_repo_tests"] == [
            {"repo_name": "guardkitfactory", "ran": True, "passed": True}
        ]

    def test_bundle_defaults_to_empty_list(self):
        bundle = _bundle()
        assert bundle.evidence_repo_tests == []

    def test_gather_evidence_records_each_changed_siblings_run(self, tmp_path):
        """The sibling's run is a part of ``independent_tests`` (31 October
        2026) and its record is repeated in ``evidence_repo_tests``."""
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        factory = tmp_path / "guardkitfactory"
        factory.mkdir()
        repo = EvidenceRepo(
            name="guardkitfactory", root=factory, test_command="exit 1"
        )
        # No starting commit is known for either, so the sibling is tested.
        validator = CoachValidator(
            str(worktree),
            evidence_repos=[repo],
            toolchain=ToolchainDeclaration(test="true"),
        )
        bundle = validator.gather_evidence(
            task_id="TASK-SIB-1", turn=1, task={"task_type": "feature"}
        )
        assert bundle.independent_tests.tests_passed is False
        assert bundle.independent_tests.failure_receipt() is not None
        assert [r["repository"] for r in bundle.evidence_repo_tests] == [
            "guardkitfactory"
        ]
        assert bundle.evidence_repo_tests[0]["outcome"] == "failed"
