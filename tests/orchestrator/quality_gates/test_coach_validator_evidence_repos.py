"""CoachValidator sibling-repo independent tests (TASK-AB-XREPOEV01 AC-002).

The Coach must be able to run a declared sibling repo's tests independently
and have the results land in the evidence bundle, with a failed/unrunnable
suite blocking the turn.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.evidence_repos import EvidenceRepo
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


def _bundle(**kw) -> CoachEvidenceBundle:
    """Build a minimal bundle (only ``honesty`` is required)."""
    return CoachEvidenceBundle(honesty=HonestyVerification(verified=True), **kw)


class TestRunEvidenceRepoTests:
    def test_no_evidence_repos_returns_empty(self, tmp_path):
        validator = CoachValidator(str(tmp_path))
        assert validator.run_evidence_repo_tests() == []

    def test_runs_declared_passing_suite(self, tmp_path):
        factory = tmp_path / "guardkitfactory"
        factory.mkdir()
        repo = EvidenceRepo(
            name="guardkitfactory",
            root=factory,
            test_command="python -c 'import sys; sys.exit(0)'",
        )
        validator = CoachValidator(str(tmp_path), evidence_repos=[repo])
        results = validator.run_evidence_repo_tests()
        assert len(results) == 1
        assert results[0].repo_name == "guardkitfactory"
        assert results[0].ran is True
        assert results[0].passed is True

    def test_runs_declared_failing_suite(self, tmp_path):
        factory = tmp_path / "guardkitfactory"
        factory.mkdir()
        repo = EvidenceRepo(
            name="guardkitfactory",
            root=factory,
            test_command="python -c 'import sys; sys.exit(1)'",
        )
        validator = CoachValidator(str(tmp_path), evidence_repos=[repo])
        results = validator.run_evidence_repo_tests()
        assert results[0].ran is True
        assert results[0].passed is False


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
