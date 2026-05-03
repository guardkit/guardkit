"""Contract tests for the operator_handoff detection rules in feature-plan.md.

The Plan agent reads installer/core/commands/feature-plan.md at runtime. The
detection rules in the "Detection Rules — when to mark a task `operator_handoff`"
subsection (added by TASK-FPTC-001) live as prompt text, not as Python code, so
the only safe regression guard is to pin the verbatim markers the agent must see.

Pinned by this test:

- AC-FPTC-001-04 — strong-signal markers ("FalkorDB", "live",
  "human-in-the-loop", "Claude Desktop", "p50", "p95", "wall-clock") plus the
  false-positive guard string ("weak signal alone does NOT trigger") are all
  present in the prompt.
- AC-FPTC-001-05 — the Task Type Assignment Rules table contains a row mapping
  the operator_handoff pattern (live infra / human-in-the-loop / wall-clock) to
  ``operator_handoff``.
"""

from pathlib import Path

import pytest


_PROMPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "commands"
    / "feature-plan.md"
)


@pytest.fixture(scope="module")
def prompt_text() -> str:
    assert _PROMPT_PATH.exists(), (
        f"Expected /feature-plan prompt at {_PROMPT_PATH}; not found"
    )
    return _PROMPT_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AC-FPTC-001-04 — strong-signal markers + false-positive guard
# ---------------------------------------------------------------------------

# Each marker is a verbatim phrase or token from §AC-AUTM-02 of the parent
# review. If the Plan agent loses any of these, the detector loses coverage of
# one of the four strong-signal categories.
_STRONG_SIGNAL_MARKERS = (
    "FalkorDB",          # live infrastructure (study-tutor TASK-GR-SEED reproducer)
    "live",              # live infrastructure category keyword
    "human-in-the-loop", # human verbs / author self-disclosure
    "Claude Desktop",    # human verbs (study-tutor TASK-GR-DEMO reproducer)
    "p50",               # wall-clock language
    "p95",               # wall-clock language
    "wall-clock",        # wall-clock language category keyword
)


@pytest.mark.parametrize("marker", _STRONG_SIGNAL_MARKERS)
def test_strong_signal_marker_present(prompt_text: str, marker: str) -> None:
    """Each strong-signal marker from AC-AUTM-02 must appear verbatim."""
    assert marker in prompt_text, (
        f"Strong-signal marker {marker!r} missing from feature-plan.md — the "
        "Plan agent will lose coverage of that detection category. See "
        ".claude/reviews/TASK-REV-AUTM-review-report.md §AC-AUTM-02."
    )


def test_false_positive_guard_present(prompt_text: str) -> None:
    """The false-positive guard ('weak signal alone does NOT trigger') must
    appear verbatim so the agent knows weak-only matches must not fire the
    operator-handoff prompt.
    """
    assert "weak signal alone does NOT trigger" in prompt_text, (
        "Missing false-positive guard string from feature-plan.md. The agent "
        "must not flag tasks on weak signals alone — see "
        ".claude/reviews/TASK-REV-AUTM-review-report.md §AC-AUTM-02."
    )


def test_detection_rules_section_heading_present(prompt_text: str) -> None:
    """The dedicated 'Detection Rules' subsection must exist by name so the
    agent can locate the rules block and humans reading the prompt can find
    the rationale.
    """
    assert "Detection Rules — when to mark a task `operator_handoff`" in prompt_text, (
        "Detection Rules section heading missing from feature-plan.md. "
        "AC-FPTC-001-01 requires a dedicated section."
    )


# ---------------------------------------------------------------------------
# AC-FPTC-001-05 — operator_handoff row in Task Type Assignment Rules table
# ---------------------------------------------------------------------------

def test_operator_handoff_row_in_assignment_table(prompt_text: str) -> None:
    """The Task Type Assignment Rules table must contain a row mapping the
    operator_handoff pattern (live infrastructure / human-in-the-loop /
    wall-clock observation) to ``operator_handoff``. Pinned as a single
    substring so reordering columns doesn't silently break the rule.
    """
    expected_row_fragment = (
        "Live infrastructure / human-in-the-loop / wall-clock observation "
        "patterns"
    )
    assert expected_row_fragment in prompt_text, (
        "Task Type Assignment Rules table is missing the operator_handoff "
        "pattern row. AC-FPTC-001-02 requires this row so the rules table "
        "and the Detection Rules subsection stay in sync."
    )
    assert "`operator_handoff`" in prompt_text, (
        "Task Type Assignment Rules table mentions the operator_handoff "
        "pattern but never names the task_type value. The agent will not "
        "know what to emit."
    )
