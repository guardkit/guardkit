"""WS2-B10 gate: every committed tier-2/3 exemplar validates; every mutated copy
fails LOUDLY with field-level messages.

Mirrors the B1 discipline (tests/qa/test_format_exemplars.py) for the formats
B10 owns: F6 seam-manifest, F7 deploy-record, F10 live-matrix, F11 runbook
(markdown), F12 discovery-gates, F13 kickoff-prompt, F14 review-findings, F15
walk-checkpoints, and the deploy-profile format (scope-design §4). Exemplars are
derived from the two fixture repos' committed artifacts — the schema work is not
done until a real instance validates (scope-design §2 evolution rules).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.qa.formats import QAFormatError, resolve_kind, validate_instance

FIXTURES = Path(__file__).parent.parent / "fixtures" / "qa_formats"

# (kind, relative fixture path) — YAML exemplars, both fixture repos where the
# committed artifact supports one.
YAML_EXEMPLARS = [
    ("seam-manifest", "lpa-platform-poc/seam-manifest.yaml"),
    ("seam-manifest", "study-tutor/seam-manifest.yaml"),
    ("deploy-record", "lpa-platform-poc/deploy-record.yaml"),
    ("deploy-record", "study-tutor/deploy-record.yaml"),
    ("live-matrix", "lpa-platform-poc/live-matrix.yaml"),
    ("live-matrix", "study-tutor/live-matrix.yaml"),
    ("deploy-profile", "lpa-platform-poc/deploy-profile.yaml"),
    ("deploy-profile", "study-tutor/deploy-profile.yaml"),
    ("discovery-gates", "study-tutor/discovery-gates.yaml"),
    ("kickoff-prompt", "lpa-platform-poc/kickoff-prompt.yaml"),
    ("review-findings", "study-tutor/review-findings.yaml"),
    ("walk-checkpoints", "study-tutor/walk-checkpoints.yaml"),
]

# The F11 markdown-convention exemplar (validated by conventions, not YAML).
MARKDOWN_EXEMPLARS = [
    ("runbook", "lpa-platform-poc/runbook-foundation.md"),
]

# (kind, relative fixture path, substrings the loud failure must mention)
MUTANTS = [
    (
        "seam-manifest",
        "mutated/seam-manifest-mutated.yaml",
        ["kind", "sha", "attribution_sides"],
    ),
    (
        "deploy-record",
        "mutated/deploy-record-mutated.yaml",
        ["deployer", "evidence_artifact", "committed_at"],
    ),
    (
        "live-matrix",
        "mutated/live-matrix-mutated.yaml",
        ["redrive_policy", "risk_rank", "last_driven"],
    ),
    (
        "deploy-profile",
        "mutated/deploy-profile-mutated.yaml",
        ["env_id", "file", "REFS ONLY"],
    ),
    (
        "discovery-gates",
        "mutated/discovery-gates-mutated.yaml",
        ["gate", "probe"],
    ),
    (
        "kickoff-prompt",
        "mutated/kickoff-prompt-mutated.yaml",
        ["guardrails", "gate_ref"],
    ),
    (
        "review-findings",
        "mutated/review-findings-mutated.yaml",
        ["executed_reproduction", "refuter"],
    ),
    (
        "walk-checkpoints",
        "mutated/walk-checkpoints-mutated.yaml",
        ["install_cmd", "kind", "evidence_artifact"],
    ),
    (
        "runbook",
        "mutated/runbook-mutated.md",
        ["Facts", "Pass", "type"],
    ),
]


@pytest.mark.parametrize("kind,rel_path", YAML_EXEMPLARS + MARKDOWN_EXEMPLARS)
def test_exemplar_validates(kind: str, rel_path: str) -> None:
    instance = validate_instance(kind, FIXTURES / rel_path)
    assert instance.FORMAT_KIND == kind
    assert instance.format_version == "1.0"


@pytest.mark.parametrize("kind,rel_path,expected_mentions", MUTANTS)
def test_mutated_copy_fails_loudly(
    kind: str, rel_path: str, expected_mentions: list
) -> None:
    path = FIXTURES / rel_path
    with pytest.raises(QAFormatError) as excinfo:
        validate_instance(kind, path)
    message = str(excinfo.value)
    # Loud: names the file and the kind...
    assert str(path) in message
    assert "INVALID" in message
    # ...and every seeded mutation is called out at field level.
    for mention in expected_mentions:
        assert mention in message, f"mutation {mention!r} not reported in:\n{message}"


def test_f_number_aliases_resolve_same_models() -> None:
    for alias, canonical in [
        ("f6", "seam-manifest"),
        ("f7", "deploy-record"),
        ("f8", "disposition-record"),
        ("f9", "attempts-ledger"),
        ("f10", "live-matrix"),
        ("f11", "runbook"),
        ("f12", "discovery-gates"),
        ("f13", "kickoff-prompt"),
        ("f14", "review-findings"),
        ("f15", "walk-checkpoints"),
    ]:
        assert resolve_kind(alias) is resolve_kind(canonical)


def test_runbook_missing_marker_fails_loudly(tmp_path: Path) -> None:
    """A markdown runbook with no machine marker fails loudly (version unpinnable)."""
    p = tmp_path / "no-marker.md"
    p.write_text("# Runbook\n\n## Facts\n\n## Phase 1: x — type: verify\n**Pass:** ok\n")
    with pytest.raises(QAFormatError, match="machine marker"):
        validate_instance("runbook", p)
