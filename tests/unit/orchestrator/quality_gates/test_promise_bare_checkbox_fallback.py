"""Unit tests for the *bare checkbox* promise-key fallback in
``CoachValidator._match_by_promises`` (close-the-loop lane, 2026-08-14).

Round-3 work-leg evidence (18 trials,
``/home/richardwoollcott/experiments/work-leg-quality-r3/receipts``) showed
9 legs failing with a working-tree edit that satisfied the fix predicate and
zero commits. The mechanism was a four-character string-matching miss:

* the canonical criterion reads ``"- [ ] AC-ANTISTUB-1: ..."`` and strips
  cleanly to the ID ``AC-ANTISTUB-1``;
* the Player's ``completion_promises`` entry keys on the *index* ID
  (``criterion_id="AC-005"``) and carries the label in ``criterion_text``,
  but **half-stripped** — the ``- `` bullet is gone and the ``[ ] ``
  checkbox marker survives (``"[ ] AC-ANTISTUB-1: ..."``);
* ``_strip_criterion_prefix`` only knows the full ``"- [ ] "`` form, so the
  bare marker survives, ``_extract_ac_id`` (anchored on ``^``) returns
  ``None``, no fallback key is built, and the criterion resolves to *no
  promise* — a false ``rejected`` with evidence "No completion promise".

The cure adds ``_strip_bare_checkbox_marker`` at the promise-lookup site
only. ``_strip_criterion_prefix`` and ``_extract_ac_id`` are deliberately
byte-identical (see :class:`TestSharedHelpersUntouched`), which is what
makes the routine build path's differential provable rather than argued.

Coverage:
- AC-BCB-01: r3 reproducer, verbatim strings — 6/6 met, all_criteria_met.
- AC-BCB-02: ``[x] `` / ``[X] `` forms recover identically.
- AC-BCB-03: pre-fix sentinel — the *shared* helpers still do not strip it.
- AC-BCB-04: anti-weakening — non-complete promise statuses still reject.
- AC-BCB-05: bounds — no AC ID, no marker, and no-space marker are no-ops.
- AC-BCB-06: shadowing — an explicit ``criterion_id`` still wins.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import CoachValidator


# --------------------------------------------------------------------------
# Verbatim r3 receipt strings
# (r3-A-TASK-TMGT-002-…-rep1/autobuild/player_turn_1.json — the failing turn)
# --------------------------------------------------------------------------

ANTISTUB_1_TEXT = (
    "AC-ANTISTUB-1: All primary deliverable functions contain meaningful "
    "implementation logic (no stubs, pass-only bodies, or TODOs)"
)
ANTISTUB_2_TEXT = (
    "AC-ANTISTUB-2: At least one test exercises a primary function "
    "end-to-end without mocking its core logic"
)

R3_ACCEPTANCE_CRITERIA = [
    "- [ ] Implementation complete",
    "- [ ] Tests passing",
    "- [ ] Code reviewed",
    "- [ ] Documentation updated",
    f"- [ ] {ANTISTUB_1_TEXT}",
    f"- [ ] {ANTISTUB_2_TEXT}",
]

R3_COMPLETION_PROMISES = [
    {
        "criterion_id": "AC-001",
        "criterion_text": "[ ] Implementation complete",
        "status": "complete",
        "evidence": "Modified src/routes/time.ts line 49 to add the Allow header.",
    },
    {
        "criterion_id": "AC-002",
        "criterion_text": "[ ] Tests passing",
        "status": "complete",
        "evidence": "All 13 tests pass across 2 test files.",
    },
    {
        "criterion_id": "AC-003",
        "criterion_text": "[ ] Code reviewed",
        "status": "complete",
        "evidence": "The change is a single-line addition plus a message field.",
    },
    {
        "criterion_id": "AC-004",
        "criterion_text": "[ ] Documentation updated",
        "status": "complete",
        "evidence": "The existing JSDoc comment already states the behaviour.",
    },
    {
        "criterion_id": "AC-005",
        "criterion_text": f"[ ] {ANTISTUB_1_TEXT}",
        "status": "complete",
        "evidence": "The DELETE handler returns a proper 405 response.",
    },
    {
        "criterion_id": "AC-006",
        "criterion_text": f"[ ] {ANTISTUB_2_TEXT}",
        "status": "complete",
        "evidence": "Tests use app.inject() to make real HTTP requests.",
    },
]


@pytest.fixture
def validator(tmp_path) -> CoachValidator:
    """A CoachValidator pointed at a throwaway worktree.

    ``_match_by_promises`` is pure (no IO, no broker), so the worktree never
    has to exist on disk — ``tmp_path`` just keeps the constructor happy.
    """
    return CoachValidator(worktree_path=str(tmp_path))


# ============================================================================
# AC-BCB-01 — the r3 reproducer, verbatim
# ============================================================================


class TestR3Reproducer:
    """The exact shape that blocked 9 of 18 round-3 work legs."""

    def test_bare_checkbox_promise_text_matches_labelled_criterion(
        self, validator: CoachValidator
    ):
        result = validator._match_by_promises(
            R3_ACCEPTANCE_CRITERIA, R3_COMPLETION_PROMISES
        )

        assert result.criteria_total == 6
        assert result.criteria_met == 6
        assert result.all_criteria_met is True
        assert result.missing == []

        by_id = {c.criterion_id: c for c in result.criteria_results}
        assert by_id["AC-ANTISTUB-1"].result == "verified"
        assert by_id["AC-ANTISTUB-2"].result == "verified"
        # The evidence travelled from the promise, not a synthetic default.
        assert "405" in by_id["AC-ANTISTUB-1"].evidence

    def test_pre_cure_shape_had_no_promise_at_all(
        self, validator: CoachValidator
    ):
        """Documents what the miss looked like: 4/6, both ANTISTUB missing.

        Reproduced by taking the same promise set and blanking the
        ``criterion_text`` fields the cure depends on — i.e. the state the
        fallback cannot rescue. This pins *why* the receipts read
        ``2/6 acceptance criteria`` unmet.
        """
        promises = [
            {**p, "criterion_text": None} for p in R3_COMPLETION_PROMISES
        ]

        result = validator._match_by_promises(
            R3_ACCEPTANCE_CRITERIA, promises
        )

        assert result.criteria_met == 4
        assert result.all_criteria_met is False
        by_id = {c.criterion_id: c for c in result.criteria_results}
        assert by_id["AC-ANTISTUB-1"].result == "rejected"
        assert "No completion promise" in by_id["AC-ANTISTUB-1"].evidence


# ============================================================================
# AC-BCB-02 — the checked forms
# ============================================================================


class TestCheckedMarkerForms:
    @pytest.mark.parametrize("marker", ["[ ] ", "[x] ", "[X] ", "[ ]   "])
    def test_all_checkbox_markers_recover_the_id(
        self, validator: CoachValidator, marker: str
    ):
        criteria = [f"- [ ] {ANTISTUB_1_TEXT}"]
        promises = [
            {
                "criterion_id": "AC-005",
                "criterion_text": f"{marker}{ANTISTUB_1_TEXT}",
                "status": "complete",
                "evidence": "real implementation present",
            }
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 1
        assert result.all_criteria_met is True
        assert result.criteria_results[0].criterion_id == "AC-ANTISTUB-1"

    def test_bold_collapse_and_checkbox_strip_compose(
        self, validator: CoachValidator
    ):
        """FEAT-FD32's ``**`` collapse and the new marker strip stack."""
        criteria = ["**AC-SEED-01** — seed script runs"]
        promises = [
            {
                "criterion_id": "AC-001",
                "criterion_text": "[ ] AC-SEED-01** — seed script runs",
                "status": "complete",
                "evidence": "seed ran",
            }
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 1
        assert result.criteria_results[0].criterion_id == "AC-SEED-01"


# ============================================================================
# AC-BCB-03 — the shared helpers were NOT touched (byte-preservation sentinel)
# ============================================================================


class TestSharedHelpersUntouched:
    """If these go red, the cure leaked into the product-wide match path.

    ``_strip_criterion_prefix`` runs on *every* acceptance criterion in the
    product, canonical side included. Keeping it byte-identical is the whole
    basis of the routine-path differential, so its pre-cure behaviour on a
    bare checkbox is pinned here as a sentinel.
    """

    def test_strip_criterion_prefix_still_ignores_bare_checkbox(self):
        assert (
            CoachValidator._strip_criterion_prefix("[ ] AC-ANTISTUB-1: x")
            == "[ ] AC-ANTISTUB-1: x"
        )
        assert (
            CoachValidator._strip_criterion_prefix("[x] AC-ANTISTUB-2: y")
            == "[x] AC-ANTISTUB-2: y"
        )

    def test_extract_ac_id_still_returns_none_for_bare_checkbox(self):
        assert (
            CoachValidator._extract_ac_id("[ ] AC-ANTISTUB-1: x")[1] is None
        )

    def test_strip_criterion_prefix_full_checkbox_unchanged(self):
        assert (
            CoachValidator._strip_criterion_prefix("- [ ] AC-1: z")
            == "AC-1: z"
        )


# ============================================================================
# The new helper's own contract
# ============================================================================


class TestStripBareCheckboxMarker:
    def test_marker_removed_and_text_left_flush(self):
        """No leading whitespace survives — the ID must sit at position 0."""
        out = CoachValidator._strip_bare_checkbox_marker("[ ] AC-1: x")
        assert out == "AC-1: x"
        assert not out.startswith(" ")

    def test_leading_whitespace_before_the_marker_is_tolerated(self):
        """The marker is recognised even when the text is not pre-stripped.

        Callers currently hand this helper text that
        ``_strip_criterion_prefix`` already stripped, so this is a contract
        guarantee rather than a live path — but it is the guarantee that
        makes the leading-whitespace handling load-bearing.
        """
        assert (
            CoachValidator._strip_bare_checkbox_marker("   [ ] AC-1: x")
            == "AC-1: x"
        )

    def test_only_one_marker_removed(self):
        assert (
            CoachValidator._strip_bare_checkbox_marker("[ ] [ ] AC-1: x")
            == "[ ] AC-1: x"
        )

    def test_marker_without_trailing_space_is_not_a_checkbox(self):
        """Strictness bound: only a real ``[ ] `` marker is consumed.

        Widening this is a deliberate decision, not a regression fix.
        """
        assert (
            CoachValidator._strip_bare_checkbox_marker("[ ]AC-1: x")
            == "[ ]AC-1: x"
        )

    def test_no_marker_is_a_no_op(self):
        assert (
            CoachValidator._strip_bare_checkbox_marker("AC-1: x") == "AC-1: x"
        )
        assert CoachValidator._strip_bare_checkbox_marker("") == ""


# ============================================================================
# AC-BCB-04 — anti-weakening: the cure adjudicates, it does not approve
# ============================================================================


class TestDoesNotWeakenRejection:
    @pytest.mark.parametrize(
        "status", ["incomplete", "blocked", "failed", "not_started"]
    )
    def test_non_complete_promise_still_rejects(
        self, validator: CoachValidator, status: str
    ):
        criteria = [f"- [ ] {ANTISTUB_1_TEXT}"]
        promises = [
            {
                "criterion_id": "AC-005",
                "criterion_text": f"[ ] {ANTISTUB_1_TEXT}",
                "status": status,
                "evidence": "not done",
            }
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 0
        assert result.all_criteria_met is False
        assert result.criteria_results[0].result == "rejected"
        # Now rejected for the *honest* reason: the promise says it isn't done.
        assert result.criteria_results[0].evidence == f"Promise status: {status}"

    def test_partial_promise_keeps_its_partial_confidence_marker(
        self, validator: CoachValidator
    ):
        criteria = [f"- [ ] {ANTISTUB_1_TEXT}"]
        promises = [
            {
                "criterion_id": "AC-005",
                "criterion_text": f"[ ] {ANTISTUB_1_TEXT}",
                "status": "partial",
                "evidence": "half there",
                "evidence_type": "manual",
            }
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 1
        assert "Partial confidence" in result.criteria_results[0].evidence


# ============================================================================
# AC-BCB-05 — bounds: no spurious keys
# ============================================================================


class TestNoSpuriousKeys:
    def test_checkbox_text_without_ac_id_adds_no_key(
        self, validator: CoachValidator
    ):
        """``"[ ] plain prose"`` must not raise and must not invent a key."""
        criteria = ["- [ ] AC-REAL-1: something real"]
        promises = [
            {
                "criterion_id": "AC-001",
                "criterion_text": "[ ] plain prose with no identifier",
                "status": "complete",
            }
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 0
        assert result.criteria_results[0].result == "rejected"
        assert "No completion promise" in result.criteria_results[0].evidence

    def test_missing_and_empty_criterion_text_do_not_raise(
        self, validator: CoachValidator
    ):
        criteria = ["- [ ] AC-REAL-1: something real"]
        promises = [
            {"criterion_id": "AC-001", "status": "complete"},
            {"criterion_id": "AC-002", "criterion_text": "", "status": "complete"},
            {"criterion_id": "AC-003", "criterion_text": None, "status": "complete"},
            {"criterion_id": "AC-004", "criterion_text": "[ ] ", "status": "complete"},
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_total == 1
        assert result.criteria_met == 0


# ============================================================================
# AC-BCB-06 — shadowing bound: the explicit criterion_id wins
# ============================================================================


class TestExplicitCriterionIdWins:
    def test_fallback_key_never_overwrites_an_explicit_promise(
        self, validator: CoachValidator
    ):
        """A bare-checkbox fallback must not displace a real keyed promise.

        Promise 1 explicitly owns ``AC-ANTISTUB-1`` and says ``complete``.
        Promise 2's checkbox text extracts the same ID but says
        ``incomplete``. Without the ``text_id not in promise_map`` guard the
        second would overwrite the first and the criterion would flip to
        rejected.
        """
        criteria = [f"- [ ] {ANTISTUB_1_TEXT}"]
        promises = [
            {
                "criterion_id": "AC-ANTISTUB-1",
                "criterion_text": "AC-ANTISTUB-1: the real one",
                "status": "complete",
                "evidence": "explicit promise",
            },
            {
                "criterion_id": "AC-009",
                "criterion_text": f"[ ] {ANTISTUB_1_TEXT}",
                "status": "incomplete",
                "evidence": "shadow promise",
            },
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 1
        assert result.criteria_results[0].result == "verified"
        assert result.criteria_results[0].evidence == "explicit promise"
