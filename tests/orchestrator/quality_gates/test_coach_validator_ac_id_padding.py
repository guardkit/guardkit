"""AC-1 and AC-001 are the same criterion written two ways.

The case, in plain words. On 3 September 2026 the build ``build-FEAT-9C7B``
ran the feature task ``TASK-9C7B-002``, which has four acceptance criteria.
The Coach numbers criteria by position and zero-pads them (``AC-001`` …
``AC-004``); the Player writes whatever it writes.

- Turn 1 — the Player wrote its four promises as ``AC-001``..``AC-004``. All
  four matched: 4 of 4 criteria met. (That turn was still sent back, over a
  separate architecture finding.)
- Turn 2 — the Player fixed the architecture finding and wrote the same four
  promises again, all marked complete, this time as ``AC-1``..``AC-4``. None
  matched. The requirements slice recorded **0 of 4 criteria met**, with
  "No completion promise for AC-001" against each criterion, for work that
  was done and whose tests passed. The Coach approved the turn anyway, and it
  was right to: the independent test run passed eight tests, spec-conformance
  passed and the behavioural oracle passed. The detector was what was wrong.

``CoachValidator._normalize_numeric_ac_id`` closes that: a simple numeric AC
id matches whatever its zero-padding, in both directions, exact matches always
winning. Compound ids (``AC-LOAD-01``) are untouched.

The four files in ``tests/fixtures/coach-criteria-padding-2026-09-03/`` are
byte-for-byte copies of that build's real records (see the PROVENANCE.txt
beside them), so the headline test is graded against what actually happened.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


FIXTURE_DIR = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "coach-criteria-padding-2026-09-03"
)


def _fixture(name: str) -> Dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text())


def _validator() -> CoachValidator:
    """A validator instance without running __init__ — ``_match_by_promises``
    and its helpers are pure and touch no instance state."""
    return CoachValidator.__new__(CoachValidator)


def _criteria_texts() -> List[str]:
    """The four acceptance criteria, taken from the saved evidence record so
    the test cannot drift from what the Coach actually compared against."""
    evidence = _fixture("coach_evidence_turn_2.json")
    return [
        c["criterion_text"]
        for c in evidence["requirements"]["criteria_results"]
    ]


# ---------------------------------------------------------------------------
# the real turn
# ---------------------------------------------------------------------------


class TestRealBuildTurnTwo:
    def test_the_saved_record_shows_the_defect(self) -> None:
        """Pin what went wrong, from the receipt itself: zero of four, and the
        reason given against every criterion is a missing promise — while the
        Player's report of that same turn carries four complete promises."""
        evidence = _fixture("coach_evidence_turn_2.json")
        req = evidence["requirements"]
        assert (req["criteria_met"], req["criteria_total"]) == (0, 4)
        assert req["all_criteria_met"] is False
        assert all(
            c["result"] == "rejected"
            and c["evidence"].startswith("No completion promise")
            for c in req["criteria_results"]
        )

        promises = _fixture("player_turn_2.json")["completion_promises"]
        assert [p["criterion_id"] for p in promises] == [
            "AC-1",
            "AC-2",
            "AC-3",
            "AC-4",
        ]
        assert all(p["status"] == "complete" for p in promises)
        # and the Coach approved it anyway
        assert _fixture("coach_turn_2.json")["decision"] == "approve"

    def test_the_real_promises_now_match_all_four_criteria(self) -> None:
        """The fix, graded on the real turn: 4 of 4, each carrying the
        Player's own evidence text. Red before the change (0 of 4)."""
        validation = _validator()._match_by_promises(
            _criteria_texts(),
            _fixture("player_turn_2.json")["completion_promises"],
        )

        assert (validation.criteria_met, validation.criteria_total) == (4, 4)
        assert validation.all_criteria_met is True
        assert validation.missing == []
        assert [c.criterion_id for c in validation.criteria_results] == [
            "AC-001",
            "AC-002",
            "AC-003",
            "AC-004",
        ]
        assert all(c.result == "verified" for c in validation.criteria_results)
        assert "crud.py" in validation.criteria_results[0].evidence

    def test_turn_one_is_unchanged(self) -> None:
        """The already-padded turn scored 4 of 4 before the change and must
        still score 4 of 4 — the fix widens matching, it does not move it."""
        validation = _validator()._match_by_promises(
            _criteria_texts(),
            _fixture("player_turn_1.json")["completion_promises"],
        )
        assert (validation.criteria_met, validation.criteria_total) == (4, 4)
        assert validation.all_criteria_met is True


