"""PERMISSIVE_DOUBLE is surfaced (advisory) instead of computed-and-dropped.

Background in plain words
-------------------------
A test "double" is a stand-in object a test uses in place of the real thing.
A *permissive* double accepts any arguments at all, so a test using one still
passes even when the real call would fail because the argument names are wrong.
That is the defect class that shipped forge's Mode P dead on arrival (see
``forge/docs/reviews/feat-spl-002-post-merge-review-2026-07-06.md``).

The analyzer in ``guardkitfactory`` has always detected these and written them
into ``analyze_wiring(...)["permissive_double"]``. Until 2026-08-21 nothing on
the guardkit side ever read that value: it was carried into the Coach's
evidence JSON as one unlabelled key among a dozen siblings, with no log line
and no explanation. These tests pin the two places it is now named.

Everything here is ADVISORY. ``TestStaysAdvisory`` exists to keep it that way:
if someone later makes a permissive double reject a turn, that test fails and
forces the decision to be deliberate.

``TestBroadIsNeverCalledSafe`` guards the OTHER way the advisory can fail — by
being present but wrong. Its first draft told the reviewing model that the
high-volume "broad" group was near-certainly not defects; on the one file this
advisory exists for, every finding was in that group.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

# NOTE ON WHERE THE `seam` MARK AND THE `importorskip` LIVE (2026-08-21).
# They are deliberately NOT at file level. Only TestFactoryStillProducesTheSignal
# needs the sibling `guardkitfactory` package; the other 13 tests here drive
# guardkit's own code with plain dictionaries and need nothing extra.
#
# A file-level `importorskip("guardkitfactory.wiring")` skipped ALL of them in
# the main test workflow (.github/workflows/tests.yml), which deliberately does
# not install guardkitfactory — and this file was not in the seam workflow's
# explicit file list either, so every test here ran in NO CI job at all. That is
# the exact trap TASK-FIX-WIREGATECI01 already caught once for
# tests/unit/orchestrator/test_wiring_gate.py ("Without this gate those 7 tests
# ran in no CI job", .github/workflows/seam-tests.yml).
#
# The split now is: 13 tests run in tests.yml, and all 15 run in seam-tests.yml
# (this file is listed there). Keep it that way — a guard test that never
# executes guards nothing.


def _write(root: Path, rel: str, content: str) -> str:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return rel


def _wiring_result_with(findings: list[dict]) -> dict:
    """A minimal analyze_wiring-shaped dict carrying the given findings."""
    return {
        "status": "complete",
        "findings": [],
        "mocked_seam": {"status": "skipped_no_acceptance_files", "findings": []},
        "ctor_arity": {"status": "skipped_no_composition_root", "findings": []},
        "callsite_drift": {"status": "skipped_no_targets", "findings": []},
        "env_tamper": {"status": "skipped_no_targets", "findings": []},
        "permissive_double": {"status": "ran", "ran": True, "findings": findings},
    }


_SHARP = {
    "file": "tests/test_svc.py",
    "lineno": 3,
    "symbol": "fake_send_invoice",
    "kind": "PERMISSIVE_DOUBLE",
    "pattern": "PERMISSIVE_DOUBLE",
    "form": "star_args_fake",
    "target_evidence": "name_matched",
    "target": "send_invoice",
    "severity": "warning",
    "why": "accepts anything — signature drift is invisible",
}

_BROAD = {
    "file": "tests/test_svc.py",
    "lineno": 9,
    "symbol": "pkg.svc.send_invoice",
    "kind": "PERMISSIVE_DOUBLE",
    "pattern": "PERMISSIVE_DOUBLE",
    "form": "unspecced_mock",
    "target_evidence": "patched",
    "severity": "warning",
    "why": "binds nothing",
}


@pytest.mark.seam
class TestFactoryStillProducesTheSignal:
    """The cross-repo contract: the key exists and carries real findings.

    The only class here that needs the sibling ``guardkitfactory`` package, so
    it is the only one carrying the ``seam`` mark and the ``importorskip``.
    """

    @pytest.fixture
    def wiring(self):
        """The real analyzer, or a clean skip where the sibling is absent."""
        return pytest.importorskip("guardkitfactory.wiring")

    def test_analyze_wiring_returns_permissive_double_key(self, wiring, tmp_path):
        svc = _write(tmp_path, "pkg/svc.py", "def send_invoice(a, b):\n    return 1\n")
        result = wiring.analyze_wiring([svc], tmp_path, "feature")
        assert result is not None
        assert "permissive_double" in result, (
            "guardkitfactory.wiring.analyze_wiring dropped the "
            "'permissive_double' key the guardkit advisory depends on"
        )

    def test_detector_fires_on_a_star_args_stand_in(self, wiring, tmp_path):
        _write(tmp_path, "pkg/__init__.py", "")
        _write(
            tmp_path,
            "pkg/svc.py",
            "def send_invoice(customer_id, amount, currency):\n    return True\n",
        )
        test_rel = _write(
            tmp_path,
            "tests/test_svc.py",
            "def fake_send_invoice(*args, **kwargs):\n"
            "    return True\n"
            "def test_it():\n"
            "    assert fake_send_invoice(1)\n",
        )
        result = wiring.analyze_wiring(["pkg/svc.py", test_rel], tmp_path, "feature")
        findings = result["permissive_double"]["findings"]
        assert any(
            f["target_evidence"] == "name_matched" and f["target"] == "send_invoice"
            for f in findings
        ), f"expected a name_matched finding for send_invoice, got {findings}"


class TestSplitByConfidence:
    """The high/low confidence split the log and the prompt both use."""

    def test_splits_sharp_from_broad(self):
        sharp, broad = FeatureOrchestrator._split_permissive_double_findings(
            _wiring_result_with([_SHARP, _BROAD])
        )
        assert [f["symbol"] for f in sharp] == ["fake_send_invoice"]
        assert [f["symbol"] for f in broad] == ["pkg.svc.send_invoice"]

    @pytest.mark.parametrize(
        "result",
        [
            None,
            {},
            {"permissive_double": None},
            {"permissive_double": {"status": "skipped_no_targets", "findings": []}},
            {"permissive_double": {"status": "ran", "findings": "not-a-list"}},
            {"permissive_double": {"status": "error", "findings": [_SHARP]}},
        ],
    )
    def test_absent_or_malformed_signal_is_empty_not_an_exception(self, result):
        assert FeatureOrchestrator._split_permissive_double_findings(result) == ([], [])


class TestOperatorLogAdvisory:
    """A person reading the run log can see the finding."""

    def test_sharp_finding_is_named_in_the_log(self, caplog):
        caplog.set_level(logging.WARNING)
        orch = FeatureOrchestrator.__new__(FeatureOrchestrator)
        orch._surface_advisory_seam_findings(
            _wiring_result_with([_SHARP, _BROAD]),
            authored=[],
            worktree=None,
            wave_number=2,
        )
        text = caplog.text
        assert "PERMISSIVE_DOUBLE" in text
        assert "fake_send_invoice" in text, (
            "the high-confidence finding must be named line by line"
        )
        assert "broad group" in text, (
            "the high-volume group must be reported as a count, not a list"
        )
        assert "Broad does NOT mean safe" in text, (
            "the log must not imply the broad group can be ignored"
        )

    def test_no_findings_logs_nothing(self, caplog):
        caplog.set_level(logging.WARNING)
        orch = FeatureOrchestrator.__new__(FeatureOrchestrator)
        orch._surface_advisory_seam_findings(
            _wiring_result_with([]), authored=[], worktree=None, wave_number=1,
        )
        assert "PERMISSIVE_DOUBLE" not in caplog.text


class TestCoachPromptAdvisory:
    """The Coach's prompt text names the signal instead of burying it."""

    def _render(self, wiring_result):
        from guardkit.orchestrator.agent_invoker import AgentInvoker
        from guardkit.orchestrator.coach_verification import HonestyVerification
        from guardkit.orchestrator.quality_gates.coach_evidence import (
            CoachEvidenceBundle,
        )

        bundle = CoachEvidenceBundle(
            honesty=HonestyVerification(
                verified=True, discrepancies=[], honesty_score=1.0
            ),
            wiring=wiring_result,
        )
        return AgentInvoker._render_evidence_bundle_section(
            AgentInvoker.__new__(AgentInvoker), bundle
        )

    def test_advisory_line_names_the_field_and_the_counts(self):
        text = self._render(_wiring_result_with([_SHARP, _BROAD, _BROAD]))
        assert "wiring.permissive_double" in text
        assert "1 sharp, 2 broad" in text
        # Collapse newlines so the wrapped sentence can be matched as one line.
        assert "never reject the turn on these counts alone." in " ".join(text.split())

    def test_no_advisory_line_when_there_are_no_findings(self):
        text = self._render(_wiring_result_with([]))
        assert "ADVISORY: wiring.permissive_double" not in text

    def test_nested_findings_are_bounded(self):
        """A test file with 80 permissive doubles must not flood the prompt."""
        many = [dict(_BROAD, lineno=i) for i in range(80)]
        text = self._render(_wiring_result_with(many))
        payload = text.split("<evidence_bundle>")[1].split("</evidence_bundle>")[0]
        nested = json.loads(payload)["wiring"]["permissive_double"]["findings"]
        assert len(nested) == 21, (
            "expected 20 findings plus one '... and N more' marker, "
            f"got {len(nested)}"
        )
        assert "and 60 more" in str(nested[-1])
        # The count in the advisory line is the TRUE total, not the truncated one.
        assert "0 sharp, 80 broad" in text


