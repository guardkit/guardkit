"""
Unit tests for how AutoBuild treats a sibling repository's test result.

The stall detectors this file used to cover were removed in the cull of
27 October 2026. What remained was ``_evidence_repo_gate``, a separate gate
for declared sibling repositories that sent the turn back only when a suite
ran and failed, and let a suite that could not run through to approval. It
was removed on 31 October 2026: a sibling the task changed is one more part
of the task's check (``CoachValidator.run_changed_parts``), so its result
reaches AutoBuild inside ``independent_tests`` and is handled exactly as a
part's. These tests cover that hand-over.
"""

from pathlib import Path

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.orchestrator.quality_gates.coach_validator import (
    IndependentTestResult,
    SiblingPart,
    combine_part_results,
)


def _sibling(name="guardkitfactory"):
    return SiblingPart(
        name=f"sibling repository {name}", cwd=f"/repos/{name}", repository=name
    )


def _stop(result):
    orchestrator = AutoBuildOrchestrator(repo_root=Path.cwd(), max_turns=5)
    return orchestrator._check_could_not_run_stop(
        CoachEvidenceBundle(independent_tests=result), "TASK-SIB-1", 1, 0.0
    )


class TestASiblingsResultInAutoBuild:
    def test_the_separate_gate_is_gone(self):
        assert not hasattr(AutoBuildOrchestrator, "_evidence_repo_gate")

    def test_a_sibling_that_could_not_run_stops_the_task(self):
        # Was test_suite_that_could_not_run_sends_nothing_back.
        result = combine_part_results(
            [
                (
                    _sibling(),
                    IndependentTestResult.could_not_run(
                        test_command="no-such-program",
                        detail="its program `no-such-program` is not on the command's PATH",
                        duration_seconds=0.0,
                    ),
                )
            ]
        )
        stop = _stop(result)
        assert stop is not None
        assert stop.success is False
        assert stop.error.startswith("The check could not run")
        assert "guardkitfactory" in stop.error

    def test_a_sibling_that_failed_goes_on_to_be_sent_back(self):
        # Was test_suite_that_ran_and_failed_sends_the_turn_back: the failure
        # no longer stops here; like a part's, it reaches the reviewer and
        # the required-suite rule turns an approval into feedback.
        result = combine_part_results(
            [
                (
                    _sibling(),
                    IndependentTestResult.from_run(
                        tests_passed=False,
                        test_command="pytest -q",
                        test_output_summary="1 failed",
                        duration_seconds=0.1,
                        output="1 failed",
                        exit_code=1,
                    ),
                )
            ]
        )
        assert _stop(result) is None
        assert result.failure_receipt() is not None

    def test_a_passing_sibling_neither_stops_nor_fails(self):
        result = combine_part_results(
            [
                (
                    _sibling(),
                    IndependentTestResult.from_run(
                        tests_passed=True,
                        test_command="pytest -q",
                        test_output_summary="3 passed",
                        duration_seconds=0.1,
                        output="3 passed",
                        exit_code=0,
                    ),
                )
            ]
        )
        assert _stop(result) is None
        assert result.tests_passed is True

    def test_the_siblings_starting_commits_come_from_the_tasks_scope(self):
        from guardkit.orchestrator.task_work_scope import (
            RepositoryScope,
            TaskWorkScope,
        )

        orchestrator = AutoBuildOrchestrator(repo_root=Path.cwd(), max_turns=5)
        assert orchestrator._sibling_baselines() == {}
        orchestrator.task_work_scope = TaskWorkScope(
            task_id="TASK-SIB-1",
            feature_id="FEAT-SIB",
            scope_id="s",
            repositories=(
                RepositoryScope("", "/repos/product", "/g/p", "a" * 40, "b"),
                RepositoryScope("guardkitfactory", "/repos/gkf", "/g/f", "c" * 40, "b"),
            ),
        )
        assert orchestrator._sibling_baselines() == {"/repos/gkf": "c" * 40}