# ---------------------------------------------------------------------------
# the normaliser itself
# ---------------------------------------------------------------------------


class TestNumericAcIdNormaliser:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("AC-1", "AC-001"),
            ("AC-01", "AC-001"),
            ("AC-001", "AC-001"),
            ("AC-0001", "AC-001"),
            ("AC-12", "AC-012"),
            ("AC-1234", "AC-1234"),
            ("  AC-2  ", "AC-002"),
            ("ac-3", "AC-003"),
        ],
    )
    def test_simple_numeric_ids_are_padded(
        self, raw: str, expected: str
    ) -> None:
        assert CoachValidator._normalize_numeric_ac_id(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "AC-LOAD-01",
            "AC-SEED-1",
            "AC",
            "",
            "   ",
            "REQ-001",
            "AC-001a",
            "AC-",
            None,
            123,
        ],
    )
    def test_everything_else_is_left_alone(self, raw: Any) -> None:
        assert CoachValidator._normalize_numeric_ac_id(raw) is None


# ---------------------------------------------------------------------------
# matching behaviour around the widened lookup
# ---------------------------------------------------------------------------


def _promise(cid: str, status: str = "complete", **extra: Any) -> Dict[str, Any]:
    p = {
        "criterion_id": cid,
        "criterion_text": f"criterion for {cid}",
        "status": status,
        "evidence": f"evidence for {cid}",
    }
    p.update(extra)
    return p


class TestMatchingBehaviour:
    def test_padded_criterion_matches_unpadded_promise(self) -> None:
        v = _validator()
        result = v._match_by_promises(["do the thing"], [_promise("AC-1")])
        assert result.criteria_results[0].result == "verified"
        assert result.criteria_results[0].evidence == "evidence for AC-1"

    def test_unpadded_criterion_matches_padded_promise(self) -> None:
        """The other direction: the task markdown labels the criterion
        ``AC-1:`` and the Player wrote ``AC-001``."""
        v = _validator()
        result = v._match_by_promises(["AC-1: do the thing"], [_promise("AC-001")])
        assert result.criteria_results[0].criterion_id == "AC-1"
        assert result.criteria_results[0].result == "verified"

    def test_an_exact_match_always_wins_over_a_padded_alias(self) -> None:
        """Both ``AC-001`` and ``AC-1`` present: the criterion ``AC-001``
        must take the promise that actually says ``AC-001``, whatever order
        they arrive in."""
        v = _validator()
        for promises in (
            [_promise("AC-1", evidence="from the alias"),
             _promise("AC-001", evidence="from the exact id")],
            [_promise("AC-001", evidence="from the exact id"),
             _promise("AC-1", evidence="from the alias")],
        ):
            result = v._match_by_promises(["do the thing"], promises)
            assert result.criteria_results[0].evidence == "from the exact id"

    def test_an_incomplete_padded_promise_is_still_rejected(self) -> None:
        """Widening WHICH promise is found never changes WHETHER it counts:
        a promise found by padding that says ``incomplete`` still rejects."""
        v = _validator()
        result = v._match_by_promises(
            ["do the thing"], [_promise("AC-1", status="incomplete")]
        )
        assert result.criteria_results[0].result == "rejected"
        assert result.criteria_results[0].evidence.startswith("Promise status:")
        assert result.all_criteria_met is False

    def test_a_genuinely_missing_promise_is_still_rejected(self) -> None:
        """No promise for the criterion at all — the padding lookup must not
        invent one out of a different criterion's promise."""
        v = _validator()
        result = v._match_by_promises(
            ["first thing", "second thing"], [_promise("AC-1")]
        )
        assert result.criteria_results[0].result == "verified"
        assert result.criteria_results[1].result == "rejected"
        assert (
            result.criteria_results[1].evidence
            == "No completion promise for AC-002"
        )
        assert result.criteria_met == 1

    def test_compound_ids_are_untouched(self) -> None:
        """A compound label matches exactly or not at all — no padding, and
        no accidental collapse of ``AC-LOAD-01`` onto ``AC-001``."""
        v = _validator()
        result = v._match_by_promises(
            ["**AC-LOAD-01** — load the thing"], [_promise("AC-LOAD-01")]
        )
        assert result.criteria_results[0].criterion_id == "AC-LOAD-01"
        assert result.criteria_results[0].result == "verified"

        missed = v._match_by_promises(
            ["**AC-LOAD-01** — load the thing"], [_promise("AC-1")]
        )
        assert missed.criteria_results[0].result == "rejected"