class TestBroadIsNeverCalledSafe:
    """The regression this round exists to prevent (2026-08-21).

    The first draft of the advisory told the reviewing model that low-confidence
    entries "are near-certainly not defects". Rendered against the ONE file the
    whole advisory exists for — forge's ``tests/cli/test_serve_planning_wiring.py``
    at the broken commit, which produces 24 findings, ALL broad and NONE sharp —
    that wording said, in effect, "there is nothing here to look at".

    These tests render the real prompt for that exact shape and read it back.
    """

    #: The shape the real forge file produces: 24 ordinary patch() stand-ins,
    #: no sharp entries. Verified against the 2026-08-21 estate scan.
    FORGE_MODE_P_SHAPE = [dict(_BROAD, lineno=i) for i in range(24)]

    def _render(self, wiring_result):
        return TestCoachPromptAdvisory()._render(wiring_result)

    def test_the_motivating_file_is_not_described_as_nothing_to_see(self):
        text = self._render(_wiring_result_with(self.FORGE_MODE_P_SHAPE))
        assert "0 sharp, 24 broad" in text
        flat = " ".join(text.split())
        for dismissal in (
            "near-certainly not defects",
            "not defects",
            "safe to ignore",
            "can be ignored",
        ):
            assert dismissal not in flat, (
                f"the advisory tells the reviewer {dismissal!r} on the exact "
                "shape (0 sharp / 24 broad) that motivated this whole change"
            )

    def test_the_advisory_says_the_split_is_a_volume_filter(self):
        flat = " ".join(self._render(
            _wiring_result_with(self.FORGE_MODE_P_SHAPE)).split())
        assert "VOLUME FILTER, NOT A DEFECT JUDGEMENT" in flat, (
            "the reviewer must be told what the sharp/broad split does and "
            "does not mean"
        )
        assert "a broad entry is NOT evidence that the wiring is fine" in flat

    def test_the_advisory_names_the_worst_known_case_and_why_it_was_broad(self):
        flat = " ".join(self._render(
            _wiring_result_with(self.FORGE_MODE_P_SHAPE)).split())
        assert "ALL of them broad and NONE sharp" in flat, (
            "the estate's worst known regression of this class sat entirely "
            "in the broad bucket — say so"
        )
        assert "RecordingFake" in flat, (
            "name the structural reason the sharp path missed it: the sharp "
            "path needs the stand-in's name to strip to a real symbol"
        )


