"""S3 gate — F14 emission for the R-b code-review seat (2026-07-13).

Spec of record: ``ai-transition/docs/factory-code-quality-seat-options-2026-07.md``
R-b build-lane stage **S-3**. Layers exercised:

1. The flag (``is_review_seat_enabled``) — default OFF, env/config precedence,
   mirroring ``enforcement.is_tier1_enforced``.
2. The advisory entrypoint as a PROVABLE NO-OP when the flag is OFF: neither the
   seat nor the running-probe is ever invoked.
3. Schema-valid F14 emission on a fixture diff with a STUBBED seat.
4. The F14 honesty rules (rule 2): a reading-only seat never earns ``confirmed``;
   critical/high with <2 refuters is downgraded, never fabricated.
5. The single-slot guard (never collide with a live drive).
6. Advisory never-raises: a seat outage / parse failure is a named outcome error.
7. ONE real-seat integration smoke (seat-law-checked, auto-skips if the seat is
   busy or unreachable).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from guardkit.qa.diff_ingest import ReviewPayload, parse_unified_diff
from guardkit.qa.formats import validate_instance
from guardkit.qa.formats.review_findings import ReviewFindings
from guardkit.qa.review_seat import (
    ALLOWED_SEATS,
    DEFAULT_BASE_URL,
    DEFAULT_SEAT,
    REVIEW_SEAT_ENV,
    ReviewOutcome,
    ReviewSeatError,
    _await_free_slot,
    _default_running_probe,
    build_seat_messages,
    check_single_slot,
    emit_review_findings,
    is_review_seat_enabled,
    render_payload_for_seat,
    run_advisory_review,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_DIFF = """\
diff --git a/pkg/calc.py b/pkg/calc.py
index 1111111..2222222 100644
--- a/pkg/calc.py
+++ b/pkg/calc.py
@@ -1,4 +1,6 @@
 def average(xs):
