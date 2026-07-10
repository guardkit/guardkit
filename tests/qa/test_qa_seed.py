"""PB-6 · the additive qa-seed harvest phase (``guardkit/templates/qa_seed.py``).

Acceptance surface: the committed fixture repo ``tests/fixtures/qa_seed_source``
(N passing tests, ≥1 deliberately-triaged red, ≥1 real mock identity, ≥2
``layer_mappings``). Scope of record:
``ai-transition/docs/pb6-harvest-verification-seeds-scope-2026-07-09.md`` §7.

Covered acceptance criteria (AC1–AC8) are annotated per test.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import List, Tuple

from guardkit.qa.formats import validate_instance
from guardkit.qa.formats.known_failures import KnownFailureLedger
from guardkit.templates import qa_seed as q

FIXTURE = Path(__file__).parent.parent / "fixtures" / "qa_seed_source"
_TODAY = date(2026, 7, 10)


def _layer_keys() -> List[str]:
    data = json.loads((FIXTURE / "settings.json").read_text())
    return list(data["layer_mappings"].keys())


def _fixture_mock_strings() -> List[str]:
    # The identity strings planted in tests/fixture_mocks.py.
    return ["Mockingbird McTest", "mock.user@example.com"]


def _green_runner(passed: int) -> q.SuiteRunner:
    def run(argv: List[str], cwd: Path) -> Tuple[int, str]:
        return 0, f"{passed} passed in 0.01s\n"

    return run


def _red_runner(passed: int, failed_ids: List[str]) -> q.SuiteRunner:
    def run(argv: List[str], cwd: Path) -> Tuple[int, str]:
        lines = [f"{len(failed_ids)} failed, {passed} passed in 0.02s"]
        lines += [f"FAILED {fid} - boom" for fid in failed_ids]
        return 1, "\n".join(lines) + "\n"

    return run


# ---------------------------------------------------------------------------
# Renderers validate against the real (unmodified) schemas.
# ---------------------------------------------------------------------------


def test_all_renderers_validate(tmp_path: Path) -> None:
    (tmp_path / "e1.yaml").write_text(
        q.render_known_failures_instance(
            suite_id="s", framework="pytest", language="python", passed=42, entries=[]
        )
    )
    validate_instance("known-failures", tmp_path / "e1.yaml")

    entry = q.ObservedFailureEntry(
        test_id="t::x", reason="r", since_date="2026-07-10", since_sha="abcd1234",
        owner="o", review_by="2026-10-08",
    )
    (tmp_path / "e1r.yaml").write_text(
        q.render_known_failures_instance(
            suite_id="s", framework="pytest", language="python", passed=40, entries=[entry]
        )
    )
    validate_instance("known-failures", tmp_path / "e1r.yaml")

    mocks = q.MockIdentities(identity_strings=["Mock User"], url_patterns=["example.com"])
    (tmp_path / "e3.yaml").write_text(q.render_leak_sweep_instance(mocks))
    validate_instance("leak-sweep", tmp_path / "e3.yaml")

    (tmp_path / "e4.yaml").write_text(q.render_discovery_gate_stub("repository"))
    validate_instance("discovery-gates", tmp_path / "e4.yaml")

    (tmp_path / "e2k.yaml").write_text(
        q.render_known_failures_stub(framework="jest", language="typescript")
    )
    validate_instance("known-failures", tmp_path / "e2k.yaml")

    (tmp_path / "e2l.yaml").write_text(q.render_leak_sweep_stub())
    validate_instance("leak-sweep", tmp_path / "e2l.yaml")


# ---------------------------------------------------------------------------
# Suite observation (E1 input) — absence-of-failure safe.
# ---------------------------------------------------------------------------


def test_observe_parses_passed_and_failed() -> None:
    obs = q.observe_suite(
        Path("."), "pytest", runner=_red_runner(5, ["tests/t.py::a", "tests/t.py::b"])
    )
    assert obs.ran is True
    assert obs.passed == 5
    assert obs.failed == 2
    assert obs.failure_ids == ["tests/t.py::a", "tests/t.py::b"]


def test_observe_unsupported_framework_is_absent_not_green() -> None:
    obs = q.observe_suite(Path("."), "dotnet_test", runner=_green_runner(10))
    assert obs.ran is False
    assert "not supported" in obs.detail
    # Absence-of-failure: an unrun suite is NEVER a fabricated green baseline.
    assert obs.passed == 0


def test_observe_unparseable_output_is_absent() -> None:
    def noise(argv: List[str], cwd: Path) -> Tuple[int, str]:
        return 0, "collected nothing meaningful\n"

    obs = q.observe_suite(Path("."), "pytest", runner=noise)
    assert obs.ran is False


def test_observe_real_pytest_on_fixture() -> None:
    """The committed fixture: 3 passing + 1 deliberately-red, via a real subprocess."""
    obs = q.observe_suite(FIXTURE, "pytest")
    assert obs.ran is True
    assert obs.passed == 3
    assert obs.failed == 1
    assert obs.failure_ids == ["tests/check_red.py::check_known_red"]


# ---------------------------------------------------------------------------
# Mock-identity detection (E3 input).
# ---------------------------------------------------------------------------


def test_detect_mock_identities_from_fixture() -> None:
    mocks = q.detect_mock_identities(FIXTURE)
    assert "Mockingbird McTest" in mocks.identity_strings
    assert "mock.user@example.com" in mocks.identity_strings
    assert any("test.example.com" in u for u in mocks.url_patterns)
    assert not mocks.is_empty()


def test_detect_is_conservative_on_production_code(tmp_path: Path) -> None:
    # A production module with ordinary string literals is NOT swept.
    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text('GREETING = "hello world"\nTITLE = "Report"\n')
    mocks = q.detect_mock_identities(tmp_path)
    assert mocks.is_empty()


# ---------------------------------------------------------------------------
# write_if_absent — the K5 per-file-if-absent contract.
# ---------------------------------------------------------------------------


def test_write_if_absent_writes_then_skips(tmp_path: Path) -> None:
    dest = tmp_path / "qa" / "known-failures.yaml"
    assert q.write_if_absent(dest, "first\n") is True
    assert dest.read_text() == "first\n"
    assert q.write_if_absent(dest, "second\n") is False
    assert dest.read_text() == "first\n"  # never clobbered


# ---------------------------------------------------------------------------
# AC1 — F2 observed-suite baseline INSTANCE into the SOURCE repo.
# ---------------------------------------------------------------------------


def test_ac1_source_baseline_records_observed_count(tmp_path: Path) -> None:
    src = tmp_path / "srcrepo"
    src.mkdir()
    res = q.seed_qa_verification(
        src, tmp_path / "tmpl",
        language="Python", test_framework="pytest",
        layer_mapping_keys=["domain"], today=_TODAY,
        suite_runner=_green_runner(37),
    )
    assert "qa/known-failures.yaml" in res.source_seeds
    kf = src / "qa" / "known-failures.yaml"
    validate_instance("known-failures", kf)
    model = KnownFailureLedger.model_validate(
        __import__("yaml").safe_load(kf.read_text())
    )
    assert model.expected.passed == 37  # the observed count
    assert model.framework == "pytest"
    assert model.language == "python"


def test_ac1_and_ac7_reds_ledgered_with_owner_review_by(tmp_path: Path) -> None:
    """AC1 (owner+review_by populated) + AC7 (reds triaged, not 'all green').

    Uses the real fixture observation (passed=3, failed=1). The observed red is
    ledgered with owner+review_by AND surfaced as a finding (§6) — the
    FEAT-POC-006 '345 green, feature dead' class becomes a diff, not a shrug.
    """
    src = tmp_path / "srcrepo"
    src.mkdir()
    res = q.seed_qa_verification(
        src, None,
        language="python", test_framework="pytest",
        layer_mapping_keys=[], today=_TODAY,
        # Mirrors the committed fixture's observation: passed=3, 1 red.
        suite_runner=_red_runner(3, ["tests/check_red.py::check_known_red"]),
    )
    kf = src / "qa" / "known-failures.yaml"
    validate_instance("known-failures", kf)
    model = KnownFailureLedger.model_validate(__import__("yaml").safe_load(kf.read_text()))
    assert model.expected.passed == 3
    assert len(model.known_failures) == 1
    entry = model.known_failures[0]
    assert entry.owner and len(entry.owner) >= 1  # populated
    assert entry.review_by == "2026-10-08"  # today + 90d
    assert "triage" in entry.reason.lower()
    # AC7: the red is ALSO surfaced as a finding, never swallowed.
    assert any("failing test" in f for f in res.findings)


# ---------------------------------------------------------------------------
# AC2 — stack-typed qa/ STUBS into the generated TEMPLATE dir.
# ---------------------------------------------------------------------------


def test_ac2_template_stubs_validate_and_carry_no_instance_data(tmp_path: Path) -> None:
    src = tmp_path / "srcrepo"
    src.mkdir()
    # Give the source real mocks so E3's instance data exists to check against.
    (src / "tests").mkdir()
    (src / "tests" / "fixture_mocks.py").write_text('MOCK_NAME = "Secret Sam"\n')
    tmpl = tmp_path / "tmpl"
    res = q.seed_qa_verification(
        src, tmpl,
        language="csharp", test_framework="dotnet_test",  # a non-pytest stack
        layer_mapping_keys=["domain"], today=_TODAY,
        suite_runner=_green_runner(99),
    )
    assert "qa/known-failures.yaml" in res.template_stubs
    kf_stub = tmpl / "qa" / "known-failures.yaml"
    validate_instance("known-failures", kf_stub)
    validate_instance("leak-sweep", tmpl / "qa" / "leak-sweep.yaml")
    # Stack-typed: carries the harvested stack's framework/language.
    stub_model = KnownFailureLedger.model_validate(
        __import__("yaml").safe_load(kf_stub.read_text())
    )
    assert stub_model.framework == "dotnet_test"
    assert stub_model.language == "csharp"
    # K5: the template stub is a PLACEHOLDER — never the source's instance data.
    assert stub_model.expected.passed == 0
    assert "Secret Sam" not in (tmpl / "qa" / "leak-sweep.yaml").read_text()


# ---------------------------------------------------------------------------
# AC3 — F3 deny_patterns from real mock identities, NO claimed-real surface.
# ---------------------------------------------------------------------------


def test_ac3_leak_sweep_deny_seeded_surfaces_are_placeholders(tmp_path: Path) -> None:
    src = tmp_path / "srcrepo"
    src.mkdir()
    (src / "tests").mkdir()
    (src / "tests" / "fixture_mocks.py").write_text(
        'MOCK_USER_NAME = "Mockingbird McTest"\nMOCK_EMAIL = "mock.user@example.com"\n'
    )
    res = q.seed_qa_verification(
        src, None,
        language="python", test_framework="pytest",
        layer_mapping_keys=[], today=_TODAY,
        suite_runner=_green_runner(1),
    )
    assert "qa/leak-sweep.yaml" in res.source_seeds
    ls = src / "qa" / "leak-sweep.yaml"
    validate_instance("leak-sweep", ls)
    from guardkit.qa.formats.leak_sweep import LeakSweepManifest

    model = LeakSweepManifest.model_validate(__import__("yaml").safe_load(ls.read_text()))
    # deny seeded from the real mock identities.
    assert "Mockingbird McTest" in model.deny.identity_strings
    assert "mock.user@example.com" in model.deny.identity_strings
    # No real surface claimed — every surface is the TASK-0000 placeholder (§3).
    assert all(s.claimed_by == "TASK-0000" for s in model.surfaces)


def test_ac3_no_mocks_skips_with_warning(tmp_path: Path) -> None:
    src = tmp_path / "srcrepo"
    src.mkdir()
    res = q.seed_qa_verification(
        src, None,
        language="python", test_framework="pytest",
        layer_mapping_keys=[], today=_TODAY,
        suite_runner=_green_runner(1),
    )
    # No mock identities -> E3 is a warned skip, NOT a fabricated/empty deny.
    assert "qa/leak-sweep.yaml" not in res.source_seeds
    assert not (src / "qa" / "leak-sweep.yaml").exists()
    assert any("deny_patterns" in w for w in res.warnings)


# ---------------------------------------------------------------------------
# AC4 — one F12 discovery-gate STUB per layer_mapping.
# ---------------------------------------------------------------------------


def test_ac4_one_discovery_gate_per_layer_mapping(tmp_path: Path) -> None:
    src = tmp_path / "srcrepo"
    src.mkdir()
    keys = _layer_keys()  # ≥2 from the fixture settings.json
    assert len(keys) >= 2
    res = q.seed_qa_verification(
        src, None,
        language="python", test_framework="pytest",
        layer_mapping_keys=keys, today=_TODAY,
        suite_runner=_green_runner(1),
    )
    emitted = [s for s in res.source_seeds if s.startswith("qa/discovery-gates-")]
    assert len(emitted) == len(keys)  # count == number of layer_mappings
    for rel in emitted:
        validate_instance("discovery-gates", src / rel)


# ---------------------------------------------------------------------------
# AC5 — K5 no-clobber regression.
# ---------------------------------------------------------------------------


def test_ac5_k5_never_clobbers_existing_qa_file(tmp_path: Path) -> None:
    src = tmp_path / "srcrepo"
    (src / "qa").mkdir(parents=True)
    committed = src / "qa" / "known-failures.yaml"
    committed.write_text("# this repo's REAL committed ledger\n")
    (src / "tests").mkdir()
    (src / "tests" / "fixture_mocks.py").write_text('MOCK_NAME = "Real Mock"\n')
    res = q.seed_qa_verification(
        src, None,
        language="python", test_framework="pytest",
        layer_mapping_keys=["domain"], today=_TODAY,
        suite_runner=_green_runner(5),
    )
    # The pre-existing file is byte-unchanged and not reported as seeded.
    assert committed.read_text() == "# this repo's REAL committed ledger\n"
    assert "qa/known-failures.yaml" not in res.source_seeds
    # Other absent artefacts are still seeded around it.
    assert "qa/leak-sweep.yaml" in res.source_seeds


# ---------------------------------------------------------------------------
# AC6 — additivity: F1–F5 semantics untouched, K15 intact, schema unchanged.
# ---------------------------------------------------------------------------


def test_ac6_f1_f5_exemplars_still_validate() -> None:
    """The committed F1–F5 exemplars re-validate byte-identical (schema untouched)."""
    fixtures = Path(__file__).parent.parent / "fixtures" / "qa_formats"
    exemplars = [
        ("pass-bar", "lpa-platform-poc/pass-bar-FEAT-POC-DEMO-0705.yaml"),
        ("known-failures", "lpa-platform-poc/known-failures.yaml"),
        ("leak-sweep", "lpa-platform-poc/leak-sweep.yaml"),
        ("gate-registry", "lpa-platform-poc/gates-registry.yaml"),
        ("evidence-index", "lpa-platform-poc/evidence-index.yaml"),
    ]
    for kind, rel in exemplars:
        validate_instance(kind, fixtures / rel)


def test_ac6_k15_plan_time_lint_still_fires() -> None:
    """Harvest does not weaken the K15/LPA-09 plan-time reject-lint."""
    from guardkit.qa.enforcement import check_plan_does_not_author_ledger

    # A plan-session diff touching the F2 ledger is still refused.
    res = check_plan_does_not_author_ledger(["qa/known-failures.yaml"])
    assert res.status == "fail"
    # A non-ledger diff still passes.
    assert check_plan_does_not_author_ledger(["src/app.py"]).status == "pass"


def test_ac6_known_failures_schema_shape_unchanged() -> None:
    """Regression guard: the F2 root has NO owner/review_by (those are per-entry).

    Pins the schema shape the emitter respects — a future edit adding root
    owner/review_by (or removing the entry fields) would break this.
    """
    root_fields = set(KnownFailureLedger.model_fields)
    assert "owner" not in root_fields
    assert "review_by" not in root_fields
    from guardkit.qa.formats.known_failures import KnownFailureEntry

    entry_fields = set(KnownFailureEntry.model_fields)
    assert {"owner", "review_by"} <= entry_fields


# ---------------------------------------------------------------------------
# AC8 — missing template payload surfaces at WARNING (DF-011), not silent skip.
# ---------------------------------------------------------------------------


def test_ac8_missing_template_dir_warns_not_silent(tmp_path: Path) -> None:
    src = tmp_path / "srcrepo"
    src.mkdir()
    res = q.seed_qa_verification(
        src, None,  # no template dir resolved (dry-run)
        language="python", test_framework="pytest",
        layer_mapping_keys=["domain"], today=_TODAY,
        suite_runner=_green_runner(1),
    )
    assert res.template_stubs == []
    assert any("template" in w.lower() and "skipped" in w.lower() for w in res.warnings)


# ---------------------------------------------------------------------------
# End-to-end — every emitted file (source + template) validates.
# ---------------------------------------------------------------------------


def test_end_to_end_all_emitted_files_validate(tmp_path: Path) -> None:
    src = tmp_path / "srcrepo"
    src.mkdir()
    (src / "tests").mkdir()
    (src / "tests" / "fixture_mocks.py").write_text('MOCK_NAME = "Mock Person"\n')
    tmpl = tmp_path / "tmpl"
    res = q.seed_qa_verification(
        src, tmpl,
        language="python", test_framework="pytest",
        layer_mapping_keys=_layer_keys(), today=_TODAY,
        suite_runner=_red_runner(4, ["tests/check_red.py::check_known_red"]),
    )
    for rel in res.source_seeds:
        if "known-failures" in rel:
            kind = "known-failures"
        elif "leak-sweep" in rel:
            kind = "leak-sweep"
        else:
            kind = "discovery-gates"
        validate_instance(kind, src / rel)
    for rel in res.template_stubs:
        kind = "known-failures" if "known-failures" in rel else "leak-sweep"
        validate_instance(kind, tmpl / rel)
    # E1+E3+E4(×2)=4 source seeds; E2(×2)=2 template stubs.
    assert len(res.source_seeds) == 4
    assert len(res.template_stubs) == 2
