"""WS2-B1 gate: every committed exemplar instance validates; every mutated
copy fails LOUDLY.

The 2x5 exemplars are derived from the two fixture repos' committed artifacts
(lpa-platform-poc B0 rescue commit 8980af1; study-tutor p2 live-acceptance
records) — the schema work is not done until a real instance validates
(scope-design §2 evolution rules).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.qa.formats import QAFormatError, validate_instance

FIXTURES = Path(__file__).parent.parent / "fixtures" / "qa_formats"

# (kind, relative fixture path) — the 10 committed exemplar instances.
EXEMPLARS = [
    ("pass-bar", "lpa-platform-poc/pass-bar-FEAT-POC-DEMO-0705.yaml"),
    ("known-failures", "lpa-platform-poc/known-failures.yaml"),
    ("leak-sweep", "lpa-platform-poc/leak-sweep.yaml"),
    ("gate-registry", "lpa-platform-poc/gates-registry.yaml"),
    ("evidence-index", "lpa-platform-poc/evidence-index.yaml"),
    ("pass-bar", "study-tutor/pass-bar-p2-wave-7.yaml"),
    ("known-failures", "study-tutor/known-failures.yaml"),
    ("leak-sweep", "study-tutor/leak-sweep.yaml"),
    ("gate-registry", "study-tutor/gates-registry.yaml"),
    ("evidence-index", "study-tutor/evidence-index.yaml"),
]

# (kind, relative fixture path, substrings the loud failure must mention)
MUTANTS = [
    (
        "pass-bar",
        "mutated/pass-bar-mutated.yaml",
        ["registered_at", "negative_paths", "runbook_ref"],
    ),
    (
        "known-failures",
        "mutated/known-failures-mutated.yaml",
        ["passed", "reason", "notes"],
    ),
    (
        "leak-sweep",
        "mutated/leak-sweep-mutated.yaml",
        ["deny", "scope", "wired_selector"],
    ),
    (
        "gate-registry",
        "mutated/gate-registry-mutated.yaml",
        ["pass_bar_ref", "url", "date"],
    ),
    (
        "evidence-index",
        "mutated/evidence-index-mutated.yaml",
        ["format_version", "artifact", "checkpoint_or_assertion_id"],
    ),
]


@pytest.mark.parametrize("kind,rel_path", EXEMPLARS)
def test_exemplar_validates(kind: str, rel_path: str) -> None:
    instance = validate_instance(kind, FIXTURES / rel_path)
    assert instance.format_version == "1.0"


@pytest.mark.parametrize("kind,rel_path,expected_mentions", MUTANTS)
def test_mutated_copy_fails_loudly(
    kind: str, rel_path: str, expected_mentions: list
) -> None:
    path = FIXTURES / rel_path
    with pytest.raises(QAFormatError) as excinfo:
        validate_instance(kind, path)
    message = str(excinfo.value)
    # Loud: the error names the file and the kind...
    assert str(path) in message
    assert "INVALID" in message
    # ...and every seeded mutation is called out at field level.
    for mention in expected_mentions:
        assert mention in message, (
            f"mutation {mention!r} not reported in:\n{message}"
        )


def test_f_number_aliases_resolve_same_models() -> None:
    from guardkit.qa.formats import resolve_kind

    for alias, canonical in [
        ("f1", "pass-bar"),
        ("f2", "known-failures"),
        ("f3", "leak-sweep"),
        ("f4", "gate-registry"),
        ("f5", "evidence-index"),
    ]:
        assert resolve_kind(alias) is resolve_kind(canonical)


def test_unknown_kind_is_loud() -> None:
    with pytest.raises(QAFormatError, match="unknown QA format kind"):
        validate_instance("f99", FIXTURES / "study-tutor/known-failures.yaml")


def test_results_envelope_round_trip() -> None:
    """The F4 results envelope (runner-emitted from B3 on) validates.

    No committed exemplar exists yet — the runner that writes envelopes is
    B3's deliverable — so the envelope is exercised synthetically, shaped
    from the lpa phase-6 sweep's real outcome.
    """
    from guardkit.qa.formats import ResultsEnvelope

    envelope = {
        "format_version": "1.0",
        "run_id": "lpa-2026-07-05-demo-push",
        "feature_id": "FEAT-POC-DEMO-0705",
        "target_env": "lpa-poc-tailnet",
        "started": "2026-07-05T18:00:00Z",
        "finished": "2026-07-05T18:22:00Z",
        "preflight": {"checks": [{"kind": "login_helper_loads", "ok": True}], "instrument_ok": True},
        "gates": [
            {
                "gate_id": "gate-phase6-sweep",
                "exit_code": 0,
                "assertions": [
                    {
                        "id": "GATE-6-SWEEP",
                        "status": "pass",
                        "evidence_ref": "shots-gate-phase6/attorney-accounts.png",
                    }
                ],
            }
        ],
        "sweep": {"surfaces_checked": 12, "leaks": []},
        "poller_outcomes": [],
        "evidence_index_ref": "qa/gates/evidence-2026-07-05/EVIDENCE.yaml",
        "verdict": "pass",
    }
    parsed = ResultsEnvelope.model_validate(envelope)
    assert parsed.verdict == "pass"
    assert parsed.gates[0].exit_code == 0


def test_results_envelope_rejects_unknown_verdict() -> None:
    from pydantic import ValidationError

    from guardkit.qa.formats import ResultsEnvelope

    with pytest.raises(ValidationError, match="verdict"):
        ResultsEnvelope.model_validate(
            {
                "format_version": "1.0",
                "run_id": "r",
                "feature_id": "f",
                "target_env": "e",
                "started": "t",
                "finished": "t",
                "preflight": {"checks": [], "instrument_ok": True},
                # "maybe" is not a verdict — instrument_fail/environment_fail
                # are the only non-binary options (ST-11), never a hedge.
                "verdict": "maybe",
            }
        )
