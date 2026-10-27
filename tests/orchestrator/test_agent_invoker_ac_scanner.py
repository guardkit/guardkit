"""Tests for the file-existence promises a synthetic report carries.

(27 October 2026 cull: ``AgentInvoker._scan_ac_for_missing_paths`` and the
``_compute_plan_audit_verdict`` escalation it fed are deleted, with their
tests and the FEAT-PEBR fixture worktree that only they used.)
"""

from __future__ import annotations

from pathlib import Path

from guardkit.orchestrator.synthetic_report import (
    generate_file_existence_promises,
)


class TestSyntheticReportNonRegression:
    """``synthetic_report.generate_file_existence_promises`` matches a file
    named in the acceptance criteria against the files the turn changed."""

    def test_synthetic_report_still_promises_modified_basename(
        self, tmp_path: Path
    ) -> None:
        """The synthetic-report path matches a basename mentioned in AC
        text against the ``files_modified`` list and returns
        ``status="complete"``."""
        promises = generate_file_existence_promises(
            files_created=[],
            files_modified=["src/forge/adapters/nats/pipeline_consumer.py"],
            acceptance_criteria=[
                "`pipeline_consumer.py` publishes a recovery event."
            ],
            worktree_path=tmp_path,
        )

        assert len(promises) == 1
        # The bare basename in AC text matches against the qualified
        # entry in files_modified by suffix — synthetic-report's job.
        assert promises[0]["status"] in {"complete", "partial"}

    def test_synthetic_report_still_flags_unmentioned_qualified_path(
        self, tmp_path: Path
    ) -> None:
        """Qualified path in AC text that's nowhere in modified/created
        and not on disk → ``status="incomplete"``."""
        promises = generate_file_existence_promises(
            files_created=[],
            files_modified=[],
            acceptance_criteria=["Add `src/foo/bar/missing.py`."],
            worktree_path=tmp_path,
        )

        assert len(promises) == 1
        assert promises[0]["status"] == "incomplete"