class TestOneRuleOneHome:
    """The sharp/broad rule must exist once, not twice (2026-08-21).

    The run log and the reviewing model's prompt previously each carried their
    own copy. Two copies can drift, and then a person reading the log and a
    model reading the prompt disagree about the same run.
    """

    def test_log_and_prompt_agree_on_every_shape(self):
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        for findings in ([], [_SHARP], [_BROAD], [_SHARP, _BROAD, _BROAD]):
            result = _wiring_result_with(findings)
            sharp, broad = FeatureOrchestrator._split_permissive_double_findings(result)
            counts = AgentInvoker._count_permissive_doubles(result)
            assert counts == (len(sharp), len(broad)), (
                f"log and prompt disagree on {findings!r}"
            )

    def test_both_sides_call_the_single_implementation(self):
        from guardkit.orchestrator import permissive_double_advisory

        result = _wiring_result_with([_SHARP, _BROAD])
        assert (
            FeatureOrchestrator._split_permissive_double_findings(result)
            == permissive_double_advisory.split_findings(result)
        )


class TestStaysAdvisory:
    """Guard: a permissive double must not reject a turn in this change."""

    def test_permissive_double_is_never_turn_rejecting(self):
        turn_rejecting = FeatureOrchestrator._collect_turn_rejecting_wiring_findings(
            _wiring_result_with([_SHARP, _BROAD])
        )
        assert turn_rejecting == [], (
            "PERMISSIVE_DOUBLE was surfaced as ADVISORY only. Promoting it to "
            "turn-rejecting must be a deliberate, separately-reviewed decision "
            "— the estate scan of 2026-08-21 found 3,156 findings, of which "
            "only 46 were high-confidence."
        )
