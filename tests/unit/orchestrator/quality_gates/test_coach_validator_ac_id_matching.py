"""Unit tests for natural-label AC-ID matching in CoachValidator (TASK-GK-CV-001).

These tests reproduce the bug surfaced in FEAT-PEBR run-2 turn 1
(2026-05-07): ``_strip_criterion_prefix`` consumed the ``AC-N:`` prefix
*before* ``_extract_ac_id`` could read it, so the extractor returned
``None``, the caller fell back to a zero-padded ``AC-NNN`` lookup key,
and Player promises emitted under the natural label (``criterion_id="AC-N"``)
silently missed. Coach reported ``criteria_met=0/7`` even though the
Player had submitted seven valid promises.

After the fix (TASK-GK-CV-001), ``_strip_criterion_prefix`` no longer
touches AC labels — that is ``_extract_ac_id``'s sole responsibility.
The natural-label lookup key matches the Player's emitted ``criterion_id``
and the criterion is verified.

Coverage:

- ``AC-2`` — reproducer: natural-label ``AC-N:`` with Player
  ``criterion_id="AC-N"`` matches end-to-end.
- ``AC-3`` — zero-padded ``criterion_id="AC-001"`` paired with
  ``criterion_text`` carrying the natural label still matches via the
  TASK-CVAC-002 text-fallback path.
- ``AC-4`` — compound IDs (``**AC-LOAD-01** — text``) continue to work.
- ``AC-6`` — end-to-end fixture using the seven-AC FEAT-PEBR run-2
  turn-1 signature: pre-fix ``criteria_met=0``, post-fix ``criteria_met=7``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import CoachValidator  # noqa: E402


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def validator(tmp_path) -> CoachValidator:
    """A CoachValidator anchored at a throwaway worktree path."""
    return CoachValidator(str(tmp_path))


@pytest.fixture
def feat_pebr_run2_criteria() -> list[str]:
    """Seven natural-label criteria mirroring the FEAT-PEBR run-2 turn-1 task."""
    return [
        "- [ ] AC-1: `src/forge/lifecycle_bridge/translation.py` exposes a `translate_payload()` helper",
        "- [ ] AC-2: Helper rejects malformed payloads with a typed `TranslationError`",
        "- [ ] AC-3: Helper emits structured INFO logs for each translated payload",
        "- [ ] AC-4: Existing translation fixtures continue to pass",
        "- [ ] AC-5: Coverage of the translation module remains above 85%",
        "- [ ] AC-6: Helper integrates with the lifecycle dispatcher pipeline",
        "- [ ] AC-7: Concurrent translations serialise on the global write lock",
    ]


@pytest.fixture
def feat_pebr_run2_promises() -> list[dict]:
    """Seven Player completion promises emitted under the natural labels.

    This is the exact ``criterion_id="AC-N"`` (not zero-padded) shape the
    Player produced in FEAT-PEBR run-2 turn 1, which Coach failed to match
    pre-fix.
    """
    return [
        {
            "criterion_id": f"AC-{i}",
            "criterion_text": (
                "src/forge/lifecycle_bridge/translation.py exposes a "
                "translate_payload() helper" if i == 1
                else f"Helper satisfies AC-{i} per task spec"
            ),
            "status": "complete",
            "evidence": f"AC-{i} satisfied by translation_bridge changes (turn 1)",
        }
        for i in range(1, 8)
    ]


# ============================================================================
# AC-2 — Reproducer: natural label AC-N matches Player criterion_id="AC-N"
# ============================================================================


class TestNaturalLabelACMatching:
    """Natural-label ``AC-N:`` criteria match Player promises emitted with the same label."""

    def test_natural_label_matches_player_promise_ac_n(
        self, validator: CoachValidator,
    ):
        """AC-2 — Reproducer: ``AC-1: ...`` + ``criterion_id="AC-1"`` → 1/1.

        Pre-fix this returned ``criteria_met=0/1`` with a
        ``No completion promise for AC-001`` diagnostic. Post-fix, the
        natural-label lookup key matches.
        """
        criteria = ["AC-1: src/forge/foo.py exposes Bar"]
        promises = [
            {
                "criterion_id": "AC-1",
                "criterion_text": "src/forge/foo.py exposes Bar",
                "status": "complete",
                "evidence": "src/forge/foo.py created with class Bar",
            },
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 1
        assert result.all_criteria_met is True
        assert result.criteria_results[0].criterion_id == "AC-1"
        assert result.criteria_results[0].result == "verified"

    def test_natural_label_matches_with_checkbox_prefix(
        self, validator: CoachValidator,
    ):
        """AC-2 variant: checkbox-prefixed ``- [ ] AC-1: ...`` still matches AC-1."""
        criteria = ["- [ ] AC-1: src/forge/foo.py exposes Bar"]
        promises = [
            {
                "criterion_id": "AC-1",
                "criterion_text": "src/forge/foo.py exposes Bar",
                "status": "complete",
                "evidence": "src/forge/foo.py created with class Bar",
            },
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 1
        assert result.criteria_results[0].criterion_id == "AC-1"
        assert result.criteria_results[0].result == "verified"


# ============================================================================
# AC-3 — Zero-padded format coexists via text-fallback path
# ============================================================================


class TestZeroPaddedFormatStillMatches:
    """Player promises with zero-padded ``criterion_id="AC-001"`` still match.

    Backwards-compat path (TASK-CVAC-002 text fallback): when the Player
    emits ``criterion_id="AC-001"`` against a natural-label criterion
    ``AC-1: ...``, the promise's own ``criterion_text`` carries the
    natural label, ``_extract_ac_id`` reads it, and the promise is
    keyed under both ``"AC-001"`` and ``"AC-1"`` in ``promise_map``.
    The criterion's natural-label lookup key (``"AC-1"``) hits.
    """

    def test_zero_padded_id_matches_via_criterion_text_fallback(
        self, validator: CoachValidator,
    ):
        """AC-3 — ``criterion_id="AC-001"`` + ``criterion_text="AC-1: ..."`` → 1/1."""
        criteria = ["AC-1: src/forge/foo.py exposes Bar"]
        promises = [
            {
                "criterion_id": "AC-001",
                "criterion_text": "AC-1: src/forge/foo.py exposes Bar",
                "status": "complete",
                "evidence": "src/forge/foo.py created with class Bar",
            },
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 1
        assert result.all_criteria_met is True
        # The criterion ID is the natural label (AC-1), not the
        # zero-padded form, because extraction now succeeds.
        assert result.criteria_results[0].criterion_id == "AC-1"
        assert result.criteria_results[0].result == "verified"


# ============================================================================
# AC-4 — Compound IDs continue to work
# ============================================================================


class TestCompoundIDsStillMatch:
    """Compound natural labels (e.g. ``**AC-LOAD-01** — text``) continue to match.

    Verifies that the strip-helper change did not regress the bold +
    em-dash compound-ID format covered by TASK-CVAC-001 / FEAT-FD32.
    """

    def test_bold_compound_id_matches(self, validator: CoachValidator):
        """AC-4 — ``**AC-LOAD-01** — text`` + ``criterion_id="AC-LOAD-01"`` → 1/1."""
        criteria = ["**AC-LOAD-01** — Frobnicate the widget"]
        promises = [
            {
                "criterion_id": "AC-LOAD-01",
                "criterion_text": "Frobnicate the widget",
                "status": "complete",
                "evidence": "Widget frobnicator implemented",
            },
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 1
        assert result.all_criteria_met is True
        assert result.criteria_results[0].criterion_id == "AC-LOAD-01"
        assert result.criteria_results[0].result == "verified"

    def test_compound_id_with_checkbox(self, validator: CoachValidator):
        """AC-4 variant: ``- [ ] **AC-LOAD-01** — text`` still extracts AC-LOAD-01."""
        criteria = ["- [ ] **AC-LOAD-01** — Frobnicate the widget"]
        promises = [
            {
                "criterion_id": "AC-LOAD-01",
                "criterion_text": "Frobnicate the widget",
                "status": "complete",
                "evidence": "Widget frobnicator implemented",
            },
        ]

        result = validator._match_by_promises(criteria, promises)

        assert result.criteria_met == 1
        assert result.criteria_results[0].criterion_id == "AC-LOAD-01"
        assert result.criteria_results[0].result == "verified"


# ============================================================================
# AC-6 — End-to-end fixture using FEAT-PEBR run-2 signature
# ============================================================================


class TestFeatPebrRun2Reproducer:
    """Reproduce the FEAT-PEBR run-2 turn-1 ``criteria_met=0/7`` fingerprint.

    Mirrors the exact shape of the run-2 turn-1 inputs:

    - 7 ACs in natural-label form (``AC-1:`` … ``AC-7:``).
    - 7 Player promises with ``criterion_id="AC-N"`` (not zero-padded).

    Pre-fix: ``criteria_met == 0`` because every natural-label criterion
    fell back to ``AC-NNN`` and missed Player's ``AC-N`` keys.
    Post-fix: ``criteria_met == 7`` and ``all_criteria_met == True``
    because the natural label is preserved through the strip step and
    extracted by ``_extract_ac_id``.
    """

    def test_seven_natural_label_acs_match_seven_promises(
        self,
        validator: CoachValidator,
        feat_pebr_run2_criteria: list[str],
        feat_pebr_run2_promises: list[dict],
    ):
        """AC-6 — 7/7 natural-label criteria match 7 ``AC-N`` promises end-to-end."""
        result = validator._match_by_promises(
            feat_pebr_run2_criteria, feat_pebr_run2_promises,
        )

        assert result.criteria_total == 7
        assert result.criteria_met == 7
        assert result.all_criteria_met is True
        assert result.missing == []

        # Verify each criterion is keyed under its natural label, not
        # the zero-padded fallback.
        for i, criterion_result in enumerate(result.criteria_results, start=1):
            assert criterion_result.criterion_id == f"AC-{i}", (
                f"Criterion {i} keyed as {criterion_result.criterion_id!r} "
                f"but expected 'AC-{i}'"
            )
            assert criterion_result.result == "verified"
