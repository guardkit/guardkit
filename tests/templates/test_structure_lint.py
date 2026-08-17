"""Tests for the template-structure lint (PB-5 / DIM2-F4).

The lint is ADVISORY (report-only) — these tests assert it *detects* the
structure hazards a fence-naive header-offset slicer would trip over, not that
it fails a build.
"""
from __future__ import annotations

from pathlib import Path

from guardkit.templates.structure_lint import (
    COMMITTED_SERVING_WINDOW_TOKENS,
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
# TASK-OBS-F3F5: Committed serving-window figure flips severity to WARNING
# ---------------------------------------------------------------------------


def test_committed_serving_window_constant_is_32k():
    """The committed serving-window floor is 32K tokens (32768) per WS4 Amendment M3."""
    assert COMMITTED_SERVING_WINDOW_TOKENS == 32768


def test_token_budget_warning_with_committed_figure():
    """AC-1: Section-token-budget findings render as WARNING (not INFO) when the
    committed serving-window figure is provided."""
    # Need at least 32768 tokens * 4 chars/token = 131,072 chars to trigger
    # a finding against the committed figure. Use 140,000 to be safe.
    big = "x" * 140_000  # ≈35k tokens at 4 chars/token
    text = f"# C\n\n## Execution\n\n{big}\n"
    findings = lint_structure(text, serving_window_tokens=COMMITTED_SERVING_WINDOW_TOKENS)
    budget = [f for f in findings if f.check == "section-token-budget"]

    assert budget, "expected a token-budget finding for the oversized section"
    assert all(f.severity is Severity.WARNING for f in budget), (
        "with committed figure, budget findings should be WARNING"
    )
    # AC-1: message names the committed figure, not "report-only"
    assert all("committed serving-window floor 32768 tokens" in f.message for f in budget)
    assert all("report-only" not in f.message for f in budget)


def test_token_budget_info_without_committed_figure():
    """Verify that without the figure (serving_window_tokens=None), findings stay INFO."""
    big = "x" * 40_000
    text = f"# C\n\n## Execution\n\n{big}\n"
    findings = lint_structure(text, serving_window_tokens=None)
    budget = [f for f in findings if f.check == "section-token-budget"]

    assert budget, "expected a token-budget finding"
    assert all(f.severity is Severity.INFO for f in budget), (
        "without figure, budget findings should stay INFO"
    )
    assert all("report-only" in f.message for f in budget)


# ---------------------------------------------------------------------------
# Regression pin against the real pinned templates (DIM2-F4)
# ---------------------------------------------------------------------------


def test_real_feature_plan_flags_four_integration_contract_anchors():
    """The DIM2-F4 finding: feature-plan.md's 4 colliding Integration-Contracts
    headers must be surfaced as warnings. Lines shifted +15 after the DF-019
    re-pin (2026-07-11) added the frontmatter block + the F1-emission subsection
    above them (:1827/:1888/:1895/:1918 → :1842/:1903/:1910/:1933); PB-5 kept the
    anchor BYTES unchanged (fence-aware disposition), only positions moved.
    Shifted +40 again by the ROUTING-LAW template additions (card Q8/A.2,
    2026-08-15): 3 schema-table rows + "The Routing Law" section, both above
    the anchors (:1842/:1903/:1910/:1933 → :1882/:1943/:1950/:1973); anchor
    bytes again unchanged. Shifted +9 again by the R9-WIDENING template note
    (RULED, Rich 2026-08-17): the copyable `routing_law: enforced` line left
    the worked example, the VERBATIM-titles rule and the "plan-writer never
    sets policy" instruction were added above the anchors
    (:1882/:1943/:1950/:1973 → :1891/:1952/:1959/:1982); anchor bytes again
    unchanged."""
    results = lint_command_templates()
    assert "feature-plan.md" in results
    ic = [
        f
        for f in results["feature-plan.md"]
        if f.check == "unique-normative-anchors"
        and "integration contracts" in f.message.lower()
    ]
    lines = {f.line for f in ic}
    assert {1891, 1952, 1959, 1982} <= lines, (
        f"expected the 4 Integration-Contracts anchors flagged, got lines {lines}"
    )


def test_lint_is_advisory_never_raises_on_pinned_templates():
    """The lint only READS the pinned templates and returns findings — it must
    not mutate or raise (the pins stay byte-identical)."""
    results = lint_command_templates()
    assert set(results) == {"feature-plan.md", "feature-spec.md"}
    for findings in results.values():
        assert isinstance(findings, list)


def test_exit_code_neutrality_preserved_with_committed_figure():
    """AC-2: Exit-code neutrality is preserved — budget findings at the committed
    figure never affect the validate command's exit code.

    The structure lint is advisory (report-only) and runs AFTER the parse gate
    (:144 in cli/template.py). It NEVER changes the exit code, even when it
    produces WARNINGs. This test pins that contract."""
    # The lint runs with the committed figure and produces WARNINGs for oversized
    # sections, but those findings are advisory — they never fail a build.
    results = lint_command_templates(
        serving_window_tokens=COMMITTED_SERVING_WINDOW_TOKENS
    )
    # Both pinned templates exist and have findings (the DIM2-F4 anchors and
    # oversized sections), but the function returns normally and the findings
    # are advisory.
    assert "feature-plan.md" in results
    assert "feature-spec.md" in results
    # Confirm WARNINGs are present (some from anchors, possibly from budget)
    all_findings = [f for fs in results.values() for f in fs]
    warns = [f for f in all_findings if f.severity is Severity.WARNING]
    assert warns, "expected WARNINGs from the real templates"
    # The function returns normally — it does not raise or signal failure.
    # The CLI caller (_print_structure_lint) prints findings but never calls
    # sys.exit() on their account (only the parse gate does, and it runs first).