-    return sum(xs) / len(xs)
+    total = 0
+    for x in xs:
+        total += x
+    return total / len(xs)
"""


@pytest.fixture(autouse=True)
def _clear_flag_env(monkeypatch: pytest.MonkeyPatch):
    """Every test starts with the flag env unset — the flag defaults OFF."""
    monkeypatch.delenv(REVIEW_SEAT_ENV, raising=False)


@pytest.fixture
def payload() -> ReviewPayload:
    return ReviewPayload(
        subject_kind="commit",
        ref="abc1234",
        context_lines=3,
        files=parse_unified_diff(SAMPLE_DIFF),
    )


def _config(repo_root: Path, review_seat: bool) -> None:
    cfg = repo_root / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(
        f"qa:\n  review_seat: {'true' if review_seat else 'false'}\n",
        encoding="utf-8",
    )


def _seat_json(findings: list) -> str:
    return json.dumps({"summary": "changes average() to a loop", "findings": findings})


class _SpySeat:
    def __init__(self, output: str):
        self.output = output
        self.calls = 0

    def __call__(self, system: str, user: str, model: str) -> str:
        self.calls += 1
        self.last = (system, user, model)
        return self.output


class _SpyProbe:
    def __init__(self, running=None):
        self.running = running or []
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.running


# ===========================================================================
# 1. The flag (mirrors qa.enforce_tier1)
# ===========================================================================


class TestFlag:
    def test_default_off_no_config(self, tmp_path: Path):
        assert is_review_seat_enabled(tmp_path) is False

    def test_config_on(self, tmp_path: Path):
        _config(tmp_path, review_seat=True)
        assert is_review_seat_enabled(tmp_path) is True

    def test_config_off(self, tmp_path: Path):
        _config(tmp_path, review_seat=False)
        assert is_review_seat_enabled(tmp_path) is False

    def test_env_truthy_wins_over_config_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        _config(tmp_path, review_seat=False)
        monkeypatch.setenv(REVIEW_SEAT_ENV, "1")
        assert is_review_seat_enabled(tmp_path) is True

    def test_env_falsy_wins_over_config_on(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        _config(tmp_path, review_seat=True)
        monkeypatch.setenv(REVIEW_SEAT_ENV, "off")
        assert is_review_seat_enabled(tmp_path) is False

    def test_env_garbage_is_off(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        _config(tmp_path, review_seat=True)
        monkeypatch.setenv(REVIEW_SEAT_ENV, "maybe")
        assert is_review_seat_enabled(tmp_path) is False


# ===========================================================================
# 2. Flag OFF = provable no-op (no seat, no probe, no record)
# ===========================================================================


class TestFlagOffNoOp:
    def test_off_never_calls_seat_or_probe(self, tmp_path: Path, payload):
        # No config at all -> flag OFF.
        seat = _SpySeat(_seat_json([]))
        probe = _SpyProbe()
        outcome = run_advisory_review(
            tmp_path, payload, seat_call=seat, running_probe=probe
        )
        assert outcome.enabled is False
        assert outcome.record is None
        assert outcome.emitted is False
        assert outcome.blocking is False
        # The load-bearing assertion: nothing fired.
        assert seat.calls == 0
        assert probe.calls == 0

    def test_off_writes_no_record(self, tmp_path: Path, payload):
        seat = _SpySeat(_seat_json([]))
        run_advisory_review(
            tmp_path, payload, seat_call=seat, running_probe=_SpyProbe(), write=True
        )
        assert not (tmp_path / "qa").exists()


# ===========================================================================
# 3. Schema-valid emission on a fixture diff (stubbed seat)
# ===========================================================================


class TestSchemaValidEmission:
    def test_clean_change_emits_empty_valid_record(self, payload):
        record = emit_review_findings(payload, _seat_json([]))
        assert isinstance(record, ReviewFindings)
        assert record.stats.findings_total == 0
        # Re-validate through the pinned F14 loader (round-trip proof).
        ReviewFindings.model_validate(record.model_dump())

    def test_findings_emit_schema_valid(self, payload):
        out = _seat_json(
            [
                {
                    "id": "F1",
                    "dimension": "correctness",
                    "severity": "medium",
                    "file": "pkg/calc.py",
                    "line": 6,
                    "summary": "average() raises ZeroDivisionError on empty input",
                    "failing_scenario": "average([]) -> ZeroDivisionError",
                    "executed_reproduction": None,
                    "refuters": [],
                }
            ]
        )
        record = emit_review_findings(payload, out)
        assert record.stats.findings_total == 1
        f = record.findings[0]
        assert f.dimension == "correctness"
        assert f.status == "refuted"
        assert "pkg/calc.py:6" in f.summary
        ReviewFindings.model_validate(record.model_dump())

    def test_subject_maps_from_payload(self, payload):
        record = emit_review_findings(payload, _seat_json([]))
        assert record.subject.kind == "commit"
        assert record.subject.ref == "abc1234"
        assert list(record.dimensions) == [
            "correctness",
            "simplification",
            "efficiency",
            "test_coverage",
        ]

    def test_run_advisory_emits_and_writes(self, tmp_path: Path, payload):
        _config(tmp_path, review_seat=True)
        seat = _SpySeat(
            _seat_json(
                [
                    {
                        "id": "F1",
                        "dimension": "efficiency",
                        "severity": "low",
                        "file": "pkg/calc.py",
                        "line": 3,
                        "summary": "manual sum loop replaces builtin sum()",
                        "failing_scenario": "large xs -> slower than sum()",
                        "refuters": [],
                    }
                ]
            )
        )
        outcome = run_advisory_review(
            tmp_path,
            payload,
            seat_call=seat,
            running_probe=_SpyProbe(),
            write=True,
        )
        assert outcome.enabled is True
        assert outcome.emitted is True
        assert outcome.error is None
        assert outcome.blocking is False
        assert seat.calls == 1
        # The written instance re-validates through the canonical F14 loader.
        assert outcome.emitted_path is not None
        validate_instance("review-findings", Path(outcome.emitted_path))


# ===========================================================================
# 4. F14 honesty rules (rule 2)
# ===========================================================================


class TestHonestyRules:
    def test_claimed_confirmation_is_not_trusted(self, payload):
        # Seat claims confirmed + a reproduction it could not have run.
        out = _seat_json(
            [
                {
                    "id": "F1",
                    "dimension": "correctness",
                    "severity": "medium",
                    "file": "pkg/calc.py",
                    "line": 6,
                    "summary": "empty-list crash",
                    "failing_scenario": "average([]) -> crash",
                    "verdict": "confirmed",
                    "executed_reproduction": "ran pytest, saw ZeroDivisionError",
                    "refuters": [],
                }
            ]
        )
        record = emit_review_findings(payload, out, trust_seat_reproduction=False)
        f = record.findings[0]
        assert f.status == "refuted"  # reading is not a verdict
        assert f.executed_reproduction is None  # stripped, not trusted
        assert record.stats.confirmed == 0
        ReviewFindings.model_validate(record.model_dump())

    def test_trusted_reproduction_can_confirm(self, payload):
        out = _seat_json(
            [
                {
                    "id": "F1",
                    "dimension": "correctness",
                    "severity": "medium",
                    "file": "pkg/calc.py",
                    "line": 6,
                    "summary": "empty-list crash",
                    "failing_scenario": "average([]) -> crash",
                    "executed_reproduction": "python -c 'average([])' -> ZeroDivisionError",
                    "refuters": [],
                }
            ]
        )
        record = emit_review_findings(payload, out, trust_seat_reproduction=True)
        f = record.findings[0]
        assert f.status == "confirmed"
        assert f.executed_reproduction  # required for confirmed — schema enforces
        assert record.stats.confirmed == 1
        ReviewFindings.model_validate(record.model_dump())

    def test_high_severity_without_two_refuters_is_downgraded(self, payload):
        out = _seat_json(
            [
                {
                    "id": "F1",
                    "dimension": "correctness",
                    "severity": "high",
                    "file": "pkg/calc.py",
                    "line": 6,
                    "summary": "crash on empty input",
                    "failing_scenario": "average([]) -> crash",
                    "refuters": [{"who": "r1", "verdict": "refuted", "note": "only one"}],
                }
            ]
        )
        record = emit_review_findings(payload, out)
        f = record.findings[0]
        assert f.severity == "medium"  # downgraded, not fabricated up
        assert "downgraded" in f.summary.lower()
        ReviewFindings.model_validate(record.model_dump())

    def test_critical_with_two_refuters_survives(self, payload):
        out = _seat_json(
            [
                {
                    "id": "F1",
                    "dimension": "correctness",
                    "severity": "critical",
                    "file": "pkg/calc.py",
                    "line": 6,
                    "summary": "crash on empty input",
                    "failing_scenario": "average([]) -> crash",
                    "refuters": [
                        {"who": "r1", "verdict": "refuted", "note": "callers guard? no"},
                        {"who": "r2", "verdict": "refuted", "note": "type hint? none"},
                    ],
                }
            ]
        )
        record = emit_review_findings(payload, out)
        f = record.findings[0]
        assert f.severity == "critical"
        assert len(f.refuters) == 2
        assert record.stats.refutations_attempted == 2
        ReviewFindings.model_validate(record.model_dump())

    def test_finding_without_anchor_is_dropped(self, payload):
        out = _seat_json(
            [
                {"id": "F1", "dimension": "correctness", "severity": "low",
                 "summary": "something vague", "refuters": []},
                {"id": "F2", "dimension": "correctness", "severity": "low",
                 "file": "pkg/calc.py", "line": 6, "summary": "real anchored one",
                 "refuters": []},
            ]
        )
        record = emit_review_findings(payload, out)
        assert record.stats.findings_total == 1
        assert record.findings[0].id == "F2"


# ===========================================================================
# 5. Parser tolerance + dimension normalisation
# ===========================================================================


class TestParsing:
    def test_strips_think_block_and_fences(self, payload):
        raw = (
            "<think>let me look at the diff...</think>\n"
            "```json\n" + _seat_json([]) + "\n```\n"
        )
        record = emit_review_findings(payload, raw)
        assert record.stats.findings_total == 0

    def test_extracts_object_amid_prose(self, payload):
        raw = "Here is my review:\n" + _seat_json([]) + "\nThanks!"
        record = emit_review_findings(payload, raw)
        assert isinstance(record, ReviewFindings)

    def test_no_json_raises_review_seat_error(self, payload):
        with pytest.raises(ReviewSeatError):
            emit_review_findings(payload, "I could not review this.")

    def test_dimension_aliases_normalise(self, payload):
        out = _seat_json(
            [
                {"id": "F1", "dimension": "test-coverage", "severity": "low",
                 "file": "pkg/calc.py", "line": 6, "summary": "no test for []",
                 "refuters": []},
                {"id": "F2", "dimension": "performance", "severity": "low",
                 "file": "pkg/calc.py", "line": 3, "summary": "slow loop",
                 "refuters": []},
            ]
        )
        record = emit_review_findings(payload, out)
        dims = {f.dimension for f in record.findings}
        assert dims == {"test_coverage", "efficiency"}


# ===========================================================================
# 6. Single-slot guard
# ===========================================================================


class TestSingleSlot:
    def test_all_ready_is_free(self):
        free, _ = check_single_slot(
            [{"model": "qwen36-workhorse", "state": "ready"}]
        )
        assert free is True

    def test_processing_is_busy(self):
        free, reason = check_single_slot(
            [{"model": "qwen36-workhorse", "state": "processing"}]
        )
        assert free is False
        assert "qwen36-workhorse" in reason

    def test_unreachable_probe_is_not_busy(self):
        free, _ = check_single_slot(None)
        assert free is True

    def test_await_waits_then_proceeds(self):
        # Busy for the first two probes, then free.
        states = iter(
            [
                [{"model": "qwen36-workhorse", "state": "processing"}],
                [{"model": "qwen36-workhorse", "state": "processing"}],
                [{"model": "qwen36-workhorse", "state": "ready"}],
            ]
        )
        slept: list = []
        note = _await_free_slot(
            lambda: next(states),
            retry_max=5,
            retry_sleep_s=0.01,
            sleep=slept.append,
        )
        assert len(slept) == 2  # waited twice
        assert "free" in note.lower()

    def test_await_bounded_then_proceeds_under_contention(self):
        slept: list = []
        note = _await_free_slot(
            lambda: [{"model": "qwen36-workhorse", "state": "processing"}],
            retry_max=3,
            retry_sleep_s=0.01,
            sleep=slept.append,
        )
        assert len(slept) == 3  # exhausted the budget
        assert "proceeding" in note.lower()


# ===========================================================================
# 7. Advisory never-raises
# ===========================================================================


class TestAdvisoryNeverRaises:
    def test_seat_outage_is_named_not_raised(self, tmp_path: Path, payload):
        _config(tmp_path, review_seat=True)

        def _boom(system, user, model):
            raise ConnectionError("seat down")

        outcome = run_advisory_review(
            tmp_path, payload, seat_call=_boom, running_probe=_SpyProbe()
        )
        assert outcome.enabled is True
        assert outcome.record is None
        assert outcome.error is not None
        assert "seat call failed" in outcome.error
        assert outcome.blocking is False

    def test_unparseable_output_is_named_not_raised(self, tmp_path: Path, payload):
        _config(tmp_path, review_seat=True)
        outcome = run_advisory_review(
            tmp_path,
            payload,
            seat_call=_SpySeat("no json here at all"),
            running_probe=_SpyProbe(),
        )
        assert outcome.enabled is True
        assert outcome.record is None
        assert outcome.error is not None
        assert "could not be parsed" in outcome.error

    def test_off_policy_seat_is_refused_not_raised(self, tmp_path: Path, payload):
        _config(tmp_path, review_seat=True)
        outcome = run_advisory_review(
            tmp_path,
            payload,
            model="gpt-oss-120b",  # not in ALLOWED_SEATS
            seat_call=_SpySeat(_seat_json([])),
            running_probe=_SpyProbe(),
        )
        assert outcome.enabled is True
        assert outcome.error is not None
        assert "not an allowed local seat" in outcome.error


# ===========================================================================
# 8. Prompt assembly sanity
# ===========================================================================


class TestPrompt:
    def test_render_includes_diff_markers(self, payload):
        text = render_payload_for_seat(payload)
        assert "pkg/calc.py" in text
        assert "+    total = 0" in text
        assert "-    return sum(xs) / len(xs)" in text

    def test_messages_carry_subject_and_diff(self, payload):
        system, user = build_seat_messages(payload)
        assert "INSPECTOR" in system
        assert "JSON object" in system
        assert "kind: commit" in user
        assert "pkg/calc.py" in user


# ===========================================================================
# 9. ONE real-seat integration smoke (seat-law-checked; auto-skips)
# ===========================================================================


@pytest.mark.integration
def test_real_seat_smoke(tmp_path: Path, payload, monkeypatch: pytest.MonkeyPatch):
    """Drive the REAL local seat once, honesty-to-state.

    Seat-law-checked: probes ``/running`` first and SKIPS (never collides) if the
    seat is unreachable or a live drive holds the single slot. Asserts the
    advisory contract holds against a real model — either a schema-valid F14
    record OR a NAMED error (an unrunnable/unparseable seat is a finding, never a
    faked green). It never asserts specific findings (model output varies).
    """
    probe = _default_running_probe(DEFAULT_BASE_URL)
    running = probe()
    if running is None:
        pytest.skip("llama-swap /running unreachable — seat not available")
    free, reason = check_single_slot(running)
    if not free:
        pytest.skip(f"seat busy, refusing to collide: {reason}")

    monkeypatch.setenv(REVIEW_SEAT_ENV, "1")
    outcome = run_advisory_review(
        tmp_path, payload, model=DEFAULT_SEAT, write=True
    )

    assert outcome.enabled is True
    assert outcome.blocking is False
    if outcome.record is not None:
        # A real emission must be schema-valid through the canonical loader.
        ReviewFindings.model_validate(outcome.record.model_dump())
        assert outcome.record.stats.confirmed == 0  # reading-only seat never confirms
        if outcome.emitted_path is not None:
            validate_instance("review-findings", Path(outcome.emitted_path))
    else:
        # Honesty-to-state: no record => a named error, never a silent green.
        assert outcome.error, "no record and no error is a faked green"
