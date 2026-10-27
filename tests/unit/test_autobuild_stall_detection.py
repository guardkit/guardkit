"""
Unit tests for the sibling-repository test gate in AutoBuild.

The stall detectors this file used to cover were removed in the cull of
27 October 2026. What remains here is ``_evidence_repo_gate``: a declared
sibling repository's test suite that ran and failed sends the turn back to
the Player; a suite that could not run sends nothing back.
"""

from pathlib import Path
from unittest.mock import Mock

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.evidence_repos import EvidenceTestResult

from guardkit.worktrees import Worktree


class TestEvidenceRepoGate:
    """_evidence_repo_gate sends the turn back only when a suite ran and failed."""

    def _run_gate(self, tmp_path, results):
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=5,
        )
        validator = Mock()
        validator.run_evidence_repo_tests.return_value = results
        worktree = Mock(spec=Worktree)
        worktree.path = tmp_path
        return orchestrator._evidence_repo_gate(
            validator,
            "TASK-FIX-SIBTESTENV01",
            1,
            worktree,
            0.0,
        )

    def test_suite_that_could_not_run_sends_nothing_back(self, tmp_path):
        results = [
            EvidenceTestResult(
                repo_name="guardkitfactory",
                command="python -m pytest tests/wiring -q",
                ran=False,
                passed=False,
                returncode=2,
                output_summary="collection failed with an import error",
            )
        ]
        assert self._run_gate(tmp_path, results) is None

    def test_suite_that_ran_and_failed_sends_the_turn_back(self, tmp_path):
        results = [
            EvidenceTestResult(
                repo_name="guardkitfactory",
                command="python -m pytest tests/wiring -q",
                ran=False,
                passed=False,
                returncode=2,
                output_summary="collection failed with an import error",
            ),
            EvidenceTestResult(
                repo_name="other",
                command="pytest -q",
                ran=True,
                passed=False,
                returncode=1,
                output_summary="1 failed",
            ),
        ]
        gate_result = self._run_gate(tmp_path, results)
        assert gate_result is not None
        assert gate_result.report["decision"] == "feedback"
        rationale = gate_result.report["rationale"]
        # Only the suite that ran and failed is named.
        assert "other" in rationale
        assert "guardkitfactory" not in rationale
        # The decision is written where the turn loop reads it.
        written = list(tmp_path.rglob("coach_turn_1.json"))
        assert written

    def test_passing_suite_sends_nothing_back(self, tmp_path):
        results = [
            EvidenceTestResult(
                repo_name="other",
                command="pytest -q",
                ran=True,
                passed=True,
                returncode=0,
                output_summary="3 passed",
            ),
        ]
        assert self._run_gate(tmp_path, results) is None
