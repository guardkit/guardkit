"""
Test the /feature-plan task classification guide exists and covers the
three known defect classes plus the operator_handoff escape hatch.

Anchors AC-FPTC-007-06 (TASK-FPTC-007 — docs and folder consolidation
for the feature-plan-defects feature).
"""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
GUIDE_PATH = REPO_ROOT / "docs" / "guides" / "feature-plan-task-classification.md"


def test_classification_guide_exists():
    """The guide file must exist at the AC-specified path."""
    assert GUIDE_PATH.exists(), f"Classification guide not found at {GUIDE_PATH}"


@pytest.mark.parametrize(
    "needle",
    ["Class A", "Class B", "Class C", "operator_handoff"],
)
def test_classification_guide_mentions_required_terms(needle: str):
    """
    AC-FPTC-007-06: the guide must mention each of the three defect
    classes and the operator_handoff escape hatch by name.
    """
    content = GUIDE_PATH.read_text(encoding="utf-8")
    assert needle in content, (
        f"Classification guide is missing required term: {needle!r}"
    )
