"""Golden derivation (wire-true): capability.dcl + api_test binding -> spike set.

Deriving from the spike's ``capability.dcl`` (byte-copied) + the api_test-shaped
binding MUST reproduce the spike's 13 RUN assertion ids + 1 SKIP (A-AVAIL) — the
recorded result of R1–R10 in ``api_test/qa/dcl-spike/derivation-rules.md``.
"""

from __future__ import annotations

from guardkit.qa.dcl import checker
from guardkit.qa.dcl.binding import load_binding, sha256_of
from guardkit.qa.dcl.deriver import derive, make_receipt
from guardkit.qa.formats import validate_instance

from .conftest import requires_node

EXPECTED_RUN = [
    "A-OUTCOME",
    "A-FIELD-SVC",
    "A-FIELD-REQ",
    "A-FIELD-FRA",
    "A-COUNT-MONO",
    "A-DURATION",
    "A-LIFE-SERVING",
    "A-LIFE-STABLE",
    "A-FRA-FORMAT",
    "A-CW-POST",
    "A-CW-PUT",
    "A-CW-PATCH",
    "A-CW-DELETE",
]
EXPECTED_SKIP = ["A-AVAIL"]


@requires_node
def test_golden_run_and_skip_sets(capability_dcl, binding_file) -> None:
    binding = load_binding(binding_file)
    ir_obj = checker.ir(capability_dcl)
    result = derive(ir_obj, binding, feature="stats-endpoint")

    assert set(result.run_ids) == set(EXPECTED_RUN)
    assert result.skip_ids == EXPECTED_SKIP
    # Order matches the spike's derivation table.
    assert result.run_ids == EXPECTED_RUN


@requires_node
def test_golden_rules_and_flags(capability_dcl, binding_file) -> None:
    binding = load_binding(binding_file)
    result = derive(checker.ir(capability_dcl), binding, feature="stats-endpoint")
    # R10 fired four closed-world rejections; every rule R2–R10 is represented.
    assert result.rules_fired["R10"] == 4
    assert result.rules_fired["R3"] == 3
    # All nine judgment flags appear — the honest mechanizability cost.
    assert result.judgment_flags == [f"J{i}" for i in range(1, 10)]


@requires_node
def test_r10_mutating_verbs_fixed_in_code(capability_dcl, binding_file) -> None:
    binding = load_binding(binding_file)
    result = derive(checker.ir(capability_dcl), binding, feature="stats-endpoint")
    cw = {a.id: a for a in result.assertion_set.assertions if a.rule == "R10"}
    assert set(cw) == {"A-CW-POST", "A-CW-PUT", "A-CW-PATCH", "A-CW-DELETE"}
    for a in cw.values():
        assert a.request["method"] in {"POST", "PUT", "PATCH", "DELETE"}
        assert a.request["path"] == "/stats"
        assert a.predicate == {"check": "status_in_range", "low": 400, "high": 499}


@requires_node
def test_j5_format_only_when_binding_opts_in(capability_dcl, binding_file) -> None:
    """A-FRA-FORMAT exists ONLY because the binding opts firstRequestAt in (J5)."""
    binding = load_binding(binding_file)
    # With the format opt-in removed, the format assertion must disappear.
    binding.capabilities["ReportServiceStatistics"].fields["firstRequestAt"].format = None
    result = derive(checker.ir(capability_dcl), binding, feature="stats-endpoint")
    assert "A-FRA-FORMAT" not in result.run_ids


@requires_node
def test_derived_set_writes_and_receipt_validates(
    capability_dcl, binding_file, tmp_path
) -> None:
    binding = load_binding(binding_file)
    envelope = checker.check(capability_dcl)
    result = derive(checker.ir(capability_dcl), binding, feature="stats-endpoint")

    out = tmp_path / "qa" / "dcl" / "derived" / "stats-endpoint.yaml"
    result.assertion_set.write_yaml(out)
    assert out.is_file()

    receipt = make_receipt(
        result,
        feature="stats-endpoint",
        source_dcl=str(capability_dcl),
        source_dcl_sha256=sha256_of(capability_dcl),
        binding_sha256=sha256_of(binding_file),
        checker_ok=bool(envelope.get("ok")),
        error_count=envelope.get("errorCount", 0),
        warning_count=envelope.get("warningCount", 0),
        checker_pin=checker.CHECKER_PIN,
    )
    import yaml

    receipt_path = tmp_path / "qa" / "dcl" / "derivation-stats-endpoint.yaml"
    receipt_path.write_text(
        yaml.safe_dump(receipt.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )
    # The receipt validates as its registered F-format.
    validated = validate_instance("dcl-derivation", receipt_path)
    assert validated.assertions.run == EXPECTED_RUN
    assert validated.assertions.skip == EXPECTED_SKIP
