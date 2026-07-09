"""Tests for the template-structure lint (PB-5 / DIM2-F4).

The lint is ADVISORY (report-only) — these tests assert it *detects* the
structure hazards a fence-naive header-offset slicer would trip over, not that
it fails a build.
"""
from __future__ import annotations

from pathlib import Path

from guardkit.templates.structure_lint import (
    Severity,
    lint_command_templates,
    lint_structure,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _warnings(findings, check=None):
    return [
        f
        for f in findings
        if f.severity is Severity.WARNING and (check is None or f.check == check)
    ]


# ---------------------------------------------------------------------------
# (a) unique normative anchors
# ---------------------------------------------------------------------------

_COLLIDING = """\
# Command

## Execution Flow

Do the thing.

## Integration Contracts

First normative section.

## §4: Integration Contracts

Second normative section — collides with the first.
"""

_CLEAN = """\
# Command

## Overview

A short overview.

## Execution Flow

The execution protocol lives here.

**Example:**

```markdown
## Some Example Header

illustrative only
```

## Wrap Up

Done.
"""


def test_colliding_anchor_fixture_warns():
    findings = lint_structure(_COLLIDING)
    anchor_warns = _warnings(findings, "unique-normative-anchors")
    assert len(anchor_warns) == 2
    assert {w.line for w in anchor_warns} == {7, 11}


def test_clean_synthetic_template_passes():
    """A well-formed template yields NO warnings (info is allowed)."""
    findings = lint_structure(_CLEAN)
    assert _warnings(findings) == [], (
        "clean template should produce no warnings, got: "
        + ", ".join(f"{w.check}@{w.line}" for w in _warnings(findings))
    )


def test_fenced_headers_alone_do_not_collide():
    """Two identical *fenced* example headers with no normative twin: no warning."""
    text = (
        "# C\n\n## Execution\n\n**Example:**\n\n```markdown\n## Foo\n```\n\n"
        "**Example:**\n\n```markdown\n## Foo\n```\n"
    )
    assert _warnings(lint_structure(text), "unique-normative-anchors") == []


def test_fenced_header_collides_with_a_normative_twin():
    """A normative header + a fenced echo of it IS the naive-slicer hazard."""
    text = "# C\n\n## Execution\n\n## Foo\n\n**Example:**\n\n```markdown\n## Foo\n```\n"
    warns = _warnings(lint_structure(text), "unique-normative-anchors")
    assert len(warns) == 2  # the normative one and the fenced echo


# ---------------------------------------------------------------------------
# (b) protocol-section presence
# ---------------------------------------------------------------------------


def test_missing_protocol_section_warns():
    text = "# C\n\n## Overview\n\nNo protocol here.\n"
    warns = _warnings(lint_structure(text), "protocol-section-presence")
    assert len(warns) == 1


def test_protocol_section_present_no_warning():
    text = "# C\n\n## Workflow\n\nThe steps.\n"
    assert _warnings(lint_structure(text), "protocol-section-presence") == []


# ---------------------------------------------------------------------------
# (c) per-section token budgets — report-only (INFO) with no serving window
# ---------------------------------------------------------------------------


def test_token_budget_is_info_only_when_no_serving_window():
    big = "x" * 40_000
    text = f"# C\n\n## Execution\n\n{big}\n"
    findings = lint_structure(text, serving_window_tokens=None)
    budget = [f for f in findings if f.check == "section-token-budget"]
    assert budget, "expected a token-budget finding for the oversized section"
    assert all(f.severity is Severity.INFO for f in budget)


def test_token_budget_becomes_warning_with_committed_window():
    big = "x" * 40_000
    text = f"# C\n\n## Execution\n\n{big}\n"
    findings = lint_structure(text, serving_window_tokens=2000)
    budget = _warnings(findings, "section-token-budget")
    assert budget, "a committed serving-window figure should make this a warning"


# ---------------------------------------------------------------------------
# (d) non-normative example marking
# ---------------------------------------------------------------------------


def test_unmarked_example_block_warns():
    text = "# C\n\n## Execution\n\n```markdown\n## Contract\n\nbody\n```\n"
    warns = _warnings(lint_structure(text), "example-block-marking")
    assert len(warns) == 1


def test_marked_example_block_no_warning():
    text = "# C\n\n## Execution\n\n**Example:**\n\n```markdown\n## Contract\n```\n"
    assert _warnings(lint_structure(text), "example-block-marking") == []


# ---------------------------------------------------------------------------
# Regression pin against the real pinned templates (DIM2-F4)
# ---------------------------------------------------------------------------


def test_real_feature_plan_flags_four_integration_contract_anchors():
    """The DIM2-F4 finding: feature-plan.md's 4 colliding Integration-Contracts
    headers (:1827/:1888/:1895/:1918) must be surfaced as warnings."""
    results = lint_command_templates()
    assert "feature-plan.md" in results
    ic = [
        f
        for f in results["feature-plan.md"]
        if f.check == "unique-normative-anchors"
        and "integration contracts" in f.message.lower()
    ]
    lines = {f.line for f in ic}
    assert {1827, 1888, 1895, 1918} <= lines, (
        f"expected the 4 Integration-Contracts anchors flagged, got lines {lines}"
    )


def test_lint_is_advisory_never_raises_on_pinned_templates():
    """The lint only READS the pinned templates and returns findings — it must
    not mutate or raise (the pins stay byte-identical)."""
    results = lint_command_templates()
    assert set(results) == {"feature-plan.md", "feature-spec.md"}
    for findings in results.values():
        assert isinstance(findings, list)
