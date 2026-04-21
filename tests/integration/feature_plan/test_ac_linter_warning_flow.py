"""Integration test: /feature-plan post-step AC linter (warn-mode v1).

Exercises the full plan-level flow — simulates a planner output of
mixed-quality tasks, runs them through ``lint_plan_warnings``, and
asserts the expected warn-surface. Does NOT invoke the actual
/feature-plan skill (that's a markdown-driven prompt); instead mocks
the planner's data handoff shape.

See TASK-AC-53445 §Acceptance Criteria.
"""

from __future__ import annotations

import pytest

from guardkit.orchestrator.quality_gates.ac_linter import (
    format_warning_summary,
    lint_plan_warnings,
)
from guardkit.orchestrator.quality_gates.criteria_classifier import (
    UnverifiableACWarning,
)


@pytest.fixture
def mock_feature_plan_output():
    """Shape of what /feature-plan would hand to the post-step.

    Mirrors the task dicts the planner holds in memory just after
    writing task markdown files (id + acceptance_criteria being the
    only fields the linter cares about).
    """
    return [
        {
            "id": "TASK-FP-0001",
            "title": "Create dependency declaration",
            "acceptance_criteria": [
                "- [ ] `yt-dlp>=2024.1.0` added to `dependencies` list in `pyproject.toml`",
                "- [ ] `pip install -e \".[dev]\"` succeeds without errors",
            ],
        },
        {
            "id": "TASK-FP-0002",
            "title": "Wire transcript fetcher",
            "acceptance_criteria": [
                # Unverifiable prose — this is the F3/F6 pattern the
                # review called out as load-bearing.
                "- [ ] handles edge cases correctly",
                "- [ ] backward-compatible defaults ensure no breakage",
            ],
        },
        {
            "id": "TASK-FP-0003",
            "title": "Add smoke tests",
            "acceptance_criteria": [
                "- [ ] `pytest tests/smoke/ -v` passes all tests",
            ],
        },
    ]


class TestProseAcsSurfaceWarnings:
    """AC line 71 of TASK-AC-53445:
    planner run on mocked feature description emits >=1 warning
    without blocking.
    """

    def test_prose_acs_surface_warnings(self, mock_feature_plan_output):
        warnings = lint_plan_warnings(mock_feature_plan_output)

        # >=1 warning surfaced (AC requirement).
        assert len(warnings) >= 1

        # Specifically, the two prose ACs in TASK-FP-0002 must both
        # surface; verifiable ACs elsewhere must not.
        flagged_task_ids = {w.task_id for w in warnings}
        assert flagged_task_ids == {"TASK-FP-0002"}
        assert len(warnings) == 2

        # Warnings carry verbatim AC text for downstream rewrite UX.
        texts = {w.ac_text for w in warnings}
        assert any("handles edge cases correctly" in t for t in texts)
        assert any("backward-compatible defaults" in t for t in texts)

    def test_linter_does_not_raise_on_empty_plan(self):
        """Non-blocking guarantee: an empty plan doesn't explode."""
        assert lint_plan_warnings([]) == []

    def test_linter_tolerates_missing_acceptance_criteria(self):
        """Malformed planner output must degrade to zero warnings, not error."""
        warnings = lint_plan_warnings([{"id": "TASK-FP-0004"}])
        assert warnings == []

    def test_linter_tolerates_missing_task_id(self):
        """Anonymous task falls back to '<unknown>' rather than crashing."""
        warnings = lint_plan_warnings(
            [{"acceptance_criteria": ["- [ ] handles edge cases correctly"]}]
        )
        assert len(warnings) == 1
        assert warnings[0].task_id == "<unknown>"

    def test_warning_summary_is_human_readable(self, mock_feature_plan_output):
        """Format must surface count + per-task grouping for planner output."""
        warnings = lint_plan_warnings(mock_feature_plan_output)
        summary = format_warning_summary(warnings)

        assert "2 unverifiable acceptance criteria" in summary
        assert "TASK-FP-0002" in summary
        assert "handles edge cases correctly" in summary
        # Warn-mode framing — must be explicit this is non-blocking.
        assert "non-blocking" in summary or "warn" in summary.lower()

    def test_empty_warning_summary_still_reports_zero(self):
        """Callers can display the summary unconditionally."""
        summary = format_warning_summary([])
        assert "0 unverifiable" in summary


class TestLinterReasonFidelity:
    """Warnings must echo the classifier's reason verbatim.

    This is the architectural invariant: if warning.reason ever disagrees
    with ClassifiedCriterion.reason, the single-source-of-truth guarantee
    is broken.
    """

    def test_warning_reason_is_classifier_reason(self):
        warnings = lint_plan_warnings(
            [
                {
                    "id": "TASK-FIDELITY",
                    "acceptance_criteria": [
                        "- [ ] handles edge cases correctly",
                    ],
                }
            ]
        )
        assert len(warnings) == 1
        # The classifier's default fallback reason — if this drifts we
        # know someone has grown a parallel "reason" path in the linter.
        assert "defaulting to file_content" in warnings[0].reason
